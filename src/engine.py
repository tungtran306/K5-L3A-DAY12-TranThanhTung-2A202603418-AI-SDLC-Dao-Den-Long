"""Deterministic 60-tick simulation engine for Dao Den Long (Test Contract v1.0)."""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

TICK_RATE = 60
DT = 1.0 / TICK_RATE
ISLAND_RADIUS = 45.0
LANTERN_RING_RADIUS = 26.0
JUMP_VELOCITY = 7.5
GRAVITY = 20.0
INITIAL_MOTE_COUNT = 24
MOTE_RESPAWN_INTERVAL_TICKS = 300
MOTE_MAX_ACTIVE = 24
INITIAL_SHADE_COUNT = 2
SHADE_SPAWN_INTERVAL_TICKS = 1800
SHADE_MAX_ACTIVE = 5


class ContractValidationError(ValueError):
    """Raised when scenario or inputs JSON violates Test Contract v1.0."""


def r3(val: float) -> float:
    """Round coordinate/time to 3 decimal places, avoiding -0.0."""
    out = round(float(val), 3)
    return 0.0 if out == 0.0 else out


def dist_xz(a: list[float], b: list[float]) -> float:
    return math.hypot(a[0] - b[0], a[2] - b[2])


def clamp_to_island(pos: list[float], radius: float = ISLAND_RADIUS) -> None:
    d = math.hypot(pos[0], pos[2])
    if d > radius and d > 0.0:
        scale = radius / d
        pos[0] *= scale
        pos[2] *= scale


def load_contract(contract_path: Path | None = None) -> dict[str, Any]:
    if contract_path is None:
        contract_path = Path(__file__).resolve().parent.parent / "game.contract.json"
    with contract_path.open("r", encoding="utf-8") as f:
        return json.load(f)


@dataclass
class Lantern:
    id: str
    pos: list[float]
    lit: bool = False
    deposited: int = 0

    def to_snapshot(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "pos": [r3(self.pos[0]), r3(self.pos[1]), r3(self.pos[2])],
            "lit": self.lit,
            "deposited": self.deposited,
        }


@dataclass
class Mote:
    id: str
    pos: list[float]

    def to_snapshot(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "pos": [r3(self.pos[0]), r3(self.pos[1]), r3(self.pos[2])],
        }


@dataclass
class Shade:
    id: str
    pos: list[float]
    state: str = "chase"
    stun_timer: float = 0.0

    def to_snapshot(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "pos": [r3(self.pos[0]), r3(self.pos[1]), r3(self.pos[2])],
            "state": self.state,
        }


@dataclass
class InputState:
    move_x: float = 0.0
    move_z: float = 0.0
    cam_yaw_deg: float = 0.0
    jump: bool = False
    interact: bool = False
    pulse: bool = False
    dash: bool = False

    def copy(self) -> "InputState":
        return InputState(
            move_x=self.move_x,
            move_z=self.move_z,
            cam_yaw_deg=self.cam_yaw_deg,
            jump=self.jump,
            interact=self.interact,
            pulse=self.pulse,
            dash=self.dash,
        )


