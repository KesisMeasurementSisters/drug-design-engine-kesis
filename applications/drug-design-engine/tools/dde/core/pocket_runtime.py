"""Bounded fpocket execution and failure-safe publication of new result bundles."""

from __future__ import annotations
from contextlib import contextmanager
import fcntl
import math
import re
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import tempfile
import uuid
from .errors import ArtifactError, UsageError
from . import provenance
from .structures import detect_structure_format

MAX_INPUT_BYTES = 128 * 1024 * 1024


def atom_rows(text: str, fmt: str):
    """Decode source identifiers without splitting quoted CIF strings."""
    if fmt == "cif":
        import gemmi

        try:
            block = gemmi.cif.read_string(text).sole_block()
            table = block.find_mmcif_category("_atom_site.")
            if not table:
                raise ValueError("missing atom_site loop")
            names = [x.split(".", 1)[1] for x in table.tags]
            for row in table:
                yield {
                    key: (None if row[i] in (".", "?") else gemmi.cif.as_string(row[i]))
                    for i, key in enumerate(names)
                }
        except (ValueError, RuntimeError) as exc:
            raise ArtifactError("invalid mmCIF structure", detail=str(exc)) from exc
    else:
        for line in text.splitlines():
            if line.startswith(("ATOM  ", "HETATM")):
                if len(line) < 54:
                    raise ArtifactError("truncated PDB atom record")
                yield {
                    "group_PDB": line[:6].strip(),
                    "label_atom_id": line[12:16].strip(),
                    "label_comp_id": line[17:20].strip(),
                    "auth_asym_id": line[21:22].strip(),
                    "auth_seq_id": line[22:26].strip(),
                    "pdbx_PDB_ins_code": line[26:27].strip(),
                    "Cartn_x": line[30:38].strip(),
                    "Cartn_y": line[38:46].strip(),
                    "Cartn_z": line[46:54].strip(),
                }


