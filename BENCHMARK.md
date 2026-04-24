# Lab #17 — Benchmark Report

10 multi-turn conversations, each run twice: **no-memory baseline** vs **with-memory (4-stack LangGraph agent)**.

Token counts are exact (tiktoken `cl100k_base`) on the probe turn's final prompt. Latency is wall-clock from `chat()` invocation and includes OpenAI round-trips.

## Summary

| # | Scenario | Category | No-memory | With-memory | Pass? |
|---|----------|----------|-----------|-------------|-------|
| 1 | Recall user name after 6 turns | profile_recall | Tên bạn là [tên của bạn]. | Tên bạn là Linh. | ✅ |
| 2 | Allergy correction (rubric mandatory) | conflict_update | Tất nhiên! Bạn có thể thử làm món cơm chiên hải sản hoặc mì xào thập cẩm. Nếu bạn thích mó… | Chắc chắn rồi, Mai! Vì bạn dị ứng với đậu nành, mình gợi ý bạn thử món gà nướng với rau củ… | ✅ |
| 3 | Recall debug lesson about docker networking | episodic_recall | Bạn có thể xem lại các bước sau:  1. **Kiểm tra kết nối mạng**: Đảm bảo rằng kết nối inter… | Nếu bạn gặp lại lỗi connection refused giữa các container trong Docker, hãy kiểm tra những… | ✅ |
| 4 | Retrieve FAQ chunk about returns | semantic_retrieval | Nếu sản phẩm còn nguyên hộp, bạn thường có khoảng 14 đến 30 ngày để trả, tùy thuộc vào chí… | Nếu sản phẩm còn nguyên hộp, bạn có 30 ngày để trả lại và nhận hoàn tiền đầy đủ. | ✅ |
| 5 | Retrieve FAQ about password reset | semantic_retrieval | Để reset password, bạn thường làm theo các bước sau:  1. Truy cập vào trang đăng nhập của … | Bạn có thể đặt lại mật khẩu bằng cách vào Cài đặt → Bảo mật → Đặt lại mật khẩu. Một liên k… | ✅ |
| 6 | Preferred language after small talk | profile_recall | Bạn muốn tôi tóm tắt cuộc trò chuyện bằng ngôn ngữ bạn thích. Hãy cho tôi biết ngôn ngữ đó… | Hôm nay, Hà Nội có mưa và thời tiết khá lạnh. Nếu bạn cần thêm thông tin về thời tiết hoặc… | ✅ |
| 7 | Job role correction | conflict_update | Xin lỗi, nhưng tôi không có thông tin về công việc hiện tại của bạn. Bạn có thể cho tôi bi… | Job hiện tại của bạn là data engineer. | ✅ |
| 8 | Reuse previous outcome (shipping) | episodic_recall | Bạn có thể thử tìm kiếm các nguồn tài liệu trực tuyến hoặc sử dụng các ứng dụng hỗ trợ học… | Bạn có thể chọn dịch vụ giao hàng express như lần trước. Nếu đặt hàng trước 14:00, bạn sẽ … | ✅ |
| 9 | Python asyncio behavior | semantic_retrieval | Khi bạn gọi `asyncio.gather` và một coroutine gặp lỗi, các coroutine còn lại sẽ vẫn tiếp t… | Khi gọi `asyncio.gather`, nếu một coroutine gặp lỗi, các coroutine còn lại vẫn tiếp tục ch… | ✅ |
| 10 | Token budget: recall name after very long chat | trim_budget | Tên bạn là gì? | Tên bạn là Trang. | ✅ |

## Aggregate

- With-memory pass rate: **10/10**
- No-memory pass rate:   **3/10**
- Probe-turn token totals: no-memory=292, with-memory=2693 (Δ=2401). Memory adds prompt tokens but recovers answers the baseline cannot produce.

## Details per scenario

### Scenario 1 — Recall user name after 6 turns
*Category:* `profile_recall`  |  *Probe turn:* #7 / 7

