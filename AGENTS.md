# AGENTS.md — Đảo Đèn Lồng (AI SDLC Harness — Phase 4 / Release v1.0.0 / Contract v1.3)

## Stack & Commands
- **Build / Check:** `python3 -m py_compile src/maps.py src/engine.py src/headless.py src/server.py src/leaderboard.py src/soak.py src/bench.py`
- **Play 3D Web Game:** `python3 -m src.server` (opens `http://127.0.0.1:8000`)
- **Export Leaderboard:** `python3 -m src.server --export-leaderboard out.json`
- **Headless CLI (Contract v1.3):** `python3 -m src.headless --seed 42 --night <1|2|3> --ticks 600 --out out.jsonl`
- **3D Benchmark (1280×720, 200 shades, 100 motes):** `python3 -m src.bench --seed 42 --duration 30 --out bench.json`
- **10-Night Soak Test:** `python3 -m src.soak --seed 7 --nights 10 --out soak.json`
- **Full Verification Gate:** `python3 scripts/verify.py` (compiles, runs all Phase 1–4 tests, verifies determinism across Nights 1–3, runs 10-night soak test, writes proof to `docs/proof/phase-4/`)
- **Package Release Bundle:** `python3 scripts/package_release.py` (outputs `dist/dao-den-long-v1.0.0.zip`)

## Hard Invariants (Contract v1.3)
1. **Single Source of Truth:** `game.contract.json` (`contract_version: "1.3"`) declares all tuning constants plus `bench_cmd` and `soak_cmd`.
2. **Standard Benchmark & Soak Purity:** Creative 3D-only features (Magnet & Light Shield charms) MUST be disabled in headless, soak, and benchmark scenes.
3. **Integer Fuel Precision & Dawn Survival:** Retain all Contract v1.2 invariants (`fuel_60 ∈ [0..6000]`, `drain` state, `dawn_survived` win rule, `capacity = min(20, 10 + 2*successful_lights)`).
4. **Evidence Integrity:** `bench.json` and `soak.json` must be real, unmodified outputs from running the commands above. Never commit `.env` or secrets.
