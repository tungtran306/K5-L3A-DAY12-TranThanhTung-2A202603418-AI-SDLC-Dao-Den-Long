# AGENTS.md — Đảo Đèn Lồng (AI SDLC Harness — Phase 3 / Contract v1.2)

## Stack & Commands
- **Build / Check:** `python3 -m py_compile src/maps.py src/engine.py src/headless.py src/server.py`
- **Play 3D Web Game:** `python3 -m src.server` (opens `http://127.0.0.1:8000`)
- **Headless CLI (Contract v1.2):** `python3 -m src.headless --seed 42 --night <1|2|3> --ticks 600 --out out.jsonl`
- **Full Verification Gate:** `python3 scripts/verify.py` (compiles, runs all `tests/`, verifies determinism across Nights 1–3, benchmarks full Night 3 <= 30s, writes proof to `docs/proof/phase-3/`)

## Hard Invariants (Contract v1.2)
1. **Single Source of Truth:** `game.contract.json` (`contract_version: "1.2"`) holds all standardized Ticket-02 & Ticket-03 constants.
2. **Integer Fuel Precision:** Store lantern fuel internally in integer `1/60` units (`fuel_60 ∈ [0..6000]`). Decay `1/60` per tick, draining shades deduct `5/60` per tick. Round to 1 decimal only on output (`0` when unlit).
3. **Lantern Safe Zone & Drain:** Only lit lanterns with `fuel_60 >= 1800` (`>= 30`) have a safe zone. Only `wander` shades target weak lanterns (`< 30`) and enter `drain` at `<= 2m`, emitting `fuel_drain` every 60 ticks.
4. **Dawn Survival Win Rule:** No early win (`all_lit` removed). `no_flames` always loses immediately; at dawn (`time_left_s <= 0`), win (`dawn_survived`) iff lit lanterns `>= ceil(0.6 * total)`.
5. **Dynamic Capacity:** `min(20, 10 + 2 * successful_lights)` (pre-lit scenario lanterns do not count).
6. **Evidence Integrity:** Never fake tests, never silently skip broken tests (update with documented reason), never hand-edit proof outputs. Always run `python3 scripts/verify.py` before committing or tagging.
