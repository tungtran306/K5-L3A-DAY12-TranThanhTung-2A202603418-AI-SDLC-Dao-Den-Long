"""Standardized 3-Night map definitions, terrain height, ramps, jump pads, and obstacles (Ticket-02)."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class JumpPad:
    pos: tuple[float, float, float]
    radius: float
    vel_y: float
    vel_h: float
    dir_x: float
    dir_z: float


@dataclass(frozen=True)
class NightConfig:
    night: int
    name: str
    duration_s: float
    shade_speed: float
    shade_spawn_interval_ticks: int
    shade_max: int
    has_drifters: bool
    has_wind: bool
    lanterns: list[tuple[str, tuple[float, float, float]]]
    mote_spawns: list[tuple[float, float, float]]
    shade_spawns: list[tuple[float, float, float]]
    charms: list[tuple[str, tuple[float, float, float]]]
    jump_pads: list[JumpPad]


def _ring_points(
    count: int,
    radius: float,
    start_deg: float = 0.0,
    step_deg: float | None = None,
    cx: float = 0.0,
    cy: float = 0.0,
    cz: float = 0.0,
) -> list[tuple[float, float, float]]:
    if step_deg is None:
        step_deg = 360.0 / count
    pts: list[tuple[float, float, float]] = []
    for i in range(count):
        ang = math.radians(start_deg + i * step_deg)
        pts.append((round(cx + radius * math.cos(ang), 3), round(cy, 3), round(cz + radius * math.sin(ang), 3)))
    return pts


def get_night_config(night: int) -> NightConfig:
    if night == 1:
        lanterns = [
            ("L1", (0.0, 0.0, 25.0)),
            ("L2", (23.8, 0.0, 7.7)),
            ("L3", (14.7, 0.0, -20.2)),
            ("L4", (-14.7, 0.0, -20.2)),
            ("L5", (-23.8, 0.0, 7.7)),
        ]
        mote_spawns = _ring_points(8, 12.0, 0.0, 45.0) + _ring_points(16, 33.0, 0.0, 22.5)
        shade_spawns = _ring_points(12, 37.0, 15.0, 30.0)
        return NightConfig(
            night=1,
            name="Đêm 1 – Đảo Bến",
            duration_s=300.0,
            shade_speed=4.0,
            shade_spawn_interval_ticks=480,
            shade_max=6,
            has_drifters=False,
            has_wind=False,
            lanterns=lanterns,
            mote_spawns=mote_spawns,
            shade_spawns=shade_spawns,
            charms=[],
            jump_pads=[],
        )

    if night == 2:
        lanterns = [
            ("L1", (0.0, 0.0, 20.0)),
            ("L2", (17.0, 0.0, -10.0)),
            ("L3", (-17.0, 0.0, -10.0)),
            ("L4", (70.0, 0.0, 20.0)),
            ("L5", (87.0, 0.0, -10.0)),
            ("L6", (53.0, 0.0, -10.0)),
        ]
        mote_spawns = (
            _ring_points(4, 10.0, 0.0, 90.0, cx=0.0)
            + _ring_points(8, 22.0, 0.0, 45.0, cx=0.0)
            + _ring_points(4, 10.0, 0.0, 90.0, cx=70.0)
            + _ring_points(8, 22.0, 0.0, 45.0, cx=70.0)
        )
        shade_spawns = (
            _ring_points(8, 26.0, 22.5, 45.0, cx=0.0)
            + _ring_points(8, 26.0, 22.5, 45.0, cx=70.0)
        )
        # Pad 1 at (20,0,18) -> toward (70,0,0)
        d1 = math.hypot(50.0, -18.0)
        # Pad 2 at (50,0,-18) -> toward (0,0,0)
        d2 = math.hypot(-50.0, 18.0)
        jump_pads = [
            JumpPad((20.0, 0.0, 18.0), 1.0, 14.0, 24.0, 50.0 / d1, -18.0 / d1),
            JumpPad((50.0, 0.0, -18.0), 1.0, 14.0, 24.0, -50.0 / d2, 18.0 / d2),
        ]
        return NightConfig(
            night=2,
            name="Đêm 2 – Đảo Cau",
            duration_s=330.0,
            shade_speed=4.0,
            shade_spawn_interval_ticks=420,
            shade_max=8,
            has_drifters=True,
            has_wind=False,
            lanterns=lanterns,
            mote_spawns=mote_spawns,
            shade_spawns=shade_spawns,
            charms=[("C1", (35.0, 0.0, 0.0))],
            jump_pads=jump_pads,
        )

    if night == 3:
        lanterns = [
            ("L1", (0.0, 6.0, 6.0)),
            ("L2", (18.0, 3.0, 10.0)),
            ("L3", (-18.0, 3.0, 10.0)),
            ("L4", (35.0, 0.0, -10.0)),
            ("L5", (-35.0, 0.0, -10.0)),
            ("L6", (20.0, 0.0, -35.0)),
            ("L7", (-20.0, 0.0, -35.0)),
        ]
        mote_spawns = (
            _ring_points(18, 34.0, 0.0, 20.0, cy=0.0)
            + _ring_points(8, 18.0, 20.0, 20.0, cy=3.0)
            + _ring_points(4, 5.0, 45.0, 90.0, cy=6.0)
        )
        shade_spawns = _ring_points(16, 43.0, 0.0, 22.5, cy=0.0)
        jump_pads = [
            JumpPad((0.0, 3.0, 13.0), 1.0, 12.0, 8.0, 0.0, -1.0),
        ]
        return NightConfig(
            night=3,
            name="Đêm 3 – Đảo Chuông",
            duration_s=360.0,
            shade_speed=4.5,
            shade_spawn_interval_ticks=360,
            shade_max=10,
            has_drifters=True,
            has_wind=True,
            lanterns=lanterns,
            mote_spawns=mote_spawns,
            shade_spawns=shade_spawns,
            charms=[("C1", (30.0, 0.0, 25.0)), ("C2", (-30.0, 0.0, 25.0))],
            jump_pads=jump_pads,
        )

    raise ValueError(f"Unsupported night: {night}")


def _night3_ramp_height(x: float, z: float) -> float | None:
    """Return ramp height [0..3] if (x, z) lies on either 3m-wide ramp at 30 deg or 150 deg."""
    for deg in (30.0, 150.0):
        ang = math.radians(deg)
        ux, uz = math.cos(ang), math.sin(ang)
        # Projection along radius and perpendicular distance
        proj = x * ux + z * uz
        perp = abs(-x * uz + z * ux)
        if 24.0 <= proj <= 30.0 and perp <= 1.5:
            # Linear from Y=0 at r=30 to Y=3 at r=24
            return 3.0 * (30.0 - proj) / 6.0
    return None


def ground_height(night: int, x: float, z: float, cur_y: float = 0.0) -> float | None:
    """Return walkable ground height at (x, z), or None if over the cloud sea."""
    if night == 1:
        return 0.0 if math.hypot(x, z) <= 40.0 else None

    if night == 2:
        in_a = math.hypot(x, z) <= 28.0
        in_b = math.hypot(x - 70.0, z) <= 28.0
        on_bridge = 26.0 <= x <= 44.0 and -2.0 <= z <= 2.0
        return 0.0 if (in_a or in_b or on_bridge) else None

    if night == 3:
        r = math.hypot(x, z)
        if r > 45.0:
            return None
        # Collect valid surfaces at or below cur_y + small step tolerance (or highest reachable)
        surfaces = [0.0]
        ramp_h = _night3_ramp_height(x, z)
        if ramp_h is not None:
            surfaces.append(ramp_h)
        if 12.0 <= r <= 24.0 and z > 0.0:
            surfaces.append(3.0)
        if r <= 8.0:
            surfaces.append(6.0)
        # Highest surface that is <= cur_y + 0.35 (cannot walk up vertical 3m walls)
        reachable = [h for h in surfaces if h <= cur_y + 0.35]
        return max(reachable) if reachable else 0.0

    return None


def is_blocked_by_wall_or_tower(night: int, old_x: float, old_z: float, new_x: float, new_z: float, cur_y: float) -> bool:
    """Check if horizontal move hits Night 3 vertical tier wall or bell tower cylinder."""
    if night != 3:
        return False
    r_new = math.hypot(new_x, new_z)
    # Bell tower at center of Tier 2: cylinder radius 2m, height 8m (Y in [6, 14])
    if r_new < 2.0 and cur_y >= 5.5:
        return True

    # Check if stepping horizontally into a higher tier without being high enough
    ramp_h = _night3_ramp_height(new_x, new_z)
    if ramp_h is not None and ramp_h <= cur_y + 0.55:
        return False

    # Entering Tier 2 disk (Y=6) from below
    if r_new <= 8.0 and cur_y < 5.65:
        r_old = math.hypot(old_x, old_z)
        if r_old > 8.0:
            return True

    # Entering Tier 1 annulus (Y=3) from below (not via ramp)
    if 12.0 <= r_new <= 24.0 and new_z > 0.0 and cur_y < 2.65:
        r_old = math.hypot(old_x, old_z)
        was_in_t1 = 12.0 <= r_old <= 24.0 and old_z > 0.0
        if not was_in_t1:
            return True

    return False
