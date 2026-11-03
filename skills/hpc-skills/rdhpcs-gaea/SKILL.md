---
name: rdhpcs-gaea
description: >-
  NOAA RDHPCS Gaea system at Oak Ridge National Laboratory's NCCS, a federated
  Slurm cluster with HPE Cray EX 3000 compute and the Cray Programming
  Environment. Use when writing Slurm jobs for Gaea, selecting the c5, c6, c7,
  or es cluster with -M or --clusters, choosing the batch or novel partition or
  the normal, debug, urgent, windfall, dtn, ppan, hpss, or interactive QOS,
  targeting C5, C6, or C7 AMD EPYC node generations, using the dtn_f5_f6
  partition with --constraint=f5 or --constraint=f6, placing data on the
  cluster-specific /gpfs/f5, /gpfs/f6, or /gpfs/f7 filesystems or the
  /ncrc/home[12] and /ncrc/proj NFS areas, or compiling with the cc, CC, and
  ftn Cray wrappers and PrgEnv modules.
compatibility: Script-authoring skill; no login required. Submitting jobs requires CAC/PIV or YubiKey access through a Gaea bastion and a signed master certificate.
metadata:
  version: "1.0"
  system: gaea
  facility: rdhpcs
  scheduler: slurm
  source: https://docs.rdhpcs.noaa.gov/systems/gaea_user_guide.html
  as_of: "2026-10-28"
allowed-tools: Read Write Grep Glob
---

# Gaea — NOAA RDHPCS at ORNL NCCS

Gaea is the largest RDHPCS machine: a DOE/NOAA collaborative system operated
by the **National Center for Computational Sciences (NCCS)** at the Oak Ridge
National Laboratory (ORNL). It is **not a single cluster** — it is a Slurm
**federation** of three HPE Cray EX 3000 compute clusters (`c5`, `c6`, `c7`)
plus an `es` cluster holding every login node and data transfer node.
Aggregate peak is **more than 54 petaflops** across the three generations,
served by three IBM Spectrum Scale (GPFS) file systems totalling **over
220 PB** (F5 75 PB, F6 75 PB, F7 70 PB) on HPE Slingshot.

Connect with `ssh <First.Last>@gaea-rsa.rdhpcs.noaa.gov`; the bastion places
you on a random C5 login node — interrupt within 5 seconds and run `hostname`,
or type `gaea6` to jump to a C6 login node. Login sessions are capped at 7
days and are dropped Mondays at 4 AM ET at the Princeton bastion; batch jobs
are unaffected. Read the `slurm` skill's *RDHPCS Shared Policy* first for the
fleet-wide job-authoring rules.

## System Overview

| Cluster | Nodes | CPU | Cores per node | Memory per node | NUMA | ISA | Peak | Interconnect |
|---------|-------|-----|----------------|-----------------|------|-----|------|--------------|
| C5 | 1,920 | 2× AMD EPYC 7H12 2.6 GHz, 64-core | 128 | 256 GB | 8 | AVX-2 | 10.22 PF | 2× Slingshot 100 Gbps |
| C6 | 2,048 | 2× AMD EPYC 9654 2.4 GHz, 96-core | 192 | 384 GB | 8 | AVX-512 | 15.1 PF | 1× Slingshot 200 Gbps |
| C7 | 1,208 | 2× AMD EPYC 9965 2.0 GHz, 192-core (Zen 5c Turin) | 384 | 768 GB | 4 | AVX-512 | 29 PF | 1× Slingshot 200 Gbps |

**Login nodes are a separate set with different specs — never quote them as
compute nodes:** `gaea5[1-6]` are 2× EPYC 7662 64-core (128 cores, 512 GB),
`gaea6[1-6]` are 2× EPYC 9654 (192 cores, 512 GB), and `gaea7[1-6]` are 2×
EPYC 9845 96-core reported at **320 cores per node with 1.6 TB**. Data
transfer nodes: `dtn[50-79]` (EPYC 7302, mount `/gpfs/f5` + `$HOME`) and
`dtn[01-09]` (EPYC 7713, mount `/gpfs/f6` + `$HOME`).

Operating system: Cray OS 3.1.0-28 (based on SLES 15.5) on C5 and C6; RHEL
9.8 "Plow" on C7. Confirm what you are standing on with
`cat /opt/cray/etc/release/cos-base` and `lsb_release -a`; the guide updates
COS yearly in the fall.

## Critical Requirements

1. **`-A <projectID>` is mandatory.** Every job names a project allocation.
2. **`-M <cluster>` selects the Slurm cluster.** Scheduler commands default to
   the cluster whose login node you are on, so a job submitted without `-M`
   runs where you happen to be standing.
