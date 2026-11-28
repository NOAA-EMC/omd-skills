# State Schema Version

**Schema-version check on resume.** There is **one** version number for
the whole skill. It appears in the root `SKILL.md` frontmatter (`metadata.version`) and in
all three state templates, and every copy always carries the same value.
The value is a quoted `"MAJOR.MINOR.PATCH"` string (for example `"6.0.0"`),
never a bare number:

| File | Template |
|------|----------|
| `.nsight-ai-port/config.json` | `assets/config-template.json` |
| `.nsight-ai-port/progress.json` | `assets/progress-template.json` |
| `.nsight-ai-port/skill_feedback.json` | `assets/skill_feedback-template.json` |

On resume, compare the `schema_version` in **each** existing state file
against its template as an exact string. If any differs — or a file has
no `schema_version`, or carries one that is not a `"MAJOR.MINOR.PATCH"`
string — the project was started under a different skill version.
**Warn the user** that behavior may be undefined, say which files
disagree and in which direction, and **ask whether to proceed** before
continuing. Do not silently migrate or overwrite a state file.

When you change the shape of any state file, bump `metadata.version` in the
frontmatter and `schema_version` in all three templates together. They
are one version, not three.
