# Model Formulation — Excerpt (medium)

This curated excerpt summarises the model formulation used to simulate co-located PV and battery energy storage systems and to compute operational and economic KPIs. It focuses on the core state dynamics, constraints, control choices, and the structure of the economic layer without reproducing the full original document verbatim.

## Core modelling elements

- Time-stepped representation: The model runs on a defined timestep Δt (e.g., 1 min / 5 min / 15 min / 1 h). Inputs per timestep are load (demand) and PV generation; outputs include battery charge/discharge, state-of-charge (SoC), grid import/export and curtailed generation.

- Battery state dynamics: The battery is modelled with energy capacity E_nom (kWh), power rating P_max (kW), and round-trip efficiency factors. The SoC is tracked across time-steps with charging and discharging flows bounded by power limits and SoC bounds.

- Operational constraints: Charging and discharging power are constrained by the battery's power limits and instantaneous SoC (to avoid overcharge/overdischarge). The model enforces non-simultaneous charge/discharge through a practical LP/MILP implementation choice; this is documented in the equations file.

- Control strategies: The formulation supports different operational objectives: maximise self-consumption (minimise exported energy), minimise imported cost under time-varying tariffs (arbitrage), minimise peak import (peak shaving), or multi-objective blends (weighted sum). Control can be rule-based (heuristics) or optimisation-based (linear programming for convex approximations). The thesis uses an optimisation-based approach where computationally feasible and fallback heuristics for large-scale sweeps if needed.

## Economic and lifecycle modelling

- Cost elements: CAPEX and OPEX for PV and battery systems and replacement costs for repairs/upgrades are included in the economic layer. Economic evaluation uses a discount rate and lifetime to compute NPV, payback, and LCOE/LCOS.

- Battery degradation (NOT modelled in base case): The base-case model and default scenario runs DO NOT model battery degradation or capacity fade. Degradation equations are available in the equations file as an optional extension but are disabled by default. This is a stated limitation — lifecycle performance and NPV may be overestimated as a result.

## Outputs and KPIs

- Per-timestep outputs: battery P_charge, P_discharge, SoC, grid import/export, curtailed PV.
- Aggregated KPIs: annual/period self-consumption rate, self-sufficiency, energy shifted by storage, peak reduction, curtailed energy, NPV, payback, LCOE/LCOS, and sensitivity maps across scenario variables.

## Implementation notes

- Numerical approach: where the optimisation is convex (linear constraints and linear objective), a linear programming solver is used for robustness and speed. For non-convex features (discrete battery replacement decisions or non-simultaneous charging/discharging with binaries) the model uses approximations or deterministic scheduling with post-hoc checks.

- Reproducibility: key model inputs and assumptions (time-step, units, efficiencies, battery cost trajectory, discount rate, tariff assumptions) are recorded in machine-readable manifests so scenario sweeps are reproducible and comparable.

---

This curated, non-verbatim excerpt keeps the conceptual clarity needed to implement or review the model. The repo's default behaviour is to NOT model battery degradation; enabling degradation requires changing a clear flag and enabling the optional extension formulas in the equations file.
