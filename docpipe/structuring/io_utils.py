from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def append_empty_page(log_path: Path, page_dir: str) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    existing = set()
    if log_path.exists():
        existing = {line.strip() for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()}
    if page_dir not in existing:
        with log_path.open("a", encoding="utf-8") as file:
            file.write(page_dir + "\n")

