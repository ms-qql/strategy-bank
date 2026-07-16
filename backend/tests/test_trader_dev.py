from unittest.mock import patch

from app.services.trader_dev import _next_sse_data, _tool_json, start_backtest


class _Stream:
    def __init__(self, *lines: bytes):
        self._lines = iter(lines)

    def readline(self) -> bytes:
        return next(self._lines, b"")


def test_parses_direct_mcp_credit_result():
    assert _next_sse_data(_Stream(b"event: message\n", b"data: {\"id\": 3}\n")) == '{"id": 3}'
    assert _tool_json({"content": [{"type": "text", "text": '{"balance": 999}'}]}) == {"balance": 999}


def test_starts_backtest_via_direct_mcp():
    with patch("app.services.trader_dev._call_tool", return_value={"jobId": "job-1"}) as call:
        assert start_backtest(pine_source="// pine", symbol="BTC", timeframe="4h", period_start="2021-01-01", period_end="2024-12-31") == {"jobId": "job-1"}

    assert call.call_args.args == ("quick_backtest", {"pineSource": "// pine", "symbol": "BTC", "timeframe": "4h", "from": "2021-01-01", "to": "2024-12-31"})
