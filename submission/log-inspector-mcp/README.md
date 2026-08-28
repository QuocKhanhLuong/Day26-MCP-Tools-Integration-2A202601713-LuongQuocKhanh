# Day26 Submission — Log Inspector MCP

Bài nộp cá nhân cho **Day26: MCP Tools Integration**. Mục tiêu của server là biến một thao tác thường làm thủ công khi debug/training/deploy — mở log, `grep` keyword rồi `tail` các lỗi gần nhất — thành MCP tools để Claude Code tự khám phá và gọi.

Bài làm đủ ba mức:

- **Dễ:** MCP Server local qua `stdio` với 2 tools thực tế.
- **Trung bình:** bản `Streamable HTTP` có Bearer-token authentication.
- **Khó:** versioning thật cho `search_logs`, giữ client v1 hoạt động, thêm `server://info`, và client mới đọc metadata trước khi chọn tool.

## 1. Use case thực tế

**Công việc hiện tại:** kiểm tra log của backend/training job để tìm lỗi và nguyên nhân gần nhất.

**Cách làm thủ công trước đây:** mở file log, dùng `grep`, `rg`, `tail`, rồi đọc nhiều dòng để xác định ERROR/CRITICAL mới nhất.

**Input:** file log nằm dưới một thư mục được cho phép, keyword, số lượng kết quả, tùy chọn phân biệt hoa/thường.

**Output:** các dòng match hoặc JSON có cấu trúc gồm line number, timestamp, level, message và metadata truy vấn.

Server chỉ được đọc file nằm bên trong `LOG_INSPECTOR_ROOT`; path traversal như `../secret.txt` bị từ chối.

## 2. Cấu trúc

```text
submission/log-inspector-mcp/
├── core.py                 # logic đọc/search/parse log, không phụ thuộc MCP
├── server_stdio.py         # bài Dễ + versioning/resource qua stdio
├── server_http.py          # Streamable HTTP + TokenVerifier
├── client_v1.py            # client cũ, gọi search_logs v1
├── client_smart.py         # đọc server://info rồi ưu tiên v2
├── requirements.txt
├── data/
│   └── sample.log
└── tests/
    └── test_core.py
```

## 3. MCP tools và input/output

### `search_logs` — v1, backward compatible

Tìm keyword trong file log.

Input:

- `keyword: str` — ví dụ `ERROR`, `timeout`, `CUDA`.
- `log_file: str = "sample.log"` — tương đối với `LOG_INSPECTOR_ROOT`.
- `limit: int = 50` — tối đa 500.
- `case_sensitive: bool = False`.

Output: `list[str]`, ví dụ:

```text
4: 2026-08-28 08:03:22 ERROR trainer failed to load checkpoint: file not found
6: 2026-08-28 08:05:31 ERROR database timeout after 3000ms
```

### `get_recent_errors` — v1

Lấy các lỗi mới nhất theo thứ tự mới → cũ.

Input:

- `limit: int = 10`.
- `log_file: str = "sample.log"`.
- `include_warnings: bool = False`.

Output: `list[str]` chứa ERROR/CRITICAL; nếu `include_warnings=true` thì thêm WARNING/WARN.

### `search_logs_v2` — v2

Phiên bản mới **không sửa/xóa v1**. Tool này trả JSON có cấu trúc để client mới dễ xử lý.

Input giữ tương thích về ý nghĩa với v1. Output có dạng:

```json
{
  "api_version": "2.0",
  "file": "sample.log",
  "query": {"keyword": "ERROR", "case_sensitive": false, "limit": 5},
  "matched": 3,
  "returned": 3,
  "truncated": false,
  "entries": [
    {
      "line_number": 4,
      "timestamp": "2026-08-28 08:03:22",
      "level": "ERROR",
      "message": "trainer failed to load checkpoint: file not found",
      "raw": "..."
    }
  ]
}
```

## 4. Cài đặt

Từ root repository:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r submission/log-inspector-mcp/requirements.txt
cd submission/log-inspector-mcp
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r submission/log-inspector-mcp/requirements.txt
cd submission/log-inspector-mcp
```

## 5. Chạy bài Dễ — stdio

Test logic trước:

```bash
python -m unittest discover -s tests -v
```

Chạy server trực tiếp:

```bash
python server_stdio.py
```

Để dùng log thật, đặt root chỉ tới thư mục log cần đọc:

```bash
export LOG_INSPECTOR_ROOT=/absolute/path/to/my/project/logs
```

Không đặt biến này thì server dùng `data/sample.log` đi kèm repository.

## 6. Đăng ký với Claude Code

Đứng ở root repository và dùng đường dẫn tuyệt đối để ổn định:

```bash
claude mcp add --transport stdio --scope local log-inspector -- \
  python /ABSOLUTE/PATH/TO/REPO/submission/log-inspector-mcp/server_stdio.py
```

Nếu muốn cho server đọc log của một project cụ thể:

```bash
claude mcp add --transport stdio \
  --env LOG_INSPECTOR_ROOT=/ABSOLUTE/PATH/TO/PROJECT/logs \
  --scope local log-inspector -- \
  python /ABSOLUTE/PATH/TO/REPO/submission/log-inspector-mcp/server_stdio.py
