#!/usr/bin/env python3
import json
import math
import random
import os
import hashlib
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
        return active[:12]

    for repo in candidates:
        repo.setdefault("recent_commits", 0)
        repo.setdefault("latest_commit", None)
    return candidates[:12]


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


def palette_for(category, index, repo_name=""):
    language_map = {
        "Python": "#0F2C3D",
        "Security / SOC": "#547A6E",
        "Networking": "#2D4F56",
        "Web": "#C4936A",
        "Java / SQL": "#6E4E3D",
        "Writeups": "#A6B7A1",
    }
    if category in language_map:
        return language_map[category]
    seed = f"{category}|{repo_name}|{index}".encode("utf-8")
    return PALETTE[int(hashlib.sha256(seed).hexdigest(), 16) % len(PALETTE)]


def text_for(fill):
    return "#0F2027" if fill in {"#A6B7A1", "#D4C8B5", "#C4936A"} else "#F8FAFC"


def wrap_label(name):
    if len(name) <= 18:
        return [name]
    split = name.find("-", len(name) // 2)
    if split > 0:
        return [name[:split], name[split + 1:]]
    return [name[:18], name[18:]]


def force_layout(repos):
    """Seeded spring layout: hub attraction, domain edges, and strong pairwise repulsion."""
    count = len(repos)
    if count == 0:
        return []

    center_x, center_y = 590, 314
    rng = random.Random(20261121 + count)
    positions = []

    # Seed asymmetrically: broad radial arcs with per-node angle and radius variance.
    for index, repo in enumerate(repos):
        angle = rng.uniform(-math.pi * 0.95, math.pi * 0.95)
        radius = rng.uniform(220, 390)
        x = center_x + math.cos(angle) * radius
        y = center_y + math.sin(angle) * radius * rng.uniform(0.52, 0.72)
        positions.append([x, y])

    edges = []
    for i, repo in enumerate(repos):
        edges.append((i, -1))
        for j in range(i + 1, count):
            if category_for(repo) == category_for(repos[j]):
                edges.append((i, j))

    # Spring/repulsion relaxation in deterministic 900-step passes.
    for _ in range(900):
        forces = [[0.0, 0.0] for _ in range(count)]

        for i, (x, y) in enumerate(positions):
            dx = center_x - x
            dy = center_y - y
            distance = max(math.sqrt(dx * dx + dy * dy), 1)
            desired = rng.uniform(235, 305)
            spring = (distance - desired) * 0.00024
            forces[i][0] += dx / distance * spring
            forces[i][1] += dy / distance * spring

        for i in range(count):
            for j in range(i + 1, count):
                dx = positions[j][0] - positions[i][0]
                dy = positions[j][1] - positions[i][1]
                distance = max(math.sqrt(dx * dx + dy * dy), 25)
                repulsion = 3900 / (distance * distance)
                ux, uy = dx / distance, dy / distance
                forces[i][0] -= ux * repulsion
                forces[i][1] -= uy * repulsion
                forces[j][0] += ux * repulsion
                forces[j][1] += uy * repulsion

        for i, j in edges:
            if j >= 0:
                dx = positions[j][0] - positions[i][0]
                dy = positions[j][1] - positions[i][1]
                distance = max(math.sqrt(dx * dx + dy * dy), 1)
                desired = 175
                attraction = (distance - desired) * 0.0009
                ux, uy = dx / distance, dy / distance
                forces[i][0] += ux * attraction
                forces[i][1] += uy * attraction
                forces[j][0] -= ux * attraction
                forces[j][1] -= uy * attraction

        for i, (x, y) in enumerate(positions):
            x += forces[i][0]
            y += forces[i][1]
            x = max(175, min(1005, x))
            y = max(150, min(500, y))
            positions[i] = [x, y]

    # Final collision pass uses activity-sized radii and padded label boxes.
    for _ in range(12):
        for i in range(count):
            for j in range(i + 1, count):
                xi, yi = positions[i]
                xj, yj = positions[j]
                dx, dy = xj - xi, yj - yi
                distance = max(math.sqrt(dx * dx + dy * dy), 1)
                ri = min(48, max(38, 38 + min(repos[i]["recent_commits"], 20) * 0.35 + repos[i]["stars"] * 0.8))
                rj = min(48, max(38, 38 + min(repos[j]["recent_commits"], 20) * 0.35 + repos[j]["stars"] * 0.8))
                minimum = ri + rj + 58
                if distance < minimum:
                    ux, uy = dx / distance, dy / distance
                    push = (minimum - distance) / 2
                    positions[i][0] -= ux * push
                    positions[i][1] -= uy * push
                    positions[j][0] += ux * push
                    positions[j][1] += uy * push

        for i, (x, y) in enumerate(positions):
            positions[i] = [
                max(175, min(1005, x)),
                max(150, min(500, y)),
            ]

    return [(round(x, 1), round(y, 1)) for x, y in positions]


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

    positions = force_layout(repos)
    category_counts = {}
    for repo in repos:
        category = category_for(repo)
        category_counts[category] = category_counts.get(category, 0) + 1

    legend_items = []
    for index, repo in enumerate(repos):
        category = category_for(repo)
        color = palette_for(category, index, repo["name"])
        if category not in [item[0] for item in legend_items]:
            legend_items.append((category, color))

    lines = []
    for index, repo in enumerate(repos):
        lines.append(("andyydz", repo["name"], positions[index]))

    # Organic cross-links: link repositories that share a domain/category or language.
    category_added = set()
    for i in range(len(repos)):
        for j in range(i + 1, len(repos)):
            category_i = category_for(repos[i])
            category_j = category_for(repos[j])
            if category_i == category_j and (category_i, j) not in category_added:
                lines.append((repos[i]["name"], repos[j]["name"], None))
                category_added.add((category_i, j))

    # Add a sparse second-link network for nearest-neighbor visual structure.
    for i in range(len(repos)):
        nearest = sorted(
            (j for j in range(len(repos)) if j != i),
            key=lambda j: math.hypot(
                positions[i][0] - positions[j][0],
                positions[i][1] - positions[j][1],
            ),
        )[:1]
        for j in nearest:
            pair = tuple(sorted((repos[i]["name"], repos[j]["name"])))
            if not any(
                tuple(sorted((a, b))) == pair
                for a, b, _ in lines
            ):
                lines.append((repos[i]["name"], repos[j]["name"], None))

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
        f'<g><animateTransform attributeName="transform" type="translate"'
        f' values="0 0; 2 1.5; 0 3; -2 -1; 0 0"'
        f' keyTimes="0;0.25;0.5;0.75;1" calcMode="spline"'
        f' keySplines="0.42 0 0.58 1;0.42 0 0.58 1;0.42 0 0.58 1;0.42 0 0.58 1"'
        f' dur="12s" repeatCount="indefinite"/>'
    )
    parts.append(
        f'<circle cx="{hub_x}" cy="{hub_y}" r="36" fill="{surface}" fill-opacity="0.92" stroke="{accent}" stroke-width="1.2"/>'
    )
    parts.append(
        f'<text x="{hub_x}" y="{hub_y - 1}" text-anchor="middle" font-family="Menlo, Consolas, monospace" font-size="15" font-weight="700" fill="{ink}">andyydz</text>'
        f'<text x="{hub_x}" y="{hub_y + 17}" text-anchor="middle" font-family="Menlo, Consolas, monospace" font-size="9" fill="{muted}">CENTRAL HUB</text>'
        "</g>"
    )

    for index, repo in enumerate(repos):
        name = repo["name"]
        x, y = positions[index]
        category = category_for(repo)
        fill = palette_for(category, index, name)
        label_color = text_for(fill)
        radius = min(48, max(38, 38 + min(repo["recent_commits"], 20) * 0.35 + repo["stars"] * 0.8))
        durations = [7, 9, 11, 13, 15]
        duration = durations[index % len(durations)]
        phase = (index * 1.37) % duration
        dx = 5 + (index % 3)
        dy = 5 + ((index * 2) % 5)

        parts.append(
            f'<g><animateTransform attributeName="transform" type="translate"'
            f' values="0 0; {dx} {dy // 2}; {dy} -{dx // 2}; -{dx // 2} -{dy}; -{dx} {dy // 2}; 0 0"'
            f' keyTimes="0;0.2;0.4;0.6;0.8;1" calcMode="spline"'
            f' keySplines="0.42 0 0.58 1;0.42 0 0.58 1;0.42 0 0.58 1;0.42 0 0.58 1;0.42 0 0.58 1"'
            f' dur="{duration}s" begin="-{phase:.2f}s" repeatCount="indefinite"/>'
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
