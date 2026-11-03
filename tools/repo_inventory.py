#!/usr/bin/env python3
"""Helpers for validating the repository structure and provenance docs."""

from __future__ import annotations

import re
from pathlib import Path


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _skill_names(root: Path) -> list[str]:
    if not root.is_dir():
        return []
    names = {path.parent.name for path in root.rglob("SKILL.md") if path.is_file()}
    return sorted(names, key=str.casefold)


def _top_level_skill_dirs(skills_root: Path) -> list[Path]:
    if not skills_root.is_dir():
        return []

    candidates = [
        path
        for path in skills_root.iterdir()
        if path.is_dir() and not path.name.startswith(".") and any(child.is_file() for child in path.rglob("SKILL.md"))
    ]
    return sorted(candidates, key=lambda path: path.name.casefold())


def _skill_tree_line(skill_root: Path) -> str:
    direct_skill = skill_root / "SKILL.md"
    skill_files = [path for path in skill_root.rglob("SKILL.md") if path.is_file()]
    if len(skill_files) == 1 and skill_files[0] == direct_skill:
        return f"{skill_root.name}/SKILL.md"

    names = _skill_names(skill_root)
    return f"{skill_root.name}/  # {', '.join(names)} ({len(names)})"


def _people_sort_key(name: str) -> tuple[str, str]:
    parts = name.split()
    last = parts[-1] if parts else name
    return (last.casefold(), name.casefold())


# Recognised ATTRIBUTION.md shapes (documented in CONTRIBUTING.md):
#   **Team:** <team name>
#   **Team:** <team name>: <Name (Org)>, <Name (Org)>, ...
#   **Author:** <Name (Org)>, <Name (Org)>, ...
#   **Authors:**
#   - <Name, Org>
# Put an author's institution in parentheses (or after a comma on a bullet line) so the
# name can be extracted reliably.
TEAM_LINE_PREFIX = "**Team:**"
AUTHOR_LINE_PREFIXES = ("**Author:**", "**Authors:**")


def _extract_name(fragment: str) -> str:
    fragment = fragment.strip()
    fragment = re.sub(r"\s*\[.*?\]$", "", fragment)
    fragment = re.split(r"\s*[\(<]", fragment, maxsplit=1)[0].strip()
    return fragment


def _names_from_csv_line(text: str) -> list[str]:
    names: list[str] = []
    for chunk in text.split(","):
        name = _extract_name(chunk)
        if name and not _looks_like_organization(name):
            names.append(name)
    return names


# Attribution lines may use either `Name (Org)` or `Name, Institution` (the latter is
# common in existing ATTRIBUTION.md files). Chunks that read as institutions rather
# than people are skipped so they never appear in the README contributor list.
ORGANIZATION_KEYWORDS = (
    "agency",
    "center",
    "centre",
    "corporation",
    "consortium",
    "department",
    "division",
    "foundation",
    "group",
    "institute",
    "institution",
    "laborator",
    "labs",
    "office",
    "program",
    "school",
    "team",
    "university",
)


def _looks_like_organization(name: str) -> bool:
    lowered = name.casefold()
    return any(keyword in lowered for keyword in ORGANIZATION_KEYWORDS)


def _notice_contact(root: Path) -> str | None:
    notice = root / "NOTICE"
    if not notice.is_file():
        return None
    match = re.search(r"^Contact:\s*(.+?)\s*<", _read(notice), re.MULTILINE)
    if not match:
        return None
    return _extract_name(match.group(1))


def _attribution_paths(root: Path) -> list[Path]:
    """Return every ATTRIBUTION.md under skills/, sorted by directory path."""

    skills = root / "skills"
    if not skills.is_dir():
        return []
    return sorted(
        (path for path in skills.rglob("ATTRIBUTION.md") if path.is_file()),
        key=lambda path: str(path.parent).casefold(),
    )


