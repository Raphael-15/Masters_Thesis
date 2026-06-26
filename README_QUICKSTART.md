# Quick-start: run the example end-to-end notebook

This quick-start file explains how to reproduce the minimal example in the repository (notebooks/example_end_to_end.ipynb).

1) Create a Python virtual environment and activate it

   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate

2) Install the required Python packages

   pip install --upgrade pip
   pip install -r requirements.txt

3) Open the example notebook in Jupyter Lab and run it

   jupyter lab notebooks/example_end_to_end.ipynb

Notes:
- The notebook uses synthetic data by default and runs out-of-the-box.
- A small sample dataset is included under data/sample/ for convenience. To use these files instead of the synthetic generator, open the notebook and replace the synthetic-data block with a CSV/Parquet load from data/sample/.
- The provided GitHub Actions workflow runs the notebook as a smoke test on push/pull-request. If the notebook changes, CI will execute it and fail if execution errors occur.