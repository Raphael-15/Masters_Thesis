# Model assumptions and limitations — Pasteable snippet

Important modelling assumptions and baseline limitations (Chapter 4)

- Baseline model: deterministic hourly rule‑based simulation (no optimisation solver); baseline annual horizon T = 8,760 hours.
- PV: PVGIS hourly output, scaled to site capacity; member allocation is static.
- Dispatch: heuristic each hour — PV → local load, PV → battery (up to P_ch_max and S_max), battery → load (up to P_dis_max and S_min). No intentional grid charging.
- OMIE: used as a threshold/label signal to adjust heuristic behaviour (not an optimisation objective).
- Exports/curtailment: surplus PV after battery charging is exported under PVPC; export caps/curtailment are not modelled in baseline.
- Degradation: battery degradation is NOT modelled in the baseline; usable capacity and efficiencies are constant.
- Economics: default 4% real discount rate, 15‑year horizon. Primary KPIs: annual bill savings, battery operational savings, NPV inputs/cashflows, simple payback, SCR, SSR, imports/exports, SoC trajectory, and cap‑binding indicators.

See docs/Model_Formulation_equations.md for the canonical Chapter‑4 formulation and pseudocode.
