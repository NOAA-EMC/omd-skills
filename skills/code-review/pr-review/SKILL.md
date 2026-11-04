---
name: pr-review
description: >-
  End-to-end pull request review on pinned revisions. Use when reviewing a PR,
  re-reviewing after a force push, triaging submitted and pending comments as
  valid, false positive, outdated or partially valid, checking CI for false
  confidence (CTest tests gated on if(EXISTS ...), unrun hooks), or publishing
  findings as a PENDING draft review. Triggers: "review this PR", "did they fix
  the comments", "CI green but tests did not run".
metadata:
  version: "1.0"
  domain: code-review
  as_of: "2026-11-04"
  source: https://docs.github.com/en/rest/pulls/reviews
compatibility: >
  Requires an authenticated gh (2.101.0 and jq 1.7 were used to verify this
  skill; no older gh was tested), git, python3, and bash 3.2+. GitHub Cloud API
  only: GitHub Enterprise Server paths and media types differ. Read-only until
  the final publish step, which creates a draft review.
allowed-tools: Read Grep Glob Bash(gh:*) Bash(git:*) Bash(python3:*) Bash(jq:*)
---

# Pull Request Code Review

Review one pull request from a pinned revision pair to a pending review, so that
the diff, the CI evidence, the earlier comments, and every anchor describe the
same code. Comments are always prepared as a `PENDING` draft: the reviewer, not
the tool, decides when the verdict is submitted.

## Workflow

| Stage | Do this | Reference |
|---|---|---|
| 1. Pin | Capture `baseRefOid`/`headRefOid`, fetch both objects, collect diff, comments, CI runs in one `review/` directory | `references/revision-anchoring.md` |
| 2. Group | Partition changed paths into logical groups; read the full post-change files, not hunks | `references/revision-anchoring.md` |
| 3. Review | Apply the language review rules, plus domain gates for build, tests, and operations | `references/review-checks.md` |
| 4. Triage | Judge earlier submitted and pending comments with evidence-based verdicts | `references/comment-triage.md` |
| 5. CI gate | Prove each green check actually ran the tests it claims | `references/ci-false-confidence.md` |
| 6. Compose | Build `review_payload.json` with `scripts/build_review_payload.py` | `references/comment-format.md` |
| 7. Publish | Create the `PENDING` review with `scripts/post_pending_review.sh`, which re-checks the pin | `references/pending-review-api.md` |

## Non-negotiables

1. **Pin before reading.** Every `gh` lookup after stage 1 uses SHAs, never a
   branch name. Re-read `headRefOid` immediately before posting (stage 7); if it
   moved, re-anchor or the comments land on the wrong lines.
2. **Pending by construction.** `review_payload.json` must never contain an
   `"event"` key. A review POST without `event` creates a `PENDING` draft; with
   `event` it publishes a verdict, notifies the author, and changes
   `reviewDecision`. `scripts/build_review_payload.py --check` and
   `scripts/post_pending_review.sh` both enforce this.
3. **Evidence or it is not a comment.** A finding cites the file and line, the
   command or code path that demonstrates it, and the test that will prove the
   fix. Speculation is labelled as a question, not a defect.
4. **Verdicts for old comments come from the current tree.** Confirm or reverse
   with code, the diff of the fix commit, or a command -- never with the commit
   message alone.
5. **Nothing is submitted, approved, requested, merged, or resolved** by this
   skill. Draft threads stay unresolved; resolution belongs to the author.

## Stage commands

Stage 1 collects everything once (read-only; safe to re-run):

```bash
skills/code-review/pr-review/scripts/collect_review_context.sh 104 NOAA-EMC/omd-skills review
jq -r '[.baseRefOid, .headRefOid] | @tsv' review/plan.json
```

Stage 6 turns structured findings into a payload, and stage 7 publishes the
draft. Both take the pinned SHAs explicitly so a stale payload cannot post:

```bash
python3 skills/code-review/pr-review/scripts/build_review_payload.py \
  --findings review/findings.json --diff review/diff.pinned.patch \
  --head-ref-oid <HEAD_SHA> --out review/review_payload.json

skills/code-review/pr-review/scripts/post_pending_review.sh 104 \
  review/review_payload.json NOAA-EMC/omd-skills
```

That script is the only publishing path this skill uses. It re-reads
`headRefOid`, refuses a payload pinned to an older commit, refuses a payload
that carries `"event"` or has no comments, refreshes an existing `PENDING`
review instead of duplicating it, and asserts the created state is `PENDING`
before reporting the review id. The equivalent manual call, shown for
transparency only, is:

```bash
gh api "repos/NOAA-EMC/omd-skills/pulls/104/reviews" --method POST \
  --input review/review_payload.json --jq '{id, state, html_url}'
```

## Finding categories

Use the categories defined in `references/review-checks.md` (`Security`,
`Correctness`, `Memory`, `Numerics`, `Concurrency`, `Portability`,
`Reproducibility`, `Silent failure`, `False confidence`, `API break`,
`Test gap`, `Standards`, `Docs`, `Style`). One category per comment; if two
apply, split the comment.
