---
name: triage
description: Run the GitHub issue triage pipeline — fetch new issues from the curated repo list, categorize them with Claude, and present a digest of contributor-friendly issues. Use when the user asks to run triage, check for new issues, or find something to contribute to.
---

# Triage run

Run the pipeline, then present the digest it produces. Do not re-implement any
pipeline logic yourself — fetching, dedup, categorization, ranking, and delivery
all live in `src/`; your job is to run it and surface the results.

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
     the maximum Bash timeout (600000 ms).
   - If the run gets cut off before it finishes, it is **safe to re-run**: issues
     are only marked seen after the digest is successfully delivered, so an
     interrupted run consumes nothing and the next run picks the same issues up
     again.
   - `GITHUB_TOKEN not found` means `.env` is missing or incomplete — ask the user to
     add `GITHUB_TOKEN=...` to `.env` at the repo root. Don't guess or set one yourself.
   - Per-issue lines like `Claude CLI error ...` or `Categorization timed out ...` are
     non-fatal; those issues show up in the digest's "Uncategorized" section and the
     run is still valid.

2. Present the results. The pipeline writes a ranked markdown digest to
   `data/digest-YYYY-MM-DD.md` (best picks first, uncategorized issues at the
   bottom) and, when email is configured, also emails it. Read that file and
   relay it — summarize the top picks, don't re-rank or reformat.
   - If the output says `No new issues since last run`, report that and stop —
     that is correct behavior, not a bug (see dedup note below).
   - If the output says `Digest NOT delivered` (email send failed), tell the user:
     the digest file was still written, nothing was marked seen, and the same
     issues will be retried next run. Surface the SMTP error from the output.

## Run cadence

This is designed as a **daily digest** — one run per day via a systemd user
timer (`triage-agent.timer`, 5 AM machine-local time, `Persistent=true` so a
run missed while the machine slept fires on wake). Unit files live in
`deploy/systemd/`; check status with `systemctl --user list-timers
triage-agent.timer`; output appends to `data/triage.log`. Extra runs are safe
(nothing breaks, nothing is double-reported), but every *delivered* run
consumes the "new issues" pool: results are always _issues created since the
last delivered run, whenever that was_. So warn the user before running
manually — an extra run now would leave the next morning's scheduled digest
nearly empty. An immediate re-run always reports "no new issues"; that is
correct behavior, not a bug.

## Things to know

- **Dedup is delivery-gated.** An issue is marked seen in `data/seen_issues.db`
  only after the digest containing it is successfully **delivered** — email-send
  success when email is configured, otherwise the report file write. A run that
  crashes, times out, or fails to send marks nothing, so those issues are
  retried automatically next run. Uncategorized issues in a delivered digest
  are marked seen too (their title + link were delivered). To re-triage one
  issue, delete its row first:

  ```bash
  sqlite3 data/seen_issues.db "DELETE FROM seen_issues WHERE repo='owner/name' AND issue_number=123"
  ```

- **Email is optional.** With `GMAIL_ADDRESS` and `GMAIL_APP_PASSWORD` in `.env`
  the digest is emailed via Gmail SMTP (`DIGEST_TO` overrides the recipient,
  defaulting to the sender). Without them the run still works — the report file
  counts as delivery. Never print or echo the app password.
- The repo watchlist lives in `src/repos.py` — edit that list if the user asks to
  add or remove a repo.
- The categorization prompt, model, and output validation live in `src/categorize.py`.
- Digest ranking and rendering (markdown + email HTML) live in `src/digest.py`;
  SMTP sending lives in `src/emailer.py`.
