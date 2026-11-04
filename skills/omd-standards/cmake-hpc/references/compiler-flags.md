# Compiler and Linker Flag Hygiene Across GNU, IntelLLVM, and Cray

Flags are a portability contract on an HPC machine: the same `CMakeLists.txt`
must produce a correct build under `PrgEnv-gnu`, `PrgEnv-intel`, and
`PrgEnv-cray`, and CI usually only exercises one of them. Keep every
compiler-specific string inside a generator expression or a vendor table, and
never edit `CMAKE_*_FLAGS_*` from inside a component.

## Vendor identities in CMake

| Launcher | `CMAKE_<LANG>_COMPILER_ID` | Notes |
|---|---|---|
| `gnu` | `GNU` | `gfortran` and friends |
| `intel` | `IntelLLVM` (oneAPI) | `ifx`/`icpx`; classic `Intel` (`ifort`/`icpc`) is the legacy ID |
| `nvidia` | `NVHPC`, sometimes `Clang` | NVHPC/`nvfortran` vs its LLVM-based lineage; older PGI is `PGI` |
| `aocc` | `Clang`-derived or `AOCl`, depending on CMake version | Verify it on the machine, do not assume |
| `cray` | `Cray`, and `CrayClang` for its Clang-based family | `CrayLinuxEnvironment` is a *system* value, not a compiler ID |

CMake does not define these vendor names uniformly across versions, and the
wrappers hide the real compiler behind them. Never harden a flag block on a
vendor ID that has only been seen on one machine: print `CMAKE_<LANG>_COMPILER_ID`,
`CMAKE_<LANG>_COMPILER_VERSION`, and the CMake version into the configure summary
(`references/ecbuild.md`) and gate flags on what the configured toolchain
actually reports. Anything that *parses* compiler output (`-warn` gremlins
settings, `check_fortran_source_compiles` patterns, `PASS_REGULAR_EXPRESSION` on
a runtime message) must be re-validated under a newer vendor release, because
diagnostic strings change even when the language level is the same.

## Per-vendor flag pattern

```cmake
target_compile_options( mom6physics PRIVATE
  $<$<COMPILE_LANG_AND_ID:Fortran,GNU>:-ffree-line-length-none -fno-range-check>
  $<$<COMPILE_LANG_AND_ID:Fortran,IntelLLVM>:-Mfree -fpp>
  $<$<COMPILE_LANG_AND_ID:Fortran,Cray>:-Mfree>
  $<$<COMPILE_LANG_AND_ID:Fortran,NVIDIA>:-Mfree -Minf=0 >
  -Wall )
```

The rules:

1. `target_compile_options`, not `CMAKE_Fortran_FLAGS`. Appending to a global
   variable breaks every dependency added later — including the ones in a bundle —
   and cannot express language or vendor.
2. One flag per generator expression keyed on
   `$<COMPILE_LANG_AND_ID:lang,VendorID>`; never a bare
   `if( CMAKE_Fortran_COMPILER_ID STREQUAL "GNU" )` that leaks flags into
   `add_subdirectory` children.
3. Never pass a vendor flag "for information" through `add_compile_options`
   unconditionally — an unknown flag on the site's other toolchains is a hard
   compile error, and on Cray wrappers it frequently arrives during the
   link step of an unrelated target.

The classic Intel→IntelLLVM trap — `ifx` accepts `-qopenmp`/`-fpp` but its
diagnostic strings differ from `ifort` — means anything that *parses* compiler
output (`ERROR`/`FATAL ERROR` patterns in `check_c_source_compiles`, a `-warn`
gremlins list, a test using `PASS_REGULAR_EXPRESSION` against a runtime message)
has to be re-validated under `newer` Intel. Vendor names are CMake-version
dependent; validate them against the CMake actually used to build. (`Intel
oneAPI` is called `IntelLLVM` in `CMAKE_<LANG>_COMPILER_ID`; classic `Intel`
(`ifort`/`icpc`) is the legacy ID and should still be accepted, because WCOSS and
NVIDIA-superbuild scripts still use it.)