def validate_input(path: Path) -> str:
    try:
        if path.stat().st_size > MAX_INPUT_BYTES:
            raise ValueError("input exceeds 128 MiB")
        fmt = detect_structure_format(path)
        text = path.read_text(encoding="utf-8")
        if "\0" in text:
            raise ValueError("NUL byte")
        count = 0
        for row in atom_rows(text, fmt):
            for key in ("Cartn_x", "Cartn_y", "Cartn_z"):
                token = row[key]
                if not isinstance(token, str) or not re.fullmatch(
                    r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?", token
                ):
                    raise ValueError("invalid coordinate token")
                value = float(token)
                if not math.isfinite(value) or abs(value) > 1e15:
                    raise ValueError("invalid coordinate")
            for key, limit in (
                ("label_atom_id", 4),
                ("label_comp_id", 7),
                ("auth_asym_id", 15),
                ("label_asym_id", 15),
                ("pdbx_PDB_ins_code", 1),
            ):
                value = row.get(key)
                if value is not None and len(value.encode("utf-8")) > limit:
                    raise ValueError(f"{key} exceeds supported capacity")
            count += 1
            if count > 1_000_000:
                raise ValueError("input exceeds one million atoms")
        if not count:
            raise ValueError("no atom records")
        return fmt
    except (OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        raise ArtifactError("invalid structure for fpocket", detail=str(exc)) from exc


def residue_key(record):
    """Full identity used consistently by parsing, peptide counting and analysis."""
    return (
        record["chain"],
        record["resnum"],
        record.get("insertion_code", ""),
        record.get("label_chain", record["chain"]),
        record.get("label_resnum", record["resnum"]),
    )


def _sequence(value):
    if value is None:
        return None
    if not re.fullmatch(r"[+-]?[0-9]+", value):
        raise ArtifactError("invalid residue number")
    number = int(value)
    if not -(2**31) <= number < 2**31:
        raise ArtifactError("residue number exceeds native integer capacity")
    return number


def _residue(row, fmt):
    author = _sequence(row.get("auth_seq_id"))
    label = _sequence(row.get("label_seq_id"))
    if author is None and label is None:
        raise ArtifactError("missing residue number in both namespaces")
    fallback = fmt == "cif" and (author is None or not row.get("auth_asym_id"))
    if fallback and (label is None or not row.get("label_asym_id")):
        raise ArtifactError("missing complete residue identity in both namespaces")
    chain = row.get("label_asym_id") if fallback else row.get("auth_asym_id") or "_"
    record = {
        "chain": chain,
        "resnum": label if fallback else author,
        "resname": row.get("label_comp_id"),
    }
    if row.get("pdbx_PDB_ins_code"):
        record["insertion_code"] = row["pdbx_PDB_ins_code"]
    label_chain = row.get("label_asym_id")
    if fmt == "cif" and (label_chain != chain or label != record["resnum"]):
        record.update(label_chain=label_chain, label_resnum=label)
    if fmt == "cif" and (author is None or row.get("auth_asym_id") is None):
        record.update(
            auth_chain=row.get("auth_asym_id"),
            auth_resnum=author,
            identity_namespace="label",
        )
    return record


def primary_chain(row):
    if row.get("auth_seq_id") is None or not row.get("auth_asym_id"):
        return row.get("label_asym_id") or "_"
    return row["auth_asym_id"]


def _native_key(row):
    # ABI18's optional HETATM label number is emitted as zero. Recover its
    # original missingness from the verified source map, never infer it from zero.
    return (
        row.get("auth_asym_id"),
        _sequence(row.get("auth_seq_id")),
        row.get("pdbx_PDB_ins_code") or "",
        row.get("label_asym_id"),
        _sequence(row.get("label_seq_id")) or 0,
        row.get("label_comp_id"),
    )


def residue_records(text: str, fmt: str, *, identities=None):
    seen = {}
    for row in atom_rows(text, fmt):
        if identities is not None:
            key = _native_key(row)
            if key not in identities:
                raise ArtifactError("fpocket emitted an unknown residue identity")
            record = dict(identities[key])
        else:
            record = _residue(row, fmt)
        seen[residue_key(record) + (record.get("resname"),)] = record
    return sorted(seen.values(), key=lambda r: repr(residue_key(r)))


def stage_structure(source: Path, work: Path, fmt: str):
    """Normalize missing author IDs explicitly, retaining a reversible identity map."""
    if fmt != "cif":
        shutil.copyfile(source, work)
        return None
    import gemmi

    text = source.read_text(encoding="utf-8")
    document = gemmi.cif.read_string(text)
    block = document.sole_block()
    category = block.get_mmcif_category("_atom_site.", raw=True)
    rows = list(atom_rows(text, fmt))
    for field in ("auth_seq_id", "auth_asym_id"):
        category.setdefault(field, ["?"] * len(rows))
    identities = {}
    for index, row in enumerate(rows):
        record = _residue(row, fmt)
        if record.get("identity_namespace") == "label":
            for author, label in (
                ("auth_seq_id", "label_seq_id"),
                ("auth_asym_id", "label_asym_id"),
            ):
                value = row.get(label)
                row[author] = value
                category[author][index] = gemmi.cif.quote(value)
        key = _native_key(row)
        if key in identities and identities[key] != record:
            raise ArtifactError("ambiguous residue identity after staging")
        identities[key] = record
    block.set_mmcif_category("_atom_site.", category, raw=True)
    document.write_file(str(work))
    return identities


def resolve_selectors(selectors, pockets):
    """Unqualified selectors are compatible only when their identity is unique."""
    records = {residue_key(r): r for p in pockets for r in p.get("residues", [])}
    wanted = set()
    for selector in selectors:
        chain, number, *suffix = selector
        insertion = suffix[0] if suffix else None
        matches = {
            key
            for key in records
            if key[:2] == (chain, number) and (insertion is None or key[2] == insertion)
        }
        if len(matches) > 1:
            raise UsageError(
                "ambiguous residue selector",
                detail=f"{chain}:{number}",
                remedy="specify an insertion code or use an unambiguous residue",
            )
        wanted.update(matches)
    return wanted


def residue_label(key):
    return f"{key[0]}:{key[1]}{key[2]}"


def read_bundle_metadata(source: Path, doc):
    """New records require one canonical completion marker and an intact tree."""
    suffix = ".pockets.json"
    version = doc.get("publication_version")
    if version is not None and version != 1:
        raise ArtifactError("unsupported pocket publication version")
    if version == 1 and not source.name.endswith(suffix):
        raise ArtifactError("new pocket records must retain the .pockets.json filename")
    stem = source.name[: -len(suffix)] if source.name.endswith(suffix) else source.name
    meta_path = source.with_name(f"{stem}.pockets.meta.json")
    if not meta_path.is_file():
        if version == 1:
            raise ArtifactError(
                "pocket bundle is incomplete: missing completion sidecar"
            )
        return {}
    meta = provenance.read_json(meta_path, "provenance sidecar")
    if version != 1:
        return meta
    declared = [x for x in meta.get("outputs", []) if x.get("path") == source.name]
    if len(declared) != 1 or declared[0].get("sha256") != provenance.sha256_file(
        source
    ):
        raise ArtifactError("pocket record does not match completion sidecar")
    tree_name = doc.get("fpocket_output_dir")
    if tree_name != f"{stem}_fpocket":
        raise ArtifactError("invalid pocket output directory")
    tree = source.parent / tree_name
    expected = meta.get("fpocket_output_hashes")
    actual = {
        str(p.relative_to(tree)): provenance.sha256_file(p)
        for p in tree.rglob("*")
        if p.is_file()
    }
    if not expected or actual != expected:
        raise ArtifactError("pocket output tree is incomplete or changed")
    return meta


def _diagnostic_tail(stream):
    stream.seek(0, 2)
    stream.seek(max(0, stream.tell() - 65536))
    return stream.read().decode("utf-8", errors="replace")


def run_bounded(args, cwd: Path, timeout: float = 120):
    import resource

    def limits():
        resource.setrlimit(resource.RLIMIT_FSIZE, (64 * 1024 * 1024, 64 * 1024 * 1024))

    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        child = subprocess.Popen(
            args,
            cwd=cwd,
            stdout=stdout,
            stderr=stderr,
            start_new_session=True,
            preexec_fn=limits,
        )
        try:
            child.wait(timeout=timeout)
        except BaseException as exc:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            child.wait()
            detail = f"limit: {timeout} seconds\nstdout:\n{_diagnostic_tail(stdout)}\nstderr:\n{_diagnostic_tail(stderr)}"
            if isinstance(exc, subprocess.TimeoutExpired):
                raise ArtifactError("fpocket timed out", detail=detail) from exc
            raise
        return subprocess.CompletedProcess(
            args, child.returncode, _diagnostic_tail(stdout), _diagnostic_tail(stderr)
        )


@contextmanager
def calculation_workspace(stage):
    """Keep partial calculation files on failure; clean successful scratch work."""
    work = stage / "calculation"
    work.mkdir()
    try:
        yield work
    except BaseException:
        raise
    else:
        shutil.rmtree(work)


def validate_pockets(
    pockets, required_fields=("score", "druggability_score", "volume")
):
    if not pockets or [p.get("rank") for p in pockets] != list(
        range(1, len(pockets) + 1)
    ):
        raise ArtifactError("empty or incomplete fpocket descriptor output")
    for pocket in pockets:
        for required in required_fields:
            value = pocket.get(required)
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ArtifactError(
                    "missing or non-finite fpocket descriptor", detail=required
                )
        for key, value in pocket.items():
            if isinstance(value, float) and not math.isfinite(value):
                raise ArtifactError("non-finite fpocket descriptor", detail=key)


@contextmanager
def publication(destination: Path, stem: str):
    """Lock the namespace; never overwrite. Commit marker is published last.

    A crashed writer leaves an uncommitted bundle which readers refuse. An ordinary
    exception moves staged/published new files into a retained diagnostic directory.
    Lock files are deliberately retained to avoid lock-inode replacement races.
    """
    lock_path = destination / f".{stem}.pocket.lock"
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    stage = None
    moved = []
    names = [f"{stem}_fpocket", f"{stem}.pockets.json", f"{stem}.pockets.meta.json"]
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if any(os.path.lexists(destination / name) for name in names):
            raise ArtifactError(
                "pocket results already exist",
                remedy="choose a new destination with --out",
            )
        stage = Path(tempfile.mkdtemp(prefix=f".{stem}.pending-", dir=destination))
        yield stage
        if not all((stage / name).exists() for name in names):
            raise ArtifactError("incomplete pocket bundle cannot be published")
        for name in names:
            if os.path.lexists(destination / name):
                raise ArtifactError("publication collision")
            os.rename(stage / name, destination / name)
            moved.append(name)
        stage.rmdir()
        stage = None
    except BlockingIOError as exc:
        raise ArtifactError(
            "another pocket run owns this destination",
            remedy="choose --out or wait for that run",
        ) from exc
    except BaseException as exc:
        if stage is not None:
            (stage / "failure.json").write_text(
                json.dumps(
                    {"error": str(exc), "detail": getattr(exc, "detail", None)},
                    indent=2,
                )
                + "\n"
            )
            for name in reversed(moved):
                os.rename(destination / name, stage / name)
            stage.rename(destination / f".{stem}.failed-{uuid.uuid4().hex}")
        raise
    finally:
        os.close(fd)


def validate_vertices(rows, expected):
    if len(rows) != expected:
        raise ArtifactError("incomplete pocket vertex records")
    for row in rows:
        # fpocket's writer uses adjacent %8.3f coordinates; splitting on spaces
        # fails for neighbouring negative values. Charge/radius follow fixed gaps.
        tail = row[-41:]
        try:
            values = [
                float(tail[a:b])
                for a, b in ((0, 8), (8, 16), (16, 24), (26, 32), (35, 41))
            ]
            if not all(math.isfinite(v) for v in values):
                raise ValueError("non-finite vertex")
        except ValueError as exc:
            raise ArtifactError(
                "invalid fpocket vertex record", detail=str(exc)
            ) from exc
