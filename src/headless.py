"""Headless CLI runner implementing Test Contract v1.1 for Dao Den Long."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from src.engine import (
    ContractValidationError,
    GameEngine,
    InputState,
    load_contract,
    validate_inputs_data,
    validate_scenario_data,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dao Den Long Headless Runner (Contract v1.1)")
    parser.add_argument("--seed", type=int, required=True, help="Deterministic RNG seed")
    parser.add_argument("--night", type=int, required=True, help="Night number (1, 2, or 3)")
    parser.add_argument("--scenario", type=str, default=None, help="Optional scenario JSON file")
    parser.add_argument("--inputs", type=str, default=None, help="Optional inputs JSON file")
    parser.add_argument("--ticks", type=int, required=True, help="Maximum simulation ticks to run")
    parser.add_argument("--out", type=str, required=True, help="Output JSONL file path")
    parser.add_argument("--snapshot-every", type=int, default=10, help="Snapshot interval in ticks (default: 10)")
    return parser.parse_args(argv)


def _load_json_file(path_str: str, label: str) -> Any:
    p = Path(path_str)
    if not p.is_file():
        raise ContractValidationError(f"{label} file not found: {path_str}")
    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        raise ContractValidationError(f"Invalid JSON in {label} ({path_str}): {exc}") from exc


def run_headless(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2

    if args.ticks < 0:
        print("Error: --ticks must be >= 0", file=sys.stderr)
        return 2
    if args.snapshot_every <= 0:
        print("Error: --snapshot-every must be > 0", file=sys.stderr)
        return 2

    try:
        scenario_data: dict[str, Any] | None = None
        if args.scenario is not None:
            raw_scenario = _load_json_file(args.scenario, "scenario")
            scenario_data = validate_scenario_data(raw_scenario)

        frames: list[dict[str, Any]] = []
        if args.inputs is not None:
            raw_inputs = _load_json_file(args.inputs, "inputs")
            frames = validate_inputs_data(raw_inputs)

        contract = load_contract()
        engine = GameEngine(
            seed=args.seed,
            night=args.night,
            tuning=contract["tuning"],
            scenario=scenario_data,
        )
    except ContractValidationError as exc:
        print(f"Contract validation error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # pragma: no cover
        print(f"Unexpected initialization error: {exc}", file=sys.stderr)
        return 1

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    cur_input = InputState()
    frame_idx = 0
    num_frames = len(frames)

    with out_path.open("w", encoding="utf-8", newline="\n") as out_f:
        def write_line(obj: dict[str, Any]) -> None:
            out_f.write(json.dumps(obj, separators=(",", ":")) + "\n")

        # Tick 0 snapshot: after scenario setup, before applying any input
        write_line(engine.snapshot())

        for k in range(args.ticks):
            if engine.state in ("won", "lost"):
                break

            if frame_idx < num_frames and frames[frame_idx]["tick"] == k:
                fr = frames[frame_idx]
                frame_idx += 1
                if "move" in fr:
                    cur_input.move_x = float(fr["move"][0])
                    cur_input.move_z = float(fr["move"][1])
                if "cam_yaw_deg" in fr:
                    cur_input.cam_yaw_deg = float(fr["cam_yaw_deg"])
                if "jump" in fr:
                    cur_input.jump = bool(fr["jump"])
                if "interact" in fr:
                    cur_input.interact = bool(fr["interact"])
                if "pulse" in fr:
                    cur_input.pulse = bool(fr["pulse"])
                if "dash" in fr:
                    cur_input.dash = bool(fr["dash"])
                if "pause" in fr:
                    cur_input.pause = bool(fr["pause"])

            events = engine.step(cur_input)
            for ev in events:
                write_line(ev)

            if engine.tick % args.snapshot_every == 0:
                write_line(engine.snapshot())

            if engine.state in ("won", "lost"):
                break

        write_line(engine.end_record())

    return 0


def main() -> None:
    sys.exit(run_headless())


if __name__ == "__main__":
    main()
