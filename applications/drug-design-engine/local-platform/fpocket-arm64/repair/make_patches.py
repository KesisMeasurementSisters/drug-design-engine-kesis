"""Generate reviewable patches from the exact pinned, untouched source trees."""

import difflib, sys
from pathlib import Path

base = Path(sys.argv[1])
dest = Path(__file__).parent / "patches"
dest.mkdir(exist_ok=True)


def edit(rel, fn):
    src = base / rel
    old = src.read_text()
    new = fn(old)
    (dest / (src.name + ".patch")).write_text(
        "".join(
            difflib.unified_diff(
                old.splitlines(True),
                new.splitlines(True),
                fromfile="a/" + rel,
                tofile="b/" + rel,
            )
        )
    )


def replace(s, a, b):
    if a not in s:
        raise ValueError("Patch context not found: " + a[:80])
    return s.replace(a, b)


def pdbx(s):
    s = '#include "reader_validation.h"\n' + s
    s = replace(s, "#define CHAIN_SIZE 4", "#define CHAIN_SIZE 16")
    s = replace(s, "new pdbxParser;", "new pdbxParser();")
    s = replace(
        s,
        'parser->file = fopen(filepath, "r");',
        "parser->file = dde_reader::pdbx(filepath);",
    )
    s = replace(s, "fclose(parser->file);", "if (parser->file) fclose(parser->file);")
    a = s.index(
        "static void getNextWord(char * str, void * word, int& pos, int maxstrlen, int maxwordlen) {"
    )
    b = s.index("\n\nstatic float stringToFloat", a)
    s = (
        s[:a]
        + """static void getNextWord(char *str, void *word, int& pos, int maxstrlen, int maxwordlen) {
  char *w = static_cast<char *>(word);
  if (maxwordlen <= 0) throw std::runtime_error("invalid token capacity");
  w[0] = 0;
  while (pos < maxstrlen && str[pos] && isspace(static_cast<unsigned char>(str[pos]))) ++pos;
  int n = 0;
  while (pos < maxstrlen && str[pos] && !isspace(static_cast<unsigned char>(str[pos]))) {
    if (n >= maxwordlen-1) throw std::runtime_error("token exceeds destination");
    w[n++] = str[pos++];
  }
  w[n] = 0;
}
"""
        + s[b:]
    )
    a = s.index(
        "static void skipNextWord(char * str, void * word, int& pos, int maxlen) {"
    )
    b = s.index("\n\nstatic bool isPDB_DevFile", a)
    s = s[:a] + """static void skipNextWord(char *str, void *, int& pos, int maxlen) {
  while (pos < maxlen && str[pos] && isspace(static_cast<unsigned char>(str[pos]))) ++pos;
  while (pos < maxlen && str[pos] && !isspace(static_cast<unsigned char>(str[pos]))) ++pos;
}
""" + s[b:]
    s = s.replace(
        "getNextWord(buffer, columns[i], pos, sizeof(buffer), COLUMN_BUFFER_SIZE);",
        """size_t capacity = COLUMN_BUFFER_SIZE;
        switch(table[i]) {
          case COLUMN_TYPE: capacity=sizeof(atom->type); break;
          case COLUMN_TYPE_AUTH: capacity=TYPE_SIZE; break;
          case COLUMN_RESNAME: capacity=sizeof(atom->resname); break;
          case COLUMN_INSERTION: capacity=sizeof(atom->insertion); break;
          case COLUMN_CHAIN_AUTH: capacity=CHAIN_SIZE; break;
          case COLUMN_ALT_LOC: capacity=(count ? sizeof(atom->altloc) : sizeof(altlocbuffer)); break;
#if (vmdplugin_ABIVERSION >= 20)
          case COLUMN_CHAIN: capacity=sizeof(atom->chain); break;
#endif
        }
        getNextWord(buffer, columns[i], pos, sizeof(buffer), capacity);""",
        1,
    )
    a = s.index("    /* check to see if the chain length is greater than 2 */")
    b = s.index("#endif", a)
    s = s[:a] + """    memcpy(atom->chain, chainbuffer, strlen(chainbuffer)+1);
""" + s[b:]
    s = replace(
        s,
        "if (bfactorbuffer[0] != '.' && bfactorbuffer[0] != '.')",
        "if (bfactorbuffer[0] && bfactorbuffer[0] != '.' && bfactorbuffer[0] != '?')",
    )
    for v in ("occupancy", "charge"):
        s = replace(
            s, f"if ({v}buffer[0] != '.'", f"if ({v}buffer[0] && {v}buffer[0] != '.'"
        )
    # Reset buffers and never compute member addresses through one-past atoms.
    s = replace(
        s,
        "    pos = 0;\n    for (i=0; i<tableSize; ++i)",
        "    memset(atom, 0, sizeof(*atom));\n    pos = 0;\n    for (i=0; i<tableSize; ++i)",
    )
    s = replace(
        s,
        "    ++atom;\n    typeAuth",
        "    if (count >= parser->natoms) break;\n    ++atom;\n    typeAuth",
    )
    s = replace(
        s,
        '    printf("pdbxplugin) error opening file.\\n");\n    return NULL;',
        '    printf("pdbxplugin) error opening file.\\n");\n    delete_pdbxParser(data->parser); delete data;\n    return NULL;',
    )
    s = replace(
        s,
        "  if (parseStructure(atoms, optflags, data->parser)) {",
        "  try { if (parseStructure(atoms, optflags, data->parser)) {",
    )
    s = replace(
        s,
        "  //PS/ skipping this",
        '  } catch (const std::exception &e) { fprintf(stderr, "pdbx: %s\\n", e.what()); return MOLFILE_ERROR; }\n  //PS/ skipping this',
    )
    return s


