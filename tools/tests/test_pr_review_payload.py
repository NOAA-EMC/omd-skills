"""Tests for the pr-review skill's pending-review payload builder.

The builder is the safety gate of the skill, so these are behaviour tests: the
mechanical guarantees the skill claims (pending-only, pinned anchors, house
comment format) are asserted against fixtures, and the documented good form must
pass. ``right_side_lines`` is exercised on real ``git diff`` text as well, since
every anchor check depends on it.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import os
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "skills/code-review/pr-review/scripts/build_review_payload.py"

_spec = importlib.util.spec_from_file_location("build_review_payload", SCRIPT)
assert _spec and _spec.loader
builder = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(builder)

ADDED_DIFF = """diff --git a/src/physics.F90 b/src/physics.F90
index 1111111..2222222 100644
--- a/src/physics.F90
+++ b/src/physics.F90
@@ -10,6 +10,9 @@ module phys
   implicit none
 contains
+  real :: total
+  total = 0.0
+  if (n == 0) return
   subroutine run(n)
     integer, intent(in) :: n
   end subroutine run
@@ -40,3 +43,4 @@ module phys
 end module phys
+end module phys
"""

NEW_FILE_DIFF = """diff --git a/new.txt b/new.txt
new file mode 100644
index 0000000..3333333
--- /dev/null
+++ b/new.txt
@@ -0,0 +1,2 @@
+first
+second
"""

DELETED_DIFF = """diff --git a/gone.txt b/gone.txt
deleted file mode 100644
index 4444444..0000000
--- a/gone.txt
+++ /dev/null
@@ -1,1 +0,0 @@
-by
"""


def good_comment(**overrides):
    """A single structurally valid finding."""
    base = {
        "path": "src/physics.F90",
        "line": 12,
        "priority": "CRITICAL",
        "category": "Correctness",
        "title": "Division guard returns before deallocating",
        "prose": [
            "The early return at line 12 leaves `alloc` allocated.",
            "Every later call re-enters with the previous buffer still live.",
        ],
        "fix": "Deallocate before returning, or move the guard after the release.",
        "test": "gfortran -Wall src/physics.F90 && ./a.out 0",
    }
    base.update(overrides)
    return base


def build(findings, anchors=None, head="abc1234567890", require_fix=False):
    return builder.build(findings, head, anchors if anchors is not None else builder.right_side_lines(ADDED_DIFF),
                         builder.MAX_SUGGESTION_LINES, require_fix)


class TestAnchors(unittest.TestCase):
    """The diff parser that every anchor check relies on."""

    def test_added_and_context_lines_are_right_side(self):
        anchors = builder.right_side_lines(ADDED_DIFF)
        self.assertEqual(anchors["src/physics.F90"][0], 10)
        self.assertIn(12, anchors["src/physics.F90"])
        self.assertIn(13, anchors["src/physics.F90"])
        self.assertIn(44, anchors["src/physics.F90"])

    def test_new_file_lines_are_right_side(self):
        anchors = builder.right_side_lines(NEW_FILE_DIFF)
        self.assertEqual(anchors["new.txt"], [1, 2])

    def test_deleted_file_has_no_right_side_lines(self):
        anchors = builder.right_side_lines(DELETED_DIFF)
        self.assertNotIn("gone.txt", anchors)


class TestBuild(unittest.TestCase):
    """Payload construction and the pending-only guarantees."""

    def test_valid_findings_build_a_pending_payload(self):
        payload, report = build({"body": "Summary.", "comments": [good_comment()]})
        self.assertFalse(report.has_errors, report.errors)
        self.assertIsNotNone(payload)
        self.assertNotIn("event", payload)
        self.assertEqual(payload["commit_id"], "abc1234567890")
        self.assertEqual(len(payload["comments"]), 1)
        body = payload["comments"][0]["body"]
        self.assertIn("**[Correctness]: Division guard returns before deallocating**", body)
        self.assertIn("**Suggested fix:**", body)
        self.assertIn("**Test:**", body)

    def test_priority_trails_the_header_except_for_important(self):
        critical, _ = build({"comments": [good_comment()]})
        self.assertTrue(critical["comments"][0]["body"].startswith("**[Correctness]: Division guard"))
        self.assertIn("(\U0001f534 CRITICAL)", critical["comments"][0]["body"].splitlines()[0])
        suggestion, _ = build({"comments": [good_comment(priority="SUGGESTION")]})
        self.assertIn("\U0001f7e2 SUGGESTION", suggestion["comments"][0]["body"].splitlines()[0])
        important, _ = build({"comments": [good_comment(priority="IMPORTANT")]})
        self.assertEqual(important["comments"][0]["body"].splitlines()[0],
                         "**[Correctness]: Division guard returns before deallocating**")

    def test_suggestion_block_is_appended_after_the_fix(self):
        comment = good_comment(suggestion="  if (n == 0) then\n    deallocate(alloc)\n    return\n  end if")
        payload, report = build({"comments": [comment]})
        self.assertFalse(report.has_errors, report.errors)
        body = payload["comments"][0]["body"]
        self.assertIn("```suggestion\n  if (n == 0) then", body)
        self.assertLess(body.index("**Suggested fix:**"), body.index("```suggestion"))

    def test_per_comment_event_is_dropped_with_a_note(self):
        payload, report = build({"comments": [good_comment(event="APPROVE")]})
        self.assertFalse(report.has_errors, report.errors)
        self.assertNotIn("event", payload)
        self.assertFalse(any(c in payload["comments"][0] for c in ("event",)))
        self.assertTrue(any("event-ignored" in note for note in report.notes))

    def test_summary_body_is_optional(self):
        payload, report = build({"comments": [good_comment()]})
        self.assertFalse(report.has_errors, report.errors)
        self.assertNotIn("body", payload)

    def test_batch_comments_never_carry_their_own_pin(self):
        """``POST .../reviews`` comments inherit the review's commit_id."""
        payload, report = build({"comments": [good_comment(commit_id="abc1234567890")]})
        self.assertFalse(report.has_errors, report.errors)
        entry = payload["comments"][0]
        self.assertNotIn("commit_id", entry)
        self.assertEqual(payload["commit_id"], "abc1234567890")
        self.assertEqual(set(entry) <= {"path", "body", "line", "side", "start_line", "start_side",
                                        "subject_type", "in_reply_to"}, True)


