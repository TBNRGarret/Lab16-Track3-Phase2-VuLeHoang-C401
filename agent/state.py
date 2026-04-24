"""Typed state flowing through the LangGraph."""

from __future__ import annotations

from typing import TypedDict, List, Dict, Any


class MemoryState(TypedDict, total=False):
    # input
    user_input: str

    # short-term view (rolling window of dialog)
    messages: List[Dict[str, str]]

    # retrieved memory (router aggregates here)
    user_profile: Dict[str, Any]
    episodes: List[Dict[str, Any]]
    semantic_hits: List[Dict[str, Any]]

    # budget + assembled prompt
    memory_budget: int            # max tokens for memory block
    final_prompt: str
    prompt_tokens: int

    # model output
    response: str

    # extracted writes
    memory_updates: Dict[str, Any]
