"""Builds the SVGs in output/ for the profile README: header, stats, languages and inventory.

Styled like the block-world portfolio (grass-topped panels, pixel font).
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

BG, TEXT, MUTED = "#1b1b1f", "#f2f2f2", "#a5a5ad"
GRASS, GRASS_DARK, DIRT, DIRT_DARK, GOLD = "#5d9b2d", "#4a7d23", "#86603d", "#6b4c30", "#f2c94c"
PIXEL = "font-family=\"'Press Start 2P', 'Courier New', monospace\" font-weight=\"bold\""
MONO = "font-family=\"Consolas, 'DejaVu Sans Mono', monospace\""

# Same skills and colors as the portfolio (js/data.js)
SKILLS = [
    ("Languages", [("Java", "#e76f00"), ("TypeScript", "#3178c6"), ("Python", "#f2c94c"), ("SQL", "#3d8bd9"),
                   ("C++", "#5c8dbc"), ("Dart", "#2bb7f6"), ("Pascal", "#8a6dd8")]),
    ("Frameworks", [("Spring Boot", "#6db33f"), ("Angular", "#dd0031"), ("React", "#61dafb"), ("Flutter", "#47c5fb"),
                    ("Flask", "#d0d0d0"), ("FastAPI", "#05998b"), ("Streamlit", "#ff4b4b")]),
    ("ML & Data", [("PyTorch", "#ee4c2c"), ("scikit-learn", "#f7931e"), ("pandas", "#8f7ce8"), ("NumPy", "#4dabcf"),
                   ("OpenCV", "#5bd35b")]),
    ("Tools", [("Git", "#f05033"), ("Docker", "#2496ed"), ("PostgreSQL", "#6c9bd2"), ("MySQL", "#f29111"),
               ("HMI", "#9bd36a")]),
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


def grass(width, y=0, h=10):
    """Grass strip with a jagged pixel edge, like the top of a grass block."""
    out = f'<rect x="0" y="{y}" width="{width}" height="{h}" fill="{GRASS}"/>'
    for i, x in enumerate(range(0, width, 8)):
        if i % 3 != 1:
            out += f'<rect x="{x}" y="{y + h}" width="8" height="{4 if i % 2 else 8}" fill="{GRASS_DARK}"/>'
    return out


def svg(width, height, body):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" shape-rendering="crispEdges">{body}'
        f'<rect x="2" y="2" width="{width - 4}" height="{height - 4}" fill="none" stroke="#000" stroke-width="4"/></svg>\n'
    )


def panel(width, height, title, body):
    return svg(width, height,
               f'<rect width="{width}" height="{height}" fill="{BG}"/>{grass(width)}'
               f'<text x="22" y="50" {PIXEL} font-size="13" fill="{GOLD}">{escape(title)}</text>{body}')


def header_svg():
    w, h, ground = 880, 210, 160
    stars = "".join(
        f'<rect x="{(i * 97) % w}" y="{(i * 37) % 90 + 8}" width="3" height="3" fill="#fff">'
        f'<animate attributeName="opacity" values="1;0.2;1" dur="{2 + i % 4}s" repeatCount="indefinite"/></rect>'
        for i in range(1, 22)
    )
    dirt = f'<rect x="0" y="{ground + 12}" width="{w}" height="{h - ground - 12}" fill="{DIRT}"/>' + "".join(
        f'<rect x="{x}" y="{ground + 24 + (x // 8 % 3) * 8}" width="8" height="8" fill="{DIRT_DARK}"/>'
        for x in range(4, w, 40)
    )
    return svg(w, h,
               '<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">'
               '<stop offset="0" stop-color="#1a2a4f"/><stop offset="1" stop-color="#3d5a8a"/></linearGradient></defs>'
               f'<rect width="{w}" height="{h}" fill="url(#sky)"/>{stars}{grass(w, ground, 12)}{dirt}'
               f'<text x="443" y="81" {PIXEL} font-size="34" fill="#000" fill-opacity="0.5" text-anchor="middle">KHALIL MEFTEHI</text>'
               f'<text x="440" y="78" {PIXEL} font-size="34" fill="{TEXT}" text-anchor="middle">KHALIL MEFTEHI</text>'
               f'<text x="440" y="106" {PIXEL} font-size="13" fill="{GOLD}" text-anchor="middle">&gt; junior software engineer'
               '<tspan>_<animate attributeName="opacity" values="1;1;0;0" dur="1s" repeatCount="indefinite"/></tspan></text>'
               f'<text x="440" y="138" {MONO} font-size="16" fill="#dfe7f5" text-anchor="middle">Java · Spring Boot · Angular · Machine Learning</text>')


def stats_svg(s):
    rows = [
        ("Contributions", s["contributions"]),
        ("Commits", s["commits"]),
        ("Public repos", s["repos"]),
        ("Playing since", s["since"]),
    ]
    body = "".join(
        f'<text x="22" y="{88 + i * 30}" {MONO} font-size="15" fill="{MUTED}">{label}</text>'
        f'<text x="338" y="{88 + i * 30}" {PIXEL} font-size="14" fill="{TEXT}" text-anchor="end">{value}</text>'
        for i, (label, value) in enumerate(rows)
    )
    return panel(360, 80 + len(rows) * 30, "PLAYER STATS", body)


def languages_svg(s):
    total = sum(size for _, (size, _) in s["langs"]) or 1
    # 30 segments split by share, like an XP bar
    bar, seg = "", 0
    for name, (size, color) in s["langs"]:
        for _ in range(max(1, round(30 * size / total))):
            if seg < 30:
                bar += f'<rect x="{22 + seg * 10.6:.0f}" y="68" width="8" height="12" fill="{color}"/>'
                seg += 1
    legend = ""
    for i, (name, (size, color)) in enumerate(s["langs"]):
        cx, cy = 22 + (i % 2) * 165, 112 + (i // 2) * 24
        legend += (
            f'<rect x="{cx}" y="{cy - 10}" width="10" height="10" fill="{color}"/>'
            f'<text x="{cx + 18}" y="{cy}" {MONO} font-size="14" fill="{TEXT}">{escape(name)} '
            f'<tspan fill="{MUTED}">{100 * size / total:.0f}%</tspan></text>'
        )
    rows = (len(s["langs"]) + 1) // 2
    return panel(360, 100 + rows * 24, "TOP LANGUAGES", bar + legend)


def skills_svg():
    width, body, y = 0, "", 72
    for group, items in SKILLS:
        body += f'<text x="22" y="{y + 20}" {MONO} font-size="14" fill="{MUTED}">{escape(group)}</text>'
        x = 130
        for name, color in items:
            w = 36 + 7.8 * len(name)
            # inventory slot: light rim, dark inside, colored block icon
            body += (
                f'<rect x="{x}" y="{y}" width="{w:.0f}" height="30" fill="#8b8b8b"/>'
                f'<rect x="{x + 2}" y="{y + 2}" width="{w - 4:.0f}" height="26" fill="#373737"/>'
                f'<rect x="{x + 9}" y="{y + 10}" width="10" height="10" fill="{color}"/>'
                f'<text x="{x + 26}" y="{y + 20}" {MONO} font-size="14" fill="{TEXT}">{escape(name)}</text>'
            )
            x += w + 6
        width = max(width, int(x) + 16)
        y += 40
    return panel(width, y + 12, "INVENTORY", body)


def main():
    os.makedirs(OUT, exist_ok=True)
    s = fetch()
    files = {"header.svg": header_svg(), "stats.svg": stats_svg(s),
             "languages.svg": languages_svg(s), "skills.svg": skills_svg()}
    for name, content in files.items():
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            f.write(content)
    print(json.dumps({k: v for k, v in s.items() if k != "langs"}))


if __name__ == "__main__":
    main()
