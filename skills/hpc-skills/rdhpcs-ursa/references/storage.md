# Ursa Storage Reference

Ursa's file systems are the same NESCC systems Hera uses: Lustre on `/scratch3-4`, the
all-flash VAST file system on `/scratch5`, and HPSS for archive. Over 100 PB total, above
1000 GB/s aggregate, shared with Hera.

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
| Scratch | `/scratch3`, `/scratch4` | project-based (Lustre) | **No** | No (except `stmp`) | Routine job input and output |
| Scratch temp | `/scratch[3,4]/.../stmp` | project-based | **No** | Weekly, Monday, >30 days | Short-lived intermediates |
| VAST scratch | `/scratch5` | project quota for `rstprod` and `public` only | **No** | No | All-flash work for those two projects |
| VAST purged | `/scratch5/purged/First.Last` | 250 TB pool | **No** | Files not accessed in 90 days | Every other project's `/scratch5` access |
| Node-local | `$TMPDIR` | per node | **No** | Job lifetime | Fast temporary files |
| Archive | NESCC-HPSS | portfolio-managed | Yes | No | Long-term retention |

RDHPCS states plainly that the HPFS scratch file systems are **not** backed up.

---

## Checking Quota and Recovering Files

```bash
# Home usage against the quota
quota -Qs

# Where the bytes actually are
du -sh /scratch3/<portfolio>/<project>/<user>/*
```

`saccount_params` prints projects, fairshare, partition access, and per-directory
`DiskInUse`/`Quota`/`Files`/`FileQUota`, but it is documented on **Hera and Orion only** — do
not expect it on Ursa. The Ursa guide points at its own `/scratch[3,4]` usage and quota
section instead.

Quota problems on RDHPCS are usually file *count* rather than bytes: a directory of a million
small results can exhaust an inode quota while `du` reports gigabytes. Tar small files into
one archive.

`/home` keeps per-day snapshots in a directory that does not appear in `ls`, even `ls -a`, but
which you can list directly. Scratch has **no** snapshots — a file deleted from `/scratch3`
is gone:

```bash
ls /home/$USER/.snapshot/          # entries look like 2026-03-09_0015-0600.daily
cp /home/$USER/.snapshot/<daily-snapshot-name>/important.f90 .
```

The snapshot directory is available in any subdirectory of `/home`. Hourly copies appear
alongside the daily ones as `hourly.YYYY-MM-DD-HHMM`.

---

## Purge Policy

| Location | Rule |
|----------|------|
| `stmp` on `/scratch3-4` | Purged weekly on Mondays for files older than 30 days |
| `/scratch5/purged` | Purged of all files not accessed in the past 90 days |
| `/scratch3`, `/scratch4` outside `stmp` | Not purged — but never backed up |
| `$TMPDIR` | Gone when the allocation ends |

RDHPCS says the `/scratch5/purged` schedule may be adjusted with usage, preceded by user
notification. Find files approaching the threshold before they disappear:

```bash
find /scratch5/purged/$USER -type f -atime +75
find /scratch3/<portfolio>/<project>/<user>/stmp -type f -atime +25
```

---

## `/scratch5` and the VAST File System

`/scratch5` is VAST, an all-flash file system offered alongside the Lustre `/scratch3-4`
systems. RDHPCS is explicit that it is newer and more expensive per petabyte, and that the
performance consequences for NOAA applications are not yet characterised — which is why only
two projects, `rstprod` and `public`, hold project-based quotas on it.

Everyone else works under the purged tree:

```bash
mkdir -p /scratch5/purged/$USER/$(basename "$PWD")
```

Rules for that tree:

- Create and use a **single sub-directory** under `/scratch5/purged`, named the same as the
  `First.Last` of your NOAA email.
- Users under `/purged` share a 250 TB quota.
- Nothing there is backed up, and files not accessed for 90 days are deleted.

RDHPCS asks for feedback on your experience with it, especially performance comparisons
against Lustre for your applications, through a help ticket titled `/scratch5` performance
results. If you are evaluating the file system, that ticket is part of the work.

---

## Hot Pools and Reported Usage

On `/scratch3-4` the first 1 GB of each file is written to a solid-state hot pool and
mirrored to spinning disk 10 to 15 minutes later. While that copy is in flight the file's
usage can appear **doubled** in quota reports.

This is expected behavior, not a quota bug and not a sign that a job is writing twice. Wait
fifteen minutes and re-check before opening a ticket.

---

## Archiving to HPSS

HPSS is the only long-term store on this system besides `/home`. Archive work runs in a
partition whose nodes hold the external connection — on Ursa that is `u1-service`, and RDHPCS
names it as the target for pushing and pulling data to and from HPSS. Load the client inside
the job:

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

The batch-job form is in [job-scripts.md](job-scripts.md#u1-service-serial-job).

---

## What Goes Where

| You have | Put it in |
|----------|-----------|
| Source code, job scripts, dotfiles | `/home` |
| Model input you regenerate cheaply | `/scratch3` or `/scratch4` |
| Model output other jobs read next | `/scratch3` or `/scratch4` |
| Intermediate files under 30 days old | `stmp` |
| I/O-bound work that needs flash, or an evaluation of VAST | `/scratch5/purged/$USER` |
| Anything you cannot afford to lose | HPSS, or `/home` if it fits in 30 GB |
| Data a collaborator needs long-term | HPSS or GFDL-DMF |

Two rules that RDHPCS states plainly:

1. **Never run a job against files in `/home`**, including through a symlink that points at
   scratch. Home I/O from compute jobs degrades the file system for everyone.
2. **Scratch is not storage.** It is not backed up, and a project that lapses can lose it.
   Move anything worth keeping to HPSS.

The published home quota figures disagree with each other: the queue-policy page claims
50 GB on every system, while the data-storage summary table gives Ursa 30 GB and the example
`quota` output on that same page shows a smaller limit again. Use what `quota -Qs` reports for
your own account, and ask the Help Desk for more rather than assuming.
