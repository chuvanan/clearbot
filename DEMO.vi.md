# Các Prompt Demo Cho Abidibot (Bản Tiếng Việt)

Bản dịch/phóng tác tiếng Việt của `DEMO.md`. Sử dụng các prompt này để trình
diễn từng tính năng của ứng dụng. Sau mỗi câu trả lời của trợ lý, nhấp vào
liên kết trace `{...}` để xem lại request và response JSON đã được dựng lại.

## 1. Trò Chuyện Cơ Bản + Bộ Kiểm Tra Trace

Cấu hình sidebar: mặc định.

Prompt:

```text
Hãy giải thích trong 3 gạch đầu dòng ngắn gọn: AI agent là gì và nó khác gì so với một chatbot thông thường?
```

Trọng tâm trace: model, temperature, system prompt, messages, và cấu trúc
response.

## 2. Chèn System Prompt

Cấu hình sidebar: đặt System prompt thành `Bạn là một gia sư cướp biển. Hãy trả lời bằng các phép ẩn dụ về hàng hải.`

Prompt:

```text
Giải thích việc gọi công cụ (tool calling) cho người mới bắt đầu trong hai câu.
```

Trọng tâm trace: system prompt tùy chỉnh xuất hiện trong trường `system`.

## 3. Temperature

Cấu hình sidebar: chạy một lần với Temperature `0`, sau đó chạy lại với
Temperature `1.6`.

Prompt:

```text
Hãy cho tôi năm cái tên cho một robot nhỏ chuyên dọn dẹp hồ bơi.
```

Trọng tâm trace: giá trị `temperature` thay đổi trong khi tin nhắn người dùng
giữ nguyên.

## 4. Slash Command Là Các Prompt Macro

Cấu hình sidebar: mặc định.

Prompt:

```text
/explain vector embeddings
```

Trọng tâm trace: khung chat hiển thị `/explain ...`, nhưng trace hiển thị
prompt đã được mở rộng và `_expanded_from_command: explain`.

## 5. Lệnh Summarize

Cấu hình sidebar: mặc định.

Prompt:

```text
/summarize Agent kết hợp một mô hình ngôn ngữ với một vòng lặp. Vòng lặp nhận đầu vào từ người dùng, quyết định phải làm gì, có thể gọi công cụ, quan sát kết quả, rồi quyết định tiếp tục hay trả lời. Điều này hữu ích vì mô hình có thể tương tác với các hệ thống bên ngoài thay vì chỉ tạo ra văn bản.
```

Trọng tâm trace: `/summarize` được mở rộng thành template của lệnh trước khi
mô hình nhìn thấy nó.

## 6. Lệnh Critique

Cấu hình sidebar: mặc định.

Prompt:

```text
/critique Ứng dụng của chúng tôi tốt vì nó có AI và công cụ, người dùng chắc chắn sẽ thích nó.
```

Trọng tâm trace: việc mở rộng lệnh cộng với việc lưu trữ request/response bình
thường.

## 7. Công Cụ Filesystem: Khám Phá Chỉ Đọc

Cấu hình sidebar: bật Tools > Filesystem access.

Prompt:

```text
Hãy dùng công cụ filesystem của bạn để liệt kê thư mục hiện tại, đọc file README.md nếu có, và cho tôi biết dự án này có vẻ là gì.
```

Trọng tâm trace: schema của công cụ trong `tools`, sau đó các mục tool
request/result trong nội dung tin nhắn response.

## 8. Công Cụ Tìm Kiếm Web

Cấu hình sidebar: bật Tools > Web search. Yêu cầu `GOOGLE_SEARCH_ENGINE_ID` và
`GOOGLE_API_KEY`.

Prompt:

```text
Tìm kiếm trên web tài liệu hiện tại về component Chat của Shiny for Python, sau đó cho tôi liên kết liên quan nhất và một câu giải thích tại sao nó quan trọng đối với ứng dụng này.
```

Trọng tâm trace: `google_search` và/hoặc `http_get` được hiển thị như các
công cụ, cùng với mọi lệnh gọi/kết quả công cụ.

## 9. Planning Mode: Chỉ Đọc Trước

Cấu hình sidebar: bật Planning mode và Tools > Filesystem access.

Prompt:

```text
Hãy lên kế hoạch cách bạn sẽ kiểm tra repository này và đề xuất một cải tiến tài liệu nhỏ. Đừng chỉnh sửa gì cho đến khi tôi phê duyệt.
```

Trọng tâm trace: hậu tố planning được thêm vào `system`, và các công cụ thay
đổi trạng thái như `set_current_dir` bị loại bỏ. Sau khi có phản hồi, ứng
dụng hiển thị nút `Approve & execute` (hoặc `Cancel` để từ chối kế hoạch và
yêu cầu một bản chỉnh sửa khác).

## 10. Phê Duyệt Kế Hoạch

Cấu hình sidebar: tiếp tục từ prompt trước, sau đó nhấp `Approve & execute`.

Prompt (nút này tự động gửi nguyên văn tiếng Anh sau, đúng như ứng dụng đã lập
trình sẵn):

