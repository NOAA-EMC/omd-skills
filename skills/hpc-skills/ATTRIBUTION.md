# Attribution

**Team:** OMD - Modeling Division

**Author:** Barry Baker (OMD)

Licensed Apache-2.0 as part of this subtree - see [LICENSE](LICENSE).

Skills derived from the upstream ModCon hpc-skills subtree:
- `pbs` — PBS/OpenPBS batch job scheduling on any PBS cluster
- `slurm` — Slurm batch job scheduling on any Slurm cluster

The `aurora`, `frontier`, and `perlmutter` machine skills from the original
subtree were retired when this repository's HPC tier was converted to the
NOAA RDHPCS fleet.

## NOAA RDHPCS skills

The eight `rdhpcs-*` skills were authored for this repository from the public
NOAA RDHPCS documentation at <https://docs.rdhpcs.noaa.gov>; they are not
derived from the DOE lab skills. Machine facts are current `as_of` 2026-10-28
and should be re-verified against the guides below when they change:

- `rdhpcs-cloud` — NOAA RDHPCS Cloud on Parallel Works (on-demand clusters, on-prem access, storage and cost governance) — <https://docs.rdhpcs.noaa.gov/systems/cloud_user_guide.html>
- `rdhpcs-gaea` — NOAA RDHPCS Gaea at ORNL NCCS (Slurm federation, C5/C6/C7 generations, GPFS F5/F6/F7) — <https://docs.rdhpcs.noaa.gov/systems/gaea_user_guide.html>
- `rdhpcs-hera` — NOAA RDHPCS Hera (Slurm, E4-node shape, fleet QOS policy) — <https://docs.rdhpcs.noaa.gov/systems/hera_user_guide.html>
- `rdhpcs-hercules` — NOAA RDHPCS Hercules at MSU-HPC (Slurm, 80-core nodes, MSU accounts) — <https://docs.rdhpcs.noaa.gov/systems/MSU-HPC_user_guide.html>
- `rdhpcs-mercury` — NOAA RDHPCS Mercury data-transfer system (trusted/untrusted DTNs, /collab2 staging) — <https://docs.rdhpcs.noaa.gov/systems/mercury_user_guide.html>
- `rdhpcs-orion` — NOAA RDHPCS Orion at MSU-HPC (Slurm, 40-core nodes, MSU accounts) — <https://docs.rdhpcs.noaa.gov/systems/MSU-HPC_user_guide.html>
- `rdhpcs-ppan` — NOAA RDHPCS PPAN (Pan) at GFDL Princeton (Slurm post-processing tier, tape-backed /archive) — <https://docs.rdhpcs.noaa.gov/systems/ppan_user_guide.html>
- `rdhpcs-ursa` — NOAA RDHPCS Ursa (Slurm, H100 GPU queues, fleet QOS policy) — <https://docs.rdhpcs.noaa.gov/systems/ursa_user_guide.html>

The shared `slurm` skill carries the fleet-wide RDHPCS queue-and-allocation
policy derived from <https://docs.rdhpcs.noaa.gov/queue_policy/policies.html>,
and its RDHPCS Archive Storage Reference
(`slurm/references/storage.md`) is derived from the NESCC-HPSS and GFDL-archive
sections of <https://docs.rdhpcs.noaa.gov/data/storage.html>.
