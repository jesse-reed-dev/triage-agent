from fetcher import fetch_issues, GITHUB_TOKEN
from repos import REPOS
from db import init_db, has_seen, mark_seen
from categorize import categorize_issue

MAX_ISSUES_PER_REPO = 20


def get_new_issues():
    """
    Loops through every repo, fetches issues, and keeps only the ones
    we haven't seen before. Marks them as seen along the way.
    """
    new_issues = []

    for repo in REPOS:
        print(f"Checking {repo}...")
        issues = fetch_issues(repo, MAX_ISSUES_PER_REPO)

        if issues is None:
            continue  # timed out — fetch_issues already logged it

        for issue in issues:
            number = issue["number"]

            if has_seen(repo, number):
                continue  # already reported, skip it

            mark_seen(repo, number)
            issue["repo"] = repo  # tag it so we know where it came from
            new_issues.append(issue)

    return new_issues


def categorize_new_issues(issues: list[dict]) -> None:
    """
    Rates each new issue via Claude and attaches the result as issue["triage"].
    Mutates issues in place so callers just keep using the same list.
    """
    for issue in issues:
        print(f"Categorizing [{issue['repo']}] #{issue['number']}...")
        issue["triage"] = categorize_issue(issue)


def print_new_issues(issues: list[dict]) -> None:
    if not issues:
        print("\nNo new issues since last run.")
        return

    print(f"\n{'='*60}")
    print(f"  {len(issues)} new issue(s) found")
    print(f"{'='*60}\n")

    for issue in issues:
        print(f"[{issue['repo']}] #{issue['number']}: {issue['title']}")
        print(f"  {issue['html_url']}")

        triage = issue.get("triage")
        if triage:
            good_first = "yes" if triage["good_first_issue"] else "no"
            print(f"  {triage['category']} | {triage['difficulty']} | good first issue: {good_first}")
            print(f"  Summary : {triage['one_line_summary']}")
            print(f"  Why     : {triage['why_easy']}")
        else:
            print("  Uncategorized (Claude CLI call failed)")

        print()


def main():
    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN not found. Check your .env file.")

    init_db()
    new_issues = get_new_issues()
    categorize_new_issues(new_issues)
    print_new_issues(new_issues)


if __name__ == "__main__":
    main()