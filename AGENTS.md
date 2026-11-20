# AGENTS.md — Đảo Đèn Lồng (AI SDLC Harness)

## Stack & Commands
- **Build / Check:** `python3 -m py_compile src/engine.py src/headless.py src/server.py`
- **Play 3D Web Game:** `python3 -m src.server` (opens `http://127.0.0.1:8000`)
- **Headless CLI (Contract v1.0):** `python3 -m src.headless --seed 42 --night 1 --ticks 300 --out out.jsonl`
- **Full Verification Gate:** `python3 scripts/verify.py` (compiles, runs all `tests/`, verifies determinism SHA-256, writes proof to `docs/proof/phase-1/`)

## Hard Invariants (Never Violate)
1. **Single Source of Truth:** `game.contract.json` owns all `tuning` parameters. Both `src/engine.py` and `web/game.js` MUST read/match it exactly.
2. **Test Contract v1.0 Strictness:**
   - 60 tick/s fixed step (`DT = 1/60`). Tick 0 snapshot is after scenario setup and before any input.
   - Step `k` applies tick `k` input and produces tick `k+1`; events emit `tick = k+1`.
   - Distances are measured on the horizontal XZ plane (`<= r`), no entity radius added.
   - Scenario setup emits NO events and adds NO score.
   - Invalid `--inputs` / `--scenario` JSON or non-strictly-increasing frame ticks MUST exit with code `2` and log to `stderr`.
   - Same `--seed`, scenario, and inputs MUST produce byte-identical JSONL output.
3. **Evidence Integrity:** Never fake tests, never hand-edit proof outputs, never commit `.env` or secrets.
4. **Verification Before Done:** Never mark a task or phase complete while `python3 scripts/verify.py` fails.
