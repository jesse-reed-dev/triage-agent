"""Tests for the seen-issues dedup database."""

import pytest

import db


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Point the module at a throwaway database file for each test."""
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "seen_issues.db"))
    db.init_db()


def test_unseen_issue_returns_false(temp_db):
    assert db.has_seen("owner/repo", 123) is False


def test_mark_seen_then_has_seen(temp_db):
    db.mark_seen("owner/repo", 123)
    assert db.has_seen("owner/repo", 123) is True


def test_same_number_different_repo_is_distinct(temp_db):
    db.mark_seen("owner/repo", 123)
    assert db.has_seen("other/repo", 123) is False


def test_mark_seen_is_idempotent(temp_db):
    db.mark_seen("owner/repo", 123)
    db.mark_seen("owner/repo", 123)  # must not raise on the duplicate
    assert db.has_seen("owner/repo", 123) is True


def test_init_db_is_safe_to_call_twice(temp_db):
    db.mark_seen("owner/repo", 1)
    db.init_db()  # re-running setup must not wipe existing rows
    assert db.has_seen("owner/repo", 1) is True
