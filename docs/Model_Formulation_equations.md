# Model Formulation — Chapter 4 (Finalised, Chapter‑4 specific)

This file records the final, Chapter‑4 model formulation used in the thesis. It describes the deterministic hourly, rule‑based simulation (baseline), notation specialised to the hourly backbone, and the economic assumptions used in Chapter 4.

Notation (hourly backbone)
- t : hourly timestep index (1..T)
- T = 8,760 : baseline annual horizon (hours)
- E_nom : nominal battery energy capacity (kWh)
- S_t : battery stored energy at the end of hour t (kWh)
- S_min, S_max : SoC bounds (kWh)
- P_ch,t ≥ 0 : battery charge power in hour t (kW)
- P_dis,t ≥ 0 : battery discharge power in hour t (kW)
- P_ch_max, P_dis_max : battery power limits (kW)
- η_ch ∈ (0,1] : charging efficiency (hourly energy accounting)
- η_dis ∈ (0,1] : discharging efficiency (hourly energy accounting)
- Load_t : community load in hour t (kWh or kW for hourly notation)
- PV_t : PV generation in hour t (kWh) — PVGIS hourly output scaled to site capacity
- Import_t ≥ 0, Export_t ≥ 0 : grid import/export in hour t (kWh)
- price_t : market or tariff price used for billing signals (€/MWh stored in Silver; convert to €/kWh when used)

Model type and baseline assumptions
- Baseline model type: deterministic hourly rule‑based simulation (no optimisation solver). The baseline dispatch is implemented as transparent heuristics applied hour‑by‑hour for T = 8,760 hours.
- PV: hourly PV output comes from PVGIS (hourly) and is scaled to the community/site capacity. Member‑level allocations are static (pre‑defined split of PV to members).
- Settlement & prices: baseline uses PVPC/retail settlement where applicable; OMIE price series are used as a dispatch/price signal (threshold based) rather than as the basis of optimisation. OMIE may be used to label hours for changed behaviour (e.g., export/charge inhibition when price<threshold).
- No grid charging: the baseline does not allow intentional charging from the grid (battery only charges from PV in baseline operation).
- Curtailment/export: surplus PV after self‑consumption and battery charging is exported to the grid under PVPC rules; curtailment is not modelled as a core variable in the baseline (no export limits in baseline).
- Degradation: battery degradation is NOT modelled in the Chapter‑4 baseline. Usable capacity and efficiencies are held constant over the horizon. This is an explicit modelling limitation.
- Economic assumptions: Chapter 4 uses a 4% real discount rate and a 15‑year project horizon for lifecycle calculations unless a scenario specifies otherwise.

1) State-of-charge (hourly energy notation)

Because the model runs hourly (Δt = 1 h), energy accounting is written in hourly terms without Δt factors:

S_t = S_{t-1} + η_ch · P_ch,t − (P_dis,t / η_dis)

SoC bounds:

S_min ≤ S_t ≤ S_max

Typically: S_max = E_nom and S_min = (1 − DoD) · E_nom.

2) Power limits and non‑simultaneous operation (baseline rule‑based)

0 ≤ P_ch,t ≤ P_ch_max

0 ≤ P_dis,t ≤ P_dis_max

The baseline enforces non‑simultaneous charging and discharging by rule: the dispatch heuristic never schedules P_ch,t > 0 and P_dis,t > 0 in the same hour (simple conditional logic). There is no MILP binary formulation in the Chapter‑4 baseline.

3) Hourly balance, exports, and surplus handling

Net community demand after PV and battery action (hour t):

Net_t = Load_t − PV_t − P_dis,t + P_ch,t

Imports/exports (baseline):

Import_t = max(Net_t, 0)  
Export_t = max(−Net_t, 0)

Surplus PV after meeting load and available charging is exported under PVPC; export limits and curtailment are not part of the baseline.

4) Rule‑based dispatch heuristic (detailed pseudocode)

The Chapter‑4 baseline uses a deterministic set of heuristic rules applied each hour in sequence. The pseudocode below captures the exact rule ordering used in Chapter 4 and can be used to reproduce the dispatch logic in a notebook or script.

