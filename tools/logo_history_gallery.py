from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import flet as ft

from ui.components.header import GUI_LOGO_BOX_HEIGHT, LOGO_CHAR_WIDTH_FACTOR, LOGO_FONT_FAMILY
from ui.themes.catalog import THEMES

SEARCH_TERMS = ("eva", "nerv", "magi", "wh40k", "warhammer", "cogitator")
SEARCH_TERM_PATTERN = re.compile(r"(^|[^a-z0-9])(eva|nerv|magi|wh40k|warhammer|cogitator)([^a-z0-9]|$)", re.IGNORECASE)
EVA_TERM_PATTERN = re.compile(r"(^|[^a-z0-9])(eva|nerv|magi)([^a-z0-9]|$)", re.IGNORECASE)
WH40K_TERM_PATTERN = re.compile(r"(^|[^a-z0-9])(wh40k|warhammer|cogitator|omnissiah)([^a-z0-9]|$)", re.IGNORECASE)
TEXT_EXTENSIONS = {".txt", ".asc", ".ansi", ".py", ".json", ".md"}
SEARCH_ROOTS = ("static", "assets", "archive", "backups", "future_implementations", "legacy", "themes", "ui")
WORKTREE_SKIP_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "build",
    "dist",
    "reports",
    "node_modules",
}
REPORT_DIR = ROOT / "reports"
CANDIDATE_DIR = REPORT_DIR / "logo_history_candidates"
AUDIT_JSON = REPORT_DIR / "logo_history_audit_v7.13.30.json"
AUDIT_MD = REPORT_DIR / "logo_history_audit_v7.13.30.md"
EXPECTED_CURRENT_HASHES = {
    "EVA": "5c10f1a59339b6a788880c4187481c0d3290abddc1dff9da80389fa8684df476",
    "WH40K": "dfe05107f652c009ef1c7a5efc6005adc82ceae42ff321870acdb67c21ec150c",
}


@dataclass(frozen=True)
class Candidate:
    theme: str
    source_path: str
    commit: str
    commit_date: str
    commit_subject: str
    sha256: str
    line_count: int
    non_empty_line_count: int
    maximum_column_width: int
    character_set_used: str
    aspect_ratio: float
    source_file: str
    source_kind: str


@dataclass(frozen=True)
class RenderMetrics:
    viewport_width: int
    viewport_height: int
    mode: str
    base_font_size: int
    line_height: float
    natural_visible_width: float
    natural_visible_height: float
    fit_scale: float
    transformed_width: float
    transformed_height: float
    clearance_left: float
    clearance_right: float
    clearance_top: float
    clearance_bottom: float
    occupancy: float


def run_git(args: list[str], *, text: bool = True) -> str | bytes:
    result = subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=text)
    return result.stdout


def try_git(args: list[str], *, text: bool = True) -> str | bytes:
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=text)
    if result.returncode != 0:
        return "" if text else b""
    return result.stdout


def path_matches(path: str) -> bool:
    lower = path.lower().replace("\\", "/")
    suffix = Path(lower).suffix
    if suffix not in TEXT_EXTENSIONS:
        return False
    return bool(SEARCH_TERM_PATTERN.search(lower))


def theme_for_path_or_text(path: str, text: str) -> str | None:
    haystack = f"{path}\n{text[:1000]}".lower()
    if WH40K_TERM_PATTERN.search(haystack):
        return "WH40K"
    if EVA_TERM_PATTERN.search(haystack):
        return "EVA"
    return None


def is_logo_like(path: str, text: str) -> bool:
    if not text.strip():
        return False
    normalized_path = path.lower().replace("\\", "/")
    if normalized_path.startswith("tests/"):
        return False
    lines = text.splitlines()
    if len(lines) > 80:
        return False
    if Path(path).suffix.lower() in {".py", ".json", ".md"}:
        art_chars = sum(1 for char in text if char in "#@/\\|_-=+:.`'\",;*[]{}()<>~^$%&!█╗╝╚═║")
        alpha = sum(1 for char in text if char.isalpha())
        if art_chars < 30 and alpha > art_chars:
            return False
    return max((len(line) for line in lines), default=0) <= 220


