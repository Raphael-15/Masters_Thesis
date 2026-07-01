# Model Formulation — Chapter 4 (Finalised, Chapter‑4 specific)

This file records the final, Chapter‑4 model formulation used in the thesis. It describes the deterministic hourly, rule‑based simulation (baseline), notation specialised to the hourly backbone, and the complete mathematical framework for PV-only and PV-BESS scenarios including member-level settlement, battery dispatch, and Spanish billing rules.

## Notation (hourly backbone)

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

## Model type and baseline assumptions

- Baseline model type: deterministic hourly rule‑based simulation (no optimisation solver). The baseline dispatch is implemented as transparent heuristics applied hour‑by‑hour for T = 8,760 hours per year.
- PV: hourly PV output comes from PVGIS (hourly) and is scaled to the community/site capacity. Member‑level allocations are static (pre‑defined split of PV to members).
- Settlement & prices: baseline uses PVPC/retail settlement where applicable; OMIE price series are used as a dispatch/price signal (threshold based) rather than as the basis of optimisation. OMIE is not used to value baseline imports or exports.
- No grid charging: the baseline does not allow intentional charging from the grid (battery only charges from PV in baseline operation).
- Curtailment/export: surplus PV after self‑consumption and battery charging is exported to the grid under PVPC rules; curtailment is not modelled as a core variable in the baseline (no export limits).
- Degradation: battery degradation is NOT modelled in the Chapter‑4 baseline. Usable capacity and efficiencies are held constant over the horizon. This is an explicit modelling limitation.
- Economic assumptions: Chapter 4 uses a 4% real discount rate and a 15‑year project horizon for lifecycle calculations unless a scenario specifies otherwise.

---

## 1) State-of-charge (hourly energy notation)

Because the model runs hourly (Δt = 1 h), energy accounting is written in hourly terms without Δt factors:

S_t = S_{t-1} + η_ch · P_ch,t − (P_dis,t / η_dis)

SoC bounds:

S_min ≤ S_t ≤ S_max

Typically: S_max = E_nom and S_min = (1 − DoD) · E_nom.

## 2) Power limits and non‑simultaneous operation (baseline rule‑based)

0 ≤ P_ch,t ≤ P_ch_max

0 ≤ P_dis,t ≤ P_dis_max

The baseline enforces non‑simultaneous charging and discharging by rule: the dispatch heuristic never schedules P_ch,t > 0 and P_dis,t > 0 in the same hour (simple conditional logic). There is no need for an explicit constraint; the rule-based design forbids it by construction.

## 3) Hourly balance, exports, and surplus handling

Net community demand after PV and battery action (hour t):

Net_t = Load_t − PV_t − P_dis,t + P_ch,t

Imports/exports (baseline):

Import_t = max(Net_t, 0)  
Export_t = max(−Net_t, 0)

Surplus PV after meeting load and available charging is exported under PVPC; export limits and curtailment are not part of the baseline.

---

## 4.3 Member-Level Energy Flows (PV-only scenario)

For the PV-only scenario, each member i receives a static allocation coefficient β_i such that ∑_i β_i = 1. At each hour, member-level self-consumption and import/export are calculated as:

SCPV_{i,t} = min(L_{i,t}, G^{alloc}_{i,t}), (4.12)

IPV_{i,t} = max(L_{i,t} − G^{alloc}_{i,t}, 0), (4.13)

EPV_{i,t} = max(G^{alloc}_{i,t} − L_{i,t}, 0), (4.14)

where G^{alloc}_{i,t} = β_i · G_t is the allocated PV generation for member i in hour t.

Community-level aggregates are:

SCPV_t = ∑_i SCPV_{i,t}, IPV_t = ∑_i IPV_{i,t}, EPV_t = ∑_i EPV_{i,t}. (4.15)

This individualized hourly calculation is preferred to aggregate community netting because aggregate netting can overestimate self-consumption. For example, one member may export surplus allocated PV while another imports grid energy in the same hour. Static allocation therefore requires member-level flow calculation before aggregation.