class TestFormatRules(unittest.TestCase):
    """House comment format enforcement, which keeps posted comments uniform."""

    def test_suggestion_over_budget_is_rejected(self):
        comment = good_comment(suggestion="\n".join(f"  line{i}" for i in range(builder.MAX_SUGGESTION_LINES + 1)))
        payload, report = build({"comments": [comment]})
        self.assertIsNone(payload)
        self.assertIn("suggestion-length", " ".join(report.errors))

    def test_suggestion_within_budget_passes(self):
        comment = good_comment(suggestion="\n".join(f"  line{i}" for i in range(builder.MAX_SUGGESTION_LINES)))
        payload, report = build({"comments": [comment]})
        self.assertIsNotNone(payload, report.errors)

    def test_prose_needs_two_to_five_sentences(self):
        for prose, label in ((["Only one sentence."], "too few"),
                             (["Sentence %d." % i for i in range(6)], "too many")):
            payload, report = build({"comments": [good_comment(prose=prose)]})
            self.assertIsNone(payload, label)
            self.assertIn("prose-length", " ".join(report.errors), label)

    def test_missing_fix_or_test_is_rejected(self):
        for field in ("fix", "test"):
            payload, report = build({"comments": [good_comment(**{field: ""})]})
            self.assertIsNone(payload)
            self.assertIn(f"missing-{field}", " ".join(report.errors))

    def test_missing_category_or_title_is_rejected(self):
        for field in ("category", "title"):
            payload, report = build({"comments": [good_comment(**{field: ""})]})
            self.assertIsNone(payload)
            self.assertIn(f"missing-{field}", " ".join(report.errors))

    def test_bad_priority_is_rejected(self):
        payload, report = build({"comments": [good_comment(priority="BLOCKER")]})
        self.assertIsNone(payload)
        self.assertIn("bad-priority", " ".join(report.errors))

    def test_hand_written_body_must_use_the_header(self):
        ok = builder.Report()
        builder.check_body_text("**[Security]: Path traversal**\n\nProof text here.\n", 15, ok, "#0")
        self.assertFalse(ok.has_errors, ok.errors)
        bad = builder.Report()
        builder.check_body_text("please fix this line, thanks\n", 15, bad, "#0")
        self.assertIn("body-header", " ".join(bad.errors))

    def test_hand_written_body_suggestion_budget(self):
        report = builder.Report()
        body = "**[Style]: Tighten**\n\nTwo sentences here.\n\n```suggestion\n" + \
            "\n".join(f"a{i}" for i in range(20)) + "\n```\n"
        builder.check_body_text(body, 15, report, "#0")
        self.assertIn("suggestion-length", " ".join(report.errors))


