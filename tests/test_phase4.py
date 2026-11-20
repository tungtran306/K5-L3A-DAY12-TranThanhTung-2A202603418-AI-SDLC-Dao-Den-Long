"""Phase 4 (Contract v1.3) tests: leaderboard persistence/export, soak test, and contract fields."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.engine import load_contract
from src.leaderboard import add_entry, export_leaderboard, load_entries

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestPhase4ContractV13(unittest.TestCase):
    def test_contract_v13_fields(self) -> None:
        c = load_contract(REPO_ROOT / "game.contract.json")
        self.assertEqual(c["contract_version"], "1.3")
        self.assertIn("bench_cmd", c)
        self.assertIn("soak_cmd", c)
        self.assertTrue(len(c["bench_cmd"]) > 0)
        self.assertTrue(len(c["soak_cmd"]) > 0)

    def test_leaderboard_top10_sort_tiebreak_and_export_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lb_path = Path(tmp) / "lb.json"
            out_path = Path(tmp) / "export.json"

            # Invalid names rejected
            with self.assertRaises(ValueError):
                add_entry(name="ab", score=100, nights_won=1, path=lb_path)
            with self.assertRaises(ValueError):
                add_entry(name="bad name!", score=100, nights_won=1, path=lb_path)

            # Add 12 entries including tie score with different timestamps
            add_entry(name="LateTie", score=500, nights_won=3, achieved_at="2026-11-20T16:10:00+07:00", path=lb_path)
            add_entry(name="EarlyTie", score=500, nights_won=3, achieved_at="2026-11-20T16:05:00+07:00", path=lb_path)
            add_entry(name="Mây_Việt", score=900, nights_won=3, achieved_at="2026-11-20T16:12:00+07:00", path=lb_path)
            for i in range(9):
                add_entry(name=f"Player_{i}", score=100 + i * 20, nights_won=1, achieved_at=f"2026-11-20T16:0{i}:00+07:00", path=lb_path)

            entries = load_entries(lb_path)
            self.assertEqual(len(entries), 10)
            self.assertEqual(entries[0]["name"], "Mây_Việt")
            self.assertEqual(entries[1]["name"], "EarlyTie")
            self.assertEqual(entries[2]["name"], "LateTie")

            export_leaderboard(out_path, path=lb_path)
            exported = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertIn("entries", exported)
            self.assertEqual(len(exported["entries"]), 10)

            # Test --export-leaderboard CLI via src.server
            cli_out = Path(tmp) / "cli_lb.json"
            proc = subprocess.run(
                [sys.executable, "-m", "src.server", "--export-leaderboard", str(cli_out)],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("entries", json.loads(cli_out.read_text(encoding="utf-8")))

    def test_soak_runner_3_nights_no_crash_and_stable_mem(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "soak.json"
            proc = subprocess.run(
                [sys.executable, "-m", "src.soak", "--seed", "7", "--nights", "3", "--out", str(out_path)],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            data = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(data["nights"], 3)
            self.assertEqual(data["crashes"], 0)
            self.assertEqual(len(data["results"]), 3)
            self.assertLessEqual(data["mem_end_mb"], data["mem_start_mb"] * 1.2)


if __name__ == "__main__":
    unittest.main()
