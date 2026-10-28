# NOAA RDHPCS HPC Skills — Design

**Date:** 2026-10-28
**Scope:** `skills/hpc-skills/`

## 1. Goal

Replace the three DOE-lab machine skills (`frontier`, `aurora`, `perlmutter`) in
`skills/hpc-skills/` with skills for the NOAA Research and Development High
Performance Computing Systems (RDHPCS), so that an agent helping a NOAA
researcher writes job scripts, chooses partitions/QOS, and places data
correctly on RDHPCS machines instead of DOE ones.

The skills are **script-authoring** skills: the agent works in a checkout on a
workstation or container and produces or reviews job scripts, module loads, and
storage paths for a human to submit. They are not written to assume the agent
itself is logged into a login node.

## 2. Sources of fact

Two sources, each authoritative for a different class of claim:

- **https://docs.rdhpcs.noaa.gov** — machine hardware, partition names, QOS
  limits, file systems, quotas, purge policy, access/bastion process. Every
  machine-specific number in these skills comes from here.
- **The `omd` MCP server** (`~/.copilot/mcp-config.json`, docker image
  `omd-mcp`) — indexes NOAA software documentation: `nws-hpc-standards`
  (11.0.0), `ufs-weather-model`, `esmf` (8.9.1), `dask-jobqueue` (0.9.0),
  `kokkos`, `jedi`, `ccpp`, `ecflow`, `mom6`, `mpas`, `fv3`, `cice`,
  `grib2io`, `pytorch`.

The omd index contains **no RDHPCS machine specifications**. Searches for
"hera", "orion", "RDHPCS", and "Lustre" return unrelated ESMF sections. omd is
therefore used for NOAA *software and coding standards*, and
docs.rdhpcs.noaa.gov is used for *machine facts*. This design does not embed
omd tool calls in the skills (see §9).

Jet is decommissioned and is out of scope. Its data stays readable on Ursa
login nodes at `/jet/home/$USER`, `/jet/contrib` and `/jet/lfs[5,6]` only until
2026-07-31, and only LFS files accessed during March 2026 survived, so the
Ursa/PPAN/Gaea skills must not send an agent to Jet for anything.

## 3. Systems in scope

| System | Scheduler | Site | Notes |
|---|---|---|---|
| Hera | Slurm + LMOD | NESCC, Fairmont WV | Skylake 6148, 40 cores/node |
| Ursa | Slurm | NESCC, Fairmont WV | AMD Genoa CPU + NVIDIA H100 / GH200 / AMD MI300X GPU partitions |
| Orion | Slurm + LMOD | MSU HPC2 | Skylake 6148, 40 cores/node. Managed by Mississippi State University, not OCIO; NOAA documents it in the MSU-HPC user guide and it is not in the RDHPCS systems list |
| Hercules | Slurm + LMOD | MSU HPC2 | Xeon 8380, 80 cores/node. MSU-HPC, as Orion |
| Gaea | Slurm federation + Cray CPE | ORNL NCCS | C5/C6/C7 HPE-Cray EX3000, GPFS F5/F6/F7 |
| PPAN | Slurm | GFDL, Princeton NJ | analysis + post-processing hosts, CXFS |
| Mercury | none | NESCC/GFDL | data transfer only, no compute nodes |
| Cloud | Slurm on ad-hoc clusters | — | ParallelWorks, ACTIVATE, storage costing |

Hera and Ursa share HPFS file systems and one QOS table. Orion and Hercules
share the MSU-HPC documentation, account system, and `work`/`work2` file
systems. Each still gets its own skill: an agent working on Ursa should not
have to load Orion's facts, and per-machine skills are how `unpack.sh` installs
them (one directory per skill, standalone).

## 4. Directory layout

```
skills/hpc-skills/
├── slurm/                  # kept, refreshed (§6)
├── pbs/                    # kept, unchanged
├── rdhpcs-hera/            SKILL.md + references/{job-scripts,storage,programming-env}.md
├── rdhpcs-ursa/            SKILL.md + references/{job-scripts,storage,programming-env}.md
├── rdhpcs-orion/           SKILL.md + references/{job-scripts,storage,programming-env}.md
├── rdhpcs-hercules/        SKILL.md + references/{job-scripts,storage,programming-env}.md
├── rdhpcs-gaea/            SKILL.md + references/{job-scripts,storage,programming-env}.md
├── rdhpcs-ppan/            SKILL.md + references/storage.md
├── rdhpcs-mercury/         SKILL.md
└── rdhpcs-cloud/           SKILL.md
```

