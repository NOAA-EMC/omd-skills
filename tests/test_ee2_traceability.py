"""Guard the EE2 skill against invented rules and leaked RST markup.

Two directions are checked for every curated probe:
  * upstream -> file: the probe text exists in the pinned standards.rst, so the rule
    was not fabricated;
  * file -> upstream: the probe text exists in the reference file, so the vendoring
    actually carried the rule through.
Bolded bullet rule headings in references/*.md are extracted and checked the same way
(currently only standards.md section A carries lines in that shape; the authored review
checklists are tag-first bullets like "- **[portable]** ..." which never match this
shape and are deliberately not scanned, as they are skill prose, not vendored rules).
Residue and fence-balance checks ensure the converter left no raw RST markup behind.
The upstream Table 7 gap must be documented, never reconstructed. The vendored RST is
also checked against the digest the extractor pins, so the two cannot drift apart.
"""
from __future__ import annotations

import hashlib
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.ee2_extract import SECTIONS, UPSTREAM_MD5  # noqa: E402

RST_PATH = ROOT / "tests" / "data" / "ee-standards.rst"
REF_DIR = ROOT / "skills" / "omd-standards" / "ee2-standards" / "references"
SKILL_PATH = ROOT / "skills" / "omd-standards" / "ee2-standards" / "SKILL.md"

SMART = {"\u201c": '"', "\u201d": '"', "\u2018": "'", "\u2019": "'", "\u2013": "-", "\u2014": "--"}

# Curated probes per reference file. Each must appear in the upstream RST and in
# the corresponding reference file.
REQUIRED = {
    "workflow.md": [
        "all jobs are scheduled and submitted to the WCOSS resource manager, PBS Pro, by ecFlow",
        "set PBS (job scheduler) directives",
        "The purpose of the J-job is fourfold",
        "Downstream scripts must always use the variables established in the J-job and must never alter them",
        "job card -> J-job -> ex-script -> ush",
    ],
    "environment-variables.md": [
        "A standard set of environment variables has been established",
        "They must be used wherever appropriate",
        "Variables that are not used in a given job need not be defined",
        "Table 1: A list of the standard environment variables",
        "SENDDBN_NTC",
        "HOMEmodel",
        "COMOUTmodel",
        "KEEPDATA",
    ],
    "file-naming.md": [
        "File names must not contain special characters, uppercase characters or the date",
        "Use periods to separate categories and use underscores to separate words within the same category",
        "Use a leading 0 in describing a grid resolution that is less than 1",
        "Pad forecast hours with zeros so that all files have the same number of digits",
        "Output file names must be consistent across environments and application versions",
        "model.tHHz.var_info.f###.domain.format",
    ],
    "production-utilities.md": [
        "prep_step",
        "startmsg",
        "postmsg",
        "err_chk",
        "cpreq",
        "compath.py",
        "mail.py",
        "getsystem",
        "Table 2: getsystem output",
    ],
    "standards.md": [
        "Fatal errors must print a descriptive message beginning with",
        "Any job that runs longer than 15 minutes is required to have restart capability",
        "Code must compile without errors or warnings",
        "Using numbers 11-49 for input, 51-79 for output, 80-94 for work files",
        "w3nco",
    ],
    "date-and-grib-utilities.md": ["finddate.sh", "ndate", "setpdy.sh", "wgrib2"],
    "dataflow.md": [
        "Distributed Brokered Networking (DBNet) is used to disseminate products operationally from WCOSS",
        "All DBNet alerts must be wrapped in a check for",
        "The NCO Dataflow Team is responsible for maintaining DBNet",
    ],
    "code-delivery.md": [
        "release/vX.Y",
        "bugfix/<short_description>",
        "hotfix/<short_description>",
        "vX.Y-rc<#>",
        "Begin release candidate numbering at 0",
        "Lmod",
        "Table 3: Package Sub-directories",
        "Table 4: WCOSS directory structure",
        "Table 5: Structure of COM directories",
    ],
    "examples.md": [
        "Example 5: Version file",
        "Example 6: Job card",
        "Example 8: J-job",
        "Example 9: ex-script",
        "Example 13: sorc/pmb_forecast.fd/makefile",
        "Table 6: Binary executable production utilities accessible via module variables",
        "Table 8: Structure of sub-directories under com",
        "Table 9: Structure of DCOMROOT directory",
    ],
}

