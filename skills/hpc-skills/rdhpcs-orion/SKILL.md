---
name: rdhpcs-orion
description: >
  NOAA RDHPCS Orion system at the Mississippi State University HPC2
  collaboratory. Use when writing Slurm job scripts for Orion, choosing the
  orion, bigmem, or service partition, requesting Skylake 40-core nodes, working
  with MSU-HPC account management that is separate from RDHPCS accounts,
  placing data on the work or work2 Lustre scratch filesystems or the 10 GB NFS
  home, using cron on orion-login-1, or discovering LMOD compiler and MPI
  modules on Orion.
compatibility: Script-authoring skill; no login required. Orion is hosted at Mississippi State University, so access uses MSU credentials and Duo rather than the NOAA RDHPCS bastions.
metadata:
  version: "1.0"
  system: orion
  facility: rdhpcs
  scheduler: slurm
  source: https://docs.rdhpcs.noaa.gov/systems/MSU-HPC_user_guide.html
  as_of: "2026-10-28"
allowed-tools: Read Write Grep Glob
---

# Orion — MSU-HPC (NOAA RDHPCS)

Orion is NOAA's allocation on the Mississippi State University HPC2 system, one
of the two MSU-HPC machines (the other is Hercules). Slurm schedules the jobs and
LMOD provides the software; the operating system is **CentOS 7.x**.

Access is different from the NOAA-operated RDHPCS systems: you connect directly
to `orion-login.hpc.msstate.edu` (or through Open OnDemand) with an **MSU**
username, MSU password, and Duo two-factor, and MSU administers accounts and
projects independently of RDHPCS. Read the `slurm` skill's *RDHPCS Shared
Policy* first for the fleet-wide QOS semantics and job-authoring rules.

## System Overview

| Item | Value |
|------|-------|
| Node model | Dell EMC PowerEdge C6420 |
| CPU | Intel Xeon Gold 6148, 20 cores x 2 sockets = **40 cores per node** at 2.40 GHz |
| Nodes | 1,792 compute + 8 bigmem = **1,800 total** |
| Total cores | 72,000 |
| Memory | 192 GB per compute node (12 x 16 GB DDR4-2666); 384 GB per bigmem node (12 x 32 GB) |
| Interconnect | Mellanox HDR-100 InfiniBand |
| Login nodes | 4 |
| Data transfer nodes | 4 |
| Development nodes | 2 |
| Scheduler / modules | Slurm / LMOD |
| OS | CentOS 7.x |

Orion and Hercules share the InfiniBand fabric and both Lustre filesystems, but
MSU documents them as **standalone systems**: separate batch systems, separate
logins, no federation, and FairShare computed per system.

## Critical Requirements

1. **`-A <account>` is mandatory.** Every job must name a project account.
2. **Always set `-t`.** The default wall clock is **5 minutes**; a job with no
   time request is silently killed at 5 minutes.
3. **Never request less than 5 minutes.** MSU explicitly recommends against it.
4. **Do not over-request.** Long wall clocks increase your wait and reduce
   scheduler efficiency for everyone. MSU suggests padding observed runtimes by
   10-20% for short jobs and 5-10% for long ones.
5. Any job that passes its requested wall clock **or** its partition limit is
   terminated by the scheduler.

## Partitions

| Partition | QOS allowed | Notes |
|-----------|-------------|-------|
| `orion` | batch, windfall, debug, urgent, novel | General compute; 40 cores and 192 GB per node |
| `bigmem` | batch, windfall, debug, urgent | 8 nodes with 384 GB; no `novel` |
| `service` | batch, windfall, debug, urgent | Serial jobs, maximum **1 core**, 24-hour limit, runs on front ends with external network and HSMS/HPSS access |

List several partitions only when the job genuinely runs on any of them, and
remember that when you do, the **longest** partition limit governs, so size the
wall clock accordingly.

## QOS

MSU publishes its own per-QOS table for Orion and Hercules. It agrees with the
RDHPCS fleet policy on wall clock and billing factor, but expresses job size in
**nodes** rather than cores and applies different caps:

| QOS | Min nodes | Max nodes | Maximum Wall Clock | Billing TRES Factor | Limits |
|-----|-----------|-----------|--------------------|---------------------|--------|
| `batch` | 1 | 500 | 8 hours | 1.0 | Default QOS for projects with more than a windfall-only allocation (`RawShare=1`) |
| `urgent` | 1 | 500 | 8 hours | 2.0 | **One job per project pending or running.** FairShare drops at twice the batch rate; below 0.45 the job is changed to `batch` and the user is notified on stderr |
| `debug` | 1 | 500 | 30 minutes | 1.25 | Two jobs per user pending or running; highest priority; not for fast-turnaround general work |
| `windfall` | 1 | 500 | 8 hours, partition exception for `service` | 0.0 | Lowest priority, charges nothing, does not affect FairShare; the only QOS a windfall-only project may use |
| `novel` | 501 | largest partition | 8 hours | 1.0 | Nearly the whole system; submit a help ticket first so MSU can schedule the window with you |