Deleted: `frontier/`, `aurora/`, `perlmutter/`.

Full-tier skills (five) are compute machines where job scripts, storage
placement, and the programming environment are each substantial enough to need
their own file. Slim-tier skills cover systems whose guidance is one page: PPAN
needs the storage/archive detail but not a job-script set, and Mercury and Cloud
have no batch job to write.

## 5. Naming

`rdhpcs-` prefix on all eight skills.

Bare `hera`/`ursa`/`orion`/`gaea` follow the existing `perlmutter`/`frontier`
convention, but bare `cloud` and `mercury` are ambiguous in a catalog that also
contains `globus-compute`, `amsc-data-movement-api`, and `iri-api`. The prefix
makes each name self-describing in skill listings and in `description` trigger
text, and groups the family visibly. Names are lowercase, hyphenated, and under
the 64-character limit, so they satisfy the spec's `name` constraints.

## 6. Shared policy lives in `slurm`

`skills/hpc-skills/slurm/SKILL.md` is kept and gains an "RDHPCS shared policy"
section holding facts true across the RDHPCS fleet, so machine skills state
their own deltas rather than restating a full table:

- **Access.** SSH through `*-mfa.{princeton,fairmont}.rdhpcs.noaa.gov` bastions
  with CAC/PIV or YubiKey MFA; first login generates a master certificate
  request that must be signed before full access; the passphrase must contain
  at least three words.
- **QOS semantics and billing factors** (from
  `queue_policy/policies.html#qos-table`, which is the authoritative source —
  the per-QOS "Billable TRes" column in the individual system guides shows a
  single repeated value (165 on Hera, 100 on Ursa) that does not correspond to
  any per-QOS factor, so the skills use the policy table and leave that column
  out): `batch` TRES 1,
  `urgent` TRES 2 with FairShare penalty and one pending/running job per
  project, `debug` TRES 1.25 at 30 minutes and two jobs per user, `long` 16
  hours, `windfall` TRES 0 (free, lowest priority), `gpu` TRES 1, `gpuwf`
  TRES 0.
- **Job caps.** Max 1500 jobs (pending + running) per project/account, extra
  jobs rejected at submit; max 400 running per project; max 20 gaining age
  priority.
- **Login node prohibition.** No computation on front ends; use the `service`
  partition for compiles, data transfer, and HPSS access.
- **`scrontab` preferred over `cron`** for recurring work.
- **Home quota.** Not uniform across the fleet. The per-system tables on the
  data-storage page give Gaea 50 GB, Ursa and Hera 30 GB, Mercury and Pan
  10 GB, and the MSU-HPC guide gives Orion and Hercules 10 GB; the queue-policy
  page's fleet-wide "50 GB on each system" sentence contradicts those tables
  and is the less specific claim, so the skills state the per-system number and
  note the conflict. Check with `quota -Qs` (Gaea, Ursa, Hera, Mercury),
  `homeuse` (Pan), or `saccount_params` (Hera and Orion only — not a fleet
  command). `/home` is backed up and supports user-recoverable snapshots at
  `~/.snapshot`.
- **Scratch is never backed up.** HPFS-scratch is for current job I/O, not long
  term storage; use HPSS/GFDL-DMF for archive.
- **Purge rules.** `stmp` on `/scratch3-4` purged weekly (Monday, >30 days);
  `/scratch5/purged` purged at 90 days since access.
- **Hot-pool double counting.** On `/scratch3-4`, the first 1 GB of an active
  file is written to the SSD tier and mirrored to HDD, so reported usage may be
  doubled.
- **Compilers and MPI.** The fleet software page lists Intel and NVIDIA
  compilers with Intel MPI and recommends the **Intel compiler + Intel MPI**
  combination unless there is a specific reason otherwise: `module load intel/<v>
  impi/<v>` with wrappers `ifx`/`ifort` (Fortran), `icx`/`icc` (C/C++),
  `mpiifx -fc=ifx`, `mpiicx`. There is **no `oneapi-hpckit` module** anywhere in
  the docs. `-xHOST` is recommended for **Hera only**. Debug starting point
  `-O0 -g -traceback -check all -fpe0`. Ursa's own page additionally lists AMD
  AOCC and HPC-X/OpenMPI and says it has seen better performance and stability
  from HPC-X on the NDR-200 fabric, so the Ursa skill reconciles the two rather
  than picking one.
