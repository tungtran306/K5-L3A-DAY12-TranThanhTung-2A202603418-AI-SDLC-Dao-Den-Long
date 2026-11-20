"""Local HTTP server for playing Dao Den Long (3D Web) on Windows, macOS, and Linux."""

from __future__ import annotations

import argparse
import functools
import http.server
import socketserver
import threading
import webbrowser
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve Dao Den Long 3D Web Game")
    parser.add_argument("--port", type=int, default=8000, help="HTTP port (default: 8000)")
    parser.add_argument("--no-browser", action="store_true", help="Do not auto-open browser")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent

    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def translate_path(self, path: str) -> str:
            # Serve /game.contract.json from repo root, everything else from web/
            clean = path.split("?", 1)[0].split("#", 1)[0]
            if clean == "/game.contract.json":
                return str(repo_root / "game.contract.json")
            if clean == "/" or clean == "":
                return str(repo_root / "web" / "index.html")
            return str(repo_root / "web" / clean.lstrip("/"))

        def log_message(self, format: str, *msg_args: object) -> None:
            pass

    handler = functools.partial(QuietHandler)
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
