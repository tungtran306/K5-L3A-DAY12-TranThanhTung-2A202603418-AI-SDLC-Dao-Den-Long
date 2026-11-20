"""Automated 1280x720 3D benchmark runner for Dao Den Long (Ticket-04 / Contract v1.3)."""

from __future__ import annotations

import argparse
import http.server
import json
import os
import platform
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
import webbrowser
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent


def find_chromium() -> str | None:
    candidates: list[str] = []
    if sys.platform == "win32":
        for env in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            base = os.environ.get(env)
            if base:
                candidates.extend(
                    [
                        os.path.join(base, "Google", "Chrome", "Application", "chrome.exe"),
                        os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe"),
                    ]
                )
    elif sys.platform == "darwin":
        candidates.extend(
            [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Chromium.app/Contents/MacOS/Chromium",
                "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            ]
        )
    else:
        for name in ("google-chrome", "chromium", "chromium-browser", "microsoft-edge"):
            found = shutil.which(name)
            if found:
                candidates.append(found)

    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def run_benchmark(seed: int, duration: float, out_path: str) -> int:
    start_ts = time.perf_counter()
    result_holder: dict[str, Any] = {}
    done_event = threading.Event()

    class BenchHandler(http.server.SimpleHTTPRequestHandler):
        def translate_path(self, path: str) -> str:
            clean = path.split("?", 1)[0].split("#", 1)[0]
            if clean == "/game.contract.json":
                return str(REPO_ROOT / "game.contract.json")
            if clean == "/" or clean == "":
                return str(REPO_ROOT / "web" / "index.html")
            return str(REPO_ROOT / "web" / clean.lstrip("/"))

        def do_POST(self) -> None:
            if self.path.split("?", 1)[0] == "/bench-result":
                length = int(self.headers.get("Content-Length", "0"))
                data = json.loads(self.rfile.read(length).decode("utf-8"))
                result_holder["data"] = data
                raw = b'{"ok":true}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
                done_event.set()
                return
            self.send_error(404)

        def log_message(self, format: str, *msg_args: object) -> None:
            pass

    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", 0), BenchHandler)
    port = httpd.server_address[1]
    srv_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    srv_thread.start()

    url = f"http://127.0.0.1:{port}/?bench=1&seed={seed}&duration={duration}"
    browser_bin = find_chromium()
    proc: subprocess.Popen[bytes] | None = None
    vsync_off = False
    tmp_profile = tempfile.mkdtemp(prefix="ddl_bench_")

    try:
        if browser_bin:
            vsync_off = True
            cmd = [
                browser_bin,
                f"--user-data-dir={tmp_profile}",
                "--window-size=1280,720",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-frame-rate-limit",
                "--disable-gpu-vsync",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                f"--app={url}",
            ]
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            webbrowser.open(url)

        timeout_s = max(30.0, duration + 35.0)
        if not done_event.wait(timeout=timeout_s):
            print("Benchmark timed out waiting for browser results.", file=sys.stderr)
            return 1
    finally:
        httpd.shutdown()
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except Exception:
                proc.kill()
        shutil.rmtree(tmp_profile, ignore_errors=True)

    data = result_holder["data"]
    load_ms = int(round(data.get("load_ms", (time.perf_counter() - start_ts) * 1000)))
    output = {
        "contract_version": "1.3",
        "avg_fps": round(float(data["avg_fps"]), 2),
        "p1_low_fps": round(float(data["p1_low_fps"]), 2),
        "frame_ms_p95": round(float(data["frame_ms_p95"]), 2),
        "frames": int(data["frames"]),
        "load_ms": load_ms,
        "peak_mem_mb": data.get("peak_mem_mb", None),
        "vsync_off": bool(vsync_off),
        "renderer": str(data.get("renderer", "Three.js r160 (WebGL2)")),
        "os": f"{platform.system()} {platform.release()} ({platform.machine()})",
    }
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Dao Den Long 3D Benchmark Runner (Contract v1.3)")
    parser.add_argument("--seed", type=int, default=42, help="Benchmark seed (default: 42)")
    parser.add_argument("--duration", type=float, default=30.0, help="Measurement duration in seconds (default: 30)")
    parser.add_argument("--out", type=str, required=True, help="Output bench.json path")
    args = parser.parse_args()
    sys.exit(run_benchmark(args.seed, args.duration, args.out))


if __name__ == "__main__":
    main()
