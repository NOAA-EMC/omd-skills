"""Offline tests for the pr-review context collector.

The collector normally talks to GitHub; here a stub ``gh`` replays the three
shapes it consumes (a plan object, GraphQL review data, REST lists) so the logic
that matters can be asserted without network: revision pinning (including the
merge base when the base branch has advanced), local-first diffs, and the
partial-failure exit code.
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
SCRIPT = REPO / "skills/code-review/pr-review/scripts/collect_review_context.sh"

GH_STUB = r'''#!/usr/bin/env python3
"""Stub gh: replays fixtures from $GH_FIX, filtered through the real jq."""
import json
import os
import subprocess
import sys

argv = sys.argv[1:]
joined = " ".join(argv)
fix = os.environ["GH_FIX"]

for needle in os.environ.get("GH_MISSING", "").split():
    if needle in joined:
        sys.stderr.write(f"gh: simulated failure for {needle}\n")
        sys.exit(1)


def emit(text):
    if "--jq" in argv:
        expr = argv[argv.index("--jq") + 1]
        proc = subprocess.run(["jq", "-r", expr], input=text, capture_output=True, text=True)
        if proc.returncode != 0:
            sys.exit(3)
        sys.stdout.write(proc.stdout)
        return
    sys.stdout.write(text)


def fixture(name):
    with open(os.path.join(fix, name), encoding="utf-8") as handle:
        return handle.read()


if argv[:2] == ["pr", "view"]:
    emit(fixture("plan.json"))
elif argv[:2] == ["pr", "diff"]:
    if os.path.exists(os.path.join(fix, "no_remote_diff")):
        sys.stderr.write('gh: Sorry, the diff exceeded the maximum number of lines (20000) '
                         '{"documentation_url":"https://docs.github.com/rest/pulls/pulls'
                         '#get-a-pull-request-diff","message":"Sorry, the diff exceeded the '
                         'maximum number of lines (20000)","status":"406"}\n')
        sys.exit(1)
    emit(fixture("remote.patch"))
elif argv[:2] == ["run", "list"]:
    emit(fixture("runs.json"))
elif argv[:2] == ["api", "graphql"]:
    emit(fixture("threads.json" if "reviewThreads" in joined else "reviews_graphql.json"))
elif argv[:2] == ["api", "repos/o/r/pulls/7"]:
    emit(fixture("pull.json"))
elif argv[:1] == ["api"] and "/commits" in joined:
    emit(fixture("commits.json"))
elif argv[:1] == ["api"] and "/comments" in joined:
    emit(fixture("comments.json"))
else:
    sys.stderr.write(f"stub gh: unmatched call: {joined}\n")
    sys.exit(1)
'''


def git(repo, *args, env=None):
    return subprocess.run(["git", *args], cwd=repo, env=env, capture_output=True,
                          text=True, check=True).stdout.strip()


class CollectorCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for tool in ("jq", "git", "bash"):
            if shutil.which(tool) is None:
                raise unittest.SkipTest(f"{tool} is required")
        if not SCRIPT.exists():
            raise unittest.SkipTest(f"{SCRIPT} is missing")

    def make_repo(self, repo):
        """Branch point A, head B branched from A, base advanced to C."""
        env = {**os.environ, "GIT_AUTHOR_DATE": "@0 +0000", "GIT_COMMITTER_DATE": "@0 +0000",
               "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        git(repo, "init", "-q", env=env)
        base_branch = git(repo, "symbolic-ref", "--quiet", "--short", "HEAD", env=env)
        (repo / "kern.F90").write_text("a\nb\nc\n", encoding="utf-8")
        git(repo, "add", "-A", env=env)
        git(repo, "commit", "-qm", "branch point", env=env)
        point = git(repo, "rev-parse", "HEAD", env=env)

        git(repo, "checkout", "-q", "-b", "pr", env=env)
        (repo / "kern.F90").write_text("a\nnew\nb\nc\n", encoding="utf-8")
        git(repo, "add", "-A", env=env)
        git(repo, "commit", "-qm", "add new line", env=env)
        head = git(repo, "rev-parse", "HEAD", env=env)

        git(repo, "checkout", "-q", base_branch, env=env)
        (repo / "other.F90").write_text("x\n", encoding="utf-8")
        git(repo, "add", "-A", env=env)
        git(repo, "commit", "-qm", "base moved", env=env)
        base_tip = git(repo, "rev-parse", "HEAD", env=env)
        git(repo, "checkout", "-q", "pr", env=env)
        return point, base_tip, head, env

    def run_collector(self, missing="", no_remote_diff=False):
        tmp = Path(self.tmp.name)
        repo = tmp / "repo"
        repo.mkdir()
        point, base_tip, head, git_env = self.make_repo(repo)
        fix = tmp / "fix"
        fix.mkdir()
        plan = {"number": 7, "url": "https://github.com/o/r/pull/7", "title": "Add a line",
                "author": "dev", "state": "OPEN", "isDraft": False, "baseRefName": "base",
                "headRefName": "pr", "id": "NODEID777",
                "baseRefOid": base_tip, "headRefOid": head,
                "changedFiles": 1, "additions": 1, "deletions": 0,
                "files": [{"path": "kern.F90", "additions": 1, "deletions": 0}],
                "headRepository": {"name": "r"}, "headRepositoryOwner": {"login": "fork"},
                "reviewDecision": "REVIEW_REQUIRED",
                "statusCheckRollup": [{"name": "build", "status": "COMPLETED",
                                       "conclusion": "SUCCESS", "detailsUrl":
                                       "https://github.com/o/r/actions/runs/1/job/1"}]}
        (fix / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
        (fix / "pull.json").write_text(json.dumps(
            {"number": 7, "body": "Summary", "head": {"sha": head, "repo": {"full_name": "fork/r"}}}),
            encoding="utf-8")
        (fix / "commits.json").write_text(json.dumps([{"sha": head, "commit": {
            "message": "add new line\n\ntext", "author": {"date": "2026-01-01T00:00:00Z"}},
            "parents": [{"sha": point}]}]), encoding="utf-8")
        (fix / "threads.json").write_text(json.dumps({"data": {"node": {"reviewThreads": {
            "pageInfo": {"hasNextPage": False},
            "nodes": [{"id": "T1", "isResolved": False, "isOutdated": False, "path": "kern.F90",
                       "line": 2, "originalLine": 2, "subjectType": "line",
                       "comments": {"nodes": [{"databaseId": 11, "path": "kern.F90", "line": 2,
                                               "originalLine": 2, "outdated": False,
                                               "subjectType": "line", "publishedAt":
                                               "2026-01-02T00:00:00Z",
                                               "body": "existing nit", "author": {"login": "other"}}]}}]}}}}),
            encoding="utf-8")
        (fix / "reviews_graphql.json").write_text(json.dumps(
            {"data": {"node": {"viewerLatestReview": {"id": "R4", "state": "PENDING",
                                                       "body": "wip", "submittedAt": None},
                                "reviews": {"nodes": [{"databaseId": 4, "state": "PENDING",
                                                       "body": "wip", "submittedAt": None,
                                                       "author": {"login": "reviewer"},
                                                       "comments": {"nodes": []}},
                                                      {"databaseId": 5, "state": "COMMENTED",
                                                       "body": "notes", "author": {"login": "reviewer"},
                                                       "submittedAt": "2026-01-02T00:00:00Z",
                                                       "comments": {"nodes": [{"databaseId": 11,
                                                                                "path": "kern.F90",
                                                                                "line": 2}]}}]}}}}),
            encoding="utf-8")
        (fix / "comments.json").write_text(json.dumps([{"id": 11, "user": {"login": "reviewer"},
            "path": "kern.F90", "line": 2, "original_line": 2, "side": "RIGHT",
            "subject_type": "line", "commit_id": head, "original_commit_id": head,
            "in_reply_to_id": None, "pull_request_review_id": 5, "created_at": "2026-01-02T00:00:00Z",
            "updated_at": "2026-01-02T00:00:00Z", "body": "existing nit",
            "diff_hunk": "@@ -1,3 +1,4\n context\n+new\n context"}]), encoding="utf-8")
        (fix / "runs.json").write_text(json.dumps([
            {"databaseId": 1, "name": "build-and-test", "status": "completed",
             "conclusion": "success", "event": "pull_request", "workflowName": "CI",
             "headSha": head, "createdAt": "2026-01-01T00:00:00Z"},
            {"databaseId": 2, "name": "build-and-test", "status": "completed",
             "conclusion": "failure", "event": "push", "workflowName": "CI",
             "headSha": "9" * 40, "createdAt": "2026-01-01T00:00:00Z"}]),
            encoding="utf-8")

        if no_remote_diff:
            (fix / "no_remote_diff").write_text("", encoding="utf-8")
        (fix / "remote.patch").write_text(
            "diff --git a/kern.F90 b/kern.F90\n--- a/kern.F90\n+++ b/kern.F90\n"
            "@@ -1,3 +1,4 @@\n a\n+new\n b\n c\n", encoding="utf-8")
        bindir = tmp / "bin"
        bindir.mkdir()
        stub = bindir / "gh"
        stub.write_text(GH_STUB, encoding="utf-8")
        stub.chmod(0o755)
        # git_env carries a full copy of os.environ, so overlay PATH last.
        self.env = {**os.environ, **git_env, "GH_FIX": str(fix), "GH_MISSING": missing,
                    "PATH": f"{bindir}{os.pathsep}{os.environ['PATH']}"}
        outdir = tmp / "out"
        proc = subprocess.run(["bash", str(SCRIPT), "7", "o/r", str(outdir)], cwd=repo,
                              env=self.env, capture_output=True, text=True)
        self.proc = proc
        self.out = outdir
        self.fix = fix
        self.repo = repo
        self.shas = {"point": point, "base": base_tip, "head": head}
        return proc

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def read(self, name):
        return (self.out / name).read_text(encoding="utf-8")

    def test_complete_collection_writes_every_artefact(self):
        proc = self.run_collector()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        for name in ("plan.json", "pull.json", "commits.json", "threads.json", "submitted.json",
                     "reviews.json", "checks.json", "runs.txt", "diff.patch", "diff.pinned.patch",
                     "diff.txt", "files.txt", "pin.txt", "log.txt"):
            self.assertTrue((self.out / name).exists(), f"missing {name}")

    def test_pin_records_all_three_revisions_and_prefers_the_merge_base(self):
        self.run_collector()
        pin = dict(line.split("=", 1) for line in self.read("pin.txt").strip().splitlines())
        self.assertEqual(pin["BASE_OID"], self.shas["base"])
        self.assertEqual(pin["HEAD_OID"], self.shas["head"])
        self.assertEqual(pin["MERGE_BASE"], self.shas["point"])
        self.assertIn("base branch advanced", self.read("log.txt"))

    def test_local_objects_drive_the_diff(self):
        self.run_collector()
        self.assertIn("built locally", self.read("log.txt"))
        diff = self.read("diff.pinned.patch")
        self.assertIn("+++ b/kern.F90", diff)
        self.assertNotIn("other.F90", diff, "base-side commits must not appear in the PR diff")
        self.assertIn("kern.F90", self.read("files.txt"))

    def test_existing_triage_data_is_captured(self):
        self.run_collector()
        submitted = json.loads(self.read("submitted.json"))
        self.assertEqual(submitted[0]["id"], 11)
        self.assertEqual(submitted[0]["commit_id"], self.shas["head"])
        reviews = json.loads(self.read("reviews.json"))
        self.assertEqual(reviews["viewer"]["state"], "PENDING")
        self.assertEqual([r["state"] for r in reviews["reviews"]], ["PENDING", "COMMENTED"])
        self.assertIn("draft (PENDING) reviews", self.read("log.txt"))
        threads = json.loads(self.read("threads.json"))
        self.assertEqual(threads["data"]["node"]["reviewThreads"]["nodes"][0]["id"], "T1")

    def test_ci_rows_are_filtered_to_the_pinned_head(self):
        self.run_collector()
        runs = self.read("runs.txt")
        self.assertIn("1\tcompleted\tsuccess\tpull_request\tCI", runs)
        self.assertNotIn("9999999", runs)

    def test_checks_are_derived_from_the_plan(self):
        self.run_collector()
        checks = json.loads(self.read("checks.json"))
        self.assertEqual(checks[0]["name"], "build")

    def test_a_graphql_failure_is_partial_not_silent(self):
        proc = self.run_collector(missing="graphql")
        self.assertEqual(proc.returncode, 3)
        self.assertIn("WARN", proc.stderr + self.read("log.txt"))

    def test_a_run_list_failure_is_partial(self):
        proc = self.run_collector(missing="run list")
        self.assertEqual(proc.returncode, 3)
        self.assertIn("no rows above", self.read("runs.txt"))

    def test_an_unreadable_pr_is_fatal(self):
        proc = self.run_collector(missing="pr view")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("cannot read PR", proc.stderr)

    def test_remote_diff_failure_falls_back_to_the_local_range(self):
        """HTTP 406 on a huge diff must not lose the review context."""
        proc = self.run_collector(no_remote_diff=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("HTTP 406", self.read("log.txt"))
        self.assertEqual(self.read("diff.patch"), self.read("diff.pinned.patch"))


if __name__ == "__main__":
    unittest.main()