- **Containers.** RDHPCS supports **SingularityCE and Apptainer** and explicitly
  criticises Docker (root/sudo to build and run; microservice model fits large
  parallel jobs poorly). Per system: Gaea apptainer, Hera singularity +
  apptainer, Ursa apptainer, PPAN singularity, Hercules/Orion singularity with
  `module load singularity` (their apptainer is a Spack-managed install that
  loads its own environment and may not combine with other modules). **Podman is
  not the fleet runtime** — it appears only in the PPAN and Gaea guides and
  needs an email to `oar.gfdl.help@noaa.gov` for access. The Ursa `u1-gh` Grace
  Hopper compute nodes are air-gapped, so ARM images must be built or pulled on a
  login node with `--arch arm64`. RDHPCS also runs a container registry at
  `registry.rdhpcs.noaa.gov`, which doubles as a spack mirror.
- **Debuggers and profilers.** Linaro Forge **DDT** is the documented GUI
  debugger; the recommended workflow is a **locally installed client connecting
  to the remote system over a forwarded SSH port**, and the local client version
  must match the Forge version on the system. Hera documents DDT and `map
  --profile` (MAP) with `module load intel impi forge`. GDB, GDB4HPC,
  Valgrind4hpc and the HPE Performance Analysis Tools are documented on **Gaea
  only**. Ursa, Orion/Hercules and PPAN publish no profiler or affinity
  guidance, so those skills point at the fleet pages and tell the agent to
  confirm with `module spider`.
- **Python.** `module load rdhpcs-python` on Gaea (after `module use
  /ncrc/usw/rdhpcs/modulefiles/`), Hera, Ursa and PPAN; `module load python` on
  Mercury; `module load contrib` **then** `module load rdhpcs-python` on
  Orion/Hercules.

Its `description` and `compatibility` are updated to name RDHPCS. Machine
skills link to it for shared policy but restate the values a user on that
machine needs in-line, because a skill must be usable standalone.

## 7. Per-skill content

Each full-tier `SKILL.md` follows the existing `perlmutter`/`frontier`
skeleton: frontmatter, System Overview table, Critical Requirements, Partitions
and QOS, minimal job script, storage table, modules, interactive jobs, Common
Gotchas, Additional Resources pointing at its own `references/`.

Frontmatter differs from the DOE skills in two ways, because these are
script-authoring skills:

- `allowed-tools` centers on `Read`/`Write`/`Grep`/`Glob` and drops the
  `Bash(sbatch *)` preapprovals — the agent is not submitting.
- `compatibility` states the access requirement (MFA bastion, signed x.509
  master cert; MSU-managed accounts for Orion/Hercules) instead of "must be
  logged into a login node".

`metadata` keeps the existing keys: `version`, `system`, `facility: rdhpcs`,
`scheduler`, plus `source` (§12).

### 7.1 rdhpcs-hera

- 1,328 regular + 268 `bigmem` Intel Skylake 6148 nodes, 40 cores/node,
  63,840 cores total, HDR-100 InfiniBand, 3.27 PFLOPS capacity. `bigmem` nodes
  have 384 GB. The docs' per-node memory row for regular nodes is malformed, so
  the skill states 40 cores/node and tells the agent to read actual node memory
  with `sinfo -o "%N %m %c"` rather than guessing a figure.
- Partitions: `hera*` (default), `bigmem`, `novel`, `service`.
- `novel` partition **requires** `novel` QOS and a help ticket in advance.
- `service` runs on front ends: external network + HPSS, default 1 core, max 4
  cores, 24 h limit.
- Programming env: LMOD hierarchical modules; IntelMPI with Intel compiler
  (`mpiifort`/`mpiicc`/`mpiicpc`) or MVAPICH2 with PGI (`mpif90`/`mpicc`);
  MPI-IO on Lustre needs `I_MPI_EXTRA_FILESYSTEM=on` and
  `I_MPI_EXTRA_FILESYSTEM_LIST=lustre`; `KMP_AFFINITY=scatter` recommended.
