"""Long-term profile memory: JSON-backed key-value store.

Designed for stable facts about the user (name, allergies, preferences, goals).
`set` OVERWRITES existing keys — that is the conflict-resolution policy:
the newest fact always wins. Old value is preserved in `_history` for audit.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ProfileMemory:
    path: str = "data/profile.json"

    def __post_init__(self) -> None:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        if not os.path.exists(self.path):
            self._write({"facts": {}, "_history": []})

    # ---------- low-level IO ----------
    def _read(self) -> dict:
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write(self, data: dict) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ---------- public API ----------
    def get(self, key: str, default: Any = None) -> Any:
        return self._read()["facts"].get(key, default)

    def all(self) -> dict:
        return dict(self._read()["facts"])

    def set(self, key: str, value: Any, source: str = "user") -> None:
        """Overwrite key. Records previous value in `_history` for auditability."""
        data = self._read()
        prev = data["facts"].get(key)
        if prev == value:
            return  # no-op, avoid history spam
        data["facts"][key] = value
        data["_history"].append(
            {
                "ts": datetime.utcnow().isoformat(timespec="seconds"),
                "key": key,
                "old": prev,
                "new": value,
                "source": source,
            }
        )
        self._write(data)

    def delete(self, key: str) -> bool:
        data = self._read()
        if key not in data["facts"]:
            return False
        old = data["facts"].pop(key)
        data["_history"].append(
            {
                "ts": datetime.utcnow().isoformat(timespec="seconds"),
                "key": key,
                "old": old,
                "new": None,
                "source": "deletion",
            }
        )
        self._write(data)
        return True

    def history(self, key: str | None = None) -> list[dict]:
        hist = self._read()["_history"]
        if key is None:
            return hist
        return [h for h in hist if h["key"] == key]

    def reset(self) -> None:
        self._write({"facts": {}, "_history": []})

    def as_text(self) -> str:
        facts = self.all()
        if not facts:
            return "(no profile facts)"
        return "\n".join(f"- {k}: {v}" for k, v in sorted(facts.items()))