def text_stats(text: str) -> tuple[int, int, int, str, float]:
    lines = text.splitlines()
    non_empty = [line for line in lines if line.strip()]
    max_width = max((len(line) for line in lines), default=0)
    chars = "".join(sorted({char for char in text if not char.isspace()}))
    aspect = round(max_width / max(1, len(non_empty)), 3)
    return len(lines), len(non_empty), max_width, chars, aspect


def commit_info(commit: str) -> tuple[str, str]:
    raw = try_git(["show", "-s", "--date=iso-strict", "--format=%cI%x00%s", commit])
    if not raw:
        return "", ""
    parts = raw.rstrip("\n").split("\x00", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return "", raw.strip()


def candidate_paths_from_history() -> set[str]:
    paths: set[str] = set()
    name_only = try_git(["log", "--all", "--name-only", "--pretty=format:"])
    for line in str(name_only).splitlines():
        clean = line.strip()
        if clean and path_matches(clean):
            paths.add(clean)
    objects = try_git(["rev-list", "--all", "--objects"])
    for line in str(objects).splitlines():
        parts = line.split(" ", 1)
        if len(parts) == 2 and path_matches(parts[1].strip()):
            paths.add(parts[1].strip())
    for current_root, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [dirname for dirname in dirnames if dirname not in WORKTREE_SKIP_DIRS]
        for filename in filenames:
            worktree_path = Path(current_root) / filename
            try:
                rel = worktree_path.relative_to(ROOT).as_posix()
            except ValueError:
                continue
            if path_matches(rel):
                paths.add(rel)
    return paths


def commits_for_path(path: str) -> list[str]:
    raw = try_git(["log", "--all", "--follow", "--format=%H", "--", path])
    commits = [line.strip() for line in str(raw).splitlines() if line.strip()]
    return commits


def reflog_commits() -> list[str]:
    raw = try_git(["reflog", "--format=%H"])
    return list(dict.fromkeys(line.strip() for line in str(raw).splitlines() if line.strip()))


def extract_blob(commit: str, path: str) -> bytes:
    return try_git(["show", f"{commit}:{path}"], text=False)


def write_candidate_file(candidate_hash: str, theme: str, text: str) -> Path:
    theme_dir = CANDIDATE_DIR / theme.lower()
    theme_dir.mkdir(parents=True, exist_ok=True)
    target = theme_dir / f"{candidate_hash[:12]}.txt"
    target.write_text(text, encoding="utf-8", newline="")
    return target


def collect_candidates() -> list[Candidate]:
    candidates: dict[str, Candidate] = {}
    paths = sorted(candidate_paths_from_history())
    current_commit = "WORKTREE"

    for path in paths:
        commits = commits_for_path(path)
        if Path(ROOT / path).exists():
            commits = [current_commit, *commits]
        for commit in commits:
            if commit == current_commit:
                data = (ROOT / path).read_bytes()
                date, subject = datetime.now().isoformat(timespec="seconds"), "Current working tree"
            else:
                data = extract_blob(commit, path)
                date, subject = commit_info(commit)
            if not data:
                continue
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                continue
            theme = theme_for_path_or_text(path, text)
            if theme not in {"EVA", "WH40K"}:
                continue
            if not is_logo_like(path, text):
                continue
            digest = hashlib.sha256(data).hexdigest()
            if digest in candidates:
                continue
            line_count, non_empty, max_width, charset, aspect = text_stats(text)
            source_file = write_candidate_file(digest, theme, text)
            candidates[digest] = Candidate(
                theme=theme,
                source_path=path,
                commit=commit,
                commit_date=date,
                commit_subject=subject,
                sha256=digest,
                line_count=line_count,
                non_empty_line_count=non_empty,
                maximum_column_width=max_width,
                character_set_used=charset,
                aspect_ratio=aspect,
                source_file=str(source_file.relative_to(ROOT)),
                source_kind="worktree" if commit == current_commit else "git",
            )

    for commit in reflog_commits():
        for path in paths:
            data = extract_blob(commit, path)
            if not data:
                continue
            digest = hashlib.sha256(data).hexdigest()
            if digest in candidates:
                continue
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                continue
            theme = theme_for_path_or_text(path, text)
            if theme not in {"EVA", "WH40K"} or not is_logo_like(path, text):
                continue
            date, subject = commit_info(commit)
            line_count, non_empty, max_width, charset, aspect = text_stats(text)
            source_file = write_candidate_file(digest, theme, text)
            candidates[digest] = Candidate(
                theme=theme,
                source_path=path,
                commit=commit,
                commit_date=date,
                commit_subject=subject,
                sha256=digest,
                line_count=line_count,
                non_empty_line_count=non_empty,
                maximum_column_width=max_width,
                character_set_used=charset,
                aspect_ratio=aspect,
                source_file=str(source_file.relative_to(ROOT)),
                source_kind="reflog",
            )

    return sorted(candidates.values(), key=lambda item: (item.theme, item.maximum_column_width, item.line_count, item.sha256))


def visible_box(text: str) -> tuple[int, int, int, int]:
    lines = text.splitlines()
    visible = [(index, line) for index, line in enumerate(lines) if line.strip()]
    if not visible:
        return 0, 0, 0, 0
    min_col = min(len(line) - len(line.lstrip(" ")) for _index, line in visible)
    max_col = max(len(line.rstrip(" ")) for _index, line in visible)
    top = visible[0][0]
    bottom = visible[-1][0] + 1
    return min_col, max_col, top, bottom


def render_metrics(text: str, width: int, height: int, *, line_height: float = 1.0, base_font_size: int = 10) -> RenderMetrics:
    lines = text.splitlines()
    max_width = max((len(line) for line in lines), default=0)
    min_col, max_col, top, bottom = visible_box(text)
    char_width = base_font_size * LOGO_CHAR_WIDTH_FACTOR
    effective_line_height = base_font_size * line_height
    visible_width = (max_col - min_col) * char_width
    visible_height = (bottom - top) * effective_line_height
    usable_width = width - 12
    usable_height = height - 12
    fit_scale = min(usable_width / visible_width, usable_height / visible_height) if visible_width and visible_height else 1.0
    transformed_width = visible_width * fit_scale
    transformed_height = visible_height * fit_scale
    left = (width - transformed_width) / 2
    top_clearance = (height - transformed_height) / 2
    return RenderMetrics(
        viewport_width=width,
        viewport_height=height,
        mode="supersampled_fit" if line_height == 1.0 else "supersampled_fit_line_height_0.85",
        base_font_size=base_font_size,
        line_height=line_height,
        natural_visible_width=visible_width,
        natural_visible_height=visible_height,
        fit_scale=fit_scale,
        transformed_width=transformed_width,
        transformed_height=transformed_height,
        clearance_left=left,
        clearance_right=width - left - transformed_width,
        clearance_top=top_clearance,
        clearance_bottom=height - top_clearance - transformed_height,
        occupancy=transformed_height / height if height else 0.0,
    )


def make_preview(text: str, theme_key: str, metrics: RenderMetrics, title: str) -> ft.Container:
    theme = THEMES["eva" if theme_key == "EVA" else "wh40k"]
    min_col, _max_col, top_line, _bottom_line = visible_box(text)
    char_width = metrics.base_font_size * LOGO_CHAR_WIDTH_FACTOR
    effective_line_height = metrics.base_font_size * metrics.line_height
    canvas_left = metrics.clearance_left - (min_col * char_width * metrics.fit_scale)
    canvas_top = metrics.clearance_top - (top_line * effective_line_height * metrics.fit_scale)
    canvas_width = max((len(line) for line in text.splitlines()), default=0) * char_width
    canvas_height = len(text.splitlines()) * effective_line_height
    text_control = ft.Text(
        text,
        font_family=LOGO_FONT_FAMILY,
        color=theme.primary_color,
        selectable=True,
        no_wrap=True,
        overflow=ft.TextOverflow.VISIBLE,
        size=metrics.base_font_size,
        style=ft.TextStyle(
            font_family=LOGO_FONT_FAMILY,
            size=metrics.base_font_size,
            weight=ft.FontWeight.NORMAL,
            height=metrics.line_height,
            letter_spacing=0,
            word_spacing=0,
            overflow=ft.TextOverflow.VISIBLE,
        ),
    )
    viewport = ft.Stack(
        width=metrics.viewport_width,
        height=metrics.viewport_height,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        controls=[
            ft.Container(
                content=text_control,
                width=canvas_width,
                height=canvas_height,
                left=canvas_left,
                top=canvas_top,
                scale=ft.Scale(scale=metrics.fit_scale, alignment=ft.alignment.top_left),
                clip_behavior=ft.ClipBehavior.NONE,
            )
        ],
    )
    return ft.Container(
        content=ft.Column(
            [
                ft.Text(title, size=11, color=theme.text_color, font_family=LOGO_FONT_FAMILY),
                ft.Container(content=viewport, width=metrics.viewport_width, height=metrics.viewport_height, bgcolor=theme.background_color, border=ft.border.all(1, theme.primary_color)),
                ft.Text(f"fit={metrics.fit_scale:.4f} occ={metrics.occupancy:.3f}", size=10, color=theme.secondary_color, font_family=LOGO_FONT_FAMILY),
            ],
            spacing=4,
            tight=True,
        ),
        padding=6,
        bgcolor=theme.surface_color,
    )


def score_candidate(candidate: Candidate, metrics: RenderMetrics) -> float:
    density_penalty = abs(metrics.occupancy - 0.88) * 3
    width_penalty = max(0, candidate.maximum_column_width - 90) * 0.02
    line_penalty = max(0, candidate.non_empty_line_count - 40) * 0.06
    small_penalty = max(0, 10 - candidate.non_empty_line_count) * 0.08
    charset_bonus = 0.2 if any(char in candidate.character_set_used for char in "#@█") else 0.0
    return 1.0 - density_penalty - width_penalty - line_penalty - small_penalty + charset_bonus


def recommend(candidates: list[Candidate], theme: str) -> list[dict]:
    rows = []
    for candidate in candidates:
        if candidate.theme != theme:
            continue
        text = (ROOT / candidate.source_file).read_text(encoding="utf-8")
        metrics_a = render_metrics(text, 162, 162, line_height=1.0)
        metrics_b = render_metrics(text, 162, 162, line_height=0.85)
        best_mode, best_metrics = max((("A", metrics_a), ("B", metrics_b)), key=lambda item: score_candidate(candidate, item[1]))
        rows.append({"candidate": candidate, "mode": best_mode, "metrics": best_metrics, "score": score_candidate(candidate, best_metrics)})
    rows.sort(key=lambda item: item["score"], reverse=True)
    return rows


def write_reports(candidates: list[Candidate]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "production_version": "7.13.30",
        "candidate_count": len(candidates),
        "candidates": [asdict(candidate) for candidate in candidates],
        "previews": {},
        "recommendations": {},
    }
    for candidate in candidates:
        text = (ROOT / candidate.source_file).read_text(encoding="utf-8")
        payload["previews"][candidate.sha256] = [
            asdict(render_metrics(text, width, height, line_height=line_height))
            for width, height in ((162, 162), (200, 162), (240, 162))
            for line_height in (1.0, 0.85)
        ]
    for theme in ("EVA", "WH40K"):
        payload["recommendations"][theme] = [
            {
                "rank": index + 1,
                "commit": row["candidate"].commit,
                "source_path": row["candidate"].source_path,
                "sha256": row["candidate"].sha256,
                "dimensions": {
                    "lines": row["candidate"].line_count,
                    "non_empty": row["candidate"].non_empty_line_count,
                    "max_width": row["candidate"].maximum_column_width,
                },
                "renderer_mode": "A supersampled fit" if row["mode"] == "A" else "B supersampled fit line-height 0.85",
                "score": round(row["score"], 4),
                "reason": "best heuristic balance of containment, density, and recognisable ASCII character mass at 162x162",
            }
            for index, row in enumerate(recommend(candidates, theme)[:3])
        ]
    AUDIT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Logo History Audit v7.13.30",
        "",
        "Read-only audit. No production assets were replaced.",
        "",
        f"Generated: {payload['generated_at']}",
        f"Total unique candidates: {len(candidates)}",
        "",
    ]
    for theme in ("EVA", "WH40K"):
        theme_candidates = [candidate for candidate in candidates if candidate.theme == theme]
        lines.extend([f"## {theme}", "", f"Unique candidates: {len(theme_candidates)}", ""])
        lines.extend(["### Top recommendations", ""])
        for item in payload["recommendations"][theme]:
            lines.extend(
                [
                    f"{item['rank']}. `{item['source_path']}` @ `{item['commit'][:7]}`",
                    f"   - SHA256: `{item['sha256']}`",
                    f"   - Dimensions: {item['dimensions']['lines']} lines, {item['dimensions']['max_width']} columns",
                    f"   - Renderer: {item['renderer_mode']}",
                    f"   - Reason: {item['reason']}",
                    "",
                ]
            )
        lines.extend(["### All candidates", ""])
        for candidate in theme_candidates:
            lines.extend(
                [
                    f"- `{candidate.sha256[:12]}` `{candidate.source_path}` @ `{candidate.commit[:7]}`",
                    f"  - date: {candidate.commit_date}",
                    f"  - subject: {candidate.commit_subject}",
                    f"  - dimensions: {candidate.line_count} lines, {candidate.non_empty_line_count} non-empty, {candidate.maximum_column_width} columns",
                    f"  - charset: `{candidate.character_set_used}`",
                    f"  - extracted: `{candidate.source_file}`",
                ]
            )
        lines.append("")
    AUDIT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_gallery(candidates: list[Candidate]) -> None:
    def main(page: ft.Page) -> None:
        page.title = "CONSENSUS Logo History Gallery"
        page.theme_mode = ft.ThemeMode.DARK
        page.window_width = 1500
        page.window_height = 950
        tabs = []
        for theme in ("EVA", "WH40K"):
            controls: list[ft.Control] = []
            for candidate in [item for item in candidates if item.theme == theme]:
                text = (ROOT / candidate.source_file).read_text(encoding="utf-8")
                preview_controls = []
                for width, height in ((162, 162), (200, 162), (240, 162)):
                    preview_controls.append(make_preview(text, theme, render_metrics(text, width, height, line_height=1.0), f"A {width}x{height}"))
                    preview_controls.append(make_preview(text, theme, render_metrics(text, width, height, line_height=0.85), f"B {width}x{height}"))
                controls.append(
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(f"{candidate.source_path} @ {candidate.commit[:7]} {candidate.sha256[:12]}", size=13, color=ft.Colors.WHITE, font_family=LOGO_FONT_FAMILY),
                                ft.Text(f"{candidate.line_count} lines / {candidate.maximum_column_width} columns / {candidate.commit_subject}", size=11, color=ft.Colors.GREY_400, font_family=LOGO_FONT_FAMILY),
                                ft.Row(preview_controls, spacing=8, wrap=True),
                            ],
                            spacing=6,
                        ),
                        padding=8,
                        border=ft.border.all(1, ft.Colors.GREY_800),
                    )
                )
            tabs.append(ft.Tab(text=theme, content=ft.ListView(controls=controls, spacing=10, padding=10, expand=True)))
        page.add(ft.Tabs(tabs=tabs, expand=True))

    ft.app(target=main)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a read-only historical logo candidate audit and optional Flet gallery.")
    parser.add_argument("--audit-only", action="store_true", help="Write reports without launching the Flet gallery.")
    args = parser.parse_args()

    candidates = collect_candidates()
    write_reports(candidates)
    print(f"Wrote {AUDIT_JSON}")
    print(f"Wrote {AUDIT_MD}")
    print(f"Unique EVA candidates: {sum(1 for item in candidates if item.theme == 'EVA')}")
    print(f"Unique WH40K candidates: {sum(1 for item in candidates if item.theme == 'WH40K')}")
    if not args.audit_only:
        run_gallery(candidates)


if __name__ == "__main__":
    main()
