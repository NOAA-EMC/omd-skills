"""Tests for the pr-review skill's pending-only publisher.

The publisher is the only step that talks to GitHub with write access, so every
gate it claims is asserted here against a stub ``gh``. Tests are offline: the
stub replays recorded API shapes, including the failure modes (force-pushed
head, a payload that smuggles an ``event`` key, an API that somehow publishes
the review).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "skills/code-review/pr-review/scripts/post_pending_review.sh"

HEAD = "b" * 40
STALE = "a" * 40


def payload(valid=True, **overrides):
    data = {"commit_id": HEAD, "body": "Summary.",
            "comments": [{"path": "kern.F90", "line": 3, "body": "**[Correctness]: Guard**\n\nText."}]}
    if not valid:
        data["event"] = "REQUEST_CHANGES"
        data["commit_id"] = STALE
        data["comments"] = []
    data.update(overrides)
    return data


# A stub ``gh`` that emulates the three calls the publisher makes, filtered
# through the real jq when ``--jq`` is given. Canned responses are read from the
# environment so each test can pick a scenario.
GH_STUB = r"""#!/usr/bin/env python3
import json
import os
import subprocess
import sys

argv = sys.argv[1:]


def emit(text):
    if "--jq" in argv:
        expr = argv[argv.index("--jq") + 1]
        proc = subprocess.run(["jq", "-r", expr], input=text, capture_output=True, text=True)
        if proc.returncode != 0:
            sys.exit(proc.returncode)
        sys.stdout.write(proc.stdout)
        return
    sys.stdout.write(text)


head = os.environ.get("PR_HEAD", "")
if argv[:2] == ["pr", "view"]:
    emit(json.dumps({"headRefOid": head}))
elif argv[:2] == ["api", "user"]:
    emit(json.dumps({"login": "reviewer"}))
elif argv[:1] == ["api"]:
    path = argv[1]
    method = argv[argv.index("--method") + 1] if "--method" in argv else "GET"
    if "--paginate" in argv:
        reviews = [{"id": 5, "state": os.environ.get("REVIEW_STATE", "COMMENTED"),
                    "user": {"login": "reviewer"}}]
        emit(json.dumps(reviews))
    elif method == "PUT":
        emit(json.dumps({"id": 5}))
    elif method == "POST":
        if os.environ.get("CREATE_FAIL"):
            sys.stderr.write(json.dumps({"message": "Validation Failed",
                                         "errors": [{"message": "PullRequest.head sha mismatch"}],
                                         "documentation_url": "https://docs.github.com"}))
            sys.exit(1)
        emit(json.dumps({"id": 7, "state": os.environ.get("CREATE_STATE", "PENDING"),
                         "submitted_at": None, "html_url": "https://github.com/o/r/pull/7#discussion_r7"}))
    else:
        emit("{}")
else:
    emit("{}")
"""


class PublisherCase(unittest.TestCase):
    """Runs the publisher with a stubbed gh on PATH."""

    @classmethod
    def setUpClass(cls):
        for tool in ("bash", "jq"):
            if shutil.which(tool) is None:
                raise unittest.SkipTest(f"publisher tests stub gh, but need {tool}")
        if not SCRIPT.exists():
            raise unittest.SkipTest(f"{SCRIPT} is missing")

    def run_publisher(self, payload_data, *, pr_head=HEAD, review_state="COMMENTED",
                      create_state="PENDING", create_fail=False):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            bindir = tmp / "bin"
            bindir.mkdir()
            (bindir / "gh").write_text(GH_STUB, encoding="utf-8")
            (bindir / "gh").chmod(0o755)
            payload_path = tmp / "review_payload.json"
            payload_path.write_text(json.dumps(payload_data), encoding="utf-8")
            env = {**os.environ, "PATH": f"{bindir}{os.pathsep}{os.environ['PATH']}",
                   "PR_HEAD": pr_head, "REVIEW_STATE": review_state, "CREATE_STATE": create_state}
            if create_fail:
                env["CREATE_FAIL"] = "1"
            proc = subprocess.run(["bash", str(SCRIPT), "7", str(payload_path), "o/r"],
                                  env=env, capture_output=True, text=True)
            return proc, payload_path.read_text(encoding="utf-8")

    def test_valid_payload_is_posted_pending(self):
        proc, _ = self.run_publisher(payload())
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "7")
        self.assertIn("PENDING draft 7", proc.stderr)
        self.assertIn("gh api repos/o/r/pulls/7/reviews/7/events", proc.stderr)

    def test_a_payload_with_an_event_key_is_refused(self):
        proc, _ = self.run_publisher(payload(valid=False, commit_id=HEAD,
                                             comments=payload()["comments"]))
        self.assertEqual(proc.returncode, 1)
        self.assertIn('"event"', proc.stderr)

    def test_a_stale_pin_is_refused(self):
        proc, _ = self.run_publisher(payload(), pr_head=STALE)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("stale payload", proc.stderr)

    def test_an_empty_comment_set_is_refused(self):
        proc, _ = self.run_publisher(payload(comments=[]))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("no comments to post", proc.stderr)

    def test_an_existing_own_draft_is_refreshed_not_duplicated(self):
        proc, _ = self.run_publisher(payload(), review_state="PENDING")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "5")
        self.assertIn("refreshing draft 5", proc.stderr)
        self.assertIn("not edited", proc.stderr)

    def test_submitted_reviews_do_not_block_a_new_draft(self):
        proc, _ = self.run_publisher(payload(), review_state="APPROVED")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "7")

    def test_an_unexpected_published_state_is_an_error(self):
        proc, _ = self.run_publisher(payload(), create_state="APPROVED")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("UNEXPECTED state APPROVED", proc.stderr)

    def test_a_rejected_create_keeps_a_friendly_error(self):
        proc, _ = self.run_publisher(payload(), create_fail=True)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("gh api failed", proc.stderr)
        self.assertIn("anchor drifted", proc.stderr)


if __name__ == "__main__":
    unittest.main()
