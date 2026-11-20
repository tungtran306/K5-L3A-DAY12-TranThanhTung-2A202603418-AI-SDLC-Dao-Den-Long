"""Local HTTP server & leaderboard CLI for Dao Den Long (Windows, macOS, Linux)."""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import socketserver
import sys
import threading
import webbrowser
from pathlib import Path

from src.leaderboard import add_entry, export_leaderboard, load_entries


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Serve Dao Den Long 3D Web Game")
    parser.add_argument("--port", type=int, default=8000, help="HTTP port (default: 8000)")
    parser.add_argument("--no-browser", action="store_true", help="Do not auto-open browser")
    parser.add_argument("--export-leaderboard", type=str, default=None, help="Export leaderboard JSON and exit")
    args = parser.parse_args(argv)

    if args.export_leaderboard is not None:
        export_leaderboard(args.export_leaderboard)
        print(f"Exported leaderboard to {args.export_leaderboard}")
        sys.exit(0)

    repo_root = Path(__file__).resolve().parent.parent

    class GameHandler(http.server.SimpleHTTPRequestHandler):
        def translate_path(self, path: str) -> str:
            clean = path.split("?", 1)[0].split("#", 1)[0]
            if clean == "/game.contract.json":
                return str(repo_root / "game.contract.json")
            if clean == "/" or clean == "":
                return str(repo_root / "web" / "index.html")
            return str(repo_root / "web" / clean.lstrip("/"))

        def _send_json(self, code: int, obj: object) -> None:
            raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self) -> None:
            clean = self.path.split("?", 1)[0]
            if clean == "/api/leaderboard":
                self._send_json(200, {"entries": load_entries()})
                return
            super().do_GET()

        def do_POST(self) -> None:
            clean = self.path.split("?", 1)[0]
            if clean == "/api/leaderboard":
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length).decode("utf-8")
                try:
                    data = json.loads(body)
                    entries = add_entry(
                        name=str(data.get("name", "")),
                        score=int(data.get("score", 0)),
                        nights_won=int(data.get("nights_won", 0)),
                        seed=int(data.get("seed", 42)),
                    )
                    self._send_json(200, {"entries": entries})
                except Exception as exc:
                    self._send_json(400, {"error": str(exc)})
                return
            self.send_error(404)

        def log_message(self, format: str, *msg_args: object) -> None:
            pass

    handler = functools.partial(GameHandler)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", args.port), handler) as httpd:
        url = f"http://127.0.0.1:{args.port}/"
        print(f"Dao Den Long 3D running at {url} (Ctrl+C to stop)")
        if not args.no_browser:
            threading.Timer(0.4, lambda: webbrowser.open(url)).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    main()
