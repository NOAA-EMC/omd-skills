# Review Checks and Finding Categories

This is the checklist applied in stage 3, and the source of the `category` values
used by `references/comment-format.md`. The per-language detail lives in
[.github/instructions/code-review-generic.instructions.md](../../../../.github/instructions/code-review-generic.instructions.md)
(installed as an editor rule); this file is what a reviewer applies to a whole
pull request, in order.

## Order of work

1. **Understand the intent** from the title, body, and linked issue. A diff cannot
   be judged against a goal that has not been stated; if the goal is unclear, that
   is a finding against the description, not the code.
2. **Map the change** into the logical groups of `references/revision-anchoring.md`
   and read the post-change version of every file in a group, together.
3. **Run the cheap gates** before reasoning about anything: the linters and tests
   the repository already declares (`shellcheck -x`, `ruff check`, the test runner,
   `python3 tools/validate_repo_policy.py` in this catalog). A finding the tooling
   would have caught is a finding about the tooling, not the code.
4. **Review correctness, then robustness, then clarity.** Never spend the review
   budget on style while a race condition is unexamined.

## Categories

| Category | Ask | Typical finding |
|---|---|---|
| `Security` | secrets, injection, path traversal, deserialisation, authz | hardcoded credential, unsanitised path into a shell command |
| `Correctness` | does the code do what the contract says | off-by-one, wrong operator, dropped status, inverted condition |
| `Memory` | allocation, ownership, bounds, lifetime | buffer written past its declared size, use-after-free, leak on the error path |
| `Numerics` | stability, precision, reproducibility | exact `==` on a float, missing NaN/Inf guard, division by a possible zero |
| `Concurrency` | MPI/OpenMP/thread safety, deadlock, determinism | unmatched non-blocking pair, collective inside a rank-conditional, reduction order dependence |
| `Portability` | toolchain and platform assumptions | vendor flag applied to the wrong compiler ID, a POSIX-only construct in a batch script |
| `Reproducibility` | determinism, seeds, ordering, provenance | unseeded RNG, directory iteration order leaking into output |
| `Silent failure` | can a failure be missed | swallowed exception, ignored exit status, a job that reports success on a failed run |
| `False confidence` | does a green result mean what it claims | gated test, `|| true`, hooks only run manually (see `references/ci-false-confidence.md`) |
| `API break` | downstream compatibility | changed module signature, removed public symbol, changed output file schema or variable names |
| `Test gap` | is the new behaviour actually asserted | test exists but only exercises the old path; assertion that cannot fail |
| `Standards` | documented operational or repository rules | EE2 violations, unapproved output path, missing `DOC_BLOCK` |
| `Docs` | whether claims still match behaviour | README option list missing the new flag, stale default |
| `Style` | readability and convention only | naming, nesting depth, dead code |

`Data loss` and `Breaking changes` from the passive instructions are covered by
`Correctness` plus `API break`; do not invent a fifth severity level.

## Domain gates worth loading inside this catalog

Load the sibling skill when the diff touches that area, instead of reviewing it
from memory:

- build system, `find_package`, flags, test registration:
  `skills/omd-standards/cmake-hpc/` (its `scripts/check_cmake_antipatterns.py` is a
  review gate you can run on the tree under review);
- job scripts, partition and queue names, WCOSS or RDHPCS specifics:
  `skills/hpc-skills/`;
- NCO EE2 production standards (paths, restart behaviour, background jobs,
  naming): `skills/omd-standards/ee2-standards/`;
- PR or issue text and templates: `skills/github-issues/`, `skills/github-release/`.

## Numeric and parallel review rules that catch most defects

- **Guard the denominators.** Any division by a computed value, including inside
  a diagnostic, needs an explicit zero or near-zero test and a documented result.
- **No exact float equality**, and no float equality hidden inside a `where` or a
  mask.
- **Collectives are control flow.** A collective inside a conditional must have a
  condition that is identical on every rank of the communicator; otherwise
  document and test the sub-communicator.
- **Non-blocking pairs must complete.** Every `MPI_Isend`/`MPI_Irecv` has a
  matching wait, on all exits including the error path.
- **Never gather a full field to rank 0** for processing or output; a rank-0
  aggregation of a distributed state in a PR is a design finding, not a style one.
- **Reduce order is part of the result.** Any change that alters the order or the
  algorithm of a reduction must be justified by a reproducibility test, not only
  by a performance number.
- **I/O is checked or it did not happen.** NetCDF/PIO calls return status; a call
  whose status is discarded is `Silent failure`.
- **Random state is seeded, recorded, and reproducible** across rank counts.

## What not to raise

- Style the repository's own linter does not enforce and the diff did not worsen.
- Rewrite preferences presented as defects ("I would have used a class here").
- Findings about files outside the diff, unless the diff makes them wrong; then
  raise the consequence in the changed file and name the dependency.
- A test request for code that is deleted, generated, or a thin binding: say why
  instead.
- Duplicate comments. Grouping (stage 2) exists to prevent them; if two reviewers
  raised the same defect, reply to the earlier thread rather than posting again.