## OpenMP

Do not hardcode a flag; ask the toolchain:

```cmake
find_package( OpenMP COMPONENTS C Fortran REQUIRED )
target_link_libraries( mom6physics PRIVATE OpenMP::OpenMP_Fortran )
```

`ecbuild` ships the same table in `ecbuild_find_omp`:

| Vendor | OpenMP flag | stubs |
|---|---|---|
| GNU | `-fopenmp` | `-fno-openmp` |
| Cray | `-homp` | `-hnoomp` |
| XL | `-qsmp=omp` | `-qsmp=noomp` |
| Intel | `-qopenmp` | `-qopenmp-stubs` |

Two HPC-specific consequences:

- `-fopenmp` changes both compile **and** link lines; use the imported target so
  the linker is configured too. Hand-placing it in `CMAKE_EXE_LINKER_FLAGS`
  produces a link that works until an OpenMP-aware dependency is added.
- `-qopenmp-stubs` / `-fno-openmp` are for libraries built *without* threading
  that must link into threaded executables — a real need on some mixes. Use them
  deliberately and comment why.

## Fortran-specific correctness flags

Recommended for every physics/dynamics library, in debug and CI builds (in
`<CMAKE_BUILD_TYPE>`-scoped, vendor-keyed form):

- bounds and undefined-use checking: names for these differ by vendor
  (`-fcheck=bounds`/`-fbacktrace` for `GNU`, `-check bounds -traceback` for the
  Intel family, `-Rb` for `Cray`) — enable them in a debug build and keep the
  spelling inside a generator expression (see above)
- free/fixed form and line-length handling stated explicitly
  (e.g. `-ffree-line-length-none`, `-Mfree`) — never rely on a default that
  changed between vendor versions
- floating-point exception trapping (`-ffpe-trap=...` on GNU, `-fpe0` on the
  Intel family, `-TRAP` on `Cray`) in a *test* build, so a NaN halts at the
  faulting unit instead of propagating into a forecast field
- warning *suppressions* only as `-Wno-...`-style strings with a comment naming
  the exact warning being silenced and why, never a blanket `-w`/`-nowarn`

Release and operational builds must not depend on `-ffast-math`/`-Ofast`:
reassociation changes reduction order, and EE2 requires results to be
reproducible across reruns of the same build. If a component opts into
contraction or vectorization-aggressive flags, gate that behind an
`ecbuild_add_option` feature so a baseline comparison is always available.

## Cray and module-stack details

- Use the wrappers (`cc`, `CC`, `ftn`) as the compilers; then pass
  `find_package( MPI )` the wrapper, never an MPICH path from a module you did
  not load. The `CRAYPE_LINK_TYPE` cache variable (`dynamic` for a job that
  loads modules at run time, `static` for a self-contained image) must match the
  delivery method — a `static` link under a job that loads a newer libsci fails
  at run time, not at build time.
- Do not put `-l`/`-L` strings in `CMakeLists.txt` to work around a wrapper
  problem; that hides a module-stack error and produces a binary that links
  against the login node's libraries.
- `CMAKE_*_FLAGS_INIT` may be set in a toolchain file, but a component that
  assumes those initializations without checking is fragile — print
  `CMAKE_Fortran_COMPILER_ID`/`_VERSION` in the configure summary (see
  `ecbuild_print_summary`).

## Style gates that keep flags reviewable

- A `cmake/` module owns the toolchain logic; component `CMakeLists.txt` files
  only consume it. Reviewers should see no vendor `if` chains in a component.
- Any new flag must state in the diff why it is needed, and on which vendor(s)
  it was exercised.
- Prefer `ecbuild_compile_options( LANG ... DEBUG ... )` /
  `ecbuild_purge_compiler_flags` / `ecbuild_remove_fortran_flags` over bespoke
  filter lists or string surgery.
- `check_c_source_compiles`/`check_fortran_source_runs` results, not
  compiler-ID guesses, decide whether an optional feature is available.
