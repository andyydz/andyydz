#!/usr/bin/env python3
import os
import math
import html
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from xml.sax.saxutils import escape

OWNER = "andyydz"
REPOSITORIES = [
    "sentinel-soc-lab",
    "python-soc-automation",
    "Cybersecurity-Writeups",
    "bank-secure-network",
    "andyy-s-site",
    "Cisco-Network-Defence",
]

POSITIONS = {
    "sentinel-soc-lab": (300, 322),
    "python-soc-automation": (250, 432),
    "Cybersecurity-Writeups": (444, 282),
    "bank-secure-network": (452, 446),
    "andyy-s-site": (674, 324),
    "Cisco-Network-Defence": (704, 438),
}


def github_get(path):
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-Github-Api-Version": "2022-11-28",
        "User-Agent": "andyydz-project-map",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(f"https://api.github.com{path}", headers=headers)
    try:
        with urlopen(request, timeout=20) as response:
            import json
            return json.load(response), dict(response.headers)
    except HTTPError as error:
        if error.code == 403 or error.code == 404:
            return None, {}
        raise
    except URLError:
        return None, {}


def repository_data(name):
    repo, _ = github_get(f"/repos/{OWNER}/{name}")
    if not repo:
        repo = {
            "name": name,
            "stargazers_count": 0,
            "language": "Multiple",
            "html_url": f"https://github.com/{OWNER}/{name}",
            "pushed_at": None,
        }

    since = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    commits, headers = github_get(
        f"/repos/{OWNER}/{name}/commits?since={since}&per_page=100"
    )
    commits = commits if isinstance(commits, list) else []

    latest = None
    if commits:
        latest = commits[0].get("commit", {}).get("committer", {}).get("date")

    return {
        "name": name,
        "stars": int(repo.get("stargazers_count") or 0),
        "language": repo.get("language") or "Multiple",
        "url": repo.get("html_url") or f"https://github.com/{OWNER}/{name}",
        "recent_commits": len(commits),
        "latest_commit": latest,
    }


def short_date(value):
    if not value:
        return "No recent commit"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc).strftime("%d %b %Y")
    except ValueError:
        return "No recent commit"


def wrap_label(text, max_chars=20):
    explicit = {
        "Cybersecurity-Writeups": ["Cybersecurity", "Writeups"],
        "Cisco-Network-Defence": ["Cisco-Network", "Defence"],
        "python-soc-automation": ["python-soc", "automation"],
    }
    if text in explicit:
        return explicit[text]
    if len(text) <= max_chars:
        return [text]
    words = text.split("-")
    if len(words) > 1:
        return ["-".join(words[:2]), "-".join(words[2:])] if len("-".join(words[:2])) < max_chars else [text[:max_chars], text[max_chars:]]
    return [text[:max_chars], text[max_chars:]]


