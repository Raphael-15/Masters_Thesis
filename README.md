# Techno-Economic Assessment of Co-Located PV and Battery Energy Storage Systems in Energy Communities

This repository contains the data, documentation, and models supporting the Master's thesis titled: "Techno-Economic Assessment of Co-Located PV and Battery Energy Storage Systems in Energy Communities". The work evaluates the technical performance and economic viability of co-locating photovoltaic (PV) generation and battery energy storage systems (BESS) within energy communities using data-driven time-series analysis and scenario-based techno-economic modelling.

## Purpose

The primary purpose of this repository is to collect and organise the inputs, models, and documentation needed to answer the thesis research questions: quantify how co-located PV+BESS affects energy balances in a community, determine key technical performance indicators (self-consumption, self-sufficiency, curtailment), and evaluate the techno-economic outcomes (LCOE, NPV, payback) across scenarios and sensitivities.

## Systemic approach and pipeline

1. Data ingestion and architecture
   - Load time-series consumption data are stored in the `SMEC/` directory (community/consumer load profiles).
   - PV generation scenarios are in the `Gen/` directory (zipped generation datasets and scenario bundles).
   - Thesis documents (Table of contents, Introduction, Literature Review, Data Architecture, Methodology, Model Formulation) describe data formats, assumptions, and model choices.

2. Pre-processing
   - Clean and align timestamps across load and generation datasets, handle missing data and aggregation/resampling as required by the modelling time-step.
   - Normalize units and ensure consistent time resolution for scenario runs.

3. Technical modelling
   - Create net-load profiles (load minus PV) for each scenario.
   - Implement BESS operational model: SoC tracking, charge/discharge limits, round-trip efficiency, power/energy constraints, degradation assumptions, and an operational objective (e.g., maximise self-consumption, minimise peak import, or maximise arbitrage where applicable).
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

## Files & folders (root-level)
- README.md (this file)
- `SMEC/` — load data (time-series for the case study community)
- `Gen/` — PV generation datasets and scenario zip files
- `Introduction .docx` — project introduction and scope
- `Literature Review.docx` — review of related work and methodological justification
- `Case_Study_and_Data_Architecture_CITED.docx` — case study description and data architecture (cited)
- `Model_Formulation.docx` — formal model description and equations
- `Thesis_Table_of_Contents.docx` — thesis TOC

## Excerpt from Introduction (abridged / selected paragraphs)

The thesis investigates the techno-economic implications of co-locating photovoltaic generation with battery energy storage within energy communities. It frames the study around the needs of community-scale energy sharing and how combined PV+BESS systems can increase self-consumption, reduce peak demand on the distribution grid, and support higher shares of renewables without excessive curtailment.

The approach is data-driven: high-resolution load profiles for the community are combined with PV generation scenarios to produce net-load time series. A battery model with realistic operational constraints (power and energy limits, efficiency losses, and state-of-charge dynamics) is used to simulate dispatch under different objectives and control strategies. Economic analysis overlays the operational results with capital and operating cost assumptions to compute metrics such as NPV, payback, and levelized costs.

Scenario and sensitivity analyses are used to explore how results change with system sizing, varying cost assumptions, different tariff structures, and policy incentives. The thesis then synthesises technical and economic KPIs to answer the research questions and provide design and policy recommendations for energy communities considering co-located PV and storage.

(Note: the above excerpt is an abridged selection of the Introduction content to keep the README concise. The full Introduction and related documents are available in the repository.)

## How to reproduce (high-level)
1. Prepare the environment: install required Python/R packages for time-series analysis, optimisation (if present), and plotting.
2. Place/verify data in `SMEC/` and `Gen/` and follow the Data Architecture document for file format expectations.
3. Run the pre-processing scripts to align timestamps and generate net-load profiles.
4. Execute the BESS dispatch routine for each scenario and record outputs.
5. Run the techno-economic analysis module to compute KPIs and aggregate scenario results.
6. Recreate figures/tables for thesis chapters from the results folder (exported CSVs/plots).

## Notes & recommended next steps
- Convert the key Word documents (Introduction, Methodology, Model_Formulation) to plain text or markdown snippets for inclusion in analysis notebooks where needed.
- Add a requirements.txt or environment.yml to capture reproducible environment specifications.
- Consider adding example Jupyter notebooks that run a single scenario end-to-end (data load → dispatch → economic KPI) to make reproduction faster for reviewers.

---

If you want, I will now commit this README.md to the repository default branch (I have prepared this change). I can also extract a slightly longer 1–2 page excerpt from `Introduction .docx` or create an example notebook that runs a single scenario. Which would you like next?