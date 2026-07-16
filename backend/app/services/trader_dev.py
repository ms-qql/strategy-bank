"""trader.dev MCP-Integration (PROJ-5 Credit-Gate)."""

import json
import re
from urllib.error import URLError
from urllib.request import Request, urlopen
from typing import Any

from ..config import settings

_MCP_URL = "https://mcp.trader.dev"
_SSE_URL = f"{_MCP_URL}/sse"
_RESULT_API_URL = "https://mcp-api.trader.dev/backtest-results"
_REPORT_RE = re.compile(r"https://mcp-api\.trader\.dev/backtest/([\w-]+)", re.IGNORECASE)


class CreditServiceError(RuntimeError):
    """get_credits fehlgeschlagen — Batch-Start muss blockieren."""


class TraderDevServiceError(RuntimeError):
    """trader.dev-MCP-Aufruf fehlgeschlagen."""


def get_credits() -> dict[str, Any]:
    """Live-Abruf ohne den API-Key an ein Modell weiterzugeben."""
    try:
        parsed = _call_tool("get_credits", {})
    except TraderDevServiceError as exc:
        raise CreditServiceError(f"trader.dev-Credit-Abfrage fehlgeschlagen: {exc}") from exc

    balance = _first(parsed, "balance", "credits", "creditsRemaining")
    if balance is None:
        raise CreditServiceError("trader.dev-Antwort enthält keinen Credit-Bestand.")
    return {
        "balance": int(balance),
        "tier": str(parsed.get("tier", "unbekannt")),
        "reset": str(_first(parsed, "nextReset", "next_reset", "weeklyReset") or "unbekannt"),
        "weekly_free": int(_first(parsed, "weeklyFreeCredits", "weekly_free_credits") or 0),
    }


def start_backtest(*, pine_source: str, symbol: str, timeframe: str, period_start: Any, period_end: Any) -> dict[str, Any]:
    arguments: dict[str, Any] = {
        "pineSource": pine_source,
        "symbol": symbol,
        "timeframe": timeframe,
        "from": str(period_start),
    }
    if period_end:
        arguments["to"] = str(period_end)
    output = _call_tool("quick_backtest", arguments)
    result_id = _first(output, "resultId", "id")
    if not result_id:
        return output

    result = output if "netProfitPct" in output else _fetch_backtest_result(str(result_id))
    result = dict(result)
    if "tradeCount" not in result and "totalTrades" in result:
        result["tradeCount"] = result["totalTrades"]
    return {
        "status": "completed",
        "result": result,
        "resultId": str(result_id),
        "reportLink": output.get("reportLink") or f"https://mcp-api.trader.dev/backtest/{result_id}",
    }


def get_backtest_result(job_id: str) -> dict[str, Any]:
    return _call_tool("get_backtest_result", {"jobId": job_id})


def _fetch_backtest_result(result_id: str) -> dict[str, Any]:
    try:
        headers = {"User-Agent": "strategy-bank/1.0"}
        if settings.trader_dev_api_key:
            headers["Authorization"] = f"Bearer {settings.trader_dev_api_key}"
        request = Request(
            f"{_RESULT_API_URL}/{result_id}",
            headers=headers,
        )
        with urlopen(request, timeout=30) as response:
            result = json.load(response)
    except (OSError, TimeoutError, URLError, ValueError, json.JSONDecodeError) as exc:
        raise TraderDevServiceError(f"Backtest-Ergebnis konnte nicht geladen werden: {exc}") from exc
    if not isinstance(result, dict):
        raise TraderDevServiceError("trader.dev lieferte kein strukturiertes Backtest-Ergebnis.")
    return result


def _call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if not settings.trader_dev_api_key:
        raise TraderDevServiceError("TRADER_DEV_API_KEY ist nicht gesetzt.")
    try:
        with urlopen(Request(_SSE_URL, headers={"Accept": "text/event-stream", "User-Agent": "strategy-bank/1.0"}), timeout=30) as stream:
            endpoint = _next_sse_data(stream)
            _mcp_post(endpoint, 1, "initialize", {
                "protocolVersion": "2024-11-05", "capabilities": {},
                "clientInfo": {"name": "strategy-bank", "version": "1"},
            })
            _next_mcp_result(stream, 1)
            _mcp_post(endpoint, None, "notifications/initialized", {})
            _mcp_post(endpoint, 2, "tools/call", {"name": "authenticate", "arguments": {"key": settings.trader_dev_api_key}})
            if _next_mcp_result(stream, 2).get("isError"):
                raise ValueError("trader.dev hat den API-Key abgelehnt.")
            _mcp_post(endpoint, 3, "tools/call", {"name": name, "arguments": arguments})
            return _tool_json(_next_mcp_result(stream, 3))
    except (OSError, TimeoutError, URLError, ValueError, json.JSONDecodeError) as exc:
        raise TraderDevServiceError(str(exc)) from exc


def _mcp_post(endpoint: str, request_id: int | None, method: str, params: dict[str, Any]) -> None:
    payload: dict[str, Any] = {"jsonrpc": "2.0", "method": method, "params": params}
    if request_id is not None:
        payload["id"] = request_id
    request = Request(
        f"{_MCP_URL}{endpoint}", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "strategy-bank/1.0"}, method="POST",
    )
    with urlopen(request, timeout=30):
        pass


def _next_sse_data(stream: Any) -> str:
    while True:
        raw = stream.readline()
        if not raw:
            raise ValueError("trader.dev hat die MCP-Verbindung beendet.")
        line = raw.decode().strip()
        if not line:
            continue
        if line.startswith("data: "):
            return line[6:]


def _next_mcp_result(stream: Any, request_id: int) -> dict[str, Any]:
    while True:
        data = _next_sse_data(stream)
        message = json.loads(data)
        if message.get("id") != request_id:
            continue
        if "error" in message:
            raise ValueError(message["error"].get("message", "MCP-Fehler"))
        return message["result"]


def _tool_json(result: dict[str, Any]) -> dict[str, Any]:
    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        return structured
    text = "\n".join(
        part["text"] for part in result.get("content", [])
        if part.get("type") == "text" and part.get("text")
    )
    if result.get("isError"):
        raise ValueError(text or "trader.dev hat die Anfrage abgelehnt.")
    if text:
        fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
        try:
            parsed = json.loads((fenced.group(1) if fenced else text).strip())
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            report = _REPORT_RE.search(text)
            if report:
                return {"resultId": report.group(1), "reportLink": report.group(0)}
            job = re.search(r"(?:job[ _-]?id|backtest[ _-]?id)\s*[:=]\s*[`\"']?([\w-]+)", text, re.IGNORECASE)
            if job:
                return {"jobId": job.group(1)}
            raise ValueError(text)
    raise ValueError("trader.dev hat keine strukturierte Credit-Antwort geliefert.")


def _first(data: dict[str, Any], *keys: str) -> Any:
    return next((data[key] for key in keys if data.get(key) is not None), None)
