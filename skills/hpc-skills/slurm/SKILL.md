---
name: slurm
description: >
  Slurm workload manager for HPC batch job scheduling, including NOAA RDHPCS
  fleet policy. Use when submitting jobs with sbatch/salloc/srun, monitoring
  with squeue/sacct/sreport, cancelling with scancel, writing #SBATCH job
  scripts, choosing RDHPCS QOS tiers (batch, urgent, debug, long, windfall,
  gpu, gpuwf), respecting login-node and scratch rules on Hera, Ursa, Orion,
  Hercules, or Gaea, escalating a pending job's QOS with scontrol update, or
  checking fair-share and file-system quotas with sacctmgr, sacccount_params,
  or lfs quota.
compatibility: Requires access to a Slurm cluster (sbatch, squeue, sacct, sinfo available in PATH). RDHPCS systems additionally require CAC/PIV or YubiKey authentication through an RDHPCS bastion and a signed master certificate.
metadata:
  version: "2.0"
  scheduler: slurm
  facility: rdhpcs
  source: https://docs.rdhpcs.noaa.gov/queue_policy/policies.html
  as_of: "2026-10-28"
allowed-tools: Bash(sbatch *) Bash(squeue *) Bash(scancel *) Bash(sinfo *) Bash(sacct *) Bash(salloc *) Bash(srun *) Bash(scontrol *) Bash(sacctmgr *) Bash(sreport *) Read Write Grep Glob
---

# Slurm Workload Manager

Slurm is the dominant HPC batch scheduler. Jobs are submitted to queues (partitions), allocated nodes, and run with full or partial node access.

## Quick Command Reference

| Command | Purpose |
|---------|---------|
| `sbatch script.sh` | Submit a batch job script |
| `salloc` | Allocate nodes for an interactive session |
| `srun` | Run a parallel job step (inside or outside a batch job) |
| `squeue` | View pending and running jobs |
| `scontrol show job <id>` | Detailed job info |
| `scancel <id>` | Cancel a job |
| `scontrol hold/release <id>` | Hold or release a pending job |
| `sinfo` | Cluster partition and node status |
| `sacct` | Query completed job accounting records |
| `sacctmgr` | Manage accounts, QOS, and allocations |

### Job State Codes

| Code | State | Meaning |
|------|-------|---------|
| PD | PENDING | Waiting for resources |
| R | RUNNING | Currently executing |
| CG | COMPLETING | Cleaning up after execution |
| CD | COMPLETED | Finished with exit code 0 |
| CA | CANCELLED | Cancelled by user or admin |
| F | FAILED | Non-zero exit code |
| TO | TIMEOUT | Exceeded time limit |
| OOM | OUT_OF_MEMORY | Killed by memory manager |
| PR | PREEMPTED | Preempted by higher-priority job |

## Writing Job Scripts

Directives go at the top of the script as `#SBATCH` comments before any executable line.

**Minimal working script:**
```bash
#!/bin/bash
#SBATCH --job-name=myjob
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=32
#SBATCH --time=01:00:00
#SBATCH --account=myproject
#SBATCH --output=myjob_%j.out
#SBATCH --error=myjob_%j.err

module load gcc openmpi
srun ./my_application
```

### Key `#SBATCH` Directives

| Directive | Example | Notes |
|-----------|---------|-------|
| `--job-name` | `myjob` | Shown in squeue |
| `--nodes` / `-N` | `4` | Number of nodes |
| `--ntasks-per-node` | `128` | MPI ranks per node |
| `--cpus-per-task` / `-c` | `4` | Threads per MPI rank |
| `--time` / `-t` | `2-00:00:00` | `D-HH:MM:SS` or `HH:MM:SS` |
| `--partition` / `-p` | `gpu` | Queue to use |
| `--account` / `-A` | `myproject` | Allocation to charge |
| `--output` / `-o` | `job_%j.out` | Stdout path |
| `--error` / `-e` | `job_%j.err` | Stderr path |
| `--gres` | `gpu:4` | Generic resources (GPUs) |
| `--mem` | `64G` | Memory per node |
| `--mem-per-cpu` | `4G` | Memory per CPU core |
| `--exclusive` | — | Reserve entire node(s) |
| `--dependency` | `afterok:12345` | Wait for another job |
| `--array` | `0-99` | Submit job array |
| `--mail-type` | `END,FAIL` | Email notifications |
| `--mail-user` | `user@host` | Email address |

### Output Filename Tokens

