---
name: rdhpcs-hera
description: >
  NOAA RDHPCS Hera supercomputer at the NESCC facility in Fairmont West
  Virginia. Use when writing Slurm job scripts for Hera, choosing a Hera
  partition (hera, bigmem, novel, service) or QOS (batch, urgent, debug, long,
  windfall), requesting Intel Skylake 40-core nodes, pairing Intel compilers
  with IntelMPI or PGI with MVAPICH2, setting I_MPI_EXTRA_FILESYSTEM for MPI-IO
  on Lustre, placing data on /home, /scratch3-4, or /scratch5, archiving to
  HPSS, or checking Hera quotas and allocations.
compatibility: Script-authoring skill; no login required. Submitting jobs requires CAC/PIV or YubiKey access through hera-mfa.princeton.rdhpcs.noaa.gov or hera-mfa.fairmont.rdhpcs.noaa.gov and a signed master certificate.
metadata:
  version: "1.0"
  system: hera
  facility: rdhpcs
  scheduler: slurm
  source: https://docs.rdhpcs.noaa.gov/systems/hera_user_guide.html
  as_of: "2026-10-28"
allowed-tools: Read Write Grep Glob
---

# Hera — NOAA RDHPCS

Hera is an Intel Skylake system at the NOAA Environmental Security Computing
Center (NESCC) in Fairmont, West Virginia, used for high-impact weather
prediction work. It runs **Slurm** with LMOD hierarchical modules and shares its
file systems with Ursa.

## System Overview

| Component | Specification |
|-----------|--------------|
| CPU | Intel Xeon Gold 6148 "Skylake", 2.40 GHz, 40 cores per node |
| Regular compute nodes | 1,328 |
| Total cores | 63,840 |
| Large-memory nodes | 268 `bigmem` nodes, 40 cores and 384 GB each |
| Interconnect | Mellanox HDR-100 InfiniBand |
| Peak capacity | 3.27 PFLOPS |
| Scratch | HPFS Lustre on `/scratch3-4`, shared with Ursa |

The RDHPCS documentation does not publish per-node memory for regular Hera
nodes. Read the real value instead of assuming one:

```bash
sinfo -N -l
```

## Critical Requirements

```bash
#SBATCH -A <account>          # project account — mandatory on every RDHPCS job
#SBATCH -p hera,bigmem        # list every partition you can use; -p is partition
#SBATCH -t 4:00:00            # always set a wall clock, and do not over-ask
#SBATCH -o /scratch3/<user>/job_%j.out   # output to scratch, never to /home
```

Requesting several partitions lets the scheduler start the job on whichever
resource frees up first, which RDHPCS recommends for general compute work.

## Partitions

| Partition | QOS allowed | Use |
|-----------|-------------|-----|
| `hera*` | batch, windfall, debug, urgent, long | General compute. **Default** when no partition is given |
| `bigmem` | batch, windfall, debug, urgent, long | Large-memory jobs; 268 nodes at 40 cores and 384 GB |
| `novel` | novel | Nearly the whole system. Needs a help ticket in advance **and** `--qos=novel` |
| `service` | batch, windfall | External network and HPSS access. Runs on front ends; default 1 core, maximum 4 cores, 24 hour limit |

`hera` is the default partition — the documented way to confirm is:

```bash
sinfo -O partition     # hera* service bigmem novel  (asterisk marks the default)
```

## QOS

| QOS | Max walltime | Max cores | Billing TRES | Limits |
|-----|-------------|-----------|--------------|--------|
| `batch` | 8 hours | 8400 (Hera) / 14400 (Ursa) | 1 | Default QOS for projects with more than a windfall-only allocation |
| `urgent` | 8 hours | 8400 (Hera) / 14400 (Ursa) | 2 | One job per project pending or running. FairShare drops at twice the batch rate; below FairShare 0.45 the job is changed to `batch` and the user is notified on stderr |
| `debug` | 30 mins | 8400 (Hera) / 14400 (Ursa) | 1.25 | Two jobs per user. Highest priority; not for general fast-turnaround work |
| `long` | 16 hours | 4200 (Hera) / 7296 (Ursa) | 1 | Normal priority for 8 to 16 hour jobs |
| `windfall` | 8 hours | 8400 (Hera) / 14400 (Ursa) | 0 | Lowest priority, charges nothing, does not lower FairShare |

