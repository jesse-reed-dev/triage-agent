# Triage Agent

Scans ~20 active open source repos daily, runs new issues through Claude to rate category,
difficulty, and good-first-issue fit (with a one-line summary and reasoning for each), and
delivers a digest of contributor-friendly issues worth picking up.

Built in Python. Powered by Claude.

## Status

🚧 In progress — Day 5 of 8

## Planned features

- Fetch open issues from 20+ repos via GitHub REST API
- Categorize each issue via Claude (claude-haiku-4-5): category (bug/feature/docs/test/refactor),
  difficulty (easy/medium/hard), good-first-issue fit, a one-line summary, and reasoning
- Filter for `good first issue`, `help wanted`, and `documentation` labels
- Daily HTML email digest via Gmail SMTP, ranked easiest-first (best picks →
  easy → medium → hard), with a markdown copy saved to `data/`
- GitHub Pages dashboard filterable by repo and difficulty

## Setup (Day 3)

1. Clone the repo
2. Create a `.env` file with your GitHub token:
   GITHUB_TOKEN=your_token_here

3. Install dependencies:

```bash
   pip install -r requirements.txt
```

4. Make sure the [Claude Code CLI](https://code.claude.com) is installed and logged in
   (`claude` on your PATH) — categorization runs through it, so no separate API key needed.

5. Run the agent:

```bash
   python src/main.py
```

## Email digest (Day 5)

Each run delivers the digest by email when Gmail credentials are present in `.env`:

```
GMAIL_ADDRESS=you@gmail.com
GMAIL_APP_PASSWORD=your_app_password
DIGEST_TO=optional_recipient@example.com   # defaults to GMAIL_ADDRESS
```

`GMAIL_APP_PASSWORD` is a Gmail [app password](https://myaccount.google.com/apppasswords)
(requires 2FA), not the account password. Sending uses Python's stdlib `smtplib` —
no email-service account or extra dependency. Without these variables the run still
works: the digest is written to `data/digest-YYYY-MM-DD.md` either way.

Deduplication is **delivery-gated**: issues are marked seen only after the digest is
successfully delivered (email-send success, or the report write when email isn't
configured). A run that crashes or fails to send consumes nothing — the same issues
are picked up again next run.

## Claude Code skill (Day 4)

The repo ships a project skill at `.claude/skills/triage/SKILL.md`. Open Claude Code
in this repo and run:

```
/triage
```

Claude runs the pipeline and presents the results as a ranked digest — good-first-issue
easy picks at the top, uncategorized issues at the bottom. The skill also encodes the
operational knowledge (dedup semantics, run cadence, failure modes) so Claude handles
edge cases without being re-told each session.

## Architecture

_(Mermaid diagram coming Day 8)_

## Tech stack

- Python, GitHub REST API
- Claude Code CLI headless mode (`claude -p`, claude-haiku-4-5) for categorization —
  runs on the Claude Code subscription rather than a separate billed API key
- SQLite for deduplication
- GitHub Pages for dashboard
