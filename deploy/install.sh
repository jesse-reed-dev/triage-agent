#!/usr/bin/env bash
# One-command install of the daily triage schedule (systemd user timer,
# 5 AM machine-local time, catches up after sleep). Linux only — see the
# README for prerequisites (venv, .env, claude CLI login).
#
# Safe to re-run: re-copies the units and reloads without disturbing an
# already-armed timer or its catch-up stamp.

set -euo pipefail
cd "$(dirname "$0")"

mkdir -p ~/.config/systemd/user
cp systemd/triage-agent.service systemd/triage-agent.timer ~/.config/systemd/user/
systemctl --user daemon-reload

# Seed the Persistent=true stamp so the first enable doesn't fire an
# immediate catch-up run. Only if absent — touching an existing stamp
# would postpone a genuinely pending catch-up.
stamp=~/.local/share/systemd/timers/stamp-triage-agent.timer
if [ ! -f "$stamp" ]; then
    mkdir -p "$(dirname "$stamp")"
    touch "$stamp"
fi

systemctl --user enable --now triage-agent.timer

echo
echo "Installed. Next scheduled run:"
systemctl --user list-timers triage-agent.timer --no-pager