Caps for every QOS: 1500 total jobs per project or account (extra jobs are
**rejected at submit time**), 400 running jobs per project, and only 20 jobs per
project gain age priority. A windfall-only project may use only `windfall`.

Escalate a pending windfall job when it needs to run:

```bash
scontrol update job 26866,26867 qos=batch
echo "scontrol update job 26990 qos=batch" | at -M now +5min
```

## Minimal Job Script

```bash
#!/bin/bash
#SBATCH -A myproject
#SBATCH -J myjob
#SBATCH -p hera,bigmem
#SBATCH -q batch
#SBATCH -N 1
#SBATCH --ntasks-per-node=40
#SBATCH -t 2:00:00
#SBATCH -o /scratch3/user/myjob_%j.out
#SBATCH -e /scratch3/user/myjob_%j.err

module load intel impi
cd /scratch3/user/run.456
srun ./my_mpi_app
```

For a serial job, request one core, or use `--mem=<MB>` when sharing a node. Use
the `service` partition when the job needs external network or HPSS.

## Storage

| Filesystem | Path | Quota | Backup | Use for |
|-----------|------|-------|--------|---------|
| Home | `/home/First.Last` | 30 GB | Yes, plus `~/.snapshot` | Code and configs — never job I/O |
| Scratch | `/scratch3`, `/scratch4` | project-based | **No** | Job input and output |
| VAST scratch | `/scratch5` | project quota for `rstprod` and `public`; `/scratch5/purged/<First.Last>` for everyone else | **No** | All-flash experimental area, 90-day purge |
| Archive | NESCC-HPSS via `hsi` / `htar` | portfolio-managed | Yes | Long-term retention |

`stmp` on `/scratch3-4` is purged every Monday for files older than 30 days.
Scratch is never backed up. Do not run jobs against files in `/home`.

## Modules

LMOD on Hera is **hierarchical**, so `module avail` shows only what the loaded
compiler family exposes. Search everything with `module spider`.

```bash
module spider <pkg>          # authoritative availability search
module load intel impi       # Intel compilers + IntelMPI
module load pgi mvapich2     # PGI compilers + MVAPICH2
module list; module purge
```

## Interactive Jobs

```bash
salloc -A myproject -p hera -q debug -N 1 -t 30:00 --ntasks-per-node=40
```

Packaged applications such as IDL, ImageMagick, MATLAB, and R run on compute
nodes, not front ends. IDL defaults to one thread per virtual CPU — 48 on a Hera node — so
set `IDL_CPU_TPOOL_NTHREADS=1` for a serial run. IDL needs over 10 GB of memory for many
workloads, which means `bigmem` or a whole node.

## Common Gotchas

- No `-A` — RDHPCS rejects the job; the account is mandatory everywhere.
- `novel` partition without `--qos=novel`, or without a prior help ticket.
- Compiling on a login node instead of the `service` partition.
- Writing job output to `/home` — 30 GB quota on Hera, and heavy I/O harms it for everyone.
- MPI-IO on Lustre without `I_MPI_EXTRA_FILESYSTEM=on` and `I_MPI_EXTRA_FILESYSTEM_LIST=lustre`; Intel MPI does not detect the file system by default.
- Running a threaded application with default thread counts on a shared node.
- Treating `/scratch5/purged` as durable — files untouched for 90 days are deleted.
- A windfall-only project submitting to `batch` instead of `windfall`.

## Additional Resources

- Annotated job scripts, hybrid MPI+OpenMP, arrays: [references/job-scripts.md](references/job-scripts.md)
- File systems, quotas, HPSS archiving, purge rules: [references/storage.md](references/storage.md)
- Compilers, MPI choices, profilers, debuggers: [references/programming-env.md](references/programming-env.md)
- Hera user guide: https://docs.rdhpcs.noaa.gov/systems/hera_user_guide.html
