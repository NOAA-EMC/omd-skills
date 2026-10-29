# Hercules Programming Environment Reference

MSU-HPC publishes a module tree rather than a fixed compiler/MPI recommendation, and
Hercules' tree is built with Spack and shaped differently from Orion's. This file
teaches **discovery**: find what Hercules actually offers today instead of assuming a
pairing that exists on another RDHPCS system — or on Orion.

---

## The Orion/Hercules Difference Rule

MSU is explicit that these do **not** transfer between the two systems:

- The `/apps` directory structure, which is "significantly different" between them.
- **The names and the load order of module files.** A load sequence that works on
  Orion can fail on Hercules.
- Software versions: Hercules carries the latest versions of the same basic packages,
  with older versions available only by a justified help ticket.

What *is* shared: `/work` and `/work2`, your project directory path, your account, and
your Duo credentials. So treat every software path and module name as something to
re-discover on each system.

---

## LMOD Hierarchical Modules

Lmod is a Lua-based module system used on Gaea, Ursa, Hera, and the MSU systems
Hercules and Orion. Because many packages depend on a specific compiler or MPI
library, Lmod uses a **hierarchical layout**: loading a compiler makes
compiler-dependent packages (MPI stacks, libraries) visible, and loading an MPI stack
makes MPI-dependent packages visible in turn. `module avail` therefore shows only
what is compatible with what you already have loaded — which is intentional.

```bash
module avail                    # what the current environment exposes
module list                     # what is loaded
module -t list                  # compact
module purge                    # start clean
module show <name>              # what a module actually sets
```

`module spider` searches the **entire** hierarchy, including modules hidden behind
unloaded dependencies. RDHPCS documents it fleet-wide and it is the right way to find
out whether Hercules has a package at all:

```bash
module spider <pkg>
```

Do not carry a Gaea module name to Hercules. Gaea is an HPE/Cray system whose
toolchain comes from `PrgEnv-*` modules; Hercules has no Cray Programming Environment.

---

## Spack and the Rule Against Hard-Coded Paths

Hercules' open-source stack is built and managed with **Spack**, including each
package's module file. Spack installs into `/apps/spack/<package-hash>`, and MSU
states plainly:

> Any time `/apps/spack` software packages are rebuilt they will get a new hash. This
> may occur often. So it is imperative to not use hard coded paths and instead, use
> modules for loading the required build and run environment.

Concretely, on Hercules:

- Never write `/apps/spack/...` into a script, module file, job submission, or
  compiled-in prefix. It will break without warning.
- Always go through `module load`, and let the module set the prefix variables.
- Do not cache a path in your own config files from a previous run; re-derive it in
  the job.
- Do not copy an Orion `/apps` path across. The layouts are different systems, not
  different mounts of the same tree.

---

## NOAA Tooling on Hercules

The NOAA helper commands live behind two modules. MSU documents this exact sequence:

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

Treat the version numbers as placeholders: enumerate what Hercules offers with
`module avail` after loading the compiler, and pin the versions you build with so a
module default change does not silently break your job. Typical pattern:

```bash
module purge
module load intel                # or the compiler family your build needs
module avail                     # now the MPI stacks for that compiler appear
module load impi
module list                      # record what the build actually used
```

MPI-dependent packages (netCDF, PnetCDF, and similar) become visible only after an MPI
stack is loaded, so build in that order: compiler → MPI → libraries.

---

## Environment Variables Set by Modules

MSU warns that module-provided variables "may not be what you used on other machines.
Users should check and make sure." Their documented WRF example is written **for
Hercules specifically**:

`netcdf-c` and `netcdf-fortran` are installed in **different directories** on
Hercules. After loading the modules you get `NETCDF_C_ROOT` and
`NETCDF_FORTRAN_ROOT`, but a WRF build expects a single `NETCDF` root, so assemble one:

```bash
mkdir -p $NETCDF
cp -r $NETCDF_C_ROOT/* $NETCDF/.
cp -r $NETCDF_FORTRAN_ROOT/* $NETCDF/.
```

Parallel netCDF exposes `PARALLEL_NETCDF_ROOT`, and you must define `PNETCDF` or the
model **compiles successfully and then fails at runtime** on parallel I/O (for
example `io_form_input=11` in `namelist.input`):

```bash
export PNETCDF=$PARALLEL_NETCDF_ROOT
```

Check the variables your build system reads against what `module show` sets before the
first compile, not after a mysterious runtime failure.

---

## MPI Runtime Problems MSU Documents

**Node-memory crashes.** MSU's remedy, for both systems: use more nodes, or fewer MPI
tasks per node, and make sure the node is not shared with other jobs by adding
`#SBATCH --exclusive`.

**Intel MPI shared-memory heap (Hercules only).** MSU documents this failure pattern
as a Hercules FAQ: large runs crash while small ones work, and multi-task runs crash
where a single task succeeds. Intel MPI's default `I_MPI_SHM_HEAP_VSIZE` is 8192 MB,
and when it exceeds the memory the node can give the job, MPI initialization fails
with "unable to allocate shared memory". Redefine it before `srun`, sized against your
job's share of the node. Hercules nodes carry 512 GB, so the default is rarely the
right value here.

**`--ntasks-per-node` on large domains (Hercules only).** MSU's Hercules FAQ records
crashes in large-domain model runs caused by `--ntasks-per-node`, and advises against
the option because Hercules nodes have far more memory per core than Orion's. Prefer
an explicit task count.

