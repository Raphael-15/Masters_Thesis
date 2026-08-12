# Phase 3 Task 3 — Household Metadata and Allocation

## Status

PASS

## Community

- Community ID: SEVILLE_CSC_001
- Simulation year: 2013
- Members: 30
- Hours per member: 8760

## Annual demand

- Community annual demand: 117656.065866 kWh
- Minimum household annual demand: 87.566529 kWh
- Mean household annual demand: 3921.868862 kWh
- Maximum household annual demand: 9314.606997 kWh

## Static allocation

Allocation coefficients are proportional to validated
annual household demand:

beta_i = annual demand_i / total community annual demand

- Allocation coefficient sum: 1.000000000000000
- Minimum allocation coefficient: 0.000744258514
- Maximum allocation coefficient: 0.079168098377

## Load-data provenance

- Originally complete households: 23
- Short-gap reconstructed households: 4
- Long-gap reconstructed households: 3
- Total reconstructed hours: 11990
- Highest household reconstruction share: 95.8790%

## Consumption classification

The descriptive household classification is based on
empirical tertiles of the actual validated 2013 annual
demand distribution.

No household demand values are rescaled.

- Low: 10 households
- Medium: 10 households
- High: 10 households

The baseline simulation continues to use all 30
individual household profiles. The cluster labels are
metadata for descriptive analysis and later
community-composition sensitivity testing.

## Outputs

Household metadata:

`data/gold/metadata/household_metadata_2013.csv`

Cluster summary:

`results/phase3_task3_consumption_cluster_summary.csv`

Allocation audit:

`results/phase3_task3_allocation_audit.csv`

## Integrity

Task 2 input SHA-256:

`3583f22fdba8ff2cdd62dc94fd36f3abc98998ff6cb915efae178de244b26a22`

Household metadata SHA-256:

`4f98f1a9fb479b6b00221ec407477b57254647f625ba82451a4e973a338a47b1`
