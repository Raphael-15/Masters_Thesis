# Introduction — Modelling Limitation Note

This short note clarifies a modelling assumption used across the repository and thesis materials.

Important modelling note (base case)

- Battery degradation is NOT modelled in the base‑case simulations. The repository's default operational runs and lifecycle economic results therefore omit capacity fade, cycle‑related losses, and scheduled battery replacements. This is an explicit modelling choice for the base case and should be treated as a limitation when interpreting long‑term performance, NPV, and LCOE outcomes.

Where to find the optional extension

- An optional throughput/cycle‑based degradation proxy and example formulas are provided in docs/Model_Formulation_equations.md. That file shows how to enable degradation modelling as an extension to the base case (throughput, equivalent full cycles, and replacement scheduling examples).

How to enable degradation in code

- In the model code, enable degradation by setting the configuration flag `degradation_enabled = True` (or the equivalent in the repo's config) and wiring the optional degradation routines from the equations file into the lifecycle and dispatch steps. When enabled, ensure replacement CAPEX and reduced available capacity (E_avail) are included in the economic module.

Usage

- Add this note to your thesis Methodology or Introduction chapter when discussing limitations and assumptions. For reproducibility, record whether `degradation_enabled` was set in the scenario manifest (bronze/metadata/manifest.json or the scenario entry in gold/).

