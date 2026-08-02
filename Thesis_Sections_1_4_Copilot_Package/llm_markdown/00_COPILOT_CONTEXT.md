# GitHub Copilot Context — Thesis Chapters 1–4

## Project title

**Techno-Economic Assessment of Shared PV and Battery Energy Storage Systems under Spanish Residential Collective Self-Consumption**  
*A Simulation-Based Case Study in Seville, Spain*

## How to use this package

1. Treat files under `canonical_tex/` as the authoritative source.
2. Use files under `llm_markdown/` for easier LLM navigation. They embed the exact LaTeX source without rewriting it.
3. Use `plain_text_search/` only for fast keyword search; mathematical notation and formatting may be simplified there.
4. Use `references.bib` to resolve citation keys.
5. Read the chapters in numerical order.

## Research questions

- **RQ1:** Under what conditions does a shared BESS provide incremental value over a PV-only configuration?
- **RQ2:** How much value is attributable specifically to the battery, and how is it affected by the monthly compensation cap under RD 244/2019?
- **RQ3:** How sensitive are the results to PV penetration, battery CAPEX, electricity prices, community size, and participant composition?

## Core comparison

The model compares three configurations under identical inputs and settlement assumptions:

1. **No-DER:** no shared PV and no battery.
2. **PV-only:** shared PV without storage.
3. **PV–BESS:** shared PV with a centralised community battery.

Battery-specific value is isolated by comparing **PV–BESS directly with PV-only**.

## Regulatory and billing boundary

- Spanish residential collective self-consumption under **RD 244/2019**.
- Static participant-level allocation coefficients.
- PVPC import valuation.
- PVPC surplus export-credit valuation.
- Monthly participant-level compensation cap.
- No carry-over of unused compensation.
- Fixed power charges, meter rental, taxes, and non-energy invoice components are outside the modelled bill-savings boundary.

## Case-study baseline

- Location: Seville, Spain.
- Baseline community: 30 households.
- Sensitivity range: 10–50 households.
- Consumption composition: low, medium, and high-demand clusters.
- Battery: centralised 150 kWh LFP system.
- Battery charging: allocated PV surplus only; no grid charging.
- Simulation: deterministic hourly time series.
- Economic horizon: 15 years.

## Editing constraints for Copilot

- Do not invent numerical results that are not present in the source.
- Do not replace the Spanish participant-level settlement model with community-level netting.
- Do not introduce grid charging, demand charges, degradation, replacement scheduling, ancillary-service revenue, or dynamic allocation unless explicitly requested and consistently added across all chapters.
- Preserve equation labels, figure labels, table labels, citation keys, notation, and cross-references.
- Preserve the distinction between the mathematical formulation in Chapter 3 and the application/implementation methodology in Chapter 4.
