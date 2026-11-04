#!/usr/bin/env bash
#  Collect the pinned review context of one pull request into a single directory.
#
#  A structured review is only trustworthy if the diff, the existing comments,
#  the CI state and the payload anchors all describe the same code. Everything is
#  therefore fetched once, against one revision pair (baseRefOid..headRefOid):
#
#      review/plan.json        pinned revisions, title, author, changed files
#      review/pull.json        raw pull request object (REST)
#      review/commits.json     commits on the head ref
#      review/threads.json     GraphQL review threads (isResolved, isOutdated)
#      review/submitted.json   flat list of submitted inline comments
#      review/reviews.json     every review, its state, and its own comments
#      review/diff.patch       unified diff of the pinned range (gh)
#      review/diff.pinned.patch same range from local objects, when available
#      review/diff.txt         numstat + name-status of the range
#      review/files.txt        grouping input: path, +adds -dels
#      review/runs.txt         workflow runs recorded for the pinned head
#      review/log.txt          timestamped record of what was fetched
#
#  Requires: gh (authenticated), git, jq. Read-only -- nothing here posts to the
#  pull request; publishing is a separate deliberate step
#  (references/pending-review-api.md).
#
#  Usage: ./collect_review_context.sh PR [OWNER/REPO] [outdir]
#  Exit:  0 complete; 1 dependency missing or PR unavailable; 3 partial (see log)

set -euo pipefail

PR="${1:-}"
SCOPE="${2:-}"
OUTDIR="${3:-review}"

die() { echo "pr-context: $*" >&2; exit 1; }

# Warnings go to stderr and into log.txt, so a partial run is diagnosable from
# the artefact directory alone.
warn() {
  echo "pr-context: $*" >&2
  printf '%s WARN %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >>"$OUTDIR/log.txt" 2>/dev/null || true
}

for tool in gh git jq; do
  command -v "$tool" >/dev/null 2>&1 || die "$tool is required but not on PATH"
done
[[ "$PR" =~ ^[0-9]+$ ]] || die "usage: $0 PR [OWNER/REPO] [outdir] (PR must be a number)"

view_args=("$PR")
[[ -n "$SCOPE" ]] && view_args+=(--repo "$SCOPE")

mkdir -p "$OUTDIR"
: >"$OUTDIR/log.txt"
partial=0
log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" | tee -a "$OUTDIR/log.txt" >/dev/null; }

# -- Phase 1: pin the revisions. Nothing after this is fetched by branch name. --
# --json takes one comma-separated list; build it from several lines for width.
PLAN_FIELDS=$(printf '%s\n' \
  'number,url,title,author,state,isDraft,baseRefName,headRefName,id,' \
  'baseRefOid,headRefOid,changedFiles,additions,deletions,files,' \
  'headRepository,headRepositoryOwner,reviewDecision,statusCheckRollup' |
  tr -d '\n ')
if ! gh pr view "${view_args[@]}" --json "$PLAN_FIELDS" >"$OUTDIR/plan.json"; then
  die "cannot read PR $PR${SCOPE:+ in $SCOPE} (check gh auth status and the repository)"
fi

head_oid=$(jq -r .headRefOid "$OUTDIR/plan.json")
base_oid=$(jq -r .baseRefOid "$OUTDIR/plan.json")
node_id=$(jq -r .id "$OUTDIR/plan.json")
[[ -n "$head_oid" && "$head_oid" != null ]] || die "no headRefOid returned for PR $PR"

if [[ -z "$SCOPE" ]]; then
  SCOPE=$(gh repo view --json owner,name --jq '[.owner.login, .name] | join("/")')
fi

# GitHub's view of a pull request is a merge-base comparison, not base..head:
# when the base branch has moved, only merge-base..head is what the PR changes.
merge_base=$base_oid
if git cat-file -e "${base_oid}^{commit}" 2>/dev/null &&
  git cat-file -e "${head_oid}^{commit}" 2>/dev/null; then
  merge_base=$(git merge-base "$base_oid" "$head_oid" 2>/dev/null || echo "$base_oid")
  [[ "$merge_base" == "$base_oid" ]] ||
    log "NOTE: base branch advanced past the branch point ($base_oid -> $merge_base); using the merge base"
fi
printf 'BASE_OID=%s\nHEAD_OID=%s\nMERGE_BASE=%s\n' "$base_oid" "$head_oid" "$merge_base" \
  >"$OUTDIR/pin.txt"

API="repos/$SCOPE/pulls/$PR"
log "PR $PR in $SCOPE; pinned range $merge_base..$head_oid (base tip $base_oid)"

gh api "$API" >"$OUTDIR/pull.json"
gh api "$API/commits" --paginate --jq \
  '[.[] | {sha, subject: (.commit.message | split("\n")[0]), date: .commit.author.date,
           parents: (.parents | length)}]' >"$OUTDIR/commits.json"

# -- Phase 2: existing feedback, submitted and pending. ------------------------
# Threads (resolution and outdated state) only exist in GraphQL; REST lists the
# flat comment stream. Both are fetched: triage needs the thread, the API anchor
# needs the stream.
# GraphQL $variables are expanded by GitHub, not by bash.
# shellcheck disable=SC2016
gh api graphql -f id="$node_id" -f query='
query($id:ID!){
  node(id:$id){ ... on PullRequest {
    reviewThreads(first:100){ pageInfo{ hasNextPage }
      nodes{ id isResolved isOutdated path line originalLine subjectType
        comments(first:60){ nodes{ databaseId path line originalLine outdated subjectType
          publishedAt body author{ login } } } } }
  } }
}' >"$OUTDIR/threads.json" || { warn "reviewThreads failed"; partial=1; }

