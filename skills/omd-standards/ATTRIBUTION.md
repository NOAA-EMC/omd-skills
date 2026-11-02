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
