# Triage Agent

Scans ~20 active open source repos daily, runs new issues through Claude to categorize
difficulty and contributor-friendliness, and delivers a digest of contributor-friendly
issues worth picking up.

Built in Python. Powered by Claude.

## Status

🚧 In progress — Day 2 of 8

## Planned features

- Fetch open issues from 20+ repos via GitHub REST API
- Categorize issues by difficulty and contributor-friendliness using Claude (claude-haiku-4-5)
- Filter for `good first issue`, `help wanted`, and `documentation` labels
- Daily HTML email digest grouped by repo, easy issues first
- GitHub Pages dashboard filterable by repo and difficulty

## Setup (Day 2)

1. Clone the repo
2. Create a `.env` file with your GitHub token:
   GITHUB_TOKEN=your_token_here

3. Install dependencies:

```bash
   pip install -r requirements.txt
```

4. Run the fetcher:

```bash
   python src/main.py
```

## Architecture

_(Mermaid diagram coming Day 8)_

## Tech stack

- Python, GitHub REST API
- Claude API (claude-haiku-4-5) for categorization
- SQLite for deduplication
- GitHub Pages for dashboard
