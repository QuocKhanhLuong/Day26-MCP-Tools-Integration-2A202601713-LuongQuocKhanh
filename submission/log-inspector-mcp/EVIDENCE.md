# Verification Evidence / Reproduction Guide

File này không giả lập screenshot. Nó ghi lại các kiểm tra có thể tái lập từ source.

## Automated tests

```bash
cd submission/log-inspector-mcp
python -m unittest discover -s tests -v
```

Expected: **7 tests pass**.

Test suite gồm 5 test business logic/path-safety và 2 MCP contract tests dùng in-process `Client(mcp)` để xác nhận tool discovery, tool call thật và resource `server://info` đọc được.

## Syntax check

```bash
python -m py_compile core.py server_stdio.py server_http.py client_v1.py client_smart.py
```

Expected: exit code 0.

## MCP stdio smoke test

Sau khi `pip install -r requirements.txt`:

```bash
python server_stdio.py
```

Sau đó đăng ký với Claude Code theo README và hỏi tự nhiên:

```text
Tìm cho tôi 5 lỗi gần nhất trong sample.log.
```

Reviewer nên xác nhận Claude Code tự chọn `get_recent_errors` thay vì được prompt trực tiếp tên tool.

## HTTP auth matrix

Server terminal:

```bash
export MCP_AUTH_TOKEN='local-only-token'
python server_http.py
```

Client matrix:

| Case | Client environment | Expected |
|---|---|---|
| Valid | `MCP_AUTH_TOKEN=local-only-token` | initialize + tool call succeeds |
| Wrong | `MCP_AUTH_TOKEN=wrong-token` | HTTP 401/403 during MCP connection |
| Missing | token unset | client refuses to start; raw unauthenticated HTTP is rejected by server |

Kiểm tra thiếu token trực tiếp ở HTTP layer:

```bash
curl -i http://127.0.0.1:8000/mcp
```

Expected: `401 Unauthorized` trước khi bất kỳ tool nào được chạy.

## Versioning proof

1. Run `client_v1.py`: it calls `search_logs` and does not read `server://info`.
2. Run `client_smart.py`: it reads `server://info`, detects `search_logs_v2`, then calls v2.
3. Confirm both clients work against `server_http.py` with the same valid token.
