#!/usr/bin/env python3
import json
import math
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape

OWNER = "andyydz"
PALETTE = [
    "#0F2C3D",
    "#2D4F56",
    "#547A6E",
    "#A6B7A1",
    "#D4C8B5",
    "#C4936A",
    "#6E4E3D",
]
FALLBACK_REPOSITORIES = [
    "sentinel-soc-lab",
    "python-soc-automation",
    "Cybersecurity-Writeups",
    "bank-secure-network",
    "andyy-s-site",
    "Cisco-Network-Defence",
]


def github_get(path):
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "andyydz-project-map",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(f"https://api.github.com{path}", headers=headers)
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    except (HTTPError, URLError, TimeoutError):
        return None


def parse_timestamp(value):
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)


def short_date(value):
    parsed = parse_timestamp(value)
    if parsed.year == 1:
        return "No recent commit"
    return parsed.astimezone(timezone.utc).strftime("%d %b %Y")


def discover_repositories():
    items = github_get(
        f"/users/{OWNER}/repos?per_page=100&sort=pushed&direction=desc"
    )
    candidates = []

    if isinstance(items, list):
        for item in items:
            name = item.get("name")
            if not name or name.lower() == OWNER.lower():
                continue
            if item.get("archived"):
                continue
            stars = int(item.get("stargazers_count") or 0)
            pushed = item.get("pushed_at")
            forks = bool(item.get("fork"))
            if forks and stars == 0:
                continue
            candidates.append({
                "name": name,
                "stars": stars,
                "language": item.get("language") or "Multiple",
                "url": item.get("html_url") or f"https://github.com/{OWNER}/{name}",
                "pushed_at": pushed,
                "fork": forks,
            })

    found_names = {repo["name"].lower() for repo in candidates}
    if len(candidates) < 5:
        for name in FALLBACK_REPOSITORIES:
            if name.lower() not in found_names:
                candidates.append({
                    "name": name,
                    "stars": 0,
                    "language": "Multiple",
                    "url": f"https://github.com/{OWNER}/{name}",
                    "pushed_at": None,
                    "fork": False,
                })
                found_names.add(name.lower())

    since = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    recent_cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    active = []
    for repo in candidates:
        commits = github_get(
            f"/repos/{OWNER}/{quote(repo['name'], safe='')}/commits"
            f"?since={quote(since, safe='')}&per_page=100"
        )
        commits = commits if isinstance(commits, list) else []
        latest_commit = None
        if commits:
            latest_commit = commits[0].get("commit", {}).get("committer", {}).get("date")
        pushed = parse_timestamp(repo["pushed_at"])
        is_recent = pushed >= recent_cutoff
        if repo["fork"] and repo["stars"] == 0 and not commits:
            continue
        if not is_recent and repo["stars"] == 0 and not commits:
            continue
        repo["recent_commits"] = len(commits)
        repo["latest_commit"] = latest_commit
        repo["activity_score"] = len(commits) * 10 + repo["stars"] * 5
        active.append(repo)

    active.sort(
        key=lambda repo: (
            repo["activity_score"],
            repo["stars"],
            parse_timestamp(repo["pushed_at"]),
            repo["name"].lower(),
        ),
        reverse=True,
    )
    if active:
        return active[:10]

    for repo in candidates:
        repo.setdefault("recent_commits", 0)
        repo.setdefault("latest_commit", None)
    return candidates[:10]


def category_for(repo):
    language = (repo.get("language") or "").lower()
    name = repo["name"].lower()
    if "python" in language or "python" in name:
        return "Python"
    if language in {"javascript", "typescript", "html", "css"} or "site" in name:
        return "Web"
    if language in {"java", "kotlin", "sql", "c#", "c++"}:
        return "Java / SQL"
    if any(word in name for word in ("network", "cisco", "vlan", "acl")):
        return "Networking"
    if any(word in name for word in ("soc", "sentinel", "security", "writeup", "cyber")):
        return "Security / SOC"
    return "Other"


def palette_for(category, index):
    language_map = {
        "Python": "#0F2C3D",
        "Security / SOC": "#547A6E",
        "Networking": "#2D4F56",
        "Web": "#C4936A",
        "Java / SQL": "#6E4E3D",
        "Writeups": "#A6B7A1",
        "Other": PALETTE[index % len(PALETTE)],
    }
    return language_map.get(category, PALETTE[index % len(PALETTE)])


def text_for(fill):
    return "#0F2027" if fill in {"#A6B7A1", "#D4C8B5", "#C4936A"} else "#F8FAFC"


