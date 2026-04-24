"""Prompt templates + token-aware trimming."""

from __future__ import annotations

from typing import Iterable

import tiktoken


_ENC = tiktoken.get_encoding("cl100k_base")


SYSTEM_PROMPT = (
    "You are a helpful assistant with structured long-term memory.\n"
    "Rules:\n"
    "1. Always prefer the MOST RECENT fact. If the user's CURRENT message corrects "
    "or updates a fact that appears in the profile section, the user's current "
    "message wins — acknowledge the correction and use the new value in your reply.\n"
    "2. Never restate outdated facts as if they were still true after a correction.\n"
    "3. Answer concisely in the user's language."
)


def count_tokens(text: str) -> int:
    if not text:
        return 0
    return len(_ENC.encode(text))


def trim_to_budget(text: str, max_tokens: int) -> str:
    """Truncate `text` to the last `max_tokens` tokens (keep the tail)."""
    if max_tokens <= 0 or not text:
        return ""
    ids = _ENC.encode(text)
    if len(ids) <= max_tokens:
        return text
    return _ENC.decode(ids[-max_tokens:])


def build_memory_block(
    profile_text: str,
    episodic_text: str,
    semantic_text: str,
    recent_conversation: str,
    budget: int,
) -> tuple[str, int]:
    """Assemble the memory section with clear headings and a token budget.

    Budget is split: profile 30%, episodic 25%, semantic 25%, recent 20%.
    """
    shares = {
        "profile": max(80, int(budget * 0.30)),
        "episodic": max(60, int(budget * 0.25)),
        "semantic": max(60, int(budget * 0.25)),
        "recent": max(60, int(budget * 0.20)),
    }
    parts = [
        ("## User Profile (long-term facts — newest wins)", trim_to_budget(profile_text, shares["profile"])),
        ("## Relevant Past Episodes", trim_to_budget(episodic_text, shares["episodic"])),
        ("## Retrieved Knowledge (semantic)", trim_to_budget(semantic_text, shares["semantic"])),
        ("## Recent Conversation", trim_to_budget(recent_conversation, shares["recent"])),
    ]
    block = "\n\n".join(f"{h}\n{body}" for h, body in parts)
    return block, count_tokens(block)


def build_final_prompt(user_input: str, memory_block: str, with_memory: bool) -> str:
    if not with_memory:
        return f"User question: {user_input}\nAnswer:"
    return (
        f"{memory_block}\n\n"
        f"## Current User Message\n{user_input}\n\n"
        f"Answer using the memory above when relevant. "
        f"Do not invent facts that are not in the memory or the user's message."
    )


EXTRACTION_SYSTEM = (
    "You extract durable memory updates from a single user turn. "
    "Return STRICT JSON matching this schema:\n"
    "{\n"
    '  "profile_updates": {"<snake_case_key>": "<value or null to delete>"},\n'
    '  "episode": {"topic": str, "summary": str, "outcome": str, "lesson": str, "tags": [str]} | null,\n'
    '  "semantic_note": str | null\n'
    "}\n"
    "Rules:\n"
    "- profile_updates: ONLY stable personal facts (name, allergies, language, city, job, "
    "preferences, goals). \n"
    "- CORRECTION HANDLING: if the user corrects an earlier fact (e.g. 'nhầm', 'actually', "
    "'sorry I meant', 'không phải X mà là Y'), emit the NEW value. NEVER use null for "
    "corrections — the store overwrites automatically.\n"
    "- Use null ONLY when the user explicitly asks to forget/erase (e.g. 'quên đi', "
    "'delete my allergy', 'I no longer have that allergy').\n"
    "- episode: fill ONLY when the turn completes a task or reveals a reusable lesson; else null.\n"
    "- semantic_note: a standalone factual snippet worth recalling later (docs, preferences context); else null.\n"
    "- Use snake_case, singular keys (e.g. allergy, favorite_food, job_title).\n"
    "- Output JSON only, no markdown."
)
