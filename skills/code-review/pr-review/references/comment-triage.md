# Triage of Existing Review Comments

Before adding findings, work out what has already been said, by whom, and what
the current code actually does about it. A re-review generates more noise than
value when previous comments are not accounted for.

## Fetch state, not vibes

`scripts/collect_review_context.sh` writes both views into `review/`:

- `threads.json` -- GraphQL `reviewThreads`: `isResolved`, `isOutdated`, the
  thread's `path`/`line`/`originalLine`, and each comment's `databaseId`,
  `outdated`, and `body`. This is the only view that knows about resolution.
- `submitted.json` -- REST `pulls/{n}/comments`: `id`, `user`, `path`, `line`,
  `original_line`, `side`, `subject_type`, `commit_id`, `original_commit_id`,
  `in_reply_to_id`, `pull_request_review_id`, `body`, timestamps. This is the
  anchor-grade view for replies.
- `reviews.json` -- every review with its `state`, including the `PENDING` ones;
  `.pending_comments` is the flattened draft comment list. Only the author of a
  draft can see a pending review's comments; the REST list of review comments
  shows submitted comments plus your own drafts.

Compact views that are usually enough to triage from:

```bash
jq -r '.data.node.reviewThreads.nodes[] | [.isResolved, .isOutdated, .path, .line,
  (.comments.nodes | length)] | @tsv' review/threads.json
jq -r '.[] | [.id, .user, .path, .line, .commit_id[0:8]] | @tsv' review/submitted.json
jq '{viewer, reviews: [.reviews[] | {author, state, comments}]}' review/reviews.json
```

## Assign a verdict to every prior comment

Judge the code at the pinned head, not the conversation. Record one verdict per
comment (or per thread, when the thread is one point made repeatedly):

| Verdict | Meaning | Evidence required |
|---|---|---|
| `[VALID]` | still applies; the code is unchanged or the defect was moved, not fixed | cite the current file/line and what is still wrong |
| `[INVALID / FALSE POSITIVE]` | never applied; the reviewer misread the contract, the language, or the scope | cite the code or document that proves it, stated without sarcasm |
| `[OUTDATED]` | the concern was real, the current revision removed it | cite the fix (file/line or the commit that addressed it) |
| `[PARTIALLY VALID]` | the mechanism was right but the stated consequence or proposed fix was wrong, or only part of it was acted on | split into "what held" and "what did not"; state the remaining action |

Rules:

1. **Check the anchor before checking the claim.** If `commit_id` differs from the
   pinned head and the lines around `original_line` moved, re-locate the passage
   before judging it. A comment rendered grey as outdated may still be correct.
2. **A resolved thread is not proof of a fix.** Confirm `isResolved` against the
   code; if it was resolved as "will address in a follow-up", say so.
3. **Do not re-post a `[VALID]` finding silently.** Reply in the existing thread
   (`in_reply_to` the thread's last comment `id`) with the verdict and the current
   anchor. New comments are for new defects.
4. **One verdict per comment.** Multi-comment threads get one verdict reply that
   cites the thread, not a reply to each comment.
5. **Disagreement with a maintainer decision** is stated once, as a risk with a
   mitigation, then dropped; it is not escalated across revisions.

## Verdict reply format

Keep it three parts, and put the verdict first so it survives truncation:

```markdown
`[VALID]` still applies at `dd1bc8c` -- `src/comm.F90:118` guards with
`if (n == 0) return`, which leaves `alloc` allocated, so every subsequent call
re-enters with the previous buffer live. The fix commit moved the guard, it did
not release the memory.

**Test:** `ctest -R comm_leak --output-on-failure` under `-fsanitize=address`.
```

```markdown
`[INVALID / FALSE POSITIVE]` -- the `STOP 1` here is not a silent failure: the
subroutine is called only from `driver.F90:88`, which is the rank-0 path.
```

```markdown
`[OUTDATED]` -- fixed in `a1b2c3d` by the `close(status)` check now at
`src/io.f90:52`; the residual concern was raised separately at `src/io.f90:71`.
```

```markdown
`[PARTIALLY VALID]` -- the reduction-order concern is real and the header was
updated, but the requested regression test was not added, so the claim remains
unproven. Remaining action: add `tests/test_reduce_determinism.py`.
```

Do not invent `[WONTFIX]`, `[BYDESIGN]`, or a fifth label; `[INVALID / FALSE
POSITIVE]` and `[PARTIALLY VALID]` cover that ground, and extra labels make the
audit unsearchable.

## Resolving threads

Resolution is a **write action** and is not part of this skill's publish step.
Only the thread author, the comment author, or a user with write access may
resolve, and resolving someone else's `[VALID]` concern is how defects disappear.
If the reviewer explicitly asked for closure, use the GraphQL mutation and record
it in the review body:

```bash
gh api graphql -f threadId="$THREAD_NODE_ID" -f query='
mutation($threadId: ID!) {
  resolveReviewThread(input: {threadId: $threadId}) { thread { id isResolved } }
}'
```

## Building the audit into the review body

The pending review's `body` opens with the audit, so the author sees the state of
the conversation before the new comments:

```markdown
Re-review of `4added6..dd1bc8c` (previous head `9f3c1ab`).

Prior feedback: 7 comments in 5 threads -- 4 `[OUTDATED]`, 1 `[VALID]` (replied in
thread), 1 `[INVALID / FALSE POSITIVE]`, 1 `[PARTIALLY VALID]`.
New in this revision: 3 comments (1 `CRITICAL`).
Draft only -- nothing here is submitted.
```

## Reading a draft that has not been submitted yet

`GET .../pulls/{n}/comments` lists submitted comments only -- a draft's comments
are not there, and `GET /repos/{owner}/{repo}/pulls/comments/{id}` 404s for one.
Read them from their review instead:

```bash
gh api "$API/reviews/$REVIEW/comments" --paginate \
  --jq '.[] | {id, path, position, line, body: (.body[0:60])}'
```

Expect `line`, `side` and `subject_type` to be `null` until the review is
submitted; `position` (lines into the diff) is what GitHub records for a draft.
Treat those nulls as "not yet resolved to a file line", never as evidence that an
earlier comment was misplaced.