Energy conservation and performance indicators:

L_{i,t} + EPV_{i,t} = G^{alloc}_{i,t} + IPV_{i,t}, (4.16)

L_t + EPV_t = G_t + IPV_t, (4.17)

SCR^{PV} = ∑_t SCPV_t / ∑_t G_t, (4.18)

SSR^{PV} = ∑_t SCPV_t / ∑_t L_t. (4.19)

The self-consumption ratio (SCR) measures the share of PV generation consumed locally, while the self-sufficiency ratio (SSR) measures the share of community demand served by local PV generation.

---

## 4.4 PV-BESS Scenario

The PV-BESS scenario adds a centralized community battery to the PV-only configuration. The baseline battery is a 150.00 kWh LFP system with 90% round-trip efficiency and a 0.5C charge/discharge rate. The battery charges only from surplus PV and discharges to serve community demand during high-value hours. Grid charging is excluded in the baseline so that battery-specific value remains attributable to PV surplus shifting and simplified-compensation effects.

### 4.4.1 Community Energy Balance

G_t + I^{BESS}_t + P^{dis}_t = L_t + E^{BESS}_t + P^{ch}_t. (4.20)

Battery losses are not included as a separate term in the external community energy balance. They are captured internally through the state-of-charge equation. This avoids double-counting losses.

S_t = S_{t-1} + η_{ch} P^{ch}_t − P^{dis}_t / η_{dis}. (4.21)

In this convention, P^{ch}_t is the energy drawn from PV surplus into the battery charger terminal, and P^{dis}_t is the energy delivered from the battery to the community bus. The charging and discharging losses appear as differences between bus-side and stored energy in the SOC equation.

### 4.4.2 Battery Operating Bounds

S_{min} ≤ S_t ≤ S_{max}, (4.22)

0 ≤ P^{ch}_t ≤ P^{ch,max}, 0 ≤ P^{dis}_t ≤ P^{dis,max}, (4.23)

P^{ch}_t · P^{dis}_t = 0. (4.24)

For the baseline 150.00 kWh battery with a 0.5C rate, the maximum charge and discharge powers are 75.00 kW. With a 90% depth-of-discharge reserve, the minimum SOC is 15.00 kWh and the usable operating range is 15–150 kWh. The initial SOC is set to 50% of maximum capacity:

S_0 = 0.5 S_{max}. (4.25)

### 4.4.3 Community Surplus, Import, Export, and Self-Consumption

Surplus_t = max(G_t − L_t, 0), (4.26)

E^{BESS}_t = max(Surplus_t − P^{ch}_t, 0), (4.27)

I^{BESS}_t = max(L_t − G_t − P^{dis}_t, 0), (4.28)

SC^{BESS}_t = G_t − E^{BESS}_t. (4.29)

Equation (4.27) subtracts P^{ch}_t, not η_{ch} P^{ch}_t, because P^{ch}_t is already the PV surplus energy entering the battery charger. Multiplying by charging efficiency in the export equation would incorrectly leave part of the charged energy available for export.

### 4.4.4 Member-Level Allocation of PV-BESS Flows

Because Spanish collective self-consumption settlement is ultimately calculated at the individual consumer level, the PV-BESS scenario must also define member-level imports and exports. The baseline uses the same static allocation coefficients β_i for PV allocation and for battery-related benefits. This is consistent with the thesis scope, avoids dynamic allocation, and keeps the benefit allocation method transparent.

First, each member receives its allocated PV generation as in the PV-only case:

G^{alloc}_{i,t} = β_i G_t. (4.30)

Battery charging is allocated to members in proportion to their allocated PV surplus. Let the pre-battery surplus of member i be:

Surplus^{PV}_{i,t} = max(G^{alloc}_{i,t} − L_{i,t}, 0). (4.31)

If total allocated surplus is positive, the battery charge assigned to member i is:

P^{ch,alloc}_{i,t} = P^{ch}_t · Surplus^{PV}_{i,t} / ∑_j Surplus^{PV}_{j,t}. (4.32)

