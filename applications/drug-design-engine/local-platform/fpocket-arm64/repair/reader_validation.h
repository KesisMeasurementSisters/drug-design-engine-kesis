/*
 * Copyright 2026 Technologies Kesis & Sisters Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/* Local input-boundary repairs for pinned molfile readers; no scoring changes.
 * Bounded lexical validation precedes the original conversion callbacks.
 * Files are normalized into a private tmpfile, preventing validation/use races.
 */
#ifndef DDE_READER_VALIDATION_H
#define DDE_READER_VALIDATION_H
#include <algorithm>
#include <cerrno>
#include <climits>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
namespace dde_reader {
const size_t MAX_FILE = 128 * 1024 * 1024, MAX_ATOMS = 1000000;
static void require(bool ok, const char *msg) {
  if (!ok)
    throw std::runtime_error(msg);
}
static std::string trim(std::string s) {
  auto a = s.find_first_not_of(" \t\r\n");
  return a == s.npos ? "" : s.substr(a, s.find_last_not_of(" \t\r\n") - a + 1);
}
static std::string load(const char *path) {
  std::ifstream f(path, std::ios::binary);
  require(bool(f), "cannot open input");
  std::string out;
  char buf[8192];
  while (f) {
    f.read(buf, sizeof buf);
    out.append(buf, size_t(f.gcount()));
    require(out.size() <= MAX_FILE, "input exceeds 128 MiB reader limit");
  }
  require(f.eof() && out.find('\0') == out.npos,
          "input read error or NUL byte");
  return out;
}
static long integer(const std::string &s) {
  require(!s.empty(), "missing integer");
  char *end;
  errno = 0;
  long n = strtol(s.c_str(), &end, 10);
  require(!errno && end == s.c_str() + s.size() && n >= INT_MIN && n <= INT_MAX,
          "invalid integer");
  return n;
}
static bool decimal_token(const std::string &value) {
  size_t cursor = 0;
  if (cursor < value.size() && (value[cursor] == '+' || value[cursor] == '-'))
    ++cursor;
  auto digits = [&]() {
    size_t start = cursor;
    while (cursor < value.size() && value[cursor] >= '0' &&
           value[cursor] <= '9')
      ++cursor;
    return cursor - start;
  };
  size_t mantissa_digits = digits();
  if (cursor < value.size() && value[cursor] == '.') {
    ++cursor;
    mantissa_digits += digits();
  }
  if (!mantissa_digits)
    return false;
  if (cursor < value.size() && (value[cursor] == 'e' || value[cursor] == 'E')) {
    ++cursor;
    if (cursor < value.size() && (value[cursor] == '+' || value[cursor] == '-'))
      ++cursor;
    if (!digits())
      return false;
  }
  return cursor == value.size();
}

static double real(const std::string &s) {
  require(decimal_token(s), "invalid decimal real");
  char *end;
  errno = 0;
  double n = strtod(s.c_str(), &end);
  require(!errno && end == s.c_str() + s.size() && std::isfinite(n) &&
              std::isfinite(float(n)),
          "invalid or nonfinite real");
  return n;
}
struct Token {
  std::string value;
  bool quoted;
};
static std::vector<Token> lex(const std::string &s) {
  std::vector<Token> out;
  size_t i = 0;
  while (i < s.size()) {
    if (isspace(static_cast<unsigned char>(s[i]))) {
      ++i;
      continue;
    }
    if (s[i] == '#') {
      while (i < s.size() && s[i] != '\n')
        ++i;
      continue;
    }
    std::string word;
    bool quoted = false;
    if (s[i] == ';' && (i == 0 || s[i - 1] == '\n')) {
      quoted = true;
      size_t start = ++i, end = s.find("\n;", i);
      require(end != s.npos, "unterminated multiline string");
      word = s.substr(start, end - start);
      i = end + 2;
    } else if (s[i] == '\'' || s[i] == '"') {
      quoted = true;
      char q = s[i++];
      bool closed = false;
      while (i < s.size()) {
        char c = s[i++];
        if (c == q &&
            (i == s.size() || isspace(static_cast<unsigned char>(s[i])))) {
          closed = true;
          break;
        }
        word += c;
      }
      require(closed, "unterminated quoted field");
    } else {
      while (i < s.size() && !isspace(static_cast<unsigned char>(s[i])))
        word += s[i++];
    }
    out.push_back({word, quoted});
    require(out.size() <= MAX_FILE / 2, "too many tokens");
  }
  return out;
}
static bool control(const Token &t) {
  return !t.quoted && (t.value == "loop_" || t.value == "stop_" ||
                       t.value.compare(0, 1, "_") == 0 ||
                       t.value.compare(0, 5, "data_") == 0 ||
                       t.value.compare(0, 5, "save_") == 0);
}
static bool missing(const std::string &s) { return s == "?" || s == "."; }
static FILE *pdbx(const char *path) {
  FILE *f = nullptr;
  try {
    auto ts = lex(load(path));
    std::vector<std::string> tags;
    std::vector<std::vector<std::string>> rows;
    for (size_t i = 0; i < ts.size(); ++i) {
      if (ts[i].quoted || ts[i].value != "loop_")
        continue;
      size_t first = ++i;
      while (i < ts.size() && !ts[i].quoted &&
             ts[i].value.compare(0, 1, "_") == 0)
        ++i;
      size_t cols = i - first;
      require(cols > 0, "loop without columns");
      bool atom = ts[first].value.compare(0, 11, "_atom_site.") == 0;
      size_t start = i;
      while (i < ts.size() && !control(ts[i]))
        ++i;
      require((i - start) % cols == 0, "incomplete loop row");
      if (atom) {
        require(tags.empty() && cols < 32,
                "duplicate atom loop or too many columns");
        std::set<std::string> unique;
        for (size_t j = first; j < first + cols; ++j) {
          require(ts[j].value.compare(0, 11, "_atom_site.") == 0 &&
                      unique.insert(ts[j].value).second,
                  "mixed or duplicate atom column");
          require(ts[j].value.size() < 128, "atom column name too long");
          tags.push_back(ts[j].value.substr(11));
        }
        require((i - start) / cols <= MAX_ATOMS, "too many atoms");
        for (size_t j = start; j < i; j += cols) {
          std::vector<std::string> row;
          for (size_t k = 0; k < cols; ++k) {
            require(!(ts[j + k].quoted && missing(ts[j + k].value)),
                    "quoted missing token is not representable");
            row.push_back(ts[j + k].value);
          }
          rows.push_back(row);
        }
      }
      if (i)
        --i;
    }
    require(!rows.empty(), "missing atom records");
    std::map<std::string, size_t> idx;
    for (size_t i = 0; i < tags.size(); ++i)
      idx[tags[i]] = i;
    // Some supported label-numbered files omit the author-number column.
    // The namespace fallback is explicit; a present missing token is rejected.
    if (!idx.count("auth_seq_id")) {
      require(tags.size() + 1 < 32 && idx.count("label_seq_id"),
              "cannot represent author-number fallback");
      idx["auth_seq_id"] = tags.size();
      tags.push_back("auth_seq_id");
      for (auto &row : rows) {
        require(!missing(row[idx["label_seq_id"]]),
                "missing fallback residue number");
        row.push_back(row[idx["label_seq_id"]]);
      }
    }
    for (auto key :
         {"group_PDB", "id", "type_symbol", "label_atom_id", "label_comp_id",
          "label_asym_id", "label_seq_id", "auth_asym_id", "auth_seq_id",
          "Cartn_x", "Cartn_y", "Cartn_z"})
      require(idx.count(key), "missing required atom column");
    const std::map<std::string, size_t> caps = {
        {"group_PDB", 6},        {"type_symbol", 2},   {"label_atom_id", 4},
        {"auth_atom_id", 4},     {"label_comp_id", 7}, {"auth_comp_id", 7},
        {"label_asym_id", 15},   {"auth_asym_id", 15}, {"label_alt_id", 1},
        {"pdbx_PDB_ins_code", 1}};
    for (auto &row : rows) {
      size_t row_bytes = 1;
      for (auto &value : row)
        row_bytes += value.size() + 1;
      require(row_bytes < 4095, "atom row exceeds legacy buffer capacity");
      for (size_t k = 0; k < row.size(); ++k) {
        const auto &v = row[k];
        const auto &key = tags[k];
        require(!v.empty() && v.size() < 1024 &&
                    v.find_first_of("\r\n\t ") == v.npos,
                "unrepresentable atom field");
        auto cap = caps.find(key);
        if (cap != caps.end())
          require(v.size() <= cap->second,
                  "atom field exceeds downstream capacity");
        if (key == "Cartn_x" || key == "Cartn_y" || key == "Cartn_z")
          require(std::abs(real(v)) <= 1e15,
                  "coordinate exceeds safe arithmetic range");
        else if (key == "id" || key == "label_seq_id" || key == "auth_seq_id" ||
                 key == "pdbx_PDB_model_num") {
          if (!missing(v))
            integer(v);
        } else if (key == "occupancy" || key == "B_iso_or_equiv" ||
                   key == "pdbx_formal_charge") {
          if (!missing(v))
            real(v);
        }
      }
      require(
          !missing(row[idx["auth_seq_id"]]) &&
              !missing(row[idx["auth_asym_id"]]),
          "missing author identity; stage an explicit label fallback first");
      if (row[idx["group_PDB"]] == "ATOM")
        require(!missing(row[idx["label_seq_id"]]),
                "missing protein label residue number");
      require(row[idx["group_PDB"]] == "ATOM" ||
                  row[idx["group_PDB"]] == "HETATM",
              "invalid atom record kind");
    }
    f = tmpfile();
    require(f, "cannot create normalized input");
    fputs("data_validated\n#\nloop_\n", f);
    for (auto &tag : tags)
      fprintf(f, "_atom_site.%s\n", tag.c_str());
    for (auto &row : rows) {
      for (auto &v : row)
        fprintf(f, "%s ", v.c_str());
      fputc('\n', f);
    }
    fputs("#\n", f);
    require(!ferror(f), "normalized input write failed");
    rewind(f);
    return f;
  } catch (const std::exception &e) {
    if (f)
      fclose(f);
    fprintf(stderr, "pdbx validation: %s\n", e.what());
    return nullptr;
  }
}
struct Section {
  std::string name, format;
  std::vector<std::string> lines, values;
  char kind = 0;
  int width = 0, repeat = 0;
};
static FILE *parm7(const char *path) {
  FILE *f = nullptr;
  try {
    std::istringstream input(load(path));
    std::string line, version;
    require(bool(std::getline(input, version)) &&
                version.compare(0, 8, "%VERSION") == 0 && version.size() <= 80,
            "missing VERSION");
    std::vector<Section> sections;
    std::set<std::string> seen;
    while (std::getline(input, line)) {
      if (!line.empty() && line.back() == '\r')
        line.pop_back();
      require(line.size() <= 80, "topology line too long");
      if (line.compare(0, 8, "%COMMENT") == 0)
        continue;
      if (line.compare(0, 6, "%FLAG ") == 0) {
        std::string name = trim(line.substr(6));
        require(!name.empty() && seen.insert(name).second,
                "duplicate or empty section");
        sections.push_back(Section());
        sections.back().name = name;
        continue;
      }
      if (trim(line).empty() && sections.empty())
        continue;
      require(!sections.empty(), "content outside section");
      auto &s = sections.back();
      if (s.format.empty()) {
        s.format = trim(line);
        require(s.format.compare(0, 8, "%FORMAT(") == 0 &&
                    s.format.back() == ')',
                "missing FORMAT");
        auto fmt = s.format.substr(8, s.format.size() - 9);
        size_t p = 0;
        while (p < fmt.size() && isdigit(static_cast<unsigned char>(fmt[p])))
          ++p;
        s.repeat = p ? int(integer(fmt.substr(0, p))) : 1;
        require(p < fmt.size(), "invalid format");
        s.kind = toupper(static_cast<unsigned char>(fmt[p++]));
        size_t a = p;
        while (p < fmt.size() && isdigit(static_cast<unsigned char>(fmt[p])))
          ++p;
        s.width = int(integer(fmt.substr(a, p - a)));
        require(s.repeat > 0 && s.width > 0 && s.repeat <= 80 / s.width &&
                    (s.kind == 'A' || s.kind == 'I' || s.kind == 'E'),
                "unsupported format");
        if (p < fmt.size()) {
          require(s.kind == 'E' && fmt[p++] == '.', "invalid format suffix");
          integer(fmt.substr(p));
        }
      } else {
        require(line.empty() || line[0] != '%', "unexpected directive");
        s.lines.push_back(line);
        if (s.name == "TITLE" || s.name == "CTITLE")
          continue;
        require(line.size() <= size_t(s.repeat * s.width),
                "too many fields on line");
        for (size_t p = 0; p < line.size(); p += s.width) {
          auto v = trim(line.substr(p, s.width));
          require(p + s.width <= line.size() || trim(line.substr(p)).empty(),
                  "truncated fixed-width field");
          if (!v.empty()) {
            if (s.kind == 'I')
              integer(v);
            if (s.kind == 'E')
              real(v);
            s.values.push_back(v);
          }
        }
      }
    }
    require(sections.size() >= 2 &&
                (sections[0].name == "TITLE" || sections[0].name == "CTITLE") &&
                sections[1].name == "POINTERS",
            "unsupported section order");
    std::map<std::string, Section *> by;
    for (auto &s : sections) {
      require(!s.format.empty(), "section without FORMAT");
      by[s.name] = &s;
    }
    auto get = [&](const char *name, size_t n, char kind,
                   bool required) -> Section * {
      auto it = by.find(name);
      if (it == by.end()) {
        require(!required, "missing required section");
        return nullptr;
      }
      auto s = it->second;
      require(s->kind == kind && s->values.size() == n,
              "wrong section type or record count");
      return s;
    };
    require(by.count("POINTERS"), "missing POINTERS");
    auto ptr = by["POINTERS"];
    require(ptr->kind == 'I' &&
                (ptr->values.size() == 31 || ptr->values.size() == 32),
            "incomplete POINTERS");
    std::vector<long> p;
    for (auto &v : ptr->values) {
      long x = integer(v);
      require(x >= 0 && x <= 1000000, "invalid control count");
      p.push_back(x);
    }
    long n = p[0], nr = p[11];
    require(n > 0 && n <= long(MAX_ATOMS) && nr > 0 && nr <= n && p[1] <= 32767,
            "invalid atom/residue/type counts");
    get("ATOM_NAME", n, 'A', true);
    get("AMBER_ATOM_TYPE", n, 'A', true);
    get("RESIDUE_LABEL", nr, 'A', true);
    auto rp = get("RESIDUE_POINTER", nr, 'I', true);
    long prev = 0;
    for (auto &v : rp->values) {
      long x = integer(v);
      require(x > prev && x <= n, "invalid residue pointer");
      prev = x;
    }
    require(integer(rp->values[0]) == 1,
            "first residue must start at atom one");
    for (auto key : {"CHARGE", "MASS"})
      get(key, n, 'E', false);
    auto an = get("ATOMIC_NUMBER", n, 'I', false);
    if (an)
      for (auto &v : an->values)
        require(integer(v) >= 0 && integer(v) <= 118, "invalid element number");
    for (int j = 0; j < 2; ++j) {
      long count = p[j ? 3 : 2];
      auto s = get(j ? "BONDS_WITHOUT_HYDROGEN" : "BONDS_INC_HYDROGEN",
                   3 * count, 'I', count > 0);
      if (s)
        for (size_t k = 0; k < s->values.size(); k += 3) {
          long a = integer(s->values[k]), b = integer(s->values[k + 1]),
               type = integer(s->values[k + 2]);
          require(a >= 0 && b >= 0 && a % 3 == 0 && b % 3 == 0 && a / 3 < n &&
                      b / 3 < n && type > 0 && type <= p[15],
                  "invalid bond index");
        }
    }
    // The legacy callback requires labels before pointers. Normalize this
    // dependency only, preserving every other section's order and contents.
    auto labels =
        std::find_if(sections.begin(), sections.end(), [](const Section &s) {
          return s.name == "RESIDUE_LABEL";
        });
    auto pointers =
        std::find_if(sections.begin(), sections.end(), [](const Section &s) {
          return s.name == "RESIDUE_POINTER";
        });
    if (labels > pointers) {
      Section saved = *labels;
      auto position = pointers - sections.begin();
      sections.erase(labels);
      sections.insert(sections.begin() + position, saved);
    }
    f = tmpfile();
    require(f, "cannot create normalized topology");
    fprintf(f, "%s\n", trim(version).c_str());
    for (auto &s : sections) {
      fprintf(f, "%%FLAG %s\n%s\n", s.name.c_str(), s.format.c_str());
      for (auto &row : s.lines)
        fprintf(f, "%s\n", row.c_str());
    }
    require(!ferror(f), "normalized topology write failed");
    rewind(f);
    return f;
  } catch (const std::exception &e) {
    if (f)
      fclose(f);
    fprintf(stderr, "parm7 validation: %s\n", e.what());
    return nullptr;
  }
}
} // namespace dde_reader
#endif