```text
The plan is approved. Proceed with executing it.
```

Trọng tâm trace: request tiếp theo có Planning mode tắt và toàn bộ danh sách
công cụ khả dụng trở lại.

## 11. Skills: Tiết Lộ Dần (Progressive Disclosure)

Cấu hình sidebar: bật Skills > regex-builder.

Prompt:

```text
Hãy xây dựng một regex khớp với các ngày kiểu ISO như 2026-07-21 nhưng loại bỏ 21-07-2026. Giải thích từng phần.
```

Trọng tâm trace: ban đầu chỉ có tên/mô tả của skill xuất hiện trong system
prompt; mô hình phải gọi `load_skill` để lấy đầy đủ hướng dẫn.

## 12. Skills: Định Dạng Commit Message

Cấu hình sidebar: bật Skills > commit-messages.

Prompt:

```text
Hãy viết một commit message cho thay đổi này: thêm planning mode, chặn các công cụ ghi trong khi lập kế hoạch, và thêm nút approve để thực thi kế hoạch sau đó.
```

Trọng tâm trace: `load_skill` chỉ trả về hướng dẫn viết commit message khi
skill đó liên quan.

## 13. Skills: CSV Profiler

Cấu hình sidebar: bật Skills > csv-profiler.

Prompt:

```text
Hãy phân tích (profile) bộ dữ liệu này:

id,name,signup_date,age,country
1,Ana,2024-01-03,29,US
2,Bilal,2024-01-04,,PK
3,Chen,2024-01-04,34,CN
4,Chen,2024-01-04,34,CN
5,Dana,03/01/2024,41,US
```

Trọng tâm trace: `load_skill` lấy về checklist phân tích dữ liệu, và câu trả
lời chỉ ra tuổi bị thiếu, dòng trùng lặp, và định dạng ngày không nhất quán.

## 14. Skills: Checklist Làm Sạch Dữ Liệu

Cấu hình sidebar: bật Skills > data-cleaning-checklist.

Prompt:

```text
Tôi có một file CSV đăng ký khách hàng với một số tuổi bị thiếu, một dòng trùng lặp, một ngày có định dạng khác (03/01/2024 thay vì 2024-01-03), và mã quốc gia không nhất quán (US so với USA). Hãy hướng dẫn tôi làm sạch nó trước khi phân tích.
```

Trọng tâm trace: câu trả lời tuân theo đúng thứ tự checklist (giá trị thiếu,
trùng lặp, ép kiểu, ngoại lệ, chuẩn hóa danh mục, ghi lại các thay đổi) thay
vì một danh sách tùy tiện.

## 15. Skills: SQL Query Builder

Cấu hình sidebar: bật Skills > sql-query-builder.

Prompt:

```text
Hãy viết một câu truy vấn để tìm 5 khách hàng có tổng giá trị đơn hàng cao nhất trong 90 ngày qua, với các bảng customers(id, name) và orders(id, customer_id, amount, created_at).
```

Trọng tâm trace: câu truy vấn được xây dựng từng mệnh đề trước khi đưa ra khối
code cuối cùng, và có ghi chú về dialect/đánh chỉ mục (indexing).

## 16. Skills: Đánh Giá Thiết Kế Schema

Cấu hình sidebar: bật Skills > schema-design-review.

Prompt:

```text
Hãy đánh giá schema này: một bảng orders duy nhất với các cột id, customer_name, customer_email, product_name, product_price, quantity, order_date. Thiết kế này có phù hợp cho một ứng dụng thương mại điện tử đang phát triển không?
```

Trọng tâm trace: câu trả lời chỉ ra các vấn đề chuẩn hóa (dữ liệu khách
hàng/sản phẩm bị lặp lại theo từng đơn hàng) và đề xuất tách schema kèm khóa
(keys).

## 17. Skills: Gợi Ý Biểu Đồ

Cấu hình sidebar: bật Skills > chart-recommender.

Prompt:

```text
Tôi có doanh thu hàng tháng trong 3 năm qua của 4 dòng sản phẩm. Tôi muốn thể hiện tỷ trọng doanh thu của mỗi dòng sản phẩm thay đổi như thế nào theo thời gian. Tôi nên dùng loại biểu đồ nào?
```

Trọng tâm trace: gợi ý biểu đồ suy luận dựa trên hình dạng dữ liệu (danh mục x
số liệu x thời gian) trước khi chọn loại biểu đồ, và có kèm code vẽ biểu đồ
minh họa.

## 18. Đăng Ký Công Cụ Tùy Chỉnh

Cấu hình sidebar: dán đoạn code sau vào Custom tool code, nhấp
`Register tools`, rồi chạy prompt bên dưới.

```python
def calculate_pool_volume(length_m: float, width_m: float, depth_m: float) -> str:
    """Calculate rectangular pool volume in liters from dimensions in meters."""
    liters = float(length_m) * float(width_m) * float(depth_m) * 1000
    return f"{liters:,.0f} liters"
```

Prompt:

```text
Hãy dùng công cụ tùy chỉnh để tính thể tích của một hồ bơi dài 8 m, rộng 4 m, sâu 1.5 m. Sau đó giải thích công thức.
```

