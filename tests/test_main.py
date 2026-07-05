"""Tests for the pipeline orchestration (fetch/db/categorize mocked)."""

import main


def test_get_new_issues_skips_seen_and_tags_repo(monkeypatch):
    monkeypatch.setattr(main, "REPOS", ["owner/repo"])
    monkeypatch.setattr(
        main, "fetch_issues", lambda repo, max_issues: [{"number": 1}, {"number": 2}]
    )
    monkeypatch.setattr(main, "has_seen", lambda repo, number: number == 1)

    new_issues = main.get_new_issues()

    assert [i["number"] for i in new_issues] == [2]
    assert new_issues[0]["repo"] == "owner/repo"


def test_get_new_issues_skips_repos_that_failed_to_fetch(monkeypatch):
    monkeypatch.setattr(main, "REPOS", ["down/repo", "up/repo"])
    monkeypatch.setattr(
        main,
        "fetch_issues",
        lambda repo, max_issues: None if repo == "down/repo" else [{"number": 7}],
    )
    monkeypatch.setattr(main, "has_seen", lambda repo, number: False)

    new_issues = main.get_new_issues()

    assert [(i["repo"], i["number"]) for i in new_issues] == [("up/repo", 7)]


def test_mark_delivered_marks_every_issue(monkeypatch):
    marked = []
    monkeypatch.setattr(main, "mark_seen", lambda repo, number: marked.append((repo, number)))

    main.mark_delivered(
        [{"repo": "a/b", "number": 1}, {"repo": "c/d", "number": 2}]
    )

    assert marked == [("a/b", 1), ("c/d", 2)]


def test_categorize_new_issues_attaches_triage(monkeypatch):
    monkeypatch.setattr(main, "categorize_issue", lambda issue: {"category": "bug"})

    issues = [{"repo": "a/b", "number": 1}]
    main.categorize_new_issues(issues)

    assert issues[0]["triage"] == {"category": "bug"}
