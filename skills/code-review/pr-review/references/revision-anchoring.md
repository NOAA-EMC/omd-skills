# Revision Anchoring and Logical File Grouping

A review is only reproducible if it names the commits it looked at. Branch names
move: a force push between "read the diff" and "post the comment" silently
re-labels every line number, and a green CI badge can belong to a commit that no
longer exists.

## Stage 1: pin first, then read

Capture the pair before opening a single file, and never fetch by branch name
again:

```bash
gh pr view "$PR" --repo "$SCOPE" \
  --json baseRefName,baseRefOid,headRefName,headRefOid,isDraft,state,headRepository \
  --jq '{base: .baseRefOid, head: .headRefOid, draft: .isDraft}'
```

`baseRefOid` is the tip of the base branch recorded by GitHub. The pull request's
own diff is a merge-base comparison, so the review range is:

```bash
git fetch --quiet origin "pull/$PR/head:refs/review/$PR/head"   # head into the local store
git cat-file -e "$BASE_OID" 2>/dev/null || git fetch --quiet origin "$BASE_OID"
MB=$(git merge-base "$BASE_OID" "$HEAD_OID")
[ "$MB" = "$BASE_OID" ] || echo "NOTE: base advanced since the branch point ($MB)"
git diff --no-color -U3 "$MB..$HEAD_OID" > review/diff.pinned.patch
git log --oneline --no-decorate "$MB..$HEAD_OID" > review/commits.txt
```

Recording `MB` matters twice: it is the honest range of the change, and a moved
base is a merge-risk finding on its own (the checks GitHub ran may have used a
merge commit of head into a base that has since moved).

Use `scripts/collect_review_context.sh` to run this together with the comment and
CI fetches. It records the pinned pair in `review/plan.json` and the range it used
in `review/log.txt`.

## Line numbers in a comment are head-revision numbers

`line`/`start_line` in the API address the file **as it exists at the commit the
comment is anchored on** (`commit_id`, which for a batch review is the review's
`commit_id`). Practical rules:

1. Read numbers from the post-image of the pinned diff, not from an editor buffer
   of a working tree that may be dirty. To confirm a number:

   ```bash
   git show "$HEAD_OID:$PATH" | nl -ba | sed -n '140,160p'
   ```

2. Only lines that the diff touched (added) or showed (context) are commentable
   on `side=RIGHT`. A deletion is commented with `side=LEFT` and the pre-image
   line number, and cannot carry a `suggestion` block.
3. `position` (the count of lines into the diff) is documented as "closing down"
   in favour of `line`; this skill never emits `position`.

`scripts/build_review_payload.py` derives the commentable line set from
`review/diff.pinned.patch` and refuses any anchor that is not in it.

## Stage 2: logical file grouping

Group changed paths before reading, then review each group as one change with one
mental model. Reviewing file-by-file in diff order is how paired changes get
half-reviewed (a signature updated without its caller, or a new option without a
documentation or test update).

Default grouping, adjusted to the repository:

| Group | Typical paths | What must be consistent inside it |
|---|---|---|
| Build | `CMakeLists.txt`, `*.cmake`, `Makefile`, `*.mk`, `ecbuild*` | targets, flags, module dirs, install/export |
| Interfaces | public headers, `.c`/`.F90` module APIs, IDL/schema | signature, intent, kind, defaults |
| Implementation | sources named by the interface group | every caller and test of a changed contract |
| Configuration | `*.yml`, `*.yaml`, `*.nml`, `params.*`, `*.conf` | defaults, key spelling and value validity, provenance |
| Tests | `tests/`, `test_*.py`, `*_test.f90`, fixtures, fixtures data | the new or fixed behaviour is asserted, and actually runs |
| CI / workflow | `.github/workflows/`, `.pre-commit-config.yaml`, scripts that gate | what runs, on which event, and what a green result proves |
| Docs | `README*`, `docs/`, `*.md`, comments in code touched above | claims still match the machine-visible behaviour |

Grouping is a review unit, not a comment unit: one comment per defect, but write
the comments of a group together so duplicated findings collapse into one.

Then read the whole changed file at the pinned revision (`git show
"$HEAD_OID:$path"`) before commenting. A diff hunk cannot show that the new
early-return below the hunk skips the `deallocate` that the hunk added.

## Re-check before posting

A pending review stays valid across pushes but its comments age out. Immediately
before publishing:

```bash
LIVE=$(gh pr view "$PR" --repo "$SCOPE" --json headRefOid --jq .headRefOid)
PINNED=$(jq -r .commit_id review/review_payload.json)
[ "$LIVE" = "$PINNED" ] || echo "STALE: re-anchor against $LIVE before posting (was $PINNED)"
```

`build_review_payload.py --check` performs the same comparison against the head
you pass it (`--head-ref-oid`, or `--pr`, which reads the live value) and fails
with `commit-drift` on mismatch; `post_pending_review.sh` re-checks before every
publish, so a stale payload cannot be posted without an explicit override. If the
check is run without a head or a diff it says so (`pin-unverified`,
`anchors-unverified`) instead of implying it verified something.

After a force push, re-run stage 1 with the new `headRefOid` and re-anchor the
findings you still believe.
