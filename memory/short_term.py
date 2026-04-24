"""Short-term memory: sliding-window conversation buffer.

Keeps only the last N turns to bound prompt size. Role-aware so the graph
can reconstruct a clean dialog view for the model.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Iterable, Literal


Role = Literal["user", "assistant", "system"]


@dataclass
class ShortTermMemory:
    """In-memory conversation buffer with a hard turn cap."""

    max_turns: int = 12
    _buffer: Deque[dict] = field(default_factory=deque, init=False)

    def add(self, role: Role, content: str) -> None:
        self._buffer.append({"role": role, "content": content})
        # one "turn" = one message; trim from the head
        while len(self._buffer) > self.max_turns:
            self._buffer.popleft()

    def extend(self, messages: Iterable[dict]) -> None:
        for m in messages:
            self.add(m["role"], m["content"])

    def recent(self, n: int | None = None) -> list[dict]:
        if n is None:
            return list(self._buffer)
        if n <= 0:
            return []
        return list(self._buffer)[-n:]

    def as_text(self, n: int | None = None) -> str:
        msgs = self.recent(n)
        return "\n".join(f"{m['role'].upper()}: {m['content']}" for m in msgs)

    def clear(self) -> None:
        self._buffer.clear()

    def __len__(self) -> int:
        return len(self._buffer)
