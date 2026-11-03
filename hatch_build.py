"""Hatchling build hook: bundle the skill catalog into the package tree.

The repository keeps the catalog at the top level (``install.sh``,
``tools/installer/``, ``skills/``, ``.github/instructions/``) so a plain clone
works standalone. For pip/uvx installs this hook snapshots those same files
next to the Python CLI so the wheel is self-contained and offline-installable.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

ROOT = Path(__file__).resolve().parent
PKG_TEMPLATES = ROOT / "src" / "omd_skills" / "templates"

_PAYLOAD_FILES = ["install.sh"]
_PAYLOAD_DIRS = ["tools/installer", "skills", ".github/instructions"]
_SKIP_NAMES = {"__pycache__", ".DS_Store"}


def _copy_tree(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for item in sorted(src.iterdir()):
        if item.name in _SKIP_NAMES or item.suffix == ".pyc":
            continue
        if item.is_dir():
            _copy_tree(item, dst / item.name)
        else:
            shutil.copy2(item, dst / item.name)


class CustomHook(BuildHookInterface):
    """Populate src/omd_skills/templates immediately before wheel collection."""

    TARGET = "wheel"

    def clean(self, versions=None):
        if PKG_TEMPLATES.is_dir():
            shutil.rmtree(PKG_TEMPLATES, ignore_errors=True)

    def initialize(self, version, build_data):
        base = Path(self.root)
        for rel in _PAYLOAD_FILES + _PAYLOAD_DIRS:
            if not (base / rel).exists():
                raise FileNotFoundError(
                    f"installer payload missing: {base / rel} "
                    "(build must run from the omd-skills repository root)"
                )
        self.clean()
        PKG_TEMPLATES.mkdir(parents=True, exist_ok=True)
        for name in _PAYLOAD_FILES:
            shutil.copy2(base / name, PKG_TEMPLATES / name)
        for rel in _PAYLOAD_DIRS:
            _copy_tree(base / rel, PKG_TEMPLATES / rel)
        # inclusion of this git-ignored tree is forced by the
        # [tool.hatch.build] artifacts glob in pyproject.toml
        return build_data
