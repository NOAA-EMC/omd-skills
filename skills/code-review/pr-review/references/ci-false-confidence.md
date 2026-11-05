# CI False Confidence and Conditional Test Gating

A green pull request check is evidence that *a job ran*, not that *the tests ran*.
This stage proves, per check, what actually executed on the pinned head.

## The two checks that matter

1. **Did a run exist for the pinned commit?**

   ```bash
   gh run list --repo "$SCOPE" --limit 100 --json databaseId,headSha,status,conclusion,name \
     --jq --arg sha "$HEAD_OID" 'map(select(.headSha == $sha))'
   gh pr checks "$PR" --repo "$SCOPE"
   ```

   No run for `headRefOid` means the checks being displayed belong to an earlier
   commit of the branch -- the usual situation after a force push while CI is
   queued, and the reason stage 1 pins before anything else.

2. **Did the job execute the tests it claims?** Success with a skipped, gated, or
   zero-count test run is a false pass. `Total Tests: 0` and
   `No tests were found!!!` both exit `0`, so the exit code proves nothing:

   ```bash
   gh run view "$RUN_ID" --log 2>/dev/null | grep -E 'Total Tests: 0|No tests were found|skipped|Skipped' | sort -u
   ```

## Detector list

Run these greps over the checkout at `headRefOid` (use `git grep` so the results
are revision-accurate), and read each hit before judging it.

| Pattern | Where | Why it is false confidence |
|---|---|---|
| `if( *EXISTS*` around `add_test` / `ecbuild_add_test` | `CMakeLists.txt`, `*.cmake` | the test is not registered when its input is absent, and an unregistered test cannot fail |
| `set(..._DATA` + `if(NOT EXISTS` | build files | same failure mode expressed as a variable |
| `add_test` without any `enable_testing()` / `include(CTest)` in the tree | build files | CMake configures and generates cleanly, `ctest -N` reports 0 tests |
| `BUILD_TESTING=OFF`, `ENABLE_TESTS=OFF`, ``-DCTEST_`` suppression in a configure step | `.github/workflows/*.yml`, build scripts | the pipeline that "passed" never built or enabled the tests |
| `continue-on-error: true`, `\|\| true`, `set +e` before a test step | workflows, scripts | a failure becomes a green check |
| `|| echo` / `|| exit 0` around a runner | scripts | same, one level down |
| `pytest.skip`, `@pytest.mark.skip`, `@pytest.mark.skipif`, `skipIf` | tests | a skip is not a pass; count them |
| `pre-commit` only in docs or `.pre-commit-config.yaml` with no job running it | repo root vs `.github/workflows/` | formatting/lint gates exist only on developer machines |
| `pytest -x` absent while the suite is sharded, or `fail-fast: false` | workflow | partial or non-failing results reported as complete |
| `actions/upload-artifact` with `if: always()` on a test job but no test summary | workflow | the artifact is the evidence, but nobody reads it |

```bash
git grep -nE 'if[[:space:]]*\([[:space:]]*(NOT[[:space:]]+)?EXISTS' -- '*CMakeLists.txt' '*.cmake'
git grep -nE 'enable_testing|include\(CTest\)' -- '*CMakeLists.txt' '*.cmake'
git grep -nE 'continue-on-error|\|\|[[:space:]]*(true|echo)|set \+e' -- '.github/workflows' '*.sh'
git grep -nE 'skip|skipif|xfail' -- 'tests' 'test' | head -40
grep -rn '\-\-hook-stage\|pre-commit' .github/workflows/ 2>/dev/null || echo "no pipeline runs pre-commit"
```

For the CMake side, `skills/omd-standards/cmake-hpc/scripts/check_cmake_antipatterns.py`
already implements the `silent-test-skip`, `condition-disable`, and
`no-enable-testing` rules plus the runner-masked patterns:

```bash
python3 skills/omd-standards/cmake-hpc/scripts/check_cmake_antipatterns.py "$TREE"
```

## Proving a test actually ran

From the checkout at the pinned head, prefer a count over an inference:

```bash
ctest --test-dir "$BUILD" -N | tail -1                                  # "Total Tests: N"
ctest --test-dir "$BUILD" -N | grep -c 'Test #[0-9]*:'                  # registered tests
ctest --test-dir "$BUILD" -R "$LABEL_OR_NAME" --output-on-failure        # executed
python3 -m pytest -q --collect-only 2>/dev/null | tail -1               # collected tests
```

A check whose log says `Total Tests: 0`, or whose `--output-on-failure` step is
missing, is reported under the `False confidence` category:

```markdown
**[False confidence]: The regression test does not run in CI**

`tests/regression/CMakeLists.txt:22` registers `ufs_smoke` only when
`$INPUT_FILE` exists, and the workflow checkout has no input file, so the test is
never added. The job still exits 0: CTest treats an empty suite as success. Every
later pass of this check therefore proves the build, not the regression.

**Suggested fix:**
Generate a small synthetic fixture in the repository and register the test
unconditionally, or `message(FATAL_ERROR ...)` when the real input is absent in a
CI build.

**Test:** `ctest --test-dir build -N` reports `Total Tests: 1` and
`ctest --test-dir build -R ufs_smoke --output-on-failure` executes it.
```

## What counts as a real fix

Ask what the gate does when the precondition is missing. Acceptable answers:

1. the test runs against a committed micro-fixture, so the assertion still executes;
2. configure or the job stops with a message naming the missing input;
3. the test is skipped **visibly and loudly**: `message(WARNING ...)` plus a
   recorded skip (`set_tests_properties(... PROPERTIES SKIP_TEST ...)` with a
   reason), or a CI step that marks the outcome `neutral`/annotated, and the
   gating variable is documented.

Not acceptable: a silent `else()` branch, an unregistered test, a runner that
swallows the exit status, or a comment saying "works on hera".

## EE2 and operational angle

The same reasoning applies to operational job scripts, where the false pass costs
a forecast cycle instead of a merge: a job must return a failing status when its
own verification did not run. Check the job script for postcondition tests that
assume products exist, and for `if [ -f ... ]` guards around the verification step
(`skills/omd-standards/ee2-standards/` covers the standard; the `Silent failure`
and `False confidence` categories carry the finding).
