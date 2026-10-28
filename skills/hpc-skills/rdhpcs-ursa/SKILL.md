---
name: rdhpcs-ursa
description: >
  NOAA RDHPCS Ursa system at NESCC in Fairmont West Virginia, covering both CPU
  and GPU queues. Use when writing Slurm jobs for Ursa, choosing between the
  u1-compute CPU partition and the u1-h100, u1-gh, and u1-mi300x GPU partitions,
  pairing a GPU partition with the gpu or gpuwf QOS, requesting NVIDIA H100,
  GH200 Grace Hopper, or AMD MI300X accelerators with --gpus=h100:N,
  --gpus=gh200:N, or --gpus=mi300x:N, deciding whether a gpu- project
  allocation is required, using --exclusive on shared nodes, or loading Intel
  oneAPI, nvhpc, AOCC, HPC-X, or ROCm on Ursa.
compatibility: Script-authoring skill; no login required. Submitting jobs requires CAC/PIV or YubiKey access through ursa-mfa.princeton.rdhpcs.noaa.gov or ursa-mfa.fairmont.rdhpcs.noaa.gov and a signed master certificate.
metadata:
  version: "1.0"
  system: ursa
  facility: rdhpcs
  scheduler: slurm
  source: https://docs.rdhpcs.noaa.gov/systems/ursa_user_guide.html
  as_of: "2026-10-28"
allowed-tools: Read Write Grep Glob
---

# Ursa — NOAA RDHPCS

Ursa is the AMD Genoa CPU and GPU system at the NOAA Environmental Security Computing
Center (NESCC) in Fairmont, West Virginia, supporting NOAA's weather prediction workloads.
It is connected to the **same high-performance file systems as Hera**, so storage guidance
carries over between the two. Slurm, Rocky 9.4, spack-installed modules.

## System Overview

| Component | Specification |
|-----------|--------------|
| CPU compute | 576 nodes, 2x AMD EPYC 9654 "Genoa", 96 cores each, 192 threads per node, 384 GB |
| CPU peak | 4.25 PFLOPS |
| GPU system | 58 nodes, 2x NVIDIA H100-94 GB each, 11,136 cores |
| Exploratory GPU | 8x GH200 nodes (ARM Grace, 72 cores, ~213 GB) and 5x MI300X nodes (96 Intel cores, 8x MI300X 192 GB each) |
| Interconnect | Mellanox NDR-200 InfiniBand |
| Scratch | over 100 PB shared with Hera at NESCC, above 1000 GB/s aggregate |

Memory is 2 GB per core, which is where the 384 GB per node figure comes from. Confirm what
is actually available to you:

```bash
sinfo -O partition        # u1-compute u1-gh u1-h100 u1-mi300x u1-service
sinfo -N -l               # node cores and memory
```

## Critical Requirements

```bash
#SBATCH -A <account>          # project account — mandatory on every RDHPCS job
#SBATCH -p u1-compute         # partition
#SBATCH -q gpu                # GPU jobs: a GPU QOS is required IN ADDITION to the partition
#SBATCH -t 2:00:00            # always set a wall clock, and do not over-ask
#SBATCH --exclusive           # when the job needs a whole node
#SBATCH -o /scratch3/<user>/job_%j.out   # output to scratch, never to /home
```

A GPU job must name **both** a GPU partition and a GPU QOS. `#SBATCH -p u1-h100` alone is
not sufficient — the partition allows only `gpu` and `gpuwf`, so an unnamed or `batch` QOS
will not schedule.

Node sharing is enabled for **all job sizes** as of 2026-06-18 unless you pass
`--exclusive`, so add `--exclusive` whenever the job needs the whole node to itself.

## CPU Partitions and QOS

| Partition | QOS allowed | Notes |
|-----------|-------------|-------|
| `u1-compute` | `batch`, `windfall`, `debug`, `urgent`, `long` | General compute. **Default** when no partition is given. `batch` is a QOS name, not a partition |
| `u1-service` | `batch`, `windfall` | Front-end work needing external network or HPSS; max 64 cores and/or 250 GB per user, 24 hour limit. Also the right place to compile |

| QOS | Max walltime | Max cores | Billing TRES | Limits |
|-----|-------------|-----------|--------------|--------|
| `batch` | 8 hours | 8400 (Hera) / 14400 (Ursa) | 1 | Default QOS for projects with more than a windfall-only allocation |
| `urgent` | 8 hours | 8400 (Hera) / 14400 (Ursa) | 2 | One pending and one running job per project. FairShare drops at twice the batch rate; below FairShare 0.45 the job is silently changed to `batch` |
| `debug` | 30 mins | 8400 (Hera) / 14400 (Ursa) | 1.25 | Two jobs per user. Highest priority; not for general fast-turnaround work |
| `long` | 16 hours | 4200 (Hera) / 7296 (Ursa) | 1 | Normal priority for 8 to 16 hour jobs |
| `windfall` | 8 hours | 8400 (Hera) / 14400 (Ursa) | 0 | Lowest priority, charges nothing, does not lower FairShare |