If total allocated surplus is zero, P^{ch,alloc}_{i,t} is set to zero for all members. This rule attributes battery charging to the members whose allocated PV surplus physically creates the storage opportunity.

Battery discharge is allocated in proportion to each member's residual demand after allocated PV generation. This ensures that stored energy is assigned only to members who still have unmet load in that hour, while the overall model remains rule-based and transparent.

Deficit^{PV}_{i,t} = max(L_{i,t} − G^{alloc}_{i,t}, 0), (4.33)

P^{dis,alloc}_{i,t} = P^{dis}_t · Deficit^{PV}_{i,t} / ∑_j Deficit^{PV}_{j,t}, if ∑_j Deficit^{PV}_{j,t} > 0, (4.34)

P^{dis,alloc}_{i,t} = 0, if ∑_j Deficit^{PV}_{j,t} = 0. (4.35)

The member-level PV-BESS import and export equations are then:

I^{BESS}_{i,t} = max(L_{i,t} − G^{alloc}_{i,t} − P^{dis,alloc}_{i,t}, 0), (4.36)

E^{BESS}_{i,t} = max(G^{alloc}_{i,t} − L_{i,t} − P^{ch,alloc}_{i,t}, 0), (4.37)

SC^{BESS}_{i,t} = L_{i,t} − I^{BESS}_{i,t}. (4.38)

This formulation keeps member-level settlement explicit and reproducible. It also allows the model to apply the simplified-compensation cap individually to each member in Section 4.7. As a validation check, member-level flows are aggregated and compared with the community-level flows at every hour.

---

## 4.5 Battery Dispatch Logic

The battery dispatch strategy is a rule-based heuristic. It is designed to be transparent, reproducible, and computationally efficient rather than mathematically optimal. The dispatch operates at community level using aggregate load, aggregate PV generation, SOC, and the OMIE day-ahead price signal.

### 4.5.1 Charging Logic

The battery charges only from PV surplus. At hour t, charging is calculated as:

P^{ch}_t = min(Surplus_t, P^{ch,max}, (S_{max} − S_{t-1}) / η_{ch}). (4.39)

This ensures that charging does not exceed available PV surplus, the battery power limit, or the remaining SOC headroom.

### 4.5.2 Discharging Logic

The battery discharges only when PV generation is insufficient to meet community load and the OMIE day-ahead price is above a discharge threshold. In the baseline, this threshold is set to the 75th percentile of the annual OMIE price distribution, targeting high-value hours such as evening peaks.

If G_t < L_t and p^W_t ≥ p^{threshold}, (4.40)

P^{dis}_t = min(L_t − G_t, P^{dis,max}, η_{dis}(S^{after\,ch}_t − S_{min})). (4.41)

Otherwise:

P^{dis}_t = 0. (4.42)

### 4.5.3 State-of-Charge Update

S^{after\,ch}_t = S_{t-1} + η_{ch} P^{ch}_t, (4.43)

S_t = S^{after\,ch}_t − P^{dis}_t / η_{dis}. (4.44)

The model enforces the SOC bounds in Equation (4.22). If a dispatch decision violates the bounds, the simulation flags an error rather than silently correcting the result.

### 4.5.4 Dispatch Pseudocode

```text
FOR each hour t = 1 to T:
  L_t = sum_i L_{i,t}
  Surplus_t = max(G_t - L_t, 0)
  
  IF Surplus_t > 0:
    P_ch_t = min(Surplus_t, P_ch_max, (S_max - S_{t-1}) / eta_ch)
  ELSE:
    P_ch_t = 0
  
  S_after_ch = S_{t-1} + eta_ch * P_ch_t
  
  IF (G_t < L_t) AND (p_W_t >= p_threshold):
    P_dis_t = min(L_t - G_t, P_dis_max, eta_dis * (S_after_ch - S_min))
  ELSE:
    P_dis_t = 0
  
  S_t = S_after_ch - P_dis_t / eta_dis
  E_t = max(max(G_t - L_t, 0) - P_ch_t, 0)
  I_t = max(L_t - G_t - P_dis_t, 0)
  
  Allocate PV, battery charge, battery discharge, import, and export to members
  Validate SOC bounds, non-negativity, and energy balance
END
```

