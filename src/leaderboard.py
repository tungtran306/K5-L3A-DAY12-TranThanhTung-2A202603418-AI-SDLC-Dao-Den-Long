"""Local persistent Top-10 leaderboard storage & export for Dao Den Long (Ticket-04)."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LB_PATH = REPO_ROOT / "data" / "leaderboard.json"
# Allows ASCII [A-Za-z0-9_] plus Vietnamese Unicode letters, 3-12 chars
NAME_RE = re.compile(r"^[\wÀ-ỹ]{3,12}$", re.UNICODE)


def load_entries(path: Path = DEFAULT_LB_PATH) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        entries = data.get("entries", []) if isinstance(data, dict) else []
        return _sort_and_trim(entries)
    except Exception:
        return []


def _sort_and_trim(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Sort by score descending; ties broken by earlier achieved_at first
    cleaned = [e for e in entries if isinstance(e, dict) and "name" in e and "score" in e]
    cleaned.sort(key=lambda e: (-int(e.get("score", 0)), str(e.get("achieved_at", ""))))
    return cleaned[:10]


def save_entries(entries: list[dict[str, Any]], path: Path = DEFAULT_LB_PATH) -> list[dict[str, Any]]:
    sorted_entries = _sort_and_trim(entries)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"entries": sorted_entries}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return sorted_entries


def add_entry(
    *,
    name: str,
    score: int,
    nights_won: int,
    seed: int = 42,
    achieved_at: str | None = None,
    path: Path = DEFAULT_LB_PATH,
) -> list[dict[str, Any]]:
    name = name.strip()
    if not NAME_RE.match(name):
        raise ValueError("Tên phải dài 3–12 ký tự ([A-Za-z0-9_] hoặc chữ tiếng Việt có dấu).")
    nights_won = max(0, min(3, int(nights_won)))
    if achieved_at is None:
        achieved_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    entry = {
        "name": name,
        "score": int(score),
        "nights_won": nights_won,
        "achieved_at": achieved_at,
        "seed": int(seed),
    }
    entries = load_entries(path)
    entries.append(entry)
    return save_entries(entries, path)


def export_leaderboard(out_path: str | Path, path: Path = DEFAULT_LB_PATH) -> None:
    entries = load_entries(path)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"entries": entries}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
