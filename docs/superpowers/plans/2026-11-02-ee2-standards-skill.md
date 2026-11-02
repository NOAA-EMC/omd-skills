# EE2 Standards Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `skills/omd-standards/ee2-standards/`, a skill that vendors the NCO Environmental Equivalence (EE2) production standards from the upstream `standards.rst` into nine traceable reference files, so an agent can author and review code, shell scripts, job cards, and delivery branches destined for the NCO operational suite.

**Architecture:** A vendored Python extractor (`tools/ee2_extract.py`) converts each pinned section of the upstream RST into a Markdown reference file with a deterministic, repeatable transformation. Every reference file maps one-to-one to an upstream section, so a future ee-docs re-sync is a section-by-section diff rather than a rewrite. Rules are tagged `[WCOSS]` or `[portable]` at authoring time so the skill never presents WCOSS-only mechanics (`$COMOUT`, `prep_step`, PBS directives) as universal advice. `SKILL.md` carries a routing rule and a 20-item review gate; `tests/test_ee2_traceability.py` proves every bolded rule heading and curated probe round-trips into the fetched RST and that no RST markup survives outside code fences.

**Tech Stack:** Markdown skill files with YAML frontmatter; Python 3 `unittest` (this repo has no pytest — tests run via `python3 tools/run_tests.py`); `tools/validate_skills.py` (five-profile skill validator); `tools/validate_repo_policy.py`; `markdownlint` (repo config); GNU `make`.

**Spec:** [../specs/2026-11-02-ee2-standards-skill-design.md](../specs/2026-11-02-ee2-standards-skill-design.md) — approved, committed as `ab5b7f2`.

## Global Constraints

Every task below implicitly includes this section.

- Skill `name` is lowercase alphanumerics and single hyphens, no leading/trailing/consecutive hyphen, ≤64 code points, and **must equal its directory name byte-for-byte** (`ee2-standards`). Enforced by `SPEC_NAME_PORTABLE_RE = ^[a-z0-9]+(?:-[a-z0-9]+)*$` at `tools/validate_skills.py:157`.
- `description` ≤1024 code points **after YAML parsing** (`CODEX_CATALOG_DESC_CAP`, `tools/validate_skills.py:133`). Use the exact folded description in spec §7 — it parses to 406 characters; do **not** lengthen it. The catalog listing is already ~10247/8000 characters against the Claude/Codex budgets (this warning is pre-existing and does not fail the gate — `validate_skills.py` exits 0 on warnings), so an oversized description would worsen an existing problem.
- `compatibility` is a single-line string ≤500 code points. The folded block in spec §7 parses to one line of 172 characters; keep it under 500.
- `SKILL.md` ≤500 lines and body under ~20,000 characters (`tools/validate_skills.py:2198-2199`). The SKILL.md body is routing + gate only; all rule text lives in `references/`.
- `allowed-tools` on `ee2-standards` is exactly `Read Grep Glob`. This skill reads and reviews; it does not submit jobs or fetch at runtime.
- **No MCP dependency at runtime.** `SKILL.md` and every reference file must contain no `omd` tool calls or instructions to call one. `omd` is a maintenance source for re-syncing only (spec §9).
- **No invented rules.** Every rule string vendored into `references/` must be traceable to the fetched `standards.rst`. Task 7 is the automated guard.
- **Heading levels present upstream are `=`, `-`, and `^`** (the `^` level appears twice, both in the Code Delivery section: "i. Issue Tracking on Remote Hosting Services" and "ii. Bugzillas"). `tools/ee2_extract.py` maps all three (`HEADING_LEVELS` includes `"^": "####"`, and the setext regex accepts `[=\-~^]`), and every residue check includes `r"^\^+$"` so an unmapped heading character can never ship as a literal `^^^^` underline again. This is why `code-delivery.md` is 166 generated lines, not the 168 a `^`-blind converter emits.

- **Preserve upstream defects verbatim; do not silently correct them.** Specifically: the prose reference to "Table 7" in the Code Delivery section (upstream RST line 836) has no matching table definition (upstream defines Tables 1–6, 8, 9 only); the typos `procure code deliveres` (RST 729) and `intendend` (RST 16) stay as written. Document the Table 7 gap in `code-delivery.md` rather than inventing a table.
- **Source of fact is pinned.** The upstream `standards.rst` is ee-docs **11.0.0**, 1319 lines, md5 `699ca1c4ecb6e6ef6c4fbc4cd3112592`, canonical repo `NCO-HPC/nws-hpc-standards`. Fetch from `https://raw.githubusercontent.com/NCO-HPC/nws-hpc-standards/develop/docs/standards.rst`.
- Vendored files are a U.S. Government work, **not** Apache-2.0. The new family gets its own `skills/omd-standards/ATTRIBUTION.md` and must **not** fall under `skills/hpc-skills/LICENSE`.
- Do not modify: `tools/validate_skills.py`, `tools/validate_repo_policy.py`, `tools/repo_inventory.py`, `unpack.sh`, or `NOTICE`'s existing entries (only append). The only `tools/` file added is `tools/ee2_extract.py`.
- `README.md`'s Repository Structure block and Contributors list are generated by `tools/repo_inventory.py`; they change in the **same commit** as any skill directory add, or `make policy` fails.
- markdownlint (`make lint`) covers only `^(README\.md|CONTRIBUTING\.md|docs/getting_started\.md|\.github/instructions/.*\.md)$` (`.pre-commit-config.yaml:14-17`). The new `skills/omd-standards/**` files are **not** markdownlint-enforced, but Tasks 2–5 validate them with the repo config manually and they must pass. The `.github/instructions/` edit in Task 8 **is** markdownlint-enforced.
- `make lint` runs `python3 -m compileall -q tools skill-search tests` for Python — there is **no** ruff/black/flake8 pre-commit hook, so `tools/ee2_extract.py` only needs to be valid, compileable Python.
- **Environment gotcha:** prefix every `make` or `python3 tools/...` invocation with `export PATH="/opt/homebrew/Caskroom/miniforge/base/bin:$PATH"` or `validate_skills.py` falsely reports "PyYAML is required".
- Commit after every task, with a `Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>` trailer.
- **The OMD rebrand is currently uncommitted.** Task 1 Step 1 commits it as its own commit so the EE2 commits stay separate. Never fold rebrand edits into an EE2 commit.

**Pinned section ranges for all tasks (1-based inclusive, verified against upstream headings):**

| Reference file | RST lines | Generated lines (incl. H1) | Nature |
|---|---|---|---|
| `workflow.md` | 38–66 | 25 | [WCOSS] |
| `environment-variables.md` | 72–135 | 56 | [WCOSS] |
| `file-naming.md` | 136–185 | 49 | mixed, per rule |
| `production-utilities.md` | 186–297 | 106 | [WCOSS] + portable preamble |
| `date-and-grib-utilities.md` | 298–450 | 145 | [WCOSS] |
| `standards.md` | 451–654 | 197 | mixed, per rule — **the core** |
| `dataflow.md` | 655–684 | 24 | [WCOSS] |
| `code-delivery.md` | 685–893 | 166 | [WCOSS] |
| `examples.md` | 894–1319 | 385 | [WCOSS] |

---

## Task 1: Commit the pending rebrand, then scaffold the family and `SKILL.md` frontmatter

Creates the new top-level family directory, its attribution file, and the skill entry point with frontmatter only (the body arrives in Task 6). Ends with `validate_skills.py` accepting the skill.