```python
# Chapter 4: Deterministic hourly rule-based dispatch pseudocode
# Inputs per hour t: PV_t (kWh), Load_t (kWh), S_prev (kWh)
# Parameters: P_ch_max, P_dis_max (kW), S_min, S_max (kWh), eta_ch, eta_dis, omie_price_t, omie_threshold

def dispatch_hour(t, PV_t, Load_t, S_prev, params):
    # 1) Meet local load with PV first (self-consumption)
    pv_to_load = min(PV_t, Load_t)
    load_remaining = Load_t - pv_to_load
    pv_remaining = PV_t - pv_to_load

    # 2) Use remaining PV to charge battery (no grid charging)
    if pv_remaining > 0 and S_prev < params.S_max:
        # max charge energy this hour (kWh)
        max_charge_energy = min(pv_remaining, params.P_ch_max, (params.S_max - S_prev) / params.eta_ch)
        P_ch = max_charge_energy
    else:
        P_ch = 0.0

    # 3) If PV insufficient to meet load, discharge battery to supply remaining load
    if load_remaining > 0 and S_prev > params.S_min:
        # available discharge energy this hour (kWh)
        max_discharge_energy = min(load_remaining, params.P_dis_max, (S_prev - params.S_min) * params.eta_dis)
        P_dis = max_discharge_energy
        load_remaining -= P_dis
    else:
        P_dis = 0.0

    # 4) OMIE threshold adjustment (optional):
    # If omie signal indicates high price, prefer discharging (avoid export); if low price, avoid charging that leads to export.
    if params.use_omie:
        if params.omie_price_t > params.omie_threshold and P_dis == 0 and S_prev > params.S_min:
            # opportunistic discharge to reduce imports or capture high price
            extra_discharge = min(params.P_dis_max - P_dis, (S_prev - params.S_min) * params.eta_dis)
            P_dis += extra_discharge
        if params.omie_price_t < params.omie_threshold and P_ch > 0:
            # avoid charging to create an export under low-price hours
            # reduce charging if it would cause export after meeting load
            projected_export = pv_remaining - P_ch
            if projected_export > 0:
                reduce = min(P_ch, projected_export)
                P_ch -= reduce

    # 5) Recompute SoC after charge/discharge
    S_new = S_prev + params.eta_ch * P_ch - P_dis / params.eta_dis
    S_new = min(max(S_new, params.S_min), params.S_max)

    # 6) Net flow and final imports/exports
    net = Load_t - PV_t - P_dis + P_ch
    Import = max(net, 0.0)
    Export = max(-net, 0.0)

    # Return dispatch decisions and new state
    return {
        'P_ch': P_ch,
        'P_dis': P_dis,
        'S_new': S_new,
        'Import': Import,
        'Export': Export
    }
```

Notes on the pseudocode and implementation details:
- Units: in this pseudocode hourly energies (kWh) are used for clarity; if your implementation uses kW you may need to multiply/divide by the hour duration (Δt=1 h) consistently.
- This pseudocode intentionally forbids simultaneous P_ch>0 and P_dis>0 by construction (charge only from PV_remaining; discharge only to meet load_remaining or OMIE opportunistic discharge).
- The OMIE adjustment is a simple threshold example — Chapter 4 uses OMIE as a dispatch/label signal; adjust the threshold logic to match the exact rule you used in experiments.

5) Economic outputs (Chapter‑4 focus)

Primary economic outputs and KPIs in Chapter 4 include:
- Annual bill savings (€/year)
- Battery‑specific operational savings (€/year)
- NPV inputs and cashflow table (using 4% real discount rate and 15‑year horizon by default)
- Simple payback inputs
- Self‑consumption ratio (SCR) and self‑sufficiency ratio (SSR)
- Annual grid imports and exports (kWh)
- SoC trajectory and cap‑binding indicators (hours where power/energy limits bind)

LCOE/LCOS are not central to Chapter 4 baseline reporting and are only offered as a secondary/optional analysis if needed.

6) Implementation & reproducibility notes

- Horizon: baseline runs are annual at hourly resolution (T = 8,760). Use Silver hourly artifacts (silver/load_hourly.parquet, silver/pv_hourly.parquet, silver/prices_hourly.parquet) as model inputs.
- Units: energy are kWh in Silver; prices stored in €/MWh and converted to €/kWh for billing calculations where required.
- Timezone: timestamps are Europe/Madrid (timezone aware) in Silver/Gold.
- Manifest: record scenario choices (including explicit note that degradation was not modelled) in bronze/metadata/manifest.json or gold scenario entries for reproducibility.

7) Extensions (explicitly out of baseline)

The following are documented as possible extensions but are NOT part of the Chapter‑4 baseline unless explicitly enabled in a scenario:
- Grid charging from Import_t (disabled in baseline)
- Curtailment modelling due to export caps (not used in baseline)
- Degradation modelling (capacity fade) — baseline holds capacity constant
- MILP/LP optimisation‑based dispatch — baseline uses rule‑based heuristic

---

This file captures the Chapter‑4 specific formulation. Use it as the canonical reference for the baseline model and for reproducing the simulations reported in Chapter 4.
