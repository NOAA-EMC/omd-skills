# EE2 Standards Skill — Design

**Date:** 2026-11-02
**Scope:** `skills/omd-standards/ee2-standards/`
**Upstream:** NCO-HPC `nws-hpc-standards`, ee-docs **11.0.0**
(<https://nws-hpc-standards.readthedocs.io/en/stable/>)

## 1. Goal

Give an agent the NCO Environmental Equivalence (EE2) production standards so it can
**author** and **review** code, shell scripts, job cards, and delivery branches that are
expected to run in, or be handed to, the NCO operational suite.

Today the catalog has RDHPCS job-script skills (`skills/hpc-skills/`) but nothing that
encodes the operational-quality rules those scripts eventually have to satisfy. When an
OMD developer moves a workflow toward production, an agent currently has no EE2 baseline
to check against and invents one.

## 2. Source of fact

The single authoritative source is the upstream standards document. Its structure
(measured from `docs/standards.rst` on the `develop` branch, 1319 lines):

| Upstream section | RST lines |
|---|---|
| Introduction | 10 |
| Standards Governance and Lifecycle | 29 |
| Workflow | 29 |
| Standard Variables, Formats, and Utilities — A. Environment Variables | 64 |
| — B. File Name Conventions | 50 |
| — C. Production Utilities | 112 |
| — D. Date Utilities | 138 |
| — E. GRIB Utilities | 15 |
| Standards — A. General Application | 88 |
| Standards — B. Compiled Code | 55 |
| Standards — C. Interpreted Code | 58 |
| Dataflow | 30 |
| Code Delivery and Vertical Structure — A/B/C/D | 206 |
| Appendix A: Workflow Examples | 369 |
| Appendix B: Variables and Directory Structure Tables | 57 |

**Canonical repo:** `NCO-HPC/nws-hpc-standards`, which the document's own governance
section names as the place to file issues and pull requests. The older
`NOAA-EMC/ee-docs` path 301-redirects to it and currently serves byte-identical content
(`standards.rst` md5 `699ca1c4…` from both). Use the canonical URL for re-syncs.

**Preferred retrieval path:** the `omd` MCP server (`~/.copilot/mcp-config.json`, docker
image `omd-mcp`) indexes `nws-hpc-standards` 11.0.0 and is the source to use for
re-syncing. Fall back to
`https://raw.githubusercontent.com/NCO-HPC/nws-hpc-standards/develop/docs/standards.rst`
when the MCP is unavailable.

**What is *not* EE2.** The file supplied with the request comes from
`NOAA-EMC/emc-repo-template`, which is not publicly readable (404 via both the web UI and
the API), so it could not be re-verified against its source. Judging from the pasted
content, that file is a *different* document — an OMD/NWS Office of Modeling and
Development master guidelines file that merely *references* `ee2-standards.md` — and none
of the following appear in the upstream EE2 document:

- its §7.1 "EE2 Compliance Workflow" five-gate ordering,
- the MPI deadlock-prevention and data-aggregation rules,
- the `std::mdspan` / column-major interoperability mandate,
- the federal security and PII section,
- the determinism, NaN/Inf, and division-by-zero guidance.

Per the approved scope, those are excluded from this skill and will be proposed separately
as an OMD `copilot-instructions.md`. If the template repo is later made accessible and
those rules turn out to be EE2-derived, they move into this skill instead.

## 3. Placement

```
skills/omd-standards/
├── ATTRIBUTION.md
└── ee2-standards/
    ├── SKILL.md
    └── references/
        ├── workflow.md
        ├── environment-variables.md
        ├── file-naming.md
        ├── standards.md
        ├── production-utilities.md
        ├── date-and-grib-utilities.md
        ├── dataflow.md
        ├── code-delivery.md
        └── examples.md
```

`omd-standards` is a new top-level family, matching the `hpc-skills` pattern (family
directory + subtree `ATTRIBUTION.md`, leaf skills inside). It leaves room for future
standards skills without re-shaping the tree.

The family gets its own `ATTRIBUTION.md` rather than inheriting `hpc-skills/LICENSE`:
this content is a verbatim-derived U.S. Government work, not Apache-2.0 ModCon-derived
material, so it must not be swept under the HPC subtree's license.

## 4. Reference-file organization: mirror upstream

Chosen over task-oriented files (`authoring.md` / `reviewing.md` / `delivering.md`) and
over a single monolithic reference.

- **Traceability.** One reference file maps to one upstream section, so an ee-docs 12.0
  re-sync is a section-by-section diff rather than a rewrite.
- **No drift.** Task-oriented files force each rule to be restated 2–3 times; the copies
  diverge.
- **Progressive disclosure.** A single ~1000-line reference defeats the point of a skill.
  Nine focused files let the agent load only the section a task needs.
- **Consistency with the catalog.** The `rdhpcs-*` skills already mirror
  `docs.rdhpcs.noaa.gov` user-guide pages one-to-one.

`examples.md` covers Appendix A (job card, J-job, ex-script, ush, modulefile, makefile,
version file, ecFlow script) and Appendix B tables. Appendix A is 369 lines of annotated
example code; it is vendored as-is because "show me a compliant J-job" is the most common
request this skill will receive.

## 5. Portability model

EE2 rules were written for WCOSS (PBS Pro + ecFlow, `$COMROOT`/`$DATA`/`$OPSROOT`,
`prod_util` executables). This catalog also targets RDHPCS (Slurm, `/scratch3`, no
ecFlow). Applying WCOSS mechanics to an RDHPCS job script produces actively wrong advice
— `#PBS` directives on a Slurm cluster, `$COMOUT` paths that do not exist.

Every rule is therefore tagged **[WCOSS]** or **[portable]**.

Tagging is declared **per file** for the single-nature files:

| File | Nature |
|---|---|
| `workflow.md` | [WCOSS] |
| `environment-variables.md` | [WCOSS] |
| `dataflow.md` | [WCOSS] |
| `code-delivery.md` | [WCOSS] (git branch/tag rules are NCO-delivery-specific) |
| `date-and-grib-utilities.md` | [WCOSS] (w3ncio / NCO libraries) |
| `file-naming.md` | mixed, tagged per rule |
| `standards.md` | **mixed, tagged per rule** — the core of the skill |
| `production-utilities.md` | [WCOSS] with a portable-principles preamble |
| `examples.md` | [WCOSS] |

`standards.md` is mixed because the General Application section contains rules that are
environment-independent. Examples of each class:

- **[portable]:** `FATAL ERROR:` / `WARNING:` message prefixes; restart capability for
  jobs over 15 minutes; no background processing; no external-pointing symlinks;
  ASCII-only text with no carriage returns; DOCBLOCK header; removal of dead code;
  descriptive error messages naming the specific missing file; fail-early so failures do
  not propagate; backup-data notification; cold-start option; primary and backup 24/7
  contacts.
- **[WCOSS]:** module-driven builds (`module load cpe-cray`, `$W3NCO_LIB4`); `err_chk` /
  `prep_step` / `exit_err` wrapping; `$COMOUT` / `$DATA` placement; ifort `FORTn`
  unit-number conventions; `valgrind4hpc`; Lmod modulefiles; `dbn_alert`; WCOSS-specific
  compiler collections.

**SKILL.md routing rule:** if the target is WCOSS or an NCO delivery, apply everything.
If the target is RDHPCS, a workstation, or research-only, apply the [portable] subset and
**state that it did so** — the agent must not silently present research-environment advice
as full EE2 compliance, and must not block a research script for missing `$SENDDBN`.

## 6. Dual audience

The user asked for both authoring guidance and a review lens.

- **Authoring:** each reference file carries the rules themselves, in imperative language
  (`must`, `must not`, `never`), with the upstream's own code examples.
- **Reviewing:** SKILL.md holds a ~20-item gate covering the highest-severity violations
  (silent error swallowing, background processing, missing restart on a >15-minute job,
  hardcoded paths, suppressed compiler warnings, unwrapped `dbn_alert`, dead code,
  non-ASCII output, working directory not cleaned up, symlinks out of the package).
  Each reference file ends with a short per-section checklist for deeper review.

The gate is a triage list, not a duplicate of the rules.

## 7. Frontmatter

```yaml
---
name: ee2-standards
description: >
  NCO Environmental Equivalence (EE2) production standards for code, shell scripts,
  and job delivery on WCOSS. Use when writing or reviewing operational Fortran, C,
  Python, or Bash for NCO delivery, checking FATAL ERROR and WARNING conventions,
  restart and cleanup rules, COM directory and file naming, prod_util calls such as
  err_chk or prep_step, module-driven builds, or release and bugfix branch naming.
metadata:
  version: "1.0"
  domain: standards
  source: https://nws-hpc-standards.readthedocs.io/en/stable/
  upstream_version: "ee-docs 11.0.0"
  as_of: "2026-11-02"
compatibility: >
  Reference and review skill; no cluster access required. Rules tagged WCOSS apply to
  NCO operational delivery; rules tagged portable also apply to RDHPCS and research code.
allowed-tools: Read Grep Glob
---
```

The draft description above is **405 characters**, inside the 480-character Cursor budget.
The catalog listing is already at ~9506/8000 characters against the Claude Code and Codex
budgets (`validate_skills.py` raises this as a warning), so an oversized description would
worsen an existing problem.

## 8. Integration with the rest of the repo

- `.github/instructions/code-review-generic.instructions.md` gains a pointer to this skill
  for operational-compliance review, with a precedence note: **EE2 overrides style
  preferences** when the target is WCOSS.
- `CONTRIBUTING.md` "Where to Add Your Skill" gains the **Standards (1)** family line.
- `README.md` structure block and contributor list regenerate from
  `tools/repo_inventory.py` — the generic `skills/**/ATTRIBUTION.md` scanner added during
  the OMD rebrand picks up the new family automatically, with no tool change needed.
- `NOTICE` gains an upstream-provenance entry for the vendored standards text.
- `unpack.sh` needs no change: `omd-standards` is discovered as a domain folder.

## 9. Error handling and maintenance

- **The skill must not depend on the MCP at runtime.** `omd` is a *maintenance* source for
  re-syncing this skill, exactly as it was for the RDHPCS conversion. The shipped
  `SKILL.md` and references must be self-contained and contain no MCP tool calls or
  instructions to call one.
- **No invented rules.** Every rule in the skill must be traceable to the upstream
  document. Validation (§10) includes a check that vendored rule strings appear in the
  fetched RST.
- **Version pinning.** `upstream_version` and `as_of` in frontmatter. If upstream changes,
  the skill is re-synced and both fields bumped; the skill does not silently absorb edits.
- **Staleness detection.** `ATTRIBUTION.md` records the re-sync procedure (fetch the RST,
  diff section by section, re-run the traceability check).
- **Ambiguity in upstream.** Where the document says "should" rather than "must", the
  skill preserves that strength and does not promote it to a hard rule.

## 10. Validation

1. `python3 tools/validate_skills.py --profile all --no-color --format text` → 0 errors.
2. `python3 tools/validate_repo_policy.py` → `repo policy: OK`, with the tree line
   `omd-standards/  # ee2-standards (1)`.
3. `python3 tools/run_tests.py` → all pass.
4. `make verify-new-skill` → green end to end.
5. **Traceability check (one-off):** script every bolded rule heading in `references/*.md`
   against the fetched `standards.rst`; fail on any rule with no upstream match.
6. **Fence balance and markdown hygiene** in all new files; `markdownlint` with the repo
   config.
7. Manual: confirm no `[WCOSS]` rule is presented as universal, and that SKILL.md's
   routing instruction is unambiguous.

## 11. Out of scope

- The EMC master-guidelines content (MPI, data layout, federal security, determinism) —
  proposed separately as an OMD `copilot-instructions.md`.
- Any change to `unpack.sh` harness targets.
- Retroactive EE2 compliance review of existing `hpc-skills` content.
