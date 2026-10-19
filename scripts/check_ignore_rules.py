"""
Verify that .dockerignore actually excludes the files it claims to.

Docker's .dockerignore uses Go filepath.Match semantics (not gitignore):
  * a pattern without "/" matches against the BASENAME
  * a pattern with "/" matches against the whole path
  * "**" matches any number of path segments
  * the LAST matching pattern wins; "!" negates (re-includes)

This script emulates that and reports what would still be sent to the
Docker build context, so a secret or a 200 MB model can't slip in.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _compile(pattern: str) -> re.Pattern:
    """Translate a dockerignore pattern into a regex."""
    out = []
    i = 0
    while i < len(pattern):
        ch = pattern[i]
        if ch == "*":
            if pattern[i : i + 3] == "**/":
                out.append("(?:.*/)?")
                i += 3
                continue
            if pattern[i : i + 2] == "**":
                out.append(".*")
                i += 2
                continue
            out.append("[^/]*")
        elif ch == "?":
            out.append("[^/]")
        elif ch == "[":
            end = pattern.find("]", i)
            if end == -1:
                out.append(re.escape(ch))
            else:
                out.append(pattern[i : end + 1])
                i = end + 1
                continue
        else:
            out.append(re.escape(ch))
        i += 1
    return re.compile("^" + "".join(out) + "$")


def load_patterns(path: Path) -> list[tuple[str, re.Pattern, bool]]:
    patterns = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        negated = line.startswith("!")
        if negated:
            line = line[1:]
        patterns.append((line, _compile(line), negated))
    return patterns


def _candidates(rel_path: str) -> list[str]:
    """
    The path itself plus every ancestor directory.

    Docker excludes an entire subtree when a pattern matches a directory,
    so `node_modules` also excludes `node_modules/react/index.js`.
    """
    parts = rel_path.split("/")
    return ["/".join(parts[: i + 1]) for i in range(len(parts))]


def is_excluded(rel_path: str, patterns) -> bool:
    """Last matching pattern wins; a negated match re-includes the file."""
    excluded = False
    for raw, regex, negated in patterns:
        basename_only = "/" not in raw
        for candidate in _candidates(rel_path):
            target = candidate.rsplit("/", 1)[-1] if basename_only else candidate
            if regex.match(target):
                excluded = not negated
                break
    return excluded


def main() -> int:
    docker_patterns = load_patterns(REPO / ".dockerignore")

    # Files that must NEVER reach the build context
    must_exclude = [
        ".env",
        ".env.txt",
        ".env.example",          # handled separately (negated)
        "frontend/.env.production",
        "node_modules/react/index.js",
        "frontend/node_modules/react/index.js",
        "backend/venv/bin/python",
        "venv/lib/python/site-packages/x.py",
        "ml/models/isolation_forest.joblib",
        "data/model.pkl",
        "sentinel.db",
        "backend/__pycache__/x.pyc",
        "tests/test_health.py",
    ]

    # Files that MUST still reach the build context
    must_include = [
        ".env.example",
        "backend/requirements.txt",
        "backend/main.py",
        "backend/api/ws.py",
        "frontend/package.json",
        "frontend/src/App.jsx",
        "frontend/index.html",
        "data/security_logs.csv",
        "ml/models/evaluation_report.md",
        "docker/backend.Dockerfile",
        "docker/nginx.conf",
        "docker/entrypoint.sh",
    ]

    failures = 0

    print("-- must be EXCLUDED from the build context --")
    for p in must_exclude:
        if p == ".env.example":
            continue  # explicitly re-included, checked below
        excluded = is_excluded(p, docker_patterns)
        status = "excluded" if excluded else "LEAKED  "
        if not excluded:
            failures += 1
        print(f"  {status}  {p}")

    print("\n-- must be INCLUDED in the build context --")
    for p in must_include:
        excluded = is_excluded(p, docker_patterns)
        status = "included" if not excluded else "EXCLUDED"
        if excluded:
            failures += 1
        print(f"  {status}  {p}")

    print()
    if failures:
        print(f"FAILED — {failures} problem(s) found")
        return 1
    print("OK — .dockerignore behaves as intended")
    return 0


if __name__ == "__main__":
    sys.exit(main())
