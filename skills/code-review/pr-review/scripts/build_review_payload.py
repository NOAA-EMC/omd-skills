#!/usr/bin/env python3
"""Turn structured review findings into a pending-only GitHub review payload.

Input: a findings file written by the reviewer (schema below).
Output: ``review_payload.json`` for::

    gh api repos/OWNER/REPO/pulls/N/reviews --input review_payload.json

Three properties of a safe review are mechanical, and mechanical properties are
cheaper to verify than to re-read, so this script enforces them:

1. **Pending only.** The payload never carries an ``event`` key, which is what
   makes ``POST .../reviews`` create a ``PENDING`` draft instead of submitting a
   verdict (``references/pending-review-api.md``). ``--check`` re-verifies an
   existing payload and fails if an ``event`` appeared.
2. **Pinned anchors.** Every inline comment is anchored at ``headRefOid`` and its
   ``line`` must be a RIGHT-side line of ``baseRefOid..headRefOid``. GitHub
   repositions or ages out comments anchored on other revisions, and a LEFT-side
   (deleted-line) comment cannot carry a suggestion block.
3. **House comment format.** Bodies are assembled from fields, so they always
   open with ``**[Category]: [Title]**``, keep the prose short, and stay within
   the suggestion-fence budget (``references/comment-format.md``).

Findings schema (``comments`` required, everything else optional)::

    {
      "body": "Overall summary markdown for the draft review.",
      "head_ref_oid": "optional; overridden by --head-ref-oid",
      "comments": [
        {
          "path": "src/physics.F90",
          "line": 118,                   // file line at head, RIGHT side
          "start_line": 115,             // optional multi-line comment
          "side": "RIGHT",               // LEFT for a deleted line
          "priority": "CRITICAL",        // CRITICAL | IMPORTANT | SUGGESTION
          "category": "Correctness",
          "title": "Reduce order changes the ensemble mean",
          "prose": ["Sentence one.", "Sentence two."],
          "fix": "Use a deterministic reduction.",   // markdown allowed
          "suggestion": "call MPI_Reduce(...)",      // replacement lines only
          "test": "ctest -R ensemble_mean -V",
          "reference": "EE2 6.2",
          "in_reply_to": 1234567,        // optional reply; no coordinates
          "subject_type": "line"         // or "file" for a file-level comment
        }
      ]
    }

Usage::

    python3 scripts/build_review_payload.py --findings findings.json \\
        (--pr N [--repo OWNER/REPO] | --head-ref-oid SHA [--base-ref-oid SHA]) \\
        [--diff diff.patch] [--out review_payload.json] [--require-fix]

    python3 scripts/build_review_payload.py --check review_payload.json \\
        --head-ref-oid SHA [--diff diff.patch]

Exit status is 0 only when a payload was written (or a payload passed the
check). Stdlib only; Python 3.8+.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

PRIORITIES = ("CRITICAL", "IMPORTANT", "SUGGESTION")
PRIORITY_BADGE = {"CRITICAL": "\U0001f534", "IMPORTANT": "\U0001f7e1", "SUGGESTION": "\U0001f7e2"}
MAX_SUGGESTION_LINES = 15
PROSE_SENTENCES = (2, 5)
HEADER_RE = re.compile(r"^(?:\S+\s+)?\*\*\[[^\]]+\]:\s*\S")
FENCE_RE = re.compile(r"^\s*```")
SUGGESTION_RE = re.compile(r"^```suggestion[ \t]*\n(.*?)```", re.MULTILINE | re.DOTALL)
HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", re.MULTILINE)


class Report:
    """Collect errors and notes; ``has_errors`` decides whether to write."""

    def __init__(self):
        self.errors = []
        self.notes = []

    def error(self, code, message, where=""):
        self.errors.append(f"error: {code}{f' [{where}]' if where else ''}: {message}")

    def note(self, code, message, where=""):
        self.notes.append(f"note: {code}{f' [{where}]' if where else ''}: {message}")

    @property
    def has_errors(self):
        return bool(self.errors)

    def dump(self, stream=sys.stderr):
        for line in self.errors + self.notes:
            print(line, file=stream)


def run_git(args, cwd=None):
    """Run git, returning stdout; raise RuntimeError with stderr on failure."""
    proc = subprocess.run(["git", "-c", "core.quotepath=false", *args],
                          cwd=str(cwd) if cwd else None,
                          capture_output=True, text=True)
    if proc.returncode != 0:
        first = (proc.stderr.strip().splitlines() or [f"exit {proc.returncode}"])[0]
        raise RuntimeError(f"git {' '.join(args)}: {first}")
    return proc.stdout


def gh_pr_diff(pr, repo=None):
    """Fetch a pull request diff through gh, when the objects are not local."""
    cmd = ["gh", "pr", "diff", str(pr)]
    if repo:
        cmd += ["--repo", repo]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        first = (proc.stderr.strip().splitlines() or [f"exit {proc.returncode}"])[0]
        raise RuntimeError(f"gh pr diff {pr}: {first}")
    return proc.stdout


def gh_pr_view(pr, repo=None, fields="headRefOid,baseRefOid"):
    """Read the pinned revisions of a pull request through gh."""
    cmd = ["gh", "pr", "view", str(pr), "--json", fields]
    if repo:
        cmd += ["--repo", repo]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"gh pr view {pr} failed")
    data = json.loads(proc.stdout)
    if not data.get("headRefOid"):
        raise RuntimeError(f"gh returned no headRefOid for PR {pr}")
    return data["headRefOid"], data.get("baseRefOid")


def right_side_lines(diff_text):
    """Map ``path -> sorted RIGHT-side file lines`` for a unified diff.

    RIGHT-side lines are context and added lines, the numbering GitHub's
    ``side=RIGHT`` uses. Deleted lines belong to the LEFT side. Hunk headers
    drive the walk, so a ``+`` line never over-counts into the next hunk.
    """
    anchors = {}
    lines = diff_text.splitlines()
    path = None
    index = 0
    hunk = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
    while index < len(lines):
        line = lines[index]
        if line.startswith("+++ "):
            name = line[4:].strip()
            if name == "/dev/null" or not name:
                path = None
            else:
                path = name[2:] if name.startswith(("a/", "b/")) else name
                anchors.setdefault(path, set())
        else:
            match = hunk.match(line)
            if match and path is not None:
                right = int(match.group(3))
                right_count = int(match.group(4) if match.group(4) is not None else 1)
                left_count = int(match.group(2) if match.group(2) is not None else 1)
                seen_right = seen_left = 0
                index += 1
                while index < len(lines) and (seen_right < right_count or seen_left < left_count):
                    body = lines[index]
                    if body.startswith("\\"):
                        index += 1
                        continue
                    if body.startswith("+"):
                        anchors[path].add(right)
                        right += 1
                        seen_right += 1
                    elif body.startswith("-"):
                        seen_left += 1
                    elif body.startswith(" ") or body == "":
                        anchors[path].add(right)
                        right += 1
                        seen_right += 1
                        seen_left += 1
                    else:
                        break  # a new header or the end of this hunk
                    index += 1
                continue
        index += 1
    return {name: sorted(nums) for name, nums in anchors.items() if nums}


def sentence_count(text):
    """Count sentences, ignoring fenced code inside the text."""
    body = re.sub(r"```.*?```", " ", text or "", flags=re.DOTALL)
    return len([s for s in re.findall(r"[^.!?]+[.!?]+|[^.!?]+$", body) if s.strip()])


def fence_lines(text):
    """Lines inside the ```suggestion fence of a body, or 0."""
    match = SUGGESTION_RE.search(text or "")
    return len([ln for ln in match.group(1).rstrip("\n").splitlines()]) if match else 0


def render_body(comment, max_suggestion, report, where):
    """Assemble one review comment body from structured fields."""
    priority = comment.get("priority", "IMPORTANT")
    if priority not in PRIORITIES:
        report.error("bad-priority", f"priority {priority!r} not in {', '.join(PRIORITIES)}", where)
    category = (comment.get("category") or "").strip()
    title = (comment.get("title") or "").strip().rstrip(".")
    if not category:
        report.error("missing-category", "comments need a category", where)
    if not title:
        report.error("missing-title", "comments need a one-line title", where)

    prose = comment.get("prose") or []
    if isinstance(prose, str):
        prose = [prose]
    joined = " ".join(part.strip() for part in prose if part.strip())
    count = sentence_count(joined)
    if not PROSE_SENTENCES[0] <= count <= PROSE_SENTENCES[1]:
        report.error("prose-length", f"{count} sentences; keep {PROSE_SENTENCES[0]}-{PROSE_SENTENCES[1]}", where)
    for index, part in enumerate(prose):
        if FENCE_RE.search(part):
            report.error("nested-fence", f"prose[{index}] holds a code fence", where)

    fix = (comment.get("fix") or "").strip()
    test = (comment.get("test") or "").strip()
    if not fix:
        report.error("missing-fix", "add the concrete change in 'fix'", where)
    if not test:
        report.error("missing-test", "name the command or file in 'test' that proves the change", where)
    if FENCE_RE.search(fix):
        report.error("nested-fence", "'fix' holds a code fence; use 'suggestion' for replacement lines", where)

    suggestion = comment.get("suggestion")
    if suggestion is not None:
        suggestion = str(suggestion).strip("\n")
        if not suggestion.strip():
            report.error("empty-suggestion", "suggestion block has no replacement lines", where)
            suggestion = None
        elif len(suggestion.splitlines()) > max_suggestion:
            report.error("suggestion-length",
                         f"suggestion is {len(suggestion.splitlines())} lines; budget is {max_suggestion}",
                         where)
            suggestion = None
        elif FENCE_RE.search(suggestion):
            report.error("nested-fence", "suggestion must be replacement lines only", where)
            suggestion = None

    badge = PRIORITY_BADGE.get(priority, "")
    headline = f"**[{category}]: {title}**"
    if priority != "IMPORTANT" and badge:
        headline += f" ({badge} {priority})"
    out = [headline]
    if joined:
        out += ["", joined]
    if fix:
        out += ["", "**Suggested fix:**", "", fix]
    if suggestion:
        out += ["", "```suggestion", suggestion, "```"]
    if test:
        out += ["", "**Test:**", "", test]
    if comment.get("reference"):
        out += ["", f"**Reference:** {str(comment['reference']).strip()}"]
    return "\n".join(out).strip() + "\n"


def check_body_text(body, max_suggestion, report, where):
    """Validate a hand-written body against the house template."""
    text = (body or "").strip()
    if not text:
        report.error("empty-body", "comment body is empty", where)
        return
    first = text.splitlines()[0]
    if not HEADER_RE.match(first):
        report.error("body-header", f"body must open with '**[Category]: [Title]', got {first[:44]!r}", where)
    blocks = re.findall(r"```suggestion", text)
    if len(blocks) > 1:
        report.error("multiple-suggestions", "one suggestion block per comment", where)
    if fence_lines(text) > max_suggestion:
        report.error("suggestion-length", f"suggestion is {fence_lines(text)} lines; budget is {max_suggestion}",
                     where)


