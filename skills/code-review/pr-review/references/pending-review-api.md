# The Pending Review API

Everything about posting a draft review, and the asymmetry that makes it worth
spelling out: **creating** a review without an `event` is a draft, while
**submitting** it is a separate call that can never be undone quietly.

## Endpoints

Base path `repos/{owner}/{repo}/pulls/{pull_number}`. Verified against
[rest/pulls/reviews](https://docs.github.com/en/rest/pulls/reviews) and
[rest/pulls/comments](https://docs.github.com/en/rest/pulls/comments).

| Purpose | Method and path |
|---|---|
| List reviews (incl. `PENDING`) | `GET .../reviews` |
| Comments attached to one review, including a draft | `GET .../reviews/{review_id}/comments` |
| Create a review (draft when `event` is absent) | `POST .../reviews` |
| Update the pending review's summary body | `PUT .../reviews/{review_id}` (`body` required) |
| Delete a pending review | `DELETE .../reviews/{review_id}` |
| **Submit** a pending review | `POST .../reviews/{review_id}/events` (`event` required) |
| List submitted review comments | `GET .../comments` (`sort`, `since`, paginated) |
| Add one comment (needs its own `commit_id`) | `POST .../comments` |
| Reply to a comment | `POST .../comments` with `in_reply_to` |
| Edit a comment | `PATCH /repos/{owner}/{repo}/pulls/comments/{id}` |
| List *all* threads | GraphQL `reviewThreads` (no REST equivalent) |

Review `state` values: `PENDING`, `COMMENTED`, `APPROVED`, `CHANGES_REQUESTED`,
`DISMISSED`. A `PENDING` review has no `submitted_at`; it is visible only to its
author (list others' drafts through the UI as them, or read
`pullRequest.viewerLatestReview` in GraphQL).

## Why `event` must be absent

`POST .../reviews` documented behaviour: *"Pull request reviews created in the
PENDING state are not submitted and therefore do not include the `submitted_at`
property... To create a pending review, leave the `event` parameter blank."* With
`event` set, the same call publishes a verdict, notifies the author, and changes
`reviewDecision` -- a state change the repository may gate merges on.

So the payload never carries `event`, and the tool that writes it drops it with a
warning if a caller includes one. Publishing is always
`POST .../reviews/{review_id}/events`, an explicit human step.

## Payload shape

```json
{
  "commit_id": "<headRefOid>",
  "body": "Summary markdown.",
  "comments": [
    {"path": "src/comm.F90", "line": 118, "side": "RIGHT", "commit_id": "<headRefOid>", "body": "**[Correctness]: ...**"},
    {"path": "src/comm.F90", "start_line": 115, "start_side": "RIGHT", "line": 120, "side": "RIGHT", "body": "multi-line"},
    {"path": "docs/usage.md", "subject_type": "file", "body": "file-level comment"},
    {"path": "src/comm.F90", "in_reply_to": 1655724, "body": "reply in an existing thread"}
  ]
}
```

Reading a draft back (verified against GitHub Cloud on 2026-11-04, by posting a
one-comment draft and deleting it):

```json
{"id": 4474679661, "path": "tools/validate_skills.py", "position": 1,
 "line": null, "side": null, "subject_type": null, "commit_id": "dd1bc8c3…"}
```

`GET .../reviews/{review_id}/comments` reports the diff-relative `position` while
`line`, `side` and `subject_type` come back `null` -- they are filled in when the
review is submitted, so a `null` line on a draft is not a failed anchor. Do not
triage a draft with the flat `GET .../comments` stream either: pending comments
are absent from it (the global `GET /pulls/comments/{id}` even returns 404 for a
draft comment). Use the review-scoped call, as
`references/comment-triage.md` describes.

Field rules that matter in practice:

- **`commit_id` at the top level** pins every batch comment. Prefer the batch
  form: standalone `POST .../comments` requires its own `commit_id` per call, and
  an omitted or older SHA produces a comment that GitHub marks outdated.
- **`line` is the file line at that commit, not a diff offset.** `position`
  (lines into the diff) is documented as closing down in favour of `line`; this
  skill never emits `position`.
- **`side`** `RIGHT` for additions and context, `LEFT` for deletions. A `LEFT`
  anchor cannot carry a `suggestion` block. Multi-line comments need
  `start_line`/`start_side` plus `line`/`side` as the last line of the range.
- **`subject_type`** `line` (default) or `file`. A file-level comment carries no
  line coordinates.
- **`in_reply_to`** continues an existing thread; when present, the API ignores
  every field except `body`, so coordinates are not sent.
- Comments on `binary`, `unified`, `deletion`-only, or whitespace-invalid lines are
  rejected (422), as are suggestions that would not apply cleanly. Fix the anchor,
  or drop the `suggestion` half and keep the prose and `**Test:**` note.

## Posting and verifying: use the script

`scripts/post_pending_review.sh PR [payload.json] [OWNER/REPO]` is the publishing
step. Its output is the review id on stdout and the human-readable status on
stderr, so it can be captured:

```bash
review=$(skills/code-review/pr-review/scripts/post_pending_review.sh 104 \
           review/review_payload.json NOAA-EMC/omd-skills)
```

It runs the gates in this order and refuses to post if any fails:

1. no `event` key in the payload or in any comment (exit 1) -- and the comment
   array must be non-empty, since a review with no comments is a bare summary.
2. the live `headRefOid` must equal the payload `commit_id` (exit 1 with the two
   SHAs printed, so a stale payload cannot land comments on the wrong lines).
3. an existing `PENDING` review by the caller is refreshed rather than
   duplicated: the script `PUT`s the summary body, prints the number of comments
   that will *not* change, and shows the `DELETE` command to start over.

Only then does it `POST`, and it asserts `"state": "PENDING"` with
`"submitted_at": null` before reporting success. If the response says otherwise
the review was published anyway -- correct it in the UI rather than repeating the
call, which would create a second review.

The manual equivalent, kept here because the script is a convenience and the API
is the contract:

```bash
API="repos/$SCOPE/pulls/$PR"
LIVE=$(gh pr view "$PR" --repo "$SCOPE" --json headRefOid --jq .headRefOid)
PINNED=$(jq -r .commit_id review/review_payload.json)
[ "$LIVE" = "$PINNED" ] || { echo "STALE: re-anchor against $LIVE"; exit 1; }

gh api "$API/reviews" --method POST --input review/review_payload.json \
  --jq '{id, state, submitted_at, comments: (.comments | length)}'

# whose drafts already exist?
gh api "$API/reviews" --paginate \
  --jq '[.[] | select(.state == "PENDING") | {id, user: .user.login}]'
```

## Editing after a force push

A pending review survives a new push; its comments age out. Refresh the anchors
rather than leaving a draft full of greyed-out comments:

```bash
gh api "$API/reviews/$REVIEW/comments" --paginate \
  --jq '.[] | {id, path, line, original_line, commit_id, body: (.body[0:60])}'
gh api "repos/$SCOPE/pulls/comments/$COMMENT_ID" --method PATCH \
  -f body='Updated for dd12345: the guard is still missing at src/comm.F90:142.'
```

Or delete the draft and rebuild from the findings file against the new head:

```bash
gh api "$API/reviews/$REVIEW" --method DELETE
```

Deleting a *submitted* review is not available through the API; dismiss it
instead, and never dismiss someone else's review on their behalf.

## Thread resolution lives elsewhere

`isResolved`/`isOutdated` only exist in GraphQL (`reviewThreads`), and resolving a
thread is a separate mutation (`resolveReviewThread`). This skill reads thread
state for triage and never mutates it; draft threads are left unresolved for the
author to close.

## Limits and etiquette

- `GET` listings are paginated at 100 per page (`per_page` max 100), so always use
  `gh api --paginate`; a triage built on the first page looks like silence.
- Diff positions expire as soon as the head moves -- that is the whole argument for
  stage 1's pinned revisions and the pre-publish re-check.
- Creating or submitting a review **sends notifications**, and the docs warn about
  secondary rate limits on these endpoints. Read-only stages issue `GET` calls
  only; the `POST` is one deliberate human step using a checked payload.
