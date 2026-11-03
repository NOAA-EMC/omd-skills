"""Console entry point for the ``omd-skills`` command.

The engine is the repository's own ``install.sh`` (bash 3.2, offline, verified
by tests/test_installer_*.py). This wrapper locates the bundled catalog and
execs the installer with every argument passed through unchanged, so all
flags, subcommands (``uninstall``, ``list``), and exit codes
(0/2/3/4) match a clone-based run exactly.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import __version__

_USAGE_HINT = (
    "usage: omd-skills [--agents LIST] [--mode copy|symlink] [--project DIR]\n"
    "                [--domains LIST] [--no-interactive] [--list] [uninstall]\n"
    "run 'omd-skills --help' for details"
)


def catalog_root() -> Path | None:
    """Directory containing the installer payload (install.sh + catalog)."""
    here = Path(__file__).resolve().parent
    bundled = here / "templates"
    if (bundled / "install.sh").is_file():
        return bundled
    # editable install or running from a checkout: src/omd_skills -> repo root
    for parent in here.parents:
        if (parent / "install.sh").is_file() and (parent / "skills").is_dir():
            return parent
    return None


def _find_bash() -> str | None:
    found = shutil.which("bash")
    if found:
        return found
    for candidate in ("/bin/bash", "/usr/bin/bash", "/usr/local/bin/bash"):
        if os.path.exists(candidate):
            return candidate
    return None


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)

    if args and args[0] in ("--version", "-V"):
        print(f"omd-skills {__version__} (installer engine: install.sh)")
        return 0

    root = catalog_root()
    if root is None:
        print("omd-skills: installer catalog payload not found in this install; "
              "reinstall with 'pip install omd-skills' or run install.sh from a clone",
              file=sys.stderr)
        return 78  # EX_CONFIG

    bash = _find_bash()
    if bash is None:
        print("omd-skills: bash is required but was not found on PATH.\n"
              "On Windows use WSL or Git Bash.", file=sys.stderr)
        return 127

    engine = str(root / "install.sh")
    if not args:
        print(_USAGE_HINT, file=sys.stderr)
        return 2
    try:
        rc = subprocess.call([bash, engine, *args], env=os.environ.copy())
    except KeyboardInterrupt:
        return 130
    if rc < 0:  # terminated by signal N -> conventional 128+N
        rc = 128 - rc
    return rc


if __name__ == "__main__":
    sys.exit(main())