def wrap_label(name):
    explicit = {
        "Cybersecurity-Writeups": ["Cybersecurity", "Writeups"],
        "Cisco-Network-Defence": ["Cisco-Network", "Defence"],
        "python-soc-automation": ["python-soc", "automation"],
        "bank-secure-network": ["bank-secure", "network"],
    }
    if name in explicit:
        return explicit[name]
    if len(name) <= 18:
        return [name]
    split = name.find("-", len(name) // 2)
    if split > 0:
        return [name[:split], name[split + 1:]]
    return [name[:18], name[18:]]


def orbit_positions(count):
    if count <= 5:
        radius_x, radius_y = 290, 158
    elif count <= 7:
        radius_x, radius_y = 330, 178
    else:
        radius_x, radius_y = 365, 188

    center_x, center_y = 590, 314
    positions = []
    for index in range(count):
        angle = -math.pi / 2 + (2 * math.pi * index / count)
        x = center_x + radius_x * math.cos(angle)
        y = center_y + radius_y * math.sin(angle)
        positions.append((round(x, 1), round(y, 1)))

    # Pairwise separation pass: preserve radial intent while guaranteeing node breathing room.
    for _ in range(6):
        for i in range(count):
            for j in range(i + 1, count):
                xi, yi = positions[i]
                xj, yj = positions[j]
                dx, dy = xj - xi, yj - yi
                distance = math.sqrt(dx * dx + dy * dy)
                minimum = 118
                if distance < minimum:
                    if distance == 0:
                        dx, dy, distance = 1, 0, 1
                    push = (minimum - distance) / 2
                    ux, uy = dx / distance, dy / distance
                    positions[i] = (xi - ux * push, yi - uy * push)
                    positions[j] = (xj + ux * push, yj + uy * push)

    # Keep every center and label within the 1180x610 graph frame.
    for i, (x, y) in enumerate(positions):
        x = max(180, min(1000, x))
        y = max(155, min(500, y))
        positions[i] = (round(x, 1), round(y, 1))
    return positions


def generate_svg(theme, repos):
    dark = theme == "dark"
    background = "#0F2027" if dark else "#DCE2C8"
    surface = "#28623A" if dark else "#B6D298"
    panel = "#0F2027" if dark else "#FFFFFF"
    ink = "#F8FAFC" if dark else "#0F3F3F"
    muted = "#A8C6B5" if dark else "#28623A"
    line = "#547A6E" if dark else "#547A6E"
    accent = "#A6B7A1" if dark else "#0F3F3F"
    hub_x, hub_y = 590, 314

    positions = orbit_positions(len(repos))
    category_counts = {}
    for repo in repos:
        category = category_for(repo)
        category_counts[category] = category_counts.get(category, 0) + 1

    legend_items = []
    for index, repo in enumerate(repos):
        category = category_for(repo)
        color = palette_for(category, index)
        if category not in [item[0] for item in legend_items]:
            legend_items.append((category, color))

    lines = []
    for index, repo in enumerate(repos):
        lines.append(("andyydz", repo["name"], positions[index]))
    for index in range(len(repos)):
        lines.append((repos[index]["name"], repos[(index + 1) % len(repos)]["name"], None))

    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1180" height="610" viewBox="0 0 1180 610" fill="none">',
        "<defs>",
        '<linearGradient id="bg" x1="0" y1="0" x2="1180" y2="610" gradientUnits="userSpaceOnUse">',
        f'<stop stop-color="{background}"/>',
        f'<stop offset="1" stop-color="{surface}" stop-opacity="{0.76 if dark else 0.62}"/>',
        "</linearGradient>",
        '<clipPath id="clip"><rect width="1180" height="610" rx="24"/></clipPath>',
        "</defs>",
        '<g clip-path="url(#clip)">',
        f'<rect width="1180" height="610" rx="24" fill="url(#bg)"/>',
        f'<rect x="24" y="24" width="1132" height="562" rx="20" fill="{panel}" fill-opacity="{0.72 if dark else 0.78}" stroke="{surface}" stroke-opacity="{0.68 if dark else 0.82}" stroke-width="1"/>',
        f'<text x="48" y="66" font-family="Menlo, Consolas, monospace" font-size="10" font-weight="700" letter-spacing="2" fill="{accent}">PROJECT MAP</text>',
        f'<text x="48" y="96" font-family="Menlo, Consolas, monospace" font-size="24" font-weight="700" fill="{ink}">Everything I build, and how it connects</text>',
        f'<text x="48" y="118" font-family="Menlo, Consolas, monospace" font-size="11" fill="{muted}">Size reflects activity · Lines connect shared domains &amp; languages</text>',
    ]

    repo_positions = {repo["name"]: positions[index] for index, repo in enumerate(repos)}

    for index, (source, target, _) in enumerate(lines):
        sx, sy = (hub_x, hub_y) if source == "andyydz" else repo_positions[source]
        tx, ty = (hub_x, hub_y) if target == "andyydz" else repo_positions[target]
        parts.append(
            f'<line x1="{sx}" y1="{sy}" x2="{tx}" y2="{ty}" stroke="{line}" stroke-width="1.2" stroke-opacity="0.58">'
            f'<animate attributeName="stroke-opacity" values="0.38;0.78;0.38" dur="4.8s" begin="{(index % 7) * 0.28}s" repeatCount="indefinite"/>'
            "</line>"
        )
        parts.append(
            f'<circle r="2.5" fill="{accent}" opacity="0.92">'
            f'<animateMotion dur="{5.2 + (index % 3) * 0.7}s" repeatCount="indefinite" begin="{index * 0.28}s">'
            f'<mpath href="#pulse-{index}"/></animateMotion>'
            "</circle>"
        )
        parts.append(f'<path id="pulse-{index}" d="M {sx} {sy} L {tx} {ty}" fill="none" stroke="none"/>')

    parts.append(
        f'<circle cx="{hub_x}" cy="{hub_y}" r="46" fill="{surface}" fill-opacity="{0.28 if dark else 0.40}" stroke="{accent}" stroke-width="2" stroke-opacity="0.68">'
        f'<animate attributeName="r" values="46;50;46" dur="3.6s" repeatCount="indefinite"/>'
        f'<animate attributeName="stroke-opacity" values="0.68;1;0.68" dur="3.6s" repeatCount="indefinite"/>'
        "</circle>"
    )
    parts.append(
        f'<circle cx="{hub_x}" cy="{hub_y}" r="36" fill="{surface}" fill-opacity="0.92" stroke="{accent}" stroke-width="1.2"/>'
    )
    parts.append(
        f'<text x="{hub_x}" y="{hub_y - 1}" text-anchor="middle" font-family="Menlo, Consolas, monospace" font-size="15" font-weight="700" fill="{ink}">andyydz</text>'
        f'<text x="{hub_x}" y="{hub_y + 17}" text-anchor="middle" font-family="Menlo, Consolas, monospace" font-size="9" fill="{muted}">CENTRAL HUB</text>'
    )

    for index, repo in enumerate(repos):
        name = repo["name"]
        x, y = positions[index]
        category = category_for(repo)
        fill = palette_for(category, index)
        label_color = text_for(fill)
        radius = min(48, max(38, 38 + min(repo["recent_commits"], 20) * 0.35 + repo["stars"] * 0.8))
        duration = 6 + (index % 5)

        parts.append(
            f'<g><animateTransform attributeName="transform" type="translate"'
            f' values="0 0; 3 2; 0 -3; -2 1; 0 0" dur="{duration}s" begin="-{index * 0.65}s" repeatCount="indefinite"/>'
        )
        parts.append(
            f'<a href="{escape(repo["url"], {chr(34): "&quot;"})}" target="_blank">'
            f'<circle cx="{x}" cy="{y}" r="{radius + 9}" fill="{fill}" fill-opacity="0.28" stroke="{fill}" stroke-width="2" stroke-opacity="0.68">'
            f'<animate attributeName="stroke-opacity" values="0.68;0.92;0.68" dur="{5 + index * 0.25}s" begin="{index * 0.28}s" repeatCount="indefinite"/>'
            "</circle>"
        )
        parts.append(
            f'<circle cx="{x}" cy="{y}" r="{radius}" fill="{fill}" fill-opacity="0.92"/>'
        )
        label_parts = wrap_label(name)
        first_y = y - (6 if len(label_parts) > 1 else 1)
        for part_index, label in enumerate(label_parts[:2]):
            parts.append(
                f'<text x="{x}" y="{first_y + part_index * 12}" text-anchor="middle" font-family="Menlo, Consolas, monospace" font-size="9.5" font-weight="700" fill="{label_color}">{escape(label)}</text>'
            )
        parts.append(
            f'<text x="{x}" y="{y + radius + 15}" text-anchor="middle" font-family="Menlo, Consolas, monospace" font-size="9" fill="{muted}">★ {repo["stars"]} · {escape(repo["language"])}</text>'
            "</a></g>"
        )

    legend_x = 48
    legend_y = 530
    legend_width = min(520, 70 + len(legend_items) * 82)
    parts.append(
        f'<rect x="{legend_x}" y="{legend_y - 13}" width="{legend_width}" height="36" rx="9" fill="{panel}" fill-opacity="{0.42 if dark else 0.72}" stroke="{surface}" stroke-opacity="0.58"/>'
    )
    lx = legend_x + 12
    for category, color in legend_items:
        parts.append(
            f'<circle cx="{lx}" cy="{legend_y + 5}" r="4" fill="{color}" fill-opacity="0.92"/>'
            f'<text x="{lx + 10}" y="{legend_y + 9}" font-family="Menlo, Consolas, monospace" font-size="8.5" fill="{ink}">{escape(category)}</text>'
        )
        lx += 82

    total_commits = sum(repo["recent_commits"] for repo in repos)
    latest_values = [repo["latest_commit"] for repo in repos if repo["latest_commit"]]
    latest_commit = max(latest_values, key=parse_timestamp) if latest_values else None
    parts.append(
        f'<text x="1132" y="558" text-anchor="end" font-family="Menlo, Consolas, monospace" font-size="9" fill="{muted}">{total_commits} recent commits · latest {escape(short_date(latest_commit))}</text>'
    )
    parts.append("</g></svg>")
    return "\n".join(parts)


def main():
    repos = discover_repositories()
    if not repos:
        repos = []
    for theme in ("dark", "light"):
        svg = generate_svg(theme, repos)
        Path(f"project-map-{theme}.svg").write_text(svg)


if __name__ == "__main__":
    main()
