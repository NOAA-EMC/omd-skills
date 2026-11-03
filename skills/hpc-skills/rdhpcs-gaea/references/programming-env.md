# Gaea Programming Environment Reference

Source: the Gaea user guide
(<https://docs.rdhpcs.noaa.gov/systems/gaea_user_guide.html>).

## Lmod

Environment modules are provided through **Lmod**, a Lua-based module system
that edits `PATH`, `LD_LIBRARY_PATH`, and `PKG_CONFIG_PATH` without creating
impossible package/version combinations.

| Command | Description |
|---------|-------------|
| `module -t list` | terse list of currently loaded modules |
| `module avail` | table of available modules |
| `module help <modulename>` | help for one module |
| `module show <modulename>` | environment changes a modulefile makes |
| `module spider <string>` | search **all** possible modules |
| `module load <modulename> [...]` | load module(s) |
| `module use <path>` / `module unuse <path>` | add/remove a modulefile search path |
| `module purge` | unload everything |
| `module reset` | back to system defaults |
| `module update` | reload current modules |

Dependency trap: `module avail` only lists modules compatible with what is
already loaded (a library needs its compiler family present). Use
`module spider`, `module spider <name>`, `module spider <name>/<version>`, or
`module spider <string>` to search the whole hierarchy.

## Cray Programming Environment (CPE)

CPE supplies compilers, scientific libraries, debuggers, and performance
tools. Within it, the Cray Compiling Environment (CCE) provides the `cc`, `CC`,
and `ftn` **compiler wrappers**; `PrgEnv-<compiler>` modules load a matching
toolchain (compiler + Cray MPICH + LibSci and friends) and define the wrappers
that automatically add include paths and link Cray libraries.

> **CPE is reaching its end of life at version 26.03.** Because of the EOL,
> the **C7 cluster no longer loads CPE by default** — the default programming
> environment is whatever is active when you log in. For legacy workflows the
> guide provides a `load_cpe` alias: `load_cpe` then select a previous CPE.

Always build MPI through the wrappers (`cc`/`CC`/`ftn`) rather than calling
`gcc` or `ifort` directly. To see what the wrapper actually does, compile a
file with the `-craype-verbose` flag, e.g. `CC -craype-verbose test.cpp` — it
prints the full include and link information.

## Compilers on Gaea

MPI implementation: **Cray MPICH**. A system/OS GCC also exists in `/usr/bin`
outside the module system.

| Vendor | Programming environment | Compiler module | C | C++ | Fortran |
|--------|----------------------|-----------------|---|-----|---------|
| AMD | `PrgEnv-aocc` | `aocc` | `cc` → clang | `CC` → clang++ | `ftn` → flang |
| Cray | `PrgEnv-cray` | `cce` | `cc` → craycc | `CC` → craycxx or crayCC | `ftn` → crayftn |
| GNU | `PrgEnv-gnu` | `gcc-native` | `cc` → gcc | `CC` → g++ | `ftn` → gfortran |
| Intel | `PrgEnv-intel` | `intel` | `cc` → icx | `CC` → icpx | `ftn` → ifort |
| NVIDIA | `PrgEnv-nvhpc` | `nvhpc` | `cc` → nvc | `CC` → nvc++ | `ftn` → nvfortran |

Notes from the guide: `gcc-native` replaced `gcc` in the December 2023 CPE
release (`gcc` = GCC packaged inside CrayPE, `gcc-native` = GCC outside it),
and NVIDIA replaced PGI — the NVHPC name has been deprecated since CPE 24.11.

## Dynamic Linking

Every executable built on Gaea is **dynamically linked** (ELF); static linking
is not the supported method. At run time the loader (`ld.so`) searches, in
order:

1. `RPATH` embedded in the executable,
2. directories in `LD_LIBRARY_PATH`,
3. directories in `/etc/ld.so.conf`.

The first matching library wins. Embed a path at link time:

```bash
cc -Wl,-rpath,/path/to/some/lib -L/path/to/some/lib -lsomelib myprogram.c -o myprogram
# several paths: -Wl,-rpath,/path/to/lib1:/path/to/lib2  (or repeat the option)
```

**The trap:** on CPE systems the loader always searches `/opt/cray/pe/lib64`
(default Cray libraries), so *swapping a module does not fully change the
run-time environment*. The guide's `cray-mpich` demonstration: build against
`cray-mpich/9.0.0` (MPICH 4.1.2) but run with the default 8.1.32/3.4a2 library
still found in `/opt/cray/pe/lib64`. Fixes:

- Preferred: set `RPATH` with `-Wl,-rpath,<path>` (higher precedence, explicit).
- Or prepend the Cray path at run time:
  `export LD_LIBRARY_PATH=${CRAY_LD_LIBRARY_PATH}:${LD_LIBRARY_PATH}` — the
  guide's example then runs the matching 9.0.0 library. Beware that a manually
  set `LD_LIBRARY_PATH` can also make you load an *unintended* library, since
  `LD_LIBRARY_PATH` outranks `/etc/ld.so.conf` (which lists `/opt/cray/pe/lib64`).

## Launching

`srun` is the default job launcher:

```bash
srun -A <project_id> -t 00:05:00 -p <partition> -N 2 -n 4 --ntasks-per-node=2 ./a.out
```

Common `srun` options: `-N` nodes; `-n` total MPI tasks (default 1);
`-c/--cpus-per-task` logical cores per task; `--cpu-bind=threads` (default and
recommended); `--threads-per-core` (default 1, 2 hardware threads per core —
must also be set in `sbatch`/`salloc`); `-m block:cyclic:cyclic` distribution
across nodes:sockets (L3 regions):cores; `--ntasks-per-node` (without `-n` it
requests that count per node, with `-n` it caps it).

## Debugging

- **Linaro DDT** — RDHPCS's recommended debugger for large parallel
  applications; breakpoints, stepping, variable inspection, attaching to
  running processes, memory debugging. Its remote-debugging feature connects a
  workstation client to the session (much faster than the on-system graphical
  client); setup guidance is on the fleet Debugging Software page.
- **GDB** — command-line debugger, available under all compiler families:
  `module load gdb`, then `gdb ./path_to_executable`.
- **GDB4HPC** (`gdb4hpc`) — HPE Cray's GDB-based parallel debugger; launches
  an application or attaches to one already started with `srun`, command-line
  mode. Part of the HPE Cray Programming Environment tool set.
- **Valgrind4hpc** — Valgrind-based memory-leak/error detection for parallel
  apps; deduplicates and aggregates messages across ranks and manages many
  Valgrind copies. Available under all compiler families:
  `module load valgrind4hpc`.

## Profiling

**HPE Performance Analysis Tools** — three interfaces: `Perftools-lite`,
`Perftools`, and `Perftools-preload`. The guide's `Perftools` example
(advanced interface, full traces with timelines):

```bash
module load PrgEnv-amd
module load perftools
export CXXFLAGS='-ggdb -O3 -std=c++17 -Wall'
export LD='CC'
export LDFLAGS="${CXXFLAGS}"
make clean
make pat_build -g io,mpi -w -f <executable>
```

`pat_build` creates an instrumented executable with `+pat` appended (e.g.
`hello_jobstep+pat`); running it traces HIP, I/O, MPI, and user functions into
a results folder (e.g. `hello_jobstep+pat+39545-2t`) that you read with
`pat_report hello_jobstep+pat+39545-2t` — function profiles, maximum function
times, load imbalance, energy/power detail, memory high-water mark, and more.

## Software Support Scope

Only modules under `/opt` and `/sw` are supported at the RDHPCS level.
Software you install in `/ncrc/home[12]/$USER/`, `/usw`, or `/ncrc/proj` is
supported by the project/user who installed it — and per the storage tips,
Conda/Python/Spack environments belong in those areas, never on GPFS.