### 4.5.5 Rationale and Limitations

The rule-based dispatch is chosen because it can be fully stated in the methodology chapter and audited hour by hour. It avoids hidden optimization assumptions and keeps the battery-specific value directly tied to PV surplus shifting, avoided imports, and the Spanish simplified-compensation cap. Its main limitation is that it does not anticipate future PV, load, or price patterns beyond the selected threshold rule; therefore, it should be interpreted as a transparent operational heuristic rather than as an upper-bound optimization result.

---

## 4.6 Community Energy Balance and Validation

### 4.6.1 Complete Energy Balance

G_t + I^{BESS}_t + P^{dis}_t = L_t + E^{BESS}_t + P^{ch}_t. (4.45)

The same formulation reduces to the PV-only balance when the battery is disabled, P^{ch}_t = P^{dis}_t = 0.

PV-only: G_t + I^{PV}_t = L_t + E^{PV}_t, (4.46)

No-DER: I^0_t = L_t. (4.47)

### 4.6.2 Annual Accounting

E^{PV,total} = ∑_t G_t, (4.48)

E^{import,total} = ∑_t I_t, (4.49)

E^{export,total} = ∑_t E_t, (4.50)

SCR = ∑_t SC_t / ∑_t G_t, (4.51)

SSR = ∑_t SC_t / ∑_t L_t, (4.52)

ΔSCR^{BESS} = SCR^{PV-BESS} − SCR^{PV-only}. (4.53)

### 4.6.3 Validation Checks

| Check | Condition |
| --- | --- |
| Hourly energy balance | \|G_t + I_t + P^{dis}_t − L_t − E_t − P^{ch}_t\| ≤ tolerance |
| SOC bounds | S_{min} ≤ S_t ≤ S_{max} |
| Non-negativity | L_{i,t}, G_t, I_{i,t}, E_{i,t}, P^{ch}_t, P^{dis}_t ≥ 0 |
| No simultaneous member import/export | I_{i,t} · E_{i,t} = 0 for each member and hour |
| No simultaneous battery charge/discharge | P^{ch}_t · P^{dis}_t = 0 |
| Allocation coefficients | ∑_i β_i = 1 and β_i ≥ 0 |
| Flow aggregation | ∑_i I_{i,t} = I_t and ∑_i E_{i,t} = E_t within tolerance |
| Monthly cap | R^{applied}_{i,m} ≤ C^{imp}_{i,m} for every member and month |
| Zero-battery consistency | PV-BESS equals PV-only when S_{max} = 0 |
| Battery charge allocation closure | ∑_i P^{ch,alloc}_{i,t} = P^{ch}_t within tolerance |
| Battery discharge allocation closure | ∑_i P^{dis,alloc}_{i,t} = P^{dis}_t within tolerance |

The no-simultaneous-import/export check is applied at member level. At aggregate community level, some members may import while others export in the same hour under static allocation; therefore, the aggregate community may show both positive import and positive export after summing member-level bills.

---

## 4.7 Spanish Settlement and Billing Model

This section converts hourly member-level energy flows into monthly and annual bills under the Spanish PVPC tariff and the RD 244/2019 simplified compensation mechanism. OMIE is used only as a battery dispatch signal; it is not used to value PVPC baseline imports or exports.

### 4.7.1 PVPC Import Price and Billing Boundary

The baseline billing boundary includes only energy-term cashflows. Grid imports are valued using the selected PVPC hourly energy-term import price, p^{imp}_t. Fixed power charges, meter rental, distribution charges not varying with self-consumed energy, VAT, and electricity taxes are excluded from the baseline. This isolates the marginal economic effect of PV generation and battery storage on the variable energy component of the bill.

This boundary must be stated clearly because full retail bills include fixed and tax components that are not avoided by self-consumption. If those components are added in an extension, they should be reported separately from the baseline energy-term results.