**Files:**
- Create: `skills/omd-standards/ATTRIBUTION.md`
- Create: `skills/omd-standards/ee2-standards/SKILL.md` (frontmatter only)
- Create: `skills/omd-standards/ee2-standards/references/` (placeholder, replaced in Task 2)

**Interfaces:**
- Produces: `skills/omd-standards/ee2-standards/SKILL.md` with frontmatter `name: ee2-standards`; the `references/` directory that Task 2 writes nine files into; `skills/omd-standards/ATTRIBUTION.md` holding the re-sync procedure that Task 8's NOTICE entry points at.

- [ ] **Step 1: Commit the pending OMD rebrand as its own commit**

```bash
cd /Users/barry/Documents/genesis-skills
export PATH="/opt/homebrew/Caskroom/miniforge/base/bin:$PATH"
git status --short
```

Confirm the dirty paths are only rebrand files (README, NOTICE, CONTRIBUTING, docs/, `.github/`, `skills/**` renames, `tools/`). Then:

```bash
git add -A
git commit -m "chore: complete OMD rebrand of the skills catalog

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

Expected: one commit created; `git status --short` afterwards prints nothing.

- [ ] **Step 2: Create the family attribution file**

Create `skills/omd-standards/ATTRIBUTION.md` with exactly this content:

```markdown
# Attribution

**Team:** OMD - Modeling Division

**Author:** Barry Baker (OMD)

## NCO EE2 production standards

The `ee2-standards` skill vendors the NCEP/NCO Environmental Equivalence (EE2)
production standards. The reference files under `ee2-standards/references/` are
derived, via `tools/ee2_extract.py`, from the upstream standards document:

- Canonical repository: <https://github.com/NCO-HPC/nws-hpc-standards>
- Source file: `docs/standards.rst`
- Upstream version: ee-docs **11.0.0**
- Rendered documentation: <https://nws-hpc-standards.readthedocs.io/en/stable/>
- Pinned revision md5: `699ca1c4ecb6e6ef6c4fbc4cd3112592` (1319 lines)

This content is a U.S. Government work and is **not** licensed under the
Apache-2.0 grant carried by the `skills/hpc-skills/` subtree. Placing it under a
separate `omd-standards/` family keeps the two licenses distinct.

### Re-sync procedure

1. Fetch the current RST:
   `curl -fsSL https://raw.githubusercontent.com/NCO-HPC/nws-hpc-standards/develop/docs/standards.rst -o /tmp/ee-standards.rst`
2. Run `python3 tools/ee2_extract.py /tmp/ee-standards.rst` and compare the
   reported md5 against the pinned value. If it differs, the section line ranges
   in `SECTIONS` may have shifted — re-derive them from the document's own
   headings before regenerating.
3. Regenerate into a scratch directory (`--write /tmp/gen`), diff each file
   section-by-section against the committed copy, and carry forward the
   `[WCOSS]`/`[portable]` tags and per-section checklists.
4. Re-run `python3 tools/run_tests.py`; the traceability test is the guard.
5. Bump `upstream_version` and `as_of` in `SKILL.md` frontmatter.
```

- [ ] **Step 3: Create `SKILL.md` with frontmatter only**

Create `skills/omd-standards/ee2-standards/SKILL.md` with exactly this content:

```markdown
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

- [ ] **Step 4: Create the references directory placeholder**

```bash
mkdir -p skills/omd-standards/ee2-standards/references
touch skills/omd-standards/ee2-standards/references/.gitkeep
```

- [ ] **Step 5: Validate the skill frontmatter**

Run: `python3 tools/validate_skills.py --profile all --no-color --format text`
Expected: no `ERROR` line mentions `ee2-standards`. A short/empty body warning is acceptable here — Task 6 adds the body.

- [ ] **Step 6: Commit**

```bash
git add skills/omd-standards/
git commit -m "feat(ee2): scaffold omd-standards family and skill frontmatter

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 2: Vendor the extractor and generate all nine references

Adds `tools/ee2_extract.py` (the validated RST→Markdown converter with the pinned `SECTIONS` table), fetches the upstream RST, and generates all nine raw reference files. Everything later tasks hand-edit is produced here.

**Files:**
- Create: `tools/ee2_extract.py`
- Create: `skills/omd-standards/ee2-standards/references/workflow.md`
- Create: `skills/omd-standards/ee2-standards/references/environment-variables.md`
- Create: `skills/omd-standards/ee2-standards/references/file-naming.md`
- Create: `skills/omd-standards/ee2-standards/references/production-utilities.md`
- Create: `skills/omd-standards/ee2-standards/references/date-and-grib-utilities.md`
- Create: `skills/omd-standards/ee2-standards/references/standards.md`
- Create: `skills/omd-standards/ee2-standards/references/dataflow.md`
- Create: `skills/omd-standards/ee2-standards/references/code-delivery.md`
- Create: `skills/omd-standards/ee2-standards/references/examples.md`
- Test: `python3 -m compileall -q tools/ee2_extract.py`; `markdownlint` with the repo config

**Interfaces:**
- Consumes: the `references/` directory from Task 1.
- Produces: `tools/ee2_extract.py` exposing module-level `SECTIONS: dict[str, tuple[int, int, str]]`, `UPSTREAM_MD5: str`, `convert(text: str) -> str`, `section(path: str, start: int, end: int) -> str`, `extract_all(rst_path: str) -> dict[str, str]`; nine Markdown files under `references/`, each beginning with a `# <Title>` H1. Task 7 imports `SECTIONS` and `UPSTREAM_MD5`.

- [ ] **Step 1: Write `tools/ee2_extract.py`**

Create `tools/ee2_extract.py` with exactly this content:

```python
"""Extract EE2 reference files from the upstream NCO standards.rst.

Structural pass first (code blocks, csv-tables), inline-markup pass applied
only to prose parts so that emitted fences and vendored example code are
never rewritten. The SECTIONS table pins the 1-based line ranges of the
pinned upstream revision; run with --write to emit every reference file.
"""
from __future__ import annotations

import re

SMART = {"\u201c": '"', "\u201d": '"', "\u2018": "'", "\u2019": "'", "\u2013": "-", "\u2014": "--"}


def clean_prose(text: str) -> str:
    for k, v in SMART.items():
        text = text.replace(k, v)
    text = re.sub(r"^\.\. _[\w-]+:\s*$", "", text, flags=re.M)        # link targets
    text = re.sub(r"\.\. \[#(\w+)\] (.*)", r"[^\1]: \2", text)        # footnote defs
    text = re.sub(r"\[#(\w+)\]_", r"[^\1]", text)                      # footnote refs
    text = re.sub(r".. note::[ \t]*", "**Note:** ", text)
    text = re.sub(r"`([^`]+) <(https?://[^>]+)>`_", r"[\1](\2)", text)  # named hyperlinks
    text = re.sub(r"`([^`]+)`_", r"\1", text)                           # implicit refs
    text = re.sub(r":ref:`([^`]+) <[^`]+>`", r"\1", text)               # sphinx ref roles
    text = re.sub(r"\*\*\*+", "**", text)                               # bold+italic residue
    text = re.sub(r"``([^`]+)``", r"`\1`", text)                       # inline literals
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _csv_rows(block: list[str]) -> list[list[str]]:
    rows = []
    for line in block:
        s = line.strip()
        if not s or s.startswith(":"):
            continue
        cells = re.findall(r'"((?:[^"]|"")*)"', s)
        if cells:
            rows.append([c.replace('""', '"') for c in cells])
    return rows


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip()) if line.strip() else 0


HEADING_LEVELS = {"=": "##", "-": "###", "~": "####", "^": "####"}


def demote_headings(text: str) -> str:
    """Convert RST setext headings to ATX, shifted so the `=` level becomes `##`.

    Fence-aware: lines inside a code block are copied through untouched, so a
    table rule or divider in vendored example code is never read as a heading.
    """
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    in_fence = False
    while i < len(lines):
        line = lines[i]
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append(line)
            i += 1
            continue
        underline = lines[i + 1] if i + 1 < len(lines) else ""
        marker = underline.strip()
        if (
            not in_fence
            and line.strip()
            and not line.startswith((" ", "\t"))
            and re.fullmatch(r"([=\-~^])\1{2,}", marker)
        ):
            out.append(f"{HEADING_LEVELS[marker[0]]} {line.strip()}")
            i += 2
            continue
        out.append(line)
        i += 1
    return "\n".join(out)


def _relevel(text: str) -> str:
    """Shift heading levels so the shallowest *real* heading in the excerpt is `##`.

    Fence-aware: `#` comment lines inside code blocks are not headings and must
    not be counted when choosing the shift.
    """
    levels = []
    inf = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            inf = not inf
            continue
        if not inf:
            m = re.match(r"^(#+) ", line)
            if m:
                levels.append(len(m.group(1)))
    if not levels:
        return text
    shift = 2 - min(levels)
    if shift == 0:
        return text
    out = []
    inf = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            inf = not inf
            out.append(line)
            continue
        if inf:
            out.append(line)
            continue
        m = re.match(r"^(#+) ", line)
        if m:
            out.append("#" * max(2, min(6, len(m.group(1)) + shift)) + line[len(m.group(1)):])
        else:
            out.append(line)
    return "\n".join(out)


def convert(text: str) -> str:
    lines = text.split("\n")
    parts: list[tuple[str, str, int]] = []   # (kind, content, indent)
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^(\s*)\.\. (code-block|csv-table)::[ \t]*(\S*)[ \t]*$", line)
        if m:
            indent, kind, lang = len(m.group(1)), m.group(2), m.group(3)
            i += 1
            body = []
            while i < len(lines):
                if not lines[i].strip():
                    body.append("")
                    i += 1
                    continue
                if _indent_of(lines[i]) <= indent:
                    break
                body.append(lines[i])
                i += 1
            while body and not body[-1].strip():
                body.pop()
            if kind == "code-block":
                strip = min((_indent_of(b) for b in body if b.strip()), default=0)
                code = "\n".join(b[strip:] if b.strip() else "" for b in body)
                parts.append(("code", code, indent))
                parts.append(("lang", lang, indent))
            else:
                parts.append(("table", "\n".join(body), indent))
            continue
        parts.append(("prose", line, -1))
        i += 1

    out: list[str] = []
    buf: list[str] = []
    idx = 0
    while idx < len(parts):
        kind, content, indent = parts[idx]
        if kind == "prose":
            buf.append(content)
            idx += 1
            continue
        if buf:
            out.append(clean_prose("\n".join(buf)))
            buf = []
        if kind == "code":
            code = parts[idx][1]
            lang = parts[idx + 1][1] if parts[idx + 1][0] == "lang" else ""
            fence = " " * indent + "```" + lang
            body = "\n".join(((" " * indent) + c).rstrip() if c else "" for c in code.split("\n"))
            out.append(f"{fence}\n{body}\n" + " " * indent + "```")
            idx += 3 if parts[idx + 2][0] == "lang" else 2
            continue
        if kind == "lang":
            idx += 1
            continue
        rows = _csv_rows(content.split("\n"))
        if len(rows) >= 2:
            header, data = rows[0], rows[1:]
            width = len(header)

            def cell(c: str) -> str:
                return clean_prose(c).replace("|", "\\|").strip()

            table = [" " * indent + "| " + " | ".join(cell(c) for c in header) + " |",
                     " " * indent + "| " + " | ".join("---" for _ in header) + " |"]
            for r in data:
                r = (r + [""] * width)[:width]
                table.append(" " * indent + "| " + " | ".join(cell(c) for c in r[:width]) + " |")
            out.append("\n".join(table))
        idx += 1
    if buf:
        out.append(clean_prose("\n".join(buf)))
    text = "\n".join(out)
    text = demote_headings(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = _relevel(text)
    return "\n".join(line.rstrip() for line in text.split("\n")).strip() + "\n"


def section(path: str, start: int, end: int) -> str:
    lines = open(path, encoding="utf-8").read().split("\n")
    return convert("\n".join(lines[start - 1:end]))


# 1-based inclusive line ranges into the pinned standards.rst (md5
# 699ca1c4ecb6e6ef6c4fbc4cd3112592, ee-docs 11.0.0). Keys are the output
# file names under references/. The title becomes the emitted H1 so each file
# satisfies markdownlint MD041.
SECTIONS = {
    "workflow.md": (38, 66, "Workflow"),
    "environment-variables.md": (72, 135, "Standard Environment Variables"),
    "file-naming.md": (136, 185, "File Name Conventions"),
    "production-utilities.md": (186, 297, "Production Utilities"),
    "date-and-grib-utilities.md": (298, 450, "Date and GRIB Utilities"),
    "standards.md": (451, 654, "Standards"),
    "dataflow.md": (655, 684, "Dataflow"),
    "code-delivery.md": (685, 893, "Code Delivery and Vertical Structure"),
    "examples.md": (894, 1319, "Workflow Examples and Tables"),
}

UPSTREAM_MD5 = "699ca1c4ecb6e6ef6c4fbc4cd3112592"


def extract_all(rst_path: str) -> dict[str, str]:
    """Return {filename: markdown} for every pinned section, H1 included."""
    result = {}
    for name, (start, end, title) in SECTIONS.items():
        body = section(rst_path, start, end)
        result[name] = f"# {title}\n\n{body}"
    return result


def _verify_md5(rst_path: str) -> bool:
    import hashlib
    digest = hashlib.md5(open(rst_path, "rb").read()).hexdigest()
    if digest != UPSTREAM_MD5:
        print(f"WARNING: {rst_path} md5 {digest} != pinned {UPSTREAM_MD5}")
        return False
    return True


if __name__ == "__main__":
    import argparse
    import pathlib

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("rst", help="path to the fetched standards.rst")
    ap.add_argument("--write", metavar="DIR", help="directory to write reference files into")
    ap.add_argument("--only", metavar="NAME", help="emit a single section file to stdout")
    args = ap.parse_args()

    _verify_md5(args.rst)
    files = extract_all(args.rst)
    if args.only:
        print(files[args.only], end="")
    elif args.write:
        out = pathlib.Path(args.write)
        out.mkdir(parents=True, exist_ok=True)
        for name, text in files.items():
            (out / name).write_text(text, encoding="utf-8")
            print(f"wrote {out / name} ({len(text.splitlines())} lines)")
    else:
        for name, text in files.items():
            print(f"=== {name} ({len(text.splitlines())} lines) ===")
```

- [ ] **Step 2: Confirm the module compiles**

Run: `python3 -m compileall -q tools/ee2_extract.py && echo OK`
Expected: `OK`, with no `SyntaxError`.

- [ ] **Step 3: Fetch the pinned upstream RST**

```bash
curl -fsSL https://raw.githubusercontent.com/NCO-HPC/nws-hpc-standards/develop/docs/standards.rst -o /tmp/ee-standards.rst
md5 -q /tmp/ee-standards.rst
wc -l /tmp/ee-standards.rst
```

Expected: md5 `699ca1c4ecb6e6ef6c4fbc4cd3112592` and `1319` lines. If the md5 differs, **stop** — `develop` has moved and the `SECTIONS` line ranges may have shifted. Do not regenerate from a drifted file; re-derive the ranges from the document's own headings first, then update `SECTIONS`, the Global Constraints table, and the Task 7 probes together.

- [ ] **Step 4: Generate all nine reference files**

```bash
python3 tools/ee2_extract.py /tmp/ee-standards.rst --write skills/omd-standards/ee2-standards/references
```

Expected: nine `wrote .../references/<file> (N lines)` lines with N matching the "Generated lines" column of the Global Constraints table — workflow 25, environment-variables 56, file-naming 49, production-utilities 106, date-and-grib-utilities 145, standards 197, dataflow 24, code-delivery 166, examples 385 — and no `WARNING: ... md5` line.

- [ ] **Step 5: Remove the placeholder**

```bash
rm -f skills/omd-standards/ee2-standards/references/.gitkeep
```

- [ ] **Step 6: Validate markdown hygiene**

```bash
markdownlint --config .markdownlint.json skills/omd-standards/ee2-standards/references/*.md
```

Expected: exit code 0 with no output. The repo config enables only MD009 (no trailing spaces), MD041 (first line is a heading), and MD047 (file ends with a newline); the extractor emits an H1, rstrips every line, and ends with a newline.

- [ ] **Step 7: Confirm zero RST residue outside code fences**

```bash
python3 - <<'CHECK'
import pathlib
import re

RES = [r"``", r"\[#", r":ref:", r"^\.\. _", r"[\u201c\u201d\u2018\u2019]", r"`_",
       r"\.\. note::", r"csv-table", r"code-block", r"^\^+$"]
bad = 0
for path in sorted(pathlib.Path("skills/omd-standards/ee2-standards/references").glob("*.md")):
    inf = False
    for i, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
        if line.lstrip().startswith("```"):
            inf = not inf
            continue
        if inf:
            continue
        for pat in RES:
            if re.search(pat, line):
                print("RESIDUE", path.name, i, pat, repr(line[:60]))
                bad += 1
    if path.read_text(encoding="utf-8").count("```") % 2:
        print("UNBALANCED FENCE", path.name)
        bad += 1
print("residue/fence issues:", bad)
CHECK
```

Expected: `residue/fence issues: 0`. (Task 7 turns this same check into a permanent test.)

- [ ] **Step 8: Commit**

```bash
git add tools/ee2_extract.py skills/omd-standards/ee2-standards/references/
git commit -m "feat(ee2): add RST extractor and generate nine reference files

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 3: Tag `standards.md` and add its review checklist

`standards.md` is the core of the skill (spec §5). Section A's rules are environment-independent and get `[portable]`; sections B and C are WCOSS mechanics and get a scope banner. The tag is written **outside** the closing `**` so the bolded heading text is unchanged and stays traceable.

**Files:**
- Modify: `skills/omd-standards/ee2-standards/references/standards.md`

**Interfaces:**
- Consumes: the generated `standards.md` from Task 2 (197 lines; H1 `# Standards`, then `## Standards`, then `### A. General Application Standards`, `### B. Compiled Code (C or Fortran source)`, `### C. Interpreted Code (bash, ksh, perl, or python scripts)`).
- Produces: `standards.md` with thirteen section-A rule bullets tagged `[portable]`, a `> **[WCOSS]**` blockquote under each of the B and C headings, and a `## Review checklist` section appended. Task 6's gate and Task 7's heading extraction read the tagged bullets.

- [ ] **Step 1: Tag the thirteen section-A rule headings `[portable]`**

Each section-A rule is a bullet whose heading sits alone on its line as `* **<Heading>`. Append ` [portable]` after the closing `**` on each of these thirteen lines, leaving the heading text itself untouched:

```
* **Notification of use of backup data** [portable]
* **Data of opportunity** [portable]
* **Descriptive error messages** [portable]
* **Appropriate modes of failure** [portable]
* **Recovery from code failure or abnormal system failure** [portable]
* **No background processing** [portable]
* **No external-pointing symlinks** [portable]
* **Working directories** [portable]
* **Text formatting** [portable]
* **Documentation Blocks** [portable]
* **Points of contact** [portable]
* **Cold starts** [portable]
* **Removal of dead code** [portable]
```

Verify all thirteen are tagged and none missed:

```bash
grep -cE '^\* \*\*[^*]+\*\* \[portable\]$' skills/omd-standards/ee2-standards/references/standards.md
```

Expected: `13`. And no untagged bolded bullet remains in section A:

```bash
sed -n '/### A\./,/### B\./p' skills/omd-standards/ee2-standards/references/standards.md \
  | grep -E '^\* \*\*[^*]+\*\*$'
```

Expected: no output (every section-A bullet heading now carries a tag).

- [ ] **Step 2: Add a `[WCOSS]` scope banner under section B**

Replace the line `### B. Compiled Code (C or Fortran source)` with:

```markdown
### B. Compiled Code (C or Fortran source)

> **[WCOSS]** The compiler collections, the `module load` build pattern, `FORTn` unit
> numbers, `prep_step`, and `valgrind4hpc` below are WCOSS production mechanics. The
> portable principles in this section — compile without warnings, never suppress warnings,
> fail early, descriptive errors naming the specific missing file, structured control
> instead of `GO TO` — apply everywhere.
```

- [ ] **Step 3: Add a `[WCOSS]` scope banner under section C**

Replace the line `### C. Interpreted Code (bash, ksh, perl, or python scripts)` with:

```markdown
### C. Interpreted Code (bash, ksh, perl, or python scripts)

> **[WCOSS]** `$DATA`, `$COMROOT`, `$SENDDBN`/`$SENDDBN_NTC`, `setpdy.sh`, `prep_step` and
> `err_chk` wrapping, COMROOT cleanup, and "never write to dcom" are WCOSS mechanics. The
> portable principles — a `#!` shebang, invoke scripts directly rather than via `sh`,
> debug logging with `PS4='+ $SECONDS +'`, redirect verbose output, use the module's Python
> rather than the system's, and no false or misleading errors — apply everywhere.
```

- [ ] **Step 4: Append the review checklist**

Add at the very end of `standards.md`:

```markdown

## Review checklist

Items marked **[portable]** apply on RDHPCS and research code; **[WCOSS]** items apply
only to operational delivery.

- **[portable]** Fatal errors print `FATAL ERROR:`; warnings print `WARNING:`.
- **[portable]** Any job over 15 minutes has restart capability, and restarted products are
  not delayed by more than 15 minutes.
- **[portable]** No background processing; killing the job terminates all its child processes.
- **[portable]** No symlinks point outside the package (no absolute-path links).
- **[portable]** The working directory is removed on success; anything kept past one cycle is
  copied to `$COMOUT` (**[WCOSS]**) or an equivalent durable output path.
- **[portable]** Text files and standard output are ASCII-only with no carriage returns.
- **[portable]** Each source file and script carries a DOCBLOCK header.
- **[portable]** Dead (commented-out) executable statements are removed before delivery.
- **[portable]** Code compiles with no errors and no suppressed warnings; the warning level is
  at least the default.
- **[portable]** Errors are caught as early as possible and named specifically — "Missing
  GFS data" is rejected; the message names the missing file and directory.
- **[portable]** Failures do not propagate past the first point where the problem is detectable.
- **[portable]** Every production application has a primary and backup contact reachable 24/7.
- **[portable]** Jobs that depend on restart data offer a cold-start option.
- **[WCOSS]** Fortran I/O units follow 11-49 input / 51-79 output / 80-94 work, and `prep_step`
  is called before executables that use `FORTn`.
- **[WCOSS]** Each `dbn_alert` block is wrapped in a `$SENDDBN`/`$SENDDBN_NTC` check.
- **[WCOSS]** Each C or Fortran execution is wrapped with `prep_step` and `err_chk`.
- **[WCOSS]** Nothing is written to dcom unless ingesting data from an outside source.
- **[WCOSS]** Files containing restricted data carry the appropriate group and permissions.
```

- [ ] **Step 5: Re-validate markdown hygiene**

Run: `markdownlint --config .markdownlint.json skills/omd-standards/ee2-standards/references/standards.md`
Expected: exit code 0, no output.

- [ ] **Step 6: Commit**

```bash
git add skills/omd-standards/ee2-standards/references/standards.md
git commit -m "feat(ee2): tag standards.md portable/WCOSS and add review checklist

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 4: Tag `file-naming.md` and add its review checklist

`file-naming.md` is the other mixed file: the naming conventions are portable, but the `com` and `wmo` directory formats are WCOSS output-structure specifics.

**Files:**
- Modify: `skills/omd-standards/ee2-standards/references/file-naming.md`

**Interfaces:**
- Consumes: the generated `file-naming.md` from Task 2 (49 lines; H1 `# File Name Conventions`, then `## B. File Name Conventions`).
- Produces: `file-naming.md` with a `[portable]` banner under `## B. File Name Conventions`, `[WCOSS]` labels on the `com` and `wmo` format lines, and a `## Review checklist` appended.

- [ ] **Step 1: Add a `[portable]` banner under the section heading**

Replace the line `## B. File Name Conventions` with:

```markdown
## B. File Name Conventions

> **[portable]** The character, separator, prefix, padding, and consistency rules below
> apply to any model output file name. Only the `com` and `wmo` directory-format blocks are
> **[WCOSS]** output-structure specifics.
```

- [ ] **Step 2: Label the `com` format line `[WCOSS]`**

Replace the line:

```
Filename format for files in `com`:
```

with:

```markdown
Filename format for files in `com` (**[WCOSS]**):
```

- [ ] **Step 3: Label the `wmo` format line `[WCOSS]`**

Replace the line:

```
Filename format for files in the `wmo` sub-directory: `format.model.tHHz.awp_var_info.f###.domain`
```

with:

```markdown
Filename format for files in the `wmo` sub-directory (**[WCOSS]**): `format.model.tHHz.awp_var_info.f###.domain`
```

- [ ] **Step 4: Append the review checklist**

Add at the very end of `file-naming.md`:

```markdown

## Review checklist

- **[portable]** No special characters, uppercase characters, or dates in file names — the
  containing directory carries the date.
- **[portable]** Periods separate categories; underscores separate words within a category.
- **[portable]** Grid resolutions below 1 use a leading 0, and a "point" is written `p`
  (0.25 becomes `0p25`).
- **[portable]** Forecast hours carry an `f` prefix and are zero-padded so every file in a
  set has the same number of digits.
- **[portable]** File names do not embed `$job`, `$envir`, or `$model_ver` — names must be
  consistent across environments and application versions.
- **[portable]** ASCII inventory files end in `.grib2.idx`; binary index files end in
  `.bin.idx`.
- **[WCOSS]** `com` output follows the `tHHz`/`f###` cycle-and-forecast-hour pattern for its
  model class, except space weather, which uses `model.var_info.valid_time.domain.format`.
- **[WCOSS]** `wmo` sub-directory files follow `format.model.tHHz.awp_var_info.f###.domain`.
```

- [ ] **Step 5: Re-validate markdown hygiene**

Run: `markdownlint --config .markdownlint.json skills/omd-standards/ee2-standards/references/file-naming.md`
Expected: exit code 0, no output.

- [ ] **Step 6: Commit**

```bash
git add skills/omd-standards/ee2-standards/references/file-naming.md
git commit -m "feat(ee2): tag file-naming.md portable/WCOSS and add checklist

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 5: Add `[WCOSS]` banners and checklists to the seven single-nature files

The remaining seven files are uniformly `[WCOSS]` (spec §5). Each gets a scope banner directly under its H1 and a short review checklist. `workflow.md` additionally needs its `Workflow Diagram::` literal block fenced, because that block is the one non-`code-block` literal in the document and the converter passes it through verbatim. `code-delivery.md` additionally records the upstream Table 7 gap.

**Files:**
- Modify: `skills/omd-standards/ee2-standards/references/workflow.md`
- Modify: `skills/omd-standards/ee2-standards/references/environment-variables.md`
- Modify: `skills/omd-standards/ee2-standards/references/production-utilities.md`
- Modify: `skills/omd-standards/ee2-standards/references/date-and-grib-utilities.md`
- Modify: `skills/omd-standards/ee2-standards/references/dataflow.md`
- Modify: `skills/omd-standards/ee2-standards/references/code-delivery.md`
- Modify: `skills/omd-standards/ee2-standards/references/examples.md`

**Interfaces:**
- Consumes: the seven generated files from Task 2.
- Produces: each file with a `> **[WCOSS]**` (or `[portable]`) banner as the first blockquote after its H1, and a `## Review checklist` section appended.

- [ ] **Step 1: `workflow.md` — banner, fence the diagram, checklist**

Insert this banner between the `# Workflow` H1 and the `## Workflow` heading:

```markdown
> **[WCOSS]** ecFlow, PBS Pro, `qsub`, job cards, and the `J-job` → `ex-script` → `ush`
> chain are the WCOSS production workflow. The portable principle: keep every
> environment-dependent setting in the job card or `J-job` — one place per variable — so
> moving from development to production changes only those exports.
```

Then replace the trailing literal block. Find:

```
Workflow Diagram::

  job card
    -> J-job
        -> ex-script
            -> ush
                -> utility script(s)
                -> compiled executable(s)
```

and replace it with a fenced block (the outer four-backtick fence below is only so this
plan can show the three-backtick fence literally — in `workflow.md` the block starts with
three backticks):

````markdown
Workflow Diagram:

```text
job card
  -> J-job
      -> ex-script
          -> ush
              -> utility script(s)
              -> compiled executable(s)
```
````

Append:

```markdown

## Review checklist

- **[WCOSS]** All jobs are scheduled by ecFlow and submitted to PBS Pro via `qsub`.
- **[WCOSS]** The job card sets PBS directives and the execution environment, then calls the
  `J-job`; downstream scripts use the `J-job`'s variables and never alter them.
- **[WCOSS]** Moving a model from development to production changes only the variables
  exported in the job cards.
```

- [ ] **Step 2: `environment-variables.md` — banner and checklist**

Insert after the `# Standard Environment Variables` H1:

```markdown
> **[WCOSS]** These are the NCO standard production environment variables (`$COMROOT`,
> `$DATA`, `$OPSROOT`, `SENDDBN`, and the rest of Table 1). On RDHPCS or a workstation,
> adopt the *pattern* — a single documented set of role variables established in the job
> card — rather than the exact WCOSS values.
```

Append:

```markdown

## Review checklist

- **[WCOSS]** The standard variable set is used wherever appropriate; variables unused by a
  job need not be defined (keep the `J-job` clutter-free).
- **[WCOSS]** Boolean controls (`SENDECF`, `SENDDBN`, `SENDDBN_NTC`, `SENDCOM`, `SENDWEB`,
  `KEEPDATA`) are set to `YES` or `NO` in all caps.
- **[WCOSS]** Job-card-set variables (`envir`, `PACKAGEROOT`, `OPSROOT`, `job`, `jobid`,
  `DBNROOT`) come from the ecFlow-generated card, not from the scripts.
```

- [ ] **Step 3: `production-utilities.md` — portable preamble, banner, checklist**

Insert after the `# Production Utilities` H1:

```markdown
> **[WCOSS]** `prep_step`, `startmsg`, `postmsg`, `err_chk`, `cpreq`, `compath.py`,
> `mail.py`, and `getsystem` are `prod_util` executables that exist only in the NCO
> production environment.
>
> **[portable]** The principles they encode apply anywhere: copy inputs into a scratch
> working directory before running, verify that every file copy succeeded, wrap each
> executable so a nonzero exit becomes a `FATAL ERROR:` and a clean job failure, and log
> a start time and progress messages to a log file (upstream notes `startmsg`/`postmsg`
> are no longer required in operations).
```

Append:

```markdown

## Review checklist

- **[WCOSS]** Call `prep_step` before each executable that reads `FORTn` units, and `err_chk`
  after each executable to trap a nonzero exit.
- **[WCOSS]** Use `cpreq` rather than `cp` for file copies so a failed copy is fatal.
- **[WCOSS]** Use `compath.py` to resolve COM paths and `mail.py` for notifications instead of
  hardcoding paths or calling `mail` directly.
- **[portable]** Every external command's exit status is checked; failures are never silently
  swallowed.
```

- [ ] **Step 4: `date-and-grib-utilities.md` — banner and checklist**

Insert after the `# Date and GRIB Utilities` H1:

```markdown
> **[WCOSS]** `finddate.sh`, `ndate`, and `setpdy.sh` come from the `prod_util` module; the
> GRIB tools come from `grib_util` and `wgrib2`. These are NCO production utilities. The
> portable principle: never compute date arithmetic or parse GRIB inline — call the
> documented utility so behavior is identical across jobs and correct at year boundaries.
```

Append:

```markdown

## Review checklist

- **[WCOSS]** Use `finddate.sh`, `ndate`, and `setpdy.sh` for date arithmetic; do not hand-roll
  date math that breaks when crossing into a new year.
- **[WCOSS]** Use `wgrib2` (or the approved GRIB utility) for GRIB inspection and subsetting
  rather than ad-hoc parsing.
```

- [ ] **Step 5: `dataflow.md` — banner and checklist**

Insert after the `# Dataflow` H1:

```markdown
> **[WCOSS]** DBNet (`dbn_alert`, `$DBNROOT`, `$SENDDBN`) is the WCOSS dissemination
> mechanism and has no RDHPCS or research equivalent. Do not block a research script for
> missing DBNet calls; the portable idea is to signal product availability to downstream
> consumers explicitly.
```

Append:

```markdown

## Review checklist

- **[WCOSS]** Every `dbn_alert` is wrapped in a check that `$SENDDBN` (or `$SENDDBN_NTC` for
  WMO-header products) is set to `YES`.
- **[WCOSS]** The alert names the model type, subtype, job, and full file path, for example
  `$DBNROOT/bin/dbn_alert MODEL PMB_GB2 $job $COMOUT/$outputfile`.
- **[WCOSS]** The NCO Dataflow Team maintains DBNet; coordinate any new or changed alert
  with them so products keep flowing to all external customers.
```

- [ ] **Step 6: `code-delivery.md` — banner, Table 7 note, checklist**

Insert after the `# Code Delivery and Vertical Structure` H1:

```markdown
> **[WCOSS]** The branch and tag naming (`release/vX.Y`, `bugfix/…`, `hotfix/…`,
> `vX.Y-rc<#>`), the Lmod modulefiles, and the sorc/exec/parm/fix/ush/jobs vertical
> structure are the NCO delivery contract reviewed at hand-off.
```

Then insert this provenance note immediately **before** the line `**Table 5: Structure of COM directories**` — the upstream prose references a Table 7 that is never defined, so the gap is documented rather than filled:

```markdown
> **Upstream note:** the source prose ("Table 5 (below), Table 7, Table 8, and Table 9…")
> references a **Table 7** that the upstream document never defines. Tables 1–6, 8, and 9 are
> present; Table 7 is a gap in the source, preserved here rather than reconstructed.
```

Append:

```markdown

## Review checklist

- **[WCOSS]** Releases use `release/vX.Y`; bug fixes use `bugfix/<short_description>`;
  emergency fixes use `hotfix/<short_description>`; production tags use `vX.Y.Z` and
  release-candidate tags use `vX.Y-rc<#>`, with release-candidate numbering starting at 0.
- **[WCOSS]** Every delivery ships a build script and, optionally, a modulefile that pin the
  compiler and library versions; the modulefile and makefile must not reference unused
  software or libraries.
- **[WCOSS]** All modulefiles are Lmod/Lua format, and a modulefile must not create symbolic
  links to external resources (e.g. to absolute paths).
- **[WCOSS]** The package follows the vertical structure (sorc/exec/parm/fix/ush/jobs per
  Table 3), and no pre-built executables or libraries are delivered to IDSB — the SPA builds
  all code before production.
```

- [ ] **Step 7: `examples.md` — banner and checklist**

Insert after the `# Workflow Examples and Tables` H1:

```markdown
> **[WCOSS]** These are worked examples for job `jpmb_forecast` on WCOSS (version file,
> ecFlow job card, `prod_envir` module, `J-job`, `ex-script`, build readme and script,
> modulefile, makefile) plus the Appendix B directory tables. Read them as templates for the
> shape of a compliant deliverable, not as values to copy verbatim onto another system.
```

Append:

```markdown

## Review checklist

- **[WCOSS]** The version file records the package version, and each example names the model
  (`nco`) and run type (`pmb`) so it is traceable.
- **[WCOSS]** The job card sets PBS directives and exports the environment, then calls the
  `J-job`; the `J-job` sets location and temporal variables and calls the `ex-script`.
- **[WCOSS]** The `ex-script` stages inputs into `$DATA`, calls executables wrapped with
  `prep_step` and `err_chk`, and copies durable output to `$COMOUT`.
- **[WCOSS]** The makefile compiles using module-provided variables (`${G2_LIB4}`,
  `${W3NCO_LIB4}`, `${BACIO_LIB4}`, …) rather than hardcoded paths.
```

- [ ] **Step 8: Re-validate markdown hygiene on all nine files**

Run: `markdownlint --config .markdownlint.json skills/omd-standards/ee2-standards/references/*.md`
Expected: exit code 0, no output.

- [ ] **Step 9: Re-check residue and fence balance after the hand edits**

The hand edits in Steps 1–7 added blockquote banners, fenced the workflow diagram, and appended
checklists. Re-run the residue and fence check over all nine files:

```bash
python3 - <<'CHECK'
import pathlib
import re

RES = [r"``", r"\[#", r":ref:", r"^\.\. _", r"[\u201c\u201d\u2018\u2019]", r"`_",
       r"\.\. note::", r"csv-table", r"code-block", r"^\^+$"]
bad = 0
for path in sorted(pathlib.Path("skills/omd-standards/ee2-standards/references").glob("*.md")):
    inf = False
    for i, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
        if line.lstrip().startswith("```"):
            inf = not inf
            continue
        if inf:
            continue
        for pat in RES:
            if re.search(pat, line):
                print("RESIDUE", path.name, i, pat, repr(line[:60]))
                bad += 1
    if path.read_text(encoding="utf-8").count("```") % 2:
        print("UNBALANCED FENCE", path.name)
        bad += 1
print("residue/fence issues:", bad)
CHECK
```

Expected: `residue/fence issues: 0`. Fencing the workflow diagram adds one balanced pair of
fences; the appended checklists contain no RST markup.

- [ ] **Step 10: Commit**

```bash
git add skills/omd-standards/ee2-standards/references/
git commit -m "feat(ee2): add WCOSS banners and checklists to single-nature references

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 6: `SKILL.md` body — routing rule and review gate

Adds the body that makes the skill usable: which reference to load for which task, the `[WCOSS]`/`[portable]` routing rule, and a 20-item highest-severity review gate. Every gate item cites the reference file it comes from.

**Files:**
- Modify: `skills/omd-standards/ee2-standards/SKILL.md` (append the body after the frontmatter)

**Interfaces:**
- Consumes: the tagged `references/` files from Tasks 3–5.
- Produces: `SKILL.md` with a `## Which reference to load` table, a `## Portability routing` section, a `## Review gate` numbered list, and a `## Scope` section. Task 7 does not parse SKILL.md — it reads `references/*.md` only.

- [ ] **Step 1: Append the body**

Append the following after the closing `---` of the frontmatter:

```markdown

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
```

- [ ] **Step 2: Confirm SKILL.md is within size budget**

```bash
python3 - <<'SIZE'
import pathlib
text = pathlib.Path("skills/omd-standards/ee2-standards/SKILL.md").read_text(encoding="utf-8")
print("lines:", len(text.splitlines()), "chars:", len(text))
SIZE
```

Expected: `lines: 83` and `chars: 5218` (the frontmatter is 19 lines / ~850 characters and the body is 64 lines / ~4368 characters). Both are far inside the validator's 500-line and 20,000-character body limits, so no `claude-code-body-500-lines` or `claude-code-body-compaction-budget` warning is raised.

- [ ] **Step 3: Validate the skill**

Run: `python3 tools/validate_skills.py --profile all --no-color --format text`
Expected: `ee2-standards` reported with 0 errors and no body-size warning.

- [ ] **Step 4: Commit**

```bash
git add skills/omd-standards/ee2-standards/SKILL.md
git commit -m "feat(ee2): add SKILL.md routing rule and review gate

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 7: Traceability test

Adds `tests/test_ee2_traceability.py`, the guard that no rule was invented and no RST markup leaked. The test must not touch the network, so the pinned RST is vendored under `tests/data/`.

**Files:**
- Create: `tests/data/ee-standards.rst` (vendored copy of the pinned upstream RST)
- Create: `tests/test_ee2_traceability.py`

**Interfaces:**
- Consumes: `tools/ee2_extract.py` (`SECTIONS`, `UPSTREAM_MD5`) and the nine `references/*.md` files from Tasks 2–5.
- Produces: a `unittest` module discovered by `tools/run_tests.py` (which globs `test_*.py`).

- [ ] **Step 1: Vendor the pinned RST for offline tests**

The test suite must not touch the network, so the pinned document is copied into `tests/data/`.
Re-fetch it from the same URL Task 2 used (rather than relying on `/tmp` surviving):

```bash
mkdir -p tests/data
curl -fsSL https://raw.githubusercontent.com/NCO-HPC/nws-hpc-standards/develop/docs/standards.rst -o tests/data/ee-standards.rst
md5 -q tests/data/ee-standards.rst
```

Expected: `699ca1c4ecb6e6ef6c4fbc4cd3112592`. If the digest differs, upstream moved —
stop and re-run Task 2 against the new digest before continuing, and update `UPSTREAM_MD5`
in `tools/ee2_extract.py`.

- [ ] **Step 2: Write the test**

Create `tests/test_ee2_traceability.py` with exactly this content:

```python
"""Guard the EE2 skill against invented rules and leaked RST markup.

Two directions are checked for every curated probe:
  * upstream -> file: the probe text exists in the pinned standards.rst, so the rule
    was not fabricated;
  * file -> upstream: the probe text exists in the reference file, so the vendoring
    actually carried the rule through.
Bolded rule headings in references/*.md are extracted and checked the same way.
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
            raise unittest.SkipTest("vendored ee-standards.rst is missing")
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
        untagged = re.findall(r"^\* \*\*[^*]+\*\*$", section_a, re.M)
        self.assertEqual(untagged, [], f"untagged section-A rules: {untagged}")

    def test_no_rst_residue_outside_fences(self):
        for path in sorted(REF_DIR.glob("*.md")):
            prose = strip_code_fences(path.read_text(encoding="utf-8"))
            for pattern in RESIDUE:
                self.assertIsNone(re.search(pattern, prose),
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


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run the test to verify it passes**

Run: `python3 -m unittest tests.test_ee2_traceability -v`
Expected: 11 tests, all PASS. If `test_curated_probes_trace_to_upstream` fails, the probe text was mistyped — correct the probe to match upstream wording, never edit the reference file to match a wrong probe.

These assertions were simulated against the pinned RST and the generated reference files before the plan was written, so a correctly implemented task should pass on the first run: 13 rule headings trace from `standards.md`, 57 probes trace in both directions, no residue patterns match outside fences, all fences balance, and the upstream table set is exactly `{1,2,3,4,5,6,8,9}` with `Table 7` referenced in prose only.

- [ ] **Step 4: Prove the test actually fails on a violation**

```bash
cp skills/omd-standards/ee2-standards/references/standards.md /tmp/std.bak
python3 - <<'BREAK'
import pathlib
p = pathlib.Path("skills/omd-standards/ee2-standards/references/standards.md")
p.write_text(p.read_text(encoding="utf-8") + "\n* **Rules about quantum flux**\n", encoding="utf-8")
BREAK
python3 -m unittest tests.test_ee2_traceability 2>&1 | tail -5
```
Expected: a FAILURE naming `invented rule heading in standards.md: 'Rules about quantum flux'`. Then restore:

```bash
cp /tmp/std.bak skills/omd-standards/ee2-standards/references/standards.md
python3 -m unittest tests.test_ee2_traceability 2>&1 | tail -3
```
Expected: `OK`.

- [ ] **Step 5: Run the full suite**

Run: `python3 tools/run_tests.py`
Expected: all suites pass, including `test_ee2_traceability`.

- [ ] **Step 6: Commit**

```bash
git add tests/data/ee-standards.rst tests/test_ee2_traceability.py
git commit -m "test(ee2): add traceability guard for vendored standards

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 8: Repo integration — instructions pointer, CONTRIBUTING, NOTICE, README

Wires the skill into the catalog. The `.github/instructions/` edit is the only markdownlint-enforced change in this task.

**Files:**
- Modify: `.github/instructions/code-review-generic.instructions.md` (insert before `## Review Checklist`, currently line 1182)
- Modify: `CONTRIBUTING.md` (add the Standards family bullet in "Where to Add Your Skill", ~line 20)
- Modify: `NOTICE` (append an `omd-standards` entry to two blocks)
- Modify: `README.md` (add the generated tree line)

**Interfaces:**
- Consumes: the committed skill from Tasks 1–7.
- Produces: `make policy` green, with the README tree line `│   ├── omd-standards/  # ee2-standards (1)`.

- [ ] **Step 1: Add the EE2 pointer to the review instructions**

In `.github/instructions/code-review-generic.instructions.md`, immediately before the line `## Review Checklist`, insert:

```markdown
## Operational Compliance (NCO EE2)

When the target is WCOSS or an NCO delivery, apply the NCO Environmental Equivalence
(EE2) standards through the `ee2-standards` skill and its per-file review checklists.

- **EE2 overrides style preferences.** Where a formatting or structural choice conflicts
  with an EE2 rule — message prefixes, restart, cleanup, module-driven builds, branch
  naming — EE2 wins for operational code.
- **Scope the advice.** EE2 rules tagged **[WCOSS]** (`$COMOUT`, `prep_step`, PBS
  directives, `dbn_alert`) do not apply to RDHPCS, workstation, or research-only code.
  Applying them there produces actively wrong advice. Review those targets against the
  **[portable]** subset only, and say so.

```

- [ ] **Step 2: Add the Standards family line to CONTRIBUTING**

In `CONTRIBUTING.md`, after the **Literature (1):** bullet, add:

```markdown
- **Standards (1):** `skills/omd-standards/` for operational production standards
  (`ee2-standards` — NCO Environmental Equivalence)
```

- [ ] **Step 3: Append the NOTICE provenance entries**

In `NOTICE`, inside the "Known subtrees with separate licensing at the time of this writing:"
list, after the `skills/literature-search/` block, add this entry using the same indentation
as its neighbours (two spaces, then a 34-column text column):

```
  skills/omd-standards/         ee2-standards skill vendoring the NCO Environmental
                                Equivalence (EE2) production standards from
                                NCO-HPC/nws-hpc-standards (ee-docs 11.0.0). U.S.
                                Government work; not Apache-2.0. See
                                skills/omd-standards/ATTRIBUTION.md.
```

And inside the "Upstream provenance" block, after the Genesis Skills paragraph, add:

```
  `skills/omd-standards/ee2-standards` reference files are vendored from the NCO
  Environmental Equivalence standards,
  <https://github.com/NCO-HPC/nws-hpc-standards> (ee-docs 11.0.0), a U.S. Government
  work. The vendored text preserves upstream wording, including known source defects,
  and is regenerated by `tools/ee2_extract.py`; see
  `skills/omd-standards/ATTRIBUTION.md` for the re-sync procedure.
```

- [ ] **Step 4: Add the README tree line**

`tools/repo_inventory.py` sorts families case-insensitively, so `omd-standards` lands between
`literature-search` and `prompt-optimizer`. `prompt-optimizer` still sorts last and keeps the
`└──` branch — there is no branch flip. In `README.md`, change:

```
│   ├── literature-search/SKILL.md
│   └── prompt-optimizer/SKILL.md
```

to:

```
│   ├── literature-search/SKILL.md
│   ├── omd-standards/  # ee2-standards (1)
│   └── prompt-optimizer/SKILL.md
```

- [ ] **Step 5: Verify the README line matches the generator**

```bash
python3 - <<'TREE'
import pathlib
import sys

sys.path.insert(0, "tools")
from repo_inventory import build_readme_tree_lines

for line in build_readme_tree_lines(pathlib.Path(".")):
    if "literature" in line or "omd-standards" in line or "prompt-optimizer" in line:
        print(line)
TREE
```

Expected output, matching the README edit byte-for-byte:

```
│   ├── literature-search/SKILL.md
│   ├── omd-standards/  # ee2-standards (1)
│   └── prompt-optimizer/SKILL.md
```

- [ ] **Step 6: Run policy validation**

Run: `python3 tools/validate_repo_policy.py`
Expected: `repo policy: OK`.

- [ ] **Step 7: Run markdownlint on the enforced files**

`.pre-commit-config.yaml` runs `markdownlint --config .markdownlint.json` only on
`README.md`, `CONTRIBUTING.md`, `docs/getting_started.md`, and `.github/instructions/*.md`.
`NOTICE` is not in that list, so do not pass it to markdownlint.

```bash
markdownlint --config .markdownlint.json README.md CONTRIBUTING.md docs/getting_started.md .github/instructions/code-review-generic.instructions.md
echo "exit=$?"
```

Expected: `exit=0` with no output. All four files are clean before this task, so any error
here was introduced by the Task 8 Steps 1–4 edits — usually a missing blank line around the
inserted heading.

- [ ] **Step 8: Commit**

```bash
git add .github/instructions/code-review-generic.instructions.md CONTRIBUTING.md NOTICE README.md
git commit -m "feat(ee2): wire ee2-standards into review instructions, contributing, notice, readme

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 9: End-to-end verification

Proves the skill passes the repo's own gates.

**Files:**
- Test: `make verify-new-skill`

**Interfaces:**
- Consumes: everything from Tasks 1–8.
- Produces: a green `verify-new-skill`. Nothing new is committed unless a fix is required.

- [ ] **Step 1: Run the full validation gate**

```bash
export PATH="/opt/homebrew/Caskroom/miniforge/base/bin:$PATH"
make verify-new-skill
```

Expected: all four stages pass — `validate_skills.py` (0 errors), `policy` (`repo policy: OK`), `test` (all suites green, including `test_ee2_traceability`), and `lint` (`compileall` clean; pre-commit markdownlint clean on the `.github/instructions/` edit).

- [ ] **Step 2: Fix and re-run if any stage fails**

Known causes and remedies:
- `PyYAML is required` → the PATH export in Step 1 was skipped. Re-export and re-run.
- markdownlint error on `.github/instructions/...` → the inserted section needs a blank line before the following `## Review Checklist` heading. Add it.
- policy tree mismatch → the README line does not match `build_readme_tree_lines`. Re-copy from Task 8 Step 5 output.
- traceability failure → a tagged heading or probe drifted from upstream. Re-check against `tests/data/ee-standards.rst`; never edit a probe just to force a pass.

- [ ] **Step 3: Confirm the working tree is clean**

Run: `git status --short`
Expected: no output. If Step 2 required a fix, commit it:

```bash
git add -A
git commit -m "fix(ee2): resolve verify-new-skill findings

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

- [ ] **Step 4: Manual spot-check (spec §10, item 7)**

Open `skills/omd-standards/ee2-standards/SKILL.md` and confirm:
- the routing rule explicitly requires **stating** when only the [portable] subset was applied;
- no `[WCOSS]`-only rule is presented as universal;
- every review-gate item cites a reference file;
- no file under `references/` mentions the `omd` MCP or instructs the reader to call it.

- [ ] **Step 5: Confirm the spec's validation list is satisfied**

| Spec §10 gate | Where satisfied |
|---|---|
| 1. `validate_skills.py --profile all` → 0 errors | Task 9 Step 1 |
| 2. `validate_repo_policy.py` → OK with the tree line | Task 8 Steps 5–6 |
| 3. `run_tests.py` → all pass | Task 7 Step 5; Task 9 Step 1 |
| 4. `make verify-new-skill` → green | Task 9 Step 1 |
| 5. Traceability check | Task 7 |
| 6. Fence balance and markdown hygiene | Task 2 Steps 6–7; Tasks 3–5; Task 7 |
| 7. Manual portability and routing review | Task 9 Step 4 |