class TestAnchorChecks(unittest.TestCase):
    """Anchoring rules that prevent misplaced or already-outdated comments."""

    def test_line_outside_the_diff_is_rejected(self):
        payload, report = build({"comments": [good_comment(line=30)]})
        self.assertIsNone(payload)
        self.assertIn("line-out-of-diff", " ".join(report.errors))

    def test_path_absent_from_the_diff_is_rejected(self):
        payload, report = build({"comments": [good_comment(path="src/other.F90")]})
        self.assertIsNone(payload)
        self.assertIn("path-unchanged", " ".join(report.errors))

    def test_commit_id_mismatch_is_rejected(self):
        payload, report = build({"comments": [good_comment(commit_id="9999999999999")]})
        self.assertIsNone(payload)
        self.assertIn("commit-drift", " ".join(report.errors))

    def test_findings_pin_must_match_the_live_head(self):
        payload, report = build({"head_ref_oid": "8888888888", "comments": [good_comment()]})
        self.assertIsNone(payload)
        self.assertIn("commit-drift", " ".join(report.errors))

    def test_left_side_comment_carries_no_suggestion(self):
        payload, report = build({"comments": [good_comment(side="LEFT", line=11, suggestion="x = 1")]})
        self.assertIsNone(payload)
        self.assertIn("suggestion-on-left", " ".join(report.errors))

    def test_multiline_range_order_is_enforced(self):
        payload, report = build({"comments": [good_comment(start_line=14, line=12)]})
        self.assertIsNone(payload)
        self.assertIn("bad-range", " ".join(report.errors))

    def test_duplicate_anchor_is_rejected(self):
        payload, report = build({"comments": [good_comment(), good_comment()]})
        self.assertIsNone(payload)
        self.assertIn("duplicate-anchor", " ".join(report.errors))

    def test_file_level_comment_needs_no_line(self):
        payload, report = build({"comments": [good_comment(subject_type="file", line=None)]})
        self.assertIsNotNone(payload, report.errors)
        self.assertEqual(payload["comments"][0]["subject_type"], "file")
        self.assertNotIn("line", payload["comments"][0])

    def test_reply_comment_needs_no_line(self):
        payload, report = build({"comments": [good_comment(in_reply_to=1234, line=None)]})
        self.assertIsNotNone(payload, report.errors)
        self.assertEqual(payload["comments"][0]["in_reply_to"], 1234)

    def test_inline_comment_without_line_is_rejected(self):
        payload, report = build({"comments": [good_comment(line=None)]})
        self.assertIsNone(payload)
        self.assertIn("missing-line", " ".join(report.errors))

    def test_rejects_when_no_diff_is_available(self):
        payload, report = builder.build({"comments": [good_comment()]}, "abc", None, 15, False)
        self.assertIsNone(payload)
        self.assertIn("no-diff", " ".join(report.errors))

    def test_rejects_without_a_pinned_head(self):
        payload, report = builder.build({"comments": [good_comment()]}, None, {}, 15, False)
        self.assertIsNone(payload)
        self.assertIn("no-head-sha", " ".join(report.errors))


class TestCheckPayload(unittest.TestCase):
    """The ``--check`` mode that runs immediately before posting."""

    def payload_text(self, payload):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump(payload, tmp)
        tmp.close()
        self.addCleanup(lambda: Path(tmp.name).unlink(missing_ok=True))
        return Path(tmp.name)

    def test_event_key_fails_the_check(self):
        path = self.payload_text({"commit_id": "abc1234567890", "event": "APPROVE", "comments": []})
        report = builder.check_payload(path, "abc1234567890", {}, 15)
        self.assertIn("submitted-event", " ".join(report.errors))

    def test_stale_anchor_fails_the_check(self):
        payload = {"commit_id": "fffffffffff",
                   "comments": [{"path": "src/physics.F90", "line": 12, "side": "RIGHT",
                                 "commit_id": "fffffffffff", "body": "**[A]: B**\n"}]}
        report = builder.check_payload(self.payload_text(payload), "abc1234567890",
                                       builder.right_side_lines(ADDED_DIFF), 15)
        self.assertIn("commit-drift", " ".join(report.errors))

    def test_clean_payload_passes(self):
        payload, report = build({"body": "Summary.", "comments": [good_comment()]})
        self.assertFalse(report.has_errors, report.errors)
        path = self.payload_text(payload)
        second = builder.check_payload(path, "abc1234567890", builder.right_side_lines(ADDED_DIFF), 15)
        self.assertFalse(second.has_errors, second.errors)

    def test_untemplated_body_fails_the_check(self):
        payload = {"commit_id": "abc1234567890",
                   "comments": [{"path": "src/physics.F90", "line": 12, "side": "RIGHT",
                                 "body": "nit: could be simpler"}]}
        report = builder.check_payload(self.payload_text(payload), "abc1234567890",
                                       builder.right_side_lines(ADDED_DIFF), 15)
        self.assertIn("body-header", " ".join(report.errors))


