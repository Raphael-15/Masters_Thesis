# Data Architecture (Bronze–Silver–Gold pipeline)

Accurate summary of the thesis data architecture and expected file formats.

Overview

The thesis data architecture follows a Bronze–Silver–Gold pipeline:

- Bronze: raw files as ingested from sources. This includes smart-meter uploads, PV scenario inputs, market price files, and metadata. Raw files may be CSV, ZIP (archives from vendors/Kaggle), Excel, or other vendor formats. Bronze stores the original files and a small metadata manifest for provenance.

  Example directories:
  - bronze/load_raw/ — raw load uploads (per-member or aggregated, source-specific formats)
  - bronze/pv_raw/ — raw PV scenario inputs
  - bronze/prices_raw/ — market price files (OMIE/ESIOS native resolution)
  - bronze/metadata/manifest.json — source, pull date, file hash, timezone, units, license notes

- Silver: cleaned, harmonized and validated datasets at the modelling resolution (hourly). All time series used by the model backbone are stored here as Parquet for efficiency and schema enforcement.

  Key Silver artifacts:
  - silver/load_hourly.parquet — cleaned hourly community/member load in kWh
  - silver/pv_hourly.parquet — scaled PV generation (kWh) at hourly resolution
  - silver/prices_hourly.parquet — prices aligned to hourly (€/MWh) and flagged for billing conversions

  Notes:
  - The modelling backbone is hourly: all analyses aggregate or resample raw data to hourly where required. Raw load can be half-hourly or 15-min in some sources; OMIE/ESIOS price data may be 15-min or different native resolution. These are harmonized to hourly in Silver.
  - Units: energy variables are in kWh and price variables are in €/MWh (convert to €/kWh or billing units during analysis as needed).
  - Parquet format is preferred for Silver for schema, compression, and read performance.

- Gold: model-ready, scenario-specific tables derived from Silver. Gold contains the prepared inputs and aggregated outputs used directly by simulation notebooks and LP solvers.

  Example Gold artifacts:
  - gold/member_profiles.parquet — per-member hourly profiles used for representative scenario runs
  - gold/community_scenarios.parquet — pre-aggregated scenario inputs (net-load, PV, prices) ready for dispatch

Timestamp and timezone handling

- All timestamps in Silver/Gold are aligned to Europe/Madrid timezone (explicit timezone-aware timestamps). Conversions from source timezones are recorded in the Bronze manifest.
- QA/QC steps include checking for duplicates, gaps, and clock-skew; flagged intervals follow a gap policy (flag, review, and follow the declared gap policy rather than applying blind interpolation).

Quality assurance

- Validate ranges (e.g., PV non-negative; load non-negative), night-time PV zero checks, and energy unit consistency.
- Maintain manifest entries for each ingested file with file hash, provenance, and processing notes.

Other notes

- Storage and formats: Bronze stores originals (CSV/ZIP/etc.); Silver uses Parquet; Gold may export CSVs for reporting but retains Parquet for reproducible runs.
- File naming & conventions: prefer stable names like `load_hourly.parquet`, `pv_hourly.parquet` and document any deviations in the Bronze manifest.

This document should be used as the canonical architecture reference for preprocessing scripts, notebooks, and model runs.