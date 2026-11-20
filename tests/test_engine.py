"""Unit, Phase 1 regression, and Phase 2 (Contract v1.1) headless scenario tests."""

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


class TestContractV11(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load_contract(REPO_ROOT / "game.contract.json")
        self.tuning = self.contract["tuning"]

    # --- Phase 1 Regression Tests (updated to standardized Ticket-02 numbers) ---

    def test_contract_v11_schema_and_standard_tuning(self) -> None:
        self.assertEqual(self.contract["contract_version"], "1.1")
        self.assertEqual(self.tuning["player_speed"], 6.0)
        self.assertEqual(self.tuning["dash_speed"], 14.0)
        self.assertEqual(self.tuning["dash_duration_s"], 0.2)
        self.assertEqual(self.tuning["dash_cooldown_s"], 1.5)
        self.assertEqual(self.tuning["carry_capacity"], 10)
        self.assertEqual(self.tuning["lantern_cost"], 10)
        self.assertEqual(self.tuning["night1_duration_s"], 300)
        self.assertEqual(self.tuning["night2_duration_s"], 330)
        self.assertEqual(self.tuning["night3_duration_s"], 360)
        self.assertTrue(self.tuning["fall_enabled"])

    def test_move_pickup_deposit_lit_and_win(self) -> None:
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
        # player_speed=6.0 -> 60 ticks moves to z=6.0, picking up mote at z=3.0 on the way
        inputs = {
            "frames": [
                {"tick": 0, "move": [0, 1], "cam_yaw_deg": 0},
                {"tick": 60, "move": [0, 0], "interact": True},
                {"tick": 61, "interact": False},
            ]
        }
        code, recs, stderr = run_cli(ticks=120, scenario=scenario, inputs=inputs)
        self.assertEqual(code, 0, stderr)
        self.assertEqual(recs[0]["score"], 0)
        events = [r for r in recs if r["type"] == "event"]
        names = [e["name"] for e in events]
        self.assertEqual(names, ["mote_picked", "deposit", "lantern_lit", "game_over"])
        self.assertEqual(events[1]["data"], {"lantern_id": "L1", "amount": 10, "deposited": 10})
        self.assertEqual(recs[-1]["state"], "won")
        # 10*10 (deposit) + 100 (lantern) + floor(98.983)*2 (196) + 3*50 (150) = 546
        self.assertEqual(recs[-1]["score"], 546)

    def test_pulse_stuns_and_pushes_shade_over_15_ticks(self) -> None:
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
        events = [r for r in recs if r["type"] == "event"]
        self.assertTrue(any(e["name"] == "pulse" and e["data"]["stunned_ids"] == ["S1"] for e in events))
        snap20 = [r for r in recs if r["type"] == "snapshot" and r["tick"] == 20][0]
        self.assertEqual(snap20["player"]["carried"], 0)
        self.assertEqual(snap20["shades"][0]["state"], "stunned")
        self.assertAlmostEqual(snap20["shades"][0]["pos"][0], 7.0, places=1)
        self.assertEqual(snap20["score"], 5)

    def test_shade_hit_drops_motes_with_ttl_and_recoil(self) -> None:
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
        self.assertEqual(len(hit), 1)
        self.assertEqual(hit[0]["data"], {"by": "shade", "flames": 1, "dropped": 2})
        snap10 = [r for r in recs if r["type"] == "snapshot" and r["tick"] == 10][0]
        self.assertEqual(snap10["shades"][0]["state"], "recoil")
        dropped_motes = [m for m in snap10["motes"] if m["kind"] == "dropped"]
        self.assertEqual(len(dropped_motes), 2)
        self.assertIsNotNone(dropped_motes[0]["ttl_s"])

    def test_shade_respects_lit_lantern_safe_radius(self) -> None:
        scenario = {
            "player": {"pos": [0, 0, 0], "carried": 0, "flames": 3},
            "random_motes": False,
            "random_shades": False,
            "motes": [],
            "shades": [{"id": "S1", "pos": [9.0, 0, 0], "state": "chase"}],
            "lanterns": [{"id": "L1", "pos": [0, 0, 0], "lit": True, "deposited": 10}],
        }
        code, recs, stderr = run_cli(ticks=120, scenario=scenario, snapshot_every=60)
        self.assertEqual(code, 0, stderr)
        snaps = [r for r in recs if r["type"] == "snapshot"]
        for sn in snaps:
            sx, _, sz = sn["shades"][0]["pos"]
            self.assertGreaterEqual((sx * sx + sz * sz) ** 0.5, 5.99)
        self.assertEqual(snaps[-1]["player"]["flames"], 3)

    def test_dawn_timeout_loss(self) -> None:
        scenario = {"random_motes": False, "random_shades": False, "motes": [], "shades": [], "time_left_s": 0.5}
        code, recs, stderr = run_cli(ticks=60, scenario=scenario)
        self.assertEqual(code, 0, stderr)
        events = [r for r in recs if r["type"] == "event"]
        self.assertEqual(events[-1]["data"], {"result": "lost", "reason": "dawn"})
        self.assertEqual(recs[-1]["ticks"], 30)

    def test_camera_yaw_and_determinism_and_exit_code_2(self) -> None:
        inputs = {"frames": [{"tick": 0, "move": [0, 1], "cam_yaw_deg": 90}]}
        c1, r1, _ = run_cli(seed=99, ticks=60, inputs=inputs, snapshot_every=60)
        c2, r2, _ = run_cli(seed=99, ticks=60, inputs=inputs, snapshot_every=60)
        self.assertEqual(c1, 0)
        self.assertEqual(r1, r2)
        self.assertAlmostEqual(r1[-2]["player"]["pos"][0], 6.0, places=2)

        bad = {"frames": [{"tick": 5}, {"tick": 5}]}
        code_bad, _, err = run_cli(ticks=10, inputs=bad)
        self.assertEqual(code_bad, 2)
        self.assertTrue(len(err.strip()) > 0)

    # --- Phase 2 New Feature Scenario Tests ---

    def test_dash_and_wind_charm_zero_cooldown(self) -> None:
        scenario = {
            "player": {"pos": [0, 0, 0], "carried": 0, "flames": 3},
            "random_motes": False,
            "random_shades": False,
            "motes": [],
            "shades": [],
            "charms": [{"id": "C1", "pos": [0, 0, 0.5], "available": True}],
        }
        inputs = {
            "frames": [
                {"tick": 0, "move": [0, 1]},
                {"tick": 5, "dash": True},
                {"tick": 6, "dash": False},
                {"tick": 20, "dash": True},  # 2nd dash immediately after 12-tick dash because Charm gives 0 CD!
                {"tick": 21, "dash": False},
            ]
        }
        code, recs, stderr = run_cli(night=2, ticks=40, scenario=scenario, inputs=inputs, snapshot_every=40)
        self.assertEqual(code, 0, stderr)
        events = [r for r in recs if r["type"] == "event"]
        self.assertTrue(any(e["name"] == "charm_picked" and e["data"]["charm_id"] == "C1" for e in events))
        dashes = [e for e in events if e["name"] == "dash"]
        self.assertEqual(len(dashes), 2)

    def test_pause_freezes_sim_tick_and_timers(self) -> None:
        scenario = {"random_motes": False, "random_shades": False, "motes": [], "shades": [], "time_left_s": 100}
        inputs = {
            "frames": [
                {"tick": 10, "pause": True},
                {"tick": 11, "pause": False},
                {"tick": 30, "pause": True},
                {"tick": 31, "pause": False},
            ]
        }
        code, recs, stderr = run_cli(ticks=40, scenario=scenario, inputs=inputs, snapshot_every=20)
        self.assertEqual(code, 0, stderr)
        events = [r for r in recs if r["type"] == "event"]
        self.assertEqual([e["name"] for e in events], ["paused", "resumed"])
        snap20 = [r for r in recs if r["type"] == "snapshot" and r["tick"] == 20][0]
        self.assertEqual(snap20["state"], "paused")
        self.assertEqual(snap20["sim_tick"], 10)
        snap40 = [r for r in recs if r["type"] == "snapshot" and r["tick"] == 40][0]
        self.assertEqual(snap40["state"], "playing")
        self.assertEqual(snap40["sim_tick"], 20)

    def test_fall_off_island_ignores_invuln_and_respawns(self) -> None:
        scenario = {
            "player": {"pos": [40.5, 0, 0], "carried": 5, "flames": 2, "invuln_ticks": 90},
            "random_motes": False,
            "random_shades": False,
            "motes": [],
            "shades": [],
        }
        code, recs, stderr = run_cli(night=1, ticks=140, scenario=scenario, snapshot_every=140)
        self.assertEqual(code, 0, stderr)
        hit = [r for r in recs if r["type"] == "event" and r["name"] == "player_hit"]
        self.assertEqual(len(hit), 1)
        self.assertEqual(hit[0]["data"], {"by": "fall", "flames": 1, "dropped": 0, "lost": 5})
        snap_end = [r for r in recs if r["type"] == "snapshot"][-1]
        self.assertEqual(snap_end["player"]["pos"], [0.0, 0.0, 0.0])
        self.assertTrue(snap_end["player"]["invuln"])

    def test_night2_jump_pad_and_drifter_steal_and_pulse_drop(self) -> None:
        # 1. Jump pad launches player from Island A (20,0,18) onto Island B
        sc_pad = {
            "player": {"pos": [20.0, 0.0, 18.0], "carried": 0, "flames": 3},
            "random_motes": False,
            "random_shades": False,
            "random_drifters": False,
            "motes": [],
            "shades": [],
        }
        code, recs, stderr = run_cli(night=2, ticks=100, scenario=sc_pad, snapshot_every=100)
        self.assertEqual(code, 0, stderr)
        final_pos = [r for r in recs if r["type"] == "snapshot"][-1]["player"]["pos"]
        self.assertGreater(final_pos[0], 45.0)  # Landed on Island B!
        self.assertEqual(final_pos[1], 0.0)

        # 2. Drifter steals 3 motes, then Pulse forces drifter_drop
        sc_dr = {
            "player": {"pos": [0, 0, 0], "carried": 8, "flames": 3},
            "random_motes": False,
            "random_shades": False,
            "random_drifters": False,
            "motes": [],
            "shades": [],
            "drifters": [{"id": "D1", "pos": [0.5, 0, 0], "state": "chase"}],
        }
        in_dr = {"frames": [{"tick": 2, "pulse": True}, {"tick": 3, "pulse": False}]}
        code2, recs2, stderr2 = run_cli(night=2, ticks=10, scenario=sc_dr, inputs=in_dr, snapshot_every=10)
        self.assertEqual(code2, 0, stderr2)
        ev2 = [r for r in recs2 if r["type"] == "event"]
        self.assertTrue(any(e["name"] == "drifter_steal" and e["data"]["amount"] == 3 for e in ev2))
        self.assertTrue(any(e["name"] == "drifter_drop" and e["data"]["amount"] == 3 for e in ev2))

    def test_night3_ramp_jump_pad_wind_and_full_night_performance(self) -> None:
        # Test Night 3 jump pad from Tier 1 (0,3,13) to Tier 2 (Y=6)
        sc_n3 = {
            "player": {"pos": [0.0, 3.0, 13.0], "carried": 0, "flames": 3},
            "random_motes": False,
            "random_shades": False,
            "random_drifters": False,
            "wind_enabled": False,
            "motes": [],
            "shades": [],
        }
        code, recs, stderr = run_cli(night=3, ticks=90, scenario=sc_n3, snapshot_every=90)
        self.assertEqual(code, 0, stderr)
        pos = [r for r in recs if r["type"] == "snapshot"][-1]["player"]["pos"]
        self.assertEqual(pos[1], 6.0)

        # Performance: Full Night 3 (21,600 ticks) MUST complete in <= 30s
        t0 = time.perf_counter()
        code_perf, recs_perf, err_perf = run_cli(night=3, seed=7, ticks=21600, snapshot_every=3600)
        elapsed = time.perf_counter() - t0
        self.assertEqual(code_perf, 0, err_perf)
        self.assertLessEqual(elapsed, 30.0, f"Full Night 3 took {elapsed:.2f}s (> 30s limit)")
        self.assertEqual(recs_perf[-1]["type"], "end")


if __name__ == "__main__":
    unittest.main()
