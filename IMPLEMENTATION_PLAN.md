IMPLEMENTATION_PLAN
===================

Status
------
This file supplements the previously prepared implementation plan and explicitly records the raw input dataset paths you asked me to check. All content in the canonical LaTeX chapters remains authoritative and unchanged.

Confirmed raw dataset paths (REQUIRED INPUT)
-------------------------------------------
The following raw dataset directories are REQUIRED INPUTS and must be populated in the repository before running the full experiments. These directories correspond to the Bronze/raw layer described in Chapter 4 and the earlier implementation plan.

- data/raw/load/            — per‑member raw household smart‑meter files or a single combined raw load file. REQUIRED INPUT: full-year hourly load series for every participant (timestamps, member_id, load_kwh).
- data/raw/pvgis/           — PVGIS (or equivalent) raw PV output files (1 kWp reference) for the representative year. REQUIRED INPUT: hourly PV power/time series files (kW or W) and associated metadata (tilt, azimuth, location).
- data/raw/omie/            — OMIE day‑ahead hourly wholesale price series (raw downloads). REQUIRED INPUT: hourly OMIE prices for the representative year.
- data/raw/pvpc_import/     — PVPC import variable energy price series (raw source files). REQUIRED INPUT: hourly residential import price series (€/kWh) used for billing valuations.
- data/raw/pvpc_export/     — PVPC excedentaria export‑credit series (raw source files). REQUIRED INPUT: hourly export credit series (€/kWh) used for billing compensation calculations.

Mapping to the plan's Bronze/Silver/Gold layers
------------------------------------------------
- The directories above are the Bronze/raw layer. The data processing pipeline will:
  1. Read files from data/raw/... (Bronze)
  2. Clean, harmonise timestamps and units -> write to data/silver/... (Silver)
  3. Produce model-ready member-hour-scenario tables -> write to data/gold/... (Gold)

Where to place the files and expected formats
--------------------------------------------
- data/raw/load/
  - Expect either one CSV with columns [member_id,timestamp,load_kwh] or a per-member CSV named member_{id}_load.csv with columns [timestamp,load_kwh]. Timestamps must include timezone or be accompanied by a metadata timezone declaration.

- data/raw/pvgis/
  - Expect PVGIS hourly export for the representative location/year. A canonical filename: pvgis_1kw_seville_{year}.csv with columns [timestamp,power_kw] or [timestamp,power_w].

- data/raw/omie/
  - Expect files with columns [timestamp,price_eur_mwh] or [timestamp,price_eur_kwh] and a note on units; the data IO layer must convert units to €/kWh used by the dispatch routine.

- data/raw/pvpc_import/ and data/raw/pvpc_export/
  - Expect hourly CSVs with [timestamp,price_eur_kwh]. If units differ, the Silver processing converts to €/kWh.

Action taken
------------
- I added this explicit set of required raw data directory paths and descriptions to IMPLEMENTATION_PLAN.md in the repository so the plan explicitly references data/raw/... as the Bronze/raw layer. The file was created at the repository root.

What I changed (commit)
-----------------------
- Created file: IMPLEMENTATION_PLAN.md
  - Commit message: "Add IMPLEMENTATION_PLAN.md with explicit raw data paths"

Next steps (recommended)
------------------------
1. Populate each data/raw/... directory with the appropriate raw CSV files (or archives) for the chosen representative year.
2. Run the data cleaning script (to be implemented or invoked) that reads data/raw/* and writes data/silver/* (timestamp alignment, unit harmonisation).
3. Provide scenario register (config/scenarios.csv or scenarios.yaml) listing the scenario parameter values.

If you want, I can now:
- (A) open the newly created IMPLEMENTATION_PLAN.md file so you can review its exact contents, or
- (B) update the implementation plan further to include file‑naming conventions, example header rows for each raw CSV, and a small data ingestion script outline.