gh api "$API/comments" --paginate --jq \
  '[.[] | {id, user: .user.login, path, line, original_line, side, subject_type,
           commit_id, original_commit_id, in_reply_to_id, pull_request_review_id,
           created_at, updated_at, body}]' >"$OUTDIR/submitted.json" ||
  { warn "review comments failed"; partial=1; }

# shellcheck disable=SC2016
gh api graphql -f id="$node_id" -f query='
query($id:ID!){
  node(id:$id){ ... on PullRequest {
    viewerLatestReview{ id state body submittedAt }
    reviews(first:100){ nodes{ databaseId state body submittedAt author{ login }
      comments(first:80){ nodes{ databaseId path line outdated body } } } }
  } }
}' | jq '{viewer: .data.node.viewerLatestReview,
          reviews: [.data.node.reviews.nodes[] | {databaseId, state,
                    author: .author.login, submitted_at: .submittedAt,
                    body, comments: (.comments.nodes | length)}],
          pending_comments: [.data.node.reviews.nodes[]
                    | select(.state == "PENDING") as $r
                    | .comments.nodes[] | . + {review: $r.databaseId,
                                               reviewer: ($r.author.login // "unknown")}]}' \
  >"$OUTDIR/reviews.json" || { warn "reviews failed"; partial=1; }

count() { jq -r "$2 // 0 | tostring" "$1" 2>/dev/null || printf '0'; }
pending=$(count "$OUTDIR/reviews.json" '[.reviews[] | select(.state == "PENDING")] | length')
log "submitted comments: $(count "$OUTDIR/submitted.json" 'length')"
log "reviews: $(count "$OUTDIR/reviews.json" '.reviews | length') ($pending PENDING)"
if [[ "$pending" != 0 ]]; then
  log "there are draft (PENDING) reviews; confirm whose, and refresh them instead of duplicating"
fi

# -- Phase 3: CI evidence recorded against the pinned head. --------------------
jq '.statusCheckRollup // []' "$OUTDIR/plan.json" >"$OUTDIR/checks.json"
runs_json=$(gh run list --repo "$SCOPE" --limit 100 \
  --json databaseId,name,workflowName,status,conclusion,headSha,createdAt,event 2>/dev/null) ||
  { warn "workflow run list failed"; partial=1; runs_json='[]'; }
{
  echo "# workflow runs recorded for head $head_oid"
  printf '%s\n' "$runs_json" | jq -r --arg sha "$head_oid" '
    map(select(.headSha == $sha))[] |
    [.databaseId, .status, (.conclusion // "-"), .event, .workflowName] | @tsv'
  echo "# (no rows above means no CI ever ran on the pinned head)"
} >"$OUTDIR/runs.txt"

# -- Phase 4: the diff of the pinned range. ------------------------------------
# The API refuses diffs over 20,000 lines ("HTTP 406 ... too_large"), so the
# local revision range is the primary source and gh is the fallback.
have_local=0
if git cat-file -e "${base_oid}^{commit}" 2>/dev/null &&
  git cat-file -e "${head_oid}^{commit}" 2>/dev/null; then
  have_local=1
  git diff --no-color -U3 "${merge_base}..${head_oid}" >"$OUTDIR/diff.pinned.patch"
  log "diff.pinned.patch built locally from the pinned objects (use this for anchors)"
fi

if gh pr diff "${view_args[@]}" >"$OUTDIR/diff.patch" 2>/dev/null; then
  log "diff.patch covers $(grep -c '^diff --git' "$OUTDIR/diff.patch") files"
elif ((have_local)); then
  log "gh pr diff unavailable (a diff over 20,000 lines is refused with HTTP 406); using the local range"
  cp "$OUTDIR/diff.pinned.patch" "$OUTDIR/diff.patch"
else
  warn "gh pr diff failed and the pinned objects are not local"
  log "fetch them, then re-run: git fetch origin pull/$PR/head:refs/review/$PR && git fetch origin $base_oid"
  partial=1
  : >"$OUTDIR/diff.patch"
  : >"$OUTDIR/diff.pinned.patch"
fi

{
  git diff --numstat "${merge_base}..${head_oid}" 2>/dev/null ||
    jq -r '.files[]? | [(.additions | tostring), (.deletions | tostring), .path] | @tsv' "$OUTDIR/plan.json"
  echo "---"
  git diff --name-status "${merge_base}..${head_oid}" 2>/dev/null || true
} >"$OUTDIR/diff.txt"

# Grouping input: path with its change size, largest first.
sort -t "$(printf '\t')" -k1,1rn "$OUTDIR/diff.txt" 2>/dev/null |
  awk -F'\t' 'NF==3 && $1 ~ /^[0-9]+$/ { printf "%s\t+%s -%s\n", $3, $1, $2 }' \
    >"$OUTDIR/files.txt" ||
  jq -r '.files[]? | [.path, "+" + (.additions | tostring), "-" + (.deletions | tostring)] | @tsv' \
    "$OUTDIR/plan.json" >"$OUTDIR/files.txt"

if ((partial)); then
  warn "partial collection; see $OUTDIR/log.txt"
  exit 3
fi
log "complete"
echo "$OUTDIR" >&2