Caps for every QOS: 1500 total jobs per project or account (extra jobs are **rejected at
submit time**), 400 running jobs per project, and only 20 jobs per project gain age
priority. A windfall-only project may use only `windfall` or `gpuwf`.

## GPU Partitions and QOS

| Partition | QOS | Requires | Limits |
|-----------|-----|----------|--------|
| `u1-h100` | `gpu` | project name begins `gpu-`, allocation 2 or larger | 20 GPUs per project, 168 hours, Billing TRES 1 |
| `u1-h100` | `gpuwf` | any Ursa project | 10 GPUs per project, 48 hours, Billing TRES 0, at most 192 gpu-hours running per project |
| `u1-gh` | `gpuwf` | any Ursa project | 8 GH200 nodes, first come first served, ARM Grace 72 cores, 1 gpu-hour bills as 72 core-hours |
| `u1-mi300x` | `gpuwf` | any Ursa project | 5 MI300X nodes, first come first served, 96 Intel cores and 8x MI300X 192 GB per node, 1 gpu-hour bills as 12 core-hours |

| QOS | Max walltime | Max cores | Billing TRES | Limits |
|-----|-------------|-----------|--------------|--------|
| `gpu` | 168 hours | 20 GPUs (Ursa `u1-h100`) | 1 | Requires a project whose name begins `gpu-` with allocation 2 or larger |
| `gpuwf` | 48 hours | 10 GPUs (`u1-h100`) / 8 GPUs (`u1-gh`, `u1-mi300x`) | 0 | Windfall GPU access, open to every Ursa project; at most 192 gpu-hours running per project |

## GPU Access Rules

- **Priority H100 access** needs a GPU-specific project allocation: the project name begins
  `gpu-`, the allocation is 2 or larger, and the job uses `gpu` QOS. Ask your PI or Portfolio
  Manager for one.
- **Every Ursa project** can use H100s at windfall priority with `gpuwf`.
- A project with a CPU allocation gets H100 windfall access, and conversely a project with a
  GPU allocation gets windfall access to the non-GPU resources.
- `u1-gh` and `u1-mi300x` are exploratory: `gpuwf` only, no allocation and no FairShare
  priority, equal first-come-first-served access for every project with Ursa access.
- GPU-hour billing conversions: 1 H100 gpu-hour = 192/2 = 96 core-hours; 1 GH200 gpu-hour =
  72 core-hours; 1 MI300X gpu-hour = 96/8 = 12 core-hours.
- `gpuwf` counts `gpu_allocated * wallclock_requested` and stops scheduling your queued jobs
  once running jobs exceed 192 gpu-hours.

## Minimal CPU Job Script

```bash
#!/bin/bash
#SBATCH -A myproject
#SBATCH -J myjob
#SBATCH -p u1-compute
#SBATCH -q batch
#SBATCH -N 1
#SBATCH --ntasks-per-node=192
#SBATCH -t 2:00:00
#SBATCH -o /scratch3/user/myjob_%j.out

module load intel impi
srun ./my_mpi_app
```

## Minimal GPU Job Script

```bash
#!/bin/bash
#SBATCH -A mygpu_project
#SBATCH -J mltrain
#SBATCH -p u1-h100
#SBATCH -q gpu
#SBATCH -N 1
#SBATCH --ntasks-per-node=4
#SBATCH --gpus=h100:3
#SBATCH -c 48
#SBATCH -t 8:00:00
#SBATCH --exclusive
#SBATCH -o /scratch3/user/ml_%j.out

module load nvhpc/<version>
srun --cpu-bind=cores ./my_gpu_app
```

Without a GPU allocation, ask for the same hardware at windfall priority:

```bash
#SBATCH -p u1-h100
#SBATCH -q gpuwf
#SBATCH --gpus=h100:2
```

The exploratory partitions are documented as interactive allocations, after which you
compile and run on the node:

```bash
salloc -A mygpu_project -t 480 -p u1-gh -q gpuwf --gpus=gh200:1
salloc -A mygpu_project -t 480 -p u1-mi300x -q gpuwf --gpus=mi300x:2
```

## Storage