def build_entry(comment, anchors, head_sha, max_suggestion, report, used):
    """Return (where, entry-or-None) for one finding."""
    path = comment.get("path")
    where = f"#{comment.get('_index', '?')} {path or '?'}"
    if "event" in comment:
        report.note("event-ignored", f"per-comment 'event'={comment['event']!r} has no effect on a draft", where)

    if not path:
        report.error("missing-path", "each comment needs a repository-relative path", where)
        return where, None

    hand = comment.get("body")
    structured = any(comment.get(k) for k in ("prose", "title", "category", "fix"))
    if hand is not None and structured:
        report.error("conflict", "use 'body' or the structured fields, not both", where)
        return where, None
    if hand is not None:
        body = hand
        check_body_text(body, max_suggestion, report, where)
    else:
        body = render_body(comment, max_suggestion, report, where)
        if report.has_errors:
            return where, None

    entry = {"path": path, "body": body}
    if comment.get("subject_type") == "file":
        entry["subject_type"] = "file"
        return where, entry
    if comment.get("in_reply_to") is not None:
        entry["in_reply_to"] = int(comment["in_reply_to"])
        return where, entry

    line = comment.get("line")
    if line is None:
        report.error("missing-line", "inline comments need 'line', or subject_type 'file'", where)
        return where, None
    side = comment.get("side", "RIGHT")
    if side not in ("RIGHT", "LEFT"):
        report.error("bad-side", "side must be RIGHT or LEFT", where)
        return where, None
    if anchors is not None:
        if path not in anchors:
            report.error("path-unchanged", f"'{path}' has no diff lines in the pinned range", where)
            return where, None
        allowed = set(anchors[path])
        if side == "RIGHT" and int(line) not in allowed:
            report.error("line-out-of-diff", f"{path}:{line} is not a RIGHT-side line of the pinned diff", where)
            return where, None
        if side == "LEFT" and comment.get("suggestion") is not None:
            report.error("suggestion-on-left", "a LEFT-side comment cannot carry a suggestion block", where)
            return where, None
    pinned = comment.get("commit_id")
    if pinned and head_sha and pinned != head_sha:
        report.error("commit-drift", f"commit_id {str(pinned)[:7]} != pinned head {str(head_sha)[:7]}", where)
        return where, None

    entry["line"] = int(line)
    entry["side"] = side
    start = comment.get("start_line")
    if start is not None:
        if int(start) >= int(line):
            report.error("bad-range", "start_line must be lower than line", where)
            return where, None
        entry["start_line"] = int(start)
        entry["start_side"] = comment.get("start_side", side)
    # A batch comment inherits the review's commit_id: the create-review schema
    # has no per-comment pin, so a finding's commit_id is validated but not emitted.
    key = (path, entry.get("start_line"), int(line), side)
    if key in used:
        report.error("duplicate-anchor", f"{path}:{line} repeats an earlier comment; merge them", where)
        return where, None
    used.add(key)
    return where, entry


