"""Package a clean runnable release archive (dist/dao-den-long-v1.0.0.zip) for GitHub Release v1.0.0."""

from __future__ import annotations

import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DIST_ZIP = REPO_ROOT / "dist" / "dao-den-long-v1.0.0.zip"
INCLUDE_FILES = [
    "game.contract.json",
    "README.md",
    "LICENSE",
    "CREDITS.md",
    "CHANGELOG.md",
]
INCLUDE_DIRS = ["src", "web"]


def main() -> None:
    DIST_ZIP.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(DIST_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel in INCLUDE_FILES:
            p = REPO_ROOT / rel
            if p.is_file():
                zf.write(p, f"dao-den-long-v1.0.0/{rel}")
        for d in INCLUDE_DIRS:
            base = REPO_ROOT / d
            for f in sorted(base.rglob("*")):
                if f.is_file() and "__pycache__" not in f.parts and not f.name.endswith(".pyc"):
                    rel = f.relative_to(REPO_ROOT).as_posix()
                    zf.write(f, f"dao-den-long-v1.0.0/{rel}")
    print(f"Created release bundle: {DIST_ZIP} ({DIST_ZIP.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