**Stack-size segfaults.** MSU documents this for both Orion and Hercules: the default
soft stack limit is **16KB**, and a program whose subroutine and function locals
exceed it segfaults. Raise it and verify inside the job script:

```bash
ulimit -s <stack_size>   # MSU's form; pick a size, don't just use "unlimited"
ulimit -s                # confirm it took
```

MSU explicitly says to set this **in the batch script and not in `~/.bashrc`**,
because putting it in the shell startup file "can cause unintended consequences".

---

## Thread Affinity

RDHPCS publishes no Hercules-specific OpenMP affinity recipe. Use the portable Slurm
and OpenMP variables and verify the placement you actually got:

```bash
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
export OMP_PLACES=cores
export OMP_PROC_BIND=close
```

A Hercules node is 80 cores (2 x 40) at 2.3 GHz with 512 GB of memory, so Orion's
per-node task packings (and its 192 GB memory assumptions) do not transfer. For pure
MPI use `--cpus-per-task=1`; for OpenMP raise it to the thread count you want. Do not
assume a threaded application should use all 80 cores on a shared node — request the
whole node with `--exclusive` if you do.

---

## Python

RDHPCS documents the Hercules load sequence explicitly, and it is the same shape as
Orion's — both sit behind `contrib`, unlike the NOAA-operated systems:

```bash
module load contrib
module load rdhpcs-python      # or rdhpcs-conda
```

`module avail python` lists the available versions; loading one puts you in a conda
environment associated with that version. For `rdhpcs-conda` you do not need to
activate the environment.

The system-provided environment contains base Python only. Install what you need into
your own environment:

```bash
module load contrib
module load rdhpcs-conda
conda create -n myenv python=3.12
conda activate myenv
conda install -c conda-forge <pkg>
```

**conda-forge is the only channel RDHPCS approves fleet-wide**, and Miniforge is their
conda-forge installer if you want your own stack in `/work` rather than the system
module.

---

## Containers

Singularity containers are available to all users and projects on Ursa, Gaea, Hera,
MSU-HPC (Orion and Hercules), and PPAN. Hercules requires an explicit module load —
unlike Hera and Ursa, where none is needed:

```bash
module load singularity
singularity run /work/noaa/<project>/<user>/images/myimage.sif
```

Hercules also offers Apptainer as a **Spack-managed module that loads a separate
environment**, which RDHPCS warns may not combine well with other system modules:

```bash
module load spack-managed-x86-64_v3/v1.0 apptainer
```

Apptainer enables container-build features that the `singularity` module restricts for
security reasons, so use it when you must **build** an image. Upload finished images
to the RDHPCS container registry at `https://registry.rdhpcs.noaa.gov`, which also
works as a spack mirror.

Podman is **not** the RDHPCS container tool on Hercules; it is documented only for
Gaea and PPAN and requires a help-desk access request. Do not write Podman
instructions for Hercules.

---

## Interactive Development

- `salloc` is MSU's recommended way to get an interactive allocation, with
  `--x11=first` for GUI work and `ssh -X` for X forwarding.
- Open OnDemand (Hercules web portal) provides browser file management, job submission
  and monitoring, GUI applications, and a remote desktop session, all with MSU
  credentials plus Duo.
- Jupyter: the recommended route is the Interactive Apps menu on Open OnDemand, since
  MSU systems do not allow SSH port forwarding. Kernels can be placed in
  `$HOME/.local/share/jupyter/kernels` so the portal finds them — remember Hercules
  has its **own** home filesystem, so set this up on each system separately.
- Development nodes (`hercules-devel-1.hpc.msstate.edu`,
  `hercules-devel-2.hpc.msstate.edu`) exist for software development and compiles
  that need extra system libraries requested, and are the only gateway for writing
  into `/apps/contrib`. They are internal-access-only over SSH. (The configuration
  table lists 4 devel nodes for Hercules but names only these two hosts — ask the
  help system before assuming `hercules-devel-3`/`-4` exist.)
- `screen` has been replaced by `tmux` on the MSU systems.

---

## Role Accounts

NOAA projects on Hercules use role accounts for shared, long-running, or
pipeline-owned jobs. Switch to one from a login, development, or data-transfer node:

```bash
sudo -su role-<projectname>
```

The MSU username is **not** the RDHPCS `First.Last` name, and the Portfolio Manager
must hold an active MSU account to manage project membership. New role accounts and
membership changes go through `rdhpcs.hercules.help@noaa.gov`.

---

## What the Documentation Does Not Cover

Do not invent content for these; ask the help system at
`rdhpcs.orion.help@noaa.gov` (general) or `rdhpcs.hercules.help@noaa.gov` (role
accounts):

- **Debuggers and profilers.** RDHPCS's debuggers and profilers page names Gaea only —
  there is no Orion or Hercules entry, and no GNU Debugger, Valgrind4hpc, or HPE PAT
  guidance for the MSU systems. Search the module tree before promising a tool.
- **Job arrays.** MSU does not document `--array` for Hercules.
- **Build systems and language runtimes.** No CMake, GCC, or MPI-standard module list
  is published; discover them with `module spider`.
- **A published compiler/MPI pairing.** MSU shows `intel` + `impi` in its benchmark
  example but does not declare a recommended stack; enumerate versions yourself and
  pin them.
- **Node-local temp.** RDHPCS documents `$TMPDIR` only for PPAN, where it points into
  `/vftmp`. Neither the MSU guide nor the fleet storage page describes a node-local
  temp path for Hercules, so use a directory under your project scratch (an `stmp`-style
  folder you clean up yourself) rather than assuming `$TMPDIR` exists.
