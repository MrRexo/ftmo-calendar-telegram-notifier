from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class NotificationState:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.data: dict[str, Any] = {"sent": {}}
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict) and isinstance(loaded.get("sent"), dict):
                self.data = loaded
        except (OSError, json.JSONDecodeError):
            self.data = {"sent": {}}

    def was_sent(self, key: str) -> bool:
        return key in self.data["sent"]

    def mark_sent(self, key: str, sent_at: str) -> None:
        self.data["sent"][key] = sent_at
        self._save()

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.path)
