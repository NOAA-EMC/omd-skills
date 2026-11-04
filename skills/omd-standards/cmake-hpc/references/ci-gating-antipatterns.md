# CI False Confidence and Test-Gating Anti-Patterns

A green CI job that never executed the assertions is worse than a red one: it
certifies behaviour nobody has checked. In an operational weather model, a
"passing" build whose physics tests silently skipped is a latent forecast bug
with an audit trail that says it was tested. Every rule below has the same
shape: **the skip has to be visible, or the run has to be hard-blocked**.

## Anti-pattern 1 — `if( EXISTS ... )` around a test

```cmake
# ANTI-PATTERN
if( EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/data/obs_4dvar.nc )
  ecbuild_add_test( TARGET test_obs SOURCES obs_test.F90 LIBS dam )
endif()
```

The large input is not in the repository (LFS, scratch, or a project data
directory), so the `add_test` line is never reached. CTest reports one test
(`ctest -N` will not even list it), CI reports `100% tests passed`, and nobody
learns that `obs_test` did not run. Concretely:

- `ecbuild_add_test` records its test only inside
  `if( HAVE_TESTS AND <condition> AND <enabled> )`, so a false condition or an
  off switch drops it with no CTest-visible trace.
- `ecbuild_setup_test_framework` defines the `TESTS` feature (`HAVE_TESTS`); a
  configure with `-DENABLE_TESTS=OFF` disables *every* test in the tree and the
  build still succeeds.
- `ctest`'s own skip mechanism (`SKIP_REGULAR_EXPRESSION`) is a *test-run-time*
  match. A configure-time `if(EXISTS)` bypasses CTest entirely.

### Detection greps

```bash
# add_test / ecbuild_add_test nested inside an EXISTS/FOUND condition
rg -n -U 'if\s*\(\s*(EXISTS|.*_FOUND)[^)]*\)[\s\S]{0,600}?(add_test|ecbuild_add_test)' --glob 'CMakeLists.txt' --glob '*.cmake'
# tests that vanish from the plan
rg -n 'ecbuild_add_test' tests | wc -l      # compare against `ctest -N | tail -1`
```

### Acceptable form (choose one, never a silent skip)

1. **Synthetic micro-fixture.** Commit a tiny input the test can always read,
   and assert on it:

   ```cmake
   ecbuild_add_test( TARGET oops_micro
                     SOURCES micro_test.F90
                     LIBS oops
                     RESOURCES fixtures/micro.nc )   # always present, always run
   ```

   Generate the fixture at build time when a file truly must not be committed
   (`ncgen`/`ncks`/`python tools/make_micro.py` as an `add_custom_command`), so
   the "data" is deterministic and small.

2. **Explicit warning plus a gated baseline.** When a large-data test may only
   run on one machine, make the *absence* loud and make CI require it where it
   is expected:

   ```cmake
   if( EXISTS "${OBS_FILE}" )
     ecbuild_add_test( TARGET obs_fv3 SOURCES obs_test.F90 ...)
   else()
     message(WARNING "FATAL-candidate: OBS_FILE=${OBS_FILE} not found; obs_fv3 is NOT registered")
   endif()
   ```

   then have the CI/ush job assert the expected test count or label set, so the
   warning cannot be ignored: `ctest -L ops --output-on-failure` must run *N*
   tests, and the job fails if `ctest -N -L ops` reports fewer.

3. **Hard failure.** If a component's CI is defined to need the fixture, do
   `message( FATAL_ERROR ... )` when it is missing. A configure error is
   recoverable information; a green run is not information at all.

`SKIP_REGULAR_EXPRESSION` belongs to the run-time category — acceptable for
"the filesystem or quota made this run impossible", never for "this branch did
not ship the data". Because any output matching the skip pattern turns the test
green, keep the pattern narrow (`SKIP_REGULAR_EXPRESSION`) and list it in the
test's `LABELS` or a comment so a reviewer can see what a skip looks like.