- Storage: shared with Ursa (`/scratch3-4` Lustre, `/scratch5` VAST).

### 7.2 rdhpcs-ursa

Covers CPU and GPU paths as first-class, because partition/QOS pairing is the
main failure mode:

| Path | Partition | QOS | Requires | Limits |
|---|---|---|---|---|
| CPU production | `u1-compute` | `batch`/`windfall`/`debug`/`urgent`/`long` | any Ursa project | 14,400 cores; 8 h (`long` 16 h) |
| Service/serial | `u1-service` | `batch`/`windfall` | — | max 64 cores and/or 250 GB per user, 24 h |
| H100, GPU alloc | `u1-h100` | `gpu` | project beginning `gpu-`, allocation ≥ 2 | 20 GPUs, 168 h, TRES 1 |
| H100, no GPU alloc | `u1-h100` | `gpuwf` | any Ursa project (windfall) | 10 GPUs, 48 h, TRES 0, ≤192 gpu-h running per project |
| GH200 exploratory | `u1-gh` | `gpuwf` | any project, FCFS, no fairshare | 8 nodes, ARM 72 cores, 1 gpu-h = 72 core-h |
| MI300X exploratory | `u1-mi300x` | `gpuwf` | any project, FCFS | 5 nodes, 96 Intel cores, 8× MI300X 192 GB, 1 gpu-h = 12 core-h |

- 576 AMD Genoa 9654 nodes (192 cores, 2.4 GHz) + 58 H100 nodes with 2×
  H100-94 GB; NDR-200 IB; Rocky 9.4.
- GPU type strings: `--gpus=h100:3`, `--gpus=gh200:1`, `--gpus=mi300x:2`.
- CPU-allocation projects get H100 windfall access and GPU-allocation projects
  get non-GPU windfall access.
- Exploratory partitions use different CPUs from production (ARM on `u1-gh`),
  so binaries are not portable between them; interactive `salloc` is the
  documented way in.
- Node sharing is enabled for all job sizes as of 2026-06-18 unless the job
  requests `--exclusive`.
- Compilers: Intel oneAPI, NVIDIA nvhpc, AMD AOCC. MPI: Intel MPI, HPC-X,
  OpenMPI — HPC-X is documented as better performing and more stable on the
  NDR-200 fabric. ROCm for MI300X, CUDA for H100/GH200.
- Storage: `/scratch3-4` Lustre with project quotas, `/scratch5` VAST all-flash
  (quotas only for `rstprod` and `public`; everyone else uses
  `/scratch5/purged/$USER`, 250 TB quota, 90-day purge).

### 7.3 rdhpcs-orion

- 1,792 compute + 8 bigmem Dell PowerEdge C6420, Skylake 6148 40 cores, 192 GB
  (bigmem 384 GB), HDR-100 IB; 4 login, 4 DTN, 2 development nodes.
- Partitions: `orion` (general), `bigmem`, `service` (serial, max 1 core, 24 h).
  QOS allowed: `batch`, `windfall`, `debug`, `urgent`, `novel`.
- Storage: DDN Lustre `work` (9 PB) and `work2` (18 PB, hot-pool SSD cache),
  both scratch and not backed up; `/home` NFS **10 GB**, backed up nightly.
- Accounts are MSU HPC2 managed and completely independent of RDHPCS accounts.
- Cron available on `orion-login-1` only.
- Default wall clock is 5 minutes if unspecified — jobs silently die at 5
  minutes without `-t`.

### 7.4 rdhpcs-hercules

- 512 Dell PowerEdge C6520, Xeon Platinum 8380 40C ×2 = 80 cores/node, 512 GB,
  NDR-200 IB; 4 login, 4 DTN, 4 development nodes; no bigmem tier.
- Partitions: `hercules` (general), `service`.
- Same `work`/`work2` Lustre, same 10 GB `/home`, same MSU account system as
  Orion.
- The skill must not let an agent assume Orion's 40-core node shape on Hercules.

### 7.5 rdhpcs-gaea

