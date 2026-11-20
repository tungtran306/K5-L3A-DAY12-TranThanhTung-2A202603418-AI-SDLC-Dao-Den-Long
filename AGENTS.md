# AGENTS.md — Đảo Đèn Lồng (AI SDLC Harness — Phase 2 / Contract v1.1)

## Stack & Commands
- **Build / Check:** `python3 -m py_compile src/maps.py src/engine.py src/headless.py src/server.py`
- **Play 3D Web Game:** `python3 -m src.server` (opens `http://127.0.0.1:8000`)
- **Headless CLI (Contract v1.1):** `python3 -m src.headless --seed 42 --night <1|2|3> --ticks 600 --out out.jsonl`
- **Full Verification Gate:** `python3 scripts/verify.py` (compiles, runs all `tests/` including Phase 1 regression & Phase 2 scenarios, verifies determinism across Nights 1–3, benchmarks full Night 3 21,600 ticks <= 30s, writes proof to `docs/proof/phase-2/`)

## Hard Invariants (Contract v1.1)
1. **Single Source of Truth:** `game.contract.json` (`contract_version: "1.1"`) holds all standardized Ticket-02 constants.
2. **Exact 12-Step Tick Order:**
   `input/pause -> decrement timers -> move May & fall check -> pickup motes & charms -> interact lanterns -> safe zones -> pulse -> move shades & drifters -> collisions (drifter steal BEFORE shade hit, sorted by id) -> scheduled spawns -> win/lose (no_flames > all_lit > dawn) -> snapshot`.
3. **Pause Semantics:** While paused, `tick` increments, `sim_tick` and all timers/spawns freeze, snapshot `state: "paused"`.
4. **Shade States:** Must strictly use `spawning`, `wander`, `chase`, `recoil`, `stunned`.
5. **Fall Off Island (`Y < -10`):** Ignores invuln, happens once, `-1` Flame, loses ALL carried motes (`lost` field in `player_hit`), waits 60 ticks then respawns at `(0,0,0)` with 90-tick invuln.
6. **Performance:** Full Night (21,600 ticks) headless MUST finish in `<= 30s`.
7. **Evidence Integrity:** Never fake tests, never hand-edit proof outputs, never commit `.env` or secrets. Always run `python3 scripts/verify.py` before committing or tagging.