def validate_inputs_data(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, dict) or "frames" not in data or not isinstance(data["frames"], list):
        raise ContractValidationError("Inputs JSON must be an object with a 'frames' list.")
    frames: list[dict[str, Any]] = []
    prev_tick = -1
    for i, frame in enumerate(data["frames"]):
        if not isinstance(frame, dict):
            raise ContractValidationError(f"Frame {i} must be an object.")
        if "tick" not in frame or not isinstance(frame["tick"], int) or isinstance(frame["tick"], bool):
            raise ContractValidationError(f"Frame {i} missing integer 'tick'.")
        tick = frame["tick"]
        if tick < 0 or tick <= prev_tick:
            raise ContractValidationError(f"Frame ticks must be strictly increasing >= 0 (got {tick} after {prev_tick}).")
        prev_tick = tick

        if "move" in frame:
            mv = frame["move"]
            if (
                not isinstance(mv, list)
                or len(mv) != 2
                or not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in mv)
            ):
                raise ContractValidationError(f"Frame {i} 'move' must be [x, z] numbers.")
            if not (-1.0 <= float(mv[0]) <= 1.0 and -1.0 <= float(mv[1]) <= 1.0):
                raise ContractValidationError(f"Frame {i} 'move' components must be in [-1, 1].")

        if "cam_yaw_deg" in frame:
            yaw = frame["cam_yaw_deg"]
            if not isinstance(yaw, (int, float)) or isinstance(yaw, bool):
                raise ContractValidationError(f"Frame {i} 'cam_yaw_deg' must be a number.")

        for btn in ("jump", "interact", "pulse", "dash"):
            if btn in frame and not isinstance(frame[btn], bool):
                raise ContractValidationError(f"Frame {i} '{btn}' must be a boolean.")

        frames.append(frame)
    return frames


def _validate_pos3(val: Any, label: str) -> list[float]:
    if (
        not isinstance(val, list)
        or len(val) != 3
        or not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in val)
    ):
        raise ContractValidationError(f"{label} must be a 3-number array [x, y, z].")
    return [float(val[0]), float(val[1]), float(val[2])]


