# Copyright 2026 Technologies Kesis & Sisters Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Small, explicit release gates shared by qualification and provisioning."""

import hashlib
import json
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_rows(rows, expected, identity):
    require(isinstance(rows, list) and bool(rows), "missing check records")
    require(bool(expected), "missing expected check inventory")
    require(all(isinstance(row, dict) for row in rows), "invalid check schema")
    names = [row.get(identity) for row in rows]
    require(
        len(names) == len(expected) and set(names) == set(expected),
        "incomplete or duplicate checks",
    )
    require(
        all(row.get("passed") is True for row in rows), "failed or incomplete check"
    )
    require(
        not any(row.get("timeout") or row.get("skipped") for row in rows),
        "timed out or skipped check",
    )
    return rows


def checked_report(path, expected, identity="name"):
    value = json.loads(Path(path).read_text())
    if isinstance(value, dict):
        require(value.get("passed") is True, "report did not complete successfully")
        rows = value.get("checks")
    else:
        rows = value
    return validate_rows(rows, expected, identity)


def validate_dde(rows, expected):
    require(
        isinstance(rows, list) and bool(rows) and bool(expected),
        "missing DDE test modules",
    )
    require(all(isinstance(row, dict) for row in rows), "invalid DDE report schema")
    names = [row.get("module") for row in rows]
    require(
        len(names) == len(expected) and set(names) == set(expected),
        "incomplete DDE module inventory",
    )
    for row in rows:
        require(
            row.get("exit") == 0 and type(row.get("tests")) is int and row["tests"] > 0,
            "DDE module failed or collected no tests",
        )
        require(
            all(row.get(key) == 0 for key in ("failures", "errors", "skipped")),
            "DDE module has failures, errors, skips or missing counts",
        )
    return sum(row["tests"] for row in rows)


def write_binding(path, files):
    path = Path(path)
    require(not path.exists(), "binding already exists")
    require(bool(files), "empty evidence binding")
    path.write_text(
        json.dumps(
            {name: digest(file) for name, file in sorted(files.items())}, indent=2
        )
        + "\n"
    )


def verify_binding(path, files):
    expected = json.loads(Path(path).read_text())
    require(bool(files) and set(expected) == set(files), "binding inventory mismatch")
    require(
        all(digest(file) == expected[name] for name, file in files.items()),
        "evidence or tested build changed",
    )


def implementation_files(package):
    package = Path(package)
    source = package.parents[2] / "tools/dde"
    files = {
        name: source / name for name in ("commands/pocket.py", "core/pocket_runtime.py")
    }
    for name in (
        "reader_validation.h",
        "build.sh",
        "make_patches.py",
        "apply_patch.py",
    ):
        files["recipe/" + name] = package / name
    files.update({"patch/" + p.name: p for p in (package / "patches").glob("*.patch")})
    return files
