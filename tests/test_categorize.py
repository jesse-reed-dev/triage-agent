"""Tests for prompt building and Claude CLI response parsing."""

import json
import re
import subprocess

import categorize
from categorize import MAX_BODY_CHARS, _parse_categorization, build_prompt, categorize_issue


def make_issue(**overrides) -> dict:
    issue = {
        "repo": "owner/repo",
        "number": 42,
        "title": "Fix the widget",
        "labels": [{"name": "bug"}, {"name": "help wanted"}],
        "body": "The widget is broken.",
    }
    issue.update(overrides)
    return issue


def make_triage_json(**overrides) -> str:
    """A valid inner JSON payload as the model would return it."""
    payload = {
        "category": "bug",
        "difficulty": "easy",
        "good_first_issue": True,
        "one_line_summary": "Fix a broken widget.",
        "why_easy": "Small and well described.",
    }
    payload.update(overrides)
    return json.dumps(payload)


def envelope(result: str) -> str:
    """Wrap an inner payload in the CLI's --output-format json envelope."""
    return json.dumps({"result": result})


# ─── build_prompt ─────────────────────────────────────────────────────────────

def test_prompt_includes_repo_title_and_labels():
    prompt = build_prompt(make_issue())
    assert "owner/repo" in prompt
    assert "Fix the widget" in prompt
    assert "bug, help wanted" in prompt


def test_prompt_without_labels_says_none():
    prompt = build_prompt(make_issue(labels=[]))
    assert "Labels: none" in prompt


def test_prompt_with_empty_body_uses_placeholder():
    assert "(no description provided)" in build_prompt(make_issue(body=""))
    assert "(no description provided)" in build_prompt(make_issue(body=None))


def test_prompt_truncates_long_body_and_reports_omitted_count():
    body = "x" * (MAX_BODY_CHARS + 250)
    prompt = build_prompt(make_issue(body=body))
    assert "[... body truncated, 250 characters omitted]" in prompt
    assert "x" * (MAX_BODY_CHARS + 1) not in prompt


def test_prompt_keeps_body_at_exactly_max_chars():
    body = "x" * MAX_BODY_CHARS
    prompt = build_prompt(make_issue(body=body))
    # The template's instructions quote the marker with a literal "N", so
    # match a real marker (digit count) to confirm no truncation happened.
    assert not re.search(r"\[\.\.\. body truncated, \d+ characters omitted\]", prompt)
    assert body in prompt


# ─── _parse_categorization ────────────────────────────────────────────────────

def test_parse_valid_response():
    result = _parse_categorization(envelope(make_triage_json()), make_issue())
    assert result == {
        "category": "bug",
        "difficulty": "easy",
        "good_first_issue": True,
        "one_line_summary": "Fix a broken widget.",
        "why_easy": "Small and well described.",
    }


def test_parse_strips_markdown_fences():
    fenced = f"```json\n{make_triage_json()}\n```"
    result = _parse_categorization(envelope(fenced), make_issue())
    assert result is not None
    assert result["category"] == "bug"


def test_parse_rejects_non_json_stdout():
    assert _parse_categorization("not json at all", make_issue()) is None


def test_parse_rejects_envelope_without_result_key():
    assert _parse_categorization(json.dumps({"other": "thing"}), make_issue()) is None


def test_parse_rejects_non_json_result():
    assert _parse_categorization(envelope("Sure! Here's my rating..."), make_issue()) is None


def test_parse_rejects_invalid_category():
    bad = make_triage_json(category="question")
    assert _parse_categorization(envelope(bad), make_issue()) is None


def test_parse_rejects_invalid_difficulty():
    bad = make_triage_json(difficulty="trivial")
    assert _parse_categorization(envelope(bad), make_issue()) is None


def test_parse_defaults_missing_optional_fields():
    minimal = json.dumps({"category": "docs", "difficulty": "medium"})
    result = _parse_categorization(envelope(minimal), make_issue())
    assert result == {
        "category": "docs",
        "difficulty": "medium",
        "good_first_issue": False,
        "one_line_summary": "",
        "why_easy": "",
    }


# ─── categorize_issue (subprocess mocked) ─────────────────────────────────────

def test_categorize_returns_none_when_cli_missing(monkeypatch):
    def raise_not_found(*args, **kwargs):
        raise FileNotFoundError("claude")

    monkeypatch.setattr(categorize.subprocess, "run", raise_not_found)
    assert categorize_issue(make_issue()) is None


def test_categorize_returns_none_on_timeout(monkeypatch):
    def raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="claude", timeout=60)

    monkeypatch.setattr(categorize.subprocess, "run", raise_timeout)
    assert categorize_issue(make_issue()) is None


def test_categorize_returns_none_on_nonzero_exit(monkeypatch):
    def fail(*args, **kwargs):
        return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="boom")

    monkeypatch.setattr(categorize.subprocess, "run", fail)
    assert categorize_issue(make_issue()) is None


def test_categorize_parses_successful_run(monkeypatch):
    def succeed(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout=envelope(make_triage_json()), stderr=""
        )

    monkeypatch.setattr(categorize.subprocess, "run", succeed)
    result = categorize_issue(make_issue())
    assert result is not None
    assert result["category"] == "bug"
    assert result["difficulty"] == "easy"
