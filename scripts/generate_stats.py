"""Builds output/stats.svg, output/languages.svg and output/skills.svg for the profile README.

Uses only the standard library. Reads STATS_TOKEN (optional, also counts private
contributions) or GITHUB_TOKEN from the environment.
"""
import json
import os
import urllib.request
from datetime import datetime, timezone
from html import escape

USER = "Aldafoor3"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")

BG, BORDER, TEXT, MUTED, ACCENT = "#0d1117", "#30363d", "#e6edf3", "#8b949e", "#39d353"
FONT = "font-family=\"'Segoe UI', Ubuntu, 'Helvetica Neue', sans-serif\""

# Grouped like the Skills section of the portfolio (js/data.js)
SKILLS = [
    ("Languages", ["Java", "TypeScript", "Python", "SQL", "C++", "Dart", "Pascal"]),
    ("Frameworks", ["Spring Boot", "Angular", "React", "Flutter", "Flask", "FastAPI", "Streamlit"]),
    ("ML & Data", ["PyTorch", "scikit-learn", "pandas", "NumPy", "OpenCV"]),
    ("Tools", ["Git", "Docker", "PostgreSQL", "MySQL", "HMI"]),
]


def graphql(query, variables=None):
    token = os.environ.get("STATS_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("Set GITHUB_TOKEN or STATS_TOKEN")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables or {}}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": USER},
    )
    with urllib.request.urlopen(req) as res:
        body = json.load(res)
    if "errors" in body:
        raise SystemExit(body["errors"])
    return body["data"]


def fetch():
    user = graphql(
        """query($login: String!) {
          user(login: $login) {
            createdAt
            repositories(ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false, first: 100) {
              totalCount
              nodes { languages(first: 10) { edges { size node { name color } } } }
            }
          }
        }""",
        {"login": USER},
    )["user"]

    # contributionsCollection covers at most one year, so walk year by year
    start = datetime.fromisoformat(user["createdAt"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    total, commits = 0, 0
    for year in range(start.year, now.year + 1):
        frm = max(start, datetime(year, 1, 1, tzinfo=timezone.utc))
        to = min(now, datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc))
        cc = graphql(
            """query($login: String!, $from: DateTime!, $to: DateTime!) {
              user(login: $login) { contributionsCollection(from: $from, to: $to) {
                totalCommitContributions restrictedContributionsCount
                contributionCalendar { totalContributions } } }
            }""",
            {"login": USER, "from": frm.isoformat(), "to": to.isoformat()},
        )["user"]["contributionsCollection"]
        total += cc["contributionCalendar"]["totalContributions"]
        commits += cc["totalCommitContributions"] + cc["restrictedContributionsCount"]

    langs = {}
    for repo in user["repositories"]["nodes"]:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            size, color = langs.get(name, (0, edge["node"]["color"] or MUTED))
            langs[name] = (size + edge["size"], color)

    return {
        "since": start.year,
        "contributions": total,
        "commits": commits,
        "repos": user["repositories"]["totalCount"],
        "langs": sorted(langs.items(), key=lambda kv: -kv[1][0])[:8],
    }


def card(width, height, title, body):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="6" fill="{BG}" stroke="{BORDER}"/>'
        f'<text x="24" y="36" {FONT} font-size="17" font-weight="600" fill="{ACCENT}">{escape(title)}</text>'
        f"{body}</svg>\n"
    )


def stats_svg(s):
    rows = [
        ("Total contributions", s["contributions"]),
        ("Commits", s["commits"]),
        ("Public repositories", s["repos"]),
        ("On GitHub since", s["since"]),
    ]
    body = "".join(
        f'<text x="24" y="{72 + i * 26}" {FONT} font-size="14" fill="{MUTED}">{label}</text>'
        f'<text x="336" y="{72 + i * 26}" {FONT} font-size="14" font-weight="600" fill="{TEXT}" text-anchor="end">{value}</text>'
        for i, (label, value) in enumerate(rows)
    )
    return card(360, 72 + len(rows) * 26, "GitHub Stats", body)


def languages_svg(s):
    total = sum(size for _, (size, _) in s["langs"]) or 1
    bar, x = "", 24.0
    for name, (size, color) in s["langs"]:
        w = 312 * size / total
        bar += f'<rect x="{x:.1f}" y="54" width="{w:.1f}" height="10" fill="{color}"/>'
        x += w
    bar = f'<clipPath id="r"><rect x="24" y="54" width="312" height="10" rx="5"/></clipPath><g clip-path="url(#r)">{bar}</g>'
    legend = ""
    for i, (name, (size, color)) in enumerate(s["langs"]):
        cx, cy = 24 + (i % 2) * 160, 92 + (i // 2) * 24
        legend += (
            f'<circle cx="{cx + 5}" cy="{cy - 4}" r="5" fill="{color}"/>'
            f'<text x="{cx + 16}" y="{cy}" {FONT} font-size="13" fill="{TEXT}">{escape(name)} '
            f'<tspan fill="{MUTED}">{100 * size / total:.1f}%</tspan></text>'
        )
    rows = (len(s["langs"]) + 1) // 2
    return card(360, 88 + rows * 24, "Top Languages", bar + legend)


def skills_svg():
    width, body, y = 0, "", 70
    for group, items in SKILLS:
        body += f'<text x="24" y="{y + 19}" {FONT} font-size="13" font-weight="600" fill="{MUTED}">{escape(group)}</text>'
        x = 140
        for item in items:
            w = 22 + 7.6 * len(item)
            body += (
                f'<rect x="{x}" y="{y}" width="{w:.0f}" height="28" rx="14" fill="#161b22" stroke="{BORDER}"/>'
                f'<text x="{x + w / 2:.0f}" y="{y + 19}" {FONT} font-size="13" fill="{TEXT}" text-anchor="middle">{escape(item)}</text>'
            )
            x += w + 8
        width = max(width, int(x) + 16)
        y += 42
    return card(width, y + 10, "Tech Stack", body)


def main():
    os.makedirs(OUT, exist_ok=True)
    s = fetch()
    for name, svg in [("stats.svg", stats_svg(s)), ("languages.svg", languages_svg(s)), ("skills.svg", skills_svg())]:
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            f.write(svg)
    print(json.dumps({k: v for k, v in s.items() if k != "langs"}))


if __name__ == "__main__":
    main()