def _team_from_line(line: str) -> tuple[str | None, list[str]]:
    """Parse a `**Team:**` line into (team name, contributor names).

    A team line may carry a name list after a second colon, e.g.
    `**Team:** ModCon Base Data (AI-ModCon): Shreyas Cholia (LBNL), ...`.
    """

    tail = line[len(TEAM_LINE_PREFIX) :]
    names: list[str] = []
    if ":" in tail:
        team_part, _, people_part = tail.partition(":")
        team = team_part.strip().strip("*").strip()
        names.extend(_names_from_csv_line(people_part))
    else:
        team = tail.strip().strip("*").strip()
    team = re.sub(r"\s*[\(<].*$", "", team).strip()
    return (team or None), names


def build_attribution_contributors(root: Path) -> tuple[set[str], set[str]]:
    """Scan every `skills/**/ATTRIBUTION.md` for teams and individual authors.

    This replaces the earlier per-family hardcoded readers so that any skill family
    added to the catalog is credited automatically, including OMD-authored skills.
    """

    teams: set[str] = set()
    individuals: set[str] = set()

    for path in _attribution_paths(root):
        lines = _read(path).splitlines()
        for index, line in enumerate(lines):
            if line.startswith(TEAM_LINE_PREFIX):
                team, names = _team_from_line(line)
                if team:
                    teams.add(team)
                individuals.update(names)
            elif line.startswith(AUTHOR_LINE_PREFIXES):
                header = "**Authors:**" if line.startswith("**Authors:**") else "**Author:**"
                tail = line[len(header) :].strip()
                if not tail:
                    # Bullet list of authors follows the header line.
                    for bullet in lines[index + 1 :]:
                        if bullet.startswith("- "):
                            individuals.update(_names_from_csv_line(bullet[2:]))
                        elif bullet.strip():
                            break
                    continue
                individuals.update(_names_from_csv_line(tail))

    return teams, individuals


# Root label used in the README repository-structure tree. Keep in sync with the
# repository slug; it is a constant so the validator and the README agree.
README_ROOT_LABEL = "omd-skills/"


def build_readme_tree_lines(root: Path) -> list[str]:
    """Return the canonical README repository-structure tree as lines."""

    skills = root / "skills"
    lines = [
        README_ROOT_LABEL,
        "├── install.sh                 # install skills + instructions into a project, with a record (Method 1)",
        "├── unpack.sh                  # flatten skills into an agent's skills dir (Method 2, manual)",
        "├── skill-search/              # the upper-level discovery skill (Method 3)",
        "│   ├── SKILL.md",
        "│   └── scripts/skill_search.py",
        "├── skills/",
    ]

    skill_roots = _top_level_skill_dirs(skills)
    for index, skill_root in enumerate(skill_roots):
        branch = "└──" if index == len(skill_roots) - 1 else "├──"
        lines.append(f"│   {branch} {_skill_tree_line(skill_root)}")

    lines.extend(
        [
            "├── CONTRIBUTING.md",
            "├── LICENSE",
            "├── NOTICE                     # third-party licensing and attribution inventory",
            "├── README.md",
            "└── skill_spec.md              # Agent Skills format specification",
        ]
    )
    return lines


def _notice_catalog_contributors(root: Path) -> list[str]:
    """Return the NOTICE `Catalog Contributors:` entries, in declared order."""

    notice = root / "NOTICE"
    if not notice.is_file():
        return []
    for line in _read(notice).splitlines():
        if line.startswith("Catalog Contributors:"):
            entries = [e.strip() for e in line.split(":", 1)[1].split(",") if e.strip()]
            return entries
    return []


def build_readme_contributor_names(root: Path) -> list[str]:
    """Return the canonical contributor list for the README.

    The catalog-level roster mirrors the NOTICE registry (contact first, then
    every `Catalog Contributors:` entry, de-duplicated). Attribution for
    derived subtrees and their upstream authors lives in the per-skill
    `skills/**/ATTRIBUTION.md` files, which the policy checks require
    independently of this list.
    """

    names: list[str] = []
    contact = _notice_contact(root)
    if contact:
        names.append(contact)
    for name in _notice_catalog_contributors(root):
        if name not in names:
            names.append(name)
    return names
