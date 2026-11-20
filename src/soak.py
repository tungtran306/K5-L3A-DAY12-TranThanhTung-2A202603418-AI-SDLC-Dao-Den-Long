"""Headless multi-night soak test runner for Dao Den Long (Ticket-04 / Contract v1.3)."""

from __future__ import annotations

import argparse
import ctypes
import gc
import json
import math
import os
import random
import sys
import time
from pathlib import Path

from src.engine import GameEngine, InputState, TICK_RATE, load_contract


def get_rss_mb() -> float:
    """Return current process Resident Set Size (RSS) in MB (Windows, Linux, macOS)."""
    if sys.platform == "win32":
        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.c_ulong),
                ("PageFaultCount", ctypes.c_ulong),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
        k32 = ctypes.windll.kernel32
        k32.GetCurrentProcess.restype = ctypes.c_void_p
        psapi = ctypes.windll.psapi
        psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(PROCESS_MEMORY_COUNTERS), ctypes.c_ulong]
        psapi.GetProcessMemoryInfo.restype = ctypes.c_int
        hproc = k32.GetCurrentProcess()
        if psapi.GetProcessMemoryInfo(hproc, ctypes.byref(counters), counters.cb):
            return round(counters.WorkingSetSize / (1024 * 1024), 2)
        return 0.0

    # Linux /proc/self/status VmRSS
    proc_status = Path("/proc/self/status")
    if proc_status.is_file():
        for line in proc_status.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("VmRSS:"):
                kb = int(line.split()[1])
                return round(kb / 1024.0, 2)

    # macOS / POSIX fallback
    import resource  # type: ignore

    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        return round(rss / (1024 * 1024), 2)
    return round(rss / 1024.0, 2)


def run_soak(seed: int, nights: int, out_path: str) -> int:
    t0 = time.perf_counter()
    tuning = load_contract()["tuning"]
    results: list[str] = []
    crashes = 0
    mem_start_mb: float | None = None

    for i in range(nights):
        night_num = (i % 3) + 1
        night_seed = seed + i
        inp_rng = random.Random(night_seed * 10007 + 13)
        try:
            engine = GameEngine(seed=night_seed, night=night_num, tuning=tuning)
            if mem_start_mb is None:
                gc.collect()
                mem_start_mb = get_rss_mb()

            max_ticks = int(round(engine.initial_time_left_s * TICK_RATE))
            cur_inp = InputState()
            for tick_idx in range(max_ticks):
                if engine.state in ("won", "lost"):
                    break
                if tick_idx % 30 == 0:
                    ang = inp_rng.uniform(0.0, 2.0 * math.pi)
                    cur_inp.move_x = math.cos(ang)
                    cur_inp.move_z = math.sin(ang)
                cur_inp.jump = inp_rng.random() < 0.05
                cur_inp.dash = inp_rng.random() < 0.03
                cur_inp.pulse = inp_rng.random() < 0.02
                cur_inp.interact = inp_rng.random() < 0.10
                engine.step(cur_inp)

            results.append(engine.state if engine.state in ("won", "lost") else "lost")
            del engine
        except Exception as exc:
            crashes += 1
            results.append("crash")
            print(f"Soak crash on night index {i}: {exc}", file=sys.stderr)

    gc.collect()
    mem_end_mb = get_rss_mb()
    duration_s = round(time.perf_counter() - t0, 3)

    payload = {
        "nights": nights,
        "crashes": crashes,
        "results": results,
        "mem_start_mb": mem_start_mb if mem_start_mb is not None else mem_end_mb,
        "mem_end_mb": mem_end_mb,
        "duration_s": duration_s,
    }
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload))
    return 0 if crashes == 0 else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Dao Den Long Soak Test Runner (Contract v1.3)")
    parser.add_argument("--seed", type=int, default=7, help="Base seed (default: 7)")
    parser.add_argument("--nights", type=int, default=10, help="Number of consecutive nights (default: 10)")
    parser.add_argument("--out", type=str, required=True, help="Output soak.json path")
    args = parser.parse_args()
    sys.exit(run_soak(args.seed, args.nights, args.out))


if __name__ == "__main__":
    main()
