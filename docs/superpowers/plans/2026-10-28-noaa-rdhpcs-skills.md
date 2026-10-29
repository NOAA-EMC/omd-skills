# NOAA RDHPCS HPC Skills Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the three DOE-lab machine skills in `skills/hpc-skills/` with eight `rdhpcs-*` skills for the NOAA RDHPCS fleet, refresh the `slurm` skill with the fleet-wide shared policy, and add a consistency test that stops the machine skills from drifting apart.

**Architecture:** Each machine gets one self-contained skill directory following the existing `perlmutter` skeleton (`SKILL.md` + `references/`). Cross-fleet policy (bastion access, QOS billing semantics, job caps, quotas, purge rules) is stated once in `slurm/SKILL.md`; machine skills restate only the values their own users need, because `unpack.sh` installs one skill directory at a time and a skill must load standalone. `tests/test_rdhpcs_consistency.py` parses the markdown QOS tables out of the files and asserts that where a machine skill states a checked column, it agrees with `slurm`.

**Tech Stack:** Markdown skill files with YAML frontmatter; Python 3 `unittest` (this repo has no pytest — tests run via `python3 tools/run_tests.py`); `tools/validate_skills.py` (five-profile skill validator); `tools/validate_repo_policy.py`; GNU `make`.

**Spec:** [../specs/2026-10-28-noaa-rdhpcs-skills-design.md](../specs/2026-10-28-noaa-rdhpcs-skills-design.md) — approved, committed as `76becf9`.

## Global Constraints

Every task below implicitly includes this section.

- Skill `name` is lowercase alphanumerics and hyphens, no leading/trailing/consecutive hyphen, ≤64 code points, and **must equal its directory name byte-for-byte** (`spec-name-must-match-directory`).
- `description` ≤1024 code points **after YAML parsing**. A `description: >` folded block keeps its trailing newline, which counts toward the limit — keep the visible text under ~1000 characters (`spec-desc-max-1024`, `spec-desc-block-scalar-trailing-newline`).
- `compatibility` is a single-line string, ≤500 code points, non-empty (`spec-compat-string-max-500`).
- `SKILL.md` ≤500 lines and body under ~5000 tokens (`spec-body-under-500-lines`, `spec-body-under-5000-tokens`). Target 180–260 lines, like the existing machine skills.
- `allowed-tools` on every `rdhpcs-*` skill is exactly `Read Write Grep Glob`. These skills author and review scripts; they do not submit them. No `Bash(sbatch *)` preapprovals.
- `metadata` on every `rdhpcs-*` skill has keys `version`, `system`, `facility: rdhpcs`, `scheduler`, `source` (the docs URL the facts came from), `as_of: "2026-10-28"`.
- Every machine fact comes from `https://docs.rdhpcs.noaa.gov`. **Never invent a number.** Where the docs are silent or malformed about a value, write the command the user runs to discover it (for example `sinfo -N -l` for Hera per-node memory) instead of guessing.
- No omd MCP tool calls inside any skill. omd was guidance for this conversion, not a runtime dependency.
- A skill must never reference another skill by path (`../slurm/...`). Say "see the `slurm` skill" in prose. Links inside a skill are relative to its own directory (`references/storage.md`).
- In a **storage table row for `/home`**, state only that system's own quota value. Put any contrast with the fleet's other quota in prose outside the table, because `test_home_quota_matches_the_system` reads quota tables row by row.
- Do not modify: `skills/hpc-skills/pbs/`, `NOTICE`, `tests/test_repo_policy.py`, `skills/baseeval-skills/perlmutter-ns-skills/`, `tools/`. The only files outside `skills/hpc-skills/` that change are `README.md` (line 100), `CONTRIBUTING.md` (line 25 tier count, Task 10 only), `docs/superpowers/`, and `tests/test_rdhpcs_consistency.py`.
- `README.md` and `skills/hpc-skills/ATTRIBUTION.md` change in the **same commit** as any skill directory add or delete, or `make policy` fails.
- Commit after every task, with a `Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>` trailer.

**Canonical fact source for all tasks:** spec §7.1–§7.8 (per-machine content), §6 (shared policy), and the QOS table below. Tasks quote the QOS table verbatim so a worker never has to re-derive it.

---

## Task 1: Shared RDHPCS policy in the `slurm` skill + consistency test

Establishes the canonical QOS/quota table and the guard that later tasks extend.

**Files:**
- Create: `tests/test_rdhpcs_consistency.py`
- Modify: `skills/hpc-skills/slurm/SKILL.md` (frontmatter lines 3–14; append one section at the end)

**Interfaces:**
- Produces: `tests/test_rdhpcs_consistency.py` with module-level `MACHINE_SKILLS: dict[str, str]` (skill dir name → expected `metadata.system`), `HOME_QUOTA_GB: dict[str, str | None]`, `parse_md_tables(text) -> list[dict[str, str]]`, `qos_table(text) -> dict[str, dict[str, str]]`, `cell_tokens(cell) -> set[str]`, `CHECKED_QOS_COLUMNS`. Tasks 2–9 modify `MACHINE_SKILLS` only.

- [ ] **Step 1: Write the failing test**

Create `tests/test_rdhpcs_consistency.py` with exactly this content:

```python
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
MACHINE_SKILLS: dict[str, str] = {}

# QOS columns that machine skills must agree with when they publish them.
CHECKED_QOS_COLUMNS = ("Max walltime", "Billing TRES")

# Per-system /home quota, from the per-system tables on
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_rdhpcs_consistency -v`
Expected: `test_slurm_skill_documents_rdhpcs_policy` FAILs (`'## RDHPCS Shared Policy' not found`), `test_slurm_skill_publishes_canonical_qos_table` FAILs (`'batch' not found in {}`), and `test_machine_qos_facts_match_slurm` FAILs on `self.assertTrue(canonical, ...)`. The other three `MachineSkillConsistencyTests` pass trivially because `MACHINE_SKILLS` is empty.

- [ ] **Step 3: Update the `slurm` skill frontmatter**

In `skills/hpc-skills/slurm/SKILL.md`, replace lines 3–14 (`description:` through `allowed-tools:`) with:

```yaml
description: >
  Slurm workload manager for HPC batch job scheduling, including NOAA RDHPCS
  fleet policy. Use when submitting jobs with sbatch/salloc/srun, monitoring
  with squeue/sacct/sreport, cancelling with scancel, writing #SBATCH job
  scripts, choosing RDHPCS QOS tiers (batch, urgent, debug, long, windfall,
  gpu, gpuwf), respecting login-node and scratch rules on Hera, Ursa, Orion,
  Hercules, or Gaea, escalating a pending job's QOS with scontrol update, or
  checking fair-share and file-system quotas with sacctmgr, sfairshare,
  saccount_params, or quota.
compatibility: Requires access to a Slurm cluster (sbatch, squeue, sacct, sinfo available in PATH). RDHPCS systems additionally require CAC/PIV or YubiKey authentication through an RDHPCS bastion and a signed master certificate.
metadata:
  version: "2.0"
  scheduler: slurm
  facility: rdhpcs
  source: https://docs.rdhpcs.noaa.gov/queue_policy/policies.html
  as_of: "2026-10-28"
allowed-tools: Bash(sbatch *) Bash(squeue *) Bash(scancel *) Bash(sinfo *) Bash(sacct *) Bash(salloc *) Bash(srun *) Bash(scontrol *) Bash(sacctmgr *) Bash(sreport *) Read Write Grep Glob
```

The `Bash(...)` preapprovals stay here — unlike the machine skills, the `slurm` skill documents live scheduler commands.

- [ ] **Step 4: Append the shared policy section**

Add at the end of `skills/hpc-skills/slurm/SKILL.md`. This table is the canonical one; Tasks 2 and 3 copy its rows exactly.

````markdown
## RDHPCS Shared Policy