def generate_svg(theme, repos):
    dark = theme == "dark"
    background = "#0F2027" if dark else "#DCE2C8"
    surface = "#28623A" if dark else "#B6D298"
    panel = "#0F2027" if dark else "#FFFFFF"
    ink = "#ECFDF5" if dark else "#0F3F3F"
    muted = "#A8C6B5" if dark else "#28623A"
    line = "#28623A" if dark else "#8CAB67"
    accent = "#A7F3D0" if dark else "#0F3F3F"

    node_colors = [
        "#6EE7B7",
        "#A7F3D0",
        "#22C55E",
        "#34D399",
        "#4ADE80",
        "#B6D298",
    ]
    if not dark:
        node_colors = [
            "#28623A",
            "#0F3F3F",
            "#4D7C68",
            "#668D3C",
            "#3F6F6F",
            "#7A9B59",
        ]

    lines = [
        ("andyydz", "sentinel-soc-lab"),
        ("andyydz", "python-soc-automation"),
        ("andyydz", "Cybersecurity-Writeups"),
        ("andyydz", "bank-secure-network"),
        ("andyydz", "andyy-s-site"),
        ("andyydz", "Cisco-Network-Defence"),
        ("sentinel-soc-lab", "python-soc-automation"),
        ("sentinel-soc-lab", "Cybersecurity-Writeups"),
        ("sentinel-soc-lab", "bank-secure-network"),
        ("python-soc-automation", "Cybersecurity-Writeups"),
        ("Cybersecurity-Writeups", "andyy-s-site"),
        ("andyy-s-site", "Cisco-Network-Defence"),
        ("bank-secure-network", "andyy-s-site"),
        ("bank-secure-network", "Cisco-Network-Defence"),
    ]

    repo_by_name = {repo["name"]: repo for repo in repos}
    center = (590, 304)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1180" height="610" viewBox="0 0 1180 610" fill="none">',
        "<defs>",
        f'<linearGradient id="bg" x1="0" y1="0" x2="1180" y2="610" gradientUnits="userSpaceOnUse">',
        f'<stop stop-color="{background}"/>',
        f'<stop offset="1" stop-color="{surface}" stop-opacity="{0.76 if dark else 0.62}"/>',
        "</linearGradient>",
        '<filter id="nodeSoft" x="-30%" y="-30%" width="160%" height="160%">',
        '<feGaussianBlur stdDeviation="2" result="blur"/>',
        '<feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>',
        "</filter>",
        '<clipPath id="clip"><rect width="1180" height="610" rx="24"/></clipPath>',
        "</defs>",
        f'<g clip-path="url(#clip)">',
        f'<rect width="1180" height="610" rx="24" fill="url(#bg)"/>',
        f'<rect x="24" y="24" width="1132" height="562" rx="20" fill="{panel}" fill-opacity="{0.72 if dark else 0.78}" stroke="{surface}" stroke-opacity="{0.60 if dark else 0.82}" stroke-width="1"/>',
    ]

    parts.append(
        f'<text x="48" y="66" font-family="Menlo, Consolas, monospace" font-size="10" font-weight="700" letter-spacing="2" fill="{accent}">PROJECT MAP</text>'
    )
    parts.append(
        f'<text x="48" y="96" font-family="Menlo, Consolas, monospace" font-size="24" font-weight="700" fill="{ink}">Everything I build, and how it connects</text>'
    )
    parts.append(
        f'<text x="48" y="118" font-family="Menlo, Consolas, monospace" font-size="11" fill="{muted}">Size reflects activity · Lines connect shared domains &amp; languages</text>'
    )

    def node_pos(name):
        if name == "andyydz":
            return center
        return POSITIONS[name]

    for source, target in lines:
        sx, sy = node_pos(source)
        tx, ty = node_pos(target)
        parts.append(
            f'<line x1="{sx}" y1="{sy}" x2="{tx}" y2="{ty}" stroke="{line}" stroke-width="1.2" stroke-opacity="0.48">'
            f'<animate attributeName="stroke-opacity" values="0.30;0.68;0.30" dur="4.8s" begin="{(lines.index((source, target)) % 5) * 0.35}s" repeatCount="indefinite"/>'
            "</line>"
        )
        parts.append(
            f'<circle r="2.5" fill="{accent}" opacity="0.86">'
            f'<animateMotion dur="{5.2 + (lines.index((source, target)) % 3) * 0.7}s" repeatCount="indefinite" begin="{lines.index((source, target)) * 0.32}s">'
            f'<mpath href="#pulse-{lines.index((source, target))}"/></animateMotion>'
            "</circle>"
        )
        parts.append(
            f'<path id="pulse-{lines.index((source, target))}" d="M {sx} {sy} L {tx} {ty}" fill="none" stroke="none"/>'
        )

    hub_x, hub_y = center
    parts.append(
        f'<circle cx="{hub_x}" cy="{hub_y}" r="42" fill="{surface}" fill-opacity="{0.24 if dark else 0.40}" stroke="{accent}" stroke-width="2">'
        f'<animate attributeName="r" values="42;46;42" dur="3.6s" repeatCount="indefinite"/>'
        f'<animate attributeName="stroke-opacity" values="0.55;1;0.55" dur="3.6s" repeatCount="indefinite"/>'
        "</circle>"
    )
    parts.append(
        f'<circle cx="{hub_x}" cy="{hub_y}" r="34" fill="{accent}" fill-opacity="{0.18 if dark else 0.28}" stroke="{accent}" stroke-width="1.5"/>'
    )
    parts.append(
        f'<text x="{hub_x}" y="{hub_y - 1}" text-anchor="middle" font-family="Menlo, Consolas, monospace" font-size="15" font-weight="700" fill="{ink}">andyydz</text>'
        f'<text x="{hub_x}" y="{hub_y + 17}" text-anchor="middle" font-family="Menlo, Consolas, monospace" font-size="9" fill="{muted}">CENTRAL HUB</text>'
    )

    for index, repo in enumerate(repos):
        name = repo["name"]
        x, y = POSITIONS[name]
        color = node_colors[index]
        radius = min(48, 34 + min(repo["recent_commits"], 30) * 0.35 + repo["stars"] * 1.2)
        parts.append(
            f'<a href="{escape(repo["url"], {"\"": "&quot;"})}" target="_blank">'
            f'<circle cx="{x}" cy="{y}" r="{radius}" fill="{surface}" fill-opacity="{0.18 if dark else 0.34}" stroke="{color}" stroke-width="2">'
            f'<animate attributeName="stroke-opacity" values="0.62;1;0.62" dur="{4 + index * 0.25}s" begin="{index * 0.28}s" repeatCount="indefinite"/>'
            "</circle>"
        )
        parts.append(
            f'<circle cx="{x}" cy="{y}" r="{radius - 8}" fill="{color}" fill-opacity="{0.16 if dark else 0.24}"/>'
        )
        label_parts = wrap_label(name)
        first_y = y - 3 - (4 if len(label_parts) > 1 else 0)
        for part_index, label in enumerate(label_parts[:2]):
            parts.append(
                f'<text x="{x}" y="{first_y + part_index * 12}" text-anchor="middle" font-family="Menlo, Consolas, monospace" font-size="9.5" font-weight="700" fill="{ink}">{escape(label)}</text>'
            )
        parts.append(
            f'<text x="{x}" y="{y + radius + 15}" text-anchor="middle" font-family="Menlo, Consolas, monospace" font-size="9" fill="{muted}">★ {repo["stars"]} · {escape(repo["language"] or "Multiple")}</text>'
            "</a>"
        )

    legend_x = 48
    legend_y = 530
    legend = [
        ("Python", node_colors[1]),
        ("SIEM / SOC", node_colors[0]),
        ("Networking", node_colors[5]),
        ("Web", node_colors[4]),
        ("Writeups", node_colors[2]),
    ]
    parts.append(
        f'<rect x="{legend_x}" y="{legend_y - 13}" width="420" height="36" rx="9" fill="{panel}" fill-opacity="{0.42 if dark else 0.60}" stroke="{surface}" stroke-opacity="0.42"/>'
    )
    lx = legend_x + 12
    for label, color in legend:
        parts.append(
            f'<circle cx="{lx}" cy="{legend_y + 5}" r="4" fill="{color}"/>'
            f'<text x="{lx + 10}" y="{legend_y + 9}" font-family="Menlo, Consolas, monospace" font-size="8.5" fill="{ink}">{label}</text>'
        )
        lx += 80

    total_commits = sum(repo["recent_commits"] for repo in repos)
    latest_dates = [repo["latest_commit"] for repo in repos if repo["latest_commit"]]
    latest_date = max(latest_dates) if latest_dates else None
    parts.append(
        f'<text x="1132" y="558" text-anchor="end" font-family="Menlo, Consolas, monospace" font-size="9" fill="{muted}">{total_commits} recent commits · latest {escape(short_date(latest_date))}</text>'
    )
    parts.append("</g></svg>")
    return "\n".join(parts)


def main():
    repos = [repository_data(name) for name in REPOSITORIES]
    for theme in ("dark", "light"):
        svg = generate_svg(theme, repos)
        Path = __import__("pathlib").Path
        Path(f"project-map-{theme}.svg").write_text(svg)


if __name__ == "__main__":
    main()
