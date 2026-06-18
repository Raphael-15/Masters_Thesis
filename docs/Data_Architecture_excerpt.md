# Data Architecture — Excerpt (medium)

This excerpt summarises the repository's Case Study and Data Architecture document in a concise, assistant‑curated format. It focuses on the data layout, formats, preprocessing steps, metadata expectations, and recommended checks needed to reproduce the analysis.

## Data layout and primary sources

- SMEC/: Contains community load (demand) time-series. Expected content: one or more CSV/TSV files with timestamps and load measurements (per household or aggregated community). Typical columns: timestamp, load_kW (or W), node_id or meter_id (if multiple metered points), and optional metadata columns (building type, customer class).

- Gen/: Contains PV generation scenarios. The folder holds zipped bundles and time-series files for different PV system sizes/tilts/orientations. Typical contents: timestamp, pv_generation_kW (or W), scenario_id, and metadata files describing irradiance inputs, system size, and normalization factors.

- Documents: Case_Study_and_Data_Architecture_CITED.docx (explains case study boundaries and data provenance), Thesis_Table_of_Contents.docx, Introduction .docx, Literature Review.docx, Model_Formulation.docx.

## Time resolution & timestamps

- Use a consistent timestamp resolution across load and PV datasets. The modelling pipeline expects high-resolution data (e.g., 1-min, 5-min, 15-min or hourly). All files must share the same timezone or include timezone information.
- Timestamp format: ISO 8601 preferred (YYYY-MM-DDTHH:MM:SS±TZ). If timestamps are local (no TZ), document the timezone in a metadata file and convert consistently during preprocessing.

## Units, normalisation & metadata

- Units: Energies/power should be clearly labelled (W vs kW vs Wh). Convert all time-series to a common unit (e.g., kW) before modelling.
- Metadata files: store a small JSON or CSV manifest (data_manifest.json or data_manifest.csv) listing each time-series file, variable names, timezone, sampling interval, and provenance (source, date collected).

## Required preprocessing steps

1. Validate timestamps: check for duplicates, gaps, and overlapping ranges across files. Report and visualise gaps greater than one time-step.
2. Resample/align: choose model timestep and resample load and PV data to that resolution using an appropriate aggregation method (sum for energy, mean for power or interpolate for missing samples following domain best practices).
3. Missing data handling: small gaps can be interpolated; long gaps should be flagged and excluded or filled with synthetic data documented in the manifest. Consider forward/backward filling only when justifiable.
4. Normalise PV scenarios: ensure PV outputs correspond to the intended system size (e.g., 1 kW base profile scaled to scenario AC size) and include system losses where relevant.
5. Unit tests: after preprocessing, compute basic statistics (annual energy, peak demand, PV annual yield) and compare against expected magnitudes in the Case Study doc to detect misaligned units or scale factors.

## File format recommendations

- Time-series: CSV with header row; use ISO timestamps; name columns clearly: timestamp, value_kW, scenario_id, meter_id.
- Metadata/manifest: JSON or CSV listing file path, start/end timestamps, sampling_interval_minutes, timezone, variable_units, description.
- Zipped datasets: keep original raw files in a raw/ subfolder or retain compressed files but include a README describing contents.

## Data quality checks & versioning

- Quality checks: duplicate timestamps, non-monotonic time index, negative PV values (should be clipped to zero), outliers (e.g., > 3× typical peak), day/night consistency for PV.
- Versioning: treat processed datasets as derived artifacts. Keep raw inputs immutable and store processed outputs in a processed/ folder with a timestamped or git-tracked manifest.

## Reproducibility & scripts

- Add scripts/notebooks for: (a) parsing raw files into canonical CSVs, (b) resampling and alignment, (c) manifest creation and sanity checks, (d) a single-run example that executes the battery dispatch and computes KPIs.
- Recommended filenames: scripts/prepare_data.py, notebooks/01-preprocess.ipynb, notebooks/02-single-scenario-run.ipynb.
- Environment: capture Python package versions in requirements.txt or an environment.yml for reproducibility.

## Notes specific to this repo (recommendations)

- The Case_Study_and_Data_Architecture_CITED.docx contains provenance and citation details — create a short machine‑readable metadata file (case_study_metadata.json) summarising case boundaries, latitude/longitude, and dataset sources.
- If PV scenario bundles are provided as zip archives, include an index CSV inside Gen/ that lists which zip corresponds to which scenario parameters (tilt, azimuth, system size, irradiance input).

---

If you want, I will now commit this excerpt as docs/Data_Architecture_excerpt.md to the repository default branch and then proceed to extract the Literature Review or Model Formulation (same medium excerpts). Confirm and I will commit the file.