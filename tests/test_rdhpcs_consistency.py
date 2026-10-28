"""Keep RDHPCS machine skills consistent with the shared policy in the slurm skill.

The RDHPCS fleet shares one QOS table, one home-quota rule, and one set of purge
rules, but every machine skill must restate the values its users need because a
skill is installed standalone. That duplication is deliberate; this module is the
guard that stops one copy from being edited and another left behind.

MACHINE_SKILLS is extended as each rdhpcs-* skill is added.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HPC = ROOT / "skills" / "hpc-skills"

# skill directory name -> expected metadata.system value
MACHINE_SKILLS: dict[str, str] = {
    "rdhpcs-hera": "hera",
}

# QOS columns that machine skills must agree with when they publish them.
CHECKED_QOS_COLUMNS = ("Max walltime", "Billing TRES")

# Per-system /home quota, taken from the per-system tables in
# https://docs.rdhpcs.noaa.gov/data/storage.html (Gaea 50, Ursa and Hera 30,
# Mercury and Pan 10) and the MSU-HPC guide (Orion and Hercules 10 GB).  The
# Queue Policy page claims a fleet-wide 50 GB, which those tables contradict;
# None means RDHPCS publishes no number for the system, so the skill must not
# invent one.
HOME_QUOTA_GB: dict[str, str | None] = {
    "rdhpcs-hera": "30 GB",
    "rdhpcs-ursa": "30 GB",
    "rdhpcs-gaea": "50 GB",
    "rdhpcs-ppan": "10 GB",
    "rdhpcs-mercury": "10 GB",
    "rdhpcs-orion": "10 GB",
    "rdhpcs-hercules": "10 GB",
    "rdhpcs-cloud": None,
}

# Facts that must appear in the slurm skill's shared-policy section.
REQUIRED_POLICY_FACTS = (
    "## RDHPCS Shared Policy",
    "mfa.princeton.rdhpcs.noaa.gov",
    "CAC/PIV",
    "YubiKey",
    "1500",
    "400",
    "Gaea 50 GB",
    "Ursa and Hera 30 GB",
    "not backed up",
    "scrontab",
    "hot pool",
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_md_tables(text: str) -> list[dict[str, str]]:
    """Return every markdown table row in the document as a header-keyed dict."""

    rows: list[dict[str, str]] = []
    header: list[str] | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [re.sub(r"\s+", " ", cell).strip() for cell in stripped.strip("|").split("|")]
            if header is None:
                header = cells
                continue
            if all(cell and set(cell) <= set("-: ") for cell in cells):
                continue  # separator row
            if len(cells) == len(header):
                rows.append(dict(zip(header, cells)))
        else:
            header = None
    return rows


def cell_tokens(cell: str) -> set[str]:
    """Strip markdown code spans and split a cell on ``/`` for comparison."""

    cleaned = re.sub(r"`([^`]*)`", r"\1", cell)
    return {part.strip() for part in cleaned.split("/") if part.strip()}


def qos_table(text: str) -> dict[str, dict[str, str]]:
    """Return the QOS-keyed table in a document, or {} when none has the checked columns.

    Machine skills that list QOS names without wall-time or TRES values (Orion,
    Hercules, Gaea) are deliberately not cross-checked, because RDHPCS publishes
    that table for Hera and Ursa only.
    """

    found: dict[str, dict[str, str]] = {}
    for row in parse_md_tables(text):
        if "QOS" not in row:
            continue
        if not all(column in row for column in CHECKED_QOS_COLUMNS):
            continue
        name = re.sub(r"`([^`]*)`", r"\1", row["QOS"]).strip()
        if name and name.lower() != "qos":
            found.setdefault(name, row)
    return found


class SlurmSharedPolicyTests(unittest.TestCase):
    def test_slurm_skill_documents_rdhpcs_policy(self) -> None:
        text = read(HPC / "slurm" / "SKILL.md")
        for fact in REQUIRED_POLICY_FACTS:
            with self.subTest(fact=fact):
                self.assertIn(fact, text)

    def test_slurm_skill_publishes_canonical_qos_table(self) -> None:
        table = qos_table(read(HPC / "slurm" / "SKILL.md"))
        for qos in ("batch", "urgent", "debug", "long", "windfall", "gpu", "gpuwf"):
            with self.subTest(qos=qos):
                self.assertIn(qos, table)


class MachineSkillConsistencyTests(unittest.TestCase):
    def test_expected_machine_skills_exist(self) -> None:
        for name, system in MACHINE_SKILLS.items():
            with self.subTest(skill=name):
                skill_md = HPC / name / "SKILL.md"
                self.assertTrue(skill_md.is_file(), f"missing {skill_md}")
                text = read(skill_md)
                self.assertIn(f"name: {name}", text)
                self.assertIn(f"system: {system}", text)
                self.assertIn("facility: rdhpcs", text)
                self.assertIn("allowed-tools: Read Write Grep Glob", text)

    def test_machine_qos_facts_match_slurm(self) -> None:
        canonical = qos_table(read(HPC / "slurm" / "SKILL.md"))
        self.assertTrue(canonical, "slurm skill has no canonical QOS table")
        for name in MACHINE_SKILLS:
            for qos, row in qos_table(read(HPC / name / "SKILL.md")).items():
                if qos not in canonical:
                    continue
                for column in CHECKED_QOS_COLUMNS:
                    with self.subTest(skill=name, qos=qos, column=column):
                        self.assertEqual(
                            cell_tokens(row[column]),
                            cell_tokens(canonical[qos][column]),
                            f"{name} restates {column} for {qos} differently from slurm",
                        )

    def test_home_quota_matches_the_system(self) -> None:
        """A /home table row states only that system's own published quota.

        RDHPCS publishes a per-system quota in its storage tables, and the fleet
        is not uniform, so every number in a ``/home`` row must equal the value
        for this system.  Systems with no published number must not state one.
        """

        for name in MACHINE_SKILLS:
            expected = HOME_QUOTA_GB[name]
            rows = [
                line
                for line in read(HPC / name / "SKILL.md").splitlines()
                if "/home" in line and line.lstrip().startswith("|")
            ]
            with self.subTest(skill=name):
                self.assertTrue(rows, f"{name} has no /home storage table row")
            for line in rows:
                stated = re.findall(r"\b(\d+) GB\b", line)
                with self.subTest(skill=name, line=line):
                    if expected is None:
                        self.assertEqual(stated, [], f"{name} states an unpublished quota")
                    else:
                        self.assertEqual(stated, [expected.split()[0]])

    def test_reference_links_resolve(self) -> None:
        for name in MACHINE_SKILLS:
            text = read(HPC / name / "SKILL.md")
            for target in re.findall(r"\]\((references/[^)#]+)", text):
                with self.subTest(skill=name, target=target):
                    self.assertTrue((HPC / name / target).is_file(), f"{name}: {target} missing")

    def test_no_stale_doe_references(self) -> None:
        """rdhpcs-* skills and the slurm skill must not cite the retired DOE systems.

        pbs/ is excluded on purpose: it documents PBS generally and legitimately
        mentions ALCF/Aurora.
        """

        stale = ("perlmutter", "frontier", "aurora", "NERSC", "OLCF", "ALCF")
        scope = [HPC / "slurm"] + sorted(HPC.glob("rdhpcs-*"))
        for skill_dir in scope:
            for path in sorted(skill_dir.rglob("*.md")):
                text = read(path)
                for token in stale:
                    with self.subTest(file=str(path.relative_to(ROOT)), token=token):
                        self.assertNotIn(token, text)


if __name__ == "__main__":
    unittest.main()
