"""10 multi-turn benchmark conversations for Lab #17.

Each scenario has:
    id, category, turns (list of user messages in order),
    probe_turn_index (which turn tests memory; -1 = last),
    expected_keywords (pass if any appear in the response),
    must_not_contain (optional: fail if any appear)

Categories covered (per rubric):
    - profile recall
    - conflict update
    - episodic recall
    - semantic retrieval
    - trim / token budget stress
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class Scenario:
    id: int
    category: str
    title: str
    turns: List[str]
    probe_index: int = -1
    expected_keywords: List[str] = field(default_factory=list)
    must_not_contain: List[str] = field(default_factory=list)
    notes: str = ""


SCENARIOS: list[Scenario] = [
    Scenario(
        id=1,
        category="profile_recall",
        title="Recall user name after 6 turns",
        turns=[
            "Xin chào, tôi tên là Linh.",
            "Hôm nay Hà Nội có mưa phùn.",
            "Tôi đang học về agent memory.",
            "Bạn có thể giải thích RAG không?",
            "Cảm ơn, nghe có vẻ thú vị.",
            "Tôi sẽ thử cài LangGraph tối nay.",
            "Nhắc lại giúp tôi: tên tôi là gì?",
        ],
        expected_keywords=["Linh"],
        must_not_contain=["không biết", "chưa rõ"],
    ),
    Scenario(
        id=2,
        category="conflict_update",
        title="Allergy correction (rubric mandatory)",
        turns=[
            "Tôi tên Mai, tôi dị ứng sữa bò.",
            "Hôm qua tôi uống trà sữa xong bị khó chịu.",
            "À nhầm, tôi dị ứng đậu nành chứ không phải sữa bò.",
            "Bạn gợi ý giúp tôi món ăn tối phù hợp được không?",
        ],
        expected_keywords=["đậu nành"],
        must_not_contain=["sữa bò"],
    ),
    Scenario(
        id=3,
        category="episodic_recall",
        title="Recall debug lesson about docker networking",
        turns=[
            "Hôm qua tôi debug được lỗi connection refused giữa 2 container docker.",
            "Hóa ra cần dùng tên service trong docker-compose thay vì localhost.",
            "Bây giờ lại gặp lỗi tương tự, bạn gợi ý cho tôi xem lại gì?",
        ],
        expected_keywords=["service", "docker", "compose"],
    ),
    Scenario(
        id=4,
        category="semantic_retrieval",
        title="Retrieve FAQ chunk about returns",
        turns=[
            "Tôi là khách mới, muốn hỏi về chính sách đổi trả.",
            "Nếu sản phẩm còn nguyên hộp thì tôi có bao nhiêu ngày để trả?",
        ],
        expected_keywords=["30"],
    ),
    Scenario(
        id=5,
        category="semantic_retrieval",
        title="Retrieve FAQ about password reset",
        turns=[
            "Tôi quên mật khẩu đăng nhập.",
            "Làm cách nào để reset password?",
        ],
        expected_keywords=["Settings", "reset", "email"],
    ),
    Scenario(
        id=6,
        category="profile_recall",
        title="Preferred language after small talk",
        turns=[
            "Hi, my preferred language is Vietnamese.",
            "Let's talk about the weather in Hanoi.",
            "Rainy today, pretty cold.",
            "Câu hỏi tiếp theo: dùng ngôn ngữ tôi thích để tóm tắt cuộc trò chuyện.",
        ],
        expected_keywords=["Hà Nội", "thời tiết"],
    ),
    Scenario(
        id=7,
        category="conflict_update",
        title="Job role correction",
        turns=[
            "Tôi làm backend engineer tại một startup fintech.",
            "Dự án hiện tại của tôi là một payment gateway.",
            "Thực ra tôi mới chuyển sang làm data engineer từ tuần trước.",
            "Job hiện tại của tôi là gì?",
        ],
        expected_keywords=["data"],
        must_not_contain=["backend"],
    ),
    Scenario(
        id=8,
        category="episodic_recall",
        title="Reuse previous outcome (shipping)",
        turns=[
            "Lần trước tôi đặt hàng ở HCMC ngày 10, ngày 11 nhận được vì chọn express.",
            "Kỳ này tôi lại cần gấp, có cách nào tương tự không?",
        ],
        expected_keywords=["express", "next"],
    ),
    Scenario(
        id=9,
        category="semantic_retrieval",
        title="Python asyncio behavior",
        turns=[
            "Tôi đang học asyncio.",
            "Khi gọi asyncio.gather mà một coroutine lỗi thì các coroutine còn lại sao?",
        ],
        expected_keywords=["return_exceptions"],
    ),
    Scenario(
        id=10,
        category="trim_budget",
        title="Token budget: recall name after very long chat",
        turns=[
            "Tôi tên Trang, rất vui gặp bạn.",
            "Để tôi kể: " + ("Lorem ipsum dolor sit amet. " * 40),
            "Và một đoạn dài nữa: " + ("Phân tích chi tiết dự án A có rất nhiều số liệu dài dòng. " * 30),
            "Thêm background: " + ("Tôi từng làm ở nhiều công ty khác nhau trong 10 năm qua. " * 25),
            "Bây giờ: tên tôi là gì?",
        ],
        expected_keywords=["Trang"],
        must_not_contain=["không biết"],
        notes="Stress test: memory block must stay under budget; name must survive trimming because it is in profile, not short-term.",
    ),
]
