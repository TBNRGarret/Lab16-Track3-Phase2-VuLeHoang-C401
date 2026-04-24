"""Seed the semantic memory with a few FAQ-style chunks for the benchmark."""

from __future__ import annotations

from memory import SemanticMemory


FAQ_CHUNKS = [
    (
        "To resolve 'connection refused' between Docker containers, use the "
        "docker-compose service name as the hostname instead of localhost, "
        "because each container has its own loopback network.",
        {"source": "faq", "topic": "docker"},
    ),
    (
        "Our return policy: customers may return any unused item within 30 "
        "days of purchase for a full refund. Opened electronics must be "
        "returned within 14 days.",
        {"source": "faq", "topic": "returns"},
    ),
    (
        "Shipping: standard delivery is 3-5 business days inside Vietnam. "
        "Express delivery in Hanoi and HCMC arrives next business day if "
        "ordered before 14:00.",
        {"source": "faq", "topic": "shipping"},
    ),
    (
        "To reset your password, open Settings → Security → Reset Password. "
        "A reset link will be emailed to the address on file and expires in 15 minutes.",
        {"source": "faq", "topic": "account"},
    ),
    (
        "Our premium membership costs 99,000 VND/month and includes free "
        "express shipping, early sale access, and 5% cashback on all orders.",
        {"source": "faq", "topic": "membership"},
    ),
    (
        "Python's asyncio.gather runs coroutines concurrently; if one raises, "
        "others keep running unless you pass return_exceptions=False (default).",
        {"source": "faq", "topic": "python"},
    ),
]


def seed(sem: SemanticMemory | None = None) -> SemanticMemory:
    """Reset the given SemanticMemory (or a fresh one) and load FAQ chunks.

    Pass the agent's own `agent.semantic` to ensure the reset is visible to
    the agent — fresh `SemanticMemory()` instances reset the same backing
    collection, but the agent's cached `_collection` handle would become stale.
    """
    sem = sem or SemanticMemory()
    sem.reset()
    texts = [t for t, _ in FAQ_CHUNKS]
    metas = [m for _, m in FAQ_CHUNKS]
    sem.add_many(texts, metas)
    return sem


if __name__ == "__main__":
    s = seed()
    print(f"Seeded {s.count()} semantic chunks.")