**Turn-by-turn (user input):**
1. Xin chào, tôi tên là Linh.
2. Hôm nay Hà Nội có mưa phùn.
3. Tôi đang học về agent memory.
4. Bạn có thể giải thích RAG không?
5. Cảm ơn, nghe có vẻ thú vị.
6. Tôi sẽ thử cài LangGraph tối nay.
7. Nhắc lại giúp tôi: tên tôi là gì?

**Probe answers:**

- **No-memory:** Tên bạn là [tên của bạn].
- **With-memory:** Tên bạn là Linh.

**Tokens (probe prompt):** no-mem=25, with-mem=265

**Verdict (with-memory):** PASS

### Scenario 2 — Allergy correction (rubric mandatory)
*Category:* `conflict_update`  |  *Probe turn:* #4 / 4

**Turn-by-turn (user input):**
1. Tôi tên Mai, tôi dị ứng sữa bò.
2. Hôm qua tôi uống trà sữa xong bị khó chịu.
3. À nhầm, tôi dị ứng đậu nành chứ không phải sữa bò.
4. Bạn gợi ý giúp tôi món ăn tối phù hợp được không?

**Probe answers:**

- **No-memory:** Tất nhiên! Bạn có thể thử làm món cơm chiên hải sản hoặc mì xào thập cẩm. Nếu bạn thích món ăn nhẹ, salad gà nướng cũng là một lựa chọn tuyệt vời. Bạn thích món nào hơn?
- **With-memory:** Chắc chắn rồi, Mai! Vì bạn dị ứng với đậu nành, mình gợi ý bạn thử món gà nướng với rau củ. Bạn có thể ướp gà với các gia vị như tỏi, tiêu, và chanh để tăng hương vị. Kèm theo là một đĩa salad tươi ngon. Chúc bạn có bữa tối ngon miệng!

**Tokens (probe prompt):** no-mem=33, with-mem=268

**Verdict (with-memory):** PASS

### Scenario 3 — Recall debug lesson about docker networking
*Category:* `episodic_recall`  |  *Probe turn:* #3 / 3

**Turn-by-turn (user input):**
1. Hôm qua tôi debug được lỗi connection refused giữa 2 container docker.
2. Hóa ra cần dùng tên service trong docker-compose thay vì localhost.
3. Bây giờ lại gặp lỗi tương tự, bạn gợi ý cho tôi xem lại gì?

**Probe answers:**

- **No-memory:** Bạn có thể xem lại các bước sau:

1. **Kiểm tra kết nối mạng**: Đảm bảo rằng kết nối internet của bạn ổn định.
2. **Xem lại cấu hình**: Kiểm tra lại các thiết lập hoặc cấu hình liên quan đến ứng dụng hoặc hệ thống bạn đang sử dụng.
3. **Cập nhật phần mềm**: Đảm bảo rằng bạn đang sử dụng phiên bản mới nhất của phần mềm.
4. **Xem log lỗi**: Nếu có, hãy kiểm tra log lỗi để tìm hiểu nguyên nhân cụ thể.
5. **Khởi động lại**: Thử khởi động lại thiết bị hoặc ứng dụng để xem có khắc phục được vấn đề không.

Nếu vẫn gặp lỗi, bạn có thể cung cấp thêm thông tin chi tiết để tôi có thể hỗ trợ tốt hơn.
- **With-memory:** Nếu bạn gặp lại lỗi connection refused giữa các container trong Docker, hãy kiểm tra những điều sau:

1. **Tên Service**: Đảm bảo bạn đang sử dụng đúng tên service trong docker-compose thay vì localhost.
2. **Cấu Hình Mạng**: Kiểm tra cấu hình mạng của các container để đảm bảo chúng có thể giao tiếp với nhau.
3. **Port**: Đảm bảo rằng bạn đã mở đúng port trong docker-compose và rằng ứng dụng đang lắng nghe trên port đó.
4. **Logs**: Kiểm tra logs của các container để tìm hiểu nguyên nhân cụ thể của lỗi.