def validate_scenario_data(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ContractValidationError("Scenario JSON must be an object.")
    if "player" in data:
        p = data["player"]
        if not isinstance(p, dict):
            raise ContractValidationError("scenario.player must be an object.")
        if "pos" in p:
            _validate_pos3(p["pos"], "scenario.player.pos")
        for k in ("carried", "flames"):
            if k in p and (not isinstance(p[k], int) or isinstance(p[k], bool) or p[k] < 0):
                raise ContractValidationError(f"scenario.player.{k} must be a non-negative integer.")
    for bk in ("random_motes", "random_shades"):
        if bk in data and not isinstance(data[bk], bool):
            raise ContractValidationError(f"scenario.{bk} must be a boolean.")
    if "time_left_s" in data:
        t = data["time_left_s"]
        if not isinstance(t, (int, float)) or isinstance(t, bool) or t < 0:
            raise ContractValidationError("scenario.time_left_s must be a non-negative number.")
    if "motes" in data:
        if not isinstance(data["motes"], list):
            raise ContractValidationError("scenario.motes must be a list.")
        for i, m in enumerate(data["motes"]):
            if isinstance(m, list):
                _validate_pos3(m, f"scenario.motes[{i}]")
            elif isinstance(m, dict) and "pos" in m:
                _validate_pos3(m["pos"], f"scenario.motes[{i}].pos")
            else:
                raise ContractValidationError(f"scenario.motes[{i}] must be [x,y,z] or {{pos:[x,y,z]}}.")
    if "shades" in data:
        if not isinstance(data["shades"], list):
            raise ContractValidationError("scenario.shades must be a list.")
        for i, s in enumerate(data["shades"]):
            if not isinstance(s, dict) or "pos" not in s:
                raise ContractValidationError(f"scenario.shades[{i}] must be an object with 'pos'.")
            _validate_pos3(s["pos"], f"scenario.shades[{i}].pos")
    if "lanterns" in data:
        if not isinstance(data["lanterns"], list):
            raise ContractValidationError("scenario.lanterns must be a list.")
        for i, lt in enumerate(data["lanterns"]):
            if not isinstance(lt, dict) or "id" not in lt or not isinstance(lt["id"], str):
                raise ContractValidationError(f"scenario.lanterns[{i}] must be an object with string 'id'.")
            if "pos" in lt:
                _validate_pos3(lt["pos"], f"scenario.lanterns[{i}].pos")
            if "deposited" in lt and (not isinstance(lt["deposited"], int) or isinstance(lt["deposited"], bool) or lt["deposited"] < 0):
                raise ContractValidationError(f"scenario.lanterns[{i}].deposited must be a non-negative integer.")
            if "lit" in lt and not isinstance(lt["lit"], bool):
                raise ContractValidationError(f"scenario.lanterns[{i}].lit must be a boolean.")
    return data


class GameEngine:
    """Deterministic 60-Hz simulation for Night 1 (Dao Ben)."""

    def __init__(
        self,
        seed: int = 1,
        night: int = 1,
        tuning: dict[str, Any] | None = None,
        scenario: dict[str, Any] | None = None,
    ) -> None:
        if night != 1:
            raise ContractValidationError(f"Only --night 1 is supported in Phase 1 (got {night}).")
        self.seed = int(seed)
        self.night = int(night)
        self.rng = random.Random(self.seed)

        if tuning is None:
            tuning = load_contract()["tuning"]
        self.tuning = tuning
        self.score_cfg = tuning["score"]

        # Core state
        self.tick: int = 0
        self.sim_tick: int = 0
        self.state: str = "playing"  # playing | won | lost
        self.score: int = 0
        self.initial_time_left_s: float = float(tuning["night1_duration_s"])
        self.time_left_s: float = self.initial_time_left_s

        # Player state
        self.player_pos: list[float] = [0.0, 0.0, 0.0]
        self.player_vy: float = 0.0
        self.flames: int = int(tuning["flames"])
        self.carried: int = 0
        self.invuln_timer: float = 0.0
        self.pulse_cooldown_timer: float = 0.0

        # Spawning flags & counters
        self.random_motes: bool = True
        self.random_shades: bool = True
        self._mote_seq: int = 0
        self._shade_seq: int = 0

        # Entities
        self.lanterns: list[Lantern] = self._create_default_lanterns()
        self.motes: list[Mote] = []
        self.shades: list[Shade] = []

        # Input edge-tracking
        self._prev_input = InputState()

        # Apply scenario (or default spawns) without emitting events or score
        self._setup_world(scenario)

    def _create_default_lanterns(self) -> list[Lantern]:
        count = int(self.tuning["lantern_count_night1"])
        lanterns: list[Lantern] = []
        for i in range(count):
            angle = (2.0 * math.pi * i) / count
            x = r3(LANTERN_RING_RADIUS * math.sin(angle))
            z = r3(LANTERN_RING_RADIUS * math.cos(angle))
            lanterns.append(Lantern(id=f"L{i + 1}", pos=[x, 0.0, z]))
        return lanterns

    def _next_mote_id(self) -> str:
        self._mote_seq += 1
        return f"M{self._mote_seq}"

    def _next_shade_id(self) -> str:
        self._shade_seq += 1
        return f"S{self._shade_seq}"

    def _spawn_random_mote(self) -> Mote:
        for _ in range(32):
            angle = self.rng.uniform(0.0, 2.0 * math.pi)
            radius = math.sqrt(self.rng.uniform(0.04, 0.85)) * ISLAND_RADIUS
            pos = [r3(radius * math.sin(angle)), 0.0, r3(radius * math.cos(angle))]
            if dist_xz(pos, self.player_pos) > 3.0:
                return Mote(id=self._next_mote_id(), pos=pos)
        return Mote(id=self._next_mote_id(), pos=[5.0, 0.0, 5.0])

    def _spawn_random_shade(self) -> Shade:
        safe_r = float(self.tuning["safe_radius"])
        for _ in range(32):
            angle = self.rng.uniform(0.0, 2.0 * math.pi)
            radius = self.rng.uniform(32.0, ISLAND_RADIUS - 3.0)
            pos = [r3(radius * math.sin(angle)), 0.0, r3(radius * math.cos(angle))]
            in_safe = any(lt.lit and dist_xz(pos, lt.pos) < safe_r for lt in self.lanterns)
            if not in_safe and dist_xz(pos, self.player_pos) > 12.0:
                return Shade(id=self._next_shade_id(), pos=pos, state="chase")
        return Shade(id=self._next_shade_id(), pos=[36.0, 0.0, 0.0], state="chase")

    def _setup_world(self, scenario: dict[str, Any] | None) -> None:
        if scenario is not None:
            validate_scenario_data(scenario)
            if "random_motes" in scenario:
                self.random_motes = scenario["random_motes"]
            if "random_shades" in scenario:
                self.random_shades = scenario["random_shades"]
            if "time_left_s" in scenario:
                self.initial_time_left_s = float(scenario["time_left_s"])
                self.time_left_s = self.initial_time_left_s
            if "player" in scenario:
                p = scenario["player"]
                if "pos" in p:
                    self.player_pos = [float(p["pos"][0]), float(p["pos"][1]), float(p["pos"][2])]
                if "carried" in p:
                    self.carried = int(p["carried"])
                if "flames" in p:
                    self.flames = int(p["flames"])
            if "lanterns" in scenario:
                by_id = {lt.id: lt for lt in self.lanterns}
                for item in scenario["lanterns"]:
                    lt = by_id.get(item["id"])
                    if lt is None:
                        continue
                    if "pos" in item:
                        lt.pos = [float(item["pos"][0]), float(item["pos"][1]), float(item["pos"][2])]
                    if "deposited" in item:
                        lt.deposited = int(item["deposited"])
                    if "lit" in item:
                        lt.lit = bool(item["lit"])

        if scenario is not None and "motes" in scenario:
            for item in scenario["motes"]:
                if isinstance(item, list):
                    mid = self._next_mote_id()
                    pos = [float(item[0]), 0.0, float(item[2])]
                else:
                    mid = str(item.get("id") or self._next_mote_id())
                    pos = [float(item["pos"][0]), 0.0, float(item["pos"][2])]
                self.motes.append(Mote(id=mid, pos=pos))
        elif self.random_motes:
            for _ in range(INITIAL_MOTE_COUNT):
                self.motes.append(self._spawn_random_mote())

        if scenario is not None and "shades" in scenario:
            for item in scenario["shades"]:
                sid = str(item.get("id") or self._next_shade_id())
                pos = [float(item["pos"][0]), float(item["pos"][1]), float(item["pos"][2])]
                st = str(item.get("state", "chase"))
                self.shades.append(Shade(id=sid, pos=pos, state=st))
        elif self.random_shades:
            for _ in range(INITIAL_SHADE_COUNT):
                self.shades.append(self._spawn_random_shade())

    def snapshot(self) -> dict[str, Any]:
        return {
            "type": "snapshot",
            "tick": self.tick,
            "sim_tick": self.sim_tick,
            "state": self.state,
            "time_left_s": r3(self.time_left_s),
            "score": self.score,
            "player": {
                "pos": [r3(self.player_pos[0]), r3(self.player_pos[1]), r3(self.player_pos[2])],
                "flames": self.flames,
                "carried": self.carried,
            },
            "lanterns": [lt.to_snapshot() for lt in self.lanterns],
            "shades": [s.to_snapshot() for s in self.shades],
            "motes_active": len(self.motes),
            "motes": [m.to_snapshot() for m in self.motes],
        }

    def end_record(self) -> dict[str, Any]:
        return {
            "type": "end",
            "ticks": self.tick,
            "state": self.state,
            "score": self.score,
        }

    def step(self, inp: InputState) -> list[dict[str, Any]]:
        """Advance simulation by 1 tick (1/60 s) using input of tick k -> produces tick k+1."""
        if self.state != "playing":
            return []

        self.tick += 1
        self.sim_tick += 1
        cur_tick = self.tick
        events: list[dict[str, Any]] = []

        def emit(name: str, data: dict[str, Any]) -> None:
            events.append({"type": "event", "tick": cur_tick, "name": name, "data": data})

        # Rising-edge buttons
        jump_pressed = inp.jump and not self._prev_input.jump
        interact_pressed = inp.interact and not self._prev_input.interact
        pulse_pressed = inp.pulse and not self._prev_input.pulse
        self._prev_input = inp.copy()

        # Timers
        if self.invuln_timer > 0.0:
            self.invuln_timer = max(0.0, self.invuln_timer - DT)
        if self.pulse_cooldown_timer > 0.0:
            self.pulse_cooldown_timer = max(0.0, self.pulse_cooldown_timer - DT)

        # 1. Player movement on XZ plane
        mx, mz = float(inp.move_x), float(inp.move_z)
        mag = math.hypot(mx, mz)
        if mag > 1.0:
            mx /= mag
            mz /= mag
        theta = math.radians(float(inp.cam_yaw_deg))
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)
        wx = mx * cos_t + mz * sin_t
        wz = -mx * sin_t + mz * cos_t
        speed = float(self.tuning["player_speed"])
        self.player_pos[0] += wx * speed * DT
        self.player_pos[2] += wz * speed * DT
        clamp_to_island(self.player_pos)

        # Vertical jump physics
        if jump_pressed and self.player_pos[1] <= 0.0:
            self.player_vy = JUMP_VELOCITY
        if self.player_pos[1] > 0.0 or self.player_vy > 0.0:
            self.player_pos[1] += self.player_vy * DT
            self.player_vy -= GRAVITY * DT
            if self.player_pos[1] <= 0.0:
                self.player_pos[1] = 0.0
                self.player_vy = 0.0

        # 2. Pickup motes
        pickup_r = float(self.tuning["pickup_radius"])
        carry_cap = int(self.tuning["carry_capacity"])
        remaining_motes: list[Mote] = []
        for mote in self.motes:
            if self.carried < carry_cap and dist_xz(self.player_pos, mote.pos) <= pickup_r:
                self.carried += 1
                self.score += int(self.score_cfg["per_mote"])
                emit("mote_picked", {"carried": self.carried})
            else:
                remaining_motes.append(mote)
        self.motes = remaining_motes

        # 3. Deposit into nearest unlit lantern in interact_radius
        if interact_pressed and self.carried > 0:
            interact_r = float(self.tuning["interact_radius"])
            lantern_cost = int(self.tuning["lantern_cost"])
            candidates = [
                (dist_xz(self.player_pos, lt.pos), lt)
                for lt in self.lanterns
                if not lt.lit and dist_xz(self.player_pos, lt.pos) <= interact_r
            ]
            if candidates:
                candidates.sort(key=lambda pair: (pair[0], pair[1].id))
                target = candidates[0][1]
                needed = max(0, lantern_cost - target.deposited)
                amount = min(self.carried, needed)
                if amount > 0:
                    self.carried -= amount
                    target.deposited += amount
                    emit(
                        "deposit",
                        {
                            "lantern_id": target.id,
                            "amount": amount,
                            "deposited": target.deposited,
                        },
                    )
                    if target.deposited >= lantern_cost and not target.lit:
                        target.lit = True
                        self.score += int(self.score_cfg["per_lantern"])
                        emit("lantern_lit", {"lantern_id": target.id})

        # 4. Pulse (stun & push shades)
        if pulse_pressed:
            pulse_cost = int(self.tuning["pulse_cost"])
            if self.pulse_cooldown_timer <= 0.0 and self.carried >= pulse_cost:
                self.carried -= pulse_cost
                self.pulse_cooldown_timer = float(self.tuning["pulse_cooldown_s"])
                pulse_r = float(self.tuning["pulse_radius"])
                stun_s = float(self.tuning["pulse_stun_s"])
                push_m = float(self.tuning["pulse_push_m"])
                stunned_ids: list[str] = []
                for shade in self.shades:
                    d = dist_xz(self.player_pos, shade.pos)
                    if d <= pulse_r:
                        shade.state = "stunned"
                        shade.stun_timer = stun_s
                        dx = shade.pos[0] - self.player_pos[0]
                        dz = shade.pos[2] - self.player_pos[2]
                        if d > 1e-6:
                            nx, nz = dx / d, dz / d
                        else:
                            nx, nz = 1.0, 0.0
                        shade.pos[0] += nx * push_m
                        shade.pos[2] += nz * push_m
                        clamp_to_island(shade.pos)
                        stunned_ids.append(shade.id)
                        self.score += int(self.score_cfg["per_stun"])
                emit("pulse", {"stunned_ids": stunned_ids})

        # 5. Update shades (stun countdown, chase player, respect lit lantern safe_radius)
        shade_speed = float(self.tuning["shade_speed"])
        safe_r = float(self.tuning["safe_radius"])
        lit_lanterns = [lt for lt in self.lanterns if lt.lit]

        for shade in self.shades:
            if shade.state == "stunned":
                shade.stun_timer = max(0.0, shade.stun_timer - DT)
                if shade.stun_timer <= 0.0:
                    shade.state = "chase"
            else:
                dx = self.player_pos[0] - shade.pos[0]
                dz = self.player_pos[2] - shade.pos[2]
                d = math.hypot(dx, dz)
                if d > 1e-6:
                    step_d = min(d, shade_speed * DT)
                    shade.pos[0] += (dx / d) * step_d
                    shade.pos[2] += (dz / d) * step_d

            # Enforce safe_radius around all lit lanterns
            for lt in lit_lanterns:
                lx = shade.pos[0] - lt.pos[0]
                lz = shade.pos[2] - lt.pos[2]
                ld = math.hypot(lx, lz)
                if ld < safe_r:
                    if ld > 1e-6:
                        nx, nz = lx / ld, lz / ld
                    else:
                        nx, nz = 1.0, 0.0
                    shade.pos[0] = lt.pos[0] + nx * (safe_r + 1e-3)
                    shade.pos[2] = lt.pos[2] + nz * (safe_r + 1e-3)
            clamp_to_island(shade.pos)

        # 6. Check shade hits on player
        hit_r = float(self.tuning["shade_hit_radius"])
        if self.invuln_timer <= 0.0:
            for shade in self.shades:
                if shade.state != "stunned" and dist_xz(self.player_pos, shade.pos) <= hit_r:
                    self.flames = max(0, self.flames - 1)
                    dropped = math.floor(self.carried * float(self.tuning["hit_drop_ratio"]))
                    self.carried -= dropped
                    self.invuln_timer = float(self.tuning["invuln_s"])
                    emit(
                        "player_hit",
                        {
                            "by": "shade",
                            "flames": self.flames,
                            "dropped": dropped,
                        },
                    )
                    break

        # 7. Periodic random spawns (only if enabled & still playing)
        if self.random_motes and cur_tick % MOTE_RESPAWN_INTERVAL_TICKS == 0 and len(self.motes) < MOTE_MAX_ACTIVE:
            self.motes.append(self._spawn_random_mote())

        if self.random_shades and cur_tick % SHADE_SPAWN_INTERVAL_TICKS == 0 and len(self.shades) < SHADE_MAX_ACTIVE:
            new_shade = self._spawn_random_shade()
            self.shades.append(new_shade)
            emit("shade_spawned", {"id": new_shade.id})

        # 8. Update night clock and evaluate win/lose conditions
        self.time_left_s = max(0.0, self.initial_time_left_s - (cur_tick / TICK_RATE))

        if all(lt.lit for lt in self.lanterns):
            self.score += math.floor(self.time_left_s) * int(self.score_cfg["per_second_left"])
            self.score += self.flames * int(self.score_cfg["per_flame_left"])
            self.state = "won"
            emit("game_over", {"result": "won", "reason": "all_lit"})
        elif self.flames <= 0:
            self.state = "lost"
            emit("game_over", {"result": "lost", "reason": "no_flames"})
        elif self.time_left_s <= 0.0:
            self.state = "lost"
            emit("game_over", {"result": "lost", "reason": "dawn"})

        return events
