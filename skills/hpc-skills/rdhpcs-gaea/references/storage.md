# Gaea Storage Reference

Source: the Gaea user guide
(<https://docs.rdhpcs.noaa.gov/systems/gaea_user_guide.html>) and the fleet
data-storage page (<https://docs.rdhpcs.noaa.gov/data/storage.html>).

## NFS File Systems

Users and projects get NFS space for applications, executables, and small data
files.

| Area | Path | Permissions | Quota | Backups | Purged | On compute nodes |
|------|------|-------------|-------|---------|--------|------------------|
| User Home | `/ncrc/home[12]/<userID>` | user set | 50 GB | Yes | No | Yes |
| Project Home | `/ncrc/proj/<projID>` | project set | 100 GB | Yes | No | Yes |

Home backups run at regular intervals — hourly for the past 24 hours, daily
for the last 7 days, and longer-term snapshots on the fleet schedule. Because
Project Home is NFS, its performance is lower than the parallel filesystems,
and data files there **should only be small files (<100 MB)**; larger files
belong in the project work area.

**There is no `/nobackup` area on Gaea** — the GPFS member-work trees below
are the non-persistent space.

## GPFS (IBM Spectrum Scale) File Systems

Gaea has three GPFS file systems — F5 (75 PB), F6 (75 PB), F7 (70 PB) — each
attached to one compute generation. **A job can only reach the file system of
its own cluster.**

| Area | Path | Permissions | Quota | Backups | Purged | Available from |
|------|------|-------------|-------|---------|--------|----------------|
| F5 Member Work | `/gpfs/f5/<projID>/scratch/<userID>` | user set | N/A | No | No | C5 only |
| F5 Project Work | `/gpfs/f5/<projID>/proj-shared` | 770 | N/A | No | No | C5 only |
| F5 World Work | `/gpfs/f5/<projID>/world-shared` | 775 | N/A | No | No | C5 only |
| F6 Member Work | `/gpfs/f6/<projID>/scratch/<userID>` | user set | N/A | No | No | C6 only |
| F6 Project Work | `/gpfs/f6/<projID>/proj-shared` | 770 | N/A | No | No | C6 only |
| F6 World Work | `/gpfs/f6/<projID>/world-shared` | 775 | N/A | No | No | C6 only |
| F7 Member Work | `/gpfs/f7/<projID>/scratch/<userID>` | user set | N/A | No | No | C7 only |
| F7 Project Work | `/gpfs/f7/<projID>/proj-shared` | 770 | N/A | No | No | C7 only |
| F7 World Work | `/gpfs/f7/<projID>/world-shared` | 775 | N/A | No | No | C7 only |

`proj-shared` is for a single project's group; `world-shared` (775) is readable
by everyone on the system. Member work, project work, and world work are
**neither backed up nor purged**: files you abandon stay forever, and files you
need can be lost. Treat scratch as working space only.

The guide notes that the sentence "each compute cluster, C5 and C6, has its own
file system called F5 and F6" predates C7 — the storage table itself includes
the F7 rows mounted on C7.

## Checking Quota

Quotas are enforced on the NFS home areas. Gaea uses `quota` (unlike MSU-HPC
and Pan):

```bash
quota -Qs
# Disk quotas for user userid (uid 12345):
#     Filesystem         space  quota  limit  grace   files  quota  limit  grace
#  ncrc-svm1.ncrc.gov:/ncrc/home2  9228M 51200M 51200M       101k 4295m 4295m
```

Project Home usage: `df -h /ncrc/proj/<projID>`. Request a larger quota
through the Help Desk.

## GPFS Compression (F5 only)

Compression is enabled on **F5** and disabled on **F6**. The F5 policy:

- Algorithm `lz4`, migrating files to the `capacity` pool.
- Applies only to files with `KB_ALLOCATED >= 4096`.
- A file must be idle for **168 hours** — both modification time and access
  time older than 168 hours — before it is a candidate.
- Excluded paths: `/.SpaceMan/`, `/fs_audit_log/`, `/.snapshots/`, `/.msgq/`.
- Files are written uncompressed and compressed later by the compression cron
  job or an explicit `mmchattr` command.
- Compressed files are **not** decompressed when read; on modification only the
  relevant portion is decompressed and re-compressed later.

Decompress one file:

```bash
mmchattr --compression no -I yes <file>
```

There is **no direct command to report the compression ratio** — compare the
file's logical size (`ls`) against on-disk usage (`du`).

## Moving Data To and From Gaea

All extensive I/O operations, large local transfers, and **all off-Gaea
transfers** run on a data transfer node, on the `es` cluster under the
`dtn_f5_f6` partition:

| Host names | Configuration | File systems mounted |
|------------|---------------|----------------------|
| `dtn[50-79]` | AMD EPYC 7302 16-core, 256 GB | `/gpfs/f5`, `$HOME` |
| `dtn[01-09]` | AMD EPYC 7713 64-core, 512 GB | `/gpfs/f6`, `$HOME` |

Select a set with `--constraint=f5` or `--constraint=f6` when connecting or
submitting; otherwise you are routed automatically based on whether your
process originated on a C5 or C6 node.

The **suggested way to move data to and from Gaea is Globus Online** (see the
fleet Globus Connect / data-transfer pages). Firewall exceptions for external
transfers are requested through the help desk under the fleet's firewall
modification process.

## Performance Tips and Known Issues

- **GPFS F5 performance** — Gaea intermittently shows F5 slowness: file
  operation hangs in interactive sessions and jobs that run longer than normal
  or time out. The cause is still under investigation with ORNL and IBM; some
  slow read performance is tied to GPFS file compression.
- **Files accessed by multiple jobs** — do not let multiple batch jobs access
  the same files (typically through hard or soft links). That raises metadata
  server load and can lock up an MDS, affecting every file it serves. Clean up
  files after a successful job so the file system keeps free space.
- **Software environments** — do not store Conda, Python, or Spack environments
  on GPFS; their many small files get read from every compute node. Keep them
  in `/ncrc/home[12]/$USER` or `/ncrc/proj/<project>`, or request a location
  under `/usw` from the help desk for shared stacks.
- **Development** — do not develop on GPFS F5; develop in your home space,
  especially when using a source-code management system such as git. F5 is not
  backed up; the home area is, with hourly and daily snapshots.
- **Data transfer performance** — Gaea-to-GFDL archive transfers of files
  larger than 2 TB are slow. Transfers started with the Globus transfer app are
  believed unaffected; use Globus for large files until a resolution lands.