| Token | Meaning |
|-------|---------|
| `%j` | Job ID |
| `%A` | Array parent job ID |
| `%a` | Array task index |
| `%x` | Job name |
| `%N` | First node name |

## Submitting Jobs

```bash
# Batch submission
sbatch script.sh

# Override directives at submission
sbatch --nodes=8 --time=4:00:00 script.sh

# Interactive allocation (drops into a shell on allocated node)
salloc --nodes=2 --time=1:00:00 --partition=debug
srun ./my_app          # run within the allocation
exit                   # release allocation

# One-off parallel command (creates its own allocation)
srun --nodes=1 --ntasks=4 ./my_app
```

## Monitoring Jobs

```bash
# Your jobs
squeue -u $USER

# All jobs, long format
squeue -l

# Specific job
squeue -j 12345

# Estimated start times for pending jobs
squeue --start -u $USER

# Full detail (reason for pending, TRES, etc.)
scontrol show job 12345

# Live updates every 5 seconds
watch -n5 squeue -u $USER
```

**Reading output files:** Slurm writes stdout/stderr when the job finishes (or continuously if `--output` is to a path). Watch a running job's output:
```bash
tail -f myjob_12345.out
```

**After job completes:**
```bash
sacct -j 12345 --format=JobID,State,Elapsed,MaxRSS,ExitCode
```

## Cancelling and Holding Jobs

```bash
scancel 12345                      # cancel by job ID
scancel 12345_5                    # cancel one array element
scancel -u $USER --state=PENDING   # cancel all your pending jobs
scancel -n myjob                   # cancel by name

scontrol hold 12345                # hold a pending job
scontrol release 12345             # release held job
```

## Job Arrays

Run many similar jobs from one submission. Each element gets a unique `SLURM_ARRAY_TASK_ID`.

```bash
#SBATCH --array=0-99             # indices 0..99
#SBATCH --array=1-50:2           # odd indices 1,3,5,...,49
#SBATCH --array=0-999%20         # up to 20 running at once
#SBATCH --output=job_%A_%a.out   # %A=parent ID, %a=task index
```

Inside the script, use `$SLURM_ARRAY_TASK_ID` to select input:
```bash
INPUT="data/input_${SLURM_ARRAY_TASK_ID}.txt"
srun ./process "$INPUT"
```

Array management:
```bash
squeue -r -j 36           # show all elements
scancel 36                # cancel entire array
scancel 36_[1-5]          # cancel elements 1–5
```

## Job Dependencies

Chain jobs so they start only when a predecessor finishes:

```bash
JOB1=$(sbatch stage1.sh | awk '{print $4}')
sbatch --dependency=afterok:$JOB1 stage2.sh

# Common dependency types:
# afterok:<id>    — start only if <id> succeeds
# afterany:<id>   — start regardless of <id> outcome
# afternotok:<id> — start only if <id> fails
# singleton       — only one job with this name runs at a time
```

## Common Environment Variables (Inside a Job)

| Variable | Value |
|----------|-------|
| `$SLURM_JOB_ID` | Job ID |
| `$SLURM_NODELIST` | List of allocated nodes |
| `$SLURM_NTASKS` | Total number of tasks |
| `$SLURM_CPUS_PER_TASK` | CPUs per task |
| `$SLURM_SUBMIT_DIR` | Directory where `sbatch` was run |
| `$SLURM_ARRAY_JOB_ID` | Parent array job ID |
| `$SLURM_ARRAY_TASK_ID` | This element's index |

## Module System

```bash
module avail              # list available modules
module spider <pkg>       # search for a package
module load gcc/12 openmpi/4.1
module list               # show loaded modules
module purge              # unload everything
```

Always load modules inside the job script, not just in your login shell.

## Additional Resources

- Annotated job script examples: [references/job-scripts.md](references/job-scripts.md)
- Monitoring, troubleshooting, scontrol recipes: [references/job-control.md](references/job-control.md)
- Accounting, fairshare, allocation reporting: [references/accounting.md](references/accounting.md)
- Copy-paste templates: [assets/templates/](assets/templates/)

## RDHPCS Shared Policy

