# PPAN Storage Reference

PPAN (Pan) at GFDL separates three kinds of space: a small backed-up home area,
a tape-backed archive, and several scratch filesystems with different mount
polarity. This reference covers the sizes, the backup cadence, the quota
commands, the tape workflow, and `gcp` transfers.

## Filesystem Summary

| Path | Purpose | Backed up | Quota / usage command |
|---|---|---|---|
| `/home` | persistent home, unified between workstations and the analysis cluster | daily | `homeuse` |
| `/nbhome` | supplemental "no-backup" home | weekly | `homeuse` |
| `/archive` | GFDL tape archive filesystem | on tape | `archrpt -s` |
| `/work` | large long-term scratch | no | `quotause` |
| `/vftmp` | fast scratch local to each host | no | — |
| `$TMPDIR` | per-job or per-session directory under `/vftmp` | no | — |
| `/ptmp` | staging for FRE post-processing | no | — |
| `/net` | GFDL workstation filesystem (≥100 GB) | yes | — |
| `/net2`, `/net3` | GFDL workstation filesystems (≥100 GB) | no | — |

Home quotas are 10 GB for `/home` and 10 GB for `/nbhome`. The name
`/nbhome` ("no-backup `/home`") is misleading: it **is** backed up, weekly
rather than daily. Neither area is meant for model output.

## Home Areas

The GFDL workstations and the analysis cluster share a unified home directory,
and a short userdir name is provided as a shorthand for the longer
`First.Last` username. Check usage with the local `homeuse` command instead of
the usual `quota -vs`; it works on a GFDL workstation or the analysis cluster,
and its numbers are refreshed hourly:

```
linux> homeuse
/home & /nbhome usage - Jul 22 14:01
GROUP USERNAME FILESYS FILES GB QUOTA USE%
s First.Last - /home 80270 6.27 10 63%
s First.Last - /nbhome 110080 4.91 10 49%
```

`homerpt` produces group-level reports of `/home` or `/nbhome` usage; run it
with no options for its usage message.

## `/archive`: A Tape Filesystem

`/archive` is the GFDL tape archive filesystem. It behaves like any other
filesystem except that file data lives on tape until recalled to disk, and files
are recalled automatically when opened. It is mounted **read/write on the
analysis cluster** and **read-only on GFDL workstations**.

When many files are needed, recall them explicitly first (`dm` stands for Data
Migration; these commands run on the analysis cluster and on workstations):

```bash
dmget <files>          # recall files from tape
dmwho                  # show pending dmgets with wait times
dmls -l <files>        # show file state (disk or tape residence)
```

See the `dmgt` man page for details. Copy files from `/archive` to `/vftmp`
before working on them.

`/archive` is intended for **large files only**. To save small files, combine
related files into a single tar or cpio archive and store that larger file.

A `locate`-style database of `/archive` pathnames is updated daily:

```bash
dmlocate pattern       # search all of your /archive pathnames
```

### Archive allocations

The GFDL director allocates tape storage to each GFDL group, and a group leader
may set allocations for individuals within the group. The local `archrpt`
command shows those allocations and the percentage used:

```bash
archrpt -s             # your own allocation and usage
archrpt -r <group>     # a group's allocation report
```

Allocations are **enforced administratively**, not by a hard filesystem limit: a
background script checks quota compliance and emails the users of a group that
goes over its quota, or just the individual user when one person is over. Check
`archrpt` before a large archive write rather than relying on the write to fail.

## Scratch: `/vftmp`, `$TMPDIR`, `/work`, `/ptmp`

`/vftmp` is fast scratch **local to every analysis and post-processing host**.
On analysis hosts it ranges from 8 TB to 37 TB (shown on the login menu); on
most post-processing hosts it is 8 TB, with a few "bigvftmp" hosts at 27 TB or
44 TB. `$TMPDIR` points to a directory unique to each batch job or interactive
session and is **removed when the job or session ends**:

```
/vftmp/<First.Last>/pbs<pbs_jobid>   # in batch jobs
/vftmp/<First.Last>/pid<shell_pid>   # in interactive sessions
```

On analysis hosts you may keep longer-lived files in `/vftmp/<First.Last>`. They
are not backed up and not automatically wiped, but an administrator may remove
them if `/vftmp` fills. As far as possible, do interactive work in `$TMPDIR` or
`/vftmp/<First.Last>`. To return to the same analysis host later, press
Ctrl-C at the login menu and enter the host name.

`/work` is a large long-term scratch filesystem, **read/write on the analysis
cluster**, **not backed up**, and mounted **read-only** by the GFDL workstations.
Use `quotause` to see current usage. This is the normal destination for model
post-processing output.

`/ptmp` is used to stage data for FRE post-processing. It is not backed up and is
mounted read-only by the GFDL workstations.

## Mount Polarity

The guide states mount polarity for the analysis cluster and the GFDL
workstations; for the post-processing nodes it documents only `/vftmp` (local)
and that `/net`, `/net2`, and `/net3` are not mounted at all.

| Filesystem | Analysis cluster | GFDL workstation |
|---|---|---|
| `/home`, `/nbhome` | yes (unified with workstations) | yes |
| `/archive` | read/write | read-only |
| `/work` | read/write | read-only |
| `/ptmp` | read/write | read-only |
| `/vftmp` | local per host (8–37 TB) | — |
| `/net`, `/net2`, `/net3` | read-only | read/write |

`/net`, `/net2`, and `/net3` are GFDL workstation filesystems of 100 GB or more.
`/net` is backed up; `/net2` and `/net3` are not. Because they are read-only on
the analysis hosts and absent from post-processing nodes, transfers to and from
them go through `gcp`.

## `gcp`: Transfers Between NOAA Sites

`gcp` (general copy) copies data between NOAA RDHPCS sites with a `cp`-like
syntax:

```bash
module load gcp
gcp -v /path/to/some/source/file /path/to/some/destination/file
gcp /archive/USER/testfile gfdl:/net2/USER/testfile
gcp gfdl:/net2/USER/testfile /archive/USER/testfile
```

`-v` enables verbose output that is useful for debugging; `gcp --help` lists the
options. **Smartsites** name the remote site, like an scp hostname, and are
prepended to the path (`gaea:/path/to/file`). The guide lists **GFDL Pan and GFDL
workstations in Princeton, NJ** and **Gaea, the ORNL-hosted NCRC/CMRS system in
Oak Ridge, TN** as the supported smartsites. The smartsite of the destination can
usually be omitted because `gcp` can infer it.

Useful options and limits:

- `-cd` creates missing directories; a trailing slash marks the final path
  segment as a directory, otherwise it is treated as a file.
- `-r` transfers directory contents recursively.
- `--sync` copies only when the source is newer, recursive or not.
- Sources from remote sites **cannot include wildcards**.
- From a GFDL workstation you cannot push files to a remote site — use the Pan
  cluster to push or pull. Transfers from Pan need a valid Globus proxy
  certificate in your home directory, created or updated when you log in to Pan
  and valid for 30 days.
- Moving a file directly out of `/archive` can be very inefficient; transfer it
  to `/ptmp` first.

## Practical Rules

1. Model output goes to `/work` (or `/archive`), never `/home` — the quota is
   10 GB.
2. Recall with `dmget` before opening many tape-resident files, then work from a
   copy in `/vftmp`.
3. Treat `$TMPDIR` as ephemeral: nothing there survives the job.
4. Check `archrpt` before a large archive write; enforcement is administrative.
5. Reach `/net[23]` with `gcp`, not with a mount, from any analysis session.
