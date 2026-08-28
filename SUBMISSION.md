# Day26 Personal Submission

Bài nộp cá nhân nằm tại:

**[`submission/log-inspector-mcp/`](submission/log-inspector-mcp/README.md)**

Use case: **Log Inspector MCP** — tự động tìm keyword/lỗi gần nhất trong log backend/training thay cho thao tác `grep`/`tail` thủ công.

Phạm vi hoàn thành:

- MCP Server local qua **stdio**.
- Tools thật: `search_logs`, `get_recent_errors`.
- Bản **Streamable HTTP**.
- Bearer-token authentication bằng `TokenVerifier` và token lấy từ environment.
- Test token đúng / sai / thiếu token.
- Versioning thật: giữ `search_logs` v1 và thêm `search_logs_v2`.
- Backward-compatible legacy client.
- Resource `server://info`.
- Smart client đọc metadata trước khi chọn v2 hoặc fallback v1.
- Unit tests cho logic đọc log và path-safety.
- Hướng dẫn Claude Code + verification trong README/EVIDENCE.

Không có credential thật trong source/repository.