def build(findings, head_sha, anchors, max_suggestion, require_fix):
    """Return (payload or None, report)."""
    report = Report()
    if not isinstance(findings, dict):
        report.error("bad-findings", "findings file must be a JSON object")
        return None, report
    comments = findings.get("comments")
    if not isinstance(comments, list) or not comments:
        report.error("no-comments", "findings contains no comments to post")
        return None, report

    declared = findings.get("head_ref_oid")
    if declared and head_sha and declared != head_sha:
        report.error("commit-drift", f"findings pin {str(declared)[:7]} but the live head is {str(head_sha)[:7]}")
        return None, report
    head_sha = head_sha or declared
    if not head_sha:
        report.error("no-head-sha", "pass --head-ref-oid or --pr so comments can be anchored")
        return None, report
    if anchors is None:
        report.error("no-diff", "pass --diff (or a local base/head checkout) to validate anchors")
        return None, report

    for comment in comments:
        if not isinstance(comment, dict):
            report.error("bad-comment", "every comment must be a JSON object")
            return None, report
    if require_fix:
        for index, comment in enumerate(comments):
            if comment.get("body") is None and not str(comment.get("fix") or "").strip():
                report.error("missing-fix", f"comment {index} has no fix (--require-fix)", f"#{index}")
        if report.has_errors:
            return None, report

    payload = {"commit_id": head_sha, "comments": []}
    if findings.get("body"):
        payload["body"] = str(findings["body"]).strip() + "\n"
    used = set()
    for index, comment in enumerate(comments):
        comment.setdefault("_index", index)
        _, entry = build_entry(comment, anchors, head_sha, max_suggestion, report, used)
        if entry:
            payload["comments"].append(entry)
    if not payload["comments"]:
        report.error("no-valid-comments", "every comment was rejected; nothing would be posted")
    payload.pop("event", None)
    if report.has_errors:
        return None, report
    return payload, report


