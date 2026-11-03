"""US1 integration tests: skills install into agent locations (V1/V2)."""

from __future__ import annotations

import os
from pathlib import Path

from installer_fixtures import InstallerTestCase


class TestLicenseAttribution(InstallerTestCase):
    """T030: FR-014 license/attribution material survives placement."""

    def test_copy_mode_carries_domain_license_and_attribution(self) -> None:
        expectations = {
            "hpc-skills": ("slurm", ["LICENSE", "ATTRIBUTION.md"]),
            "omd-standards": ("ee2-standards", ["ATTRIBUTION.md"]),
        }
        for dom, (leaf, files) in expectations.items():
            proj = self.make_project()
            self.run_installer(proj, "--agents", "codex", "--mode", "copy",
                               "--domains", dom)
            d2 = Path(proj) / ".agents" / "skills" / leaf
            for f in files:
                self.assertTrue((d2 / f).is_file(), f"{leaf}: {f}")

    def test_symlink_mode_leaf_licenses_visible(self) -> None:
        proj = self.make_project()
        self.run_installer(proj, "--agents", "codex", "--mode", "symlink",
                           "--domains", "literature-search")
        d = Path(proj) / ".agents" / "skills" / "literature-search"
        self.assertTrue((d / "LICENSE").is_file(), "flat-leaf LICENSE through link")
        self.assertTrue((d / "ATTRIBUTION.md").is_file())

    def test_generated_blocks_carry_source_paths(self) -> None:
        proj = self.make_project()
        self.run_installer(proj, "--agents", "claude", "--mode", "copy")
        text = (Path(proj) / "CLAUDE.md").read_text()
        self.assertIn(".github/instructions/", text,
                      "block attribution: per-file Source lines")


class TestSkillsInstall(InstallerTestCase):
    def test_v1_codex_fresh_project(self) -> None:
        """US1.1: --agents codex into a fresh project places every catalog skill."""
        proj = self.make_project()
        proc = self.run_installer(proj, "--agents", "codex")
        self.assertIn("install: project=", proc.stdout)
        skills_root = Path(proj) / ".agents" / "skills"
        self.assertTrue(skills_root.is_dir(), "codex skills dir must be created if missing")
        entries = sorted(p for p in skills_root.iterdir())
        expected = self.catalog_leaf_count()
        self.assertEqual(len(entries), expected)
        for entry in entries:
            self.assertTrue((entry / "SKILL.md").is_file(), f"{entry} lacks direct SKILL.md child")

    def test_v1_ee2_standards_references_survive(self) -> None:
        proj = self.make_project()
        self.run_installer(proj, "--agents", "codex", "--mode", "copy")
        ee2 = Path(proj) / ".agents" / "skills" / "ee2-standards"
        self.assertTrue((ee2 / "SKILL.md").is_file())
        refs = ee2 / "references"
        md = sorted(x.name for x in refs.glob("*.md"))
        self.assertTrue(md, "references/*.md must survive placement")
        # FR-014: domain-level attribution material rides along when the
        # leaf is flattened into the project in copy mode.
        self.assertTrue((ee2 / "ATTRIBUTION.md").is_file(),
                        "domain attribution must be installed with the skill")

    def test_v1_domain_license_overlay_copy_mode(self) -> None:
        proj = self.make_project()
        self.run_installer(proj, "--agents", "codex", "--mode", "copy",
                            "--domains", "hpc-skills")
        for name in ("slurm", "pbs", "rdhpcs-hera"):
            d = Path(proj) / ".agents" / "skills" / name
            self.assertTrue((d / "LICENSE").is_file(),
                            f"FR-014: domain LICENSE missing in {name}")
            self.assertTrue((d / "ATTRIBUTION.md").is_file())

    def test_v1_symlink_mode_leaves_purity(self) -> None:
        proj = self.make_project()
        self.run_installer(proj, "--agents", "codex", "--mode", "symlink",
                            "--domains", "hpc-skills")
        link = Path(proj) / ".agents" / "skills" / "slurm"
        self.assertTrue(link.is_symlink())
        # linked content stays whole inside the catalog clone; no overlay
        # files are fabricated in the project for symlink installs.
        self.assertFalse((link / "LICENSE").exists(),
                         "symlink mode must not fabricate overlay files in the project")
        self.assertTrue((link.resolve() / "SKILL.md").is_file())

    def test_mode_copy_snapshots_are_real_dirs(self) -> None:
        proj = self.make_project()
        self.run_installer(proj, "--agents", "claude", "--mode", "copy")
        git_commit = Path(proj) / ".claude" / "skills" / "git-commit"
        self.assertTrue(git_commit.is_dir() and not git_commit.is_symlink())
        self.assertTrue((git_commit / "SKILL.md").is_file())

    def test_mode_symlink_points_into_catalog(self) -> None:
        proj = self.make_project()
        self.run_installer(proj, "--agents", "claude", "--mode", "symlink")
        link = Path(proj) / ".claude" / "skills" / "git-commit"
        self.assertTrue(link.is_symlink())
        target = Path(os.path.realpath(link))
        self.assertTrue((target / "SKILL.md").is_file())

    def test_v2_subset_domains(self) -> None:
        """US1.2: --domains limits the set; others absent (FR-004/005)."""
        proj = self.make_project()
        self.run_installer(proj, "--agents", "codex", "--domains", "hpc-skills")
        names = {p.name for p in (Path(proj) / ".agents" / "skills").iterdir()}
        self.assertIn("slurm", names)
        self.assertIn("rdhpcs-hera", names)
        self.assertNotIn("git-commit", names)
        self.assertNotIn("ee2-standards", names)

    def test_v2_single_skill_by_name(self) -> None:
        proj = self.make_project()
        self.run_installer(proj, "--agents", "codex", "--skills", "git-commit")
        names = {p.name for p in (Path(proj) / ".agents" / "skills").iterdir()}
        self.assertEqual(names, {"git-commit"})

    def test_unknown_selection_token_is_error(self) -> None:
        proj = self.make_project()
        proc = self.run_installer(
            proj, "--agents", "codex", "--domains", "no-such-domain",
            check_rc=None,
        )
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertNotIn("Installed", proc.stdout)

    def test_copilot_installs_skills_to_github_dir(self) -> None:
        """Contract agent table: copilot installs into the repository-native
        .github/skills location."""
        proj = self.make_project()
        proc = self.run_installer(proj, "--agents", "copilot", "--skills", "git-commit")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertFalse((Path(proj) / ".agents").exists())
        self.assertFalse((Path(proj) / ".claude").exists())
        skill_paths = {e["path"] for e in self.entries_for(proj, "skill")}
        self.assertEqual(skill_paths, {".github/skills/git-commit"})
        self.assertTrue((Path(proj) / ".github" / "skills" / "git-commit" / "SKILL.md").is_file())


if __name__ == "__main__":
    import unittest

    unittest.main()
