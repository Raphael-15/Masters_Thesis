# Model Formulation — Excerpt (Chapter 4, concise)

This short excerpt summarises the Chapter‑4 baseline model used in the thesis. It is a concise, non‑verbatim summary; the canonical, detailed formulation (equations and dispatch pseudocode) is in docs/Model_Formulation_equations.md.

Key points — Chapter 4 baseline

- Model type: deterministic hourly rule‑based simulation (no optimisation solver). Baseline horizon T = 8,760 (hours, annual).
- Time resolution: hourly backbone (all inputs are harmonised to hourly in Silver).
- PV & allocation: PVGIS hourly PV output scaled to site capacity; member‑level allocations are static.
- Dispatch: transparent heuristic applied each hour — PV meets local load first (self‑consumption), remaining PV charges battery up to P_ch_max and S_max, battery discharges to meet remaining load up to P_dis_max and S_min. No intentional grid charging in baseline. OMIE is used as a threshold/label signal to adjust heuristics where applicable.
- SoC (hourly energy notation):

  S_t = S_{t-1} + η_ch · P_ch,t − (P_dis,t / η_dis)

  with S_min ≤ S_t ≤ S_max (typically S_max = E_nom, S_min = (1−DoD)·E_nom).

- Non‑simultaneous operation: enforced by the heuristic (P_ch,t and P_dis,t are never both > 0 in the same hour).
- Surplus handling: surplus PV after self‑consumption and battery charging is exported under PVPC rules; curtailment and export caps are not part of the baseline.
- Degradation: battery degradation is NOT modelled in the Chapter‑4 baseline; usable capacity and efficiencies are constant over the simulated horizon.
- Economic assumptions & KPIs: default 4% real discount rate, 15‑year project horizon. Primary outputs: annual bill savings, battery operational savings, NPV inputs/cashflows, simple payback inputs, self‑consumption ratio (SCR), self‑sufficiency ratio (SSR), annual imports/exports, SoC trajectories, and cap‑binding indicators.

Implementation notes

- Use Silver hourly artifacts (silver/load_hourly.parquet, silver/pv_hourly.parquet, silver/prices_hourly.parquet) as inputs. Timestamps in Europe/Madrid and units in kWh (energy) / €/MWh (prices stored).
- For full details, pseudocode, and extension notes (optimisation, degradation, grid charging), see docs/Model_Formulation_equations.md.

Excerpt — see docs/Model_Formulation_equations.md for the full equations and dispatch pseudocode.
