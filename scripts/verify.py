"""Single-command verification gate for Dao Den Long (runs build, unit tests, and saves real proof)."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROOF_DIR = REPO_ROOT / "docs" / "proof" / "phase-1"


def run_step(label: str, cmd: list[str]) -> str:
    print(f"[verify] {label}: {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, check=False)
    output = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        print(output, file=sys.stderr)
        raise SystemExit(f"[verify] FAILED: {label} (exit {proc.returncode})")
    return output


def main() -> None:
    PROOF_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Build / compile check
    run_step(
        "Compile Python sources",
        [sys.executable, "-m", "py_compile", "src/engine.py", "src/headless.py", "src/server.py"],
    )

    # 2. Unit & Contract v1.0 test suite
    test_out = run_step("Run unittest suite", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
    (PROOF_DIR / "unittest_output.txt").write_text(test_out, encoding="utf-8")

    # 3. Deterministic headless run (two identical runs compared by SHA-256)
    run1_path = PROOF_DIR / "headless_seed42_run1.jsonl"
    run2_path = PROOF_DIR / "headless_seed42_run2.jsonl"
    for target in (run1_path, run2_path):
        run_step(
            f"Headless determinism check ({target.name})",
            [
                sys.executable,
                "-m",
                "src.headless",
                "--seed",
                "42",
                "--night",
                "1",
                "--ticks",
                "300",
                "--out",
                str(target),
                "--snapshot-every",
                "60",
            ],
        )

    h1 = hashlib.sha256(run1_path.read_bytes()).hexdigest()
    h2 = hashlib.sha256(run2_path.read_bytes()).hexdigest()
    if h1 != h2:
        raise SystemExit(f"[verify] FAILED: Non-deterministic output ({h1} != {h2})")
    run2_path.unlink()  # Keep single proof artifact + hash summary

    summary = {
        "phase": "phase-1",
        "contract_version": "1.0",
        "determinism_sha256": h1,
        "status": "PASS",
    }
    (PROOF_DIR / "verify_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"[verify] ALL CHECKS PASSED (determinism sha256={h1[:16]}...)")


if __name__ == "__main__":
    main()
