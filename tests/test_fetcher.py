"""Tests for the GitHub API client (network calls mocked)."""

import requests

import fetcher
from fetcher import fetch_issues, make_headers


class FakeResponse:
    def __init__(self, items, status_ok=True):
        self._items = items
        self._status_ok = status_ok

    def raise_for_status(self):
        if not self._status_ok:
            raise requests.exceptions.HTTPError("404 Client Error")

    def json(self):
        return self._items


# ─── make_headers ─────────────────────────────────────────────────────────────

def test_headers_carry_token_and_api_version(monkeypatch):
    monkeypatch.setattr(fetcher, "GITHUB_TOKEN", "test-token")
    headers = make_headers()
    assert headers["Authorization"] == "Bearer test-token"
    assert headers["Accept"] == "application/vnd.github+json"
    assert headers["X-GitHub-Api-Version"] == fetcher.GITHUB_API_VERSION


# ─── fetch_issues ─────────────────────────────────────────────────────────────

def test_fetch_filters_out_pull_requests(monkeypatch):
    items = [
        {"number": 1, "title": "A real issue"},
        {"number": 2, "title": "A PR", "pull_request": {"url": "..."}},
        {"number": 3, "title": "Another issue"},
    ]
    monkeypatch.setattr(fetcher.requests, "get", lambda *a, **kw: FakeResponse(items))

    issues = fetch_issues("owner/repo")

    assert [i["number"] for i in issues] == [1, 3]


def test_fetch_returns_none_on_timeout(monkeypatch):
    def raise_timeout(*args, **kwargs):
        raise requests.exceptions.Timeout()

    monkeypatch.setattr(fetcher.requests, "get", raise_timeout)
    assert fetch_issues("owner/repo") is None


def test_fetch_returns_none_on_http_error(monkeypatch):
    monkeypatch.setattr(
        fetcher.requests, "get", lambda *a, **kw: FakeResponse([], status_ok=False)
    )
    assert fetch_issues("owner/repo") is None


def test_fetch_requests_the_right_url_and_params(monkeypatch):
    captured = {}

    def capture(url, headers=None, params=None, timeout=None):
        captured.update(url=url, params=params, timeout=timeout)
        return FakeResponse([])

    monkeypatch.setattr(fetcher.requests, "get", capture)
    fetch_issues("owner/repo", max_issues=5)

    assert captured["url"] == "https://api.github.com/repos/owner/repo/issues"
    assert captured["params"]["per_page"] == 5
    assert captured["params"]["state"] == "open"
    assert captured["timeout"] == fetcher.REQUEST_TIMEOUT_SECONDS
