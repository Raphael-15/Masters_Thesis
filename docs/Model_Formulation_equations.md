# Model Formulation — Equations and Example Snippet

This file provides the key model equations (LaTeX-style) used in the thesis and a short Python pseudocode snippet demonstrating SoC updates and constraint enforcement for a single timestep / short horizon.

Notation
- t : timestep index
- Δt : timestep duration (hours)
- E_nom : nominal battery energy capacity (kWh)
- SoC_t : state of charge at end of timestep t (kWh)
- SoC_min, SoC_max : SoC bounds (kWh)
- P_charge_t ≥ 0 : battery charging power at t (kW)
- P_discharge_t ≥ 0 : battery discharging power at t (kW)
- P_charge_max, P_discharge_max : power limits (kW)
- η_c ∈ (0,1] : charging efficiency
- η_d ∈ (0,1] : discharging efficiency
- Load_t : community load at t (kW)
- PV_t : PV generation at t (kW)
- Import_t ≥ 0 : grid import at t (kW)
- Export_t ≥ 0 : grid export at t (kW)
- price_t : electricity import price at t (currency/kWh)

---

## 1) State-of-charge (SoC) update

The SoC is updated each timestep as:

$$
\mathrm{SoC}_t = \mathrm{SoC}_{t-1} + (\eta_c \cdot P_{charge,t} - \frac{P_{discharge,t}}{\eta_d}) \cdot \Delta t
$$

SoC bounds:

$$
\mathrm{SoC}_{min} \le \mathrm{SoC}_t \le \mathrm{SoC}_{max}
$$

Typically: $\mathrm{SoC}_{max} = E_{nom}$ and $\mathrm{SoC}_{min} = (1 - \mathrm{DoD}) \cdot E_{nom}$.

## 2) Power limits and physical constraints

$$
0 \le P_{charge,t} \le P_{charge}^{max}
$$
$$
0 \le P_{discharge,t} \le P_{discharge}^{max}
$$

To avoid simultaneous charging and discharging (non-convex):

$$
P_{charge,t} \cdot P_{discharge,t} = 0
$$

A MILP-style practical formulation uses binaries $y_t \in \{0,1\}$:

$$
P_{charge,t} \le y_t \cdot P_{charge}^{max}
$$
$$
P_{discharge,t} \le (1 - y_t) \cdot P_{discharge}^{max}
$$

(Use convex relaxations for LP solves when tractable.)

## 3) Energy balance, import/export and curtailment

Net community power after battery action:

$$
\mathrm{Net}_t = \mathrm{Load}_t - \mathrm{PV}_t - P_{discharge,t} + P_{charge,t}
$$

Imports/exports:

$$
\mathrm{Import}_t = \max(\mathrm{Net}_t,\,0) \qquad
\mathrm{Export}_t = \max(-\mathrm{Net}_t,\,0)
$$

Curtailment occurs when PV cannot be used, stored or exported (if export is limited). If export limits apply, include a Curtailment term in the balance.

## 4) Objective functions (examples)

- Minimise exported energy (maximise self-consumption):

$$\min \sum_t Export_t \cdot \Delta t$$

- Minimise energy cost under time-varying tariffs:

$$\min \sum_t Import_t \cdot price_t \cdot \Delta t$$

- Multi-objective weighted sum (example):

$$\min \; w_{cost} \sum_t Import_t price_t \Delta t + w_{export} \sum_t Export_t \Delta t + w_{peak} PeakTerm$$

## 5) Economic evaluation (lifetimes & discounting)

NPV (simplified):

$$\mathrm{NPV} = -\mathrm{CAPEX}_{total} + \sum_{y=0}^{N-1} \frac{Cashflow_y}{(1 + r)^y}$$

LCOE example:

$$\mathrm{LCOE} = \frac{\sum_{y=0}^{N-1} DiscountedCosts_y}{\sum_{y=0}^{N-1} DiscountedDeliveredEnergy_y}$$

where $DiscountedCosts_y = Costs_y/(1+r)^y$.

## 6) Degradation (throughput-based proxy)

Throughput in timestep t (kWh):

