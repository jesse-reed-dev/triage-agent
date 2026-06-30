import os
import requests
from dotenv import load_dotenv

# ─── Config ───────────────────────────────────────────────────────────────────

load_dotenv()  # reads .env file and loads variables into os.environ

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_API_VERSION = "2022-11-28"


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


def fetch_issues(repo: str, max_issues: int = 20) -> list[dict]:
    """
    Fetches open issues from a GitHub repo.
    Returns a list of issue dicts.

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

    response = requests.get(url, headers=make_headers(), params=params)

    # Raise an exception if the request failed (401 = bad token, 404 = wrong repo)
    response.raise_for_status()

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