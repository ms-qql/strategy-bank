import json

import pytest

from app.db import run_command, run_query, run_query_one
from app.services import opencode_extraction as svc


def test_extract_json_candidate_handles_missing_closing_fence():
    raw = '```json\n{"strategies": []}'
    assert svc._extract_json_candidate(raw) == '{"strategies": []}'


def test_extract_json_candidate_handles_closed_fence():
    raw = 'irrelevanter Text davor\n```json\n{"strategies": []}\n```\nirrelevanter Text danach'
    assert json.loads(svc._extract_json_candidate(raw)) == {"strategies": []}


def test_parse_model_output_valid():
    parsed = svc.parse_model_output('```json\n{"strategies": []}\n```')
    assert parsed == {"strategies": []}


def test_parse_model_output_missing_strategies_key_raises():
    with pytest.raises(ValueError):
        svc.parse_model_output('```json\n{"foo": "bar"}\n```')


def test_parse_model_output_garbage_raises():
    with pytest.raises(ValueError):
        svc.parse_model_output("Ich kann diese Quelle nicht analysieren.")


def test_normalize_strategy_forces_unknown_category_to_fallback():
    normalized = svc._normalize_strategy({"category": "Krypto-Zauberei", "entry_rule": "x", "exit_rule": "y"})
    assert normalized["category"] == "Sonstige"


def test_normalize_strategy_forces_gesperrt_on_missing_exit_rule():
    normalized = svc._normalize_strategy({"name": "Test", "entry_rule": "RSI < 30", "status": "Entwurf"})
    assert normalized["status"] == "gesperrt (unvollständig)"
    assert "exit_rule" in normalized["status_reason"]


def test_normalize_strategy_forces_parameters_as_proposal():
    normalized = svc._normalize_strategy(
        {
            "entry_rule": "a",
            "exit_rule": "b",
            "parameters": [{"name": "Länge", "value": "14", "is_proposal": False}],
        }
    )
    assert normalized["parameters"][0]["is_proposal"] is True


def test_normalize_strategy_versions_and_locks_missing_rule_citations():
    normalized = svc._normalize_strategy(
        {
            "entry_rule": "a",
            "exit_rule": "b",
            "warmup_requirement": "14",
            "simultaneous_entry_exit_behavior": "exit wins",
            "reversal_behavior": "close first",
            "citations": [{"rule_field": "entry_rule", "excerpt": "a"}],
        }
    )
    assert normalized["version"] == 1
    assert normalized["status"] == "gesperrt (unvollständig)"
    assert "exit_rule" in normalized["status_reason"]


def test_execute_extraction_persists_drafts_on_success(monkeypatch):
    fake_output = """```json
{"strategies": [{
    "name": "Test-Strategie", "thesis": "These", "category": "Momentum",
    "direction": "long-only", "entry_rule": "RSI < 30", "exit_rule": "RSI > 70",
    "warmup_requirement": "14 Perioden", "simultaneous_entry_exit_behavior": "n/a",
    "reversal_behavior": "n/a", "status": "Entwurf", "status_reason": null,
    "parameters": [{"name": "Länge", "value": "14", "unit": "Perioden", "allowed_range": "1-100"}],
    "citations": [
        {"rule_field": "entry_rule", "excerpt": "RSI < 30", "line_reference": "Zeile 1"},
        {"rule_field": "exit_rule", "excerpt": "RSI > 70", "line_reference": "Zeile 2"},
        {"rule_field": "warmup_requirement", "excerpt": "14 Perioden", "line_reference": "Zeile 3"},
        {"rule_field": "simultaneous_entry_exit_behavior", "excerpt": "n/a", "line_reference": "Zeile 4"},
        {"rule_field": "reversal_behavior", "excerpt": "n/a", "line_reference": "Zeile 5"}
    ],
    "open_questions": []
}]}
```"""
    monkeypatch.setattr(svc, "run_opencode", lambda prompt: fake_output)

    source = run_command(
        "INSERT INTO sources (content, source_hash, source_type) VALUES (%s, %s, 'text') RETURNING id",
        ["Quelle", "hash123"],
        returning=True,
    )
    run = run_command(
        "INSERT INTO extraction_runs (source_id, status, model, prompt_version) "
        "VALUES (%s, 'läuft', 'test-model', 'v1') RETURNING id",
        [source["id"]],
        returning=True,
    )

    svc.execute_extraction(run["id"], source["id"], "Quelle", "hash123")

    run_row = run_query_one("SELECT status FROM extraction_runs WHERE id = %s", [run["id"]])
    assert run_row["status"] == "abgeschlossen"
    source_row = run_query_one("SELECT extraction_status FROM sources WHERE id = %s", [source["id"]])
    assert source_row["extraction_status"] == "extrahiert"

    drafts = run_query("SELECT * FROM strategy_drafts WHERE extraction_run_id = %s", [run["id"]])
    assert len(drafts) == 1
    assert drafts[0]["name"] == "Test-Strategie"
    assert drafts[0]["version"] == 1
    params = run_query("SELECT * FROM draft_parameters WHERE draft_id = %s", [drafts[0]["id"]])
    assert params[0]["is_proposal"] is True


def test_execute_extraction_marks_keine_treffer(monkeypatch):
    monkeypatch.setattr(svc, "run_opencode", lambda prompt: '```json\n{"strategies": []}\n```')

    source = run_command(
        "INSERT INTO sources (content, source_hash, source_type) VALUES (%s, %s, 'text') RETURNING id",
        ["Quelle ohne Strategie", "hash456"],
        returning=True,
    )
    run = run_command(
        "INSERT INTO extraction_runs (source_id, status, model, prompt_version) "
        "VALUES (%s, 'läuft', 'test-model', 'v1') RETURNING id",
        [source["id"]],
        returning=True,
    )

    svc.execute_extraction(run["id"], source["id"], "Quelle ohne Strategie", "hash456")

    run_row = run_query_one("SELECT status FROM extraction_runs WHERE id = %s", [run["id"]])
    assert run_row["status"] == "keine Treffer"
    source_row = run_query_one("SELECT extraction_status FROM sources WHERE id = %s", [source["id"]])
    assert source_row["extraction_status"] == "extrahiert, keine Treffer"


def test_execute_extraction_marks_failed_on_bad_json(monkeypatch):
    monkeypatch.setattr(svc, "run_opencode", lambda prompt: "Ich kann diese Quelle nicht lesen.")

    source = run_command(
        "INSERT INTO sources (content, source_hash, source_type) VALUES (%s, %s, 'text') RETURNING id",
        ["Quelle", "hash789"],
        returning=True,
    )
    run = run_command(
        "INSERT INTO extraction_runs (source_id, status, model, prompt_version) "
        "VALUES (%s, 'läuft', 'test-model', 'v1') RETURNING id",
        [source["id"]],
        returning=True,
    )

    svc.execute_extraction(run["id"], source["id"], "Quelle", "hash789")

    run_row = run_query_one("SELECT status, error_message FROM extraction_runs WHERE id = %s", [run["id"]])
    assert run_row["status"] == "fehlgeschlagen"
    assert run_row["error_message"]
    source_row = run_query_one("SELECT extraction_status FROM sources WHERE id = %s", [source["id"]])
    assert source_row["extraction_status"] == "Extraktion fehlgeschlagen"
