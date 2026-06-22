# Data Architecture — Excerpt (short)

This short excerpt summarises the canonical Data Architecture (Bronze–Silver–Gold). See docs/Data_Architecture.md for full details.

- Bronze: raw ingested files (bronze/load_raw/, bronze/pv_raw/, bronze/prices_raw/, bronze/metadata/manifest.json). Keep originals and record provenance.
- Silver: cleaned, harmonized hourly Parquet artifacts used by the model backbone (silver/load_hourly.parquet, silver/pv_hourly.parquet, silver/prices_hourly.parquet). Units: kWh (energy), €/MWh (prices stored).
- Gold: model-ready scenario tables (gold/member_profiles.parquet, gold/community_scenarios.parquet) used directly by dispatch routines.

Notes: timestamps are Europe/Madrid; QA flags gaps/duplicates; Parquet preferred for Silver; do not apply blind interpolation — follow the gap policy in Bronze manifest.
