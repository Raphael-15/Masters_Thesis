# Methodology — Modelling Limitation Note

This short note states an explicit modelling assumption used in the repository and in the thesis methodology.

Important modelling note (base case)

- Battery degradation is NOT modelled in the base‑case simulations. The repository's default operational runs and lifecycle economic results therefore omit capacity fade, cycle‑related losses, and scheduled battery replacements. This modelling choice is documented here as a limitation and should be referenced in the Methodology chapter when describing assumptions and limitations.

Reference to optional extension

- Optional throughput/cycle‑based degradation formulas and an example pseudocode snippet are provided in docs/Model_Formulation_equations.md. If you later decide to include degradation in sensitivity runs, consult that file and record the scenario choice in the Bronze manifest (bronze/metadata/manifest.json) or the scenario entry in Gold.

Recording in manifests

- For reproducibility, record whether degradation was included in each scenario by adding an entry `degradation_included: false` (or true where applicable) in bronze/metadata/manifest.json or in the scenario record in gold/.

Usage

- Include this note (or an edited version) in the Methodology chapter under "Model assumptions and limitations".