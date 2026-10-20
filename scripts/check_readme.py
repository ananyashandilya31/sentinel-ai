"""
Validate README.md.

Checks:
  1. Every fenced code block is opened and closed (no stray/unclosed fence)
  2. Every image referenced in the README points at a path that exists
  3. Internal anchor links resolve to a heading in the document
  4. Headings are not duplicated (duplicate anchors break navigation)

Usage:
    python scripts/check_readme.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
README = REPO / "README.md"

FENCE = "`" * 3
IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
LINK_RE = re.compile(r"(?<!\!)\[[^\]]*\]\((#[^)]+)\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


def slugify(text: str) -> str:
    """GitHub-style anchor slug."""
    slug = text.strip().lower()
    slug = re.sub(r"[^\w\- ]", "", slug.replace("`", ""))
    return slug.replace(" ", "-")


def main() -> int:
    if not README.exists():
        print("README.md not found")
        return 1

    text = README.read_text(encoding="utf-8")
    lines = text.split("\n")
    problems: list[str] = []

    # ── 1. Code fence balance ───────────────────────────────────
    open_at: int | None = None
    for i, line in enumerate(lines, 1):
        if line.strip().startswith(FENCE):
            if open_at is None:
                open_at = i
            else:
                open_at = None
    if open_at is not None:
        problems.append(f"unclosed code block opened at line {open_at}")

    # ── 2. Image paths exist ─────────────────────────────────────
    images = IMAGE_RE.findall(text)
    for src in images:
        if src.startswith(("http://", "https://")):
            continue
        target = (REPO / src).resolve()
        if not target.exists():
            problems.append(f"image not found: {src}")

    # ── 3/4. Heading anchors ─────────────────────────────────────
    headings: list[str] = []
    in_fence = False
    for line in lines:
        if line.strip().startswith(FENCE):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = HEADING_RE.match(line)
        if m:
            headings.append(slugify(m.group(2)))

    seen: set[str] = set()
    for h in headings:
        if h in seen:
            problems.append(f"duplicate heading anchor: #{h}")
        seen.add(h)

    for anchor in set(LINK_RE.findall(text)):
        target = anchor.lstrip("#")
        if target and target not in seen:
            problems.append(f"broken anchor link: {anchor}")

    # ── Report ───────────────────────────────────────────────────
    print(f"README.md: {len(lines)} lines, {len(images)} image refs, {len(headings)} headings")
    if problems:
        print(f"\nFAILED — {len(problems)} problem(s):")
        for p in problems:
            print(f"  - {p}")
        return 1

    print("OK — code blocks balanced, images and anchors resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main())