Every QOS on Orion: a maximum of **400 pending/running jobs per project**
(additional jobs are rejected), and only 20 jobs per project gain age priority.
Those caps replace the 1500-total/400-running pair RDHPCS publishes for Hera and
Ursa — do not apply the fleet numbers here.

Two differences worth flagging to users: Orion has no `long`, `gpu`, or `gpuwf`
QOS, and its size limits are node counts (max 500 nodes, `novel` from 501) rather
than the core counts the fleet table gives. The `urgent` and `debug` job caps
match the fleet wording. To read the live wall clocks:

```bash
sacctmgr show qos format=Name,MaxWall
```

## Minimal Job Script

```bash
#!/bin/bash
#SBATCH -A myproject
#SBATCH -J myjob
#SBATCH -p orion
#SBATCH -q batch
#SBATCH -N 1
#SBATCH --ntasks-per-node=40
#SBATCH -t 4:00:00
#SBATCH -o /work/noaa/myproject/user/myjob_%j.out

module load contrib
module load intel impi
cd /work/noaa/myproject/user/run.456
srun ./my_mpi_app
```

MSU's own example writes `module load intel <version>` and `module load impi
<version>`, so pin the versions `module avail` lists. Serial jobs get the
memory-per-core share of the node by default; request `--mem=<MB>` for more, or
`--exclusive` for the whole node. Use the `service` partition when the job needs
external network or HSMS access.

## Storage

| Filesystem | Path | Quota | Backup | Use for |
|-----------|------|-------|--------|---------|
| Home | `/home/<userid>` | 10 GB | Nightly | Code and configs — never job I/O |
| Scratch | `/work/noaa/<project>` | project-based | **No** | Job input and output (DDN Lustre SFA18k, 9 PB shared) |
| Scratch | `/work2/noaa/<project>` | project-based | **No** | Same layout, 18 PB with an SSD "Hot Pool" that helps small files and random I/O |
| Archive | HSMS/HPSS | portfolio-managed | Yes | Long-term retention, reached from the `service` partition |

Both `work` filesystems are scratch and are **not** backed up, and MSU warns that
Orion's disk space is limited — move data back to the RDHPCS Niagara archive when
a project no longer needs it live. Only members of a NOAA project may read
`/work/noaa` or `/work2/noaa`. Your home directory is **deleted when your account
is deleted**; project data is not.

## Accounts and Projects

MSU accounts are completely independent of RDHPCS accounts. A Principal
Investigator or Project/Portfolio Manager must hold an active MSU account to
manage projects online, and requests new users and project assignments through
the MSU HPC2 account management system. New users change their temporary password
in MSU's TAPS within 3 days, complete MSU security and insider-threat training,
and set up Duo. Seven failed logins lock the account for 10 minutes; passwords
change yearly alongside January security training. Accounts lock after 90 days of
inactivity and are scheduled for deletion two weeks after their expiry date.

Your MSU username is **not** the RDHPCS `First.Last` long username. Anything
account-related goes to the help system at `rdhpcs.orion.help@noaa.gov`.

`module load contrib noaatools` exposes the NOAA tooling, including
`saccount_params`, which prints your home quota in MB plus per-project FairShare,
30-day core hours used, 30-day allocation, project directory, disk and file
usage, partition access, and available QOS list:

```bash
module load contrib noaatools
saccount_params
```

There is no `account_params` alias on Orion, and the `quota -Qs` command RDHPCS
documents for Hera, Ursa, Gaea and Mercury is not documented for Orion. Use
`saccount_params`.

## Cron and Recurring Work

MSU documents plain **`cron` on `orion-login-1` only**. It does not document
`scrontab` for Orion, so check `scrontab --help` before relying on it. `at`
exists on `login1` only. Anything launched from cron must be a workflow-manager
call, a script that submits or manages batch jobs, or a data task under two
minutes.

## Common Gotchas

- No `-t` — the job dies at 5 minutes with no warning.
- `-t` under 5 minutes, which MSU advises against.
- Assuming the 30 GB home quota of Hera or Ursa; Orion gives 10 GB.
- Writing job output to `/home` — it is NFS, small, and holds your configs.
- Scheduling cron on a login node other than `orion-login-1`.
- `novel` without a help ticket, or a `novel` job below 501 nodes.
- A second `urgent` job per project — only one may be pending or running at a time.
- Using an RDHPCS `First.Last` username where an MSU username is required.
- Compiling on a login node instead of the `service` partition or a development node.
- Expecting FairShare to carry between Orion and Hercules; each system computes its own.

## Additional Resources

- Annotated job scripts, serial and MPI patterns, interactive allocations: [references/job-scripts.md](references/job-scripts.md)
- Filesystems, quotas, backup, and the `saccount_params` report: [references/storage.md](references/storage.md)
- Module discovery, compilers and MPI, Python, containers: [references/programming-env.md](references/programming-env.md)
- MSU-HPC user guide: https://docs.rdhpcs.noaa.gov/systems/MSU-HPC_user_guide.html