- Three HPE-Cray EX3000 generations, 2 threads per core on all of them:
  C5 (1,920 nodes; 2× 64-core EPYC Zen 2 = 128 cores, 256 GB, AVX-2, 8 NUMA
  domains), C6 (2,048 nodes; 2× 96-core EPYC Zen 4 = 192 cores, 384 GB,
  AVX-512, 8 NUMA), C7 (1,208 nodes; 2× 192-core EPYC Zen 5c/Turin = 384 cores,
  768 GB, AVX-512, 4 NUMA, Slingshot-11). >20 PFLOPS aggregate.
- Login nodes are a **separate** set per cluster (`gaea5[1-6]`, `gaea6[1-6]`,
  `gaea7[1-6]`) with their own memory sizes (512 GB / 512 GB / 1.6 TB) and must
  not be quoted as the compute-node memory.
- **Slurm is a federation**: clusters `c5`, `c6`, `c7`, `es`. Commands default
  to the cluster you are on; use `-M`/`--clusters=c6` or set `SLURM_CLUSTERS`.
  `#SBATCH -M c5` is the script form.
- **System-specific GPFS**: `/gpfs/f5` for C5, `/gpfs/f6` for C6, `/gpfs/f7`
  for C7, each with `<projID>/scratch/<user>`, `proj-shared` (770), and
  `world-shared` (775). None backed up, none purged.
- DTNs: `dtn[50-79]` mount `/gpfs/f5`, another set mounts F6; both mount
  `$HOME`. Use the `es` cluster and `dtn_f5_f6` partition with
  `--constraint=f5` or `--constraint=f6` to land on a DTN with the right
  filesystem.
- Cray CPE: `PrgEnv-*` modules and `cc`/`CC`/`ftn` wrappers, `craype-*` target
  modules; SLES 15.5 on C5/C6, RHEL 9.8 on C7.
- Queue policy is the two-allocation model: 50% for `urgent`/`novel` (`novel` =
  jobs needing >25% of system cores, run in the 8-hour window after
  preventative maintenance), 50% for `batch`/debug/interactive; `windfall`
  charges nothing.

### 7.6 rdhpcs-ppan

- ~130 Dell hosts at GFDL: ~20 analysis hosts for interactive use, ~100
  post-processing hosts named `pp006`, `pp317`, etc., under Slurm.
- Intel generations Sandy Bridge → Ice Lake, 48–512 GB.
- CXFS high-performance interface to `/archive` and `/work`; file systems
  `/home`, `/nbhome`, `/archive`, `/vftmp` and `$TMPDIR`, `/work`, `/ptmp`,
  `/net`, `/net2`, `/net3`.
- `archrpt` for archive reports and group/user quotas.
- Nearly 200 PB of archive storage; Slurm lets Gaea jobs submit
  post-processing here.
- Containers: the fleet container table gives PPAN **singularity** with no
  module load required. The PPAN guide additionally documents **Podman** on
  PPAN and Gaea, but access must be requested by emailing
  `oar.gfdl.help@noaa.gov` and naming Podman in the subject, so the skill leads
  with singularity and mentions Podman only as the opt-in alternative.

### 7.7 rdhpcs-mercury

- **No compute nodes.** 4 login nodes plus trusted DTNs and untrusted DTNs
  (uDTNs); dual-socket AMD EPYC Genoa 9654.
- Purpose: securely copy data to/from anywhere for collaborators.
- First login auto-creates `/home/First.Last`, `/collab2/data/First.Last`,
  `/collab2/data_untrusted/First.Last`.
- Visibility rules: `/home` is **not** accessible from DTNs; `/collab2/data`
  is accessible from both DTNs and uDTNs; `/collab2/data_untrusted` is
  accessible only from uDTNs.
- `/collab2` is Mercury's HPFS-scratch.
- CRON services and HPSS access documented for this system.

### 7.8 rdhpcs-cloud

- Ad-hoc HPC clusters on demand plus ParallelWorks remote access.
- ACTIVATE for projects; use ParallelWorks to reach on-prem RDHPCS systems,
  access the cluster head node, run Jupyter on a Slurm compute node, and run
  VS Code from a compute node.
- Storage types and costs: Lustre, bucket/block blob storage, `contrib` file
  system; cost calculator; usage reports.
- Quota warning messages forwarded from on-prem systems.

## 8. Error handling

Each skill's "Common Gotchas" section is RDHPCS-specific rather than generic,
covering the failures an agent actually produces:

