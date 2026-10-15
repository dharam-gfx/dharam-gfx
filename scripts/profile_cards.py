#!/usr/bin/env python3
"""Generate dark and light GitHub profile cards from public GitHub data."""

from __future__ import annotations

import argparse
import html
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

API = "https://api.github.com"
USER_AGENT = "dharam-gfx-profile-cards"

THEMES = {
    "dark": {
        "bg": "#0d1117",
        "border": "#30363d",
        "text": "#c9d1d9",
        "muted": "#8b949e",
        "value": "#f0f6fc",
        "accent": "#22d3ee",
        "bar_bg": "#21262d",
    },
    "light": {
        "bg": "#ffffff",
        "border": "#d0d7de",
        "text": "#1f2328",
        "muted": "#59636e",
        "value": "#0d1117",
        "accent": "#087e8b",
        "bar_bg": "#eaeef2",
    },
}

LANGUAGE_COLORS = {
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "Python": "#3572a5",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "Vue": "#41b883",
    "Java": "#b07219",
    "C#": "#178600",
    "C++": "#f34b7d",
    "PHP": "#4f5d95",
    "Ruby": "#701516",
    "Go": "#00add8",
    "Rust": "#dea584",
    "Shell": "#89e051",
}

STACK_GROUPS = [
    ("Frontend / UI", 10),
    ("Backend", 2),
    ("Database", 1),
    ("Design", 3),
    ("Platforms", 2),
    ("Dev tools", 2),
]


def api(path: str) -> Any:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"{API}{path}", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"GitHub API returned HTTP {error.code} for {path}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Could not reach the GitHub API: {error.reason}") from error


def fetch_profile(user: str) -> tuple[dict, list[dict]]:
    profile = api(f"/users/{user}")
    repos = api(f"/users/{user}/repos?per_page=100&type=owner&sort=updated")
    return profile, [repo for repo in repos if not repo.get("fork") and not repo.get("archived")]


