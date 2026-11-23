#!/usr/bin/env bash
#  Publish a review payload as a PENDING draft -- never as a submitted verdict.
#
#  Three gates run before anything is written to GitHub, because the difference
#  between a draft and a submitted review is a single JSON key:
#
#    1. the payload must not contain "event" (POST .../reviews with an event
#       publishes APPROVE / REQUEST_CHANGES / COMMENT immediately);
#    2. the payload's commit_id must equal the pull request's live headRefOid, so
#       comments land on the revision this review was written against;
#    3. an existing PENDING review by the caller is refreshed, not duplicated.
#
#  Usage: ./post_pending_review.sh PR review_payload.json [OWNER/REPO]
#  Exit:  0 a PENDING review was created or refreshed (id printed);
#         1 a gate failed -- nothing was written;
#         2 gh/git/jq missing, PR unavailable.
#
#  Submitting is deliberately out of scope:
#    gh api "repos/OWNER/REPO/pulls/PR/reviews/REVIEW_ID/events" \
#      --method POST -f body='Reviewed.' -f event=COMMENT

set -euo pipefail

PR="${1:-}"
PAYLOAD="${2:-review/review_payload.json}"
SCOPE="${3:-}"

die() { echo "pending-review: $*" >&2; exit 1; }
usage() { echo "usage: $0 PR [payload.json] [OWNER/REPO]" >&2; exit 2; }

for tool in gh jq; do
  command -v "$tool" >/dev/null 2>&1 || die "$tool is required but not on PATH"
done
[[ "$PR" =~ ^[0-9]+$ ]] || usage
[[ -f "$PAYLOAD" ]] || die "no payload at $PAYLOAD (build it with scripts/build_review_payload.py)"

view_args=("$PR")
scope_note=""
if [[ -n "$SCOPE" ]]; then
  view_args+=(--repo "$SCOPE")
  scope_note="--repo $SCOPE "
fi
if [[ -z "$SCOPE" ]]; then
  SCOPE=$(gh repo view --json owner,name --jq '[.owner.login, .name] | join("/")')
fi
API="repos/$SCOPE/pulls/$PR"

# -- Gate 1: no event key anywhere in the payload. -----------------------------
if jq -e 'has("event")' "$PAYLOAD" >/dev/null 2>&1; then
  die "the payload carries \"event\": $(jq -r .event "$PAYLOAD") -- this would submit a verdict"
fi
if jq -e '[.comments[]? | select(has("event"))] | length > 0' "$PAYLOAD" >/dev/null 2>&1; then
  die "a comment carries \"event\"; batch comments have no per-comment action"
fi
[[ "$(jq -r '.comments | length' "$PAYLOAD")" != 0 ]] || die "payload has no comments to post"

# -- Gate 2: the payload is anchored on the live head. -------------------------
live=$(gh pr view "${view_args[@]}" --json headRefOid --jq .headRefOid)
pinned=$(jq -r '.commit_id // empty' "$PAYLOAD")
if [[ -z "$pinned" ]]; then
  die "payload has no commit_id; nothing would anchor these comments"
fi
if [[ "$live" != "$pinned" ]]; then
  die "stale payload: PR head is $live, payload is pinned to $pinned -- rebuild against $live"
fi

# -- Gate 3: reuse the caller's own pending review. ----------------------------
me=$(gh api user --jq .login)
# gh's --jq takes a bare expression (no --arg), so the login is interpolated.
# shellcheck disable=SC2016
existing=$(gh api "$API/reviews" --paginate \
  --jq "[.[] | select(.state == \"PENDING\") | select(.user.login == \"$me\") | .id] | last // empty")

if [[ -n "$existing" ]]; then
  echo "pending-review: refreshing draft $existing (comments are not edited; the summary body is)" >&2
  gh api "$API/reviews/$existing" --method PUT --field body="$(jq -r '.body // ""' "$PAYLOAD")" >/dev/null
  echo "$existing"
  echo "pending-review: draft $existing body updated; the comment set is unchanged -- delete it with" >&2
  echo "pending-review:   gh api $API/reviews/$existing --method DELETE   and re-run to post the new payload" >&2
  exit 0
fi

# -- Create. -------------------------------------------------------------------
# Capture rather than let set -e abort, so a rejected create can be explained:
# the common cause is a head that moved (or drifted anchors) after the build.
if ! created=$(gh api "$API/reviews" --method POST --input "$PAYLOAD" \
  --jq '{id, state, submitted_at, html_url}' 2>&1); then
  echo "pending-review: gh api failed" >&2
  printf '%s\n' "$created" >&2
  echo "pending-review: gate 2 passed, so a rejected create usually means the head moved" >&2
  echo "pending-review:   or an anchor drifted; re-collect context and rebuild the payload" >&2
  echo "pending-review:   (gh pr view $PR ${scope_note}--json headRefOid)" >&2
  exit 1
fi
state=$(printf '%s' "$created" | jq -r .state)
if [[ "$state" != "PENDING" ]]; then
  # Defensive: this branch means the API published the review anyway.
  echo "pending-review: UNEXPECTED state $state for review $(printf '%s' "$created" | jq -r .id)" >&2
  printf '%s\n' "$created" >&2
  exit 1
fi

printf '%s\n' "$created" | jq -r .id
echo "pending-review: PENDING draft $(printf '%s' "$created" | jq -r .id) at $(printf '%s' "$created" | jq -r .html_url)" >&2
echo "pending-review: $(jq '.comments | length' "$PAYLOAD") comments anchored on ${pinned:0:7};" >&2
echo "pending-review: nothing is visible to the author until you submit:" >&2
echo "pending-review:   gh api $API/reviews/$(printf '%s' "$created" | jq -r .id)/events \\" >&2
echo "pending-review:     --method POST -f body='Summary.' -f event=COMMENT" >&2