These rules apply on every NOAA Research and Development High Performance
Computing System (RDHPCS): Hera, Ursa, Orion, Hercules, Gaea, PPAN, Mercury,
and Cloud. The per-machine skills restate the values their users need, because
a skill is installed standalone; this section is the shared reference. Facts
come from [docs.rdhpcs.noaa.gov](https://docs.rdhpcs.noaa.gov).

### Access

Access to the systems RDHPCS operates directly is SSH through a site bastion,
authenticated with a CAC/PIV card or a YubiKey:

```text
<system>-mfa.princeton.rdhpcs.noaa.gov
<system>-mfa.fairmont.rdhpcs.noaa.gov
```

Orion and Hercules are hosted by Mississippi State University and are **not**
behind those bastions: you SSH to `orion-login.hpc.msstate.edu` or
`hercules-login.hpc.msstate.edu` with an MSU username, MSU password and Duo,
or use Open OnDemand.

The first login attempt generates a master certificate request that must be
signed before you get a full session, usually in under five minutes. The
passphrase protecting that certificate must contain at least three words. If
you forget it, keep trying — the fourth attempt offers to recreate the master
certificate.

### QOS reference (Hera and Ursa)

Specify with `--qos=<name>` or `#SBATCH --qos=<name>`.

| QOS | Max walltime | Max cores | Billing TRES | Limits |
|-----|-------------|-----------|--------------|--------|
| `batch` | 8 hours | 8400 (Hera) / 14400 (Ursa) | 1 | Default QOS for projects with more than a windfall-only allocation |
| `urgent` | 8 hours | 8400 (Hera) / 14400 (Ursa) | 2 | One job per project pending or running. FairShare drops at twice the batch rate; below FairShare 0.45 the job is changed to `batch` and the user is notified on stderr |
| `debug` | 30 mins | 8400 (Hera) / 14400 (Ursa) | 1.25 | Two jobs per user. Highest priority; not for general fast-turnaround work |
| `long` | 16 hours | 4200 (Hera) / 7296 (Ursa) | 1 | Normal priority for 8 to 16 hour jobs |
| `windfall` | 8 hours | 8400 (Hera) / 14400 (Ursa) | 0 | Lowest priority, charges nothing, does not lower FairShare |
| `gpu` | 168 hours | 20 GPUs (Ursa `u1-h100`) | 1 | Requires a project whose name begins `gpu-` with allocation 2 or larger |
| `gpuwf` | 48 hours | 10 GPUs (`u1-h100`) / 8 GPUs (`u1-gh`, `u1-mi300x`) | 0 | Windfall GPU access, open to every Ursa project; at most 192 gpu-hours running per project |

A project with a **windfall-only** allocation (monthly allocation of 1) may
submit only to `windfall` or `gpuwf`.

**Job caps, every QOS on Hera and Ursa:** 1500 total jobs (pending plus
running) per project or account, and jobs beyond that are **rejected at submit
time**, not queued; 400 running jobs per project; only 20 jobs per project
gain age priority.

### Change a pending job's QOS

Start cheap and escalate only if the job will not start — RDHPCS recommends
this to protect FairShare:

```bash
sbatch --qos=windfall job.sh                  # submit at no cost
scontrol update job 26866,26867 qos=batch     # promote now
echo "scontrol update job 26990 qos=batch" | at -M now +5min   # promote if still pending
```

Never schedule an `at` time below 120 seconds. On Orion and Hercules `at`
exists only on `login1`. A job moved to a QOS it does not qualify for stays
pending forever rather than failing.

### Login nodes

Login (front end) nodes are shared and are **not** for computation: no
compiling, no parallel or threaded runs, no long I/O. Use the `service`
partition instead, which runs on nodes with external network and HPSS access.
Exceptions are covered by the RDHPCS Login Node Usage Policy.

### Recurring work

Prefer `scrontab` over `cron`. On Gaea and PPAN `cron` is not permitted at all
and `scrontab` must be used. Where `cron` exists it is limited to specific
front ends (Orion `orion-login-1`, Hercules `hercules-login-1`; Mercury runs
its own CRON service). The MSU guide documents plain `cron` only and does not
mention `scrontab`, so check `scrontab --help` on Orion or Hercules before
relying on it.

### File systems

| Rule | Value |
|------|-------|
| Home quota | **Per system, not uniform**: Gaea 50 GB; Ursa and Hera 30 GB; Mercury, Pan, Orion and Hercules 10 GB |
| Home backed up | Yes, regularly, plus per-day snapshots in `~/.snapshot` |
| Scratch backed up | **No** — scratch is not backed up and must never be treated as long-term storage |
| Scratch purged | Not purged, except `stmp` on `/scratch3-4` (weekly, Monday, files older than 30 days) and `/scratch5/purged` (files not accessed in 90 days) |
| Long-term archive | NESCC-HPSS or GFDL-DMF only |
| Check quota | `quota -Qs` on Gaea, Ursa, Hera and Mercury; `homeuse` on Pan; `saccount_params` on Hera and Orion only |
| Check fairshare | `sfairshare` on Hera only; `saccount_params` (Hera, Orion) reports per-project fairshare elsewhere |

The RDHPCS queue-policy page states a fleet-wide 50 GB home quota, but the
per-system tables on the data-storage page contradict it, and the example
output in that page's own quota section differs again. Trust what `quota -Qs`
reports on the system you are using over any number in these skills, and ask
the Help Desk rather than assuming a larger allowance.

Do not run jobs against files in `/home`, including through symlinks that
point at scratch. It degrades the home file system for every user on the
system.

On `/scratch3-4` the first 1 GB of each file is written to a solid-state hot pool
and mirrored to disk 10 to 15 minutes later, so reported usage for an active
file can look **doubled**. That is expected, not a quota bug.
````

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m unittest tests.test_rdhpcs_consistency -v`
Expected: `PASS` (2 tests in `SlurmSharedPolicyTests`; 5 in `MachineSkillConsistencyTests`, all trivially green while `MACHINE_SKILLS` is empty).

- [ ] **Step 6: Validate the skill**

Run: `python3 tools/validate_skills.py skills/hpc-skills/slurm --profile all --no-color --format text`
Expected: exit 0, zero `error` findings. If a `spec-body-under-500-lines` warning appears, check the line count (`wc -l skills/hpc-skills/slurm/SKILL.md`); under 500 lines the warning is informational and acceptable.

- [ ] **Step 7: Commit**

```bash
git add skills/hpc-skills/slurm/SKILL.md tests/test_rdhpcs_consistency.py
git commit -m "Add RDHPCS shared Slurm policy to the slurm skill

Consolidates the fleet-wide QOS table, job caps, login-node rules, and
file-system quotas from docs.rdhpcs.noaa.gov so per-machine skills can
restate only their own deltas. Adds the consistency guard that later
machine skills are checked against.

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 2: `rdhpcs-hera`

Defines the SKILL.md section order and the `references/` file set that Tasks 3–9 reuse: `job-scripts.md`, `storage.md`, `programming-env.md`.

**Files:**
- Create: `skills/hpc-skills/rdhpcs-hera/SKILL.md`
- Create: `skills/hpc-skills/rdhpcs-hera/references/job-scripts.md`
- Create: `skills/hpc-skills/rdhpcs-hera/references/storage.md`
- Create: `skills/hpc-skills/rdhpcs-hera/references/programming-env.md`
- Modify: `tests/test_rdhpcs_consistency.py` (`MACHINE_SKILLS` only)

**Interfaces:**
- Consumes: `MACHINE_SKILLS`, `qos_table()`, the canonical QOS table from Task 1 Step 4.
- Produces: the reference-file heading convention — `# <Machine> <Topic> Reference`, then `##` sections separated by `---`, markdown tables for facts, commented `bash` blocks for commands, 145–260 lines each (matching `skills/hpc-skills/perlmutter/references/storage.md` as it exists before Task 9 deletes it).

- [ ] **Step 1: Declare the expected skill in the test**

In `tests/test_rdhpcs_consistency.py`, replace the empty `MACHINE_SKILLS` assignment with:

```python
MACHINE_SKILLS: dict[str, str] = {
    "rdhpcs-hera": "hera",
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_rdhpcs_consistency.MachineSkillConsistencyTests -v`
Expected: failures naming `rdhpcs-hera` — `test_expected_machine_skills_exist` FAILs with `AssertionError: False is not true : missing .../skills/hpc-skills/rdhpcs-hera/SKILL.md`, and the other three tests ERROR with `FileNotFoundError` on the same path.

- [ ] **Step 3: Write `SKILL.md`**

Create `skills/hpc-skills/rdhpcs-hera/SKILL.md`:

````markdown
---
name: rdhpcs-hera
description: >
  NOAA RDHPCS Hera supercomputer at the NESCC facility in Fairmont West
  Virginia. Use when writing Slurm job scripts for Hera, choosing a Hera
  partition (hera, bigmem, novel, service) or QOS (batch, urgent, debug, long,
  windfall), requesting Intel Skylake 40-core nodes, pairing Intel compilers
  with IntelMPI or PGI with MVAPICH2, setting I_MPI_EXTRA_FILESYSTEM for MPI-IO
  on Lustre, placing data on /home, /scratch3-4, or /scratch5, archiving to
  HPSS, or checking Hera quotas and allocations.
compatibility: Script-authoring skill; no login required. Submitting jobs requires CAC/PIV or YubiKey access through hera-mfa.princeton.rdhpcs.noaa.gov or hera-mfa.fairmont.rdhpcs.noaa.gov and a signed master certificate.
metadata:
  version: "1.0"
  system: hera
  facility: rdhpcs
  scheduler: slurm
  source: https://docs.rdhpcs.noaa.gov/systems/hera_user_guide.html
  as_of: "2026-10-28"
allowed-tools: Read Write Grep Glob
---

# Hera — NOAA RDHPCS

Hera is an Intel Skylake system at the NOAA Environmental Security Computing
Center (NESCC) in Fairmont, West Virginia, used for high-impact weather
prediction work. It runs **Slurm** with LMOD hierarchical modules and shares its
file systems with Ursa.

## System Overview

| Component | Specification |
|-----------|--------------|
| CPU | Intel Xeon Gold 6148 "Skylake", 2.40 GHz, 40 cores per node |
| Regular compute nodes | 1,328 |
| Total cores | 63,840 |
| Large-memory nodes | 268 `bigmem` nodes, 40 cores and 384 GB each |
| Interconnect | Mellanox HDR-100 InfiniBand |
| Peak capacity | 3.27 PFLOPS |
| Scratch | HPFS Lustre on `/scratch3-4`, shared with Ursa |

The RDHPCS documentation does not publish per-node memory for regular Hera
nodes. Read the real value instead of assuming one:

```bash
sinfo -N -l
```

## Critical Requirements

```bash
#SBATCH -A <account>          # project account — mandatory on every RDHPCS job
#SBATCH -p hera,bigmem        # list every partition you can use; -p is partition
#SBATCH -t 4:00:00            # always set a wall clock, and do not over-ask
#SBATCH -o /scratch3/<user>/job_%j.out   # output to scratch, never to /home
```

Requesting several partitions lets the scheduler start the job on whichever
resource frees up first, which RDHPCS recommends for general compute work.

## Partitions

| Partition | QOS allowed | Use |
|-----------|-------------|-----|
| `hera*` | batch, windfall, debug, urgent, long | General compute. **Default** when no partition is given |
| `bigmem` | batch, windfall, debug, urgent, long | Large-memory jobs; 268 nodes at 40 cores and 384 GB |
| `novel` | novel | Nearly the whole system. Needs a help ticket in advance **and** `--qos=novel` |
| `service` | batch, windfall | External network and HPSS access. Runs on front ends; default 1 core, maximum 4 cores, 24 hour limit |

`hera` is the default partition — the documented way to confirm is:

```bash
sinfo -O partition     # hera* service bigmem novel  (asterisk marks the default)
```

## QOS

| QOS | Max walltime | Max cores | Billing TRES | Limits |
|-----|-------------|-----------|--------------|--------|
| `batch` | 8 hours | 8400 (Hera) / 14400 (Ursa) | 1 | Default QOS for projects with more than a windfall-only allocation |
| `urgent` | 8 hours | 8400 (Hera) / 14400 (Ursa) | 2 | One job per project pending or running. FairShare drops at twice the batch rate; below FairShare 0.45 the job is changed to `batch` and the user is notified on stderr |
| `debug` | 30 mins | 8400 (Hera) / 14400 (Ursa) | 1.25 | Two jobs per user. Highest priority; not for general fast-turnaround work |
| `long` | 16 hours | 4200 (Hera) / 7296 (Ursa) | 1 | Normal priority for 8 to 16 hour jobs |
| `windfall` | 8 hours | 8400 (Hera) / 14400 (Ursa) | 0 | Lowest priority, charges nothing, does not lower FairShare |

Caps for every QOS: 1500 total jobs per project or account (extra jobs are
**rejected at submit time**), 400 running jobs per project, and only 20 jobs per
project gain age priority. A windfall-only project may use only `windfall`.

Escalate a pending windfall job when it needs to run:

```bash
scontrol update job 26866,26867 qos=batch
echo "scontrol update job 26990 qos=batch" | at -M now +5min
```

## Minimal Job Script

```bash
#!/bin/bash
#SBATCH -A myproject
#SBATCH -J myjob
#SBATCH -p hera,bigmem
#SBATCH -q batch
#SBATCH -N 1
#SBATCH --ntasks-per-node=40
#SBATCH -t 2:00:00
#SBATCH -o /scratch3/user/myjob_%j.out
#SBATCH -e /scratch3/user/myjob_%j.err

module load intel impi
cd /scratch3/user/run.456
srun ./my_mpi_app
```

For a serial job, request one core, or use `--mem=<MB>` when sharing a node. Use
the `service` partition when the job needs external network or HPSS.

## Storage

| Filesystem | Path | Quota | Backup | Use for |
|-----------|------|-------|--------|---------|
| Home | `/home/First.Last` | 30 GB | Yes, plus `~/.snapshot` | Code and configs — never job I/O |
| Scratch | `/scratch3`, `/scratch4` | project-based | **No** | Job input and output |
| VAST scratch | `/scratch5` | project quota for `rstprod` and `public`; `/scratch5/purged/<First.Last>` for everyone else | **No** | All-flash experimental area, 90-day purge |
| Archive | NESCC-HPSS via `hsi` / `htar` | portfolio-managed | Yes | Long-term retention |

`stmp` on `/scratch3-4` is purged every Monday for files older than 30 days.
Scratch is never backed up. Do not run jobs against files in `/home`.

## Modules

LMOD on Hera is **hierarchical**, so `module avail` shows only what the loaded
compiler family exposes. Search everything with `module spider`.

```bash
module spider <pkg>          # authoritative availability search
module load intel impi       # Intel compilers + IntelMPI
module load pgi mvapich2     # PGI compilers + MVAPICH2
module list; module purge
```

## Interactive Jobs

```bash
salloc -A myproject -p hera -q debug -N 1 -t 30:00 --ntasks-per-node=40
```

Packaged applications such as IDL, ImageMagick, MATLAB, and R run on compute
nodes, not front ends. IDL defaults to one thread per virtual CPU — 48 on a Hera node — so
set `IDL_CPU_TPOOL_NTHREADS=1` for a serial run. IDL needs over 10 GB of memory for many
workloads, which means `bigmem` or a whole node.

## Common Gotchas

- No `-A` — RDHPCS rejects the job; the account is mandatory everywhere.
- `novel` partition without `--qos=novel`, or without a prior help ticket.
- Compiling on a login node instead of the `service` partition.
- Writing job output to `/home` — 30 GB quota on Hera, and heavy I/O harms it for everyone.
- MPI-IO on Lustre without `I_MPI_EXTRA_FILESYSTEM=on` and `I_MPI_EXTRA_FILESYSTEM_LIST=lustre`; Intel MPI does not detect the file system by default.
- Running a threaded application with default thread counts on a shared node.
- Treating `/scratch5/purged` as durable — files untouched for 90 days are deleted.
- A windfall-only project submitting to `batch` instead of `windfall`.

## Additional Resources

- Annotated job scripts, hybrid MPI+OpenMP, arrays: [references/job-scripts.md](references/job-scripts.md)
- File systems, quotas, HPSS archiving, purge rules: [references/storage.md](references/storage.md)
- Compilers, MPI choices, profilers, debuggers: [references/programming-env.md](references/programming-env.md)
- Hera user guide: https://docs.rdhpcs.noaa.gov/systems/hera_user_guide.html
````

- [ ] **Step 4: Write `references/job-scripts.md`**

Create `skills/hpc-skills/rdhpcs-hera/references/job-scripts.md` (~200 lines) titled `# Hera Job Scripts Reference`, with these sections separated by `---`. Every script is complete and copy-pasteable, uses `<account>` for the project, and writes output under `/scratch3`.

1. **Directive reference** — table of `#SBATCH` options with the Hera value: `-A` (mandatory), `-p` (`hera` default, `bigmem`, `novel`, `service`), `-q`, `-N`, `--ntasks-per-node` (40 on both regular and `bigmem` nodes), `-c`, `--mem`, `-t`, `-o`/`-e`, `-J`, `--exclusive`, `--constraint`, `--dependency`, `--array`.
2. **Serial job** — 1 task on `service` when external network or HPSS is needed, `-c 1`.
3. **MPI job on full nodes** — `module load intel impi`, `mpiifort`-built binary, `srun ./app`, and the `I_MPI_EXTRA_FILESYSTEM` exports for MPI-IO.
4. **OpenMP-only job** — `--ntasks=1 --cpus-per-task=40`, `export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK`, `export KMP_AFFINITY=scatter` (RDHPCS-recommended for Intel OpenMP on Hera).
5. **Hybrid MPI+OpenMP** — `--ntasks-per-node=8 -c 5`, `OMP_NUM_THREADS=5`.
6. **Large-memory job** — `-p bigmem`, 384 GB and 40 cores, and why `--mem` is unnecessary when taking the whole node.
7. **Job array** — `--array=1-24%4`, per-task input from `$SLURM_ARRAY_TASK_ID`.
8. **Interactive allocation** — `salloc` on `debug` for 30 minutes, then `srun` steps.
9. **HPSS staging job** — `service` partition, `hsi`/`htar` put and get, 4-core and 24-hour maximums restated.
10. **Output conventions** — `%j`, `%x`, `%A_%a` placeholders; always write under `/scratch3`, never `/home`.

- [ ] **Step 5: Write `references/storage.md`**

Create `skills/hpc-skills/rdhpcs-hera/references/storage.md` (~150 lines) titled `# Hera Storage Reference`. Sections:

1. **Filesystem overview** — table of `/home`, `/scratch3`, `/scratch4`, `stmp`, `/scratch5`, `/scratch5/purged`, NESCC-HPSS with quota, backup, and purge columns. Scratch paths follow the documented layout `/scratch[3,4]/<portfolio>/<project>/<user>`.
2. **Quota checks** — `saccount_params` (Hera and Orion only; prints home quota in MB, per-project scratch usage and file counts), `quota -Qs`, and snapshot recovery from `/home/$USER/.snapshot/`.
3. **Purge policy** — `stmp` purged weekly on Mondays for files older than 30 days; `/scratch5/purged` purged for files not accessed in 90 days; other scratch is not purged but never backed up. Include a `find … -atime +25` example for locating aging files and the advice to tar many small files to protect the file-count quota (`saccount_params` reports `Files` against `FileQUota`).
4. **Hot pools** — the first 1 GB of each file on `/scratch3-4` lands on the SSD hot pool and is mirrored to disk after 10–15 minutes, so reported usage can look doubled; not a quota bug.
5. **HPSS archiving** — `hsi "put <local> <hpss>"` / `hsi "get …"`, `htar -cvf` / `htar -xvf`, `hsi "expls <path>"` and `hsi "expfind -d <days>"` for expiration dates, `module load hpss` (Hera) inside a batch job on the `service` partition, because only those front ends hold the external connection.
6. **What goes where** — code and configs in `/home`, job I/O in `/scratch3`, long-term data in HPSS, and the prohibition on running jobs against `/home` files or symlinks pointing at `/home`.

- [ ] **Step 6: Write `references/programming-env.md`**

Create `skills/hpc-skills/rdhpcs-hera/references/programming-env.md` (~190 lines) titled `# Hera Programming Environment Reference`. Sections:

1. **LMOD hierarchical modules** — why `module avail` hides packages, `module spider`, loading a compiler family before the MPI module.
2. **Compiler and MPI pairings** — the documented combinations:

   | Stack | Load | Wrappers |
   |-------|------|----------|
   | Intel | `module load intel impi` | `mpiifort`, `mpiicc`, `mpiicpc` (note the extra `i`) |
   | PGI | `module load pgi mvapich2` | `mpif90`, `mpif77`, `mpicc` |

3. **MPI-IO on Lustre** — `export I_MPI_EXTRA_FILESYSTEM=on`, `export I_MPI_EXTRA_FILESYSTEM_LIST=lustre`.
4. **Thread affinity** — `KMP_AFFINITY=scatter` recommended for Intel OpenMP; `OMP_NUM_THREADS` must match the cores requested or the job harms its neighbors.
5. **Profiling** — `I_MPI_STATS=<1-10>` and `I_MPI_STATS_SCOPE=col` for Intel MPI collective statistics; Intel Trace Analyzer; Linaro Forge; TAU.
6. **Debugging** — Linaro Forge DDT, GDB, Intel MPI debugging notes.
7. **Python** — Miniforge install guidance, with the RDHPCS warning that support staff do not maintain user-installed packages.
8. **Contrib projects** — `/contrib/<project>` holds a project's own compiled software; creating or changing it requires a help ticket.

- [ ] **Step 7: Run test to verify it passes**

Run: `python3 -m unittest tests.test_rdhpcs_consistency -v`
Expected: `PASS`. If `test_machine_qos_facts_match_slurm` fails, the Hera row was transcribed differently from the Task 1 canonical table — fix Hera; never edit the `slurm` table to match a machine skill.

- [ ] **Step 8: Validate the skill**

Run: `python3 tools/validate_skills.py skills/hpc-skills/rdhpcs-hera --profile all --no-color --format text`
Expected: exit 0, zero `error` findings.

- [ ] **Step 9: Commit**

```bash
git add skills/hpc-skills/rdhpcs-hera tests/test_rdhpcs_consistency.py
git commit -m "Add rdhpcs-hera skill

Hera partition and QOS rules, the shared NESCC file systems, and the
Intel/PGI module pairings RDHPCS documents. Authored as a script-authoring
skill: it writes and reviews #SBATCH scripts rather than submitting them.

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 3: `rdhpcs-ursa` (CPU and GPU queues)

**Files:**
- Create: `skills/hpc-skills/rdhpcs-ursa/SKILL.md`
- Create: `skills/hpc-skills/rdhpcs-ursa/references/job-scripts.md`
- Create: `skills/hpc-skills/rdhpcs-ursa/references/storage.md`
- Create: `skills/hpc-skills/rdhpcs-ursa/references/programming-env.md`
- Modify: `tests/test_rdhpcs_consistency.py`

**Interfaces:**
- Consumes: `MACHINE_SKILLS`, the Task 2 section order and reference-file naming.
- Produces: the Ursa partition/QOS pairing table that `references/job-scripts.md` expands.

- [ ] **Step 1: Declare the expected skill in the test**

```python
MACHINE_SKILLS: dict[str, str] = {
    "rdhpcs-hera": "hera",
    "rdhpcs-ursa": "ursa",
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_rdhpcs_consistency.MachineSkillConsistencyTests.test_expected_machine_skills_exist -v`
Expected: failures and errors naming `rdhpcs-ursa` (missing `SKILL.md`).

- [ ] **Step 3: Write `SKILL.md`**

Create `skills/hpc-skills/rdhpcs-ursa/SKILL.md`. Frontmatter:

```markdown
---
name: rdhpcs-ursa
description: >
  NOAA RDHPCS Ursa system at NESCC in Fairmont West Virginia, covering both CPU
  and GPU queues. Use when writing Slurm jobs for Ursa, choosing between the
  u1-compute CPU partition and the u1-h100, u1-gh, and u1-mi300x GPU partitions,
  pairing a GPU partition with the gpu or gpuwf QOS, requesting NVIDIA H100,
  GH200 Grace Hopper, or AMD MI300X accelerators with --gpus=h100:N,
  --gpus=gh200:N, or --gpus=mi300x:N, deciding whether a gpu- project
  allocation is required, using --exclusive on shared nodes, or loading Intel
  oneAPI, nvhpc, AOCC, HPC-X, or ROCm on Ursa.
compatibility: Script-authoring skill; no login required. Submitting jobs requires CAC/PIV or YubiKey access through ursa-mfa.princeton.rdhpcs.noaa.gov or ursa-mfa.fairmont.rdhpcs.noaa.gov and a signed master certificate.
metadata:
  version: "1.0"
  system: ursa
  facility: rdhpcs
  scheduler: slurm
  source: https://docs.rdhpcs.noaa.gov/systems/ursa_user_guide.html
  as_of: "2026-10-28"
allowed-tools: Read Write Grep Glob
---
```

Body, in this section order, with exactly these facts:

1. **`# Ursa — NOAA RDHPCS`** — AMD Genoa CPU and GPU systems at NESCC, Fairmont WV, connected to the same high-performance file systems as Hera. Slurm; Rocky 9.4.
2. **`## System Overview`** table:

   | Component | Specification |
   |-----------|--------------|
   | CPU compute | 576 nodes, 2× AMD EPYC 9654 "Genoa", 96 physical cores each, 192 threads per node, 384 GB |
   | CPU peak | 4.25 PFLOPS |
   | GPU system | 58 nodes, 2× NVIDIA H100-94 GB each, 11,136 cores, 3.48 PFLOPS |
   | Exploratory GPU | 8× GH200 nodes (ARM Grace 72 cores, ~213 GB) and 5× MI300X nodes (96 Intel cores, 8× MI300X 192 GB each) |
   | Interconnect | Mellanox NDR-200 InfiniBand |
   | Scratch | over 100 PB shared with Hera at NESCC, above 1000 GB/s aggregate |

3. **`## Critical Requirements`** — `-A <account>` mandatory; a GPU job must name **both** a GPU partition and a GPU QOS (`-p u1-h100` with `-q gpu` or `-q gpuwf`) because the partition alone is not sufficient; add `--exclusive` when the job needs a whole node, since node sharing is enabled for all job sizes as of 2026-06-18; always set `-t`.
4. **`## CPU Partitions and QOS`** — table `Partition | QOS allowed | Notes`:

   | Partition | QOS allowed | Notes |
   |-----------|-------------|-------|
   | `u1-compute` | `batch`, `windfall`, `debug`, `urgent`, `long` | Default CPU partition. `batch` is the QOS name, not a partition |
   | `u1-service` | `batch`, `windfall` | Front-end work needing external network or HPSS; up to 64 cores and 250 GB per user, 24 hour limit |

   Then the CPU QOS table copied **verbatim** from the Task 1 canonical table, restricted to the five CPU rows (`batch`, `urgent`, `debug`, `long`, `windfall`) with identical `Max walltime` and `Billing TRES` cell text — this is what `test_machine_qos_facts_match_slurm` compares.
5. **`## GPU Partitions and QOS`** — table `Partition | QOS | Requires | Limits`:

   | Partition | QOS | Requires | Limits |
   |-----------|-----|----------|--------|
   | `u1-h100` | `gpu` | project name begins `gpu-`, allocation 2 or larger | 20 GPUs per project, 168 hours, Billing TRES 1 |
   | `u1-h100` | `gpuwf` | any Ursa project | 10 GPUs per project, 48 hours, Billing TRES 0, at most 192 gpu-hours running per project |
   | `u1-gh` | `gpuwf` | any Ursa project | 8 GH200 nodes, first come first served, ARM Grace 72 cores, 1 gpu-hour bills as 72 core-hours |
   | `u1-mi300x` | `gpuwf` | any Ursa project | 5 MI300X nodes, first come first served, 96 Intel cores and 8× MI300X 192 GB per node, 1 gpu-hour bills as 12 core-hours |

   Add the two GPU rows of the canonical table (`gpu`, `gpuwf`) as a `QOS | Max walltime | Max cores | Billing TRES | Limits` table too, with cell text identical to Task 1, so the guard covers them.
6. **`## GPU Access Rules`** — priority H100 access needs a `gpu-` project with allocation ≥ 2 plus `gpu` QOS; every Ursa project can use H100s at windfall priority with `gpuwf`; a CPU-allocation project gets H100 windfall access and a GPU-allocation project gets non-GPU windfall access; `u1-gh` and `u1-mi300x` are exploratory, `gpuwf` only, no allocation or FairShare charge; GPU-hour conversions as in the table above.
7. **`## Minimal CPU Job Script`**:

```bash
#!/bin/bash
#SBATCH -A myproject
#SBATCH -J myjob
#SBATCH -p u1-compute
#SBATCH -q batch
#SBATCH -N 1
#SBATCH --ntasks-per-node=192
#SBATCH -t 2:00:00
#SBATCH -o /scratch3/user/myjob_%j.out

module load intel impi
srun ./my_mpi_app
```

8. **`## Minimal GPU Job Script`**:

```bash
#!/bin/bash
#SBATCH -A mygpu_project
#SBATCH -J mltrain
#SBATCH -p u1-h100
#SBATCH -q gpu
#SBATCH -N 1
#SBATCH --ntasks-per-node=4
#SBATCH --gpus=h100:3
#SBATCH -c 48
#SBATCH -t 8:00:00
#SBATCH --exclusive
#SBATCH -o /scratch3/user/ml_%j.out

module load nvhpc
export SLURM_CPU_BIND=cores
srun ./my_gpu_app
```

   Follow with the windfall variant for a project without a GPU allocation
   (`-q gpuwf --gpus=h100:2`) and the interactive exploratory forms:

```bash
salloc -A mygpu_project -t 480 -p u1-gh     -q gpuwf --gpus=gh200:1
salloc -A mygpu_project -t 480 -p u1-mi300x -q gpuwf --gpus=mi300x:2
```

9. **`## Storage`** table: `/home/First.Last` 30 GB backed up with `~/.snapshot`; `/scratch3` and `/scratch4` Lustre with project quotas, not backed up; `/scratch5` VAST all-flash where only `rstprod` and `public` hold non-purged project quota and everyone else uses `/scratch5/purged/<First.Last>` from a 250 TB pool with a 90-day not-accessed purge; NESCC-HPSS for archive.
10. **`## Modules`** — spack-based layout; `module spider <pkg>` is the search entry point; `module load`/`module list`/`module purge`.
11. **`## Compilers and MPI`** — table of Intel oneAPI, NVIDIA nvhpc, AMD AOCC and of Intel MPI, HPC-X, OpenMPI. State that RDHPCS measured **HPC-X** as better performing and more stable than Intel MPI on the NDR-200 fabric for communication-intensive benchmarks, so prefer it for GPU MPI work. ROCm targets MI300X; CUDA targets H100 and GH200.
12. **`## Common Gotchas`** — `-p u1-h100` with no GPU QOS; `gpu` QOS from a project whose name does not begin `gpu-` (use `gpuwf`); omitting `--exclusive` when the job needs a whole node; assuming production x86 binaries run on the ARM `u1-gh` nodes; exceeding the 192 gpu-hour `gpuwf` cap; compiling on a login node; writing job output to `/home`; treating `/scratch5/purged` as durable; a windfall-only project submitting to `batch`.
13. **`## Additional Resources`** — links to the three `references/` files plus https://docs.rdhpcs.noaa.gov/systems/ursa_user_guide.html

- [ ] **Step 4: Write `references/job-scripts.md`**

Create `skills/hpc-skills/rdhpcs-ursa/references/job-scripts.md` (~220 lines) titled `# Ursa Job Scripts Reference`. Sections separated by `---`, each with a complete `bash` script:

1. **Directive reference** — table with Ursa values: `u1-compute` 192 threads per node, `u1-h100` 192 cores and 2 GPUs per node, `--gpus=<type>:<count>` with `h100`, `gh200`, `mi300x`, `--exclusive`, `u1-service` capped at 64 cores and 250 GB per user with a 24-hour limit.
2. **CPU MPI full-node job.**
3. **CPU OpenMP-only job** with `OMP_NUM_THREADS` matching requested cores.
4. **Single-GPU H100 job** (`--gpus=h100:1`, `module load nvhpc`) and a **multi-GPU variant** (`--gpus=h100:2 --ntasks-per-node=2`).
5. **H100 at windfall priority** for a CPU-allocation project (`gpuwf`).
6. **GH200 interactive session** — `salloc` then compile and run on the node, noting the ARM CPU requires a rebuild.
7. **MI300X job** with ROCm modules and `--gpus=mi300x:2`.
8. **`u1-service` serial job** for HPSS or external-network work.
9. **Job array** over 24 members with `%4` concurrency.
10. **QOS escalation** — submit `--qos=windfall`, then `scontrol update job <id> qos=batch`, with the 120-second minimum `at` delay rule.

- [ ] **Step 5: Write `references/storage.md`**

Create `skills/hpc-skills/rdhpcs-ursa/references/storage.md` (~160 lines) titled `# Ursa Storage Reference`, with the same six-section set as Task 2 Step 5 (overview table, quota checks, purge policy, hot pools, HPSS, what-goes-where), using the Ursa `/scratch5` VAST details from §9 above: only `rstprod` and `public` get non-purged project quota; all other projects use `/scratch5/purged/<First.Last>` where the directory name must match the NOAA `First.Last`; 250 TB quota under that tree; 90-day not-accessed purge; RDHPCS wants performance feedback via a help ticket titled `/scratch5` performance results.

- [ ] **Step 6: Write `references/programming-env.md`**

Create `skills/hpc-skills/rdhpcs-ursa/references/programming-env.md` (~190 lines) titled `# Ursa Programming Environment Reference`. Sections: spack-based LMOD modules and `module spider`; compiler table (Intel oneAPI, nvhpc, AOCC) with the accelerator stack each targets; MPI table (Intel MPI, HPC-X, OpenMPI) with the documented HPC-X recommendation on NDR-200; CUDA versus ROCm selection per partition; the ARM caveat for `u1-gh` (rebuild, do not copy binaries); GPU-aware MPI settings; affinity guidance (`--cpu-bind=cores`, `--hint=nomultithread`, `KMP_AFFINITY=scatter`); Python via `module load rdhpcs-python` plus Miniforge with the self-support warning; **Apptainer** as the container runtime on Ursa (RDHPCS supports SingularityCE/Apptainer and explicitly not Docker; Podman is PPAN/Gaea only); profilers (Linaro Forge MAP, TAU) and debuggers (DDT remote connection — note that gdb, GDB4HPC and Valgrind4hpc are documented for Gaea, not Ursa). Also record that the fleet compilers page recommends Intel plus Intel MPI and lists only Intel and NVIDIA compilers, while the Ursa page adds AOCC and prefers HPC-X on NDR-200.

- [ ] **Step 7: Run test to verify it passes**

Run: `python3 -m unittest tests.test_rdhpcs_consistency -v`
Expected: `PASS`.

- [ ] **Step 8: Validate the skill**

Run: `python3 tools/validate_skills.py skills/hpc-skills/rdhpcs-ursa --profile all --no-color --format text`
Expected: exit 0, zero `error` findings.

- [ ] **Step 9: Commit**

```bash
git add skills/hpc-skills/rdhpcs-ursa tests/test_rdhpcs_consistency.py
git commit -m "Add rdhpcs-ursa skill covering CPU and GPU queues

Ursa GPU access is partition-and-QOS paired, so the skill documents
u1-compute and u1-service alongside u1-h100, u1-gh, and u1-mi300x, the
gpu versus gpuwf allocation rules, GPU-hour billing conversions, and the
node-sharing change that makes --exclusive load-bearing.

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 4: `rdhpcs-orion`

**Files:**
- Create: `skills/hpc-skills/rdhpcs-orion/SKILL.md`
- Create: `skills/hpc-skills/rdhpcs-orion/references/job-scripts.md`
- Create: `skills/hpc-skills/rdhpcs-orion/references/storage.md`
- Create: `skills/hpc-skills/rdhpcs-orion/references/programming-env.md`
- Modify: `tests/test_rdhpcs_consistency.py`

**Interfaces:**
- Consumes: `MACHINE_SKILLS`, the Task 2 skeleton.
- Produces: the "quote the operator's own QOS table under its own column names"
  pattern that Task 5 reuses for Hercules. MSU-HPC publishes a per-QOS table for
  Orion and Hercules, but with `Maximum Wall Clock` / `Billing TRES Factor`
  headers and a node-count dimension, so the consistency guard (which keys on
  `Max walltime` / `Billing TRES`) does not cross-check it. Gaea (Task 6)
  publishes a differently-shaped table again.

- [ ] **Step 1: Declare the expected skill in the test**

```python
MACHINE_SKILLS: dict[str, str] = {
    "rdhpcs-hera": "hera",
    "rdhpcs-ursa": "ursa",
    "rdhpcs-orion": "orion",
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_rdhpcs_consistency.MachineSkillConsistencyTests.test_expected_machine_skills_exist -v`
Expected: failures and errors naming `rdhpcs-orion` (missing `SKILL.md`).

- [ ] **Step 3: Write `SKILL.md`**

Create `skills/hpc-skills/rdhpcs-orion/SKILL.md`. Frontmatter:

```markdown
---
name: rdhpcs-orion
description: >
  NOAA RDHPCS Orion system at the Mississippi State University HPC2
  collaboratory. Use when writing Slurm job scripts for Orion, choosing the
  orion, bigmem, or service partition, requesting Skylake 40-core nodes, working
  with MSU-HPC account management that is separate from RDHPCS accounts,
  placing data on the work or work2 Lustre scratch filesystems or the 10 GB NFS
  home, using cron on orion-login-1, or discovering LMOD compiler and MPI
  modules on Orion.
compatibility: Script-authoring skill; no login required. Orion is hosted at Mississippi State University, so access uses MSU credentials and Duo rather than the NOAA RDHPCS bastions.
metadata:
  version: "1.0"
  system: orion
  facility: rdhpcs
  scheduler: slurm
  source: https://docs.rdhpcs.noaa.gov/systems/MSU-HPC_user_guide.html
  as_of: "2026-10-28"
allowed-tools: Read Write Grep Glob
---
```

Body sections, in this order, with exactly these facts:

1. **`# Orion — MSU-HPC (NOAA RDHPCS)`** — NOAA's allocation on the Mississippi State University HPC2 system. Slurm with LMOD; **CentOS 7.x** (the MSU guide's login banner shows 7.6 and its differences section states Orion runs CentOS 7.x while Hercules runs Rocky Linux 9.x).
2. **`## System Overview`** table: Dell EMC PowerEdge C6420 nodes; Intel Xeon Gold 6148, 20 cores × 2 sockets = **40 cores per node** at 2.40 GHz; **1,792 compute nodes plus 8 bigmem nodes** (1,800 total); **72,000 cores**; **192 GB per compute node** (12×16 GB DDR4-2666) and **384 GB per bigmem node** (12×32 GB); Mellanox HDR-100 InfiniBand; 4 login nodes, 4 data transfer nodes, 2 development nodes.
3. **`## Critical Requirements`** — `-A <account>` mandatory; **always set `-t`**, because the default wall clock is **5 minutes** and an unset job is silently killed at 5 minutes; do not request less than 5 minutes; over-requesting hurts everyone through longer waits and worse scheduler efficiency.
4. **`## Partitions`** table:

   | Partition | QOS allowed | Notes |
   |-----------|-------------|-------|
   | `orion` | batch, windfall, debug, urgent, novel | General compute, 40 cores and 192 GB per node |
   | `bigmem` | batch, windfall, debug, urgent | 8 nodes with 384 GB |
   | `service` | batch, windfall, debug, urgent | Serial jobs, maximum **1 core**, 24 hour limit, runs on front ends with external network and HPSS access |

5. **`## QOS`** — MSU-HPC **does** publish a per-QOS table for Orion and Hercules, with limits expressed in **nodes** rather than cores. Quote it under **MSU's own column names** (`Minimum Nodes`, `Maximum Nodes`, `Maximum Wall Clock`, `Billing TRES Factor`) so the guard does not attempt a cell-by-cell comparison against the fleet table, and state that the wall clock and Billing TRES values agree with the fleet table while the node limits, job caps, and `urgent` semantics differ:

   | QOS | Min nodes | Max nodes | Maximum Wall Clock | Billing TRES Factor | Limits |
   |-----|-----------|-----------|--------------------|---------------------|--------|
   | `batch` | 1 | 500 | 8 hours | 1.0 | Default QOS for projects with more than a windfall-only allocation |
   | `urgent` | 1 | 500 | 8 hours | 2.0 | **One job per project pending or running.** FairShare drops at twice the batch rate; below 0.45 the job is changed to `batch` and the user is notified on stderr |
   | `debug` | 1 | 500 | 30 minutes | 1.25 | Two jobs per user pending or running; highest priority; not for fast-turnaround general work |
   | `windfall` | 1 | 500 | 8 hours (24 h on `service`) | 0.0 | Lowest priority, charges nothing, does not lower FairShare; the only QOS a windfall-only project may use |
   | `novel` | 501 | largest partition | 8 hours | 1.0 | Nearly the whole system; requires a help ticket first |

   Every QOS on Orion: at most **400 pending/running jobs per project** (extra
   jobs are **rejected**), and only 20 jobs per project gain age priority. That
   is a different cap than the 1500-total/400-running pair RDHPCS publishes for
   Hera and Ursa, so do not present the fleet numbers as Orion's. Also offer the
   live read, using the form RDHPCS documents:

   ```bash
   sacctmgr show qos format=Name,MaxWall
   ```

   Mention that `novel` requires a help ticket and that Orion has no `long`,
   `gpu`, or `gpuwf` QOS.
6. **`## Minimal Job Script`**:

```bash
#!/bin/bash
#SBATCH -A myproject
#SBATCH -J myjob
#SBATCH -p orion
#SBATCH -q batch
#SBATCH -N 1
#SBATCH --ntasks-per-node=40
#SBATCH -t 4:00:00
#SBATCH -o /work/noaa/myproject/user/myjob_%j.out

module load contrib
module load intel impi
cd /work/noaa/myproject/user/run.456
srun ./my_mpi_app
```

7. **`## Storage`** table: `/home/<userid>` NFS **10 GB**, backed up nightly; `work` DDN Lustre SFA18k, 9 PB scratch, **not** backed up; `work2` DDN Lustre SFA18k with a hot-pool SSD cache, 18 PB scratch, **not** backed up; HPSS/HSMS reached from the `service` partition. Both `work` filesystems are scratch, not archive, and MSU advises moving data back to Niagara because Orion's disk space is limited. Do **not** list a `$TMPDIR` row: RDHPCS documents `$TMPDIR` only for PPAN (where it points into `/vftmp`), and the MSU guide says nothing about it, so there is no documented node-local temp path on Orion. Likewise do not promise a `.snapshot` recovery path — the fleet data-storage page describes it but does not name Orion, and the MSU guide says only that home is backed up nightly.
8. **`## Accounts and Projects`** — MSU HPC2 administers accounts entirely independently of RDHPCS; PI and Project/Portfolio Managers must hold an active MSU account to manage projects online; NOAA portfolio, project, and user management goes through MSU; TAPS password change within 3 days plus MSU security and insider-threat training and Duo; accounts lock after 90 days inactivity and are scheduled for deletion 2 weeks after expiry, and the home directory is deleted with the account. The MSU username is **not** the RDHPCS `First.Last` long username. `module load contrib noaatools` then `saccount_params` is the quota and project report (there is no `account_params` alias, and `quota -Qs` is not documented for Orion).
9. **`## Cron and Recurring Work`** — MSU documents plain **`cron` on `orion-login-1` only**; it does not document `scrontab` for Orion, so tell the reader to check `scrontab --help` before relying on it. `at` exists on `login1` only.
10. **`## Common Gotchas`** — no `-t` means a 5-minute kill; `-t` below 5 minutes; assuming the 30 GB RDHPCS home quota when Orion gives 10 GB; writing job output to `/home`; scheduling cron on the wrong login node; a second `urgent` job per project being rejected; `novel` without a ticket or below 501 nodes; using an RDHPCS name where an MSU username or project name is required; compiling on a login node; expecting FairShare to carry between Orion and Hercules.
11. **`## Additional Resources`** — three `references/` links plus https://docs.rdhpcs.noaa.gov/systems/MSU-HPC_user_guide.html

- [ ] **Step 4: Write `references/job-scripts.md`**

Create `skills/hpc-skills/rdhpcs-orion/references/job-scripts.md` (~200 lines) titled `# Orion Job Scripts Reference`, following the Task 2 Step 4 section set (directive table, wall-clock discipline, serial, MPI full-node, OpenMP-only, hybrid, bigmem, interactive `salloc`, timed/dependent jobs, `service` network job, recurring work, output conventions, monitoring), with Orion values: 40 cores per node, `orion`/`bigmem`/`service` partitions, `service` capped at 1 core and 24 hours, mandatory `-t` with the 5-minute default called out in the directive table, output under `/work/noaa/<project>/<user>`. MSU does not document job arrays for Orion, so state that rather than inventing an example, and title the recurring-work section `## Cron` (plain cron on `orion-login-1`) because `scrontab` is not documented there. Use MSU's own documented patterns where they exist: `srun -n $SLURM_NTASKS`, `module load intel <version>`, `--export=ALL,<var>=<value>`, `--begin=`, `--mail-user` plus `--mail-type` both required, `-D .` or `cd $SLURM_SUBMIT_DIR`.

- [ ] **Step 5: Write `references/storage.md`**

Create `skills/hpc-skills/rdhpcs-orion/references/storage.md` (~150 lines) titled `# Orion Storage Reference`. Sections: filesystem overview table (10 GB home, `work` 9 PB, `work2` 18 PB with hot pool, `/apps`, `/apps/contrib`); which Lustre filesystem to use (MSU's own advice: try both, `work2` has 2x capacity plus an SSD tier that may help small files and random I/O); quota checks (`saccount_params` — documented on Orion, it prints home quota in **MB** plus `DiskInUse`/`Quota`/`Files`/`FileQUota` per project directory — `du -sh $HOME`, `shpcrpt -c orion -s`/`-p <project>`, and `reportFSUsage`, which prints a LUSTRE QUOTA AND USAGE REPORT with `Directory/Group`, `Usage (GB)`, `Quota (GB)`, `Limit (GB)`, `Files`, `Percentage` and `**` on over-quota projects; say plainly that `quota -Qs` is listed for Gaea, Ursa, Hera and Mercury but **not** Orion, and that there is no `account_params` alias); file-count quota advice (tar small files); home backup and deletion policy — state that RDHPCS's `.snapshot` online-backup feature is documented on the fleet data-storage page which does not name Orion, so do not promise it; transfers (SCP/SFTP to `orion-dtn-{1..4}.hpc.msstate.edu` or the round-robin `orion-dtn`, Globus endpoint `msuhpc2-Orion-dtn`, MSU's recommendation to use Globus and to move data back to Niagara); `/apps/contrib` requests and the development-node write gateway; archiving — the MSU guide publishes **no** `hsi`/`htar` example for Orion, so tell the reader to confirm approved archive commands with the help system rather than copying the Hera staging script.

- [ ] **Step 6: Write `references/programming-env.md`**

Create `skills/hpc-skills/rdhpcs-orion/references/programming-env.md` (~180 lines) titled `# Orion Programming Environment Reference`. MSU-HPC publishes the module list rather than a fixed compiler/MPI recommendation, so this file must teach **discovery** instead of asserting pairings: LMOD's hierarchical layout and `module spider` (documented fleet-wide, including the MSU systems); `module avail` after loading a compiler family; the compiler families and MPI implementations as things to enumerate at runtime, using MSU's own `module load intel <version>` / `module load impi <version>` example; `module load contrib noaatools` for the NOAA tooling; module-set environment variables that differ between systems (MSU's WRF/netCDF warning: `NETCDF_C_ROOT`/`NETCDF_FORTRAN_ROOT` must be assembled into one `NETCDF`, `PNETCDF=$PARALLEL_NETCDF_ROOT`); MPI runtime problems MSU documents (node-memory crashes → more nodes or fewer tasks per node plus `--exclusive`; Intel `I_MPI_SHM_HEAP_VSIZE` default 8192 MB, Hercules-only symptom; stack-size segfaults on both); MPI launch patterns with `srun`; OpenMP thread and affinity settings stated as portable defaults because RDHPCS publishes no Orion affinity recipe; Python via `module load contrib` then `module load rdhpcs-python` (or `rdhpcs-conda`, no activation needed) with conda-forge as the only approved channel and Miniforge as the installer; containers through **`module load singularity`**, plus the Spack-managed `module load spack-managed-x86-64_v3/v1.0 apptainer` that loads a separate environment and may not combine well with other modules, the RDHPCS registry at registry.rdhpcs.noaa.gov, and the fact that Podman is documented for Gaea and PPAN only; interactive development (`salloc`, Open OnDemand, Jupyter kernel dir, devel nodes, `tmux` replacing `screen`); and an explicit "what the documentation does not cover" list — debuggers/profilers (RDHPCS names Gaea only), job arrays, build systems, and node-local temp (`$TMPDIR` is documented only for PPAN) — so the writer asks the help system instead of inventing.

- [ ] **Step 7: Run test to verify it passes**

Run: `python3 -m unittest tests.test_rdhpcs_consistency -v`
Expected: `PASS`. If `test_machine_qos_facts_match_slurm` fails, the Hercules QOS table used the shared-policy column names (`Max walltime` / `Billing TRES`) instead of MSU's own (`Maximum Wall Clock` / `Billing TRES Factor`) — rename the headers back.

- [ ] **Step 8: Validate the skill**

Run: `python3 tools/validate_skills.py skills/hpc-skills/rdhpcs-orion --profile all --no-color --format text`
Expected: exit 0, zero `error` findings.

- [ ] **Step 9: Commit**

```bash
git add skills/hpc-skills/rdhpcs-orion tests/test_rdhpcs_consistency.py
git commit -m "Add rdhpcs-orion skill

Orion's MSU-administered accounts, 10 GB home quota, and 5-minute default
wall clock are the three things an agent gets wrong without them. MSU
publishes its own per-QOS table in nodes rather than cores, so the skill
quotes MSU's column names and flags where the caps differ from the fleet
policy, with sacctmgr offered for the live wall clocks.

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 5: `rdhpcs-hercules`

**Files:**
- Create: `skills/hpc-skills/rdhpcs-hercules/SKILL.md`
- Create: `skills/hpc-skills/rdhpcs-hercules/references/job-scripts.md`
- Create: `skills/hpc-skills/rdhpcs-hercules/references/storage.md`
- Create: `skills/hpc-skills/rdhpcs-hercules/references/programming-env.md`
- Modify: `tests/test_rdhpcs_consistency.py`

**Interfaces:**
- Consumes: `MACHINE_SKILLS`, the Task 4 content model (Hercules shares MSU storage and account rules but differs in node shape).

- [ ] **Step 1: Declare the expected skill in the test**

```python
MACHINE_SKILLS: dict[str, str] = {
    "rdhpcs-hera": "hera",
    "rdhpcs-ursa": "ursa",
    "rdhpcs-orion": "orion",
    "rdhpcs-hercules": "hercules",
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_rdhpcs_consistency.MachineSkillConsistencyTests.test_expected_machine_skills_exist -v`
Expected: failures and errors naming `rdhpcs-hercules` (missing `SKILL.md`).

- [ ] **Step 3: Write `SKILL.md`**

Create `skills/hpc-skills/rdhpcs-hercules/SKILL.md`. Frontmatter:

```markdown
---
name: rdhpcs-hercules
description: >
  NOAA RDHPCS Hercules system at the Mississippi State University HPC2
  collaboratory. Use when writing Slurm job scripts for Hercules, choosing the
  hercules or service partition, requesting 80-core Xeon Platinum 8380 nodes with
  512 GB of memory, placing data on the work or work2 Lustre scratch filesystems
  or the 10 GB NFS home, using MSU-HPC accounts that are separate from RDHPCS
  accounts, setting up cron on hercules-login-1, or discovering LMOD compiler
  and MPI modules on Hercules.
compatibility: Script-authoring skill; no login required. Hercules is hosted at Mississippi State University, so access uses MSU credentials and Duo rather than the NOAA RDHPCS bastions.
metadata:
  version: "1.0"
  system: hercules
  facility: rdhpcs
  scheduler: slurm
  source: https://docs.rdhpcs.noaa.gov/systems/MSU-HPC_user_guide.html
  as_of: "2026-10-28"
allowed-tools: Read Write Grep Glob
---
```

Body — same section order as Task 4 Step 3, with these **Hercules-specific** values and no Orion numbers carried over:

1. **`# Hercules — MSU-HPC (NOAA RDHPCS)`** — the newer MSU HPC2 system. Slurm with LMOD; **Rocky Linux 9.x** (the MSU guide names the 9.x series, not a point release).
2. **`## System Overview`** table: Dell EMC PowerEdge C6520 nodes; Intel Xeon Platinum 8380, 40 cores × 2 sockets = **80 cores per node** at 2.30 GHz; **512 nodes**; **40,960 cores**; **512 GB per node**, so there is **no bigmem tier**; Mellanox NDR-200 InfiniBand; 4 login nodes, 4 data transfer nodes, 4 development nodes.
3. **`## Critical Requirements`** — `-A` mandatory; always set `-t` (5-minute default); `--ntasks-per-node` up to 80; do not request `bigmem`, it does not exist here.
4. **`## Partitions`** table: `hercules` (batch, windfall, debug, urgent, novel; 80 cores and 512 GB per node) and `service` (batch, windfall, debug, urgent; maximum 1 core, 24 hour limit, external network and HPSS).
5. **`## QOS`** — quote MSU's per-QOS table with MSU's own column names, exactly as Task 4 Step 5, but with the **Hercules** node limits: `batch` 1–500 nodes (the guide gives no per-system split for `batch`), `urgent`/`debug`/`windfall` 1–**250**, `novel` from **251** to the largest partition, `service` the 24-hour `windfall` exception. Same wall clocks (8 h, 30 min debug), same Billing TRES factors (1.0 / 2.0 / 1.25 / 0.0 / 1.0), same 400 pending/running and 20 age-priority caps. State that Hercules has no `long`, `gpu`, or `gpuwf`, and offer `sacctmgr show qos format=Name,MaxWall`.
6. **`## Minimal Job Script`** — `-p hercules`, `--ntasks-per-node=80`, `-t` set, output under `/work/<project>/<user>`.
7. **`## Storage`** — state the MSU filesystems in full (they are shared with Orion, but the skill must stand alone): `/home/First.Last` NFS 10 GB backed up nightly; `work` DDN Lustre 9 PB scratch not backed up; `work2` DDN Lustre 18 PB with hot-pool SSD cache not backed up; HPSS via HSMS. No `$TMPDIR` row — RDHPCS documents that variable only for PPAN.
8. **`## Accounts and Projects`** — MSU HPC2 administered, independent of RDHPCS; managers need an active MSU account; renewal required.
9. **`## Cron and Recurring Work`** — the MSU guide lists `cron` services as "Available on hercules-login-1 (VERIFY)": the **(VERIFY) marker is literally in the published page**, so the skill must reproduce it and tell the user to confirm before scheduling, not silently drop it. `scrontab` is not documented for Hercules; `at` only on `login1`.
10. **`## Common Gotchas`** — carrying Orion's 40-core node shape into a Hercules script (Hercules is 80 cores); requesting `bigmem`, which does not exist here; omitting `-t` (5-minute kill); the 10 GB home quota; compiling on a login node; MSU versus RDHPCS account naming; cron on the wrong login node; copying an `/apps` path or module name from Orion, since Hercules is spack-built with `<package-hash>` directory names and different module names; expecting FairShare to carry between the two systems.
11. **`## Additional Resources`** — three `references/` links plus the MSU-HPC guide URL.

- [ ] **Step 4: Write the three `references/` files**

Create `references/job-scripts.md` (~200 lines), `references/storage.md` (~150 lines), and `references/programming-env.md` (~180 lines) with the same section sets specified in Task 4 Steps 4–6, changing every node-shape value to the Hercules facts (80 cores per node, 512 GB, no bigmem partition, NDR-200, 512 nodes, 4 devel nodes, `hercules-dtn-{1..4}.hpc.msstate.edu` and the round-robin `hercules-dtn`, Globus endpoint `msuhpc2-Hercules`, `shpcrpt -c hercules`) and keeping the `service` partition rules. Restate the MSU storage and account rules in full rather than pointing at the Orion skill. Hercules-specific material to include: spack-built `/apps/spack/<package-hash>` layout with module and directory names that differ from Orion; MSU installs older versions on request via a justified help ticket; the Hercules-only MPI buffer-size crash (`I_MPI_SHM_HEAP_VSIZE`, default 8192 MB against 512 GB nodes) and the Hercules-only advice to drop `--ntasks-per-node` for large domains because nodes have so much memory; the WRF/netCDF module-variable example MSU writes for Hercules (`NETCDF_C_ROOT`, `NETCDF_FORTRAN_ROOT`, `PARALLEL_NETCDF_ROOT`/`PNETCDF`). Do not carry the Task 4 inventions: no `$TMPDIR`, no scrontab, no Podman, no invented `sacct` columns.

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m unittest tests.test_rdhpcs_consistency -v`
Expected: `PASS`.

- [ ] **Step 6: Validate the skill**

Run: `python3 tools/validate_skills.py skills/hpc-skills/rdhpcs-hercules --profile all --no-color --format text`
Expected: exit 0, zero `error` findings.

- [ ] **Step 7: Commit**

```bash
git add skills/hpc-skills/rdhpcs-hercules tests/test_rdhpcs_consistency.py
git commit -m "Add rdhpcs-hercules skill

Hercules differs from Orion in node shape (80 cores, 512 GB, no bigmem
tier) and interconnect, so its skill states those values instead of
sharing one MSU document.

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 6: `rdhpcs-gaea`

**Files:**
- Create: `skills/hpc-skills/rdhpcs-gaea/SKILL.md`
- Create: `skills/hpc-skills/rdhpcs-gaea/references/job-scripts.md`
- Create: `skills/hpc-skills/rdhpcs-gaea/references/storage.md`
- Create: `skills/hpc-skills/rdhpcs-gaea/references/programming-env.md`
- Modify: `tests/test_rdhpcs_consistency.py`

**Interfaces:**
- Consumes: `MACHINE_SKILLS`, the Task 2 skeleton, the Task 4 "QOS names only" pattern.

- [ ] **Step 1: Declare the expected skill in the test**

```python
MACHINE_SKILLS: dict[str, str] = {
    "rdhpcs-hera": "hera",
    "rdhpcs-ursa": "ursa",
    "rdhpcs-orion": "orion",
    "rdhpcs-hercules": "hercules",
    "rdhpcs-gaea": "gaea",
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_rdhpcs_consistency.MachineSkillConsistencyTests.test_expected_machine_skills_exist -v`
Expected: failures and errors naming `rdhpcs-gaea` (missing `SKILL.md`).

- [ ] **Step 3: Write `SKILL.md`**

Create `skills/hpc-skills/rdhpcs-gaea/SKILL.md`. Frontmatter:

```markdown
---
name: rdhpcs-gaea
description: >-
  NOAA RDHPCS Gaea system at Oak Ridge National Laboratory's NCCS, a federated
  Slurm cluster with HPE Cray EX 3000 compute and the Cray Programming
  Environment. Use when writing Slurm jobs for Gaea, selecting the c5, c6, c7,
  or es cluster with -M or --clusters, choosing the batch or novel partition or
  the normal, debug, urgent, windfall, dtn, ppan, hpss, or interactive QOS,
  targeting C5, C6, or C7 AMD EPYC node generations, using the dtn_f5_f6
  partition with --constraint=f5 or --constraint=f6, placing data on the
  cluster-specific /gpfs/f5, /gpfs/f6, or /gpfs/f7 filesystems or the
  /ncrc/home[12] and /ncrc/proj NFS areas, or compiling with the cc, CC, and
  ftn Cray wrappers and PrgEnv modules.
compatibility: Script-authoring skill; no login required. Submitting jobs requires CAC/PIV or YubiKey access through a Gaea bastion and a signed master certificate.
metadata:
  version: "1.0"
  system: gaea
  facility: rdhpcs
  scheduler: slurm
  source: https://docs.rdhpcs.noaa.gov/systems/gaea_user_guide.html
  as_of: "2026-10-28"
allowed-tools: Read Write Grep Glob
---
```

Body sections, in order, with exactly these facts:

1. **`# Gaea — NOAA RDHPCS at ORNL NCCS`** — a DOE/NOAA collaborative system at Oak Ridge, the largest RDHPCS machine: three HPE Cray EX 3000 cabinets (C5/C6/C7) with aggregate peak **more than 54 petaflops**, three IBM Spectrum Scale (GPFS) file systems totalling **over 220 PB** (F5 75 PB, F6 75 PB, F7 70 PB), HPE Slingshot interconnect.
2. **`## System Overview`** table, one row per generation:

   | Cluster | Nodes | CPU | Cores per node | Memory per node | NUMA | ISA | Peak | Interconnect |
   |---------|-------|-----|----------------|-----------------|------|-----|------|--------------|
   | C5 | 1,920 | 2× AMD EPYC 7H12 2.6 GHz 64-core | 128 | 256 GB | 8 | AVX-2 | 10.22 PF | 2× Slingshot 100 Gbps |
   | C6 | 2,048 | 2× AMD EPYC 9654 2.4 GHz 96-core | 192 | 384 GB | 8 | AVX-512 | 15.1 PF | 1× Slingshot 200 Gbps |
   | C7 | 1,208 | 2× AMD EPYC 9965 2.0 GHz 192-core (Zen 5c Turin) | 384 | 768 GB | 4 | AVX-512 | 29 PF | 1× Slingshot 200 Gbps |

   Then state plainly that **login nodes are a separate set with different core counts and memory** (`gaea5[1-6]` 128 cores / 512 GB, `gaea6[1-6]` 192 cores / 512 GB, `gaea7[1-6]` **320 cores** / 1.6 TB) and must never be quoted as compute-node specs. OS: Cray OS 3.1.0-28 (SLES 15.5) on C5 and C6, **RHEL 9.8 "Plow"** on C7; discover versions with `cat /opt/cray/etc/release/cos-base` and `lsb_release -a`.
3. **`## Critical Requirements`** — `-A <projectID>` mandatory; **`-M <cluster>` selects the Slurm cluster** because Gaea is a Slurm **federation** of `c5`, `c6`, `c7`, and `es`, and scheduler commands default to the cluster you are standing on; the GPFS area must match the cluster (`/gpfs/f5` for C5, `/gpfs/f6` for C6, `/gpfs/f7` for C7).
4. **`## Slurm Federation`**:

```bash
squeue --clusters=c6            # or -M c6
export SLURM_CLUSTERS=c5,es     # change the default for a session
#SBATCH -M c5                   # script form
scontrol --cluster c6 show partition   # authoritative partition list per cluster
```

   Clusters: `c5`, `c6`, `c7` are compute; `es` holds all login and data transfer nodes. **Documented partitions** (they are partitions, not QOS): on C5 and C6, `batch` (1–512 nodes, default 12:00:00, max 16:00:00) and `novel` (513 nodes up, enabled only right after system maintenance — "alert the help desk" if it is inactive); on `es`, `eslogin_c5`, `eslogin_c6`, `dtn_f5_f6`, `cron_c5`, `cron_c6` (all 1 node, 12:00:00 default / 16:00:00 max). **No C7 partitions are documented — say so and discover with `scontrol --cluster c7 show partition` rather than inventing names.** `--constraint=f5` or `--constraint=f6` on `dtn_f5_f6` selects which GPFS file system the DTN mounts (auto-selected from your origin cluster C5/C6/C7).
5. **`## QOS`** — Gaea's documented QOS are `normal` (default), `debug` (highest priority, 1 h max), `urgent`, `windfall` (no charge, no fair-share effect, lowest priority), `dtn`, `ppan`, `hpss` (the last two paused during PPAN/HPSS maintenance windows), plus `interactive` which Slurm adds automatically to `salloc` jobs (**one interactive job per user**). Restate Gaea's own table with its own column names (`QOS | Priority Factor | Usage Factor | Max Walltime | Clusters | Description`) — normal .85/1.00/16 h on C5,C6,ES; debug 1.00/1.00/1 h; urgent .95/1.00/16 h; windfall .00/.00/16 h; dtn, ppan, hpss .00/1.00/16 h on ES. The fleet policy behind it: two 50/50 allocations, `urgent` (and `novel`-partition jobs needing >25% of system cores, run in the 8-hour window right after preventative maintenance) against `batch`/`debug`/`interactive`; largest job ≤25% of cores except on `novel`; job segments ≤12 h; windfall via `sbatch --qos=windfall`. Discover with `sacctmgr show qos format=name,priority,usagefactor,maxwall`, `sprio`, `sshare`. Do **not** restate the Hera/Ursa wall-time numbers as Gaea's, and do not use the `Max walltime` or `Billing TRES` column headers (the consistency test's shared-policy shape).
6. **`## Minimal Job Script`**:

```bash
#!/bin/bash
#SBATCH -M c6
#SBATCH -A myproject
#SBATCH -J RunSim123
#SBATCH -p batch
#SBATCH -N 16
#SBATCH --ntasks-per-node=192
#SBATCH -t 4:00:00
#SBATCH -o %x-%j.out

module load PrgEnv-gnu
cd /gpfs/f6/${SLURM_ACCOUNT}/scratch/${USER}/Run.456
srun ./my_app
```

   No `-q` line: `normal` is the default QOS. Windfall work adds `#SBATCH --qos=windfall`.

7. **`## Storage`** table:

   | Area | Path | Permissions | Quota | Backed up | Purged | Available from |
   |------|------|-------------|-------|-----------|--------|----------------|
   | Member work | `/gpfs/f5/<projID>/scratch/<userID>` | user-set | N/A | No | No | C5 only |
   | Project work | `/gpfs/f5/<projID>/proj-shared` | 770 | N/A | No | No | C5 only |
   | World work | `/gpfs/f5/<projID>/world-shared` | 775 | N/A | No | No | C5 only |

   State that the same three areas exist on `/gpfs/f6` (C6 only) and `/gpfs/f7` (C7 only); home is NFS at `/ncrc/home[12]/<userID>` (**50 GB**, backed up with hourly/daily snapshots, never purged, available on compute nodes) with a 100 GB `/ncrc/proj/<projID>` project home; **there is no `/nobackup` area on Gaea** — scratch *is* the non-persistent area. All extensive I/O, large local copies, and every off-Gaea transfer run on DTNs (`dtn[50-79]` mount F5, `dtn[01-09]` mount F6, both mount `$HOME`). Check usage with `quota -Qs`; F5 has transparent lz4 compression (files idle >168 h), F6 does not; decompress one file with `mmchattr --compression no -I yes <file>`.
8. **`## Programming Environment`** — Cray CPE: `module load PrgEnv-aocc` / `PrgEnv-cray` / `PrgEnv-gnu` / `PrgEnv-intel` / `PrgEnv-nvhpc`, `module swap`, and the `cc`, `CC`, and `ftn` wrappers (CCE also exposes `craycc`/`craycxx`/`crayftn`) that link Cray MPICH automatically; add `-craype-verbose` to see include/link lines. **CPE reaches end of support at version 26.03, and C7 no longer loads CPE by default** — the default environment is whatever is active at login (the guide suggests a `load_cpe` alias for legacy workflows). Discover with `module avail` and `module -t list`.
9. **`## Common Gotchas`** — running `squeue` and seeing nothing because you are on the wrong federation cluster; writing to `/gpfs/f6` from a C5 job; omitting `-M`; landing on a DTN without the needed `--constraint` so the file system is not mounted; quoting login-node memory as compute memory; `novel`-partition jobs when the partition is not enabled after maintenance (contact the help desk); building on a login node; treating GPFS scratch as backup; **never appending `/bin/bash` to `salloc`** (it starts the allocation on the login node); `--threads-per-core=2` must be requested in the `sbatch`/`salloc` as well as `srun`; `-S <cores>` reserves cores per node that the application cannot use; no two jobs should touch the same files (hard/soft links can lock up the MDS); no conda/spack environments on GPFS — keep them in `/ncrc/home[12]/$USER`, `/ncrc/proj`, or request a `/usw` location; no development work (especially git) on F5; transfers larger than 2 TB to GFDL archive are slow — use Globus.
10. **`## Additional Resources`** — three `references/` links plus the Gaea guide URL.

- [ ] **Step 4: Write `references/job-scripts.md`**

Create `skills/hpc-skills/rdhpcs-gaea/references/job-scripts.md` (~230 lines) titled `# Gaea Job Scripts Reference`. Sections: directive table including `-M`, `-p`, `-q`, `--constraint`, `-N`, `-t`, `-S`, `--threads-per-core`, `--signal`, `--reservation`, and per-cluster cores (128/192/384); C5 MPI job (128 tasks/node); C6 MPI job (192 tasks/node); C7 job (384 tasks/node); hybrid MPI+OpenMP using the guide's own `srun -N 2 -n 4 --ntasks-per-node=2 ./a.out` form with `--cpu-bind=threads` (the default) and `--threads-per-core` (the guide documents **no** `OMP_PROC_BIND`/`OMP_PLACES` examples — do not invent them); `debug`-QOS single-node job; `novel`-partition job with the post-maintenance/"alert the help desk" note restated; DTN data-movement job on `es` / `dtn_f5_f6` with `--constraint=f5`; interactive `salloc` (with the no-`/bin/bash` warning); `srun` MPMD example only if `slurm/overview.html` documents the syntax — otherwise omit it. Monitoring: `squeue -l -u $USER`, `scontrol show job`, `sacct -a -X`, `sacct -j 12345 -S 2022-07-01T13:00:00 -o "jobid%5,jobname%25,nodelist%20" -X`, `scontrol hold/release/update NumNodes=`, `scancel -s SIG`.

- [ ] **Step 5: Write `references/storage.md`**

Create `skills/hpc-skills/rdhpcs-gaea/references/storage.md` (~170 lines) titled `# Gaea Storage Reference`. Sections: the F5/F6/F7 area table (member `scratch`, `proj-shared` 770, `world-shared` 775) with the cluster-availability restriction; NFS `/ncrc/home[12]` (50 GB, backed up, not purged) and `/ncrc/proj` (100 GB); `quota -Qs` sample output; GPFS compression on F5 (lz4, idle >168 h, exclusions `/.SpaceMan/`, `/fs_audit_log/`, `/.snapshots/`, `/.msgq/`; `mmchattr --compression no -I yes` to decompress; no direct ratio command — compare `ls` vs `du`); the guide's performance tips and known issues (MDS lockup from shared files, F5 hangs/slow reads tied to compression, F5 not backed up); DTN data movement (`dtn_f5_f6`, `--constraint`) and the firewall-exception request process plus Globus for large/off-site transfers; the "not backed up and not purged" caution that makes GPFS scratch neither durable nor safe to abandon.

- [ ] **Step 6: Write `references/programming-env.md`**

Create `skills/hpc-skills/rdhpcs-gaea/references/programming-env.md` (~200 lines) titled `# Gaea Programming Environment Reference`. Sections: Lmod (`module -t list/avail/help/show/spider/load/use/unuse/purge/reset/update`; `avail` only shows dependency-compatible modules, `spider` searches the whole hierarchy); the five `PrgEnv-*` families with their compiler names from the guide table (aocc: `cc`→clang, `CC`→clang++, `ftn`→flang; cce: `craycc`/`craycxx`/`crayftn`; gcc-native: `gcc`/`g++`/`gfortran`; intel: `icx`/`icpx`/`ifort`; nvhpc: `nvc`/`nvc++`/`nvfortran` — NVHPC deprecated since 24.11 in favour of NVIDIA); the rule that MPI builds go through `cc`/`CC`/`ftn` rather than calling `gcc` or `ifort` directly; `cray-mpich` and the module-swap-does-not-change-runtime-libraries trap; dynamic linking (order RPATH → `LD_LIBRARY_PATH` → `/etc/ld.so.conf`, `/opt/cray/pe/lib64` always searched, fix mismatches with `-Wl,-rpath,<path>` or prepending `${CRAY_LD_LIBRARY_PATH}`); CPE EOL at 26.03 and C7's no-default-CPE behaviour with the `load_cpe` alias; launching with `srun`; debugging with Linaro DDT, GDB, GDB4HPC, Valgrind4hpc; profiling with HPE Performance Analysis Tools; software-support scope (only `/opt` and `/sw` modules are RDHPCS-supported; user stacks in `/ncrc/home[12]`, `/usw`, `/ncrc/proj` are self-supported); pointers to the guide's known-issues and open-issues pages.

- [ ] **Step 7: Run test to verify it passes**

Run: `python3 -m unittest tests.test_rdhpcs_consistency -v`
Expected: `PASS`.

- [ ] **Step 8: Validate the skill**

Run: `python3 tools/validate_skills.py skills/hpc-skills/rdhpcs-gaea --profile all --no-color --format text`
Expected: exit 0, zero `error` findings.

- [ ] **Step 9: Commit**

Global constraint: `README.md` (skill tree, auto-derived by `tools/repo_inventory.py`) and `skills/hpc-skills/ATTRIBUTION.md` must be updated in the *same* commit that adds the skill directory.

```bash
git add skills/hpc-skills/rdhpcs-gaea tests/test_rdhpcs_consistency.py README.md skills/hpc-skills/ATTRIBUTION.md
git commit -m "Add rdhpcs-gaea skill

Gaea's Slurm federation (-M c5/c6/c7/es) and cluster-specific GPFS areas
are the two things that silently break a ported job script, so the skill
leads with them and keeps login-node memory separate from compute memory.

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 7: `rdhpcs-ppan` (slim tier)

**Files:**
- Create: `skills/hpc-skills/rdhpcs-ppan/SKILL.md`
- Create: `skills/hpc-skills/rdhpcs-ppan/references/storage.md`
- Modify: `tests/test_rdhpcs_consistency.py`

**Interfaces:**
- Consumes: `MACHINE_SKILLS`, `qos_table()`.
- Produces: the slim-tier precedent — `SKILL.md` plus only the `references/` files the machine actually has enough distinct material for (spec §4).

- [ ] **Step 1: Declare the expected skill in the test**

```python
MACHINE_SKILLS: dict[str, str] = {
    "rdhpcs-hera": "hera",
    "rdhpcs-ursa": "ursa",
    "rdhpcs-orion": "orion",
    "rdhpcs-hercules": "hercules",
    "rdhpcs-gaea": "gaea",
    "rdhpcs-ppan": "ppan",
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_rdhpcs_consistency.MachineSkillConsistencyTests.test_expected_machine_skills_exist -v`
Expected: failures and errors naming `rdhpcs-ppan` (missing `SKILL.md`).

- [ ] **Step 3: Write `SKILL.md`**

Create `skills/hpc-skills/rdhpcs-ppan/SKILL.md`. Frontmatter:

```markdown
---
name: rdhpcs-ppan
description: >-
  NOAA RDHPCS PPAN (Pan) post-processing and analysis cluster at GFDL in
  Princeton. Use when writing Slurm job scripts for PPAN, choosing the batch,
  stage, workflow, dask, hpetest, or gpu partition, targeting the an* analysis
  hosts or pp* post-processing hosts across mixed Xeon generations, running
  post-processing for a Gaea model run, working with the tape-backed /archive
  and CXFS /work filesystems, using /vftmp, $TMPDIR, /ptmp, /nbhome, or /net
  storage, checking quotas with homeuse, quotause, or archrpt, recalling tape
  files with dmget, or transferring files with gcp.
compatibility: Script-authoring skill; no login required. Access is through GFDL credentials and the RDHPCS bastion with CAC or YubiKey, and typically accompanies a Gaea allocation.
metadata:
  version: "1.0"
  system: ppan
  facility: rdhpcs
  scheduler: slurm
  source: https://docs.rdhpcs.noaa.gov/systems/ppan_user_guide.html
  as_of: "2026-10-28"
allowed-tools: Read Write Grep Glob
---
```

Body sections with exactly these facts:

1. **`# PPAN — NOAA RDHPCS at GFDL`** — "Post Processing and Analysis (PPAN)" (also called **Pan**), a small cluster of **over 130 Dell servers at the Geophysical Fluid Dynamics Laboratory (GFDL) in Princeton, NJ**, scheduled by Slurm. About **20 analysis hosts** (`an*`) for interactive use and about **100 post-processing hosts** (`pp*`, e.g. `pp006`, `pp317`). It supports GFDL's science community by analyzing and interpreting models generated on other HPC systems — **Slurm lets models running on Gaea submit post-processing jobs here** — and hosts software packages including MATLAB and Python/R stacks.
2. **`## System Overview`** — multiple petabytes of disk plus **access to nearly 200 PB of archive storage**. The overview blurb says "Sandy Bridge to Ice Lake, 48–512 GB", but the host tables are the authority: analysis hosts run **nehalem/westmere/sandybridge/broadwell/skylake/icelake/Emerald Rapids** (101 GB up to **4,328 GB** on `an208`–`an212`); post-processing hosts are 8–24 CPUs at 51–540 GB. CXFS gives the analysis hosts high-performance access to `/archive` and `/work`. Slurm is used from any analysis host; login to analysis auto-runs `module load slurm`.
3. **`## What PPAN Is For`** — interactive analysis and post-processing of model output; a Gaea workflow commonly ends with a PPAN job. Login: `ssh` with CAC or YubiKey; from GFDL workstations `setup-CAC` enables further logins without re-auth, and YubiKey users run `ssh analysis`.
4. **`## Critical Requirements`** — set `-t`; write model output to `/work` (or archive it), never `/home` (10 GB quota); pin host generations deliberately — **the guide documents partitions and per-host AVX levels, not `--constraint`** — because pp hosts range from no-AVX 8-core boxes to AVX-512 24-core boxes; always `module load <module>/<version>` with the version in batch scripts (fleet modules guidance: silent default-version changes break reproducibility).
5. **`## Partitions`** — from the guide's post-processing host table: `workflow` (`pp[008-010]`), `hpetest` (`pp[013-014]`), `dask` (`pp[017-026]`), `batch/stage` (the bulk — `pp[027-066,068,072-074]`, `pp[101,104,105]`, `pp[200-212]`, `pp[300-343]`), and `gpu` (`pp[400-401]`). The guide gives no wall-time/QOS table for PPAN; use the fleet discovery commands:

   ```bash
   sbatch-limits          # fleet tool: limits + permitted partition/QOS combinations
   sinfo                  # live partition/node state
   sacctmgr show qos format=Name,MaxWall
   ```

   Do not create a table with `Max walltime` or `Billing TRES` headers, and do not assume Hera/Ursa QOS names. Local queue views: `qa`/`qi`/`qr`/`qc`/`qj <jobid>`/`qn an|pp`.
6. **`## Minimal Job Script`** — a post-processing script using `-p batch`, `-N 1`, `-t`, output under `/work/<project>/<user>`, and a comment noting host generations differ (pick a partition/AVX class that fits).
7. **`## Storage`** table listing `/home` (backed up **daily**, 10 GB), `/nbhome` (backed up **weekly** — "no-backup" is the name, not the policy; 10 GB), `/archive` (GFDL **tape** archive via CXFS; read/write on the analysis cluster, read-only on workstations; ~200 PB), `/work` (large long-term scratch, not backed up, read-only on workstations), `/vftmp` + `$TMPDIR` (node-local fast scratch, 8–44 TB, not backed up), `/ptmp` (staging for FRE post-processing, not backed up), `/net`, `/net2`, `/net3` (GFDL workstation filesystems ≥100 GB; `/net` backed up, `/net2`//`/net3` not; **not mounted on post-processing nodes** — use `gcp`). Quota commands: `homeuse` (not `quota -vs`) for `/home`+`/nbhome`, `quotause` for `/work`, `archrpt -s` / `archrpt -r <group>` for archive allocations.
8. **`## Archive`** — `/archive` behaves like a filesystem but data lives on tape until recalled: `dmget <files>`, `dmwho`, `dmls -l`; copy to `/vftmp` before heavy use; **large files only** — tar/cpio small files together; `dmlocate <pattern>` searches a daily-updated filename database; allocations are set by the GFDL director/group leaders and enforced administratively.
9. **`## Common Gotchas`** — assuming a uniform CPU generation across `pp*` hosts; using `/home` for model output (10 GB); treating `/nbhome` as unbacked-up (it is weekly) or `/vftmp`//`/work` as durable; skipping `archrpt` before a large archive write; opening many tape-resident files without `dmget` first; expecting RDHPCS fleet QOS names on a GFDL cluster; the guide's own Slurm gotchas: `-o` pointing at a directory makes the job fail immediately with `NonZeroExitCode`; without `-D dir` the job runs in the submission directory and falls back to `/tmp` if that path is absent on the execution host; output appears in the logfile only after each line completes; scripts not ending in a newline lose their last line.
10. **`## Additional Resources`** — link to `references/storage.md`, plus the PPAN guide URL.

- [ ] **Step 4: Write `references/storage.md`**

Create `skills/hpc-skills/rdhpcs-ppan/references/storage.md` (~150 lines) titled `# PPAN Storage Reference`. Sections: filesystem table for all nine paths with purpose, backup cadence, and quota command; the `/home` versus `/nbhome` daily-vs-weekly distinction and the `homeuse`/`homerpt` commands; `/archive` tape behavior — `dmget`/`dmwho`/`dmls`, `dmlocate`, the large-files-only/tar convention, `archrpt` group/user allocations enforced administratively; mount polarity table (analysis hosts vs GFDL workstations vs post-processing nodes) and `gcp` for `/net[23]` access from analysis sessions (`module load gcp`; not mounted on pp nodes at all); `/vftmp` sizes (8–37 TB analysis, mostly 8 TB pp, "bigvftmp" 27/44 TB), `$TMPDIR` = `/vftmp/<user>/pbs<jobid>` in batch and `pid<pid>` interactively, removed at session end; `/work` (`quotause`) and `/ptmp` (FRE staging) cautions.

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m unittest tests.test_rdhpcs_consistency -v`
Expected: `PASS`.

- [ ] **Step 6: Validate the skill**

Run: `python3 tools/validate_skills.py skills/hpc-skills/rdhpcs-ppan --profile all --no-color --format text`
Expected: exit 0, zero `error` findings.

- [ ] **Step 7: Commit**

```bash
git add skills/hpc-skills/rdhpcs-ppan tests/test_rdhpcs_consistency.py
git commit -m "Add rdhpcs-ppan skill

PPAN is GFDL's post-processing tier: mixed Intel generations, CXFS to
/archive and /work, and archrpt for quotas. Slim tier, so it ships one
reference file instead of three.

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 8: `rdhpcs-mercury` (slim tier)

**Files:**
- Create: `skills/hpc-skills/rdhpcs-mercury/SKILL.md`
- Modify: `tests/test_rdhpcs_consistency.py`

**Interfaces:**
- Consumes: `MACHINE_SKILLS`.

- [ ] **Step 1: Declare the expected skill in the test**

```python
MACHINE_SKILLS: dict[str, str] = {
    "rdhpcs-hera": "hera",
    "rdhpcs-ursa": "ursa",
    "rdhpcs-orion": "orion",
    "rdhpcs-hercules": "hercules",
    "rdhpcs-gaea": "gaea",
    "rdhpcs-ppan": "ppan",
    "rdhpcs-mercury": "mercury",
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_rdhpcs_consistency.MachineSkillConsistencyTests.test_expected_machine_skills_exist -v`
Expected: failures and errors naming `rdhpcs-mercury` (missing `SKILL.md`).

- [ ] **Step 3: Write `SKILL.md`**

Create `skills/hpc-skills/rdhpcs-mercury/SKILL.md` (no `references/` directory — the whole skill fits in one file). Frontmatter:

```markdown
---
name: rdhpcs-mercury
description: >-
  NOAA RDHPCS Mercury data-transfer system for moving data to and from
  collaborators. Use when planning a transfer to or from RDHPCS, deciding
  between Mercury trusted and untrusted data transfer nodes, placing files in
  /collab2/data or /collab2/data_untrusted, working out why /home is missing on
  a DTN, using Mercury CRON or HPSS access, or reaching Mercury through an
  RDHPCS bastion with a CAC/PIV or YubiKey certificate.
compatibility: Script-authoring skill; no login required. Access is through the mercury-mfa bastions with CAC/PIV or YubiKey credentials, and is available to all RDHPCS users.
metadata:
  version: "1.0"
  system: mercury
  facility: rdhpcs
  scheduler: none
  source: https://docs.rdhpcs.noaa.gov/systems/mercury_user_guide.html
  as_of: "2026-10-28"
allowed-tools: Read Write Grep Glob
---
```

Body sections with exactly these facts:

1. **`# Mercury — NOAA RDHPCS Data Transfer`** — "primarily a data transfer/collaboration system that is available to all RDHPCS": a collaborative system where data can be securely copied to and from any location, by any authorized user, to disseminate R&D data to NOAA's collaborators around the globe. **No compute nodes are available on Mercury.** The system comprises interactive login nodes (front ends), a file system, data transfer nodes, and back-end HPSS storage.
2. **`## System Overview`** table: **4 login nodes**; **dual-socket AMD EPYC Genoa 9654, 2.40 GHz, 96 cores**; trusted Data Transfer Nodes (DTNs) available from trusted (pre-approved) NOAA and non-NOAA sites; Untrusted Data Transfer Nodes (UDTNs) available from anywhere on the internet; back-end HPSS. Login is with CAC or YubiKey credentials through the MFA bastion (`mercury-mfa.princeton.rdhpcs.noaa.gov`, `mercury-mfa.fairmont.rdhpcs.noaa.gov`); the front ends are `mfe[01-04].fairmont.rdhpcs.noaa.gov`.
3. **`## First Login`** — the directories needed for transfers are created automatically on your **first login to a Mercury front end**: `/home/First.Last`, `/collab2/data/First.Last` (trusted data), `/collab2/data_untrusted/First.Last` (untrusted data). Log in at least once before any sharing or UDTN use.
4. **`## Where Files Must Go`** — the visibility table, which is the whole point of the skill:

   | Path | Front ends | Trusted DTNs | UDTNs | Quota | Purge |
   |------|-------------|--------------|----------------|-----|-----|
   | `/home/First.Last` | Yes | **No** | No | 10 GB | not purged, backed up daily |
   | `/collab2/data/First.Last` | Yes | Yes | Yes | 60 TB | files unaccessed 60 days are purged |
   | `/collab2/data_untrusted/First.Last` | Yes | No | Yes, as `/collab2/$USER` | 20 TB | files unaccessed 14 days are purged |

   Pick the path by the peer you are transferring with: data visible to an untrusted collaborator goes in `data_untrusted`, and **the `/home` tree is not accessible from the DTNs at all**. On a UDTN the `data_untrusted` tree is *renamed*: `/collab2/data_untrusted/$USER` appears there as `/collab2/$USER`. `/collab2` is a **Lustre** scratch filesystem (per the RDHPCS storage tables), considered scratch, meant for transient data only, and **not backed up**. Access time means the last time a file was opened for reading or writing; RDHPCS warns it will adopt a more aggressive purge (30 or 15 days) if the filesystem nears capacity, so manage data actively.
5. **`## Transferring Data`** — RDHPCS encourages **Globus Connect Service** over other methods whenever possible; it is available on Mercury, and the Mercury collections are `noaardhpcs#mercury` (trusted) and `noaardhpcs#mercury_untrusted` (anywhere). Globus CLI is available on Mercury with `module load globus-cli`. For a laptop, Globus Connect Personal treats it as a Globus Untrusted Endpoint and transfers suspend/resume with the machine's sleep and reboot; scp/sftp to a DTN uses pre-configured SSH port tunnels. The nodes are `dtn-mercury.fairmont.rdhpcs.noaa.gov` and `udtn-mercury.fairmont.rdhpcs.noaa.gov`. Reaching a fixed external partner may need a firewall access request naming the DTN hostnames/IPs. **Tar many small files into one archive** — transfer performance tracks file-open cost, not bytes, and a few large files beat many small ones.
6. **`## CRON, HPSS, and Software`** — CRON services are available on Mercury for scheduled work; HPSS is accessible (see the NESCC HPSS page). Mercury carries only a **minimal software stack** for compiling and running programs, since it exists for data movement — open a help ticket for anything more.
7. **`## Common Gotchas`** — trying to run a compute job, there are no compute nodes; assuming `/home` exists on a DTN; putting externally visible data in `/collab2/data` when the peer is untrusted, or vice versa; expecting `/collab2/data_untrusted` to appear under that name on a UDTN; treating `/collab2` as archive (scratch, not backed up, purged on access time); transferring huge file counts one by one instead of tarring; expecting a full software stack on a transfer node.
8. **`## Additional Resources`** — Mercury guide URL, the RDHPCS connecting page URL, and the transferring-data page URL.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_rdhpcs_consistency -v`
Expected: `PASS`. `test_reference_links_resolve` passes because the SKILL.md has no `references/` links — confirm by checking the test output shows no failure for `rdhpcs-mercury`.

- [ ] **Step 5: Validate the skill**

Run: `python3 tools/validate_skills.py skills/hpc-skills/rdhpcs-mercury --profile all --no-color --format text`
Expected: exit 0, zero `error` findings.

- [ ] **Step 6: Commit**

```bash
git add skills/hpc-skills/rdhpcs-mercury tests/test_rdhpcs_consistency.py
git commit -m "Add rdhpcs-mercury skill

Mercury has no compute nodes, and its value is the DTN visibility rules
for /home versus /collab2/data versus /collab2/data_untrusted, so the
skill leads with the path table and refuses to present it as a machine
for jobs.

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 9: `rdhpcs-cloud` (slim tier)

**Files:**
- Create: `skills/hpc-skills/rdhpcs-cloud/SKILL.md`
- Modify: `tests/test_rdhpcs_consistency.py`

**Interfaces:**
- Consumes: `MACHINE_SKILLS`.

- [ ] **Step 1: Declare the expected skill in the test**

```python
MACHINE_SKILLS: dict[str, str] = {
    "rdhpcs-hera": "hera",
    "rdhpcs-ursa": "ursa",
    "rdhpcs-orion": "orion",
    "rdhpcs-hercules": "hercules",
    "rdhpcs-gaea": "gaea",
    "rdhpcs-ppan": "ppan",
    "rdhpcs-mercury": "mercury",
    "rdhpcs-cloud": "cloud",
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_rdhpcs_consistency.MachineSkillConsistencyTests.test_expected_machine_skills_exist -v`
Expected: failures and errors naming `rdhpcs-cloud` (missing `SKILL.md`).

- [ ] **Step 3: Write `SKILL.md`**

Create `skills/hpc-skills/rdhpcs-cloud/SKILL.md` (no `references/` directory). Frontmatter:

```markdown
---
name: rdhpcs-cloud
description: >
  NOAA RDHPCS Cloud on-demand clusters and cloud access to on-prem systems.
  Use when requesting an ad-hoc HPC cluster through ACTIVATE, reaching Hera,
  Ursa, Orion, Hercules, or Gaea from the cloud with ParallelWorks, running
  Jupyter or VS Code on a Slurm compute node, choosing Lustre, bucket or block
  blob storage, or a contrib filesystem for a cloud cluster, estimating storage
  cost with the RDHPCS cost calculator, or reviewing cloud usage reports and
  forwarded on-prem quota warnings.
compatibility: Script-authoring skill; no login required. Provisioning requires an approved RDHPCS cloud project and the cloud dashboard sign-in path for your account.
metadata:
  version: "1.0"
  system: cloud
  facility: rdhpcs
  scheduler: slurm
  source: https://docs.rdhpcs.noaa.gov/systems/cloud_user_guide.html
  as_of: "2026-10-28"
allowed-tools: Read Write Grep Glob
---
```

Body sections:

1. **`# RDHPCS Cloud`** — two distinct services: **ad-hoc clusters** provisioned on demand, and **ParallelWorks** remote access to the on-prem RDHPCS systems. Say which one a user wants before writing anything, because the job script differs.
2. **`## Two Ways to Use It`** table: ad-hoc cluster (you request a cluster through ACTIVATE, you own the head node and compute nodes, Slurm runs inside the cluster) versus ParallelWorks (a browser-delivered session that reaches an on-prem system's head node, so the machine rules of Hera, Ursa, Orion, Hercules, or Gaea still apply).
3. **`## Interactive Work`** — with an approved project, Jupyter and VS Code run on a **Slurm compute node**, not the head node. Author the allocation or job so the notebook or server lands on a compute node.
4. **`## Storage`** table: Lustre parallel filesystem; bucket and block blob storage; the `contrib` filesystem for project-managed software and shared data. Note that storage type is chosen at cluster request time, that the RDHPCS cost calculator prices the choices, and that usage reports show consumption after the fact.
5. **`## Quota Warnings`** — quota warning messages from the on-prem systems are forwarded into the cloud environment, so a warning seen in the cloud may describe an on-prem `/home` or scratch quota, not a cloud one. Check which system the message names before acting.
6. **`## Job Scripts`** — Slurm on an ad-hoc cluster uses the same directives as the on-prem systems, but the node shape is whatever the requested cluster provides. The skill must instruct the reader to read the live shape rather than reuse an on-prem number:

   ```bash
   sinfo -N -l
   scontrol show node | head -20
   ```

7. **`## Common Gotchas`** — treating a ParallelWorks session as a separate scheduler when the on-prem machine still governs it; running Jupyter or VS Code on the head node instead of a compute allocation; assuming on-prem node sizes for an ad-hoc cluster; choosing storage without consulting the cost calculator; acting on a forwarded quota warning as though it were a cloud quota.
8. **`## Additional Resources`** — cloud guide URL.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_rdhpcs_consistency -v`
Expected: `PASS`.

- [ ] **Step 5: Validate the skill**

Run: `python3 tools/validate_skills.py skills/hpc-skills/rdhpcs-cloud --profile all --no-color --format text`
Expected: exit 0, zero `error` findings.

- [ ] **Step 6: Commit**

```bash
git add skills/hpc-skills/rdhpcs-cloud tests/test_rdhpcs_consistency.py
git commit -m "Add rdhpcs-cloud skill

Ad-hoc clusters and ParallelWorks access are easy to conflate, so the
skill separates them, keeps node shape discovery on the reader, and
explains that forwarded quota warnings may describe on-prem filesystems.

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 10: Retire the DOE-lab skills and update bookkeeping

Deletions, `ATTRIBUTION.md`, the `README.md` tree line, and the `CONTRIBUTING.md` tier count must land in **one commit** so `make policy` stays green throughout.

**Files:**
- Delete: `skills/hpc-skills/frontier/` (SKILL.md + `references/`)
- Delete: `skills/hpc-skills/aurora/` (SKILL.md + `references/`)
- Delete: `skills/hpc-skills/perlmutter/` (SKILL.md + `references/`)
- Modify: `skills/hpc-skills/ATTRIBUTION.md`
- Modify: `README.md:100`
- Modify: `CONTRIBUTING.md:25` (the tier list counts this subtree's skills)

**Interfaces:**
- Consumes: the eight `rdhpcs-*` directories from Tasks 2–9.
- Produces: the final `hpc-skills/` subtree contents that `build_readme_tree_lines()` enumerates.

- [ ] **Step 1: Confirm nothing links into the deleted directories**

Run:

```bash
grep -rn "hpc-skills/\(frontier\|aurora\|perlmutter\)" --include="*.md" --include="*.py" --include="*.json" . | grep -v "^./docs/superpowers/" | grep -v "tests/test_repo_policy.py"
```

Expected: no output. `docs/superpowers/` may cite them as the thing being replaced, and `tests/test_repo_policy.py` uses `skills/hpc-skills/aurora` only as a synthetic path inside a temp tree — leave both alone.

- [ ] **Step 2: Delete the three skill directories**

```bash
git rm -r skills/hpc-skills/frontier skills/hpc-skills/aurora skills/hpc-skills/perlmutter
```

- [ ] **Step 3: Rewrite `skills/hpc-skills/ATTRIBUTION.md`**

Keep the existing structure and the original authorship/licensing statements for the retained `slurm` and `pbs` skills, and change the coverage so that: the derived-from list names `slurm` and `pbs` only; the `aurora`, `frontier`, and `perlmutter` entries are removed; a new section states that the eight `rdhpcs-*` skills were authored for this repository from the NOAA RDHPCS documentation at `https://docs.rdhpcs.noaa.gov`, listing each skill with its guide URL (Hera, Ursa, MSU-HPC for Orion and Hercules, Gaea, PPAN, Mercury, Cloud); and the machine-facts `as_of` date 2026-10-28 is recorded so a future reader knows what to re-verify. Preserve Matt Baughman's attribution and the Apache-2.0 licensing text exactly as they appear now.

- [ ] **Step 4: Regenerate the README tree line**

`README.md:100` currently reads:

```text
│   ├── hpc-skills/  # aurora, frontier, pbs, perlmutter, slurm (5)
```

Replace it with the line `build_readme_tree_lines()` produces for the new subtree (names are the directories containing a `SKILL.md`, sorted by `casefold`, count in parentheses):

```text
│   ├── hpc-skills/  # pbs, rdhpcs-cloud, rdhpcs-gaea, rdhpcs-hera, rdhpcs-hercules, rdhpcs-mercury, rdhpcs-orion, rdhpcs-ppan, rdhpcs-ursa, slurm (10)
```

If any other line in the `## Repository Structure` code block differs, the policy check will say so — do not hand-edit other lines.

- [ ] **Step 5: Update the CONTRIBUTING tier line**

`CONTRIBUTING.md:25` reads:

```text
- **HPC (5):** `skills/hpc-skills/` for Slurm, PBS, and leadership-computing systems
```

Replace it with:

```text
- **HPC (10):** `skills/hpc-skills/` for Slurm, PBS, and the NOAA RDHPCS systems
  (Hera, Ursa, Orion, Hercules, Gaea, PPAN, Mercury, Cloud)
```

The count is the number of skill directories in the subtree, which the surrounding list
states for every tier, and nothing in `validate_repo_policy.py` checks it — so it is
updated by hand here, not regenerated.

- [ ] **Step 6: Verify the README line matches the generator**

Run:

```bash
python3 -c "
import sys; sys.path.insert(0, 'tools')
from pathlib import Path
from repo_inventory import build_readme_tree_lines
for line in build_readme_tree_lines(Path('.')):
    if 'hpc-skills' in line:
        print(line)
"
```

Expected output: exactly the `hpc-skills/` line written in Step 4, character for character. If it differs, copy the generator's output into `README.md` and re-run.

- [ ] **Step 7: Run the policy check and the full test suite**

Run: `make policy && make test`
Expected: `make policy` exits 0 with no README mismatch; `make test` passes, including `tests/test_rdhpcs_consistency.py` (it runs automatically because `tools/run_tests.py` discovers the `tests` package).

- [ ] **Step 8: Confirm the consistency test still guards**

Run: `python3 -m unittest tests.test_rdhpcs_consistency -v`
Expected: `PASS`, with `test_no_stale_doe_references` now scanning `slurm` plus the eight `rdhpcs-*` directories, and `pbs` still excluded.

- [ ] **Step 9: Commit**

```bash
git add -A skills/hpc-skills README.md CONTRIBUTING.md
git commit -m "Replace DOE-lab hpc-skills with NOAA RDHPCS skills

Removes the aurora, frontier, and perlmutter machine skills now that the
repository targets the NOAA RDHPCS fleet, updates the subtree attribution
to credit the retained slurm and pbs skills and record the RDHPCS docs as
the source for the eight new skills, regenerates the README structure line
so the policy check matches, and updates the CONTRIBUTING tier count.

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 11: Final verification

**Files:**
- Modify: nothing expected. If a check fails, fix the file named by the failure and re-run from Task 1 through here as needed.

- [ ] **Step 1: Validate the whole catalog**

Run: `python3 tools/validate_skills.py --profile all --no-color --format text`
Expected: exit 0, zero `error` findings across all skills. Record any `warning` findings and confirm each is an accepted body-length or dialect warning, not a new problem.

- [ ] **Step 2: Run the full verification target**

Run: `make verify-new-skill`
Expected: all four stages pass — validate, policy, test, lint. If `make lint` exits 127 because `pre-commit` is not installed, say so explicitly in the final report rather than claiming lint passed; then run `python3 -m pre_commit run --all-files` if available, or note it as unverified.

- [ ] **Step 3: Spot-check facts against the docs**

For each of Hera, Ursa, Orion, Hercules, Gaea, PPAN, Mercury, and Cloud, re-fetch the guide URL from `metadata.source` and confirm the partition names, node counts, cores per node, and home quota stated in that skill. Use:

```bash
curl -s https://docs.rdhpcs.noaa.gov/systems/hera_user_guide.html | python3 -c "import sys,html,re;t=sys.stdin.read();t=re.sub(r'<(script|style)[^>]*>.*?</\1>','',t,flags=re.S|re.I);t=re.sub(r'<[^>]+>',' ',t);print(html.unescape(re.sub(r'[ \t]+',' ',t)))" | grep -iE "partition|qos|cores|quota|nodes"
```

Expected: every number in the skill appears in the page, or the skill states a discovery command for it instead. Fix any mismatch in the machine skill; never adjust the `slurm` canonical table to match a machine skill.

- [ ] **Step 4: Confirm the tree is clean and the deliverable is complete**

Run: `git status --short && ls skills/hpc-skills`
Expected: empty `git status` output, and `ls` shows `ATTRIBUTION.md`, `LICENSE`, `pbs`, `rdhpcs-cloud`, `rdhpcs-gaea`, `rdhpcs-hera`, `rdhpcs-hercules`, `rdhpcs-mercury`, `rdhpcs-orion`, `rdhpcs-ppan`, `rdhpcs-ursa`, `slurm`.

Run: `grep -rn "hpc-skills/\(frontier\|aurora\|perlmutter\)" --include="*.md" . | grep -v docs/superpowers/`
Expected: no output — nothing outside the design documents links into the deleted directories.

- [ ] **Step 5: Report**

Summarize: eight skills added, three removed, `slurm` refreshed with the fleet policy, one consistency test added, README and ATTRIBUTION updated, and the verification results with exact commands run. Flag the two known doc hazards (Hera per-node memory not published; the guides' per-QOS "Billable TRes" column contradicts the policies table and was not used) so the reviewer knows they were deliberate.

---

## Self-Review Notes

Spec coverage check against the approved spec:

| Spec section | Plan task |
|--------------|-----------|
| §4 directory layout, §5 naming | Tasks 2–9 (dir == `name`, `rdhpcs-*` prefix), Task 10 (deletions) |
| §6 shared policy in `slurm` | Task 1 |
| §7.1 Hera | Task 2 |
| §7.2 Ursa CPU+GPU | Task 3 |
| §7.3 Orion | Task 4 |
| §7.4 Hercules | Task 5 |
| §7.5 Gaea | Task 6 |
| §7.6 PPAN | Task 7 |
| §7.7 Mercury | Task 8 |
| §7.8 Cloud | Task 9 |
| §8 error handling | the `## Common Gotchas` list in each of Tasks 2–9 |
| §9 non-goals | Global Constraints (no omd, no `scripts/`, `pbs` untouched, no Jet) |
| §10 bookkeeping | Task 10 |
| §11 verification | Tasks 1–9 test/validate steps, Task 10 Step 6, Task 11 |
| §12 risks and provenance | `metadata.source` + `metadata.as_of` on every skill; Task 11 Step 3 |

Every spec bullet maps to a task step. No task depends on a value the plan does not state.