# A bolded rule heading may be followed by an optional portability tag.
HEADING_RE = re.compile(r"^\s*[*-] \*\*(?P<h>[^*]+?)\*\*(?:\s*\[(?:portable|WCOSS)\])?\s*$", re.M)
FENCE_RE = re.compile(r"^\s*```")

RESIDUE = [
    r"``",
    r"\[#",
    r":ref:",
    r"^\.\. _",
    r"[\u201c\u201d\u2018\u2019]",
    r"`_",
    r"\.\. note::",
    r"csv-table",
    r"code-block",
    r"^\^+$",
    r"::$",
]


def normalize(text: str) -> str:
    """Fold smart quotes, drop inline-literal backticks, collapse whitespace, lowercase.

    Case folding is required: upstream capitalizes some rule sentences differently
    than the skill quotes them.
    """
    for k, v in SMART.items():
        text = text.replace(k, v)
    text = text.replace("`", "")
    return re.sub(r"\s+", " ", text).strip().lower()


def strip_code_fences(md: str) -> str:
    """Drop fenced blocks so residue and heading checks see prose only."""
    out = []
    inf = False
    for line in md.split("\n"):
        if FENCE_RE.match(line):
            inf = not inf
            continue
        if not inf:
            out.append(line)
    return "\n".join(out)