Trọng tâm trace: các công cụ tùy chỉnh (runtime) được đăng ký cho request hiện
tại. So sánh hành vi streaming với danh sách công cụ có sẵn (built-in) trong
trace.

## 19. Logprobs

Cấu hình sidebar: chọn một model OpenAI `gpt*` và bật Logprobs.

Prompt:

```text
Chỉ trả lời đúng một từ: yes hoặc no. Nước có ướt không?
```

Trọng tâm trace: response JSON có chứa `logprobs` khi nhà cung cấp trả về xác
suất log của token.

## 20. Thinking / Reasoning

Cấu hình sidebar: bật Thinking, chọn effort `low`, `medium`, hoặc `high`. Dùng
một model có khả năng reasoning nếu có.

Prompt:

```text
Hãy giải cẩn thận: Một robot có 3 pin. Mỗi pin cấp năng lượng cho nó trong 45 phút. Nó dành 20 phút để dọn dẹp, nghỉ 10 phút, rồi lặp lại. Robot có thể hoàn thành bao nhiêu phiên dọn dẹp trọn vẹn?
```

Trọng tâm trace: các trường request như `reasoning`, `thinking`, hoặc
`_thinking_stream_display` xuất hiện tùy theo nhà cung cấp/model hỗ trợ.

## 21. Dừng / Ngắt (Stop / Interrupt)

Cấu hình sidebar: mặc định. Bắt đầu chạy prompt, sau đó nhấp `Stop (Esc)`
trong khi đang streaming.

Prompt:

```text
Hãy viết một checklist chi tiết gồm 40 điểm để đánh giá một ứng dụng AI agent phục vụ giáo dục. Mỗi điểm dài hai câu.
```

Trọng tâm trace: turn trợ lý chưa hoàn chỉnh được giữ lại trong ngữ cảnh hội
thoại, và ứng dụng mở khóa ô nhập chat một cách gọn gàng.

## 22. Ước Tính Token Của Memory

Cấu hình sidebar: mặc định. Chạy prompt này vài lần, rồi theo dõi mục Memory
token estimate ở sidebar.

Prompt:

```text
Hãy thêm ba ghi chú triển khai nữa vào cuộc thảo luận đang diễn ra của chúng ta về ứng dụng này. Hãy làm cho chúng cụ thể và không trùng lặp nhau.
```

Trọng tâm trace: mỗi request mới sẽ phát lại (replay) các turn trước đó trong
`messages`, làm cho sự tăng trưởng ngữ cảnh trở nên rõ ràng.

## 23. Nén Ngữ Cảnh Thủ Công (Manual Context Compaction)

Cấu hình sidebar: sau vài turn, nhấp `Compact context`.

Prompt:

```text
Dựa trên mọi thứ chúng ta đã thảo luận, hãy liệt kê những quyết định chính mà bạn còn nhớ.
```

Trọng tâm trace: sau khi nén, các turn cũ được thay thế bằng một turn tóm tắt
cộng với các turn hội thoại gần nhất.

## 24. Ngưỡng Tự Động Nén (Auto-Compaction Threshold)

Cấu hình sidebar: đặt Auto-compact threshold về một giá trị thấp như `500`,
sau đó gửi một prompt dài.

Prompt:

```text
Hãy tạo một kịch bản giảng dạy chi tiết về AI agent, bao gồm các phần về prompt, công cụ (tools), trace, memory, planning, skills, và cài đặt model.
```

Trọng tâm trace: khi ngữ cảnh ước tính vượt ngưỡng, việc nén sẽ tự động chạy
trước request đáng chú ý tiếp theo.

## 25. Model Tùy Chỉnh / BYOK

Cấu hình sidebar: chọn Custom model + endpoint, cung cấp base URL tương thích
OpenAI, tên model, và API key.

Prompt:

```text
Hãy cho tôi biết tên model và kiểu endpoint tôi đã cấu hình, nhưng đừng tiết lộ hay suy đoán bất kỳ API key nào.
```

Trọng tâm trace: `_endpoint` và tên model xuất hiện trong trace, nhưng API key
thì cố tình không có mặt.

## 26. Chat Mới (New Chat)

Cấu hình sidebar: nhấp `New Chat`, sau đó chạy prompt này.

Prompt:

```text
Bạn còn nhớ ngữ cảnh gì từ cuộc trò chuyện trước không?
```

Trọng tâm trace: danh sách `messages` bắt đầu lại từ đầu sau khi xóa lịch sử
chat.

## 27. Bookmark URL / Khôi Phục

Cấu hình sidebar: có ít nhất một phản hồi đã hoàn tất, sau đó sao chép/mở URL
hiện tại (kèm query parameters) trong một tab mới.

Prompt:

```text
Hãy tiếp tục từ cuộc trò chuyện đã được khôi phục và tóm tắt câu trả lời cuối cùng của trợ lý.
```

Trọng tâm trace: trạng thái session khôi phục lại các turn, snapshot, và code
công cụ tùy chỉnh, trong khi các bí mật như API key BYOK không được lưu trữ.
