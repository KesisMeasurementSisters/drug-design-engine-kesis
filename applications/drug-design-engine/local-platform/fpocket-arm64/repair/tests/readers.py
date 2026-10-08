"""Generate independently defined edge fixtures, then test real reader callbacks.

Usage: reader_edges.py prepare FPOCKET_SOURCE FIXTURES
       reader_edges.py run PROBE FIXTURES OUTPUT ABI [sanitized]
"""

import json, math, os, signal, subprocess, sys, time
from pathlib import Path


def invoke(args, limit, env=None):
    start = time.monotonic()
    p = subprocess.Popen(
        list(map(str, args)),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
        env=env,
        start_new_session=True,
    )
    try:
        stdout, stderr = p.communicate(timeout=limit)
        timed = False
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        stdout, stderr = p.communicate()
        timed = True
    return {
        "exit": p.returncode,
        "timeout": timed,
        "seconds": round(time.monotonic() - start, 3),
        "stdout": stdout,
        "stderr": stderr,
    }


def run(probe, fixtures, out, abi):
    out.mkdir(exist_ok=False)
    results = []
    env = dict(
        os.environ,
        ASAN_OPTIONS="detect_leaks=0:halt_on_error=1",
        UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1",
    )
    for case in json.loads((fixtures / "cases.json").read_text()):
        r = invoke([probe, case["reader"], fixtures / case["file"]], 30, env)
        (out / (case["name"] + ".log")).write_text(r["stdout"] + "\n" + r["stderr"])
        record = {k: v for k, v in r.items() if k not in ("stdout", "stderr")}
        record.update(name=case["name"], valid_input=case["valid"])
        memory_error = any(
            x in r["stderr"] for x in ("AddressSanitizer:", "runtime error:")
        )
        try:
            assert not r["timeout"], "timeout"
            assert not memory_error, "memory-safety failure"
            if not case["valid"]:
                assert r["exit"] in (
                    66,
                    67,
                    68,
                ), "invalid input accepted, crashed, or reader did not execute"
            else:
                assert r["exit"] == 0, "valid input rejected or crashed"
                obj = json.loads(
                    next(
                        x[11:]
                        for x in r["stdout"].splitlines()
                        if x.startswith("PROBE_JSON ")
                    )
                )
                (out / (case["name"] + ".json")).write_text(
                    json.dumps(obj, indent=2) + "\n"
                )
                assert obj["abi"] == abi
                if case["reader"] == "pdbx":
                    assert len(obj["atoms"]) == len(case["atoms"])
                    for actual, expected in zip(obj["atoms"], case["atoms"]):
                        for key in ("name", "resname", "chain", "resid"):
                            assert actual[key] == expected[key], (
                                key,
                                actual[key],
                                expected[key],
                            )
                        assert all(
                            math.isclose(x, y, abs_tol=1e-4)
                            for x, y in zip(actual["xyz"], expected["xyz"])
                        )
                else:
                    assert obj["natoms"] == 3 and [
                        a["name"].rstrip() for a in obj["atoms"]
                    ] == ["O", "H1", "H2"]
                    assert obj["bonds"] == [[1, 2], [1, 3]]
                    assert all(
                        a["resname"].rstrip() == "WAT" and a["resid"] == 1
                        for a in obj["atoms"]
                    )
                    assert [a["atomicnumber"] for a in obj["atoms"]] == [8, 1, 1]
                    for atom, mass in zip(obj["atoms"], [15.9994, 1.008, 1.008]):
                        assert math.isclose(atom["mass"], mass, abs_tol=1e-4)
            record["passed"] = True
        except Exception as e:
            record.update(passed=False, error=str(e))
        results.append(record)
        print(json.dumps(record), flush=True)
        (out / "report.json").write_text(json.dumps(results, indent=2) + "\n")
    return all(x["passed"] for x in results)


if __name__ == "__main__":
    raise SystemExit(
        not run(
            Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]), int(sys.argv[5])
        )
    )
