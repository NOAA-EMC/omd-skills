# Agent Install Reference

`install.sh` places this catalog's skills **and** instruction files into a
project so local AI agents read them from the paths they already watch, and
records what it placed so a later run can refresh, protect your edits, or
remove it cleanly.

Run it from anywhere; it finds the catalog next to itself, so a single clone
can serve every project on the machine. No network access is used or needed
(the catalog travels with the tool once installed).

Without a clone, install the packaged CLI (self-contained wheel bundling the
same `install.sh` engine and catalog):

```bash
pipx install git+https://github.com/NOAA-EMC/omd-skills.git
# or: uv tool install --from git+https://github.com/NOAA-EMC/omd-skills.git omd-skills
# or: pip install git+https://github.com/NOAA-EMC/omd-skills.git
omd-skills --list
cd ~/my-project && omd-skills --agents all
```

`omd-skills` takes exactly the arguments of `install.sh` (plus `--version`);
flags, subcommands, exit codes, and the `.ompd/` record behave identically.
It requires `bash` at run time (Git Bash/WSL on Windows). Refreshing the
catalog means re-installing the package (`pipx upgrade omd-skills`), unlike
the clone workflow where `git pull` suffices — prefer a clone for active
development of the skills themselves.

## Requirements

- Bash 3.2 or newer (macOS default and AFT RHEL bash are both fine).
- Standard POSIX tools: `find`, `sed`, `awk`, `cp`, `ln`, `shasum` **or**
  `sha256sum`.
- Nothing else — no Python, no package installs, no agent CLI required.

## Usage

```bash
/path/to/omd-skills/install.sh [operations and flags]
```

| Flag | Meaning |
| --- | --- |
| `--agents <ids>` | Comma list of `claude`, `codex`, `opencode`, `gemini`, `cursor`, `copilot`, or `all`. Required with `--no-interactive`. |
| `--project <dir>` | Target project (default: current directory). |
| `--mode copy` | Snapshot the content into the project (safe if you will move or delete the clone later). |
| `--mode symlink` | Link into the catalog clone (default; live-updates as you `git pull`, but the clone must stay in place). |
| `--domains <csv>` / positional | Install only named domains (`hpc-skills`, `omd-standards`, …) or individual flat skills. `--list` shows names. |
| `--no-interactive` | Never prompt; refuse anything ambiguous instead. |
| `--uninstall` | Remove (or de-tag) everything previously installed for the selected agents. |
| `--list` | Print the installable catalog and exit. |

Exit codes: `0` success · `2` usage error · `3` refusal (collision, foreign
`.ompd`, your local edits were kept, install into the catalog clone itself) ·
`4` unexpected failure (partially-applied work is rolled back).

Interactive mode detects which agents a project already uses
(`.claude/`, `AGENTS.md`, `.cursor/`, …), proposes them, and waits for your
confirmation before writing anything.

## What Lands Where

| Agent | Skills | Instructions |
| --- | --- | --- |
| Claude Code | `.claude/skills/<skill>/` | Managed block in `CLAUDE.md` |
| Codex | `.agents/skills/<skill>/` | Managed block in `AGENTS.md` |
| OpenCode | `.agents/skills/<skill>/` (shared) | Managed block in `AGENTS.md` (shared) |
| Gemini CLI | `.agents/skills/<skill>/` (shared) | Managed block in `GEMINI.md` |
| Cursor | `.agents/skills/<skill>/` (shared) | `.cursor/rules/*.mdc` (translated `applyTo:` → `globs:`, `alwaysApply` set false) |
| Copilot | — (reads instructions only) | `.github/instructions/*.instructions.md` (byte-identical to the catalog) |

Skills from several clients share one path when the agent documentation agrees
on it (e.g. Codex, OpenCode, Gemini CLI, and Cursor all read
`.agents/skills/`); the install record keeps the list of agents per path, so an
uninstall for one client only strips that tag while the others still use it.

Domain-level license and attribution material (`LICENSE`, `NOTICE`,
`ATTRIBUTION.md`) is installed next to each skill in `copy` mode, so flattened
skills keep their provenance even inside your project.

## The Install Record: `.ompd/`

Installed projects get a small bookkeeping directory:

```
.ompd/
├── genesis.lock          # one JSON line per managed path (add to .gitignore)
└── genesis.lock.d/       # staged copies used for drift detection
```

It is purely local state; deleting it loses the ability to auto-update or
auto-uninstall, but nothing else. Add `.ompd/` to your project's `.gitignore`.

### Refresh rules

Re-run the same command any time (e.g. after `git pull` in the clone):

- Paths whose catalog content changed are rewritten.
- Unchanged paths are left untouched (`unchanged` in the summary).
- Paths **you edited in the project** are never silently clobbered:
  interactive mode asks per file (`y` replaces, `n` keeps your version and the
  installer exits `3`); `--no-interactive` always keeps your version.
- Skills that disappeared from the selected catalog scope are removed from the
  project — but only inside `--domains` scopes you asked about, and never a
  file you edited.

## Uninstall

```bash
install.sh --agents codex --uninstall        # just Codex's claim
install.sh --agents all --uninstall          # everything
```

- `copy` mode deletes skill directories only when the directory still matches
  what the installer wrote; foreign or hand-edited files inside make it keep
  the directory (with a warning) and drop the record entry.
- Managed blocks (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`) are stripped marker by
  marker; a host file that existed before install survives with your prose.
- Shared paths lose only the named agent's tag until no other agent references
  them.
- When the last entry goes, `.ompd/` is removed entirely.

## Coexistence and Collisions

If a destination path already exists in the project and is not owned by this
installer, the run **refuses** (exit `3`) before writing anything — your files
are never overwritten. Move or rename the conflicting entry (or choose another
agent set) and re-run.

Installing into the catalog clone itself is refused the same way. So is a
project with a `.ompd/` directory this installer did not create.

## Notes and Limitations

- `symlink` mode links into your clone: keep the clone where it is, or
  re-install with `copy` before deleting it.
- Copilot receives instruction files only; its skills story differs per
  client version and is intentionally out of scope for v1.
- Cursor rules are generated with `alwaysApply: false` so they act as
  suggested instructions on matching files, not forced context.
- The tool is offline by design: it reads only the catalog clone.
