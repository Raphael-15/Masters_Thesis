# Phase 4 Task 1 — Equation-to-Code Audit

**Status:** FAIL — implementation refactor required before final simulation  
**Audit date:** 2026-08-13  
**Repository:** `Raphael-15/Masters_Thesis`  
**Implementation audited:** `src/dispatch_simulator.py`  
**Implementation blob SHA:** `ececfc3bd7586e78d7b7e900d350acbeb4c81341`  
**Canonical formulation source:** `Thesis_Sections_1_4_Copilot_Package/canonical_tex/03_mathematical_formulation.tex`  

## 1. Purpose

Task 1 compares the current Python dispatch implementation with the canonical mathematical formulation before any Phase 4 simulation work is allowed to proceed. The audit is intentionally diagnostic: a FAIL result means the implementation must be corrected in subsequent Phase 4 tasks before the model can be considered synchronized with the thesis methodology.

The canonical TeX formulation is treated as authoritative where it differs from the older `docs/Model_Formulation_equations.md`, because the canonical formulation already contains the corrected member-first collective-self-consumption logic.

## 2. Main audit result

The current `BESSDispatcher` is not mathematically synchronized with the canonical formulation. The principal problem is that the implementation performs aggregate community PV/load netting before participant-level allocation, whereas the canonical methodology requires actual participant-hour loads to be combined with allocated PV first.

The required sequence is:

1. Read actual participant-hour demand `L_{i,t}`.
2. Allocate PV using `G_alloc_{i,t} = beta_i * G_t`.
3. Calculate direct PV use, participant surplus `U_{i,t}`, and participant residual demand `D_{i,t}`.
4. Aggregate `U_t = sum_i U_{i,t}` and `D_t = sum_i D_{i,t}`.
5. Charge only from `U_t`, subject to power and SOC headroom.
6. Apply the OMIE threshold before permitting any battery discharge.
7. Discharge only up to `D_t`, subject to power and available SOC.
8. Allocate charging according to participant surplus.
9. Allocate discharge according to participant residual demand.
10. Calculate participant imports and exports, then aggregate for validation.

The current code instead follows an aggregate PV/load netting sequence, discharges before applying the OMIE threshold, and then applies additional OMIE-dependent adjustments.

## 3. Equation and requirement audit

| Equation / requirement | Current implementation | Audit result | Required correction |
|---|---|---|---|
| SOC update `S_t = S_{t-1} + eta_ch P_ch,t - P_dis,t / eta_dis` | Formula is implemented | PARTIAL | Keep formula but remove silent SOC clipping |
| SOC bounds | `np.clip()` is applied after dispatch | FAIL | Enforce feasibility before dispatch and assert bounds afterwards |
| Charge/discharge power limits | Limits are included in `min()` expressions | PARTIAL | Retain and add explicit validation tests |
| No simultaneous charge/discharge | Current sequence can schedule both in the same hour | FAIL | Make simultaneous operation impossible by construction |
| Initial SOC `S_0 = 0.5 S_max` | Implemented through `S_init_pct = 0.5` | PASS | Retain |
| Actual participant-hour load `L_{i,t}` | Reconstructed as `Load_t * beta_i` | FAIL | Use actual Gold member-hour loads |
| PV allocation `G_alloc_{i,t} = beta_i G_t` | Implemented | PASS | Retain |
| Participant PV surplus `U_{i,t}` | Formula exists but uses synthetic member load | FAIL | Use actual participant load |
| Participant residual demand `D_{i,t}` | Formula exists but uses synthetic member load | FAIL | Use actual participant load |
| Community surplus `U_t = sum_i U_{i,t}` | Uses aggregate `max(G_t - L_t, 0)` logic | FAIL | Aggregate participant surplus after allocation |
| Community residual demand `D_t = sum_i D_{i,t}` | Uses aggregate `max(L_t - G_t, 0)` logic | FAIL | Aggregate participant residual demand after allocation |
| Charging from allocated PV surplus | Charging is based on aggregate PV surplus | FAIL | Use `U_t` from participant-level allocation |
| Grid charging prohibited | No explicit grid-charging branch | PASS | Retain and test explicitly |
| OMIE controls discharge only | OMIE also reduces charging | FAIL | Remove OMIE-based charge reduction |
| OMIE threshold applied before discharge | Normal discharge occurs before OMIE threshold check | FAIL — CRITICAL | Gate every discharge decision by OMIE threshold |
| Discharge otherwise equals zero | Low-price deficit hours can still discharge | FAIL — CRITICAL | Set discharge to zero whenever threshold condition fails |
| Discharge limited to residual demand | Additional opportunistic discharge is not demand-limited | FAIL — CRITICAL | Require `P_dis,t <= D_t` in every case |
| No battery-created export | Opportunistic discharge can create export | FAIL — CRITICAL | Remove discharge beyond participant residual demand |
| SOC after charging | Implemented | PASS | Retain |
| End-of-hour SOC | Implemented before clipping | PARTIAL | Remove silent clipping and validate directly |
| Charge allocation by participant surplus | Formula is implemented | PARTIAL | Correct automatically once actual `U_{i,t}` is used |
| Discharge allocation by residual demand | Formula is implemented | PARTIAL | Correct automatically once actual `D_{i,t}` is used |
| Participant import | Structurally present | PARTIAL | Recalculate from actual participant residual demand |
| Participant export | Structurally present | PARTIAL | Recalculate from actual participant surplus |
| Participant self-consumption | Not retained explicitly | FAIL | Add or derive member-level self-consumption |
| PV allocation closure | Not validated | FAIL | Test `sum_i G_alloc_{i,t} = G_t` |
| Charge allocation closure | Not validated | FAIL | Test `sum_i P_ch,alloc_{i,t} = P_ch,t` |
| Discharge allocation closure | Not validated | FAIL | Test `sum_i P_dis,alloc_{i,t} = P_dis,t` |
| Member/community import aggregation | Checked | PARTIAL | Retain with corrected participant flows |
| Member/community export aggregation | Not checked | FAIL | Add explicit export-aggregation test |
| Community energy balance | Aggregate balance is checked | PARTIAL | Revalidate after member-first refactor |
| PV-only balance | Implemented only at aggregate level | PARTIAL | Align `PVOnlyDispatcher` to actual member data |
| No-DER balance | Implemented only at aggregate level | PARTIAL | Align `NoDERDispatcher` to actual member data |
| Allocation coefficient validation | Bad sums are silently normalized | FAIL / WEAK | Validate and reject invalid coefficients instead of silently repairing them |
| 90% round-trip efficiency | Defaults use `0.949` each way | MINOR MISMATCH | Use `sqrt(0.90) = 0.948683...` consistently |
| Terminal SOC reporting | SOC series exists but `S_T - S_0` is not reported explicitly | MISSING | Add in terminal-SOC robustness task |

