"""Run 10 multi-turn benchmark scenarios twice (no-memory vs with-memory).

Emits:
    benchmark/results.json   — raw per-turn transcripts + token counts
    BENCHMARK.md             — human-readable table + details

Usage:
    python benchmark/run_benchmark.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from agent import MemoryAgent
from benchmark.conversations import SCENARIOS, Scenario
from benchmark.seed_semantic import seed


ROOT = Path(__file__).resolve().parent.parent
RESULTS_PATH = ROOT / "benchmark" / "results.json"
MARKDOWN_PATH = ROOT / "BENCHMARK.md"


def run_scenario(agent: MemoryAgent, sc: Scenario, with_memory: bool) -> dict:
    """Run all turns of a scenario; return probe turn details."""
    agent.reset_memories()
    agent._with_memory = with_memory  # noqa: SLF001 (needed for retrieval gating)
    turns_log = []
    probe_idx = sc.probe_index if sc.probe_index >= 0 else len(sc.turns) - 1
    probe_response = ""
    probe_tokens = 0
    for i, user_msg in enumerate(sc.turns):
        t0 = time.time()
        out = agent.chat(user_msg, with_memory=with_memory)
        dt = time.time() - t0
        turns_log.append(
            {
                "i": i,
                "user": user_msg[:200],
                "response": (out.get("response") or "")[:500],
                "prompt_tokens": out.get("prompt_tokens", 0),
                "latency_s": round(dt, 2),
            }
        )
        if i == probe_idx:
            probe_response = out.get("response", "")
            probe_tokens = out.get("prompt_tokens", 0)

    def _contains_any(text: str, needles: list[str]) -> bool:
        t = text.lower()
        return any(n.lower() in t for n in needles)

    passed = True
    reasons: list[str] = []
    if sc.expected_keywords and not _contains_any(probe_response, sc.expected_keywords):
        passed = False
        reasons.append(f"missing expected keyword(s): {sc.expected_keywords}")
    if sc.must_not_contain and _contains_any(probe_response, sc.must_not_contain):
        passed = False
        reasons.append(f"contains forbidden phrase(s): {sc.must_not_contain}")

    return {
        "scenario_id": sc.id,
        "category": sc.category,
        "title": sc.title,
        "with_memory": with_memory,
        "probe_index": probe_idx,
        "probe_response": probe_response,
        "probe_prompt_tokens": probe_tokens,
        "pass": passed,
        "fail_reasons": reasons,
        "turns": turns_log,
    }


def main() -> None:
    agent = MemoryAgent()
    print("[seed] resetting + seeding semantic memory (via agent) ...")
    seed(agent.semantic)

    results: list[dict] = []
    for sc in SCENARIOS:
        for with_mem in (False, True):
            tag = "with" if with_mem else "no"
            print(f"\n=== Scenario {sc.id} [{sc.category}] — {tag}-memory ===")
            r = run_scenario(agent, sc, with_memory=with_mem)
            results.append(r)
            status = "PASS" if r["pass"] else "FAIL"
            print(f"  -> {status} | probe tokens={r['probe_prompt_tokens']}")
            print(f"  -> response: {r['probe_response'][:180]}")
            # re-seed semantic between runs to keep FAQ clean + drop any
            # semantic_notes the extractor wrote during the scenario.
            seed(agent.semantic)

    # ----- persist raw -----
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # ----- emit markdown report -----
    write_markdown(results)
    print(f"\nDone. Wrote {RESULTS_PATH} and {MARKDOWN_PATH}")


def write_markdown(results: list[dict]) -> None:
    by_id: dict[int, dict] = {}
    for r in results:
        key = r["scenario_id"]
        by_id.setdefault(key, {})[r["with_memory"]] = r

    sc_by_id = {s.id: s for s in SCENARIOS}

    lines: list[str] = []
    lines.append("# Lab #17 — Benchmark Report\n")
    lines.append(
        "10 multi-turn conversations, each run twice: **no-memory baseline** vs "
        "**with-memory (4-stack LangGraph agent)**.\n"
    )
    lines.append(
        "Token counts are exact (tiktoken `cl100k_base`) on the probe turn's final prompt. "
        "Latency is wall-clock from `chat()` invocation and includes OpenAI round-trips.\n"
    )

    # Summary table
    lines.append("## Summary\n")
    lines.append("| # | Scenario | Category | No-memory | With-memory | Pass? |")
    lines.append("|---|----------|----------|-----------|-------------|-------|")
    pass_with = 0
    pass_no = 0
    tok_no_total = 0
    tok_with_total = 0
    for sid in sorted(by_id):
        sc = sc_by_id[sid]
        rn = by_id[sid][False]
        rw = by_id[sid][True]
        resp_no = rn["probe_response"].replace("\n", " ")[:90] + (
            "…" if len(rn["probe_response"]) > 90 else ""
        )
        resp_w = rw["probe_response"].replace("\n", " ")[:90] + (
            "…" if len(rw["probe_response"]) > 90 else ""
        )
        flag = "✅" if rw["pass"] else "❌"
        lines.append(
            f"| {sid} | {sc.title} | {sc.category} | {resp_no} | {resp_w} | {flag} |"
        )
        if rw["pass"]:
            pass_with += 1
        if rn["pass"]:
            pass_no += 1
        tok_no_total += rn["probe_prompt_tokens"]
        tok_with_total += rw["probe_prompt_tokens"]

    lines.append("")
    lines.append("## Aggregate\n")
    lines.append(f"- With-memory pass rate: **{pass_with}/{len(by_id)}**")
    lines.append(f"- No-memory pass rate:   **{pass_no}/{len(by_id)}**")
    lines.append(
        f"- Probe-turn token totals: no-memory={tok_no_total}, with-memory={tok_with_total} "
        f"(Δ={tok_with_total - tok_no_total}). Memory adds prompt tokens but recovers answers "
        f"the baseline cannot produce."
    )
    lines.append("")

    # Details
    lines.append("## Details per scenario\n")
    for sid in sorted(by_id):
        sc = sc_by_id[sid]
        rn = by_id[sid][False]
        rw = by_id[sid][True]
        lines.append(f"### Scenario {sid} — {sc.title}")
        lines.append(f"*Category:* `{sc.category}`  |  *Probe turn:* #{rn['probe_index'] + 1} / {len(sc.turns)}\n")
        if sc.notes:
            lines.append(f"> Note: {sc.notes}\n")
        lines.append("**Turn-by-turn (user input):**")
        for i, t in enumerate(sc.turns):
            lines.append(f"{i+1}. {t[:200]}" + ("…" if len(t) > 200 else ""))
        lines.append("")
        lines.append("**Probe answers:**\n")
        lines.append(f"- **No-memory:** {rn['probe_response']}")
        lines.append(f"- **With-memory:** {rw['probe_response']}\n")
        lines.append(
            f"**Tokens (probe prompt):** no-mem={rn['probe_prompt_tokens']}, "
            f"with-mem={rw['probe_prompt_tokens']}"
        )
        verdict = "PASS" if rw["pass"] else "FAIL"
        lines.append(f"\n**Verdict (with-memory):** {verdict}")
        if rw["fail_reasons"]:
            lines.append(f"*Reasons:* {'; '.join(rw['fail_reasons'])}")
        lines.append("")

    with open(MARKDOWN_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
