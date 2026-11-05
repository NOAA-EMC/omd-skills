# Attribution

**Team:** OMD - Modeling Division

**Author:** Barry Baker (OMD)

## Pull request review workflow

The `pr-review` skill is original OMD authoring. It contains no vendored text;
its factual claims were checked against the references below at the time of
writing, and the scripts re-verify the mechanical parts at run time.

- GitHub REST - pull request reviews:
  <https://docs.github.com/en/rest/pulls/reviews>
- GitHub REST - pull request review comments:
  <https://docs.github.com/en/rest/pulls/comments>
- GitHub GraphQL - `PullRequestReviewThread`, `PullRequestReviewState`,
  `resolveReviewThread`: <https://docs.github.com/en/graphql>
- GitHub REST - check runs and workflow runs:
  <https://docs.github.com/en/rest/checks/runs>,
  <https://docs.github.com/en/rest/actions/workflow-runs>
- CTest manual (how tests are registered and filtered):
  <https://cmake.org/cmake/help/latest/manual/ctest.1.html>
- This repository's review conventions:
  [../../.github/instructions/code-review-generic.instructions.md](../../.github/instructions/code-review-generic.instructions.md)
  and [../omd-standards/ee2-standards](../omd-standards/ee2-standards/)

### What is this repository's own position

These are conventions OMD chose, not upstream GitHub or CMake policy:

- The verdict taxonomy (`[VALID]`, `[INVALID / FALSE POSITIVE]`, `[OUTDATED]`,
  `[PARTIALLY VALID]`) and the requirement to reply with the evaluation.
- Publishing only ever creates a **PENDING** draft review: `review_payload.json`
  omits `"event"`, and `scripts/post_pending_review.sh` refuses a payload that
  carries one, so a human always submits the verdict.
- The comment budget: a `**[Category]: [Title]**` header, 2-5 sentences of
  prose, `**Suggested fix:**`, `**Test:**`, and at most one `suggestion` block
  of 15 lines or fewer.
- Treating a test that can silently fail to run (`if(EXISTS ...)` gating, a
  `ctest` invocation with zero registered tests, an un-installed hook) as a
  review finding rather than a CI green.
- Anchoring findings to `merge-base..headRefOid` rather than to a branch name.

### Drift risks

GitHub can change defaults without a version bump. Re-check before trusting
these specifics:

- `position` on review comments is documented as being "closed down" in favour
  of `line`/`side`; the scripts use `line` and never emit `position`.
- A review body has no per-comment `commit_id`; the review-level pin applies to
  the whole batch.
- Reading a draft back: `GET .../reviews/{id}/comments` reports `position` with
  `line`/`side`/`subject_type` null until the review is submitted (observed
  2026-11-04 by posting and deleting a one-comment draft), and draft comments
  are absent from the flat `GET .../comments` stream.
- `GET .../pulls/{n}/reviews` returns `PENDING` reviews for the caller only, so
  "no drafts found" may mean "none are yours".
- GraphQL field names (`isOutdated`, `outdated`, `originalLine`) and the
  `PullRequest.diff too_large` threshold for very large diffs.
