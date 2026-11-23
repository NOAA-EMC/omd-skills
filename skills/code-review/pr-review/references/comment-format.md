# Review Comment Format and Template

One comment, one defect, one proposed action. The template is fixed so that a
reader scanning ten comments can find severity, location, proof, and the fix
without re-reading any of them.

## Template

````markdown
**<badge> [Category]: Brief, specific title**

2-5 sentences of prose: what the code does, why that is wrong or risky, and the
concrete consequence (a crash, a silent skip, a nondeterministic restart, a
broken downstream consumer). Name the file and line, or the symbol, in the prose.

**Suggested fix:**
The smallest change that resolves the defect, in prose or one short code excerpt.

```suggestion
replacement lines only -- at most 15 lines
```

**Test:**
The command, test name, or input that proves the fix works and would have caught
the defect. If none exists, say what test must be added and where.
````

`**Reference:**` may follow `**Test:**` when the rule comes from an external
document (a standard, an upstream manual, an issue). Do not repeat it for every
comment in the same file.

## Rules

1. **Badge and priority.** Use the three house priorities:
   `CRITICAL` (block merge, U+1F534), `IMPORTANT` (needs discussion, U+1F7E1),
   `SUGGESTION` (non-blocking, U+1F7E2). The builder appends the badge and the
   word only for `CRITICAL` and `SUGGESTION`; `IMPORTANT` (the default) keeps the
   title line clean:

   ```text
   **[Correctness]: Guard returns before deallocate**   (IMPORTANT, default)
   **[Correctness]: Guard returns before deallocate** (🔴 CRITICAL)   (blocking)
   ```

   `priority` must be one of the three; the builder rejects others so an urgent
   comment cannot hide behind a made-up label.
2. **Category is one of the review categories** listed in
   `references/review-checks.md` (`Security`, `Correctness`, `Memory`,
   `Numerics`, `Concurrency`, `Portability`, `Reproducibility`, `Silent failure`,
   `False confidence`, `API break`, `Test gap`, `Standards`, `Docs`, `Style`).
   Pick the one a reader would search for; if two apply, split into two comments.
3. **Title states the defect, not the location.** "Missing error check after
  MPI_Allw" is a title; "src/comm.F90 line 88 is wrong" is not. Lower-case after
   the colon is fine; no trailing period (the builder strips it).
4. **Prose is 2-5 sentences** and contains no code fence. Long reasoning belongs
   in the review body, not in an inline comment. One sentence that only says
   "this looks wrong" is not a comment: cite the failing consequence.
5. **`**Suggested fix:**` is required** unless the finding is a question. A
   question is written as `**[Standards]: Is the restart frequency configurable
   here?**` with the prose stating what the reviewer could not determine, and may
   omit the fix; the builder flags it (`--require-fix` makes that fatal).
6. **`**Test:**` is always required.** "No test needed" is not an acceptable
   value; name the command, or name the test to add.
7. **`suggestion` blocks**: at most one per comment, at most 15 lines
   (`--max-suggestion` to change the budget), replacement lines only, no fence
   inside it, and only on `side=RIGHT` lines. A fix longer than the budget is
   described in `**Suggested fix:**` prose with the file/function named, not
   squeezed into a fence. The builder never emits a fenced `suggestion` longer
   than the budget -- it drops it and raises `suggestion-length`, because a
   comment whose suggestion cannot be applied is worse than one that has none.
8. **Never two comments about one defect.** If the same root cause shows up in
   five places, comment once at the shared site (or the first), list the other
   locations in the prose, and let the author fix them together.
9. **Tone.** Imperative, specific, impersonal. "Return `ier` here so the caller
   can detect the failed read" rather than "you forgot to handle the error".
   Acknowledge deliberate design when it is visible; do not pad praise.

## Review body (summary)

The optional `body` of the review is a short paragraph plus a list of what was
examined and what was not:

```markdown
Reviewed `baseRefOid..headRefOid` (see `merge-base` note where the base had moved).
Checked: build files and flags, the two changed couplers, the CTest registration,
and whether every green check ran the tests it claims.
Not covered: the ensemble restart path (no reproducible input in the checkout).
N comments: a CRITICAL reduce-order issue, two IMPORTANT gaps, two SUGGESTIONs.
```

## Structured findings input

### Which diff the anchors are validated against

Anchor checks need the diff of the pinned range. Three ways to supply it, most
explicit first:

```bash
# (a) from the collector directory -- the pinned range, exactly as stage 1 recorded it
build_review_payload.py --findings review/findings.json \
  --diff review/diff.pinned.patch --head-ref-oid "$HEAD_OID" --out review/review_payload.json

# (b) from a clone that has both objects: the builder runs the range itself
#     (--cwd points at that working tree)
build_review_payload.py --findings review/findings.json \
  --base-ref-oid "$MERGE_BASE" --head-ref-oid "$HEAD_OID" --cwd "$CLONE" --out ...

# (c) from anywhere else: give the PR number and let gh read the revisions
build_review_payload.py --findings review/findings.json --pr 104 --repo NOAA-EMC/omd-skills --out ...
```

(c) is the least pinned of the three: `gh pr diff` returns the *current* diff, so
the builder prints a note saying the local range was unavailable and the pin
should be re-checked before posting. Never let a payload be built from a diff that
is not the head you intend to comment on -- that is how anchors drift onto the
wrong lines.

`scripts/build_review_payload.py` reads a findings file and assembles bodies, so
hand-formatting mistakes cannot reach GitHub:

```json
{
  "body": "Reviewed 12 commits ... see details below.",
  "comments": [
    {
      "path": "src/comm.F90",
      "line": 118,
      "priority": "CRITICAL",
      "category": "Correctness",
      "title": "Exact floating-point comparison in the convergence check",
      "prose": [
        "The check compares the residual with `== 0.0`, which will basically never hold.",
        "With a different reduction order the value differs between runs, so the loop exits at `max_iter`."
      ],
      "fix": "Compare against a documented tolerance and guard for NaN first.",
      "suggestion": "      if (residual <= tol) exit",
      "test": "ctest -R convergence --output-on-failure",
      "reference": "ISO/IEC 10967 numerics"
    }
  ]
}
```

Alternatively a finished body may be supplied as `"body"` on the comment; the
builder then only checks the template (`body-header`, `suggestion-length`,
`multiple-suggestions`) instead of generating it.
