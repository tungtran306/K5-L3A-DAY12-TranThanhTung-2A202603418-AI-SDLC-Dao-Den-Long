"""Deterministic 60-tick simulation engine for Dao Den Long (Test Contract v1.1)."""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.maps import NightConfig, get_night_config, ground_height, is_blocked_by_wall_or_tower

TICK_RATE = 60
DT = 1.0 / TICK_RATE
JUMP_VELOCITY = 7.0
GRAVITY = 20.0
CHARM_SPEED = 7.2
CHARM_DURATION_TICKS = 600
CHARM_RESPAWN_TICKS = 2700
DROPPED_MOTE_TTL_TICKS = 480
RESPAWN_WAIT_TICKS = 60
SAFE_PUSHOUT_MAX_TICKS = 30
PULSE_PUSH_TICKS = 15
SHADE_RECOIL_TICKS = 60
SHADE_RECOIL_DIST = 2.0
SHADE_DETECT_R = 12.0
SHADE_LOSE_R = 18.0
DRIFTER_IDLE_SPEED = 2.0
DRIFTER_FAST_SPEED = 7.0
DRIFTER_DETECT_R = 15.0
DRIFTER_DETECT_MOTES = 5
DRIFTER_STEAL_R = 1.2
DRIFTER_FLEE_TICKS = 240
DRIFTER_DROP_DESPAWN_TICKS = 120
DRIFTER_SPAWN_INTERVAL = 1200
DRIFTER_MAX = 2
WIND_CYCLE_TICKS = 1800
WIND_ACTIVE_TICKS = 300
WIND_SPEED = 2.0
INITIAL_MOTE_COUNT = 20
MOTE_CAP = 30
MOTE_SPAWN_INTERVAL = 240


class ContractValidationError(ValueError):
    """Raised when scenario or inputs JSON violates Test Contract v1.1."""


def r3(val: float) -> float:
    out = round(float(val), 3)
    return 0.0 if out == 0.0 else out


def dist_xz(a: list[float], b: list[float]) -> float:
    return math.hypot(a[0] - b[0], a[2] - b[2])


def dist_3d(a: list[float], b: list[float]) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


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
    kind: str = "random"  # random | dropped
    ttl_ticks: int | None = None
    spawn_tick: int = -1

    def to_snapshot(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "pos": [r3(self.pos[0]), r3(self.pos[1]), r3(self.pos[2])],
            "kind": self.kind,
            "ttl_s": r3(self.ttl_ticks / TICK_RATE) if self.ttl_ticks is not None else None,
        }


@dataclass
class Shade:
    id: str
    pos: list[float]
    state: str = "wander"  # spawning | wander | chase | recoil | stunned
    state_ticks_left: int = 0
    push_ticks_left: int = 0
    push_vx: float = 0.0
    push_vz: float = 0.0
    recoil_vx: float = 0.0
    recoil_vz: float = 0.0
    safe_push_ticks: int = 0
    wander_dir_x: float = 1.0
    wander_dir_z: float = 0.0
    wander_timer: int = 0
    spawn_tick: int = -1

    def to_snapshot(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "pos": [r3(self.pos[0]), r3(self.pos[1]), r3(self.pos[2])],
            "state": self.state,
        }


@dataclass
class Drifter:
    id: str
    pos: list[float]
    state: str = "idle"  # idle | chase | flee | removed
    stolen: int = 0
    flee_ticks_left: int = 0
    has_stolen: bool = False
    idle_angle: float = 0.0
    spawn_tick: int = -1

    def to_snapshot(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "pos": [r3(self.pos[0]), r3(self.pos[1]), r3(self.pos[2])],
            "state": self.state,
            "stolen": self.stolen,
        }


