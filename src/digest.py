"""
Turns a run's categorized issues into the daily digest: a ranked markdown
report (written to data/) and an HTML body for the email version.

Ranking mirrors the skill's presentation order: easy + good-first-issue picks
first, then remaining easy, then medium, then hard. Within a tier, docs/test
issues sort above bugs/features since they're usually quicker to land.
Issues whose categorization failed go at the bottom as plain title + link.
"""

import html
import json
import os
from datetime import date

# ─── Config ───────────────────────────────────────────────────────────────────

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DATA_JSON_PATH = os.path.join(DATA_DIR, "data.json")

_CATEGORY_ORDER = {"docs": 0, "test": 1, "refactor": 2, "bug": 3, "feature": 4}

# (tier heading, emoji) in display order; tier 0 is computed specially below
_TIERS = [
    "🥇 Best picks — easy + good first issue",
    "🥈 Easy",
    "🥉 Medium",
    "🏋️ Hard",
]


# ─── Ranking ──────────────────────────────────────────────────────────────────

def _tier(triage: dict) -> int:
    """0 = easy + good first issue, 1 = easy, 2 = medium, 3 = hard."""
    if triage["difficulty"] == "easy":
        return 0 if triage["good_first_issue"] else 1
    return 2 if triage["difficulty"] == "medium" else 3


def split_and_rank(issues: list[dict]) -> tuple[list[list[dict]], list[dict]]:
    """
    Splits issues into ranked tiers plus the uncategorized leftovers.
    Returns (tiers, uncategorized) where tiers[i] matches _TIERS[i].
    """
    tiers: list[list[dict]] = [[], [], [], []]
    uncategorized = []

    for issue in issues:
        triage = issue.get("triage")
        if triage:
            tiers[_tier(triage)].append(issue)
        else:
            uncategorized.append(issue)

    for tier in tiers:
        tier.sort(key=lambda i: _CATEGORY_ORDER[i["triage"]["category"]])

    return tiers, uncategorized


# ─── Rendering ────────────────────────────────────────────────────────────────

def build_subject(issues: list[dict], run_date: date) -> str:
    tiers, _ = split_and_rank(issues)
    best = len(tiers[0])
    return f"Triage digest {run_date}: {best} best pick(s) of {len(issues)} new issue(s)"


def render_markdown(issues: list[dict], run_date: date) -> str:
    """
    Ranked markdown digest — written to data/ as the run's local artifact,
    and reused as the plain-text fallback part of the email.
    """
    tiers, uncategorized = split_and_rank(issues)

    lines = [f"# Triage digest — {run_date}", ""]
    lines.append(f"**{len(issues)} new issue(s)** found, {len(tiers[0])} best pick(s).")
    lines.append("")

    for heading, tier in zip(_TIERS, tiers):
        if not tier:
            continue
        lines.append(f"## {heading}")
        lines.append("")
        for issue in tier:
            t = issue["triage"]
            lines.append(
                f"- **{issue['repo']}** [#{issue['number']}]({issue['html_url']}) — "
                f"`{t['category']} | {t['difficulty']}` — {t['one_line_summary']} "
                f"*{t['why_easy']}*"
            )
        lines.append("")

    if uncategorized:
        lines.append("## Uncategorized (Claude call failed — title and link only)")
        lines.append("")
        for issue in uncategorized:
            lines.append(f"- **{issue['repo']}** [#{issue['number']}]({issue['html_url']}) — {issue['title']}")
        lines.append("")

    return "\n".join(lines)


# Email palette — light theme only: Gmail applies its own dark-mode recoloring
# to emails, so designing a second theme would just get overridden.
_INK = "#0b0b0b"
_INK_2 = "#52514e"
_MUTED = "#898781"
_GRID = "#e1e0d9"
_ACCENT = "#2a78d6"
_GOOD = "#0ca30c"
# Difficulty is ordinal, so it gets one hue light->dark, not traffic-light colors.
_DIFF_COLOR = {"easy": "#86b6ef", "medium": "#2a78d6", "hard": "#104281"}

_MONO = "ui-monospace,'SF Mono',Consolas,monospace"
_SANS = "-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"

_TIER_LABELS = ["Best picks — easy + good first issue", "Easy", "Medium", "Hard"]