$$\mathrm{throughput}_t = (P_{charge,t} + P_{discharge,t}) \cdot \Delta t$$

Cumulative throughput $T$:

$$Cumulative\_throughput_T = \sum_{\tau=1}^{T} throughput_{\tau}$$

Linear throughput-based capacity fade:

$$E_{avail,T} = E_{nom} - k_{deg} \cdot Cumulative\_throughput_T$$

Or use an equivalent-full-cycle mapping $f(cycles)$: $E_{avail,T} = E_{nom} (1 - f(cycles_T))$.

Replacement is scheduled when $E_{avail,t}$ falls below a threshold; replacement CAPEX is included in the lifecycle cashflows.

## 7) Aggregated KPIs (examples)

- Self-consumption rate:

$$SC = \frac{\sum_t PV_{used,locally,t} \cdot \Delta t}{\sum_t PV_t \cdot \Delta t}$$

- Self-sufficiency:

$$SS = \frac{\sum_t (PV_{used,locally,t} + BatteryDischargeToLoad_t) \cdot \Delta t}{\sum_t Load_t \cdot \Delta t}$$

- Curtailment fraction, annual energy shifted, peak reduction: computed from timestep outputs.

## 8) Placeholders for figures/tables
- Figure: SoC and power flow diagram (insert figure from Model_Formulation.docx)
- Table: Default parameter list (E_nom, P_max, η_c, η_d, CAPEX per kW/kWh, OPEX, discount rate, lifetime)

---

## Example Python pseudocode (short horizon / single-step logic)

```python
# Pseudocode: single-step SoC update and constraint checks
# (values are illustrative; use arrays for multi-step horizon)

delta_t = 1.0  # hours
E_nom = 100.0  # kWh
SoC_min = 0.1 * E_nom
SoC_max = E_nom
eta_c = 0.95
eta_d = 0.95
P_charge_max = 50.0  # kW
P_discharge_max = 50.0  # kW

# sample timestep inputs
SoC_prev = 50.0  # kWh
Load = 30.0      # kW
PV = 20.0        # kW

# decision (example from optimisation or heuristic)
P_charge = 10.0    # kW (>=0)
P_discharge = 0.0  # kW (>=0)

# enforce power limits
P_charge = max(0.0, min(P_charge, P_charge_max))
P_discharge = max(0.0, min(P_discharge, P_discharge_max))

# optionally prevent simultaneous charge/discharge
if P_charge > 0 and P_discharge > 0:
    # simple tie-breaker: prefer discharge
    P_charge = 0.0

# SoC update
SoC_new = SoC_prev + (eta_c * P_charge - P_discharge / eta_d) * delta_t

# enforce SoC bounds (if violated, scale back charge/discharge)
if SoC_new > SoC_max:
    # reduce charging to fit
    excess = SoC_new - SoC_max
    # convert excess kWh back to kW over delta_t
    reduce_kw = excess / delta_t / eta_c
    P_charge = max(0.0, P_charge - reduce_kw)
    SoC_new = SoC_prev + (eta_c * P_charge - P_discharge / eta_d) * delta_t

if SoC_new < SoC_min:
    shortfall = SoC_min - SoC_new
    reduce_kw = shortfall / delta_t * eta_d
    P_discharge = max(0.0, P_discharge - reduce_kw)
    SoC_new = SoC_prev + (eta_c * P_charge - P_discharge / eta_d) * delta_t

# compute net flow and imports/exports
net = Load - PV - P_discharge + P_charge
Import = max(net, 0.0)
Export = max(-net, 0.0)

# throughput for degradation accounting
throughput = (P_charge + P_discharge) * delta_t

print(f"SoC: {SoC_new} kWh, Import: {Import} kW, Export: {Export} kW, throughput: {throughput} kWh")
```

Notes:
- For horizon optimisation use vectorised LP/MILP with decision variables for each t and SoC linkage constraints across timesteps.
- For receding-horizon control or forecast-aware operation, embed forecast scenarios or MPC with periodic re-optimisation.

---

I will now commit this file as docs/Model_Formulation_equations.md. If you confirm, I will proceed.