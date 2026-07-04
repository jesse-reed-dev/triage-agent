---
name: triage
description: Run the GitHub issue triage pipeline — fetch new issues from the curated repo list, categorize them with Claude, and present a digest of contributor-friendly issues. Use when the user asks to run triage, check for new issues, or find something to contribute to.
---

# Triage run

Run the pipeline, then turn its terminal output into a ranked digest of issues worth
picking up. Do not re-implement any pipeline logic yourself — fetching, dedup, and
categorization all live in `src/`; your job is to run it and present the results well.

## Steps

1. Run the pipeline from the repo root:

   ```bash
   source .venv/bin/activate && python3 -u src/main.py
   ```

   (Activating the venv matters — the deps are installed there, not for system
   `python3`. The `-u` keeps output unbuffered so nothing is lost if the run is
   cut short.)

   - A run with many new issues can take several minutes: each new issue is one
     `claude -p` call with a 60-second timeout. Run it in the **foreground** with
     the maximum Bash timeout (600000 ms). Do **not** run it in the background:
     if the session ends before the run finishes, the process dies — and since
     issues are marked seen the moment they're fetched, the day's issues get
     consumed without ever producing a digest.
   - If the run does get cut off by the timeout, present whatever partial results
     it printed — do not re-run (the remaining issues are already marked seen).
   - `GITHUB_TOKEN not found` means `.env` is missing or incomplete — ask the user to
     add `GITHUB_TOKEN=...` to `.env` at the repo root. Don't guess or set one yourself.
   - Per-issue lines like `Claude CLI error ...` or `Categorization timed out ...` are
     non-fatal; those issues show up as "Uncategorized" and the run is still valid.

2. Present the results as a digest, best picks first:
   - **Rank order:** `good_first_issue` + `easy` first, then remaining `easy`, then
     `medium`, then `hard`. Within a tier, put `docs`/`test` issues above `bug`/`feature`.
   - **Each entry:** repo, issue number linked to its URL, `category | difficulty`,
     the one-line summary, and the "why easy/hard" line.
   - **Uncategorized issues** go at the bottom as a plain title + link list.
   - If the output says `No new issues since last run`, report that and stop —
     do **not** re-run to try to force results (see dedup note below).

## Run cadence

This is designed as a **daily digest** — one run per day, eventually via a scheduled
Routine. Extra runs are safe (nothing breaks, nothing is double-reported), but every
run consumes the "new issues" pool: results are always _issues created since the last
run, whenever that was_. So warn the user before running if it looks like a scheduled
daily run is about to happen soon — an extra run now would leave that digest nearly
empty. An immediate re-run always reports "no new issues"; that is correct behavior,
not a bug.

## Things to know

- **Dedup is by design.** Every fetched issue is marked seen in `data/seen_issues.db`
  the moment it's fetched — even if its categorization fails — so an immediate re-run
  always reports no new issues. To re-triage one issue, delete its row first:

  ```bash
  sqlite3 data/seen_issues.db "DELETE FROM seen_issues WHERE repo='owner/name' AND issue_number=123"
  ```

- The repo watchlist lives in `src/repos.py` — edit that list if the user asks to
  add or remove a repo.
- The categorization prompt, model, and output validation live in `src/categorize.py`.
