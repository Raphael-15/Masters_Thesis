# Reproducibility checklist

This short checklist lists small, high-impact repository items that improve reproducibility and make it easier for reviewers to run the analysis end-to-end.

1. requirements.txt or environment.yml
   - Provide a pinned environment (requirements.txt or environment.yml) listing packages and minimum versions used (pandas, numpy, matplotlib, pyarrow, jupyter, etc.).
   - Example: requirements.txt or environment.yml at repo root.

2. Small example dataset / reduced sample
   - Include a small sample of Silver artifacts (e.g., sample_load_hourly.parquet, sample_pv_hourly.parquet, sample_prices_hourly.parquet) covering one week or one typical day. Keep file sizes small (<1 MB) so the repo remains lightweight.
   - Put sample data under data/sample/ with a README describing how the sample maps to the full pipeline.

3. Single-run example notebook (already added)
   - A single notebook that runs the full pipeline (preprocess → dispatch → KPIs → plots). Path: notebooks/example_end_to_end.ipynb.
   - Ensure the notebook reads sample data from data/sample/ by default and shows where to swap in the full Silver artifacts.

4. README with quick-start run instructions
   - Short instructions: create environment (pip install -r requirements.txt or conda env create -f environment.yml), open Jupyter, run notebooks/example_end_to_end.ipynb, and pointer to Silver/Gold artifacts location.

5. Manifest / scenario metadata
   - A machine-readable manifest (JSON) describing dataset sources, timezone, units, and scenario config used for published runs. Path suggestion: bronze/metadata/manifest.json or docs/manifest_example.json.

6. Random seeds and deterministic settings
   - If stochastic sampling or clustering is used (e.g., to create synthetic members), set and record random seeds in notebooks and scripts to enable exact reproduction.

7. CI smoke test (optional but recommended)
   - Add a lightweight GitHub Actions workflow that runs the example notebook or a small test script on push to ensure the example runs in a fresh environment.

Placing these items in the repo will make it straightforward for reviewers to reproduce results and to inspect the inputs used for each scenario.