Nếu bạn đã kiểm tra tất cả những điều này mà vẫn gặp lỗi, hãy cung cấp thêm thông tin để tôi có thể giúp bạn tốt hơn!

**Tokens (probe prompt):** no-mem=37, with-mem=275

**Verdict (with-memory):** PASS

### Scenario 4 — Retrieve FAQ chunk about returns
*Category:* `semantic_retrieval`  |  *Probe turn:* #2 / 2

**Turn-by-turn (user input):**
1. Tôi là khách mới, muốn hỏi về chính sách đổi trả.
2. Nếu sản phẩm còn nguyên hộp thì tôi có bao nhiêu ngày để trả?

**Probe answers:**

- **No-memory:** Nếu sản phẩm còn nguyên hộp, bạn thường có khoảng 14 đến 30 ngày để trả, tùy thuộc vào chính sách của từng cửa hàng. Hãy kiểm tra chính sách cụ thể của nơi bạn mua hàng để biết chính xác.
- **With-memory:** Nếu sản phẩm còn nguyên hộp, bạn có 30 ngày để trả lại và nhận hoàn tiền đầy đủ.

**Tokens (probe prompt):** no-mem=36, with-mem=274

**Verdict (with-memory):** PASS

### Scenario 5 — Retrieve FAQ about password reset
*Category:* `semantic_retrieval`  |  *Probe turn:* #2 / 2

**Turn-by-turn (user input):**
1. Tôi quên mật khẩu đăng nhập.
2. Làm cách nào để reset password?

**Probe answers:**

- **No-memory:** Để reset password, bạn thường làm theo các bước sau:

1. Truy cập vào trang đăng nhập của dịch vụ bạn muốn reset password.
2. Nhấn vào liên kết "Quên mật khẩu?" hoặc "Reset password".
3. Nhập địa chỉ email hoặc tên đăng nhập của bạn.
4. Kiểm tra email của bạn để nhận hướng dẫn reset password.
5. Làm theo hướng dẫn trong email để tạo mật khẩu mới.

Nếu bạn cần thêm thông tin cụ thể về dịch vụ nào, hãy cho tôi biết!
- **With-memory:** Bạn có thể đặt lại mật khẩu bằng cách vào Cài đặt → Bảo mật → Đặt lại mật khẩu. Một liên kết đặt lại sẽ được gửi đến địa chỉ email đã đăng ký và sẽ hết hạn sau 15 phút.

**Tokens (probe prompt):** no-mem=17, with-mem=255

**Verdict (with-memory):** PASS

### Scenario 6 — Preferred language after small talk
*Category:* `profile_recall`  |  *Probe turn:* #4 / 4

**Turn-by-turn (user input):**
1. Hi, my preferred language is Vietnamese.
2. Let's talk about the weather in Hanoi.
3. Rainy today, pretty cold.
4. Câu hỏi tiếp theo: dùng ngôn ngữ tôi thích để tóm tắt cuộc trò chuyện.

**Probe answers:**

- **No-memory:** Bạn muốn tôi tóm tắt cuộc trò chuyện bằng ngôn ngữ bạn thích. Hãy cho tôi biết ngôn ngữ đó là gì!
- **With-memory:** Hôm nay, Hà Nội có mưa và thời tiết khá lạnh. Nếu bạn cần thêm thông tin về thời tiết hoặc bất kỳ điều gì khác, hãy cho tôi biết nhé!

**Tokens (probe prompt):** no-mem=44, with-mem=283

**Verdict (with-memory):** PASS

### Scenario 7 — Job role correction
*Category:* `conflict_update`  |  *Probe turn:* #4 / 4

**Turn-by-turn (user input):**
1. Tôi làm backend engineer tại một startup fintech.
2. Dự án hiện tại của tôi là một payment gateway.
3. Thực ra tôi mới chuyển sang làm data engineer từ tuần trước.
4. Job hiện tại của tôi là gì?