These rules apply on every NOAA Research and Development High Performance
Computing System (RDHPCS): Hera, Ursa, Orion, Hercules, Gaea, PPAN, Mercury,
and Cloud. The per-machine skills restate the values their users need, because
a skill is installed standalone; this section is the shared reference. Facts
come from [docs.rdhpcs.noaa.gov](https://docs.rdhpcs.noaa.gov).

### Access

All RDHPCS access is SSH through a site bastion, authenticated with a CAC/PIV
card or a YubiKey:

```text
<system>-mfa.princeton.rdhpcs.noaa.gov
<system>-mfa.fairmont.rdhpcs.noaa.gov
```

The first login attempt generates a master certificate request that must be
signed before you get a full session, usually in under five minutes. The
passphrase protecting that certificate must contain at least three words. If
you forget it, keep trying — the fourth attempt offers to recreate the master
certificate.

### QOS reference (Hera and Ursa)

Specify with `--qos=<name>` or `#SBATCH --qos=<name>`.

| QOS | Max walltime | Max cores | Billing TRES | Limits |
|-----|-------------|-----------|--------------|--------|
| `batch` | 8 hours | 8400 (Hera) / 14400 (Ursa) | 1 | Default QOS for projects with more than a windfall-only allocation |
| `urgent` | 8 hours | 8400 (Hera) / 14400 (Ursa) | 2 | One pending and one running job per project. FairShare drops at twice the batch rate; below FairShare 0.45 the job is silently changed to `batch` |
| `debug` | 30 mins | 8400 (Hera) / 14400 (Ursa) | 1.25 | Two jobs per user. Highest priority; not for general fast-turnaround work |
| `long` | 16 hours | 4200 (Hera) / 7296 (Ursa) | 1 | Normal priority for 8 to 16 hour jobs |
| `windfall` | 8 hours | 8400 (Hera) / 14400 (Ursa) | 0 | Lowest priority, charges nothing, does not lower FairShare |
| `gpu` | 168 hours | 20 GPUs (Ursa `u1-h100`) | 1 | Requires a project whose name begins `gpu-` with allocation 2 or larger |
| `gpuwf` | 48 hours | 10 GPUs (`u1-h100`) / 8 GPUs (`u1-gh`, `u1-mi300x`) | 0 | Windfall GPU access, open to every Ursa project; at most 192 gpu-hours running per project |

A project with a **windfall-only** allocation (monthly allocation of 1) may
submit only to `windfall` or `gpuwf`.

**Job caps, every QOS on Hera and Ursa:** 1500 total jobs (pending plus
running) per project or account, and jobs beyond that are **rejected at submit
time**, not queued; 400 running jobs per project; only 20 jobs per project
gain age priority.

### Change a pending job's QOS

Start cheap and escalate only if the job will not start — RDHPCS recommends
this to protect FairShare:

```bash
sbatch --qos=windfall job.sh                  # submit at no cost
scontrol update job 26866,26867 qos=batch     # promote now
echo "scontrol update job 26990 qos=batch" | at -M now +5min   # promote if still pending
```

Never schedule an `at` time below 120 seconds. On Orion and Hercules `at`
exists only on `login1`. A job moved to a QOS it does not qualify for stays
pending forever rather than failing.

### Login nodes

Login (front end) nodes are shared and are **not** for computation: no
compiling, no parallel or threaded runs, no long I/O. Use the `service`
partition instead, which runs on nodes with external network and HPSS access.
Exceptions are covered by the RDHPCS Login Node Usage Policy.

### Recurring work

Prefer `scrontab` over `cron`. Where `cron` exists it is limited to specific
front ends (Orion `orion-login-1`, Hercules `hercules-login-1`; Mercury runs
its own CRON service).

### File systems

| Rule | Value |
|------|-------|
| Home quota | 50 GB per system at `/home/First.Last`, except MSU-HPC Orion and Hercules at 10 GB |
| Home backed up | Yes, nightly, plus per-day snapshots in `~/.snapshot` |
| Scratch backed up | **No** — scratch is not backed up and must never be treated as long-term storage |
| Scratch purged | Not purged, except `stmp` on `/scratch3-4` (weekly, Monday, files older than 30 days) and `/scratch5/purged` (files not accessed in 90 days) |
| Long-term archive | NESCC-HPSS or GFDL-DMF only |
| Check quota | `sacccount_params`, `quota`, or `lfs quota -u $USER <path>` |

Do not run jobs against files in `/home`, including through symlinks that
point at scratch. It degrades the home file system for every user on the
system.

On `/scratch3-4` the first 1 GB of each file is written to a solid-state hot pool
and mirrored to disk 10 to 15 minutes later, so reported usage for an active
file can look **doubled**. That is expected, not a quota bug.