- Missing `-A <account>` (mandatory everywhere).
- `novel` partition without `novel` QOS (Hera, and the MSU `novel` QOS).
- `gpu` QOS with a non-`gpu-` project on Ursa (rejected) where `gpuwf` was
  meant.
- Windfall-only projects (monthly allocation = 1) may use only `windfall` or
  `gpuwf`; other submissions are rejected.
- Forgetting `--exclusive` when a job needs a whole Ursa node.
- Compiling or running on a login node instead of `service`.
- Exceeding `/home` quota — 30 GB on Hera/Ursa, 50 GB on Gaea, 10 GB on
  Mercury, Pan, Orion and Hercules.
- No `-t` on MSU: default wall clock is 5 minutes.
- MPI-IO on Lustre without `I_MPI_EXTRA_FILESYSTEM` set.
- Gaea: wrong `-M` cluster, or writing to `/gpfs/f6` from a C5 job.
- Mercury: assuming `/home` exists on a DTN, or trying to run compute.
- Job rejection at submit time (1500 cap) versus queued pending (400 cap).

## 9. Non-goals

- No omd MCP tool calls embedded in the skills. omd is a guidance source for
  this conversion, not a runtime dependency; the skills must work without it.
- No changes to `pbs`.
- No `scripts/` directories or executable helpers — these skills produce job
  scripts, they do not submit them.
- No Jet coverage (decommissioned).
- No changes to `skills/baseeval-skills/perlmutter-ns-skills/`, which targets
  NERSC for a different purpose and is not part of this subtree.

## 10. Repository bookkeeping

- `skills/hpc-skills/ATTRIBUTION.md`: skill list updated — remove
  `aurora`/`frontier`/`perlmutter`, add the eight `rdhpcs-*` entries; note that
  machine facts come from docs.rdhpcs.noaa.gov.
- `README.md`: the `hpc-skills/` tree line and count are regenerated.
  `validate_repo_policy.py` compares that code block against
  `build_readme_tree_lines()`, so it must be updated in the same commit.
- `NOTICE`: unchanged — its entry is for the `skills/hpc-skills/` subtree as a
  whole.
- `tests/test_repo_policy.py` uses `skills/hpc-skills/aurora` as a synthetic
  fixture path in a temp tree, not the real directory, so deleting `aurora`
  does not break it. It is left alone.

## 11. Verification

1. `python3 tools/validate_skills.py --profile all --no-color --format text`
   (via `make verify-new-skill`) — frontmatter dialect, `name` uniqueness across
   the catalog, description and compatibility length limits, body constructs.
2. `make test` — existing suite still passes after the deletions.
3. New `tests/test_rdhpcs_consistency.py` — the drift guard, scoped to this
   conversion:
   - Parse the QOS limits and storage/quota facts stated in each `rdhpcs-*`
     skill and assert they agree with the consolidated table in `slurm`, so a
     value edited in one place but not another fails CI.
   - Assert every `references/` link in each `rdhpcs-*` SKILL.md resolves to a
     file that exists.
   - Assert no `rdhpcs-*` skill or the refreshed `slurm` skill mentions
     `perlmutter`, `frontier`, `aurora`, or NERSC/OLCF/ALCF paths.
   - **Not** applied to `pbs`, which stays and legitimately cites Aurora as an
     example of a PBS machine, nor to other subtrees (for example
     `plasma-sim-skills/gkeyll` and `amsc-skills/globus-compute` reference a
     Perlmutter machine script of their own, unrelated to this subtree). No
     file outside the deleted directories links into them, so the deletions
     break no references.
4. Manual spot-check of each machine's partition names and QOS values against
   docs.rdhpcs.noaa.gov.

## 12. Risks and provenance

- **Facts go stale.** RDHPCS adds hardware (C7, `/scratch5`, MI300X are all
  recent). Mitigation: every SKILL.md carries a `metadata.source` docs URL and
  a `metadata.as_of` date, and the consistency test pins cross-skill agreement.
- **Duplication between machine skills and `slurm`.** Unavoidable if skills
  must load standalone; the consistency test is the guard rather than an
  attempt to eliminate the duplication.
- **Ursa partition names are recent and easy to mis-transcribe** (`u1-compute`,
  not `batch`). Mitigation: §7.2 is the single place the values are written,
  and the test checks them.
