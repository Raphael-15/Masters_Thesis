# Phase 3 Final Handover

## Status

PHASE 3 COMPLETE

Ready for Phase 4 model implementation: YES

Generated UTC:

2026-08-12T15:15:32.210567+00:00

## Simulation calendar

- Simulation year: 2013
- Model timezone: Europe/Madrid
- Hourly periods: 8760
- Time step: 1 hour

## Community

- Community ID: SEVILLE_CSC_001
- Members: 30
- Community size fixed: True
- Annual demand: 117656.065866 kWh
- Allocation method: annual-demand proportional
- Allocation coefficient sum: 0.999999999999998
- Low / Medium / High members: 10 / 10 / 10
- Demand rescaling performed: False

## Load provenance

- Raw timestamp interpretation: UTC/GMT
- Behavioural clock: Europe/London
- Model clock: Europe/Madrid
- Temporal alignment: timezone-aware calendar-position mapping
- Reconstructed load hours retained: 11990

## PV

- PV profile unit: kWh/kWp per hour
- Annual PVGIS yield: 1564.403180 kWh/kWp/year
- PV capacity levels: [10.0, 25.0, 50.0, 100.0]

## Prices

- Storage unit: EUR/MWh
- OMIE role: dispatch signal
- PVPC import role: grid-import billing
- PVPC export role: simplified export compensation
- Negative OMIE hours retained: 247

## Scenarios

- Total: 17
- No-DER: 1
- PV-only: 4
- PV-BESS: 12
- Fixed PV-BESS capacity: 150 kWh
- BESS CAPEX levels: [350.0, 450.0, 550.0] EUR/kWh
- Community-size sensitivity: False
- Battery-capacity sensitivity: False

Reference scenarios:

- NO_DER_REFERENCE
- PV_ONLY_PV050
- PV_BESS_PV050_CAPEX450

## Authoritative Phase 4 inputs

1. `data/gold/hourly_member_inputs_2013.csv`
2. `data/gold/community_configuration_2013.csv`
3. `data/gold/scenario_parameters_2013.csv`
4. `data/gold/metadata/household_metadata_2013.csv`
5. `data/gold/metadata/spanish_hourly_inputs_2013.csv`
6. `data/gold/metadata/london_to_madrid_calendar_map_2013.csv`

Machine-readable handover configuration:

`config/phase3_model_handover.yaml`

## Freeze boundary

Upstream frozen Bronze/Silver files:

20

Frozen Phase 3 handover artifacts:

17

All hashes verified:

True

Phase 3 manifest:

`results/phase3_handover_manifest.csv`

## Validation

- Gold rows: 262800
- Members: 30
- Unique model hours: 8760
- Missing model hours: 0
- Extra model hours: 0
- Duplicate member-hours: 0
- Core model-input nulls: 0
- Negative load values: 0
- Negative PV values: 0
- Reconstructed hours: 11990

Final automated test return code:

0

Final pytest output:

`results/phase3_task7_pytest_output.txt`

## Configuration precedence

The files `config/baseline.yaml` and
`config/sensitivity.yaml` are older template files and
are not authoritative for the completed Phase 3 data
layer.

For Phase 4, use:

`config/phase3_model_handover.yaml`

together with the Gold scenario register:

`data/gold/scenario_parameters_2013.csv`

## Final decision

The Bronze/Silver input boundary is frozen.

The Gold model-facing data layer is frozen.

The 2013 Europe/Madrid simulation calendar is locked.

The 30-member community configuration is locked.

The Phase 3 scenario register is locked.

Phase 3 is complete and the repository is ready to
proceed to model implementation and hourly simulation.
