"""LangGraph wiring: router → retrieve_memory → build_prompt → call_llm → extract_and_save.

The graph is a real `StateGraph` (not skeleton). Four memory backends are
aggregated by the `retrieve_memory` router and injected as structured prompt
sections. Writes happen in `extract_and_save` via an LLM JSON extractor with
robust parse/error handling.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

from dotenv import load_dotenv
from langgraph.graph import END, StateGraph
from openai import OpenAI

from memory import EpisodicMemory, ProfileMemory, SemanticMemory, ShortTermMemory

from .prompts import (
    EXTRACTION_SYSTEM,
    SYSTEM_PROMPT,
    build_final_prompt,
    build_memory_block,
    count_tokens,
)
from .state import MemoryState


load_dotenv()


# =========================================================================
# Agent container
# =========================================================================
@dataclass
class MemoryAgent:
    """Holds the 4 backends + the compiled graph + the OpenAI client."""

    model: str = "gpt-4o-mini"
    extractor_model: str = "gpt-4o-mini"
    memory_budget: int = 400          # tokens reserved for memory block
    short_window: int = 12

    short: ShortTermMemory = field(init=False)
    profile: ProfileMemory = field(init=False)
    episodic: EpisodicMemory = field(init=False)
    semantic: SemanticMemory = field(init=False)
    client: OpenAI = field(init=False)
    graph: Any = field(init=False)

    # Toggles used by benchmarks + ablation.
    use_profile: bool = True
    use_episodic: bool = True
    use_semantic: bool = True
    use_short_term: bool = True
    write_enabled: bool = True

    def __post_init__(self) -> None:
        self.short = ShortTermMemory(max_turns=self.short_window)
        self.profile = ProfileMemory()
        self.episodic = EpisodicMemory()
        self.semantic = SemanticMemory()
        self.client = OpenAI()
        self.graph = build_graph(self)

    # ----- convenience wrappers -----
    def reset_memories(self, keep_semantic_seed: bool = True) -> None:
        self.short.clear()
        self.profile.reset()
        self.episodic.reset()
        if not keep_semantic_seed:
            self.semantic.reset()

    def chat(self, user_input: str, with_memory: bool = True) -> dict:
        state: MemoryState = {
            "user_input": user_input,
            "memory_budget": self.memory_budget if with_memory else 0,
        }
        # toggle memory off for no-memory baseline
        self._with_memory = with_memory
        out = self.graph.invoke(state)
        return out


# =========================================================================
# Node factories (closure over the agent for backend access)
# =========================================================================
def _node_retrieve_memory(agent: "MemoryAgent"):
    def retrieve_memory(state: MemoryState) -> MemoryState:
        if not getattr(agent, "_with_memory", True):
            return {
                **state,
                "user_profile": {},
                "episodes": [],
                "semantic_hits": [],
                "messages": [],
            }
        query = state["user_input"]
        profile = agent.profile.all() if agent.use_profile else {}
        episodes = agent.episodic.search(query, k=3) if agent.use_episodic else []
        semantic_hits = agent.semantic.search(query, k=3) if agent.use_semantic else []
        recent = agent.short.recent(agent.short_window) if agent.use_short_term else []
        return {
            **state,
            "user_profile": profile,
            "episodes": episodes,
            "semantic_hits": semantic_hits,
            "messages": recent,
        }

    return retrieve_memory


def _node_build_prompt(agent: "MemoryAgent"):
    def build_prompt(state: MemoryState) -> MemoryState:
        with_memory = getattr(agent, "_with_memory", True)
        if not with_memory:
            prompt = build_final_prompt(state["user_input"], memory_block="", with_memory=False)
            return {**state, "final_prompt": prompt, "prompt_tokens": count_tokens(prompt)}

        profile_text = agent.profile.as_text()
        episodic_text = agent.episodic.as_text(state.get("episodes") or [])
        semantic_text = agent.semantic.as_text(state.get("semantic_hits") or [])
        recent_text = "\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in state.get("messages") or []
        ) or "(empty)"

        block, _ = build_memory_block(
            profile_text=profile_text,
            episodic_text=episodic_text,
            semantic_text=semantic_text,
            recent_conversation=recent_text,
            budget=state.get("memory_budget", agent.memory_budget),
        )
        prompt = build_final_prompt(state["user_input"], memory_block=block, with_memory=True)
        return {**state, "final_prompt": prompt, "prompt_tokens": count_tokens(prompt)}

    return build_prompt


def _node_call_llm(agent: "MemoryAgent"):
    def call_llm(state: MemoryState) -> MemoryState:
        resp = agent.client.chat.completions.create(
            model=agent.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": state["final_prompt"]},
            ],
            temperature=0.2,
        )
        answer = (resp.choices[0].message.content or "").strip()
        return {**state, "response": answer}

    return call_llm


def _safe_json(s: str) -> dict:
    """Best-effort JSON extraction. Falls back to {} on failure."""
    if not s:
        return {}
    s = s.strip()
    # strip code fences if present
    if s.startswith("```"):
        s = s.strip("`")
        # remove optional language tag
        if s.lower().startswith("json"):
            s = s[4:]
    try:
        return json.loads(s)
    except Exception:
        # try to locate the first {...} block
        start = s.find("{")
        end = s.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(s[start : end + 1])
            except Exception:
                return {}
        return {}


def _node_extract_and_save(agent: "MemoryAgent"):
    def extract_and_save(state: MemoryState) -> MemoryState:
        # Short-term always records the dialog pair (independent of with_memory flag,
        # so the NO-MEMORY baseline stays clean — gated below).
        if getattr(agent, "_with_memory", True) and agent.write_enabled:
            agent.short.add("user", state["user_input"])
            agent.short.add("assistant", state.get("response", ""))
        else:
            return {**state, "memory_updates": {}}

        # LLM-based structured extraction with error handling.
        updates: dict = {}
        try:
            xr = agent.client.chat.completions.create(
                model=agent.extractor_model,
                messages=[
                    {"role": "system", "content": EXTRACTION_SYSTEM},
                    {
                        "role": "user",
                        "content": (
                            "Current profile (for conflict detection):\n"
                            + json.dumps(agent.profile.all(), ensure_ascii=False)
                            + "\n\nUser turn:\n"
                            + state["user_input"]
                            + "\n\nAssistant reply:\n"
                            + state.get("response", "")
                        ),
                    },
                ],
                temperature=0.0,
                response_format={"type": "json_object"},
            )
            raw = xr.choices[0].message.content or "{}"
            updates = _safe_json(raw)
        except Exception as e:
            updates = {"_error": f"extractor_failed: {e}"}

        # ----- apply profile updates (overwrite = conflict resolution) -----
        for k, v in (updates.get("profile_updates") or {}).items():
            if not k:
                continue
            if v is None:
                agent.profile.delete(k)
            else:
                agent.profile.set(str(k), v, source="llm_extractor")

        # ----- write episode if the turn had an outcome -----
        ep = updates.get("episode")
        if isinstance(ep, dict) and ep.get("summary"):
            agent.episodic.add(
                topic=ep.get("topic") or state["user_input"][:60],
                summary=ep.get("summary", ""),
                outcome=ep.get("outcome", ""),
                lesson=ep.get("lesson", ""),
                tags=ep.get("tags") or [],
            )

        # ----- write standalone semantic note -----
        note = updates.get("semantic_note")
        if isinstance(note, str) and note.strip():
            agent.semantic.add(note.strip(), metadata={"source": "turn_extract"})

        return {**state, "memory_updates": updates}

    return extract_and_save


# =========================================================================
# Graph builder
# =========================================================================
def build_graph(agent: "MemoryAgent"):
    g = StateGraph(MemoryState)
    g.add_node("retrieve_memory", _node_retrieve_memory(agent))
    g.add_node("build_prompt", _node_build_prompt(agent))
    g.add_node("call_llm", _node_call_llm(agent))
    g.add_node("extract_and_save", _node_extract_and_save(agent))

    g.set_entry_point("retrieve_memory")
    g.add_edge("retrieve_memory", "build_prompt")
    g.add_edge("build_prompt", "call_llm")
    g.add_edge("call_llm", "extract_and_save")
    g.add_edge("extract_and_save", END)
    return g.compile()
