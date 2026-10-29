# Orion Storage Reference

Orion's storage is administered by MSU-HPC, and its layout differs from the
NOAA-operated RDHPCS systems: shorter home quota, no `quota -Qs`, no documented
`htar`/`hsi` examples, and a different archive path back to Niagara.

---

## Filesystem Overview

| Filesystem | Path | Capacity | Quota | Backup | Notes |
|-----------|------|----------|-------|--------|-------|
| Home (NFS) | `/home/<userid>` | — | 10 GB per user | Nightly | Configs and dotfiles only |
| `work` (Lustre) | `/work/noaa/<project>` | 9 PB usable, shared with Hercules | project-based | **No** | DDN Lustre SFA18k |
| `work2` (Lustre) | `/work2/noaa/<project>` | 18 PB usable, shared with Hercules | project-based | **No** | DDN Lustre SFA18k with an SSD "Hot Pool" |
| Applications | `/apps/` | — | — | — | Read-only software tree |
| Contrib | `/apps/contrib/<package>` | — | request-based | — | User-maintained software |

`/work` and `/work2` are mounted on both Orion and Hercules over the shared
InfiniBand fabric, but they are **scratch**: neither is backed up and neither is
long-term storage.

---

## Which Lustre Filesystem to Use

Every NOAA project received an allocation on both. MSU's advice is empirical:
`/work2` has more than twice the capacity of `/work` and its SSD tier can improve
small-file performance and random I/O, so **try both and keep whichever measures
better for your workload**. Do not assume `work2` is automatically faster.

---

## Checking Quota and Usage

`saccount_params` is the documented tool on Orion (load the NOAA tooling first).
It prints your home quota in MB, then one block per project with FairShare, core
hours used over 30 days, the 30-day allocation, the project directory, and disk
and file usage:

```bash
module load contrib noaatools
saccount_params
```

Example shape of the home line from MSU's guide:

```
Home Quota (/home/<userid>)   Used: 1035 MB   Quota: 8192 MB   Grace: 10240
```

Note the quota is reported in **MB** (8192 MB = 10 GB), while the project lines
report GB. A windfall-only project shows an allocation of 1 and lists only
`windfall` under Available QOSes.

Other documented reports:

```bash
shpcrpt -c orion -s            # core-hour usage; all projects you can see
shpcrpt -c orion -p <project>  # one project only
reportFSUsage                  # Lustre quota and usage report
du -sh $HOME                   # home usage against the 10 GB quota
```

`reportFSUsage` prints a "LUSTRE QUOTA AND USAGE REPORT" with columns
`Directory/Group`, `Usage (GB)`, `Quota (GB)`, `Limit (GB)`, `Files`, and
`Percentage`, and marks an over-quota project with `**`.

The `quota -Qs` command RDHPCS documents for Gaea, Ursa, Hera, and Mercury is
**not** documented for Orion, and RDHPCS publishes no `lfs quota` guidance for the
MSU systems either. There is no `account_params` alias — MSU states you must use
`saccount_params`.

---

## File Counts

The Lustre report tracks a `Files` column against a per-project file quota, so a
project can be blocked by inode pressure while still under its byte quota. The
standard remedy applies: pack many small files into a tar before writing them, and
clean up restart and checkpoint debris rather than keeping every cycle.

---

## Home Directory

- NFS, **10 GB** per user, backed up nightly.
- The directory is **deleted when your account is deleted**, and deleted HFS data
  is not recoverable. Accounts are scheduled for deletion two weeks after an
  un-renewed expiry date, and lock after 90 days of inactivity.
- Project data on `/work` and `/work2` survives an individual user's deletion.

RDHPCS's fleet data-storage page describes an online `~/.snapshot` backup tree with
`hourly.*`, `daily.*`, and `weekly.*` snapshots. That page does not name Orion, and
the MSU guide documents only "backed up on a nightly basis", so **do not promise a
`.snapshot` recovery path on Orion** — ask the help system to restore from the
nightly backup.

Do not run jobs against files in `/home`, and do not point `-o`/`-e` there: it is
small, NFS, and shared.

---

## Transferring Data In and Out

| Method | Endpoint | Use |
|--------|----------|-----|
| SCP / SFTP | `orion-dtn-1.hpc.msstate.edu` … `orion-dtn-4`, or `orion-dtn.hpc.msstate.edu` (DNS round-robin) | Direct copies |
| Globus | endpoint `msuhpc2-Orion-dtn` | Large or bulk transfers, Globus File Manager app or CLI |
| Open OnDemand | Orion web portal | Browser file management, job submit/monitor, remote desktop |

MSU explicitly recommends **Globus** because of limited network bandwidth, and
recommends moving data back to the R&D HPC **Niagara** system because Orion's disk
space is limited. You authenticate to the DTNs and the portal with your MSU
username, password, and Duo.

Development nodes (`orion-devel-1`, `orion-devel-2`) are SSH-reachable from inside
only.

---

## `/apps` and `/apps/contrib`

`/apps/` holds the supported software tree. `/apps/contrib/<package>` is
user-maintained software that MSU creates **on request through a help ticket**.
The development nodes are the only gateway for writing into `/apps/contrib`, so a
build that installs there must run on `orion-devel-*`, not on a login node or in a
batch job.

Orion's software is spack-built, and its module and directory names differ from
Hercules — MSU gives `/apps/spack/<package-hash>` style paths for Hercules. Do not
copy a path from one system to the other; discover it with `module show`.

---

## Archiving

The `service` partition's front-end nodes hold the external connection, so MSU
places HSMS/HPSS push and pull workflows there (1 core, 24 hours). The MSU-HPC
guide does **not** publish `hsi` or `htar` command examples for Orion, and the
RDHPCS archiving page describes NESCC's HPSS on the NOAA-operated systems. Before
writing an archive script for Orion, confirm the approved commands and the correct
`module load` line with the help system at `rdhpcs.orion.help@noaa.gov`. The
default long-term path for Orion data is Niagara, not HPSS.

---

## What Goes Where

| Data | Location |
|------|----------|
| Dotfiles, small configs, SSH keys | `/home/<userid>` |
| Source and build trees | `/work/noaa/<project>/<user>` or `/apps/contrib/<package>` |
| Model input, output, restarts | `/work/noaa/<project>/<user>` (test `work2` for small files) |
| Job stdout/stderr | `/work/noaa/<project>/<user>` — never `/home` |
| Software shared with collaborators | `/apps/contrib/<package>` (help ticket, written from a devel node) |
| Data no longer in active use | Niagara, via Globus |