**Probe answers:**

- **No-memory:** Xin lỗi, nhưng tôi không có thông tin về công việc hiện tại của bạn. Bạn có thể cho tôi biết để tôi cập nhật không?
- **With-memory:** Job hiện tại của bạn là data engineer.

**Tokens (probe prompt):** no-mem=18, with-mem=251

**Verdict (with-memory):** PASS

### Scenario 8 — Reuse previous outcome (shipping)
*Category:* `episodic_recall`  |  *Probe turn:* #2 / 2

**Turn-by-turn (user input):**
1. Lần trước tôi đặt hàng ở HCMC ngày 10, ngày 11 nhận được vì chọn express.
2. Kỳ này tôi lại cần gấp, có cách nào tương tự không?

**Probe answers:**

- **No-memory:** Bạn có thể thử tìm kiếm các nguồn tài liệu trực tuyến hoặc sử dụng các ứng dụng hỗ trợ học tập để nhanh chóng nắm bắt kiến thức. Nếu cần, tôi có thể gợi ý một số công cụ hoặc phương pháp cụ thể hơn.
- **With-memory:** Bạn có thể chọn dịch vụ giao hàng express như lần trước. Nếu đặt hàng trước 14:00, bạn sẽ nhận được vào ngày hôm sau.

**Tokens (probe prompt):** no-mem=31, with-mem=269

**Verdict (with-memory):** PASS

### Scenario 9 — Python asyncio behavior
*Category:* `semantic_retrieval`  |  *Probe turn:* #2 / 2

**Turn-by-turn (user input):**
1. Tôi đang học asyncio.
2. Khi gọi asyncio.gather mà một coroutine lỗi thì các coroutine còn lại sao?

**Probe answers:**

- **No-memory:** Khi bạn gọi `asyncio.gather` và một coroutine gặp lỗi, các coroutine còn lại sẽ vẫn tiếp tục chạy. Tuy nhiên, `asyncio.gather` sẽ trả về một ngoại lệ cho coroutine đầu tiên gặp lỗi, và các coroutine còn lại sẽ không được hoàn thành. Nếu bạn muốn thu thập kết quả của tất cả các coroutine, bạn có thể sử dụng tham số `return_exceptions=True`, điều này sẽ cho phép `gather` trả về ngoại lệ như là một kết quả thay vì dừng lại.
- **With-memory:** Khi gọi `asyncio.gather`, nếu một coroutine gặp lỗi, các coroutine còn lại vẫn tiếp tục chạy trừ khi bạn đặt `return_exceptions=False` (mặc định là True).

**Tokens (probe prompt):** no-mem=31, with-mem=263

**Verdict (with-memory):** PASS

### Scenario 10 — Token budget: recall name after very long chat
*Category:* `trim_budget`  |  *Probe turn:* #5 / 5

> Note: Stress test: memory block must stay under budget; name must survive trimming because it is in profile, not short-term.

**Turn-by-turn (user input):**
1. Tôi tên Trang, rất vui gặp bạn.
2. Để tôi kể: Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet. Lorem ipsum dolor sit…
3. Và một đoạn dài nữa: Phân tích chi tiết dự án A có rất nhiều số liệu dài dòng. Phân tích chi tiết dự án A có rất nhiều số liệu dài dòng. Phân tích chi tiết dự án A có rất nhiều số liệu dài dòng. Phân …
4. Thêm background: Tôi từng làm ở nhiều công ty khác nhau trong 10 năm qua. Tôi từng làm ở nhiều công ty khác nhau trong 10 năm qua. Tôi từng làm ở nhiều công ty khác nhau trong 10 năm qua. Tôi từng làm…
5. Bây giờ: tên tôi là gì?

**Probe answers:**

- **No-memory:** Tên bạn là gì?
- **With-memory:** Tên bạn là Trang.

**Tokens (probe prompt):** no-mem=20, with-mem=290

**Verdict (with-memory):** PASS