### 4.7.2 PVPC Excedentaria Export Credit

Surplus exports are valued using the PVPC excedentaria export-credit price, p^{exp}_t, published by REE/ESIOS. This export credit is generally lower than the import price because it does not include the full retail components avoided through self-consumption. Therefore, direct self-consumption and battery-enabled surplus shifting are typically more valuable than exporting surplus energy.

### 4.7.3 Member-Level Monthly Compensation Cap

For each household i and month m, the model calculates import cost, raw export compensation, applied export compensation, and net monthly energy bill as follows:

C^{imp}_{i,m} = ∑_{t∈m} I_{i,t} p^{imp}_t, (4.54)

R^{raw}_{i,m} = ∑_{t∈m} E_{i,t} p^{exp}_t, (4.55)

R^{applied}_{i,m} = min(R^{raw}_{i,m}, C^{imp}_{i,m}), (4.56)

B_{i,m} = C^{imp}_{i,m} − R^{applied}_{i,m}, (4.57)

B^{community}_m = ∑_i B_{i,m}, (4.58)

B^{annual} = ∑^{12}_{m=1} B^{community}_m. (4.59)

The cap is applied at member level because each participant has an individual billing relationship. A member with high export credit and low import cost cannot transfer unused compensation to another member. This prevents hidden cross-subsidization and makes the member-level benefit analysis consistent with the settlement boundary.

### 4.7.4 Forfeited Compensation and Cap-Binding Events

Lost_{i,m} = R^{raw}_{i,m} − R^{applied}_{i,m}, (4.60)

CapBind_{i,m} = \begin{cases} 1, & R^{raw}_{i,m} > C^{imp}_{i,m} \\ 0, & \text{otherwise} \end{cases}, (4.61)

Lost^{annual} = ∑_i ∑_m Lost_{i,m}. (4.62)

These quantities identify months and members for which the simplified compensation cap binds. They are important for RQ2 because one battery-specific value mechanism is the reduction of forfeited export compensation: surplus PV that would otherwise be exported and partly forfeited can instead be stored and used later to avoid imports.

### 4.7.5 Bill Savings and Battery-Specific Bill Savings

Savings^{scenario} = B^{No-DER} − B^{scenario}, (4.63)

SavingPct^{scenario} = Savings^{scenario} / B^{No-DER}, (4.64)

Saving^{BESS-specific} = B^{PV-only} − B^{PV-BESS}. (4.65)

Equation (4.65) is the core bill-based measure of battery-specific value. Economic metrics such as NPV and payback period are developed in Chapter 5 using these annual savings and the investment-cost assumptions.

---

## 4.8 Model Assumptions and Boundary Conditions

This section summarizes the assumptions and boundaries that define the validity of the results. These boundaries are intentionally explicit so that the conclusions are not over-generalized beyond the modelled conditions.

### 4.8.1 Baseline Case-Study Parameters

| Category / parameter | Baseline value | Comment / sensitivity |
| --- | --- | --- |
| Location | Seville, Spain | Fixed baseline; selected for high solar potential and Spanish CSC relevance |
| Community size | 30 households | Sensitivity: 10, 20, 30, 40, 50 households |
| Household composition | 40% low, 40% medium, 20% high consumption | Cluster shares varied in sensitivity |
| Temporal resolution | Hourly; T = 8760 in the baseline annual simulation | Longer aligned datasets retained for validation or sensitivity checks |
| Reference year | 2026 regulatory-economic framework | The selected complete data year is documented consistently |
| PV generation source | Seville PV profile generated using PVGIS-SARAH3 through the PVGIS seriescalc API | Long-term GHI/DNI and Open-Meteo datasets retained only for validation and diagnostic checks |
| PV orientation | South-facing, 30 degrees tilt | Fixed baseline |
| PV system losses | 14% | Fixed baseline unless sensitivity is added |
| Battery chemistry | LFP lithium-ion | Fixed baseline |
| Battery capacity | 150.00 kWh | Sensitivity may vary capacity or CAPEX |
| Charge/discharge power | 75.00 kW / 75.00 kW | 0.5C rate for 150.00 kWh battery |
| SOC reserve | 10% minimum SOC | S_{min} = 15.00 kWh |
| One-way efficiencies | η_{ch} = η_{dis} ≈ 0.949 | Equivalent to 90% round-trip efficiency |
| Battery charging source | PV surplus only | No grid charging in baseline |
| Battery degradation | Not modelled | Limitation; may overestimate long-term performance |
| Project horizon | 15 years for PV-BESS and PV-only comparison | Avoids battery replacement within baseline horizon |
| Allocation coefficients | Static proportional coefficients β_i | No dynamic allocation in baseline |
| Import valuation | PVPC energy-term import price | Fixed charges/taxes excluded from baseline |
| Export valuation | PVPC excedentaria export-credit price | Monthly cap applied per member |
| Grid constraints | Not modelled | Economic coordination study, not grid-feasibility study |
| Ancillary services | Excluded | Future extension |