## Anti-Pattern Gate (blocking checklist)

Before approving any CMake/ecbuild change, confirm:

- [ ] Every registered test appears in `ctest -N` on a repository checkout, no
      data staging, on the CI runner. The test *count* is compared against an
      expected baseline as part of the CI script.
- [ ] No `if( EXISTS ... )`/`if( *_FOUND )` wraps `add_test` or
      `ecbuild_add_test` without a `message(WARNING ...)` naming the test that
      was dropped, or — better — a committed micro-fixture instead.
- [ ] No `set_tests_properties(... PROPERTIES IGNORE_SKIP TRUE)` or
      `SKIP_REGULAR_EXPRESSION` used to neutralise a real failure; skips must
      mean "the environment could not", not "the repository did not provide X".
- [ ] Tests requiring MPI run in CI with the MPI runtime present: `MPI <n>` with
      no `MPIEXEC` discovered is an `ecbuild_debug` line and a silently dropped
      test, and `MPI 1` quietly becomes a serial run, so a missing
      `mpiexec`/`srun` changes what is measured without failing the build.
- [ ] `-DENABLE_TESTS=OFF` does not appear in CI (or appears only in an
      explicitly-labelled "build-only" job, never as the merge gate).
- [ ] `ctest --output-on-failure` in CI (not `ctest | cat` or `|| true`), and the
      job's exit status is CTest's own.
- [ ] Valgrind/memcheck, if used, has `--error-exitcode=1` (the ecbuild default
      in `ecbuild_setup_test_framework` is exactly that); without it, memcheck
      findings never fail the job.

## Manual-only hooks

A pre-commit hook that fires only when a `.yaml` file is edited does not run on
a `CMakeLists.txt` commit, and "CI green + no local lint" makes the formatting
gate advisory. The same false confidence comes from `stages: [manual]` hooks,
from a job matrix with `fail-fast: true` (the first red leg hides the rest), and
from steps written as `run: ... || true`. Check *when* each gate executes, not
that it exists:

```bash
rg -n 'always_run|pass_filenames|files:|exclude:|stages:' .pre-commit-config.yaml
```

For merge-blocking checks, prefer an explicit CI step (`ctest`, `cmake --build`,
the format gate, `python3 tools/validate_skills.py`) over a local hook.

## CTest hygiene

- `enable_testing()` (or `include( CTest )`) in the top-level `CMakeLists.txt`
  of any tree with tests. Verified with CMake 3.x: a `add_test()` in a
  subdirectory of a project that never enabled testing configures and generates
  *cleanly*, and `ctest -N` then reports `Total Tests: 0` — a completely green,
  completely empty test run. Checked by `scripts/check_cmake_antipatterns.py`.
- Label every test (`LABELS unit` / `phys` / `ops`): `ctest -L` is how the gate
  above is enforced, and `ctest -LE exclude` is how a machine opts out *visibly*.
- Use `PROCESSORS`/`RESOURCE` (plain CTest) or ecbuild's `MPI`/`OMP`
  rather than a hard-coded `mpirun -np 2` inside a shell test written by hand:
  a `TYPE SCRIPT` test that self-launches MPI cannot be scheduled and will
  oversubscribe on a shared node.
- Set `ENVIRONMENT` explicitly where a test needs to know the build, not the
  environment of the invoking shell; `WORKING_DIRECTORY` is per-test, so use
  `RESOURCES`/fixtures and never `cd ..` inside a test script.
- `TIMEOUT` on every test that touches a network or a large file; the HPC
  queue kills the whole job otherwise, which looks like a build failure.

## EE2 alignment

A CI job that hides a skip is the build-side equivalent of an ex-job exiting 0
despite an `err_chk`-visible failure. The EE2 rule set (`skills/omd-standards/ee2-standards`)
applies the same way here: emit `FATAL ERROR` (or `message( FATAL_ERROR ... )`)
where a required input is missing, and never let a component "pass" by
reaching its own exit 0 through a skipped branch.
