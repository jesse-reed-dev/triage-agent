import os
import requests
from dotenv import load_dotenv

# ─── Config ───────────────────────────────────────────────────────────────────

load_dotenv()  # reads .env file and loads variables into os.environ

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_API_VERSION = "2022-11-28"
REQUEST_TIMEOUT_SECONDS = 30


# ─── GitHub API client ────────────────────────────────────────────────────────

# headers are simply key : value pairs, order does not matter for the HTTP header
def make_headers() -> dict[str, str]:
    """
    Every request to GitHub needs these headers.
    Authorization proves who we are.
    Accept tells GitHub which version of their API we want.
    """
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
    }


def fetch_issues(repo: str, max_issues: int = 20) -> list[dict] | None:
    """
    Fetches open issues from a GitHub repo.
    Returns a list of issue dicts, or None if the repo timed out.

    Note: GitHub's /issues endpoint returns both issues AND pull requests.
    We filter out PRs below by checking for the 'pull_request' key.
    """
    url = f"https://api.github.com/repos/{repo}/issues"
    params = {
        "state": "open",
        "per_page": max_issues,
        "sort": "created",
        "direction": "desc",  # newest first
    }

    try:
        response = requests.get(url, headers=make_headers(), params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        # Raise an exception if the request failed (401 = bad token, 403/429 = rate limited, 404 = wrong repo)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        print(f"  Timed out fetching {repo} — skipping.")
        return None
    except requests.exceptions.RequestException as e:
        # One bad repo (rate limit, outage, typo) shouldn't kill the whole run —
        # skip it like a timeout and let the remaining repos report.
        print(f"  Failed to fetch {repo} ({e}) — skipping.")
        return None

    all_items = response.json()

    # Filter out pull requests — they share the same endpoint as issues
    issues_only = [item for item in all_items if "pull_request" not in item]

    return issues_only


# ─── Display ──────────────────────────────────────────────────────────────────

def print_issues(issues: list[dict], repo: str) -> None:
    """
    Pretty-prints issues to the terminal.
    This is temporary — in Day 5 this becomes an HTML email.
    """
    print(f"\n{'='*60}")
    print(f"  Open Issues: {repo}  ({len(issues)} shown)")
    print(f"{'='*60}\n")

    for issue in issues:
        number = issue["number"]
        title = issue["title"]
        labels = [label["name"] for label in issue["labels"]]
        url = issue["html_url"]
        created = issue["created_at"][:10]  # trim to YYYY-MM-DD

        print(f"#{number} [{created}] {title}")
        print(f"  Labels : {', '.join(labels) if labels else 'none'}")
        print(f"  URL    : {url}")
        print()