def check_payload(path, head_sha, anchors, max_suggestion, require_pending=True):
    """Re-validate an existing payload: the pre-submit gate."""
    report = Report()
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        report.error("bad-payload", "payload must be a JSON object")
        return report
    if "event" in data and require_pending:
        report.error("submitted-event", f"payload carries event={data['event']!r}; this tool posts drafts only")
    if head_sha and data.get("commit_id") != head_sha:
        report.error("commit-drift",
                     f"payload commit_id {str(data.get('commit_id'))[:7]} != pinned head {str(head_sha)[:7]}")
    for index, entry in enumerate(data.get("comments", [])):
        where = f"#{index} {entry.get('path', '?')}"
        check_body_text(entry.get("body", ""), max_suggestion, report, where)
        if entry.get("subject_type") == "file" or entry.get("in_reply_to"):
            continue
        if anchors is None:
            continue
        if entry.get("path") not in anchors:
            report.error("path-unchanged", f"'{entry.get('path')}' is not in the pinned diff", where)
            continue
        if entry.get("side", "RIGHT") == "RIGHT" and entry.get("line") not in anchors[entry["path"]]:
            report.error("line-out-of-diff", f"{entry.get('path')}:{entry.get('line')} is not a diff line", where)
    if not data.get("comments"):
        report.note("summary-only", "no inline comments; the draft carries only its body")
    if not head_sha:
        report.note("pin-unverified", "no --head-ref-oid/--pr, so commit_id was not compared "
                                      "with the live head")
    if anchors is None:
        report.note("anchors-unverified", "no diff supplied, so line numbers were not checked "
                                          "against it")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build or check a pending-only PR review payload.")
    parser.add_argument("--findings", type=Path, help="structured findings JSON (build mode)")
    parser.add_argument("--check", type=Path, metavar="PAYLOAD", help="validate an existing payload")
    parser.add_argument("--pr", type=int, help="pull request number; revisions come from gh")
    parser.add_argument("--repo", help="OWNER/REPO for --pr")
    parser.add_argument("--head-ref-oid", help="pinned PR head SHA (headRefOid)")
    parser.add_argument("--base-ref-oid", help="pinned merge-base SHA (baseRefOid)")
    parser.add_argument("--diff", type=Path, help="unified diff used to validate anchors")
    parser.add_argument("--cwd", type=Path, default=Path("."),
                       help="working tree to run git in (default: current directory)")
    parser.add_argument("--out", type=Path, help="write the payload to this path")
    parser.add_argument("--max-suggestion", type=int, default=MAX_SUGGESTION_LINES)
    parser.add_argument("--require-fix", action="store_true", help="every comment must carry a fix")
    args = parser.parse_args(argv)

    head_sha, base_sha = args.head_ref_oid, args.base_ref_oid
    if args.pr is not None:
        try:
            gh_head, gh_base = gh_pr_view(args.pr, args.repo)
        except (RuntimeError, FileNotFoundError, json.JSONDecodeError, OSError) as exc:
            print(f"FATAL ERROR: {exc}", file=sys.stderr)
            return 2
        head_sha = head_sha or gh_head
        base_sha = base_sha or gh_base

    diff_text = None
    if args.diff:
        diff_text = args.diff.read_text(encoding="utf-8", errors="replace")
    elif base_sha and head_sha:
        try:
            diff_text = run_git(["diff", "--no-color", "-U3", f"{base_sha}..{head_sha}"], cwd=args.cwd)
        except (RuntimeError, FileNotFoundError) as git_exc:
            # The pinned objects are not in this tree: fall back to gh, which can
            # only give the current diff, and say so rather than imply a pin.
            if args.pr is None:
                print(f"FATAL ERROR: cannot read the pinned diff: {git_exc}", file=sys.stderr)
                return 2
            try:
                diff_text = gh_pr_diff(args.pr, args.repo)
                print(f"note: anchors validated against the gh-fetched diff; local range "
                      f"unavailable ({git_exc})", file=sys.stderr)
            except (RuntimeError, FileNotFoundError) as gh_exc:
                print(f"FATAL ERROR: cannot read the pinned diff: {git_exc}; {gh_exc}", file=sys.stderr)
                return 2
    anchors = right_side_lines(diff_text) if diff_text is not None else None

    if args.check:
        try:
            report = check_payload(args.check, head_sha, anchors, args.max_suggestion)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"FATAL ERROR: cannot read payload: {exc}", file=sys.stderr)
            return 2
        report.dump()
        if report.has_errors:
            print("FATAL ERROR: payload is not safe to post as a draft", file=sys.stderr)
            return 1
        print(f"payload ok: {args.check}", file=sys.stderr)
        return 0

    if not args.findings:
        print("FATAL ERROR: pass --findings FILE or --check PAYLOAD", file=sys.stderr)
        return 2
    try:
        findings = json.loads(args.findings.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FATAL ERROR: cannot read findings: {exc}", file=sys.stderr)
        return 2

    payload, report = build(findings, head_sha, anchors, args.max_suggestion, args.require_fix)
    report.dump()
    if payload is None:
        print("FATAL ERROR: no payload written", file=sys.stderr)
        return 1

    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.write_text(text, encoding="utf-8")
        print(f"wrote {args.out} with {len(payload['comments'])} pending comment(s)", file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
