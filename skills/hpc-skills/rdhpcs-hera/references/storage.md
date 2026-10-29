# Hera Storage Reference

Hera's file systems are shared with Ursa at NESCC. Two of them are backed up and one of
those is small; the rest are scratch, which means nothing in them survives a decision to
stop paying for it.

Scratch directories have a portfolio level in them. The documented layout is
`/scratch[3,4]/<portfolio>/<project>/<user>`, so expect paths like
`/scratch3/noaa-hpc/myproject/First.Last` rather than a project directory directly under
`/scratch3`.

---

## Filesystem Overview

| Filesystem | Path | Quota | Backed up | Purged | Use for |
|-----------|------|-------|-----------|--------|---------|
| Home | `/home/First.Last` | 30 GB | Yes, plus `~/.snapshot` | No | Code, configs, small persistent files |
| Home snapshots | `/home/First.Last/.snapshot/` | counts toward home | Per-day copies | Rolling | Recovery of deleted or corrupted files |
| Scratch | `/scratch3`, `/scratch4` | project-based | **No** | No (except `stmp`) | Job input and output |
| Scratch temp | `/scratch[3,4]/.../stmp` | project-based | **No** | Weekly, Monday, >30 days | Short-lived intermediates |
| VAST scratch | `/scratch5` | project quota for `rstprod` and `public` | **No** | No | All-flash experimental work |
| VAST purged | `/scratch5/purged/First.Last` | 250 TB pool | **No** | Files not accessed in 90 days | Everyone else's `/scratch5` access |
| Archive | NESCC-HPSS | portfolio-managed | Yes | No | Long-term retention |

---

## Checking Quota and Recovering Files

```bash
# Projects, fairshare, partition access, and disk and file usage per project directory
saccount_params

# Home usage against the quota
quota -Qs

# Where the bytes actually are
du -sh /scratch3/<portfolio>/<project>/<user>/*
```

`saccount_params` is documented on Hera and Orion only — it is not available on the rest of
the fleet. It prints home quota in MB, your fairshare and rank per project, the partitions
and QOSes you may use, and a `DiskInUse`/`Quota`/`Files`/`FileQUota` line for each project
directory. The `-l` option adds 30-day core-hour usage and allocation.

Quota problems on RDHPCS are usually file *count* rather than bytes: a directory of a
million small results can exhaust an inode quota while `du` reports gigabytes. Compare
`Files` against `FileQUota` before hunting for large files.

`/home` keeps per-day snapshots in a directory that does not appear in `ls`, even `ls -a`,
but which you can list directly. Scratch has **no** snapshots — a file deleted from
`/scratch3` is gone:

```bash
ls /home/$USER/.snapshot/          # entries look like 2026-03-09_0015-0600.daily
cp /home/$USER/.snapshot/<daily-snapshot-name>/important.f90 .
```

The snapshot directory is available in any subdirectory of `/home`, so recover a file from
wherever you are. Hourly copies appear alongside the daily ones as `hourly.YYYY-MM-DD-HHMM`.

---

## Purge Policy

| Location | Rule |
|----------|------|
| `stmp` on `/scratch3-4` | Purged weekly on Mondays for files older than 30 days |
| `/scratch5/purged` | Purged for files not accessed in 90 days |
| `/scratch3`, `/scratch4` outside `stmp` | Not purged — but never backed up |
| Node-local temp | RDHPCS documents `$TMPDIR` only for PPAN, so use a scratch `stmp` directory for intermediates |

Find files approaching the `stmp` threshold before they disappear:

```bash
find /scratch3/<portfolio>/<project>/<user>/stmp -type f -atime +25
```

Tar aging results rather than letting them go, and tar many small files into one archive to
protect the file-count quota:

```bash
tar -C /scratch3/<portfolio>/<project>/<user> -cf run_2026-03.tar member.0001 member.0002
```

---

## Hot Pools and Reported Usage

On `/scratch3-4` the first 1 GB of each file is written to a solid-state hot pool and
mirrored to spinning disk 10 to 15 minutes later. While that copy is in flight the file's
usage can appear **doubled** in quota reports.

This is expected behavior, not a quota bug and not a sign that a job is writing twice. Wait
fifteen minutes and re-check before opening a ticket.

---

## Archiving to HPSS

HPSS is the only long-term store on this system besides `/home`. Archive work runs in the
`service` partition, because only those front ends hold the external connection. Load the
client with `module load hpss` inside the job:

```bash
# Single file up
hsi "put /scratch3/<portfolio>/<project>/<user>/result.nc /1year/PORTFOLIO/project/User.Id/result.nc"

# Directory up as a tar
htar -cvf /1year/PORTFOLIO/project/User.Id/results.tar ./results/
```

Retrieve with the mirror commands, and check what is archived and when it expires:

```bash
hsi "get /1year/PORTFOLIO/project/User.Id/result.nc result.nc"
htar -xvf /1year/PORTFOLIO/project/User.Id/results.tar

hsi "expls /1year/PORTFOLIO/project/User.Id"          # listing with expiration
hsi "expfind -d 30 /1year/PORTFOLIO/project/User.Id"  # expiring within 30 days
```

The batch-job form of this is in [job-scripts.md](job-scripts.md#hpss-staging-job).

---

## What Goes Where

| You have | Put it in |
|----------|-----------|
| Source code, job scripts, dotfiles | `/home` |
| Model input you regenerate cheaply | `/scratch3` |
| Model output other jobs read next | `/scratch3` |
| Intermediate files under 30 days old | `stmp` |
| I/O-bound experimental work needing flash | `/scratch5` |
| Anything you cannot afford to lose | HPSS, or `/home` if it fits in 30 GB |
| Data a collaborator needs long-term | HPSS or GFDL-DMF |

Two rules that RDHPCS states plainly:

1. **Never run a job against files in `/home`**, including through a symlink that points
   at scratch. Home I/O from compute jobs degrades the file system for everyone.
2. **Scratch is not storage.** It is not backed up, and a project that lapses can lose it.
   Move anything worth keeping to HPSS.

The published home quota figures disagree with each other: the queue-policy page claims
50 GB on every system, while the data-storage summary table gives Hera 30 GB and the
example `quota` output on that same page shows a smaller limit again. Use what `quota -Qs`
reports for your own account, and ask the Help Desk for more rather than assuming.
