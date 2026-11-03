"""Packaging/CLI contract tests: the omd-skills console command wraps
install.sh unchanged (args, exit codes, catalog discovery)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

from installer_fixtures import REPO, InstallerTestCase

SRC = REPO / "src"


def _run_cli(*args: str, cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "omd_skills", *args],
        capture_output=True, text=True, timeout=300, env=env, cwd=cwd or str(REPO),
    )


@unittest.skipUnless(shutil.which("bash"), "bash required")
class TestCLIFrontend(InstallerTestCase):
    def test_catalog_root_resolves_in_source_tree(self) -> None:
        sys.path.insert(0, str(SRC))
        try:
            from omd_skills import cli

            root = cli.catalog_root()
            self.assertIsNotNone(root)
            # bundled templates/ in a build tree, repo root in a bare checkout
            self.assertTrue((root / "install.sh").is_file())
            self.assertTrue((root / "skills").is_dir())
        finally:
            sys.path.remove(str(SRC))

    def test_version_flag(self) -> None:
        p = _run_cli("--version")
        self.assertEqual(p.returncode, 0)
        self.assertIn("omd-skills", p.stdout)

    def test_no_args_is_usage_error(self) -> None:
        p = _run_cli()
        self.assertEqual(p.returncode, 2)
        self.assertIn("usage: omd-skills", p.stderr)

    def test_passthrough_list_and_exit_codes(self) -> None:
        p = _run_cli("--list")
        self.assertEqual(p.returncode, 0)
        self.assertIn("skills (", p.stdout)
        bad = _run_cli("--agents", "nope", "--project", self.make_project())
        self.assertEqual(bad.returncode, 2)

    def test_cli_installs_like_a_clone(self) -> None:
        proj = self.make_project()
        p = _run_cli("--agents", "codex", "--mode", "copy",
                     "--domains", "omd-standards", "--no-interactive",
                     cwd=proj)
        self.assertEqual(p.returncode, 0)
        lock = Path(proj) / ".ompd" / "genesis.lock"
        self.assertTrue(lock.is_file())
        # same destination tree as running install.sh directly for this scope
        proj2 = self.make_project()
        self.run_installer(proj2, "--agents", "codex", "--mode", "copy",
                           "--domains", "omd-standards")
        self.assertEqual(self.tree_hash(proj), self.tree_hash(proj2))
