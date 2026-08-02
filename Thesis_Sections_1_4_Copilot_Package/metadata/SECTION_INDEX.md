# Section Index

Source lines refer to the canonical LaTeX files.

## Chapter 1: Introduction

- Motivation (line 1) — `subsec:motivation`
- Background and Context (line 31) — `problem-definition-and-research-gap`
- Research Questions and Objectives (line 128)
- Scope of the Study (line 160)

## Chapter 2: Literature Review and Research Gap

- Theoretical Framework (line 1) — `subsec:theoretical-framework`
- State of the Art (line 504) — `subsec:state-of-the-art`
- Research Gap (line 783) — `subsec:research-gap`

## Chapter 3: Mathematical Formulation for Energy Communities

- Modelling Framework (line 7) — `sec:modelling_framework`
  - Overall Approach (line 10) — `subsec:overall_approach`
  - Regulatory and Settlement Boundary (line 32) — `subsec:regulatory_settlement_boundary`
- No-DER Baseline Scenario (line 41) — `sec:no_der_baseline_ch4`
  - Energy Balance (line 46) — `subsec:no_der_energy_balance`
  - Billing (line 69) — `subsec:no_der_billing`
- PV-Only Scenario (line 89) — `sec:pv_only_scenario_ch4`
  - Static Member-Level Allocation (line 94) — `subsec:static_member_allocation_pv_only`
  - Member-Level Energy Flows (line 116) — `subsec:member_level_energy_flows_pv_only`
  - Energy Conservation and Performance Indicators (line 141) — `subsec:energy_conservation_indicators_pv_only`
- PV–BESS Scenario (line 166) — `sec:pv_bess_scenario_ch4`
  - Allocation-Consistent Community Flow Definitions (line 180) — `subsec:allocation_consistent_flows`
  - Community Energy Balance and State of Charge (line 201) — `subsec:bess_community_energy_balance`
  - Battery Operating Bounds (line 223) — `subsec:battery_operating_bounds`
  - Charging, Discharging, Import, and Export (line 256) — `subsec:community_surplus_import_export_self_consumption`
  - Member-Level Allocation of Battery Flows (line 308) — `subsec:member_level_allocation_bess_flows`
- Battery Dispatch Logic (line 349) — `sec:battery_dispatch_logic`
- Community Energy Balance and Performance Accounting (line 354) — `sec:community_energy_balance_validation`
  - Complete Energy Balance (line 357) — `subsec:complete_energy_balance`
  - Performance Accounting (line 367) — `subsec:annual_accounting`
- Spanish Settlement and Billing Model (line 399) — `sec:spanish_settlement_billing_model`
  - PVPC Import Price and Billing Boundary (line 404) — `subsec:pvpc_import_billing_boundary`
  - PVPC Excedentaria Export Credit (line 411) — `subsec:pvpc_excedentaria_export_credit`
  - Member-Level Monthly Compensation Cap (line 416) — `subsec:member_level_monthly_compensation_cap`
  - Forfeited Compensation and Cap-Binding Events (line 453) — `subsec:forfeited_compensation_cap_binding`
  - Bill Savings and Battery-Specific Bill Savings (line 477) — `subsec:bill_savings_battery_specific`
- Economic and Allocation Formulation (line 496) — `sec:economic-framework`
  - Economic Evaluation Metrics (line 503) — `sec:ch5_economic_metrics`
  - Bill Savings Calculation (line 524) — `sec:ch5_bill_savings`
  - Capital and Operating Cost Model (line 586) — `sec:ch5_cost_model`
  - Net Present Value and Payback (line 624) — `sec:ch5_npv_payback`
  - Battery-Specific Value and Compensation-Cap Effects (line 668) — `sec:ch5_battery_value`
  - Static Allocation Coefficients (line 757) — `sec:ch5_static_allocation`
  - Member-Level Benefit Allocation (line 789) — `sec:ch5_member_benefit_allocation`
- Model Assumptions and Boundary Conditions (line 843) — `sec:model_assumptions_boundary_conditions`

## Chapter 4: Methodology

- Methodological Process (line 11) — `sec:overall_methodological_process`
- Case Study Definition: Seville Energy Community (line 75) — `sec:case_study_seville_energy_community`
- Community Composition and Load Profiles (line 86) — `sec:community_composition_load_profiles`
- PV Generation and Weather Data (line 114) — `sec:pv_generation_weather_data`
- Electricity Price and Tariff Data (line 153) — `sec:electricity_price_tariff_data`
- Technology, Dispatch, and Economic Parameters (line 166) — `sec:technology_economic_parameters`
- Battery Dispatch Implementation (line 220) — `sec:battery_dispatch_implementation`
  - Dispatch Pseudocode (line 223) — `subsec:dispatch_pseudocode`
  - Rationale and Limitations (line 262) — `subsec:dispatch_rationale_limitations`
- Data Processing Architecture (line 267) — `sec:data_processing_architecture`
- Data Quality, Assumptions, and Limitations (line 297) — `sec:data_quality_assumptions_limitations`
- Experimental Design and Sensitivity Analysis (line 316) — `sec:experimental`
  - Scenario Design (line 321) — `subsec:scenario_design`
  - PV Penetration Scenarios (line 324) — `subsec:pv_penetration_scenarios`
  - Battery CAPEX Scenarios (line 327) — `subsec:battery_capex_scenarios`
  - Electricity Price Sensitivity (line 330) — `subsec:electricity_price_sensitivity`
  - Community Size and Composition Sensitivity (line 333) — `subsec:community_size_composition_sensitivity`
  - Compensation Cap Assessment (line 336) — `subsec:compensation_cap_assessment`
- Validation and Robustness Assessment (line 339) — `subsec:validation_robustness_assessment`
  - Validation Checks (line 342) — `subsec:validation_checks`
