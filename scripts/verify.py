"""Single-command verification gate for Dao Den Long (Phase 4 / Contract v1.3)."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROOF_DIR = REPO_ROOT / "docs" / "proof" / "phase-4"


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

    run_step(
        "Compile all Python sources",
        [
            sys.executable,
            "-m",
            "py_compile",
            "src/maps.py",
            "src/engine.py",
            "src/headless.py",
            "src/server.py",
            "src/leaderboard.py",
            "src/soak.py",
            "src/bench.py",
        ],
    )

    test_out, test_s = run_step("Run full unittest suite (Phase 1-4)", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
    (PROOF_DIR / "unittest_output.txt").write_text(test_out, encoding="utf-8")

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

    # Run official 10-night soak test into repo root soak.json
    soak_path = REPO_ROOT / "soak.json"
    _, soak_s = run_step(
        "Official 10-Night soak test",
        [sys.executable, "-m", "src.soak", "--seed", "7", "--nights", "10", "--out", str(soak_path)],
    )
    soak_data = json.loads(soak_path.read_text(encoding="utf-8"))
    if soak_data["crashes"] != 0 or soak_data["mem_end_mb"] > soak_data["mem_start_mb"] * 1.2:
        raise SystemExit(f"[verify] FAILED soak thresholds: {soak_data}")

    summary = {
        "phase": "phase-4",
        "contract_version": "1.3",
        "unittest_seconds": round(test_s, 3),
        "soak_10_nights_seconds": round(soak_s, 3),
        "soak_crashes": soak_data["crashes"],
        "soak_mem_start_mb": soak_data["mem_start_mb"],
        "soak_mem_end_mb": soak_data["mem_end_mb"],
        "determinism_sha256": hashes,
        "status": "PASS",
    }
    (PROOF_DIR / "verify_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"[verify] ALL PHASE 4 CHECKS PASSED (10-night soak in {soak_s:.2f}s, mem {soak_data['mem_start_mb']}->{soak_data['mem_end_mb']} MB)")


if __name__ == "__main__":
    main()
