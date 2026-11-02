---
name: ee2-standards
description: >
  NCO Environmental Equivalence (EE2) production standards for code, shell scripts,
  and job delivery on WCOSS. Use when writing or reviewing operational Fortran, C,
  Python, or Bash for NCO delivery, checking FATAL ERROR and WARNING conventions,
  restart and cleanup rules, COM directory and file naming, prod_util calls such as
  err_chk or prep_step, module-driven builds, or release and bugfix branch naming.
metadata:
  version: "1.0"
  domain: standards
  source: https://nws-hpc-standards.readthedocs.io/en/stable/
  upstream_version: "ee-docs 11.0.0"
  as_of: "2026-11-02"
compatibility: >
  Reference and review skill; no cluster access required. Rules tagged WCOSS apply to
  NCO operational delivery; rules tagged portable also apply to RDHPCS and research code.
allowed-tools: Read Grep Glob
---
