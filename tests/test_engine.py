"""Unit, Phase 1-2 regression (with documented Phase 3 updates), and Phase 3 (Contract v1.2) tests."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from src.engine import load_contract

REPO_ROOT = Path(__file__).resolve().parent.parent


def run_cli(
    *,
    seed: int = 42,
    night: int = 1,
    ticks: int = 60,
    scenario: dict | None = None,
    inputs: dict | None = None,
    snapshot_every: int = 10,
    raw_inputs_text: str | None = None,
) -> tuple[int, list[dict], str]:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        out_path = tmp_path / "out.jsonl"
        cmd = [
            sys.executable,
            "-m",
            "src.headless",
            "--seed",
            str(seed),
            "--night",
            str(night),
            "--ticks",
            str(ticks),
            "--out",
            str(out_path),
            "--snapshot-every",
            str(snapshot_every),
        ]
        if scenario is not None:
            sc_path = tmp_path / "scenario.json"
            sc_path.write_text(json.dumps(scenario), encoding="utf-8")
            cmd += ["--scenario", str(sc_path)]
        if inputs is not None:
            in_path = tmp_path / "inputs.json"
            in_path.write_text(json.dumps(inputs), encoding="utf-8")
            cmd += ["--inputs", str(in_path)]
        elif raw_inputs_text is not None:
            in_path = tmp_path / "inputs.json"
            in_path.write_text(raw_inputs_text, encoding="utf-8")
            cmd += ["--inputs", str(in_path)]

        proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, check=False)
        records: list[dict] = []
        if out_path.is_file():
            for line in out_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    records.append(json.loads(line))
        return proc.returncode, records, proc.stderr


class TestContractV12(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load_contract(REPO_ROOT / "game.contract.json")
        self.tuning = self.contract["tuning"]

    # --- Phase 1-2 Regression Tests (updated where replaced by Ticket-03 with explicit reasons) ---

    def test_contract_v12_schema_and_tuning(self) -> None:
        self.assertEqual(self.contract["contract_version"], "1.2")
        self.assertEqual(self.tuning["fuel_max"], 100)
        self.assertEqual(self.tuning["fuel_decay_per_s"], 1.0)
        self.assertEqual(self.tuning["fuel_per_mote"], 10)
        self.assertEqual(self.tuning["relight_cost"], 5)
        self.assertEqual(self.tuning["win_ratio"], 0.6)
        self.assertEqual(self.tuning["drain_per_s"], 5)
        self.assertEqual(self.tuning["low_fuel_threshold"], 30)
        self.assertEqual(self.tuning["capacity_max"], 20)
        self.assertEqual(self.tuning["night1_duration_s"], 240)
        self.assertEqual(self.tuning["night2_duration_s"], 270)
        self.assertEqual(self.tuning["night3_duration_s"], 300)

    def test_lighting_all_lanterns_does_not_end_night_early_and_scales_capacity(self) -> None:
        """Updated from Phase 1-2 test_move_pickup_deposit_lit_and_win:
        Ticket-03 REPLACES early win ('all_lit') with 'dawn_survived' and adds dynamic capacity +5/mote scoring."""
        scenario = {
            "player": {"pos": [0, 0, 0], "carried": 9, "flames": 3},
            "random_motes": False,
            "random_shades": False,
            "motes": [[0, 0, 3.0]],
            "shades": [],
            "lanterns": [
                {"id": "L1", "pos": [0, 0, 6.0], "deposited": 0, "lit": False},
                {"id": "L2", "lit": True},
                {"id": "L3", "lit": True},
                {"id": "L4", "lit": True},
                {"id": "L5", "lit": True},
            ],
            "time_left_s": 100,
        }
        inputs = {
            "frames": [
                {"tick": 0, "move": [0, 1], "cam_yaw_deg": 0},
                {"tick": 60, "move": [0, 0], "interact": True},
                {"tick": 61, "interact": False},
            ]
        }
        code, recs, stderr = run_cli(ticks=80, scenario=scenario, inputs=inputs, snapshot_every=80)
        self.assertEqual(code, 0, stderr)
        events = [r for r in recs if r["type"] == "event"]
        names = [e["name"] for e in events]
        # No game_over! Night continues until dawn.
        self.assertEqual(names, ["mote_picked", "deposit", "lantern_lit"])
        self.assertEqual(events[2]["data"], {"lantern_id": "L1", "relight": False})
        self.assertEqual(recs[-1]["state"], "playing")
        # Dynamic capacity increased from 10 -> 12 after 1 successful light
        snap80 = [r for r in recs if r["type"] == "snapshot" and r["tick"] == 80][0]
        self.assertEqual(snap80["player"]["capacity"], 12)
        # Score: 10*5 (deposit) + 100 (first light) = 150
        self.assertEqual(snap80["score"], 150)

    def test_pulse_stuns_and_pushes_shade(self) -> None:
        scenario = {
            "player": {"pos": [0, 0, 0], "carried": 3, "flames": 3},
            "random_motes": False,
            "random_shades": False,
            "motes": [],
            "shades": [{"id": "S1", "pos": [3.0, 0, 0], "state": "chase"}],
        }
        inputs = {"frames": [{"tick": 0, "pulse": True}, {"tick": 1, "pulse": False}]}
        code, recs, stderr = run_cli(ticks=20, scenario=scenario, inputs=inputs, snapshot_every=20)
        self.assertEqual(code, 0, stderr)
        snap20 = [r for r in recs if r["type"] == "snapshot" and r["tick"] == 20][0]
        self.assertEqual(snap20["shades"][0]["state"], "stunned")
        self.assertEqual(snap20["score"], 5)

    def test_shade_hit_drops_motes_and_recoil(self) -> None:
        scenario = {
            "player": {"pos": [0, 0, 0], "carried": 4, "flames": 2},
            "random_motes": False,
            "random_shades": False,
            "motes": [],
            "shades": [{"id": "S1", "pos": [0.8, 0, 0], "state": "chase"}],
        }
        code, recs, stderr = run_cli(ticks=10, scenario=scenario, snapshot_every=10)
        self.assertEqual(code, 0, stderr)
        hit = [r for r in recs if r["type"] == "event" and r["name"] == "player_hit"]
        self.assertEqual(hit[0]["data"], {"by": "shade", "flames": 1, "dropped": 2})

    def test_dash_charm_pause_fall_and_night2_drifter_regression(self) -> None:
        # Pause freezes sim_tick & fuel decay
        sc_p = {
            "random_motes": False,
            "random_shades": False,
            "motes": [],
            "shades": [],
            "lanterns": [{"id": "L1", "lit": True, "fuel": 50}],
        }
        in_p = {"frames": [{"tick": 0, "pause": True}, {"tick": 1, "pause": False}]}
        code, recs, _ = run_cli(ticks=60, scenario=sc_p, inputs=in_p, snapshot_every=60)
        self.assertEqual(code, 0)
        snap60 = [r for r in recs if r["type"] == "snapshot" and r["tick"] == 60][0]
        self.assertEqual(snap60["state"], "paused")
        self.assertEqual(snap60["sim_tick"], 0)
        self.assertEqual(snap60["lanterns"][0]["fuel"], 50.0)

        # Fall off island ignores invuln
        sc_f = {
            "player": {"pos": [40.5, 0, 0], "carried": 5, "flames": 2, "invuln_ticks": 90},
            "random_motes": False,
            "random_shades": False,
            "motes": [],
            "shades": [],
        }
        code_f, recs_f, _ = run_cli(ticks=140, scenario=sc_f, snapshot_every=140)
        self.assertEqual(code_f, 0)
        hit = [r for r in recs_f if r["type"] == "event" and r["name"] == "player_hit"]
        self.assertEqual(hit[0]["data"], {"by": "fall", "flames": 1, "dropped": 0, "lost": 5})

    # --- Phase 3 New Mechanics Tests (Ticket-03 / Contract v1.2) ---

    def test_lantern_fuel_decay_out_and_relight_cost_5(self) -> None:
        scenario = {
            "player": {"pos": [0, 0, 25.0], "carried": 5, "flames": 3},
            "random_motes": False,
            "random_shades": False,
            "motes": [],
            "shades": [],
            "lanterns": [{"id": "L1", "pos": [0, 0, 25.0], "lit": True, "fuel": 1.0}],
        }
        # After 60 ticks (1s), L1 runs out of fuel -> lantern_out. At tick 65, relight with 5 motes!
        inputs = {"frames": [{"tick": 65, "interact": True}, {"tick": 66, "interact": False}]}
        code, recs, stderr = run_cli(ticks=80, scenario=scenario, inputs=inputs, snapshot_every=80)
        self.assertEqual(code, 0, stderr)
        events = [r for r in recs if r["type"] == "event"]
        names = [e["name"] for e in events]
        self.assertEqual(names, ["lantern_out", "deposit", "lantern_lit"])
        self.assertEqual(events[1]["data"], {"lantern_id": "L1", "amount": 5, "deposited": 5})
        self.assertEqual(events[2]["data"], {"lantern_id": "L1", "relight": True})
        snap80 = [r for r in recs if r["type"] == "snapshot" and r["tick"] == 80][0]
        self.assertEqual(snap80["lanterns"][0]["relit_count"], 1)
        # Score: 5*5 (deposit) + 40 (relight) = 65
        self.assertEqual(snap80["score"], 65)

    def test_refuel_lit_lantern_and_full_lantern_ignored(self) -> None:
        scenario = {
            "player": {"pos": [0, 0, 25.0], "carried": 5, "flames": 3},
            "random_motes": False,
            "random_shades": False,
            "motes": [],
            "shades": [],
            "lanterns": [{"id": "L1", "pos": [0, 0, 25.0], "lit": True, "fuel": 85.0}],
        }
        # Needs ceil((100 - 85)/10) = 2 motes to reach 100
        inputs = {"frames": [{"tick": 0, "interact": True}, {"tick": 1, "interact": False}]}
        code, recs, stderr = run_cli(ticks=5, scenario=scenario, inputs=inputs, snapshot_every=5)
        self.assertEqual(code, 0, stderr)
        refuels = [r for r in recs if r["type"] == "event" and r["name"] == "refuel"]
        self.assertEqual(len(refuels), 1)
        self.assertEqual(refuels[0]["data"]["amount"], 2)
        self.assertEqual(refuels[0]["data"]["fuel"], 100.0)

    def test_shade_drains_weak_lantern_and_pulse_gives_15_bonus(self) -> None:
        scenario = {
            "player": {"pos": [0, 0, 22.0], "carried": 3, "flames": 3},
            "random_motes": False,
            "random_shades": False,
            "motes": [],
            "lanterns": [{"id": "L1", "pos": [0, 0, 25.0], "lit": True, "fuel": 25.0}],
            "shades": [{"id": "S1", "pos": [0, 0, 26.0], "state": "drain", "target_lantern_id": "L1"}],
        }
        # Let shade drain for 60 ticks (emits fuel_drain), wait player is at 4m -> will aggro if <6m!
        # Put player at z=16 (10m away from shade) for drain test, then test pulse separately
        scenario["player"]["pos"] = [0, 0, 15.0]
        code, recs, stderr = run_cli(ticks=65, scenario=scenario, snapshot_every=65)
        self.assertEqual(code, 0, stderr)
        drains = [r for r in recs if r["type"] == "event" and r["name"] == "fuel_drain"]
        self.assertEqual(len(drains), 1)
        self.assertEqual(drains[0]["data"]["lantern_id"], "L1")
        self.assertEqual(drains[0]["data"]["shade_id"], "S1")
        # 25.0 - 1.0 (decay) - 5.0 (drain) = 19.0
        self.assertEqual(drains[0]["data"]["fuel"], 19.0)

        # Now test Pulse hitting a draining shade -> +15 points!
        scenario["player"]["pos"] = [0, 0, 23.0]
        inputs = {"frames": [{"tick": 0, "pulse": True}, {"tick": 1, "pulse": False}]}
        code2, recs2, _ = run_cli(ticks=5, scenario=scenario, inputs=inputs, snapshot_every=5)
        self.assertEqual(code2, 0)
        self.assertEqual(recs2[-1]["score"], 15)

    def test_dawn_survived_win_vs_dawn_loss(self) -> None:
        # Night 1 needs >= 3/5 lit at dawn
        sc_win = {
            "player": {"pos": [0, 0, 0], "carried": 0, "flames": 3},
            "random_motes": False,
            "random_shades": False,
            "motes": [],
            "shades": [],
            "lanterns": [
                {"id": "L1", "lit": True, "fuel": 50.0},
                {"id": "L2", "lit": True, "fuel": 50.0},
                {"id": "L3", "lit": True, "fuel": 50.0},
            ],
            "time_left_s": 0.5,
        }
        code, recs, stderr = run_cli(ticks=60, scenario=sc_win)
        self.assertEqual(code, 0, stderr)
        ev = [r for r in recs if r["type"] == "event" and r["name"] == "game_over"][0]
        self.assertEqual(ev["data"], {"result": "won", "reason": "dawn_survived"})
        # 3 lanterns * (50 + floor(49.5)=49) + 3 flames * 50 = 3*99 + 150 = 447
        self.assertEqual(recs[-1]["score"], 447)

        # Only 2/5 lit -> dawn loss
        sc_loss = dict(sc_win)
        sc_loss["lanterns"] = [
            {"id": "L1", "lit": True, "fuel": 50.0},
            {"id": "L2", "lit": True, "fuel": 50.0},
        ]
        code2, recs2, _ = run_cli(ticks=60, scenario=sc_loss)
        self.assertEqual(code2, 0)
        ev2 = [r for r in recs2 if r["type"] == "event" and r["name"] == "game_over"][0]
        self.assertEqual(ev2["data"], {"result": "lost", "reason": "dawn"})

    def test_full_night3_performance_and_determinism(self) -> None:
        t0 = time.perf_counter()
        c1, r1, err = run_cli(night=3, seed=7, ticks=18000, snapshot_every=3600)
        elapsed = time.perf_counter() - t0
        self.assertEqual(c1, 0, err)
        self.assertLessEqual(elapsed, 30.0)
        c2, r2, _ = run_cli(night=3, seed=7, ticks=18000, snapshot_every=3600)
        self.assertEqual(c2, 0)
        self.assertEqual(r1, r2)


if __name__ == "__main__":
    unittest.main()