def _swatch(color: str) -> str:
    return (
        f'<span style="display:inline-block;width:9px;height:9px;border-radius:2px;'
        f'background:{color}"></span>'
    )


def render_html(issues: list[dict], run_date: date) -> str:
    """
    HTML email body, styled to match the dashboard: KPI tiles, a static
    difficulty strip, and hairline-separated ledger rows. Email clients strip
    <style> blocks, CSS variables, and all JS, so everything is inline styles
    and tables — the interactive filters don't translate; tier grouping
    stands in for them. Everything from GitHub (titles, summaries) is
    escaped — it's untrusted content rendered in a mail client.
    """
    tiers, uncategorized = split_and_rank(issues)
    diff_counts = {
        d: sum(1 for i in issues if i.get("triage") and i["triage"]["difficulty"] == d)
        for d in ("easy", "medium", "hard")
    }

    def kpi(label: str, value: int, note: str) -> str:
        return (
            f'<td style="border:1px solid {_GRID};border-radius:4px;padding:10px 14px">'
            f'<div style="font-family:{_MONO};font-size:10px;letter-spacing:1px;'
            f'text-transform:uppercase;color:{_MUTED}">{label}</div>'
            f'<div style="font-family:{_SANS};font-size:26px;font-weight:700;color:{_INK}">{value}</div>'
            f'<div style="font-family:{_SANS};font-size:11px;color:{_INK_2}">{note}</div></td>'
        )

    def entry(issue: dict) -> str:
        t = issue["triage"]
        gfi = (
            f'<span style="font-family:{_MONO};font-size:11px;color:{_GOOD};'
            f'font-weight:700">&nbsp;&nbsp;&#9733; good first issue</span>'
            if t["good_first_issue"] else ""
        )
        return (
            f'<div style="border-top:1px solid {_GRID};padding:12px 0">'
            f'<div style="font-family:{_MONO};font-size:12px;color:{_INK_2}">'
            f'{html.escape(issue["repo"])}&nbsp;&nbsp;'
            f'<a href="{html.escape(issue["html_url"], quote=True)}" '
            f'style="color:{_ACCENT};font-weight:700;text-decoration:none">#{issue["number"]}</a>'
            f'&nbsp;&nbsp;{_swatch(_DIFF_COLOR[t["difficulty"]])} {html.escape(t["difficulty"])}'
            f'&nbsp;&nbsp;{html.escape(t["category"])}{gfi}</div>'
            f'<div style="font-family:{_SANS};font-size:14px;color:{_INK};'
            f'margin-top:4px;line-height:1.5">{html.escape(t["one_line_summary"])}</div>'
            f'<div style="font-family:{_SANS};font-size:12px;color:{_MUTED};'
            f'margin-top:2px;line-height:1.5">{html.escape(t["why_easy"])}</div></div>'
        )

    parts = [
        f'<div style="max-width:680px;margin:0 auto;font-family:{_SANS};color:{_INK}">',
        # Header
        f'<div style="padding:8px 0 4px;font-size:22px;font-weight:750;color:{_INK}">Triage</div>',
        f'<div style="font-family:{_MONO};font-size:11px;letter-spacing:1px;'
        f'text-transform:uppercase;color:{_MUTED};padding-bottom:16px">'
        f'Daily issue digest &middot; {run_date}</div>',
        # KPI tiles
        '<table role="presentation" width="100%" cellspacing="6" cellpadding="0"><tr>'
        + kpi("New issues", len(issues), "since last delivered run")
        + kpi("Best picks", len(tiers[0]), "easy + good first issue")
        + kpi("Easy overall", diff_counts["easy"], "across all repos")
        + "</tr></table>",
    ]

    # Difficulty strip: static version of the dashboard's clickable bar.
    if any(diff_counts.values()):
        total = sum(diff_counts.values())
        cells = "".join(
            f'<td width="{round(diff_counts[d] / total * 100)}%" '
            f'style="background:{_DIFF_COLOR[d]};height:10px;font-size:0;line-height:0">&nbsp;</td>'
            for d in ("easy", "medium", "hard") if diff_counts[d]
        )
        legend = "&nbsp;&nbsp;&nbsp;".join(
            f'{_swatch(_DIFF_COLOR[d])} {diff_counts[d]} {d}'
            for d in ("easy", "medium", "hard")
        )
        parts.append(
            '<table role="presentation" width="100%" cellspacing="2" cellpadding="0" '
            f'style="margin-top:14px"><tr>{cells}</tr></table>'
            f'<div style="font-family:{_MONO};font-size:11px;color:{_INK_2};'
            f'margin:8px 0 4px">{legend}</div>'
        )

    for label, tier in zip(_TIER_LABELS, tiers):
        if not tier:
            continue
        parts.append(
            f'<div style="font-family:{_MONO};font-size:11px;letter-spacing:1px;'
            f'text-transform:uppercase;color:{_MUTED};margin:22px 0 6px">{label}</div>'
        )
        parts.extend(entry(issue) for issue in tier)

    if uncategorized:
        parts.append(
            f'<div style="font-family:{_MONO};font-size:11px;letter-spacing:1px;'
            f'text-transform:uppercase;color:{_MUTED};margin:22px 0 6px">'
            "Uncategorized (Claude call failed)</div>"
        )
        for issue in uncategorized:
            parts.append(
                f'<div style="border-top:1px solid {_GRID};padding:10px 0;'
                f'font-family:{_MONO};font-size:12px;color:{_INK_2}">'
                f'{html.escape(issue["repo"])}&nbsp;&nbsp;'
                f'<a href="{html.escape(issue["html_url"], quote=True)}" '
                f'style="color:{_ACCENT};font-weight:700;text-decoration:none">#{issue["number"]}</a>'
                f'&nbsp;&nbsp;<span style="font-family:{_SANS};color:{_INK}">'
                f'{html.escape(issue["title"])}</span></div>'
            )

    parts.append(
        f'<div style="border-top:1px solid {_GRID};margin-top:20px;padding-top:10px;'
        f'font-family:{_MONO};font-size:11px;color:{_MUTED}">'
        "Triage Agent &middot; issues are ranked easiest first; "
        "difficulty runs light &rarr; dark</div>"
    )
    parts.append("</div>")
    return "\n".join(parts)