```

Kiểm tra:

```bash
claude mcp list
claude mcp get log-inspector
```

Trong Claude Code có thể chạy `/mcp` để xem trạng thái và số tool.

### Test bằng câu hỏi tự nhiên

Không chỉ định tên tool, để kiểm tra agent tự chọn tool:

```text
Tìm cho tôi 5 lỗi gần nhất trong sample.log.
```

```text
Trong sample.log, tìm tất cả dòng liên quan đến database và cho biết lỗi nào xảy ra trước khi connection restored.
```

```text
Tìm các lỗi CUDA gần nhất trong log và cho biết line number.
```

## 7. Bài Trung bình — Streamable HTTP + Authentication

### Chạy server

Token chỉ đặt trong shell, **không commit lên Git**:

```bash
export MCP_AUTH_TOKEN='replace-with-a-local-test-token'
export MCP_PORT=8000
python server_http.py
```

Endpoint:

```text
http://localhost:8000/mcp
```

Server bind `0.0.0.0` mặc định để có thể test từ máy khác trong LAN. Nếu chỉ muốn local:

```bash
export MCP_HOST=127.0.0.1
```

### Token đúng

Terminal khác:

```bash
export MCP_AUTH_TOKEN='replace-with-a-local-test-token'
python client_v1.py
python client_smart.py
```

Kỳ vọng: initialize thành công và tool trả kết quả.

### Thiếu token

```bash
unset MCP_AUTH_TOKEN
python client_v1.py
```

Kỳ vọng: client dừng ngay và yêu cầu set token. Với MCP client gửi HTTP request không có `Authorization`, server auth từ chối request.

Có thể kiểm tra lớp HTTP trực tiếp:

```bash
curl -i http://localhost:8000/mcp
```

Kỳ vọng: `401` hoặc `403` trước khi request được vào tool.

### Token sai

Giữ server đang chạy với token đúng, ở terminal client:

```bash
export MCP_AUTH_TOKEN='wrong-token'
python client_v1.py
```

Kỳ vọng: MCP handshake bị từ chối bằng `401` hoặc `403`.

### Đăng ký HTTP server với Claude Code

Không ghi token thật vào repository. Có thể add local config bằng lệnh chạy trực tiếp trên máy:

```bash
claude mcp add --transport http --scope local \
  --header "Authorization: Bearer $MCP_AUTH_TOKEN" \
  log-inspector-http http://localhost:8000/mcp
```

Sau đó kiểm tra `claude mcp list` hoặc `/mcp`.

## 8. Bài Khó — versioning + backward compatibility

### Thay đổi thật

- `search_logs` v1 trả `list[str]` và được **giữ nguyên**.
- `search_logs_v2` trả JSON có cấu trúc, thêm `api_version`, `matched`, `truncated`, `line_number`, `timestamp`, `level`, `message`.
- Các tham số optional của v1 vẫn giữ default; client cũ không phải sửa.

### Client cũ vẫn hoạt động

`client_v1.py` không đọc metadata và chỉ gọi:

```text
search_logs(keyword="ERROR", log_file="sample.log", limit=5)
```

Nó vẫn chạy với server v2 vì tool v1 không bị xóa hoặc đổi contract.

### `server://info`

Cả hai server công bố resource `server://info` chứa:

- server name/version,
- capabilities,
- version của từng tool,
- response contract,
- ghi chú backward compatibility.

### Client mới đọc metadata trước khi gọi tool

`client_smart.py` làm đúng flow:

1. `session.read_resource("server://info")`.
2. Parse metadata.
3. Nếu có `search_logs_v2` → dùng v2.
4. Nếu không → fallback `search_logs` v1.

Chạy:

```bash
export MCP_AUTH_TOKEN='replace-with-a-local-test-token'
python client_smart.py
```

## 9. Checklist tự chấm

- [x] Source code MCP Server tự xây.
- [x] Có ít nhất 2 tool thực tế: `search_logs`, `get_recent_errors`.
- [x] Tool đọc file thật, không trả dữ liệu hard-code.
- [x] README mô tả use case, input/output, setup, Claude Code.
- [x] Có sample data để reviewer chạy ngay.
- [x] Có unit test cho business logic và path traversal.
- [x] Có bản Streamable HTTP.
- [x] Có `TokenVerifier` dùng Bearer token từ environment.
- [x] Có hướng dẫn test token đúng / sai / thiếu.
- [x] Có versioning thật: v1 + v2 song song.
- [x] Client cũ vẫn gọi v1.
- [x] Có `server://info`.
- [x] Client mới đọc metadata trước khi chọn tool.
- [x] Không commit credential thật; `.env` đã nằm trong `.gitignore` của repo.

## 10. Lưu ý bảo mật

Repository **không chứa** API key, access token, password, private key hay `.env` thật. `MCP_AUTH_TOKEN` chỉ được đọc từ environment tại runtime. Nếu từng push secret thật, phải revoke/rotate secret và làm sạch history khi cần.
