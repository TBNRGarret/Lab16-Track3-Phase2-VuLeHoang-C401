# Lab #17 — Reflection: Privacy, Limitations & Failure Modes

## 1. Which memory helped the agent the most?

Looking at the benchmark (`BENCHMARK.md`), **profile memory** was the single biggest
lift: scenarios 1, 6, 7 and 10 were **unanswerable without it** (no-memory returns
`[tên của bạn]` or `Xin lỗi, nhưng tôi không có thông tin ...`). Profile memory is
small, cheap, and survives token trimming — exactly the shape needed for
personalization.

**Semantic memory** came second: scenarios 4, 5, 8 went from generic guesses to
grounded answers with concrete numbers (`30 days`, `15 minutes`, `before 14:00`).
The no-memory baseline could *guess plausibly* from pretraining but was wrong in
specifics — which is the worst failure mode for a real product (confident wrong
answers).

**Episodic memory** was decisive for scenario 3 (docker lesson) and scenario 8
(shipping replay). Short-term buffer matters mostly during the active
conversation; it does not survive across sessions on its own.

## 2. Which memory is the riskiest if retrieved incorrectly?

**Profile memory** is the most dangerous. A stale or wrongly-extracted profile
fact (e.g. wrong allergy) gets injected into every subsequent prompt and can
harm the user directly (medical/allergy advice, identity confusion). This is why
we:

- Always log the previous value into `_history` so resets are auditable.
- Explicitly tell the LLM extractor that `null` means "forget", never
  "correction" — corrections must emit the new value.
- Tell the generation model in the system prompt that a **user's current
  message beats the profile section** if they conflict. Without that rule, the
  model sometimes echoes the stale profile value (we observed this in
  development and fixed it).

**Semantic memory** is second-most risky: because retrieval is similarity-based,
it is perfectly capable of fetching the *wrong* FAQ chunk with high confidence.
A chunk about "14-day opened electronics returns" can be surfaced for a
question about "unopened items" and the model will happily use it.
Mitigations in this project:

- Keep chunks small and topically narrow (so distances are meaningful).
- Include `source` / `topic` metadata and show it in the injected block, so
  the model can discount an off-topic hit.
- Use cosine space (`hnsw:space: cosine`) and only top-k=3 to limit noise.

**Episodic memory** risk is subtler: a lesson from one project can be
mis-applied to another (e.g. the Docker fix above would be wrong for a K8s
issue). Keyword overlap ranking makes this worse than embedding-based
retrieval. In production we would promote episodic to vectors with project/user
scoping.

**Short-term** is the least risky for privacy (ephemeral by design) but the
most fragile under long inputs: scenario 10 specifically stresses this.
Short-term alone would have dropped the user's name after one long message;
profile memory saved the turn.

## 3. PII exposure & privacy risks

The profile store in `data/profile.json` is **plain JSON on disk**. Even in this
small demo it accumulates:

- Names (`name: Linh`)
- Medical data (`allergy: đậu nành`) — sensitive category under GDPR Art. 9.
- Employment (`job_title: data engineer`)
- Sometimes freeform notes written by the extractor.

Episodic memory is equally sensitive when extracted from real conversations,
because episodes include the context around a decision (who, where, when).

Concrete risks:

1. **No encryption at rest.** Anyone with filesystem access reads all PII.
2. **No per-user scoping.** The demo uses a single global profile file. In
   production every collection/key must be namespaced by `user_id`.
3. **LLM-based extraction leaks to a third party.** Every turn is sent to
   OpenAI. Even if the user asks "delete my data", past payloads may have been
   retained upstream outside our control.
4. **Retrieval-time leakage.** Because the memory block is injected into the
   prompt, any PII in profile/episodic is **sent to the model on every turn**,
   even when the current question would not normally require it.

## 4. Deletion / TTL / consent

Design implications for production (the demo does not fully implement all of
these — noted as limitations):

| Memory | Where deletion must happen | TTL suggestion |
|---|---|---|
| Short-term | Drop the in-memory `deque`; nothing persists. | Per-session only. |
| Profile | `profile.delete(key)` + audit row; erase `_history` on full GDPR delete. | Stable facts: keep until user revokes. |
| Episodic | `episodes.json` rows; also delete the file when the user asks. | 90-day rolling is a reasonable default. |
| Semantic | `chromadb.delete(ids=[...])` filtered by `user_id` metadata; and re-seed. | Facts: keep. User-derived notes: 180 days. |

Consent: the extractor silently writes "stable facts" that the user never
explicitly flagged as durable. A production agent should:

1. Ask before persisting sensitive facts ("Shall I remember that you are
   allergic to soy?") — **write-confirmation UX**.
2. Surface a "what do you remember about me?" command that reads from all four
   stores.
3. Provide a one-shot "forget everything" that deletes from every backend,
   including vector store.

## 5. Technical limitations of this solution

1. **Global (single-user) scope.** All four backends lack a `user_id`
   namespace. Adding multi-tenant support means metadata filters on Chroma,
   prefix keys on the profile JSON, and sharded episode files.
2. **Extractor race conditions.** The extractor runs *after* the LLM reply. A
   profile update from turn N is only visible for turn N+1. If the user
   immediately relies on it (same turn), we must refactor to a pre-reply
   extraction pass — at the cost of an extra LLM call per turn.
3. **Keyword-based episodic retrieval.** Works for short-term Vietnamese/English
   keywords but breaks under paraphrase. Upgrade path: embed episodes into the
   same Chroma collection with a `type=episode` metadata tag.
4. **No eviction policy.** The profile will grow unbounded. We should cap N
   facts with an LRU policy and archive older ones into episodic.
5. **JSON file locking.** Concurrent writes on Windows will corrupt
   `profile.json`. Fix: switch to SQLite or Redis (`set` atomic by key).
6. **Token budget is static.** We hard-split 30/25/25/20% across profile /
   episodic / semantic / recent. A router that dynamically allocates based on
   retrieval confidence would reduce prompt cost further.
7. **Extraction errors silently swallow turns.** `_safe_json` returns `{}` when
   parsing fails; we log but do not retry. For real workloads we should:
   retry once with an explicit "return JSON only" nudge, and route repeated
   failures to a dead-letter log.
8. **Scale bottleneck.** The extractor plus the generation call double the
   latency and cost per turn. At 1000 RPS this is unsustainable — production
   needs async batched extraction and a background "reflection" job rather
   than per-turn writes.
9. **No PII redaction before embedding.** Semantic notes written by the
   extractor can contain names and are embedded into Chroma unmodified. A
   redaction step (e.g. spaCy/PII NER) should run before writes.

## 6. What would make this system fail in production?

- **Cross-user retrieval** if `user_id` filters are missing — a classic data
  leak. Highest-severity failure.
- **Extractor hallucinating "stable facts"** from casual phrases
  ("I hate Mondays" → `mood: hate_mondays`). Over time the profile accumulates
  garbage that pollutes every prompt. Mitigation: confidence threshold + user
  confirmation before persisting.
- **Conflict ping-pong** where the user and extractor disagree on a
  correction and the value flips between turns. Our `_history` log makes this
  debuggable but not auto-stable. A proper fix requires a "last user
  confirmation wins" rule.
- **Vector drift.** As FAQ content is updated but old chunks are not
  invalidated, retrieval returns outdated knowledge. Needs a versioned
  `effective_to` metadata and filtered queries.
