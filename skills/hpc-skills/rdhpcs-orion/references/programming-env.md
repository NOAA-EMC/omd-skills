# Orion Programming Environment Reference

MSU-HPC publishes a module tree rather than a fixed compiler/MPI recommendation,
so this file teaches **discovery**: find what Orion actually offers today instead
of assuming a pairing that exists on another RDHPCS system.

---

## LMOD Hierarchical Modules

Lmod is a Lua-based module system used on Gaea, Ursa, Hera, and the MSU systems
Hercules and Orion. Because many packages depend on a specific compiler or MPI
library, Lmod uses a **hierarchical layout**: loading a compiler makes
compiler-dependent packages (MPI stacks, libraries) visible, and loading an MPI
stack makes MPI-dependent packages visible in turn. `module avail` therefore shows
only what is compatible with what you already have loaded — which is intentional.

```bash
module avail                    # what the current environment exposes
module list                     # what is loaded
module -t list                  # compact
module purge                    # start clean
module show <name>              # what a module actually sets
```

`module spider` searches the **entire** hierarchy, including modules hidden behind
unloaded dependencies. RDHPCS documents it fleet-wide and it is the right way to
find out whether Orion has a package at all:

```bash
module spider <pkg>
```

Do not carry a Gaea module name to Orion. Gaea is an HPE/Cray system whose
toolchain comes from `PrgEnv-*` modules; Orion has no Cray Programming Environment.

---

## NOAA Tooling on Orion

The NOAA helper commands live behind two modules. MSU documents this exact
sequence:

```bash
module avail
module load contrib noaatools
module list
```

That gives you `saccount_params`, `shpcrpt`, `reportFSUsage`, and the other NOAA
support commands. There is **no** `account_params` alias on the MSU systems.

---

## Compilers and MPI

MSU's own batch example for a benchmark build is:

```bash
module load intel <version>
module load impi <version>
srun -n $SLURM_NTASKS ./xhpl
```

Treat the version numbers as placeholders: enumerate what Orion offers with
`module avail` after loading the compiler, and pin the versions you build with so a
module default change does not silently break your job. Typical pattern:

```bash
module purge
module load intel                # or the compiler family your build needs
module avail                     # now the MPI stacks for that compiler appear
module load impi
module list                      # record what the build actually used
```

MPI-dependent packages (netCDF, PnetCDF, and similar) become visible only after an
MPI stack is loaded, so build in that order: compiler → MPI → libraries.

---

## Environment Variables Set by Modules

MSU warns that module-provided variables "may not be what you used on other
machines. Users should check and make sure." Their documented WRF example (written
for Hercules, apply the same discipline on Orion after checking `module show`) is
that `netcdf-c` and `netcdf-fortran` install in separate directories and expose
`NETCDF_C_ROOT` and `NETCDF_FORTRAN_ROOT`, while a build expecting a single
`NETCDF` root needs you to assemble one:

```bash
cp -r $NETCDF_C_ROOT/* $NETCDF/.
cp -r $NETCDF_FORTRAN_ROOT/* $NETCDF/.
```

Parallel netCDF exposes `PARALLEL_NETCDF_ROOT`, and a model built against it needs
`PNETCDF` defined or it compiles cleanly and then fails on parallel I/O:

```bash
export PNETCDF=$PARALLEL_NETCDF_ROOT
```

Check the variables your build system reads against what `module show` sets before
the first compile, not after a mysterious runtime failure.

---

## MPI Runtime Problems MSU Documents

**Node-memory crashes.** MSU's remedy: use more nodes, or fewer MPI tasks per node,
and make sure the node is not shared with other jobs by adding `#SBATCH --exclusive`.

**Intel MPI shared-memory heap.** On Hercules only, MSU documents large runs that
crash while small runs work, single-task runs work while multi-task runs crash. The
Intel compiler's default `I_MPI_SHM_HEAP_VSIZE` is 8192 MB; if it exceeds node
memory, MPI initialization fails with "unable to allocate shared memory". Redefine
it before `srun`, never above the node's memory. Orion's nodes have 192 GB, so a
default tuned for another system can be wrong here — check before copying an
environment across machines.

**Stack-size segfaults.** MSU documents this for both Orion and Hercules: the
default soft stack limit is **16KB**, and a program whose subroutine and function
locals exceed it segfaults. Raise it and verify inside the job script:

