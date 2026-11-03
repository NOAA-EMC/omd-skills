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

# EE2 Standards

NCO Environmental Equivalence (EE2) production standards, vendored from ee-docs 11.0.0.
Use this skill to author or review code, shell scripts, job cards, and delivery branches
that will run in, or be handed to, the NCO operational suite.

## Which reference to load

| Task | Reference |
|---|---|
| The ecFlow → job card → J-job → ex-script → ush chain | `references/workflow.md` |
| Standard environment variables (`$COMROOT`, `$DATA`, `SENDDBN`, …) | `references/environment-variables.md` |
| Output file naming | `references/file-naming.md` |
| `prod_util` calls (`prep_step`, `err_chk`, `cpreq`, …) | `references/production-utilities.md` |
| Date and GRIB utilities (`finddate.sh`, `ndate`, `setpdy.sh`, `wgrib2`) | `references/date-and-grib-utilities.md` |
| Error handling, restart, cleanup, compiled and interpreted code rules | `references/standards.md` |
| DBNet dissemination | `references/dataflow.md` |
| Branch and tag naming, package vertical structure | `references/code-delivery.md` |
| Worked job card, J-job, ex-script, and makefile examples | `references/examples.md` |

## Portability routing

- **Target is WCOSS or an NCO delivery:** apply everything.
- **Target is RDHPCS, a workstation, or research-only:** apply the **[portable]** subset
  and state that you did. Do not present research-environment advice as full EE2
  compliance, and do not block a research script for a missing `$SENDDBN`, `prep_step`, or
  PBS directive.

Rules tagged **[portable]** are environment-independent: message prefixes, restart,
cleanup, ASCII output, DOCBLOCK, dead-code removal, fail-early, descriptive errors, and
file-naming conventions. Rules tagged **[WCOSS]** are PBS, ecFlow, and COM mechanics.

## Review gate

Triage list of the highest-severity EE2 violations. It is not a substitute for the
per-file checklists, and every item cites the reference it comes from.

1. **Silent failure** — a command's nonzero exit is unchecked; no `err_chk` wrapper. (`standards.md`, `production-utilities.md`)
2. **Wrong message prefix** — fatal errors do not start with `FATAL ERROR:`; warnings not with `WARNING:`. (`standards.md`)
3. **Vague error** — "Missing GFS data" instead of naming the specific missing file and directory. (`standards.md`)
4. **No restart on a long job** — a job over 15 minutes lacks restart capability. (`standards.md`)
5. **Background processing** — anything is backgrounded; PBS Pro loses control of it. (`standards.md`)
6. **Working directory not cleaned up** — not removed on success, or durable output not copied to `$COMOUT`. (`standards.md`)
7. **External symlink** — a symlink points outside the package. (`standards.md`)
8. **Non-ASCII output** — carriage returns or stylized quotes in files or stdout. (`standards.md`)
9. **No DOCBLOCK** — a source file or script lacks a documentation header. (`standards.md`)
10. **Dead code** — commented-out executable statements left in. (`standards.md`)
11. **Suppressed warnings** — compiler warnings silenced or the `-W` level lowered. (`standards.md`)
12. **Unwrapped `dbn_alert`** — not guarded by a `$SENDDBN`/`$SENDDBN_NTC` check. (`dataflow.md`)
13. **Missing `prep_step`** — no `prep_step` before an executable using `FORTn` units. (`production-utilities.md`)
14. **Absolute paths** — hardcoded paths to executables, libraries, or products in source, makefiles, or scripts. (`standards.md`)
15. **Hidden modules** — a build uses a hidden module or a library not in `module avail`. (`standards.md`)
16. **`$job`/`$envir`/`$model_ver` in file names** — output names not stable across environments. (`file-naming.md`)
17. **Inline date math** — date arithmetic not using `finddate.sh`, `ndate`, or `setpdy.sh`. (`date-and-grib-utilities.md`)
18. **No shebang or indirect invoke** — a script lacks `#!`, or is run as `sh script` instead of directly. (`standards.md`)
19. **Dev work areas present** — benchmarking tools or developer paths remain before IDSB submission. (`standards.md`)
20. **Wrong delivery branch or tag name** — not `release/vX.Y`, `bugfix/…`, `hotfix/…`, or `vX.Y-rc<#>` starting at 0. (`code-delivery.md`)

## Scope

This skill covers the NCO EE2 standards document only. It does not cover MPI
deadlock-prevention, data layout, federal security or PII handling, or determinism and
NaN guidance — that material is separate OMD content, not EE2.
