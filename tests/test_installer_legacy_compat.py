"""Pre-rename install state (the Genesis-era names) must still refresh, migrate
and uninstall.

The installer renamed its project state (``.ompd/genesis.lock`` ->
``.ompd/omd-skills.lock``) and its managed-block markers (``genesis-skills:``
-> ``omd-skills:``) to match the package name. Legacy names are recognized
only: they are migrated on the next refresh and stripped on uninstall, and are
never written again. ``InstallerTestCase.legacy_install`` builds a genuine
legacy install by running the current installer and renaming the result back,
so these tests exercise end-to-end behavior instead of hand-written state.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from installer_fixtures import InstallerTestCase


class TestLegacyStateMigration(InstallerTestCase):
    """A pre-rename install adopts the current names on refresh."""

    def test_refresh_migrates_lock_and_markers(self) -> None:
        proj = self.legacy_install()
        block_paths = sorted(self.paths_in(proj, "rules-block"))
        bodies = {p: self.block_text(proj, p)[1] for p in block_paths}
        # a real legacy install is self-consistent: the recorded block_hash
        # describes the legacy-generation block text
        for path in block_paths:
            self.assertEqual(self.block_text(proj, path)[0], "legacy", path)
            self.assertEqual(self.recorded_block_hash(proj, path),
                             self.recomputed_block_hash(proj, path), path)
        entry_count = len(self.lock_entries(proj, self.LEGACY_LOCK_NAME))

        self.run_installer(proj, *self.legacy_args)

        # the state is adopted under the current names only
        self.assertEqual(self.state_names(proj), {self.LOCK_NAME, self.LOCK_NAME + ".d"})
        self.assertFalse((self.ompd(proj) / self.LEGACY_LOCK_NAME).exists())
        self.assertEqual(len(self.lock_entries(proj)), entry_count,
                         "the record must carry over as-is")
        for path in block_paths:
            gen, inner = self.block_text(proj, path)
            self.assertEqual(gen, "current", path)
            self.assertEqual(self.marker_counts(proj, path), (1, 0), path)
            self.assertEqual(inner, self.normalize_generation(bodies[path]),
                             f"{path}: block content changed")
            # the record follows the migrated text, so hashes stay trustworthy
            self.assertEqual(self.recorded_block_hash(proj, path),
                             self.recomputed_block_hash(proj, path), path)
            self.assertIn("# keep me", (Path(proj) / path).read_text(),
                          f"{path}: lost user prose")

    def test_migration_is_idempotent(self) -> None:
        proj = self.legacy_install()
        self.run_installer(proj, *self.legacy_args)
        targets = sorted(self.paths_in(proj, "rules-block"))
        first = {p: (Path(proj) / p).read_text() for p in targets}
        p2 = self.run_installer(proj, *self.legacy_args)
        self.assertNotIn("migrated", p2.stdout + p2.stderr,
                         "nothing is left to migrate on the second run")
        for path in targets:
            self.assertEqual(first[path], (Path(proj) / path).read_text(), path)
            self.assertEqual(self.marker_counts(proj, path), (1, 0), path)

    def test_legacy_env_var_still_forces_interactivity(self) -> None:
        """GENESIS_FORCE_INTERACTIVE remains an accepted alias."""
        proj = self.legacy_install()
        skill = Path(proj) / sorted(self.paths_in(proj, "skill"))[0] / "SKILL.md"
        skill.write_text("totally mine\n")
        self.run_installer(
            proj, *self.legacy_args, stdin="n\n",
            env={"GENESIS_FORCE_INTERACTIVE": "1"}, check_rc=3)
        self.assertIn("totally mine", skill.read_text())


class TestLegacyUninstall(InstallerTestCase):
    """Uninstall strips either marker generation and tears the state down."""

    def test_uninstall_after_migration(self) -> None:
        proj = self.legacy_install()
        self.run_installer(proj, *self.legacy_args)
        path = sorted(self.paths_in(proj, "rules-block"))[0]
        self.run_installer(proj, "--agents", "claude", "--uninstall")
        self.assertFalse(self.ompd(proj).exists(), ".ompd must be torn down")
        text = (Path(proj) / path).read_text()
        self.assertNotIn("omd-skills:", text)
        self.assertNotIn("genesis-skills:", text)
        self.assertIn("# keep me", text)

    def test_uninstall_without_refresh(self) -> None:
        """A legacy install uninstalls even if it was never migrated."""
        proj = self.legacy_install()
        targets = sorted(self.paths_in(proj, "rules-block"))
        self.run_installer(proj, "--agents", "claude", "--uninstall")
        for path in targets:
            text = (Path(proj) / path).read_text()
            self.assertNotIn("skills:begin", text, path)
            self.assertIn("# keep me", text, f"{path}: lost user prose")
        self.assertFalse(self.ompd(proj).exists())
        self.assertFalse((self.ompd(proj).parent / "genesis.lock").exists())
        self.assertFalse((self.ompd(proj).parent / "genesis.lock.d").exists())


class TestForeignStateRefusals(InstallerTestCase):
    """Adopting legacy names must not weaken the refusal of foreign state."""

    def test_foreign_lock_refuses_alongside_legacy_staging(self) -> None:
        proj = self.make_project(files={".ompd/other.lock": "foreign\n"})
        (Path(proj) / ".ompd" / "genesis.lock.d").mkdir()
        p = self.run_installer(proj, "--agents", "codex", check_rc=3)
        self.assertIn("was not created by this installer", p.stderr)

    def test_foreign_lock_refuses_alongside_legacy_lock(self) -> None:
        proj = self.make_project(files={".ompd/other.lock": "foreign\n",
                                       ".ompd/genesis.lock": '{"v":1}\n'})
        p = self.run_installer(proj, "--agents", "codex", check_rc=3)
        self.assertIn("was not created by this installer", p.stderr)
        self.assertTrue((Path(proj) / ".ompd" / "genesis.lock").is_file(),
                        "a foreign dir's legacy-looking record is not ours to adopt")

    def test_crashed_legacy_install_resumes(self) -> None:
        """A legacy lock plus its own legacy staging tree is ours to migrate."""
        proj = self.legacy_install()
        stage = self.ompd(proj) / "genesis.lock.d"
        self.assertTrue(stage.is_dir(), "seed must leave a legacy staging tree")
        entry_count = len(self.lock_entries(proj, self.LEGACY_LOCK_NAME))
        self.run_installer(proj, *self.legacy_args)
        self.assertEqual(len(self.lock_entries(proj)), entry_count)
        self.assertFalse(stage.exists(), "staging moves with its record")


class TestMarkerGenerationRegression(InstallerTestCase):
    """The two marker generations must be told apart exactly."""

    def test_current_block_is_not_mistaken_for_legacy(self) -> None:
        proj = self.make_project()
        self.run_installer(proj, "--agents", "claude", "--mode", "copy",
                           "--domains", "literature-search")
        path = sorted(self.paths_in(proj, "rules-block"))[0]
        self.assertEqual(self.marker_counts(proj, path), (1, 0))
        self.assertEqual(self.block_text(proj, path)[0], "current")
        before = (Path(proj) / path).read_text()
        self.run_installer(proj, "--agents", "claude", "--mode", "copy",
                           "--domains", "literature-search")
        self.assertEqual(before, (Path(proj) / path).read_text(),
                         "an up-to-date block must not be rewritten")
        self.assertEqual(self.recomputed_block_hash(proj, path),
                         self.recorded_block_hash(proj, path))

    def test_legacy_block_is_detected(self) -> None:
        proj = self.legacy_install()
        path = sorted(self.paths_in(proj, "rules-block"))[0]
        self.assertEqual(self.marker_counts(proj, path), (0, 1))
        self.assertEqual(self.block_text(proj, path)[0], "legacy")
        copy = Path(proj) / "stray-copy.md"
        shutil.copy2(Path(proj) / path, copy)
        self.assertEqual(self.marker_counts(proj, "stray-copy.md"), (0, 1))