@dataclass
class Charm:
    id: str
    pos: list[float]
    available: bool = True
    respawn_ticks: int = 0

    def to_snapshot(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "available": self.available,
            "respawn_s": r3(self.respawn_ticks / TICK_RATE),
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
    pause: bool = False

    def copy(self) -> "InputState":
        return InputState(
            move_x=self.move_x,
            move_z=self.move_z,
            cam_yaw_deg=self.cam_yaw_deg,
            jump=self.jump,
            interact=self.interact,
            pulse=self.pulse,
            dash=self.dash,
            pause=self.pause,
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

        for btn in ("jump", "interact", "pulse", "dash", "pause"):
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
        for k in ("carried", "flames", "invuln_ticks", "dash_cd_ticks", "pulse_cd_ticks", "charm_ticks"):
            if k in p and (not isinstance(p[k], int) or isinstance(p[k], bool) or p[k] < 0):
                raise ContractValidationError(f"scenario.player.{k} must be a non-negative integer.")
    for bk in ("random_motes", "random_shades", "random_drifters", "wind_enabled"):
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
    if "drifters" in data and not isinstance(data["drifters"], list):
        raise ContractValidationError("scenario.drifters must be a list.")
    if "charms" in data and not isinstance(data["charms"], list):
        raise ContractValidationError("scenario.charms must be a list.")
    return data


class GameEngine:
    """Deterministic 60-Hz simulation for Nights 1, 2, 3 (Test Contract v1.1)."""

    def __init__(
        self,
        seed: int = 1,
        night: int = 1,
        tuning: dict[str, Any] | None = None,
        scenario: dict[str, Any] | None = None,
    ) -> None:
        if night not in (1, 2, 3):
            raise ContractValidationError(f"--night must be 1, 2, or 3 (got {night}).")
        self.seed = int(seed)
        self.night = int(night)
        self.rng = random.Random(self.seed)
        self.map_cfg: NightConfig = get_night_config(self.night)

        if tuning is None:
            tuning = load_contract()["tuning"]
        self.tuning = tuning
        self.score_cfg = tuning["score"]

        # Core state
        self.tick: int = 0
        self.sim_tick: int = 0
        self.state: str = "playing"  # playing | paused | won | lost
        self.score: int = 0
        self.initial_time_left_s: float = self.map_cfg.duration_s
        self.time_left_s: float = self.initial_time_left_s

        # Player state
        self.player_pos: list[float] = [0.0, 0.0, 0.0]
        self.player_vel: list[float] = [0.0, 0.0, 0.0]
        self.facing_x: float = 0.0
        self.facing_z: float = 1.0
        self.grounded: bool = True
        self.flames: int = int(tuning["flames"])
        self.carried: int = 0
        self.invuln_ticks: int = 0
        self.dash_cd_ticks: int = 0
        self.dash_ticks_left: int = 0
        self.dash_dir_x: float = 0.0
        self.dash_dir_z: float = 1.0
        self.pulse_cd_ticks: int = 0
        self.charm_ticks: int = 0
        self.respawn_wait_ticks: int = 0
        self.pad_launched: bool = False
        self.pad_vx: float = 0.0
        self.pad_vz: float = 0.0

        # Wind (Night 3)
        self.wind_enabled: bool = self.map_cfg.has_wind
        self.wind_active: bool = False
        self.wind_dir_deg: float = 0.0
        self.wind_ticks_left: int = 0

        # Spawning flags & counters
        self.random_motes: bool = True
        self.random_shades: bool = True
        self.random_drifters: bool = self.map_cfg.has_drifters
        self._mote_seq: int = 0
        self._shade_seq: int = 0
        self._drifter_seq: int = 0

        # Entities
        self.lanterns: list[Lantern] = [
            Lantern(id=lid, pos=[p[0], p[1], p[2]]) for lid, p in self.map_cfg.lanterns
        ]
        self.motes: list[Mote] = []
        self.shades: list[Shade] = []
        self.drifters: list[Drifter] = []
        self.charms: list[Charm] = [
            Charm(id=cid, pos=[p[0], p[1], p[2]]) for cid, p in self.map_cfg.charms
        ]

        self._prev_input = InputState()
        self._setup_world(scenario)

    def _next_mote_id(self) -> str:
        self._mote_seq += 1
        return f"M{self._mote_seq}"

    def _next_shade_id(self) -> str:
        self._shade_seq += 1
        return f"S{self._shade_seq}"

    def _next_drifter_id(self) -> str:
        self._drifter_seq += 1
        return f"D{self._drifter_seq}"

    def _pick_empty_mote_spawn(self) -> tuple[float, float, float] | None:
        empty = []
        for sp in self.map_cfg.mote_spawns:
            occupied = any(
                dist_xz([sp[0], sp[1], sp[2]], m.pos) < 0.5 and abs(sp[1] - m.pos[1]) < 1.0
                for m in self.motes
            )
            if not occupied:
                empty.append(sp)
        if not empty:
            return None
        return self.rng.choice(empty)

    def _pick_valid_shade_spawn(self) -> tuple[float, float, float] | None:
        safe_r = float(self.tuning["safe_radius"])
        valid = []
        for sp in self.map_cfg.shade_spawns:
            p = [sp[0], sp[1], sp[2]]
            if dist_xz(p, self.player_pos) < 15.0:
                continue
            if any(lt.lit and dist_xz(p, lt.pos) < safe_r for lt in self.lanterns):
                continue
            valid.append(sp)
        if not valid:
            return None
        return self.rng.choice(valid)

    def _setup_world(self, scenario: dict[str, Any] | None) -> None:
        if scenario is not None:
            validate_scenario_data(scenario)
            if "random_motes" in scenario:
                self.random_motes = scenario["random_motes"]
            if "random_shades" in scenario:
                self.random_shades = scenario["random_shades"]
            if "random_drifters" in scenario:
                self.random_drifters = scenario["random_drifters"]
            if "wind_enabled" in scenario:
                self.wind_enabled = scenario["wind_enabled"]
            if "time_left_s" in scenario:
                self.initial_time_left_s = float(scenario["time_left_s"])
                self.time_left_s = self.initial_time_left_s
            if "player" in scenario:
                p = scenario["player"]
                if "pos" in p:
                    self.player_pos = [float(p["pos"][0]), float(p["pos"][1]), float(p["pos"][2])]
                    gh = ground_height(self.night, self.player_pos[0], self.player_pos[2], self.player_pos[1])
                    self.grounded = gh is not None and abs(self.player_pos[1] - gh) <= 0.05
                if "carried" in p:
                    self.carried = int(p["carried"])
                if "flames" in p:
                    self.flames = int(p["flames"])
                if "invuln_ticks" in p:
                    self.invuln_ticks = int(p["invuln_ticks"])
                if "dash_cd_ticks" in p:
                    self.dash_cd_ticks = int(p["dash_cd_ticks"])
                if "pulse_cd_ticks" in p:
                    self.pulse_cd_ticks = int(p["pulse_cd_ticks"])
                if "charm_ticks" in p:
                    self.charm_ticks = int(p["charm_ticks"])
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

        # Motes
        if scenario is not None and "motes" in scenario:
            for item in scenario["motes"]:
                if isinstance(item, list):
                    mid = self._next_mote_id()
                    pos = [float(item[0]), float(item[1]), float(item[2])]
                    kind = "random"
                    ttl_ticks = None
                else:
                    mid = str(item.get("id") or self._next_mote_id())
                    pos = [float(item["pos"][0]), float(item["pos"][1]), float(item["pos"][2])]
                    kind = str(item.get("kind", "random"))
                    ttl_s = item.get("ttl_s")
                    ttl_ticks = int(round(float(ttl_s) * TICK_RATE)) if ttl_s is not None else None
                self.motes.append(Mote(id=mid, pos=pos, kind=kind, ttl_ticks=ttl_ticks, spawn_tick=-1))
        elif self.random_motes:
            pts = list(self.map_cfg.mote_spawns)
            self.rng.shuffle(pts)
            for sp in pts[:INITIAL_MOTE_COUNT]:
                self.motes.append(Mote(id=self._next_mote_id(), pos=[sp[0], sp[1], sp[2]], kind="random", spawn_tick=-1))

        # Shades (if scenario provides shades, use them; otherwise default schedule spawns 2 at tick 300)
        if scenario is not None and "shades" in scenario:
            for item in scenario["shades"]:
                sid = str(item.get("id") or self._next_shade_id())
                pos = [float(item["pos"][0]), float(item["pos"][1]), float(item["pos"][2])]
                st = str(item.get("state", "chase"))
                st_left = int(item.get("state_ticks_left", 0))
                self.shades.append(Shade(id=sid, pos=pos, state=st, state_ticks_left=st_left, spawn_tick=-1))

        # Drifters
        if scenario is not None and "drifters" in scenario:
            for item in scenario["drifters"]:
                did = str(item.get("id") or self._next_drifter_id())
                pos = [float(item["pos"][0]), float(item["pos"][1]), float(item["pos"][2])]
                st = str(item.get("state", "idle"))
                stolen = int(item.get("stolen", 0))
                flee_left = int(item.get("flee_ticks_left", DRIFTER_FLEE_TICKS if st == "flee" else 0))
                self.drifters.append(
                    Drifter(
                        id=did,
                        pos=pos,
                        state=st,
                        stolen=stolen,
                        flee_ticks_left=flee_left,
                        has_stolen=(stolen > 0),
                        spawn_tick=-1,
                    )
                )

        # Charms
        if scenario is not None and "charms" in scenario:
            self.charms = []
            for i, item in enumerate(scenario["charms"]):
                cid = str(item.get("id") or f"C{i + 1}")
                pos = [float(item["pos"][0]), float(item["pos"][1]), float(item["pos"][2])]
                avail = bool(item.get("available", True))
                resp_s = float(item.get("respawn_s", 0.0))
                self.charms.append(
                    Charm(id=cid, pos=pos, available=avail, respawn_ticks=int(round(resp_s * TICK_RATE)))
                )

    def snapshot(self) -> dict[str, Any]:
        return {
            "type": "snapshot",
            "tick": self.tick,
            "sim_tick": self.sim_tick,
            "night": self.night,
            "state": self.state,
            "time_left_s": r3(self.time_left_s),
            "score": self.score,
            "wind": {
                "active": self.wind_active,
                "dir_deg": r3(self.wind_dir_deg),
            },
            "player": {
                "pos": [r3(self.player_pos[0]), r3(self.player_pos[1]), r3(self.player_pos[2])],
                "vel": [r3(self.player_vel[0]), r3(self.player_vel[1]), r3(self.player_vel[2])],
                "grounded": self.grounded,
                "flames": self.flames,
                "carried": self.carried,
                "invuln": self.invuln_ticks > 0,
                "dash_cd_s": r3(self.dash_cd_ticks / TICK_RATE),
                "pulse_cd_s": r3(self.pulse_cd_ticks / TICK_RATE),
                "charm_s": r3(self.charm_ticks / TICK_RATE),
            },
            "lanterns": [lt.to_snapshot() for lt in self.lanterns],
            "shades": [s.to_snapshot() for s in self.shades],
            "motes_active": len(self.motes),
            "motes": [m.to_snapshot() for m in self.motes],
            "drifters": [d.to_snapshot() for d in self.drifters if d.state != "removed"],
            "charms": [c.to_snapshot() for c in self.charms],
        }

    def end_record(self) -> dict[str, Any]:
        return {
            "type": "end",
            "ticks": self.tick,
            "state": self.state,
            "score": self.score,
        }

    def step(self, inp: InputState) -> list[dict[str, Any]]:
        """Execute one tick following the exact 12-step order of Ticket-02."""
        if self.state in ("won", "lost"):
            return []

        self.tick += 1
        cur_tick = self.tick
        events: list[dict[str, Any]] = []

        def emit(name: str, data: dict[str, Any]) -> None:
            events.append({"type": "event", "tick": cur_tick, "name": name, "data": data})

        # Step 1: Read input & process pause first
        pause_pressed = inp.pause and not self._prev_input.pause
        jump_pressed = inp.jump and not self._prev_input.jump
        interact_pressed = inp.interact and not self._prev_input.interact
        pulse_pressed = inp.pulse and not self._prev_input.pulse
        dash_pressed = inp.dash and not self._prev_input.dash
        self._prev_input = inp.copy()

        if pause_pressed:
            if self.state == "playing":
                self.state = "paused"
                emit("paused", {})
                return events
            if self.state == "paused":
                self.state = "playing"
                emit("resumed", {})

        if self.state == "paused":
            return events

        # Active gameplay tick
        self.sim_tick += 1
        st = self.sim_tick

        # Step 2: Decrement timers (time, cooldowns, invuln, stun, charm, dropped mote TTL, charm respawn, wind)
        self.time_left_s = max(0.0, self.initial_time_left_s - (st / TICK_RATE))
        if self.dash_cd_ticks > 0:
            self.dash_cd_ticks -= 1
        if self.pulse_cd_ticks > 0:
            self.pulse_cd_ticks -= 1
        if self.invuln_ticks > 0:
            self.invuln_ticks -= 1
        if self.charm_ticks > 0:
            self.charm_ticks -= 1

        # Dropped mote TTL
        alive_motes: list[Mote] = []
        for m in self.motes:
            if m.ttl_ticks is not None:
                m.ttl_ticks -= 1
                if m.ttl_ticks <= 0:
                    continue
            alive_motes.append(m)
        self.motes = alive_motes

        # Charm respawn
        for c in self.charms:
            if not c.available and c.respawn_ticks > 0:
                c.respawn_ticks -= 1
                if c.respawn_ticks <= 0:
                    c.available = True
                    c.respawn_ticks = 0

        # Shade state timers
        for s in self.shades:
            if s.safe_push_ticks > 0:
                s.safe_push_ticks -= 1
            if s.state in ("stunned", "recoil", "spawning"):
                if s.state_ticks_left > 0:
                    s.state_ticks_left -= 1
                if s.state_ticks_left <= 0:
                    s.state = "wander"

        # Wind cycle (Night 3)
        if self.wind_enabled:
            if self.wind_active:
                self.wind_ticks_left -= 1
                if self.wind_ticks_left <= 0:
                    self.wind_active = False
            elif st > 0 and st % WIND_CYCLE_TICKS == 0:
                self.wind_active = True
                self.wind_ticks_left = WIND_ACTIVE_TICKS
                self.wind_dir_deg = r3(self.rng.uniform(0.0, 360.0))

        # Respawn wait after falling
        if self.respawn_wait_ticks > 0:
            self.respawn_wait_ticks -= 1
            if self.respawn_wait_ticks <= 0:
                self.player_pos = [0.0, 0.0, 0.0]
                self.player_vel = [0.0, 0.0, 0.0]
                self.grounded = True
                self.pad_launched = False
                self.dash_ticks_left = 0
                self.invuln_ticks = int(round(float(self.tuning["invuln_s"]) * TICK_RATE))
        else:
            # Step 3: Move May (jump, dash, jump pad, wind) then check fall off island
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
            if math.hypot(wx, wz) > 1e-6:
                d_w = math.hypot(wx, wz)
                self.facing_x = wx / d_w
                self.facing_z = wz / d_w

            # Dash trigger
            dash_allowed = self.dash_ticks_left <= 0 and (self.charm_ticks > 0 or self.dash_cd_ticks <= 0)
            if dash_pressed and dash_allowed:
                self.dash_ticks_left = int(round(float(self.tuning["dash_duration_s"]) * TICK_RATE))
                self.dash_cd_ticks = 0 if self.charm_ticks > 0 else int(round(float(self.tuning["dash_cooldown_s"]) * TICK_RATE))
                if math.hypot(wx, wz) > 1e-6:
                    d_w = math.hypot(wx, wz)
                    self.dash_dir_x = wx / d_w
                    self.dash_dir_z = wz / d_w
                else:
                    self.dash_dir_x = self.facing_x
                    self.dash_dir_z = self.facing_z
                self.pad_launched = False
                emit("dash", {})

            # Compute horizontal & vertical velocity
            if self.dash_ticks_left > 0:
                dash_spd = float(self.tuning["dash_speed"])
                vx = self.dash_dir_x * dash_spd
                vz = self.dash_dir_z * dash_spd
                vy = 0.0  # Air dash keeps altitude
                self.dash_ticks_left -= 1
            elif self.pad_launched:
                vx = self.pad_vx
                vz = self.pad_vz
                vy = self.player_vel[1] - GRAVITY * DT
            else:
                move_spd = CHARM_SPEED if self.charm_ticks > 0 else float(self.tuning["player_speed"])
                vx = wx * move_spd
                vz = wz * move_spd
                if jump_pressed and self.grounded:
                    vy = JUMP_VELOCITY
                    self.grounded = False
                else:
                    vy = self.player_vel[1] - GRAVITY * DT if not self.grounded else 0.0

            # Strong wind push (Night 3)
            if self.wind_active:
                w_rad = math.radians(self.wind_dir_deg)
                vx += math.cos(w_rad) * WIND_SPEED
                vz += math.sin(w_rad) * WIND_SPEED

            old_x, old_y, old_z = self.player_pos
            new_x = old_x + vx * DT
            new_z = old_z + vz * DT
            if is_blocked_by_wall_or_tower(self.night, old_x, old_z, new_x, new_z, old_y):
                new_x, new_z = old_x, old_z
                vx, vz = 0.0, 0.0

            new_y = old_y + vy * DT
            gh = ground_height(self.night, new_x, new_z, old_y)
            if gh is not None and new_y <= gh and vy <= 0.0:
                new_y = gh
                vy = 0.0
                self.grounded = True
                self.pad_launched = False
            else:
                if gh is not None and new_y <= gh and self.grounded:
                    new_y = gh
                    vy = 0.0
                else:
                    self.grounded = False

            self.player_pos = [new_x, new_y, new_z]
            self.player_vel = [vx, vy, vz]

            # Check jump pads (only if not already launched this tick)
            for pad in self.map_cfg.jump_pads:
                if dist_xz(self.player_pos, [pad.pos[0], pad.pos[1], pad.pos[2]]) <= pad.radius and abs(self.player_pos[1] - pad.pos[1]) <= 0.6:
                    self.pad_launched = True
                    self.dash_ticks_left = 0
                    self.grounded = False
                    self.pad_vx = pad.dir_x * pad.vel_h
                    self.pad_vz = pad.dir_z * pad.vel_h
                    self.player_vel = [self.pad_vx, pad.vel_y, self.pad_vz]
                    break

            # Fall check (Y < -10): ignores invuln, happens once
            if self.tuning.get("fall_enabled", True) and self.player_pos[1] < -10.0:
                self.flames = max(0, self.flames - 1)
                lost_motes = self.carried
                self.carried = 0
                emit("player_hit", {"by": "fall", "flames": self.flames, "dropped": 0, "lost": lost_motes})
                if self.flames > 0:
                    self.respawn_wait_ticks = RESPAWN_WAIT_TICKS
                    self.player_vel = [0.0, 0.0, 0.0]

        # Steps 4-7 only if player is alive and not waiting to respawn
        if self.respawn_wait_ticks <= 0 and self.flames > 0:
            # Step 4: Pickup motes and charms
            pickup_r = float(self.tuning["pickup_radius"])
            carry_cap = int(self.tuning["carry_capacity"])
            remaining_motes: list[Mote] = []
            for m in self.motes:
                can_pick = m.spawn_tick < st
                if (
                    can_pick
                    and self.carried < carry_cap
                    and dist_xz(self.player_pos, m.pos) <= pickup_r
                    and abs(self.player_pos[1] - m.pos[1]) <= 1.5
                ):
                    self.carried += 1
                    emit("mote_picked", {"carried": self.carried})
                else:
                    remaining_motes.append(m)
            self.motes = remaining_motes

            for c in self.charms:
                if (
                    c.available
                    and dist_xz(self.player_pos, c.pos) <= pickup_r
                    and abs(self.player_pos[1] - c.pos[1]) <= 1.5
                ):
                    c.available = False
                    c.respawn_ticks = CHARM_RESPAWN_TICKS
                    self.charm_ticks = CHARM_DURATION_TICKS
                    emit("charm_picked", {"charm_id": c.id, "charm_ticks": CHARM_DURATION_TICKS})

            # Step 5: Interact with nearest unlit lantern
            if interact_pressed and self.carried > 0:
                interact_r = float(self.tuning["interact_radius"])
                lantern_cost = int(self.tuning["lantern_cost"])
                candidates = [
                    (dist_xz(self.player_pos, lt.pos), lt)
                    for lt in self.lanterns
                    if not lt.lit and dist_xz(self.player_pos, lt.pos) <= interact_r and abs(self.player_pos[1] - lt.pos[1]) <= 2.0
                ]
                if candidates:
                    candidates.sort(key=lambda pair: (pair[0], pair[1].id))
                    target = candidates[0][1]
                    needed = max(0, lantern_cost - target.deposited)
                    amount = min(self.carried, needed)
                    if amount > 0:
                        self.carried -= amount
                        target.deposited += amount
                        self.score += amount * int(self.score_cfg["per_mote"])
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
                            # Mark shades currently inside this newly lit lantern's safe zone for pushout
                            safe_r = float(self.tuning["safe_radius"])
                            for s in self.shades:
                                if dist_xz(s.pos, target.pos) < safe_r:
                                    s.safe_push_ticks = SAFE_PUSHOUT_MAX_TICKS

            # Step 6: Update safe zones around lit lanterns
            safe_r = float(self.tuning["safe_radius"])
            lit_lanterns = [lt for lt in self.lanterns if lt.lit]
            for s in self.shades:
                for lt in lit_lanterns:
                    lx = s.pos[0] - lt.pos[0]
                    lz = s.pos[2] - lt.pos[2]
                    ld = math.hypot(lx, lz)
                    if ld < safe_r:
                        nx, nz = (lx / ld, lz / ld) if ld > 1e-6 else (1.0, 0.0)
                        if s.safe_push_ticks > 0:
                            step_out = min(safe_r - ld + 0.01, (safe_r / SAFE_PUSHOUT_MAX_TICKS) * 1.5)
                            s.pos[0] += nx * step_out
                            s.pos[2] += nz * step_out
                        else:
                            s.pos[0] = lt.pos[0] + nx * (safe_r + 1e-3)
                            s.pos[2] = lt.pos[2] + nz * (safe_r + 1e-3)

            # Step 7: Pulse (Tỏa Sáng)
            if pulse_pressed:
                pulse_cost = int(self.tuning["pulse_cost"])
                if self.pulse_cd_ticks <= 0 and self.carried >= pulse_cost:
                    self.carried -= pulse_cost
                    self.pulse_cd_ticks = int(round(float(self.tuning["pulse_cooldown_s"]) * TICK_RATE))
                    pulse_r = float(self.tuning["pulse_radius"])
                    stun_ticks = int(round(float(self.tuning["pulse_stun_s"]) * TICK_RATE))
                    push_m = float(self.tuning["pulse_push_m"])
                    pulse_center = [self.player_pos[0], self.player_pos[1] + 0.8, self.player_pos[2]]

                    stunned_ids: list[str] = []
                    for s in sorted(self.shades, key=lambda x: x.id):
                        if s.spawn_tick >= st:
                            continue
                        if dist_3d(pulse_center, s.pos) <= pulse_r:
                            s.state = "stunned"
                            s.state_ticks_left = stun_ticks
                            s.push_ticks_left = PULSE_PUSH_TICKS
                            dx = s.pos[0] - self.player_pos[0]
                            dz = s.pos[2] - self.player_pos[2]
                            d_xz = math.hypot(dx, dz)
                            nx, nz = (dx / d_xz, dz / d_xz) if d_xz > 1e-6 else (1.0, 0.0)
                            push_speed = push_m / (PULSE_PUSH_TICKS * DT)
                            s.push_vx = nx * push_speed
                            s.push_vz = nz * push_speed
                            stunned_ids.append(s.id)
                            self.score += int(self.score_cfg["per_stun"])

                    emit("pulse", {"stunned_ids": stunned_ids})

                    # Pulse vs Drifters
                    for dr in sorted(self.drifters, key=lambda x: x.id):
                        if dr.state == "removed" or dr.spawn_tick >= st:
                            continue
                        if dist_3d(pulse_center, dr.pos) <= pulse_r:
                            if dr.state == "chase":
                                dr.state = "flee"
                                dr.flee_ticks_left = DRIFTER_FLEE_TICKS
                            elif dr.state == "flee" and dr.stolen > 0:
                                amt = dr.stolen
                                dr.stolen = 0
                                dr.flee_ticks_left = min(dr.flee_ticks_left, DRIFTER_DROP_DESPAWN_TICKS)
                                for _ in range(amt):
                                    self.motes.append(
                                        Mote(
                                            id=self._next_mote_id(),
                                            pos=[dr.pos[0], dr.pos[1], dr.pos[2]],
                                            kind="dropped",
                                            ttl_ticks=DROPPED_MOTE_TTL_TICKS,
                                            spawn_tick=st,
                                        )
                                    )
                                emit("drifter_drop", {"drifter_id": dr.id, "amount": amt})

        # Step 8: Move Shades and Drifters
        shade_spd = self.map_cfg.shade_speed
        safe_r = float(self.tuning["safe_radius"])
        lit_lanterns = [lt for lt in self.lanterns if lt.lit]

        for s in self.shades:
            if s.state == "spawning":
                continue
            old_x, old_z = s.pos[0], s.pos[2]
            if s.state == "stunned":
                if s.push_ticks_left > 0:
                    nx = s.pos[0] + s.push_vx * DT
                    nz = s.pos[2] + s.push_vz * DT
                    if not is_blocked_by_wall_or_tower(self.night, old_x, old_z, nx, nz, s.pos[1]):
                        s.pos[0], s.pos[2] = nx, nz
                    s.push_ticks_left -= 1
            elif s.state == "recoil":
                s.pos[0] += s.recoil_vx * DT
                s.pos[2] += s.recoil_vz * DT
            else:
                d_to_p = dist_xz(s.pos, self.player_pos)
                if s.state == "wander" and d_to_p <= SHADE_DETECT_R:
                    s.state = "chase"
                elif s.state == "chase" and d_to_p > SHADE_LOSE_R:
                    s.state = "wander"

                if s.state == "chase":
                    dx = self.player_pos[0] - s.pos[0]
                    dz = self.player_pos[2] - s.pos[2]
                    d = math.hypot(dx, dz)
                    if d > 1e-6:
                        step_d = min(d, shade_spd * DT)
                        s.pos[0] += (dx / d) * step_d
                        s.pos[2] += (dz / d) * step_d
                else:
                    # Wander slowly
                    if s.wander_timer <= 0:
                        ang = self.rng.uniform(0.0, 2.0 * math.pi)
                        s.wander_dir_x = math.cos(ang)
                        s.wander_dir_z = math.sin(ang)
                        s.wander_timer = 120
                    s.wander_timer -= 1
                    s.pos[0] += s.wander_dir_x * (shade_spd * 0.4) * DT
                    s.pos[2] += s.wander_dir_z * (shade_spd * 0.4) * DT

            # Block shades at lit lantern safe_radius
            for lt in lit_lanterns:
                lx = s.pos[0] - lt.pos[0]
                lz = s.pos[2] - lt.pos[2]
                ld = math.hypot(lx, lz)
                if ld < safe_r:
                    nx, nz = (lx / ld, lz / ld) if ld > 1e-6 else (1.0, 0.0)
                    s.pos[0] = lt.pos[0] + nx * (safe_r + 1e-3)
                    s.pos[2] = lt.pos[2] + nz * (safe_r + 1e-3)

            # Snap shade to ground if on island
            gh = ground_height(self.night, s.pos[0], s.pos[2], s.pos[1])
            if gh is not None:
                s.pos[1] = gh

        # Move Drifters
        for dr in self.drifters:
            if dr.state == "removed":
                continue
            if dr.state == "flee":
                dr.flee_ticks_left -= 1
                if dr.flee_ticks_left <= 0:
                    dr.state = "removed"
                    continue
                dx = dr.pos[0] - self.player_pos[0]
                dz = dr.pos[2] - self.player_pos[2]
                d = math.hypot(dx, dz)
                nx, nz = (dx / d, dz / d) if d > 1e-6 else (1.0, 0.0)
                dr.pos[0] += nx * DRIFTER_FAST_SPEED * DT
                dr.pos[2] += nz * DRIFTER_FAST_SPEED * DT
            else:
                d_to_p = dist_xz(dr.pos, self.player_pos)
                if self.carried >= DRIFTER_DETECT_MOTES and d_to_p <= DRIFTER_DETECT_R and not dr.has_stolen:
                    dr.state = "chase"
                else:
                    dr.state = "idle"

                if dr.state == "chase":
                    dx = self.player_pos[0] - dr.pos[0]
                    dz = self.player_pos[2] - dr.pos[2]
                    d = math.hypot(dx, dz)
                    if d > 1e-6:
                        step_d = min(d, DRIFTER_FAST_SPEED * DT)
                        dr.pos[0] += (dx / d) * step_d
                        dr.pos[2] += (dz / d) * step_d
                else:
                    dr.idle_angle += 0.6 * DT
                    dr.pos[0] += math.cos(dr.idle_angle) * DRIFTER_IDLE_SPEED * DT
                    dr.pos[2] += math.sin(dr.idle_angle) * DRIFTER_IDLE_SPEED * DT

        # Step 9: Collisions — Drifters steal FIRST, then Shades hit (sorted by ascending id)
        if self.respawn_wait_ticks <= 0 and self.flames > 0:
            for dr in sorted(self.drifters, key=lambda x: x.id):
                if dr.state in ("removed", "flee") or dr.has_stolen or dr.spawn_tick >= st:
                    continue
                if dist_xz(self.player_pos, dr.pos) <= DRIFTER_STEAL_R and self.carried > 0:
                    amt = min(3, self.carried)
                    self.carried -= amt
                    dr.stolen = amt
                    dr.has_stolen = True
                    dr.state = "flee"
                    dr.flee_ticks_left = DRIFTER_FLEE_TICKS
                    emit("drifter_steal", {"drifter_id": dr.id, "amount": amt, "carried": self.carried})

            hit_r = float(self.tuning["shade_hit_radius"])
            if self.invuln_ticks <= 0:
                for s in sorted(self.shades, key=lambda x: x.id):
                    if s.spawn_tick >= st:
                        continue
                    if s.state in ("stunned", "recoil", "spawning") or s.safe_push_ticks > 0:
                        continue
                    if dist_xz(self.player_pos, s.pos) <= hit_r and abs(self.player_pos[1] - s.pos[1]) <= 1.5:
                        self.flames = max(0, self.flames - 1)
                        dropped = math.floor(self.carried * float(self.tuning["hit_drop_ratio"]))
                        self.carried -= dropped
                        self.invuln_ticks = int(round(float(self.tuning["invuln_s"]) * TICK_RATE))
                        # Drop motes in ring 1.5 - 2.5m around May (pickable next tick)
                        for idx in range(dropped):
                            ang = self.rng.uniform(0.0, 2.0 * math.pi)
                            rad = self.rng.uniform(1.5, 2.5)
                            mx_pos = self.player_pos[0] + rad * math.cos(ang)
                            mz_pos = self.player_pos[2] + rad * math.sin(ang)
                            mgh = ground_height(self.night, mx_pos, mz_pos, self.player_pos[1])
                            my_pos = mgh if mgh is not None else self.player_pos[1]
                            self.motes.append(
                                Mote(
                                    id=self._next_mote_id(),
                                    pos=[mx_pos, my_pos, mz_pos],
                                    kind="dropped",
                                    ttl_ticks=DROPPED_MOTE_TTL_TICKS,
                                    spawn_tick=st,
                                )
                            )
                        # Shade enters recoil (2m over 60 ticks away from May)
                        dx = s.pos[0] - self.player_pos[0]
                        dz = s.pos[2] - self.player_pos[2]
                        d = math.hypot(dx, dz)
                        nx, nz = (dx / d, dz / d) if d > 1e-6 else (1.0, 0.0)
                        recoil_spd = SHADE_RECOIL_DIST / (SHADE_RECOIL_TICKS * DT)
                        s.state = "recoil"
                        s.state_ticks_left = SHADE_RECOIL_TICKS
                        s.recoil_vx = nx * recoil_spd
                        s.recoil_vz = nz * recoil_spd
                        emit("player_hit", {"by": "shade", "flames": self.flames, "dropped": dropped})
                        break

        # Step 10: Scheduled spawns (newly spawned interact starting next tick)
        if self.random_motes and st % MOTE_SPAWN_INTERVAL == 0 and len(self.motes) < MOTE_CAP:
            sp = self._pick_empty_mote_spawn()
            if sp is not None:
                self.motes.append(Mote(id=self._next_mote_id(), pos=[sp[0], sp[1], sp[2]], kind="random", spawn_tick=st))

        if self.random_shades:
            to_spawn = 0
            if st == 300:
                to_spawn = 2
            elif st > 300 and (st - 300) % self.map_cfg.shade_spawn_interval_ticks == 0:
                to_spawn = 1
            for _ in range(to_spawn):
                if len(self.shades) >= self.map_cfg.shade_max:
                    break
                sp = self._pick_valid_shade_spawn()
                if sp is not None:
                    ns = Shade(id=self._next_shade_id(), pos=[sp[0], sp[1], sp[2]], state="wander", spawn_tick=st)
                    self.shades.append(ns)
                    emit("shade_spawned", {"id": ns.id})

        if self.random_drifters and st % DRIFTER_SPAWN_INTERVAL == 0:
            active_drifters = [d for d in self.drifters if d.state != "removed"]
            if len(active_drifters) < DRIFTER_MAX and self.map_cfg.shade_spawns:
                sp = self.rng.choice(self.map_cfg.shade_spawns)
                nd = Drifter(id=self._next_drifter_id(), pos=[sp[0], sp[1], sp[2]], state="idle", spawn_tick=st)
                self.drifters.append(nd)

        # Step 11: Win / Lose priority (no_flames > all_lit > dawn)
        if self.flames <= 0:
            self.state = "lost"
            emit("game_over", {"result": "lost", "reason": "no_flames"})
        elif all(lt.lit for lt in self.lanterns):
            self.score += math.floor(self.time_left_s) * int(self.score_cfg["per_second_left"])
            self.score += self.flames * int(self.score_cfg["per_flame_left"])
            self.state = "won"
            emit("game_over", {"result": "won", "reason": "all_lit"})
        elif self.time_left_s <= 0.0:
            self.state = "lost"
            emit("game_over", {"result": "lost", "reason": "dawn"})

        return events