class TestCli(unittest.TestCase):
    """End-to-end CLI behaviour with a checked fixture diff."""

    def run_cli(self, args, cwd=None):
        return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=cwd,
                              capture_output=True, text=True)

    def test_build_from_diff_file_writes_payload(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            (tmp / "diff.patch").write_text(ADDED_DIFF, encoding="utf-8")
            findings = {"body": "Summary.", "comments": [good_comment()]}
            (tmp / "findings.json").write_text(json.dumps(findings), encoding="utf-8")
            proc = self.run_cli(["--findings", str(tmp / "findings.json"), "--diff", str(tmp / "diff.patch"),
                                 "--head-ref-oid", "abc1234567890", "--out", str(tmp / "review_payload.json")])
            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads((tmp / "review_payload.json").read_text(encoding="utf-8"))
            self.assertNotIn("event", payload)
            self.assertEqual(payload["comments"][0]["line"], 12)

    def test_bad_anchor_fails_with_fatal_error(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            (tmp / "diff.patch").write_text(ADDED_DIFF, encoding="utf-8")
            findings = {"comments": [good_comment(line=999)]}
            (tmp / "findings.json").write_text(json.dumps(findings), encoding="utf-8")
            proc = self.run_cli(["--findings", str(tmp / "findings.json"), "--diff", str(tmp / "diff.patch"),
                                 "--head-ref-oid", "abc1234567890"])
            self.assertEqual(proc.returncode, 1)
            self.assertIn("FATAL ERROR: no payload written", proc.stderr)
            self.assertIn("line-out-of-diff", proc.stderr)

    def test_check_mode_gates_a_written_payload(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            (tmp / "diff.patch").write_text(ADDED_DIFF, encoding="utf-8")
            findings = {"comments": [good_comment()]}
            (tmp / "findings.json").write_text(json.dumps(findings), encoding="utf-8")
            build = self.run_cli(["--findings", str(tmp / "findings.json"), "--diff", str(tmp / "diff.patch"),
                                  "--head-ref-oid", "abc1234567890", "--out", str(tmp / "p.json")])
            self.assertEqual(build.returncode, 0, build.stderr)
            good = self.run_cli(["--check", str(tmp / "p.json"), "--head-ref-oid", "abc1234567890",
                                 "--diff", str(tmp / "diff.patch")])
            self.assertEqual(good.returncode, 0, good.stderr)
            tampered = json.loads((tmp / "p.json").read_text(encoding="utf-8"))
            tampered["event"] = "REQUEST_CHANGES"
            (tmp / "p.json").write_text(json.dumps(tampered), encoding="utf-8")
            bad = self.run_cli(["--check", str(tmp / "p.json"), "--head-ref-oid", "abc1234567890",
                                "--diff", str(tmp / "diff.patch")])
            self.assertEqual(bad.returncode, 1)
            self.assertIn("submitted-event", bad.stderr)

    def test_missing_inputs_are_a_usage_error(self):
        proc = self.run_cli([])
        self.assertEqual(proc.returncode, 2)
        self.assertIn("FATAL ERROR", proc.stderr)

    def test_validates_against_a_real_git_range(self):
        """With --cwd on a tree holding both revisions, git supplies the diff."""
        if shutil.which("git") is None:
            self.skipTest("git is not available")
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            git_dir = tmp / "repo"
            git_dir.mkdir()
            env = {**os.environ, "GIT_AUTHOR_DATE": "@0 +0000", "GIT_COMMITTER_DATE": "@0 +0000"}

            def git(*args):
                return subprocess.run(["git", *args], cwd=git_dir, env=env,
                                      capture_output=True, text=True, check=True).stdout.strip()

            git("init", "-q")
            git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "base")
            base = git("rev-parse", "HEAD")
            (git_dir / "kern.F90").write_text("a\nb\nc\n", encoding="utf-8")
            git("add", "-A")
            git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "head")
            head = git("rev-parse", "HEAD")

            findings = {"body": "Summary.",
                        "comments": [good_comment(path="kern.F90", line=2)]}
            (tmp / "findings.json").write_text(json.dumps(findings), encoding="utf-8")
            proc = self.run_cli(["--findings", str(tmp / "findings.json"), "--base-ref-oid", base,
                                 "--head-ref-oid", head, "--cwd", str(git_dir),
                                 "--out", str(tmp / "out.json")])
            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads((tmp / "out.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["commit_id"], head)
            self.assertEqual(payload["comments"][0]["line"], 2)

    def test_unreadable_range_without_pr_is_fatal_and_terse(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            (tmp / "findings.json").write_text(json.dumps(
                {"body": "s", "comments": [good_comment()]}), encoding="utf-8")
            proc = self.run_cli(["--findings", str(tmp / "findings.json"),
                                 "--base-ref-oid", "1" * 40, "--head-ref-oid", "2" * 40,
                                 "--cwd", str(tmp / "missing-dir"), "--out", str(tmp / "out.json")])
            self.assertEqual(proc.returncode, 2)
            self.assertIn("FATAL ERROR", proc.stderr)
            self.assertNotIn("usage: git diff", proc.stderr)

    def test_pin_drift_is_caught_without_pr_mode(self):
        """A caller-supplied head that differs from the payload pin must fail."""
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            payload = {"commit_id": "b" * 40, "body": "Summary.",
                       "comments": [{"path": "src/physics.F90", "line": 12, "side": "RIGHT",
                                     "body": "**[Correctness]: Guard**\n\nText."}]}
            (tmp / "payload.json").write_text(json.dumps(payload), encoding="utf-8")
            proc = self.run_cli(["--check", str(tmp / "payload.json"),
                                 "--head-ref-oid", "a" * 40])
            self.assertEqual(proc.returncode, 1, proc.stderr)
            self.assertIn("commit-drift", proc.stderr)

    def test_check_without_a_head_reports_that_the_pin_was_unverified(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            payload = {"commit_id": "b" * 40, "body": "Summary.", "comments": []}
            (tmp / "payload.json").write_text(json.dumps(payload), encoding="utf-8")
            proc = self.run_cli(["--check", str(tmp / "payload.json")])
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("pin-unverified", proc.stderr)

    def test_both_diff_sources_failing_is_fatal_for_pr_mode(self):
        head = "aaaa222233334444555566667777888899990000"
        plan = json.dumps({"headRefOid": head, "baseRefOid": "1" * 40})
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            bin_dir = tmp / "bin"
            bin_dir.mkdir()
            stub = bin_dir / "gh"
            stub.write_text(
                "#!/bin/sh\n"
                'case "$1 $2" in\n'
                f'  "pr view") printf %s \'{plan}\' ;;\n'
                '  *) echo "gh: Sorry, the diff exceeded the maximum number of lines (20000)" >&2; '
                "exit 1 ;;\n"
                "esac\n",
                encoding="utf-8")
            stub.chmod(0o755)
            (tmp / "findings.json").write_text(json.dumps(
                {"body": "s", "comments": [good_comment()]}), encoding="utf-8")
            env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
            proc = subprocess.run([sys.executable, str(SCRIPT), "--findings",
                                   str(tmp / "findings.json"), "--pr", "7",
                                   "--out", str(tmp / "out.json")],
                                  cwd=tmp, env=env, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 2, proc.stderr)
            self.assertIn("cannot read the pinned diff", proc.stderr)
            self.assertIn("exceeded the maximum number of lines", proc.stderr)
            self.assertFalse((tmp / "out.json").exists())

    def test_falls_back_to_gh_when_the_range_is_not_local(self):
        """gh can supply the diff, and the builder says the pin was not local."""
        head_oid = "aaaa222233334444555566667777888899990000"
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            (tmp / "diff.patch").write_text(ADDED_DIFF, encoding="utf-8")
            bin_dir = tmp / "bin"
            bin_dir.mkdir()
            stub = bin_dir / "gh"
            stub.write_text(
                "#!/bin/sh\n"
                'case "$1 $2" in\n'
                f'  "pr view") printf %s \'{{"headRefOid":"{head_oid}","baseRefOid":"{"1" * 40}"}}\' ;;\n'
                f'  "pr diff") cat "{tmp}/diff.patch" ;;\n'
                '  *) exit 0 ;;\n'
                "esac\n",
                encoding="utf-8")
            stub.chmod(0o755)
            (tmp / "findings.json").write_text(json.dumps(
                {"body": "s", "comments": [good_comment(line=11)]}), encoding="utf-8")
            env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
            proc = subprocess.run([sys.executable, str(SCRIPT), "--findings", str(tmp / "findings.json"),
                                   "--pr", "7", "--out", str(tmp / "out.json")],
                                  cwd=tmp, env=env, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("gh-fetched diff", proc.stderr)
            payload = json.loads((tmp / "out.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["commit_id"], head_oid)


if __name__ == "__main__":
    unittest.main()