3. **The GPFS file system must match the cluster:** `/gpfs/f5` for C5,
   `/gpfs/f6` for C6, `/gpfs/f7` for C7. A C5 job cannot read `/gpfs/f6`.
4. **Node shapes differ per generation** — 128, 192, and 384 cores. Copying a
   `--ntasks-per-node` value across generations silently over- or
   under-subscribes the node.

## Slurm Federation

```bash
squeue --clusters=c6            # or -M c6
export SLURM_CLUSTERS=c5,es     # change the default for a session
#SBATCH -M c5                   # script form
scontrol --cluster c6 show partition   # authoritative partition list per cluster
```

Clusters `c5`, `c6`, `c7` are compute; `es` holds all login and data transfer
nodes.

**Partitions** (these are partitions, *not* QOS):

| Partition | Cluster(s) | Nodes | Default | Max | Purpose |
|-----------|-----------|-------|---------|-----|---------|
| `batch` | C5, C6 | 1–512 | 12:00:00 | 16:00:00 | regular allocated work |
| `novel` | C5, C6 | 513+ | 12:00:00 | 16:00:00 | unusual jobs, typically more than 25% of system cores; enabled only right after system maintenance — alert the help desk if it is inactive |
| `eslogin_c5` / `eslogin_c6` | es | 1 | 12:00:00 | 16:00:00 | login-node work |
| `dtn_f5_f6` | es | 1 | 12:00:00 | 16:00:00 | data movement; `--constraint=f5`/`f6` picks the mounted file system |
| `cron_c5` / `cron_c6` | es | 1 | 12:00:00 | 16:00:00 | required partitions for jobs launched under scron |

**No C7 partitions are published in the guide.** Do not invent names — run
`scontrol --cluster c7 show partition` and use what it reports.

## QOS

Gaea's own documented QOS, in its own table shape (do not confuse these with
the `batch`/`novel` partitions above):

| QOS | Priority Factor | Usage Factor | Max Walltime | Clusters | Description |
|-----|-----------------|--------------|--------------|----------|-------------|
| `normal` | 0.85 | 1.00 | 16 hours | C5, C6, ES | the default QOS for compute cluster jobs |
| `debug` | 1.00 | 1.00 | 1 hour | C5, C6 | highest priority; useful for short, non-production work |
| `urgent` | 0.95 | 1.00 | 16 hours | C5, C6 | lets groups prioritize their project's jobs |
| `windfall` | 0.00 | 0.00 | 16 hours | C5, C6, ES | lowest priority (only age and fair-share count); also keeps jobs from affecting the project's overall fair-share |
| `dtn` | 0.00 | 1.00 | 16 hours | ES | default QOS for all jobs executed on Gaea DTNs |
| `ppan` | 0.00 | 1.00 | 16 hours | ES | transfers to/from GFDL/PPAN; paused while PPAN is in maintenance |
| `hpss` | 0.00 | 1.00 | 16 hours | ES | transfers to/from NESCC HPSS; paused while HPSS is in maintenance |

Only QOS on the compute clusters affect a job's priority value. `salloc`
automatically adds the `interactive` QOS (unless `--qos` is used; same priority
factor as `debug`) — and **only one interactive job per user is allowed**.

The fleet policy behind the table: two allocations split 50/50 — high-priority
work (`urgent`, plus `novel`-partition jobs needing more than 25% of system
cores, runnable in the 8-hour window immediately after preventative
maintenance) versus `batch`/debug/interactive work. The largest job is limited
to 25% of available cores except on `novel`, and individual job segments are
limited to 12 hours. Windfall is requested with `sbatch --qos=windfall`.

Discover live values rather than trusting this table after a reconfig:

```bash
sacctmgr show qos format=name,priority,usagefactor,maxwall
sprio
sshare
```

## Minimal Job Script

```bash
#!/bin/bash
#SBATCH -M c6
#SBATCH -A myproject
#SBATCH -J RunSim123
#SBATCH -p batch
#SBATCH -N 16
#SBATCH --ntasks-per-node=192
#SBATCH -t 4:00:00
#SBATCH -o %x-%j.out

module load PrgEnv-gnu
cd /gpfs/f6/${SLURM_ACCOUNT}/scratch/${USER}/Run.456
srun ./my_app
```

There is no `-q` line: `normal` is the default QOS. Add
`#SBATCH --qos=windfall` for uncharged work.

## Storage