```bash
ulimit -s <stack_size>   # MSU's form; pick a size, don't just use "unlimited"
ulimit -s                # confirm it took
```

MSU explicitly says to set this **in the batch script and not in `~/.bashrc`**,
because putting it in the shell startup file "can cause unintended consequences".

---

## Thread Affinity

RDHPCS publishes no Orion-specific OpenMP affinity recipe. Use the portable Slurm
and OpenMP variables and verify the placement you actually got:

```bash
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
export OMP_PLACES=cores
export OMP_PROC_BIND=close
```

A node is 40 cores (2 x 20) at 2.40 GHz. For pure MPI use `--cpus-per-task=1`; for
OpenMP raise it to the thread count you want. Do not assume a threaded application
should use all 40 cores on a shared node — request the whole node with
`--exclusive` if you do.

---

## Python

RDHPCS documents the Orion load sequence explicitly, and it differs from the
NOAA-operated systems because the modules sit behind `contrib`:

```bash
module load contrib
module load rdhpcs-python      # or rdhpcs-conda
```

`module avail python` lists the available versions; loading one puts you in a conda
environment associated with that version. For `rdhpcs-conda` you do not need to
activate the environment.

The system-provided environment contains base Python only. Install what you need
into your own environment:

```bash
module load contrib
module load rdhpcs-conda
conda create -n myenv python=3.12
conda activate myenv
conda install -c conda-forge <pkg>
```

**conda-forge is the only channel RDHPCS approves fleet-wide**, and Miniforge is
their conda-forge installer if you want your own stack in `/work` rather than the
system module.

---

## Containers

Singularity containers are available to all users and projects on Ursa, Gaea, Hera,
MSU-HPC (Orion and Hercules), and PPAN. Orion requires an explicit module load —
unlike Hera and Ursa, where no load is needed:

```bash
module load singularity
singularity run /work/noaa/<project>/<user>/images/myimage.sif
```

Orion also offers Apptainer as a **Spack-managed module that loads a separate
environment**, which RDHPCS warns may not combine well with other system modules:

```bash
module load spack-managed-x86-64_v3/v1.0 apptainer
```

Apptainer enables container-build features that the `singularity` module restricts
for security reasons, so use it when you must **build** an image. Upload finished
images to the RDHPCS container registry at `https://registry.rdhpcs.noaa.gov`,
which also works as a spack mirror.

Podman is **not** the RDHPCS container tool; it is documented only for Gaea and
PPAN and requires a help-desk access request. Do not write Podman instructions for
Orion.

---

## Interactive Development

- `salloc` is MSU's recommended way to get an interactive allocation, with
  `--x11=first` for GUI work and `ssh -X` for X forwarding.
- Open OnDemand (Orion web portal) provides browser file management, job
  submission and monitoring, GUI applications, and a remote desktop session, all
  with MSU credentials plus Duo.
- Jupyter: kernels can be placed in `$HOME/.local/share/jupyter/kernels` so the
  portal finds them.
- Development nodes (`orion-devel-1`, `orion-devel-2`) exist for software
  development and compiles that need extra system libraries requested, and are the
  only gateway for writing into `/apps/contrib`. They are internal-access-only over
  SSH.
- `screen` has been replaced by `tmux` on the MSU systems.

---

## What the Documentation Does Not Cover

Do not invent content for these; ask the help system at
`rdhpcs.orion.help@noaa.gov`:

- **Debuggers and profilers.** RDHPCS's debuggers and profilers page names Gaea
  only — there is no Orion or Hercules entry, and no GNU Debugger, Valgrind4hpc, or
  HPE PAT guidance for the MSU systems. Search the module tree before promising a
  tool.
- **Job arrays.** MSU does not document `--array` for Orion.
- **Build systems and language runtimes.** No CMake, GCC, or MPI-standard module
  list is published; discover them with `module spider`.
- **Node-local temp.** RDHPCS documents `$TMPDIR` only for PPAN, where it points
  into `/vftmp`. Neither the MSU guide nor the fleet storage page describes a
  node-local temp path for Orion, so use a directory under your project scratch
  (an `stmp`-style folder you clean up yourself) rather than assuming `$TMPDIR`
  exists.