## 4. Critical implementation mismatches

### 4.1 Participant loads are not the actual Gold loads

The current allocation routine reconstructs participant demand as:

```python
member_loads = {m: Load_t * betas[m] for m in members}
```

This is incompatible with the Phase 3 Gold dataset, which already contains actual hourly demand for each of the 30 participants. Static allocation coefficients define the allocation of shared PV, not the shape of each participant's load.

### 4.2 Aggregate netting occurs too early

The current implementation calculates community self-consumption from aggregate load and PV before participant allocation. Under Spanish static collective self-consumption this can incorrectly offset one participant's import against another participant's export in the same hour.

The canonical formulation therefore requires participant PV allocation and participant surplus/deficit calculation before aggregation.

### 4.3 OMIE threshold does not correctly gate discharge

The current implementation first discharges whenever community load remains after PV, regardless of the OMIE price. The OMIE threshold is only evaluated afterwards.

This directly contradicts the intended rule:

`D_t > 0 AND OMIE_t >= threshold`

must be satisfied before any discharge occurs.

### 4.4 OMIE incorrectly influences charging

The current low-price branch can reduce charging after a valid PV-surplus charging decision. In the final methodology, OMIE is a discharge signal only. Charging must be determined by participant PV surplus, battery charge-power limit, and SOC headroom.

### 4.5 Opportunistic discharge can exceed residual demand

The additional high-price discharge branch is not bounded by residual demand. It can therefore discharge when no participant residual load exists and can create grid export from stored energy. This is outside the thesis model boundary and must be removed.

### 4.6 SOC clipping hides infeasible decisions

The current implementation applies:

```python
S_new = np.clip(S_new, S_min, S_max)
```

The final implementation must calculate feasible charge and discharge quantities so that SOC bounds are satisfied naturally. Validation should then assert the bounds. Silent clipping can mask a dispatch error.

## 5. Validation gaps identified in Task 1

The current validation routine checks:

- aggregate hourly energy balance;
- SOC bounds after clipping;
- non-negative battery/grid flows;
- simultaneous charging/discharging;
- allocation-coefficient sum; and
- member-import aggregation.

The following required checks are not yet complete:

- explicit charge-power limit;
- explicit discharge-power limit;
- member import/export exclusivity;
- PV allocation closure;
- charge allocation closure;
- discharge allocation closure;
- member-export aggregation;
- no grid charging;
- no battery-created export;
- zero-battery consistency;
- actual participant-level PV-only and No-DER flow closure;
- terminal SOC reporting.

These are assigned to later Phase 4 validation tasks after the dispatcher has been corrected.

## 6. PV-only and No-DER audit

`PVOnlyDispatcher` and `NoDERDispatcher` currently operate primarily with aggregate community arrays. They do not yet produce the same actual participant-level input/output structure required by the BESS case and by participant-level Spanish settlement.

This does not block the Task 2 BESS refactor, but both dispatchers must subsequently be aligned so that No-DER, PV-only, and PV-BESS use the same participant-hour demand data and can be compared directly.

## 7. Task 1 acceptance decision

**TASK 1: COMPLETE — AUDIT RESULT: FAIL**

The FAIL result is expected and means that the current implementation is not approved for final simulations. Phase 3 data remain valid and frozen; no Phase 3 input defect has been identified by this audit.

The implementation must now be corrected in Phase 4 Task 2. The Task 1 audit remains the baseline against which the refactored dispatcher will be reassessed.

## 8. Required next step

Proceed to **Phase 4 Task 2 — Refactor `BESSDispatcher`**.

Task 2 must correct the member-load structure, member-first allocation, PV-only charging logic, OMIE discharge gate, residual-demand discharge limit, SOC feasibility, and battery-flow allocation rules identified above. After the refactor, the relevant equation-to-code checks must be rerun before moving to Task 3.