def parm(s):
    s = '#include "reader_validation.h"\n' + s
    s = replace(s, "open_parm7_file(filename, &popn)", "dde_reader::parm7(filename)")
    s = replace(
        s,
        "  char *resnames = NULL;",
        "  char *resnames = NULL;\n  bool ok = true;\n  p->nbonds = 0;\n  memset(atoms, 0, sizeof(*atoms)*prm->Natom);",
    )
    s = replace(
        s,
        "        fgets(buf, 85, file);",
        "        if (!fgets(buf, 85, file)) { delete [] resnames; return MOLFILE_ERROR; }",
    )
    s = replace(
        s,
        "        continue;\n      }\n      if (!parse_parm7_respointers",
        "        delete [] resnames; return MOLFILE_ERROR;\n      }\n      if (!parse_parm7_respointers",
    )
    s = s.replace(") break;", ") { ok = false; break; }").replace(
        "        break;\n      // XXX", "        { ok = false; break; }\n      // XXX"
    )
    s = replace(
        s,
        "  return MOLFILE_SUCCESS;\n}\n\nstatic int read_parm7_bonds",
        "  return ok ? MOLFILE_SUCCESS : MOLFILE_ERROR;\n}\n\nstatic int read_parm7_bonds",
    )
    return s


edit(
    "molfile_plugin-5f817f263b89e8420174bb4bf0d0875a6ebe6136/vmd/plugins/molfile_plugin/src/pdbxplugin.C",
    pdbx,
)
edit(
    "molfile_plugin-5f817f263b89e8420174bb4bf0d0875a6ebe6136/vmd/plugins/molfile_plugin/src/parm7plugin.C",
    parm,
)


def fpout(s):
    s = "#include <sys/stat.h>\n#include <errno.h>\n" + s
    s = s.replace("status = system(command);", "status = mkdir(out_path, 0777);")
    s = s.replace("if (status != 0)", "if (status != 0 && errno != EEXIST)")
    s = s.replace(
        'sprintf(command, "mkdir %s", out_path_tmp);\n      status = mkdir(out_path, 0777);',
        'if (mkdir(out_path_tmp, 0777) != 0 && errno != EEXIST) { perror("pocket directory"); return; }',
    )
    s = s.replace(
        "int status = mkdir(out_path, 0777);",
        'int status = mkdir(out_path, 0777);\n      if (status != 0 && errno != EEXIST) { perror("pocket directory"); return; }',
    )
    s = s.replace(
        "strcpy(pdb_code, pdbname);",
        'if (strlen(pdbname) > 140) { fprintf(stderr, "fpocket path exceeds supported length\\n"); return; }\n      strcpy(pdb_code, pdbname);',
    )
    s = s.replace(
        "strcpy(pdb_code, input_name);",
        "if (strlen(input_name) > 140) return;\n      strcpy(pdb_code, input_name);",
    )
    return s


def visu(s):
    s = "#include <sys/stat.h>\n" + s
    s = s.replace(
        "status = system(sys_cmd);",
        'status = chmod(fout, 0755);\n            if (status != 0) { perror("visualization permissions"); }',
    )
    return s


edit("fpocket-4.2.2/src/fpout.c", fpout)
edit("fpocket-4.2.2/src/write_visu.c", visu)


def parm_helpers(s):
    # All uses are bounded even after lexical prevalidation; never rely on it
    # as the sole protection for a C destination buffer.
    s = s.replace(
        'fscanf(file, "%s\\n", buf);',
        'if (fscanf(file, "%1023s\\n", buf) != 1) return 0;',
    )
    s = s.replace(
        'fscanf(file, "%s\\n", sdum);',
        'if (fscanf(file, "%511s\\n", sdum) != 1) { delete prm; return NULL; }',
    )
    s = s.replace(
        'fscanf(file,"%s\\n", sdum);',
        'if (fscanf(file,"%511s\\n", sdum) != 1) { delete prm; return NULL; }',
    )
    s = s.replace("new parmstruct;", "new parmstruct();")
    s = s.replace(
        "      fgets(buf, 85, file);", "      if (!fgets(buf, 85, file)) return 0;"
    )
    s = s.replace(
        '  fscanf(file, " %d", &cur);',
        '  if (fscanf(file, " %d", &cur) != 1 || cur != 1) return 0;',
    )
    s = s.replace(
        "    while (cur < next) {",
        "    if (next <= cur || next > natoms) return 0;\n    while (cur < next) {",
    )
    s = s.replace(
        "  length = strlen(name);",
        "  if (strlen(name) > sizeof(cbuf)-3) return NULL;\n  length = strlen(name);",
    )
    return s


edit(
    "molfile_plugin-5f817f263b89e8420174bb4bf0d0875a6ebe6136/vmd/plugins/molfile_plugin/src/ReadPARM7.h",
    parm_helpers,
)
