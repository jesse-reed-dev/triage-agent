"""
Turns a run's categorized issues into the daily digest: a ranked markdown
report (written to data/) and an HTML body for the email version.

Ranking mirrors the skill's presentation order: easy + good-first-issue picks
first, then remaining easy, then medium, then hard. Within a tier, docs/test
issues sort above bugs/features since they're usually quicker to land.
Issues whose categorization failed go at the bottom as plain title + link.
"""

import html
import os
from datetime import date

# ─── Config ───────────────────────────────────────────────────────────────────

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

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


def render_html(issues: list[dict], run_date: date) -> str:
    """
    HTML email body. Everything from GitHub (titles, summaries) is escaped —
    it's untrusted content and this ends up rendered in a mail client.
    Styles are inline because email clients strip <style> blocks.
    """
    tiers, uncategorized = split_and_rank(issues)

    def entry(issue: dict) -> str:
        t = issue["triage"]
        return (
            '<li style="margin-bottom:12px;line-height:1.5">'
            f'<strong>{html.escape(issue["repo"])}</strong> '
            f'<a href="{html.escape(issue["html_url"], quote=True)}">#{issue["number"]}</a> '
            f'<code style="background:#f0f0f0;padding:1px 5px;border-radius:3px">'
            f'{html.escape(t["category"])} | {html.escape(t["difficulty"])}</code><br>'
            f'{html.escape(t["one_line_summary"])}<br>'
            f'<em style="color:#666">{html.escape(t["why_easy"])}</em>'
            "</li>"
        )

    parts = [
        '<div style="font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;'
        'max-width:680px;margin:0 auto;color:#1a1a1a">',
        f"<h1 style='font-size:20px'>Triage digest — {run_date}</h1>",
        f"<p><strong>{len(issues)} new issue(s)</strong> found, {len(tiers[0])} best pick(s).</p>",
    ]

    for heading, tier in zip(_TIERS, tiers):
        if not tier:
            continue
        parts.append(f"<h2 style='font-size:16px;margin-top:24px'>{heading}</h2>")
        parts.append("<ul style='padding-left:20px'>")
        parts.extend(entry(issue) for issue in tier)
        parts.append("</ul>")

    if uncategorized:
        parts.append("<h2 style='font-size:16px;margin-top:24px'>Uncategorized (Claude call failed)</h2>")
        parts.append("<ul style='padding-left:20px'>")
        for issue in uncategorized:
            parts.append(
                '<li style="margin-bottom:6px">'
                f'<strong>{html.escape(issue["repo"])}</strong> '
                f'<a href="{html.escape(issue["html_url"], quote=True)}">#{issue["number"]}</a> — '
                f'{html.escape(issue["title"])}</li>'
            )
        parts.append("</ul>")

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