class EE2Traceability(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not RST_PATH.is_file():
            # Fail loudly: a silent skip would let the whole guard vanish from CI
            # if tests/data/ee-standards.rst were ever deleted or moved.
            raise FileNotFoundError(f"vendored RST missing: {RST_PATH}")
        cls.rst = RST_PATH.read_text(encoding="utf-8")
        cls.norm_rst = normalize(cls.rst)

    def test_probe_set_covers_every_section(self):
        self.assertEqual(set(REQUIRED), set(SECTIONS), "probe files must match SECTIONS keys")

    def test_vendored_rst_matches_pinned_digest(self):
        # The references were generated from the digest this tool pins. If the vendored
        # copy drifts from it, every traceability assertion below is checking the wrong
        # document.
        digest = hashlib.md5(RST_PATH.read_bytes()).hexdigest()
        self.assertEqual(digest, UPSTREAM_MD5,
                         "tests/data/ee-standards.rst is not the revision the references were built from")

    def test_curated_probes_trace_to_upstream(self):
        for fname, probes in REQUIRED.items():
            for probe in probes:
                self.assertIn(normalize(probe), self.norm_rst,
                              f"probe is not in the upstream RST: {fname}: {probe!r}")

    def test_curated_probes_present_in_reference_files(self):
        for fname, probes in REQUIRED.items():
            path = REF_DIR / fname
            self.assertTrue(path.is_file(), f"missing reference file: {fname}")
            text = normalize(path.read_text(encoding="utf-8"))
            for probe in probes:
                self.assertIn(normalize(probe), text,
                              f"probe missing from generated file: {fname}: {probe!r}")

    def test_bolded_rule_headings_trace_to_upstream(self):
        for path in sorted(REF_DIR.glob("*.md")):
            prose = strip_code_fences(path.read_text(encoding="utf-8"))
            for match in HEADING_RE.finditer(prose):
                heading = match.group("h").strip().rstrip(":").strip()
                self.assertIn(normalize(heading), self.norm_rst,
                              f"invented rule heading in {path.name}: {heading!r}")

    def test_bolded_headings_are_present_in_standards_file(self):
        # Guards against the heading check passing vacuously: standards.md carries
        # the thirteen section-A rule headings this skill depends on.
        prose = strip_code_fences((REF_DIR / "standards.md").read_text(encoding="utf-8"))
        headings = [m.group("h").strip() for m in HEADING_RE.finditer(prose)]
        self.assertGreaterEqual(len(headings), 13,
                                f"expected at least 13 rule headings, found {len(headings)}")

    def test_every_section_a_rule_is_tagged(self):
        text = (REF_DIR / "standards.md").read_text(encoding="utf-8")
        section_a = text.split("### B. Compiled Code")[0]
        untagged = re.findall(r"^[*-] \*\*[^*]+\*\*$", section_a, re.M)
        self.assertEqual(untagged, [], f"untagged section-A rules: {untagged}")

    def test_no_rst_residue_outside_fences(self):
        for path in sorted(REF_DIR.glob("*.md")):
            prose = strip_code_fences(path.read_text(encoding="utf-8"))
            for pattern in RESIDUE:
                self.assertIsNone(re.search(pattern, prose, re.M),
                                  f"RST residue {pattern!r} in {path.name}")

    def test_fences_balanced(self):
        for path in sorted(REF_DIR.glob("*.md")):
            count = path.read_text(encoding="utf-8").count("```")
            self.assertEqual(count % 2, 0, f"unbalanced code fence in {path.name}")

    def test_upstream_table_seven_gap_documented_not_invented(self):
        # Upstream defines Tables 1-6, 8, 9 only. Table 7 is referenced in prose
        # ("Table 5 (below), Table 7, Table 8, and Table 9") but never defined. The
        # skill documents the gap instead of fabricating a table.
        defined = set(re.findall(r"Table (\d+):", self.rst))
        self.assertNotIn("7", defined, "upstream unexpectedly defines Table 7")
        self.assertIn("Table 7", self.rst,
                      "upstream no longer references Table 7 in prose")
        code_delivery = (REF_DIR / "code-delivery.md").read_text(encoding="utf-8")
        self.assertIn("Table 7", code_delivery, "code-delivery.md must note the Table 7 gap")
        self.assertNotIn("Table 7:", code_delivery,
                         "code-delivery.md must not invent a Table 7 definition")

    def test_references_are_self_contained(self):
        # A skill must not reference another skill by path. Checked on prose only:
        # upstream's own makefile and modulefile examples legitimately use ../.
        for path in sorted(REF_DIR.glob("*.md")):
            prose = strip_code_fences(path.read_text(encoding="utf-8"))
            self.assertNotIn("../", prose, f"path escape in {path.name}")

    def test_references_dir_matches_sections(self):
        # A botched re-sync that deletes a reference AND its SECTIONS entry would
        # otherwise pass every probe test; the directory and the map must agree.
        names = {p.name for p in REF_DIR.glob("*.md")}
        self.assertEqual(names, set(SECTIONS),
                         "references/ directory and SECTIONS keys have drifted apart")

    def test_skill_routing_and_gate_citations(self):
        # SKILL.md is the user-facing index; nothing else checks that it points at
        # real files and that its gate items still cite known references.
        text = SKILL_PATH.read_text(encoding="utf-8")
        table = text.split("## Which reference to load")[1].split("## Portability routing")[0]
        cited = re.findall(r"`(references/[\w.-]+\.md)`", table)
        self.assertEqual({c.split("/")[-1] for c in cited}, set(SECTIONS),
                         "routing table must cite exactly the SECTIONS references")
        for rel in cited:
            self.assertTrue((SKILL_PATH.parent / rel).is_file(), f"routing path missing: {rel}")
        gate = text.split("## Review gate")[1].split("## Scope")[0]
        items = re.findall(r"^\d+\.\s+\*\*.*$", gate, re.M)
        self.assertEqual(len(items), 20, f"expected 20 gate items, found {len(items)}")
        for line in items:
            refs = re.findall(r"([\w-]+\.md)", line)
            self.assertTrue(refs and all(r in SECTIONS for r in refs),
                            f"gate item cites unknown reference: {line[:60]!r}")
        self.assertRegex(text, r'upstream_version:\s*"[^"]+"\s*\n\s*as_of:\s*"[^"]+"',
                         "SKILL.md frontmatter must pin upstream_version and as_of")


if __name__ == "__main__":
    unittest.main()