def fetch_languages(repos: list[dict]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for repo in repos:
        try:
            languages = api(f"/repos/{repo['full_name']}/languages")
        except RuntimeError as error:
            print(f"Skipping languages for {repo['full_name']}: {error}")
            continue
        for name, byte_count in languages.items():
            totals[name] = totals.get(name, 0) + byte_count
    return totals


def frame(width: int, height: int, theme: dict, body: str, label: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img" aria-label="{html.escape(label)}" '
        'font-family="ui-sans-serif,Segoe UI,Arial,sans-serif">'
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="8" '
        f'fill="{theme["bg"]}" stroke="{theme["border"]}"/>{body}</svg>'
    )


def stats_card(user: str, profile: dict, repos: list[dict], theme: dict) -> str:
    total_stars = sum(repo.get("stargazers_count", 0) for repo in repos)
    stats = [
        (f"{total_stars:,}", "STARS"),
        (f"{profile.get('public_repos', 0):,}", "PUBLIC REPOS"),
        (f"{profile.get('followers', 0):,}", "FOLLOWERS"),
    ]
    width, height = 520, 168
    body = [
        f'<text x="24" y="31" font-size="13" font-weight="700" letter-spacing="1" '
        f'fill="{theme["accent"]}">{html.escape(user.upper())} / GITHUB</text>',
        f'<text x="496" y="31" text-anchor="end" font-size="11" '
        f'fill="{theme["muted"]}">PUBLIC PROFILE</text>',
        f'<line x1="24" y1="47" x2="496" y2="47" stroke="{theme["border"]}"/>',
    ]
    for index, (value, label) in enumerate(stats):
        x = 28 + index * 160
        body.extend([
            f'<text x="{x}" y="96" font-size="30" font-weight="700" '
            f'fill="{theme["value"]}">{value}</text>',
            f'<text x="{x}" y="119" font-size="10" letter-spacing="1" '
            f'fill="{theme["muted"]}">{label}</text>',
            f'<rect x="{x}" y="137" width="34" height="3" rx="1.5" fill="{theme["accent"]}"/>',
        ])
    return frame(width, height, theme, "".join(body), f"{user} GitHub statistics")


def languages_card(languages: dict[str, int], theme: dict) -> str:
    ranked = sorted(languages.items(), key=lambda item: item[1], reverse=True)[:6]
    width, row_height = 520, 30
    height = 66 + max(1, len(ranked)) * row_height + 18
    body = [
        f'<text x="24" y="31" font-size="13" font-weight="700" letter-spacing="1" '
        f'fill="{theme["accent"]}">LANGUAGE MIX</text>',
        f'<text x="496" y="31" text-anchor="end" font-size="11" '
        f'fill="{theme["muted"]}">BYTES ACROSS PUBLIC REPOS</text>',
    ]
    if not ranked:
        body.append(
            f'<text x="24" y="87" font-size="13" fill="{theme["muted"]}">'
            "No public language data yet</text>"
        )
    else:
        total = sum(languages.values())
        for index, (name, size) in enumerate(ranked):
            y = 61 + index * row_height
            percent = size / total * 100
            color = LANGUAGE_COLORS.get(name, theme["accent"])
            body.extend([
                f'<text x="24" y="{y + 12}" font-size="11" fill="{theme["text"]}">'
                f'{html.escape(name)}</text>',
                f'<text x="496" y="{y + 12}" text-anchor="end" font-size="10" '
                f'fill="{theme["muted"]}">{percent:.1f}%</text>',
                f'<rect x="24" y="{y + 18}" width="472" height="5" rx="2.5" '
                f'fill="{theme["bar_bg"]}"/>',
                f'<rect x="24" y="{y + 18}" width="{472 * percent / 100:.1f}" '
                f'height="5" rx="2.5" fill="{color}"/>',
            ])
    return frame(width, height, theme, "".join(body), "Programming language usage")


def radar_card(title: str, subtitle: str, axes: list[tuple[str, float, str]], theme: dict) -> str:
    width, height = 520, 400
    center_x, center_y, radius = 260.0, 211.0, 104.0
    label_radius = 137.0
    body = [
        f'<text x="{center_x}" y="25" text-anchor="middle" font-size="14" '
        f'font-weight="700" fill="{theme["value"]}">{html.escape(title)}</text>',
        f'<text x="{center_x}" y="43" text-anchor="middle" font-size="9" '
        f'letter-spacing="1" fill="{theme["muted"]}">{html.escape(subtitle.upper())}</text>',
    ]
    if not axes:
        body.append(
            f'<text x="{center_x}" y="{center_y}" text-anchor="middle" '
            f'font-size="12" fill="{theme["muted"]}">No public language data yet</text>'
        )
        return frame(width, height, theme, "".join(body), title)

    def position(index: int, distance: float) -> tuple[float, float]:
        angle = -math.pi / 2 + index * 2 * math.pi / len(axes)
        return center_x + math.cos(angle) * distance, center_y + math.sin(angle) * distance

    for level in (0.25, 0.5, 0.75, 1.0):
        points = " ".join(
            f"{x:.1f},{y:.1f}" for x, y in (position(i, radius * level) for i in range(len(axes)))
        )
        body.append(
            f'<polygon points="{points}" fill="none" stroke="{theme["border"]}" '
            'stroke-width="1"/>'
        )

    outer = [position(i, radius) for i in range(len(axes))]
    for x, y in outer:
        body.append(
            f'<line x1="{center_x:.1f}" y1="{center_y:.1f}" x2="{x:.1f}" y2="{y:.1f}" '
            f'stroke="{theme["border"]}" stroke-width="1"/>'
        )

    values = [max(0.0, min(100.0, value)) for _, value, _ in axes]
    shape = " ".join(
        f"{x:.1f},{y:.1f}"
        for i, value in enumerate(values)
        for x, y in [position(i, radius * value / 100)]
    )
    body.append(
        f'<polygon points="{shape}" fill="{theme["accent"]}" fill-opacity=".18" '
        f'stroke="{theme["accent"]}" stroke-width="2.5" stroke-linejoin="round"/>'
    )

    for index, (label, _, value_label) in enumerate(axes):
        angle = -math.pi / 2 + index * 2 * math.pi / len(axes)
        x, y = position(index, label_radius)
        horizontal = math.cos(angle)
        if abs(horizontal) < 0.2:
            anchor = "middle"
        elif horizontal > 0:
            anchor = "start"
        else:
            anchor = "end"
        point_x, point_y = position(index, radius * values[index] / 100)
        body.extend([
            f'<circle cx="{point_x:.1f}" cy="{point_y:.1f}" r="3" fill="{theme["accent"]}"/>',
            f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-size="10" '
            f'font-weight="600" fill="{theme["text"]}">{html.escape(label)}</text>',
            f'<text x="{x:.1f}" y="{y + 13:.1f}" text-anchor="{anchor}" font-size="9" '
            f'fill="{theme["muted"]}">{html.escape(value_label)}</text>',
        ])
    return frame(width, height, theme, "".join(body), title)


def stack_radar(theme: dict) -> str:
    maximum = max(count for _, count in STACK_GROUPS)
    axes = [
        (label, 100 * math.sqrt(count / maximum), f"{count} tools")
        for label, count in STACK_GROUPS
    ]
    return radar_card("Stack Area Mix", "Tools listed", axes, theme)


def language_radar(languages: dict[str, int], theme: dict) -> str:
    ranked = sorted(languages.items(), key=lambda item: item[1], reverse=True)[:6]
    total = sum(languages.values())
    maximum = ranked[0][1] if ranked else 0
    axes = [
        (name, 100 * math.sqrt(size / maximum), f"{size / total * 100:.1f}%")
        for name, size in ranked
        if maximum and total
    ]
    return radar_card("GitHub Languages", "Share of public repo bytes", axes, theme)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user", default="dharam-gfx")
    parser.add_argument("--out", type=Path, default=Path("assets"))
    args = parser.parse_args()

    profile, repos = fetch_profile(args.user)
    languages = fetch_languages(repos)
    args.out.mkdir(parents=True, exist_ok=True)
    for name, theme in THEMES.items():
        (args.out / f"card-stats-{name}.svg").write_text(
            stats_card(args.user, profile, repos, theme), encoding="utf-8"
        )
        (args.out / f"card-languages-{name}.svg").write_text(
            languages_card(languages, theme), encoding="utf-8"
        )
        (args.out / f"radar-stack-{name}.svg").write_text(
            stack_radar(theme), encoding="utf-8"
        )
        (args.out / f"radar-languages-{name}.svg").write_text(
            language_radar(languages, theme), encoding="utf-8"
        )
    print(f"Generated profile cards for {args.user} using {len(repos)} public repositories.")


if __name__ == "__main__":
    main()