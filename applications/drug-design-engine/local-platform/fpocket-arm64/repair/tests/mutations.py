"""10,000 deterministic mutations per reader, sanitizer exit/timeout checks.

Random bytes are not assumed malformed. A mutation may parse successfully; the
safety contract is bounded termination and no sanitizer findings. Semantic
accept/reject expectations are separately frozen in the boundary corpus.
"""

import hashlib, json, os, random, signal, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from release_checks import digest, require, write_binding

require(not sys.flags.optimize, "Do not disable acceptance assertions")
probe, fixtures, out = map(Path, sys.argv[1:4])
out.mkdir(exist_ok=False)
env = dict(
    os.environ,
    ASAN_OPTIONS="detect_leaks=0:halt_on_error=1",
    UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1",
)
bound = {"sanitized-probe": probe, "mutation-runner": Path(__file__)}
bound.update({"fixture/" + p.name: p for p in fixtures.iterdir() if p.is_file()})
before = {name: digest(p) for name, p in bound.items()}
results = []
start = time.monotonic()
for reader, seed in [("pdbx", 420218), ("parm7", 420219)]:
    rng = random.Random(seed)
    base = (
        fixtures / ("minimal.cif" if reader == "pdbx" else "water.parm7")
    ).read_bytes()
    index = []
    failures = []
    for i in range(10000):
        data = bytearray(base)
        mode = i % 5
        pos = rng.randrange(len(data))
        if mode == 0:
            data = data[:pos]
        elif mode == 1:
            data[pos : pos + rng.randrange(1, 30)] = bytes(
                rng.randrange(256) for _ in range(rng.randrange(1, 40))
            )
        elif mode == 2:
            data[pos:pos] = rng.choice(
                [
                    b"A" * 1024,
                    b"999999999999999999",
                    b"\x00",
                    b"\n%FLAG MASS\n",
                    b"'\nloop_\n",
                ]
            )
        elif mode == 3:
            for _ in range(1 + rng.randrange(8)):
                data[rng.randrange(len(data))] = rng.randrange(256)
        else:
            data[pos : pos + rng.randrange(1, 40)] = b""
        sha = hashlib.sha256(data).hexdigest()
        index.append(sha)
        path = out / "current.input"
        path.write_bytes(data)
        p = subprocess.Popen(
            [str(probe), reader, str(path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            start_new_session=True,
        )
        try:
            stdout, stderr = p.communicate(timeout=30)
            timed = False
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            stdout, stderr = p.communicate()
            timed = True
        bad = (
            timed
            or p.returncode not in (0, 66, 67, 68)
            or any(x in stderr for x in (b"AddressSanitizer:", b"runtime error:"))
        )
        if bad:
            stem = f"{reader}-{i:05d}"
            (out / (stem + ".input")).write_bytes(data)
            (out / (stem + ".log")).write_bytes(stdout + b"\n" + stderr)
            failures.append(
                {"case": i, "sha256": sha, "exit": p.returncode, "timeout": timed}
            )
        if i % 1000 == 999:
            print(reader, i + 1, "failures", len(failures), flush=True)
    (out / (reader + "-hashes.json")).write_text(json.dumps(index) + "\n")
    results.append(
        {"reader": reader, "seed": seed, "cases": 10000, "failures": failures}
    )
    (out / "report.json").write_text(
        json.dumps({"results": results, "seconds": time.monotonic() - start}, indent=2)
        + "\n"
    )
require(not any(r["failures"] for r in results), "Mutation failures")
require(
    before == {name: digest(p) for name, p in bound.items()}, "Mutation inputs changed"
)
bound["result/report.json"] = out / "report.json"
write_binding(out / "binding.json", bound)
(out / "binding-paths.json").write_text(
    json.dumps({name: str(p) for name, p in bound.items()}, indent=2) + "\n"
)
