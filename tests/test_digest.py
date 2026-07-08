"""Tests for digest ranking and rendering."""

import json
from datetime import date

import pytest

import digest
from digest import (
    append_data_json,
    build_subject,
    render_html,
    render_markdown,
    split_and_rank,
)

RUN_DATE = date(2026, 7, 4)


def make_issue(number=1, category="bug", difficulty="easy", good_first_issue=False, **overrides):
    issue = {
        "repo": "owner/repo",
        "number": number,
        "title": f"Issue {number}",
        "html_url": f"https://github.com/owner/repo/issues/{number}",
        "triage": {
            "category": category,
            "difficulty": difficulty,
            "good_first_issue": good_first_issue,
            "one_line_summary": f"Summary of issue {number}.",
            "why_easy": "Because reasons.",
        },
    }
    issue.update(overrides)
    return issue


def make_uncategorized(number=99, **overrides):
    issue = make_issue(number=number, **overrides)
    issue["triage"] = None
    return issue


# ─── split_and_rank ───────────────────────────────────────────────────────────

def test_issues_land_in_the_right_tiers():
    best = make_issue(1, difficulty="easy", good_first_issue=True)
    easy = make_issue(2, difficulty="easy")
    medium = make_issue(3, difficulty="medium")
    hard = make_issue(4, difficulty="hard")

    tiers, uncategorized = split_and_rank([hard, medium, easy, best])

    assert [i["number"] for tier in tiers for i in tier] == [1, 2, 3, 4]
    assert uncategorized == []


def test_uncategorized_issues_are_split_out():
    tiers, uncategorized = split_and_rank([make_issue(1), make_uncategorized(2)])
    assert [i["number"] for i in tiers[1]] == [1]
    assert [i["number"] for i in uncategorized] == [2]


def test_docs_sort_before_bugs_within_a_tier():
    bug = make_issue(1, category="bug")
    docs = make_issue(2, category="docs")
    test_cat = make_issue(3, category="test")

    tiers, _ = split_and_rank([bug, test_cat, docs])

    assert [i["triage"]["category"] for i in tiers[1]] == ["docs", "test", "bug"]


# ─── build_subject ────────────────────────────────────────────────────────────

def test_subject_counts_best_picks_and_total():
    issues = [
        make_issue(1, difficulty="easy", good_first_issue=True),
        make_issue(2, difficulty="hard"),
        make_issue(3, difficulty="medium"),
    ]
    assert build_subject(issues, RUN_DATE) == (
        "Triage digest 2026-07-04: 1 best pick(s) of 3 new issue(s)"
    )


# ─── render_markdown ──────────────────────────────────────────────────────────

def test_markdown_includes_issue_links_and_ratings():
    md = render_markdown([make_issue(7, category="docs", difficulty="easy")], RUN_DATE)
    assert "# Triage digest — 2026-07-04" in md
    assert "[#7](https://github.com/owner/repo/issues/7)" in md
    assert "`docs | easy`" in md


def test_markdown_omits_empty_tiers():
    md = render_markdown([make_issue(1, difficulty="hard")], RUN_DATE)
    assert "🏋️ Hard" in md
    assert "🥇" not in md
    assert "🥈" not in md
    assert "🥉" not in md


def test_markdown_lists_uncategorized_with_title_only():
    md = render_markdown([make_uncategorized(5, title="Mystery issue")], RUN_DATE)
    assert "## Uncategorized" in md
    assert "Mystery issue" in md


# ─── render_html ──────────────────────────────────────────────────────────────

def test_html_escapes_untrusted_summary():
    issue = make_issue(1)
    issue["triage"]["one_line_summary"] = '<script>alert("xss")</script>'
    html_out = render_html([issue], RUN_DATE)
    assert "<script>" not in html_out
    assert "&lt;script&gt;" in html_out


def test_html_escapes_untrusted_title_in_uncategorized():
    html_out = render_html([make_uncategorized(2, title="<img src=x>")], RUN_DATE)
    assert "<img" not in html_out
    assert "&lt;img" in html_out


def test_html_links_each_issue():
    # Check the href and the link text, not the exact markup — the anchor
    # also carries inline styles (email clients strip <style> blocks).
    html_out = render_html([make_issue(9)], RUN_DATE)
    assert 'href="https://github.com/owner/repo/issues/9"' in html_out
    assert ">#9</a>" in html_out


# ─── append_data_json ─────────────────────────────────────────────────────────

@pytest.fixture
def data_json(tmp_path, monkeypatch):
    """Point the module at a throwaway data.json and return its path."""
    path = tmp_path / "data.json"
    monkeypatch.setattr(digest, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(digest, "DATA_JSON_PATH", str(path))
    return path


def read_records(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)["issues"]


def test_append_creates_file_with_dashboard_fields(data_json):
    append_data_json([make_issue(1, category="docs")], RUN_DATE)

    records = read_records(data_json)
    assert len(records) == 1
    record = records[0]
    assert record["repo"] == "owner/repo"
    assert record["number"] == 1
    assert record["url"] == "https://github.com/owner/repo/issues/1"
    assert record["digest_date"] == "2026-07-04"
    assert record["triage"]["category"] == "docs"


def test_append_accumulates_across_runs(data_json):
    append_data_json([make_issue(1)], RUN_DATE)
    append_data_json([make_issue(2)], date(2026, 7, 5))

    records = read_records(data_json)
    assert [r["number"] for r in records] == [1, 2]
    assert [r["digest_date"] for r in records] == ["2026-07-04", "2026-07-05"]


def test_reappending_same_issue_replaces_not_duplicates(data_json):
    append_data_json([make_issue(1, difficulty="hard")], RUN_DATE)
    append_data_json([make_issue(1, difficulty="easy")], date(2026, 7, 5))

    records = read_records(data_json)
    assert len(records) == 1
    assert records[0]["triage"]["difficulty"] == "easy"


def test_uncategorized_issue_stored_with_null_triage(data_json):
    append_data_json([make_uncategorized(3)], RUN_DATE)
    assert read_records(data_json)[0]["triage"] is None


def test_corrupt_data_json_is_sidelined_not_crashed(data_json):
    data_json.write_text("{ not json")

    append_data_json([make_issue(1)], RUN_DATE)

    assert [r["number"] for r in read_records(data_json)] == [1]
    backup = data_json.with_suffix(".json.corrupt")
    assert backup.read_text() == "{ not json"
