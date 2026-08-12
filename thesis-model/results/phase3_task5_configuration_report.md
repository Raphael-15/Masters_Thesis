# Phase 3 Task 5 — Community and Scenario Configuration

## Status

PASS

## Community configuration

Community ID:

`SEVILLE_CSC_001`

Members:

30

Community-composition case:

`baseline_empirical_30_members`

Annual community demand:

117656.065866 kWh

Allocation coefficient sum:

0.999999999999998

Consumption clusters:

- Low: 10
- Medium: 10
- High: 10

Community size is fixed and is not a sensitivity
dimension.

## PV scenario axis

PV capacities:

[10.0, 25.0, 50.0, 100.0]

Annual PVGIS yield:

1564.403180 kWh/kWp/year

PV penetration is calculated as:

annual scenario PV generation /
annual community electricity demand

It is therefore derived from the actual validated
PVGIS and load inputs rather than assigned manually.

## Battery scenario assumptions

PV-BESS battery capacity:

150 kWh

Battery capacity is fixed and is not treated as a
sensitivity dimension in this register.

BESS CAPEX levels:

[350.0, 450.0, 550.0] EUR/kWh

## Scenario families

No-DER scenarios:

1

PV-only scenarios:

4

PV-BESS scenarios:

12

Total scenarios:

17

## Reference cases

           scenario_id  pv_capacity_kwp  pv_penetration_percent  battery_capacity_kwh  battery_capex_eur_per_kwh
      NO_DER_REFERENCE              0.0                0.000000                   0.0                        0.0
         PV_ONLY_PV050             50.0               66.482045                   0.0                        0.0
PV_BESS_PV050_CAPEX450             50.0               66.482045                 150.0                      450.0

## Settlement

Price case:

`baseline_model_price_series`

Compensation-cap case:

`rd244_monthly_participant_cap`

PV-BESS terminal-SOC treatment:

`free_terminal_soc_reported`

## Important scope note

Only the baseline empirical 30-member community
composition is instantiated in the Phase 3 scenario
register.

Alternative community-composition sensitivity cases
are not invented here. They should only be added once
their member-selection/reweighting rule has been
formally defined.

## Outputs

Community configuration:

`data/gold/community_configuration_2013.csv`

Scenario parameters:

`data/gold/scenario_parameters_2013.csv`

Audit:

`results/phase3_task5_configuration_audit.csv`

## Integrity

Community configuration SHA-256:

`210f7e2b909623ff78167c628a8010048edb53d2411d2910fdc52af2eb047ed9`

Scenario parameter SHA-256:

`3c754b363e93bdb4798bc5ab5f8ab8a2a76840e6fedd518e5b1d22d1b1d96bb2`
