from app.services.trader_dev import _next_sse_data, _tool_json


class _Stream:
    def __init__(self, *lines: bytes):
        self._lines = iter(lines)

    def readline(self) -> bytes:
        return next(self._lines, b"")


def test_parses_direct_mcp_credit_result():
    assert _next_sse_data(_Stream(b"event: message\n", b"data: {\"id\": 3}\n")) == '{"id": 3}'
    assert _tool_json({"content": [{"type": "text", "text": '{"balance": 999}'}]}) == {"balance": 999}