| Filesystem | Path | Quota | Backup | Use for |
|-----------|------|-------|--------|---------|
| Home | `/home/First.Last` | 30 GB | Yes, plus `~/.snapshot` | Code and configs — never job I/O |
| Scratch | `/scratch3`, `/scratch4` | project-based (Lustre) | **No** | Job input and output |
| VAST scratch | `/scratch5` | project quota for `rstprod` and `public`; `/scratch5/purged/<First.Last>` for everyone else | **No** | All-flash experimental area, 250 TB pool, 90-day purge |
| Node-local | `$TMPDIR` | per node | job lifetime | Fast temporary files |
| Archive | NESCC-HPSS via `hsi` / `htar` | portfolio-managed | Yes | Long-term retention |

`/scratch5/purged/<First.Last>` must be named exactly like your NOAA `First.Last`. `stmp` on
`/scratch3-4` is purged every Monday for files older than 30 days. Scratch is never backed
up. Do not run jobs against files in `/home`.

## Modules

Modules are installed with **spack**, and the layout is like the MSU systems. `module spider`
is the entry point for finding anything:

```bash
module spider <pkg>          # search everything, including hidden-by-default packages
module spider intel impi     # the recommended stack, with its available versions
module load intel/<version> impi/<version>
module list; module purge
```

## Compilers and MPI

| Compiler | Load | Targets |
|----------|------|---------|
| Intel oneAPI | `module load intel/<version>` | CPU; the fleet-recommended pairing |
| NVIDIA nvhpc | `module load nvhpc/<version>` | CUDA on `u1-h100` and `u1-gh` (`nvfortran`, `nvc`, `nvcc`, `nvc++`) |
| AMD AOCC | Ursa guide lists it; confirm the name with `module spider` | CPU on Genoa; ROCm targets `u1-mi300x` |

| MPI | Load | Notes |
|-----|------|-------|
| Intel MPI | `module load impi/<version>` | RDHPCS **recommends the Intel compiler plus Intel MPI combination** unless there is a specific reason not to |
| HPC-X | confirm with `module spider` | On Ursa specifically, RDHPCS measured **better performance and stability** than Intel MPI on communication-intensive benchmarks over NDR-200 — prefer it for GPU MPI work |
| OpenMPI | confirm with `module spider` | Available through spack |

Two documented views to keep straight: the fleet compilers page recommends Intel plus Intel
MPI and lists only Intel and NVIDIA compilers as generally available, while the Ursa guide
adds AOCC and steers GPU users toward HPC-X. CUDA targets the H100 and GH200 nodes; ROCm
targets MI300X. Ursa modules come from a **spack** tree, so verify names with
`module spider intel impi` rather than trusting the short forms here.

MPI wrappers take an extra `i` for Intel: `mpiifort`, `mpiicc`, `mpiicpc`, and the newer
`mpiifx -fc=ifx` and `mpiicx`.

## Common Gotchas

- `-p u1-h100` with no GPU QOS — the job never schedules; add `-q gpu` or `-q gpuwf`.
- `gpu` QOS from a project whose name does not begin `gpu-` with allocation 2 or larger; use
  `gpuwf` instead.
- Omitting `--exclusive` when the job needs a whole node — sharing is on for all job sizes.
- Assuming production x86 binaries run on the ARM `u1-gh` nodes; rebuild there.
- Trying to build or pull a container image on a `u1-gh` node — the Grace Hopper compute nodes
  are air-gapped. Build or pull on a login node with `--arch arm64`.
- Exceeding the 192 gpu-hour `gpuwf` cap, after which queued jobs stop being scheduled.
- Compiling on a login node instead of `u1-service`.
- Pulling or building a container on a login node — allocate a `u1-service` node with enough
  memory instead, as the container guide shows for Ursa.
- Writing job output to `/home` — 30 GB quota, and heavy I/O harms it for everyone.
- Treating `/scratch5/purged` as durable — files untouched for 90 days are deleted.
- A windfall-only project submitting to `batch` instead of `windfall`.
- Reading the per-partition "Billing TRES Factor 100" column on the Ursa guide as a job
  limit. Every Ursa partition shows 100, which cannot be a per-job factor; the per-QOS
  Billing TRES values in the table above are the ones the queue policy publishes.

## Additional Resources

- Annotated CPU and GPU job scripts: [references/job-scripts.md](references/job-scripts.md)
- File systems, `/scratch5` VAST rules, quotas, HPSS: [references/storage.md](references/storage.md)
- Compilers, MPI choices, CUDA versus ROCm, Apptainer containers: [references/programming-env.md](references/programming-env.md)
- Ursa user guide: https://docs.rdhpcs.noaa.gov/systems/ursa_user_guide.html