### 4.8.2 Economic Assumptions

The baseline economic assumptions used for Chapter 5 are: real discount rate of 4% per year, 15-year project horizon, PV CAPEX in the range of 1,000–1,200 EUR/kWp, battery CAPEX varied as a key sensitivity parameter, and annual OPEX represented as a percentage of CAPEX. The exact numerical values used for each scenario are reported in Chapter 5 so that the methodology and results remain traceable.

The 15-year horizon is selected to align the economic evaluation with the assumed battery technical lifetime. This avoids the inconsistency of modelling a 25-year PV-BESS cashflow without including battery replacement. A 25-year horizon with replacement in year 15 is identified as a possible extension.

### 4.8.3 Exclusions and Limitations

1. **Battery degradation is not modelled.** The battery is represented with fixed usable capacity and constant efficiency over the project horizon. This simplifies the model but may overestimate long-term battery performance; results should therefore be interpreted as simplified estimates rather than degradation-aware forecasts.

2. **PV degradation is not modelled in the baseline.** Constant PV output simplifies the scenario comparison but may slightly overstate long-term generation in NPV calculations.

3. **Electrical network constraints are not modelled.** The thesis evaluates economic coordination and settlement effects, not voltage limits, thermal constraints, transformer capacity, or power quality.

4. **Dynamic allocation is excluded.** Static coefficients are used throughout the baseline because they are transparent and aligned with the defined research scope.

5. **Ancillary-service revenues are excluded.** The battery is used only for community self-consumption and import reduction, not frequency response, voltage support, or balancing markets.

6. **Demand response is excluded.** Household load profiles are fixed and do not change in response to prices or battery operation.

7. **Only energy-term billing is modelled in the baseline.** Fixed power charges, meter rental, and taxes are excluded unless explicitly added as an extension.

8. **The community is not modelled as an islanded microgrid.** It remains grid-connected at all times.

---

## Chapter Summary

This chapter has defined the corrected mathematical and computational framework used in the thesis simulation. The model compares No-DER, PV-only, and PV-BESS scenarios using identical inputs so that battery-specific value can be attributed to the incremental effect of storage. It uses individualized static allocation for PV-only and PV-BESS settlement, models a 30-household Seville community with a 150.00 kWh LFP battery, captures battery losses through the SOC equation rather than double-counting them in the external energy balance, and applies the RD 244/2019 simplified-compensation cap at member level.

The chapter also defines explicit PV-BESS member-level allocation equations for battery charging, battery discharge, imports, and exports. This makes the billing model reproducible and ensures that the monthly compensation cap is applied to properly defined member-level energy flows. Twelve explicit validation checks are documented to ensure energy balance, SOC bounds, allocation closure, and cap application.

Chapter 5 builds on this model to calculate economic metrics, battery-specific value decomposition, NPV, and payback period.

---

This file captures the complete Chapter‑4 formulation. Use it as the canonical reference for the baseline model and for reproducing the simulations reported in Chapter 4.
