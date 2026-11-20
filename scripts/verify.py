"""Single-command verification gate for Dao Den Long (Phase 2 / Contract v1.1)."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROOF_DIR = REPO_ROOT / "docs" / "proof" / "phase-2"


def run_step(label: str, cmd: list[str]) -> tuple[str, float]:
    print(f"[verify] {label}: {' '.join(cmd)}")
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, check=False)
    elapsed = time.perf_counter() - t0
    output = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        print(output, file=sys.stderr)
        raise SystemExit(f"[verify] FAILED: {label} (exit {proc.returncode})")
    return output, elapsed


def main() -> None:
    PROOF_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Build / compile check
    run_step(
        "Compile Python sources",
        [sys.executable, "-m", "py_compile", "src/maps.py", "src/engine.py", "src/headless.py", "src/server.py"],
    )

    # 2. Unit, Phase 1 regression, and Phase 2 scenario test suite
    test_out, test_s = run_step("Run unittest suite", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
    (PROOF_DIR / "unittest_output.txt").write_text(test_out, encoding="utf-8")

    # 3. Determinism check across Nights 1, 2, 3
    hashes: dict[str, str] = {}
    for night in (1, 2, 3):
        r1 = PROOF_DIR / f"headless_night{night}_seed42_run1.jsonl"
        r2 = PROOF_DIR / f"headless_night{night}_seed42_run2.jsonl"
        for target in (r1, r2):
            run_step(
                f"Headless Night {night} determinism ({target.name})",
                [
                    sys.executable,
                    "-m",
                    "src.headless",
                    "--seed",
                    "42",
                    "--night",
                    str(night),
                    "--ticks",
                    "600",
                    "--out",
                    str(target),
                    "--snapshot-every",
                    "120",
                ],
            )
        h1 = hashlib.sha256(r1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(r2.read_bytes()).hexdigest()
        if h1 != h2:
            raise SystemExit(f"[verify] FAILED: Non-deterministic output on Night {night}")
        r2.unlink()
        hashes[f"night_{night}"] = h1

    # 4. Full Night 3 performance benchmark (21,600 ticks <= 30s)
    perf_out = PROOF_DIR / "headless_night3_full_21600.jsonl"
    _, full_s = run_step(
        "Full Night 3 benchmark (21,600 ticks)",
        [
            sys.executable,
            "-m",
            "src.headless",
            "--seed",
            "42",
            "--night",
            "3",
            "--ticks",
            "21600",
            "--out",
            str(perf_out),
            "--snapshot-every",
            "3600",
        ],
    )
    if full_s > 30.0:
        raise SystemExit(f"[verify] FAILED: Full Night 3 took {full_s:.2f}s (> 30s)")

    summary = {
        "phase": "phase-2",
        "contract_version": "1.1",
        "unittest_seconds": round(test_s, 3),
        "full_night3_21600_ticks_seconds": round(full_s, 3),
        "determinism_sha256": hashes,
        "status": "PASS",
    }
    (PROOF_DIR / "verify_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"[verify] ALL PHASE 2 CHECKS PASSED (Night 3 21,600 ticks in {full_s:.2f}s)")


if __name__ == "__main__":
    main()
