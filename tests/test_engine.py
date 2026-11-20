"""Unit & headless contract verification tests for Dao Den Long (Phase 1 / Contract v1.0)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
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

        proc = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        records: list[dict] = []
        if out_path.is_file():
            for line in out_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    records.append(json.loads(line))
        return proc.returncode, records, proc.stderr


class TestContractV1(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load_contract(REPO_ROOT / "game.contract.json")
        self.tuning = self.contract["tuning"]

    def test_contract_schema_fields(self) -> None:
        self.assertEqual(self.contract["contract_version"], "1.0")
        self.assertEqual(self.tuning["lantern_count_night1"], 5)
        for key in (
            "player_speed",
            "carry_capacity",
            "lantern_cost",
            "pickup_radius",
            "interact_radius",
            "pulse_cost",
            "pulse_radius",
            "night1_duration_s",
            "flames",
            "invuln_s",
            "hit_drop_ratio",
            "pulse_stun_s",
            "pulse_push_m",
            "pulse_cooldown_s",
            "safe_radius",
            "shade_speed",
            "shade_hit_radius",
            "fall_enabled",
            "score",
        ):
            self.assertIn(key, self.tuning)

    def test_move_pickup_deposit_lit_and_win(self) -> None:
        # 4 lanterns already lit in scenario (must NOT emit events or add score)
        scenario = {
            "player": {"pos": [0, 0, 0], "carried": 3, "flames": 3},
            "random_motes": False,
            "random_shades": False,
            "motes": [[0, 0, 3.5]],
            "shades": [],
            "lanterns": [
                {"id": "L1", "pos": [0, 0, 7.0], "deposited": 0, "lit": False},
                {"id": "L2", "lit": True},
                {"id": "L3", "lit": True},
                {"id": "L4", "lit": True},
                {"id": "L5", "lit": True},
            ],
            "time_left_s": 100,
        }
        # Speed 7 m/s -> 1s (60 ticks) moves to z=7.0, picking up mote at z=3.5 on the way
        inputs = {
            "frames": [
                {"tick": 0, "move": [0, 1], "cam_yaw_deg": 0},
                {"tick": 60, "move": [0, 0], "interact": True},
                {"tick": 61, "interact": False},
            ]
        }
        code, recs, stderr = run_cli(ticks=120, scenario=scenario, inputs=inputs)
        self.assertEqual(code, 0, stderr)
        # Tick 0 snapshot has 0 score (scenario setup gives no points)
        self.assertEqual(recs[0]["type"], "snapshot")
        self.assertEqual(recs[0]["tick"], 0)
        self.assertEqual(recs[0]["score"], 0)

        events = [r for r in recs if r["type"] == "event"]
        names = [e["name"] for e in events]
        self.assertEqual(names, ["mote_picked", "deposit", "lantern_lit", "game_over"])
        self.assertEqual(events[0]["data"]["carried"], 4)
        self.assertEqual(events[1]["data"], {"lantern_id": "L1", "amount": 4, "deposited": 4})
        self.assertEqual(events[2]["data"], {"lantern_id": "L1"})
        self.assertEqual(events[3]["data"], {"result": "won", "reason": "all_lit"})
        self.assertEqual(recs[-1]["type"], "end")
        self.assertEqual(recs[-1]["state"], "won")
        self.assertGreater(recs[-1]["score"], 0)

    def test_pulse_stuns_and_pushes_shade(self) -> None:
        scenario = {
            "player": {"pos": [0, 0, 0], "carried": 2, "flames": 3},
            "random_motes": False,
            "random_shades": False,
            "motes": [],
            "shades": [{"id": "S1", "pos": [4.0, 0, 0]}],
        }
        inputs = {
            "frames": [
                {"tick": 0, "pulse": True},
                {"tick": 1, "pulse": False},
            ]
        }
        code, recs, stderr = run_cli(ticks=20, scenario=scenario, inputs=inputs, snapshot_every=10)
        self.assertEqual(code, 0, stderr)
        events = [r for r in recs if r["type"] == "event"]
        self.assertTrue(any(e["name"] == "pulse" and e["data"]["stunned_ids"] == ["S1"] for e in events))
        snap10 = [r for r in recs if r["type"] == "snapshot" and r["tick"] == 10][0]
        self.assertEqual(snap10["player"]["carried"], 0)
        self.assertEqual(snap10["shades"][0]["state"], "stunned")
        self.assertGreaterEqual(snap10["shades"][0]["pos"][0], 9.5)

    def test_shade_hit_drops_motes_and_loses_no_flames(self) -> None:
        scenario = {
            "player": {"pos": [0, 0, 0], "carried": 4, "flames": 1},
            "random_motes": False,
            "random_shades": False,
            "motes": [],
            "shades": [{"id": "S1", "pos": [1.5, 0, 0]}],
        }
        code, recs, stderr = run_cli(ticks=60, scenario=scenario)
        self.assertEqual(code, 0, stderr)
        events = [r for r in recs if r["type"] == "event"]
        hit = [e for e in events if e["name"] == "player_hit"]
        self.assertEqual(len(hit), 1)
        self.assertEqual(hit[0]["data"], {"by": "shade", "flames": 0, "dropped": 2})
        self.assertEqual(events[-1]["name"], "game_over")
        self.assertEqual(events[-1]["data"], {"result": "lost", "reason": "no_flames"})
        self.assertEqual(recs[-1]["state"], "lost")

    def test_shade_respects_lit_lantern_safe_radius(self) -> None:
        scenario = {
            "player": {"pos": [0, 0, 0], "carried": 0, "flames": 3},
            "random_motes": False,
            "random_shades": False,
            "motes": [],
            "shades": [{"id": "S1", "pos": [10.0, 0, 0]}],
            "lanterns": [{"id": "L1", "pos": [0, 0, 0], "lit": True, "deposited": 4}],
        }
        code, recs, stderr = run_cli(ticks=180, scenario=scenario, snapshot_every=60)
        self.assertEqual(code, 0, stderr)
        snaps = [r for r in recs if r["type"] == "snapshot"]
        for sn in snaps:
            sx, _, sz = sn["shades"][0]["pos"]
            self.assertGreaterEqual((sx * sx + sz * sz) ** 0.5, self.tuning["safe_radius"] - 0.01)
        self.assertEqual(snaps[-1]["player"]["flames"], 3)

    def test_dawn_timeout_loss(self) -> None:
        scenario = {
            "player": {"pos": [0, 0, 0], "carried": 0, "flames": 3},
            "random_motes": False,
            "random_shades": False,
            "motes": [],
            "shades": [],
            "time_left_s": 0.5,
        }
        code, recs, stderr = run_cli(ticks=60, scenario=scenario)
        self.assertEqual(code, 0, stderr)
        events = [r for r in recs if r["type"] == "event"]
        self.assertEqual(events[-1]["name"], "game_over")
        self.assertEqual(events[-1]["data"], {"result": "lost", "reason": "dawn"})
        self.assertEqual(recs[-1]["ticks"], 30)

    def test_camera_yaw_and_diagonal_normalization(self) -> None:
        scenario = {
            "player": {"pos": [0, 0, 0], "carried": 0, "flames": 3},
            "random_motes": False,
            "random_shades": False,
            "motes": [],
            "shades": [],
        }
        # cam_yaw_deg = 90, move = [0, 1] -> x' = sin(90)=1, z' = cos(90)=0 -> moves along +X
        inputs = {"frames": [{"tick": 0, "move": [0, 1], "cam_yaw_deg": 90}]}
        code, recs, stderr = run_cli(ticks=60, scenario=scenario, inputs=inputs, snapshot_every=60)
        self.assertEqual(code, 0, stderr)
        pos = recs[-2]["player"]["pos"]
        self.assertAlmostEqual(pos[0], 7.0, places=2)
        self.assertAlmostEqual(pos[2], 0.0, places=2)

    def test_determinism_identical_runs(self) -> None:
        inputs = {
            "frames": [
                {"tick": 0, "move": [0.7, 0.7], "cam_yaw_deg": 15},
                {"tick": 45, "jump": True},
                {"tick": 46, "jump": False},
                {"tick": 90, "move": [-1, 0], "cam_yaw_deg": 45},
            ]
        }
        c1, r1, _ = run_cli(seed=1337, ticks=180, inputs=inputs, snapshot_every=30)
        c2, r2, _ = run_cli(seed=1337, ticks=180, inputs=inputs, snapshot_every=30)
        self.assertEqual(c1, 0)
        self.assertEqual(c2, 0)
        self.assertEqual(r1, r2)

    def test_invalid_inputs_exit_code_2(self) -> None:
        # Non-strictly increasing ticks
        bad_inputs = {
            "frames": [
                {"tick": 10, "move": [0, 1]},
                {"tick": 10, "move": [0, 0]},
            ]
        }
        code, _, stderr = run_cli(ticks=20, inputs=bad_inputs)
        self.assertEqual(code, 2)
        self.assertTrue(len(stderr.strip()) > 0)

        # Malformed JSON
        code2, _, stderr2 = run_cli(ticks=20, raw_inputs_text="{not valid json")
        self.assertEqual(code2, 2)
        self.assertTrue(len(stderr2.strip()) > 0)


if __name__ == "__main__":
    unittest.main()
