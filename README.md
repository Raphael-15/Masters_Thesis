# Techno-Economic Assessment of Shared PV and Battery Energy Storage Systems in Residential Collective Systems

This repository contains the data, documentation, and models supporting the Master's thesis titled: "Techno-Economic Assessment of Co-Located PV and Battery Energy Storage Systems in Energy Communities".

## Purpose

The primary purpose of this repository is to collect and organise the inputs, models, and documentation needed to answer the thesis research questions: quantify how co-located PV+BESS affects energy flows, economics, and resilience at the community scale under different configurations and tariff/incentive regimes.

## Systemic approach and pipeline

1. Data ingestion and architecture
   - Raw smart-meter, PV, price, and metadata files are stored in the Bronze layer (see docs/Data_Architecture.md for details).
   - Cleaned and harmonized hourly datasets are stored in Silver, including hourly load, price, and PV Parquet files used as the model backbone.
   - The Gold layer contains model-ready member-level and community-level tables used to simulate no-DER, PV-only, and PV–BESS scenarios.

2. Pre-processing
   - Clean and align timestamps across load and generation datasets, handle missing data and aggregation/resampling as required by the modelling time-step (hourly).
   - Normalize units and ensure consistent time resolution for scenario runs.

3. Technical modelling
   - Create net-load profiles (load minus PV) for each scenario.
   - Implement BESS operational model: SoC tracking, charge/discharge limits, round-trip efficiency, power/energy constraints, and an operational objective (e.g., maximise self-consumption or minimise cost).
   - Produce per-timestep outputs: battery dispatch, grid import/export, curtailed generation, SoC.

4. Techno-economic modelling
   - Quantify CAPEX/OPEX assumptions for PV and BESS, replacement cycles, discount rate and lifetime.
   - Calculate KPIs: LCOE, NPV, internal rate of return (IRR), simple payback, levelized cost of storage, and cost-benefit under tariff/incentive structures.

5. Scenario & sensitivity analysis
   - Vary PV sizes, battery capacities and power ratings, tariff regimes, incentives, and operational strategies.
   - Run sensitivity sweeps on key input parameters (cost trajectories, discount rate, degradation) to understand robustness of results.

6. Outputs & reporting
   - Time-series visualisations (net-load, SoC, dispatch), summary tables of KPIs per scenario, and figures/tables for thesis chapters.
   - Documentation links modelling choices to literature justification from `Literature Review.docx` and `Model_Formulation.docx`.

## Important modelling note (base case)

- Battery degradation is NOT modelled in the base-case simulations. The base-case operational runs and lifecycle economic results therefore omit capacity fade, cycle-related losses, and scheduled battery replacements. This is a stated limitation of the current analyses and may lead to optimistic long-term performance and NPV/LCOE estimates. Degradation can be enabled as an optional extension; see docs/Model_Formulation_equations.md for the optional throughput/cycle-based proxy and instructions.

## Files & folders (root-level)
- README.md (this file)
- `bronze/` — raw files: smart-meter, PV, price, metadata (raw CSV/ZIP or vendor formats)
- `bronze/load_raw/` — raw load uploads (source-specific)
- `bronze/pv_raw/` — raw PV scenario inputs
- `silver/` — cleaned, harmonized hourly Parquet files (load, pv_hourly.parquet, prices)
- `gold/` — model-ready aggregated/member-level tables for scenario runs
- `docs/` — curated model excerpts and equations (includes Data_Architecture.md)
- `Introduction .docx` — project introduction and scope
- `Literature Review.docx` — review of related work and methodological justification
- `Case_Study_and_Data_Architecture_CITED.docx` — case study description and data architecture (cited)
- `Model_Formulation.docx` — formal model description and equations
- `Thesis_Table_of_Contents.docx` — thesis TOC

## Excerpt from Introduction (abridged / selected paragraphs)

The thesis investigates the techno-economic implications of co-locating photovoltaic generation with battery energy storage within energy communities. It frames the study around the needs of community stakeholders, regulatory environments, and the role of distributed flexibility in reducing peak demand and improving self-consumption.

The approach is data-driven: high-resolution load profiles for the community are combined with PV generation scenarios to produce net-load time series. A battery model with realistic operational constraints and efficiencies is used to simulate dispatch under different control strategies. Note: the base-case simulations do not include degradation unless explicitly enabled in the optional model extension.

## How to reproduce (high-level)
1. Prepare the environment: install required Python/R packages for time-series analysis, optimisation (if present), and plotting.
2. Place/verify data in `bronze/` and `silver/` and follow the Data Architecture document for file format expectations.
3. Run the pre-processing scripts to align timestamps and generate net-load profiles.
4. Execute the BESS dispatch routine for each scenario and record outputs.
5. Run the techno-economic analysis module to compute KPIs and aggregate scenario results.
6. Recreate figures/tables for thesis chapters from the results folder (exported CSVs/plots).

## Reproducibility artifacts
The repository includes reproducibility files, sample data, an executable example notebook, and a GitHub Actions smoke test to verify that the workflow runs successfully. The Python environment is defined through `requirements.txt` and `environment.yml`, while small example input files are provided under `data/sample/`. The notebook `notebooks/example_end_to_end.ipynb` demonstrates a minimal end-to-end workflow, and the GitHub Actions workflow in `.github/workflows/run_notebook.yml` automatically executes the notebook on push or pull request to confirm that the example runs without errors.

---