| Area | Path | Permissions | Quota | Backed up | Purged | Available from |
|------|------|-------------|-------|-----------|--------|----------------|
| User home (NFS) | `/ncrc/home[12]/<userID>` | user-set | 50 GB | Yes | No | compute nodes + DTNs |
| Project home (NFS) | `/ncrc/proj/<projID>` | project-set | 100 GB | Yes | No | compute nodes + DTNs |
| Member work | `/gpfs/f5/<projID>/scratch/<userID>` | user-set | N/A | No | No | C5 only |
| Project work | `/gpfs/f5/<projID>/proj-shared` | 770 | N/A | No | No | C5 only |
| World work | `/gpfs/f5/<projID>/world-shared` | 775 | N/A | No | No | C5 only |
| NESCC-HPSS archive | `/<PORTFOLIO>/<project>/<retention>/<user>` | portfolio-managed | project allocation | **No — single copy** | Yes, on retention expiry | DTNs (`dtn_f5_f6`) only |

The same three GPFS areas exist on `/gpfs/f6` (C6 only) and `/gpfs/f7` (C7
only). The NFS areas are the guide's recommended place for user and project
applications, executables, and small data files; home is backed up with hourly
and daily snapshots and never purged. **Gaea has no `/nobackup` area** — the
GPFS scratch trees *are* the non-persistent space. Check usage with `quota -Qs`.

F5 has transparent lz4 compression (files idle more than 168 hours); F6 does
not. All extensive I/O, large local copies, and every off-Gaea transfer run on
DTNs via `dtn_f5_f6` with the matching `--constraint` (otherwise routing is
automatic based on whether your process originated on a C5 or C6 node). See
[references/storage.md](references/storage.md).

## Programming Environment

Cray Programming Environment (CPE) with Lmod: load a toolchain with
`module load PrgEnv-aocc` / `PrgEnv-cray` / `PrgEnv-gnu` / `PrgEnv-intel` /
`PrgEnv-nvhpc` (or `module swap`), and build through the `cc`, `CC`, `ftn`
wrappers, which link Cray MPICH automatically; add `-craype-verbose` to see
the include and link lines. Two Gaea-specific cautions: **CPE reaches end of
support at version 26.03**, and **C7 no longer loads CPE by default** — the
default environment is whatever is active at login (the guide suggests a
`load_cpe` shell alias for legacy workflows). Discover with `module avail`
(`module spider` searches the full hierarchy). See
[references/programming-env.md](references/programming-env.md).

## Cron and Recurring Work

Cron is **not permitted** on Gaea; use Slurm `scrontab`, whose jobs run on the
`cron_c5` / `cron_c6` partitions. The fleet rules apply: anything launched
from scrontab must be a workflow-manager call, a job-submitting script, or a
data task under 2 minutes; run no more often than every 10 minutes (3 minutes
inside an approved real-time reservation); never redirect output to
`/dev/null`; and add `--mail-user=<email>` to the scrontab.

## Common Gotchas

- `squeue` shows nothing — you are querying the cluster you are standing on,
  not the one holding your job. Use `--clusters`/`-M` or `SLURM_CLUSTERS`.
- Omitting `-M` silently places the job on your current cluster's resources.
- A C5 job reading `/gpfs/f6` (or any mismatch of cluster and file system).
- Landing on a DTN without `--constraint=f5`/`f6` so the needed file system is
  not mounted.
- Quoting login-node cores/memory as compute specs — `gaea7[1-6]` has 320
  cores and 1.6 TB; C7 compute nodes have 384 cores and 768 GB.
- Submitting to `novel` when the partition is not enabled — it is only active
  immediately after maintenance; contact the help desk.
- **Never append `/bin/bash` to `salloc`** — the allocation then runs on the
  login node.
- `--threads-per-core=2` must appear in the `sbatch`/`salloc` request as well
  as in `srun`, or it is ignored.
- `-S <n>` reserves n cores per node that your application cannot use
  (default 8).
- Two jobs touching the same files (hard/soft links) can lock up the GPFS
  MDS; clean up after jobs.
- Conda/spack/Python environments must not live on GPFS — use
  `/ncrc/home[12]/$USER`, `/ncrc/proj`, or request a `/usw` location from the
  help desk; no development work (especially git) on F5.
- Transfers over 2 TB to the GFDL archive are slow — use Globus.
- Treating GPFS scratch as backup: it is neither backed up nor purged, so
  abandoned files stay and unbacked-up files can be lost.

## Additional Resources

- [references/job-scripts.md](references/job-scripts.md) — directive table,
  per-generation job examples, dependencies, monitoring and control.
- [references/storage.md](references/storage.md) — GPFS areas, compression,
  quotas, DTN transfer rules, known I/O issues.
- [references/programming-env.md](references/programming-env.md) — Lmod,
  PrgEnv families, wrappers, dynamic linking, debuggers and profilers.
- Gaea user guide: <https://docs.rdhpcs.noaa.gov/systems/gaea_user_guide.html>
- RDHPCS queue policy: <https://docs.rdhpcs.noaa.gov/queue_policy/policies.html>