# ─── File output ──────────────────────────────────────────────────────────────

def write_digest_file(markdown: str, run_date: date) -> str:
    """
    Writes the markdown digest to data/digest-YYYY-MM-DD.md and returns the path.
    A second run on the same day overwrites the earlier file — the dedup DB
    means the second digest only contains issues the first one didn't deliver.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, f"digest-{run_date}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(markdown)
    return path


def _load_data_json() -> list[dict]:
    """
    Reads the existing dashboard records, tolerating a missing or corrupt file.
    A corrupt file is sidelined to data.json.corrupt rather than overwritten,
    so history can be recovered by hand, and the run continues fresh instead
    of crashing between email delivery and mark_seen.
    """
    if not os.path.exists(DATA_JSON_PATH):
        return []

    try:
        with open(DATA_JSON_PATH, encoding="utf-8") as f:
            return json.load(f)["issues"]
    except (json.JSONDecodeError, KeyError, TypeError):
        backup = DATA_JSON_PATH + ".corrupt"
        os.replace(DATA_JSON_PATH, backup)
        print(f"  data.json was unreadable — moved to {backup}, starting fresh.")
        return []


def append_data_json(issues: list[dict], run_date: date) -> str:
    """
    Appends this run's issues to data/data.json — the cumulative,
    machine-readable record the dashboard reads. Each record keeps just the
    fields the dashboard filters and displays; "triage" is null for issues
    whose categorization failed.

    Records are keyed by (repo, number): a re-triaged issue (its row deleted
    from the dedup DB by hand) replaces its old record instead of duplicating it.
    """
    records = _load_data_json()

    new_keys = {(i["repo"], i["number"]) for i in issues}
    records = [r for r in records if (r["repo"], r["number"]) not in new_keys]

    for issue in issues:
        records.append({
            "repo": issue["repo"],
            "number": issue["number"],
            "title": issue["title"],
            "url": issue["html_url"],
            "created_at": issue.get("created_at"),
            "digest_date": str(run_date),
            "triage": issue.get("triage"),
        })

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DATA_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump({"updated": str(run_date), "issues": records}, f, indent=2)
    return DATA_JSON_PATH
