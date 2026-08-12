# Phase 3 Task 1 — Bronze/Silver Input Freeze

## Status

PASS

## Phase 2 input boundary

- Selected simulation year: 2013
- Calendar ready: True
- Expected annual hours: 8760
- Final households: 30
- Complete households: 30
- Canonical load rows: 262800
- Reconstructed household-hours: 11990
- Load metadata valid: True
- Joint Spanish input coverage: 8760 hours
- Representative-year mapping required: False

## Frozen files

- Bronze files: 13
- Existing processed/Silver files: 7
- Total frozen files: 20

## Integrity method

Every frozen file is recorded using its relative path,
file size, and SHA-256 checksum.

Manifest:

`results/phase3_task1_input_manifest.csv`

## Phase 3 rule

Files recorded in this manifest define the frozen
Phase 2 input boundary. Existing Bronze and Silver
files must not be overwritten during Phase 3.
New Phase 3 outputs must be written to new Gold,
configuration, metadata, audit, or results files.
