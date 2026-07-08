import sys
from datetime import date

from fetcher import fetch_issues, GITHUB_TOKEN
from repos import REPOS
from db import init_db, has_seen, mark_seen
from categorize import categorize_issue
from digest import append_data_json, build_subject, render_markdown, render_html, write_digest_file
from emailer import email_configured, send_digest, DIGEST_TO

MAX_ISSUES_PER_REPO = 20


def get_new_issues():
    """
    Loops through every repo, fetches issues, and keeps only the ones
    we haven't seen before.

    Deliberately does NOT mark them seen here: marking happens only after
    the digest is successfully delivered (see mark_delivered), so a run
    that dies mid-way doesn't consume the day's issues without producing
    a digest. The whole run is transactional — deliver or retry next time.
    """
    new_issues = []

    for repo in REPOS:
        print(f"Checking {repo}...")
        issues = fetch_issues(repo, MAX_ISSUES_PER_REPO)

        if issues is None:
            continue  # timed out — fetch_issues already logged it

        for issue in issues:
            if has_seen(repo, issue["number"]):
                continue  # already delivered in an earlier digest, skip it

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


def mark_delivered(issues: list[dict]) -> None:
    """
    The second half of dedup: once the digest containing these issues has
    been delivered, record them so they don't show up again tomorrow.
    Uncategorized issues count too — their title + link made it into the
    digest, so they were delivered, just without a rating.
    """
    for issue in issues:
        mark_seen(issue["repo"], issue["number"])


def main():
    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN not found. Check your .env file.")

    init_db()
    new_issues = get_new_issues()

    if not new_issues:
        print("\nNo new issues since last run.")
        return

    print(f"\n{len(new_issues)} new issue(s) found.")
    categorize_new_issues(new_issues)

    # Build and deliver the digest. Delivery means email-send success when
    # email is configured, otherwise a successful report file write. Only
    # after delivery do the issues get marked seen.
    run_date = date.today()
    markdown = render_markdown(new_issues, run_date)
    path = write_digest_file(markdown, run_date)
    print(f"\nReport written to {path}")

    if email_configured():
        if not send_digest(build_subject(new_issues, run_date), markdown, render_html(new_issues, run_date)):
            print("Digest NOT delivered — issues left unmarked so the next run retries them.")
            sys.exit(1)
        print(f"Digest emailed to {DIGEST_TO}")
    else:
        print("Email not configured (GMAIL_ADDRESS / GMAIL_APP_PASSWORD in .env) — "
              "the report write above counts as delivery.")

    # Delivered — record the run for the dashboard, then mark seen. Order
    # matters: if the data.json write dies, nothing is marked and the next
    # run retries; replace-by-key in append_data_json keeps that dedup-safe.
    data_path = append_data_json(new_issues, run_date)
    print(f"Dashboard data updated: {data_path}")

    mark_delivered(new_issues)
    print(f"{len(new_issues)} issue(s) marked seen.")


if __name__ == "__main__":
    main()
