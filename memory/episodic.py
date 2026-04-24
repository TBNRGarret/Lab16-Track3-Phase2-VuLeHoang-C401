"""Episodic memory: append-only log of past events/outcomes.

Each episode captures a completed task or meaningful turn:
    {ts, topic, summary, outcome, lesson, tags}

Retrieval is keyword-scored (cheap fallback that works without embeddings).
Semantic episodic search can be layered on top via `SemanticMemory`.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


_WORD_RE = re.compile(r"[a-zA-Z0-9_\u00C0-\u1EF9]+", re.UNICODE)


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _WORD_RE.findall(text or "")}


@dataclass
class EpisodicMemory:
    path: str = "data/episodes.json"

    def __post_init__(self) -> None:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        if not os.path.exists(self.path):
            self._write([])

    def _read(self) -> list[dict]:
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write(self, data: list[dict]) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add(
        self,
        topic: str,
        summary: str,
        outcome: str = "",
        lesson: str = "",
        tags: list[str] | None = None,
    ) -> dict:
        episode = {
            "ts": datetime.utcnow().isoformat(timespec="seconds"),
            "topic": topic.strip(),
            "summary": summary.strip(),
            "outcome": outcome.strip(),
            "lesson": lesson.strip(),
            "tags": tags or [],
        }
        data = self._read()
        data.append(episode)
        self._write(data)
        return episode

    def all(self) -> list[dict]:
        return self._read()

    def recent(self, n: int = 5) -> list[dict]:
        return self._read()[-n:]

    def search(self, query: str, k: int = 3) -> list[dict]:
        """Cheap keyword overlap ranking. Returns top-k episodes."""
        q = _tokens(query)
        if not q:
            return []
        scored: list[tuple[float, dict]] = []
        for ep in self._read():
            blob = " ".join(
                [ep["topic"], ep["summary"], ep["outcome"], ep["lesson"], " ".join(ep["tags"])]
            )
            t = _tokens(blob)
            if not t:
                continue
            overlap = len(q & t)
            if overlap == 0:
                continue
            # jaccard-ish score
            score = overlap / (len(q | t) ** 0.5)
            scored.append((score, ep))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [ep for _, ep in scored[:k]]

    def reset(self) -> None:
        self._write([])

    def as_text(self, episodes: list[dict] | None = None) -> str:
        eps = episodes if episodes is not None else self.recent()
        if not eps:
            return "(no relevant episodes)"
        lines = []
        for ep in eps:
            lines.append(
                f"- [{ep['ts']}] {ep['topic']}: {ep['summary']}"
                + (f" | outcome: {ep['outcome']}" if ep["outcome"] else "")
                + (f" | lesson: {ep['lesson']}" if ep["lesson"] else "")
            )
        return "\n".join(lines)
