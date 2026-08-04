"""
Bronze->Silver preprocessing utilities

Implements a minimal ingestion pipeline that:
- Reads raw CSVs from configured data/raw/* directories
- Harmonises timestamps and timezones to a canonical hourly index
- Converts units where needed (OMIE €/MWh -> €/kWh)
- Writes cleaned CSVs to data/processed/

This script is intentionally defensive: if a required raw file or directory is missing it raises a clear error with instructions.
"""

import os
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Optional


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}\nPlease place the raw file in the indicated path.")
    return pd.read_csv(path)


def harmonize_timestamp(df: pd.DataFrame, ts_col: str = 'timestamp', tz: str = 'Europe/Madrid') -> pd.DataFrame:
    df = df.copy()
    if ts_col not in df.columns:
        raise ValueError(f"Timestamp column '{ts_col}' not found in dataframe")
    df[ts_col] = pd.to_datetime(df[ts_col], utc=True, errors='coerce')
    if df[ts_col].isna().any():
        raise ValueError("Some timestamps could not be parsed to datetime; check format and timezone information in raw data.")
    # Convert to local timezone then drop tzinfo for naive timestamp in local tz
    df[ts_col] = df[ts_col].dt.tz_convert(tz)
    df[ts_col] = df[ts_col].dt.tz_localize(None)
    # Round to hour if necessary and set as index
    df[ts_col] = df[ts_col].dt.round('H')
    return df


def convert_omie_to_eurkwh(df: pd.DataFrame, price_col: str = 'price', unit: str = 'eur_mwh') -> pd.DataFrame:
    df = df.copy()
    if unit == 'eur_mwh' or df[price_col].max() > 100:  # heuristic: values >100 imply €/MWh
        df[price_col] = df[price_col] / 1000.0
    return df


def ingest_loads(raw_load_dir: str, out_file: str, tz: str = 'Europe/Madrid') -> str:
    raw_dir = Path(raw_load_dir)
    if not raw_dir.exists():
        raise FileNotFoundError(f"Raw load directory not found: {raw_dir}")

    all_files = sorted(raw_dir.glob('*.csv'))
    if not all_files:
        raise FileNotFoundError(f"No CSV files found in {raw_dir}. Place member load CSVs or a combined CSV in this directory.")

    # If there's a single combined file with member_id column, use it
    combined = None
    for f in all_files:
        df = pd.read_csv(f)
        if 'member_id' in df.columns and 'timestamp' in df.columns and 'load_kwh' in df.columns:
            combined = df
            break
    if combined is None:
        # assume per-member files named member_{id}.csv with columns timestamp,load_kwh
        parts = []
        for f in all_files:
            df = pd.read_csv(f)
            if 'timestamp' not in df.columns or 'load_kwh' not in df.columns:
                raise ValueError(f"Per-member CSV {f} must contain 'timestamp' and 'load_kwh' columns")
            member_id = f.stem
            df['member_id'] = member_id
            parts.append(df[['member_id','timestamp','load_kwh']])
        combined = pd.concat(parts, ignore_index=True)

    # Harmonize timestamps
    combined = harmonize_timestamp(combined, ts_col='timestamp', tz=tz)
    # Pivot to wide format optionally or save long format as Silver
    out_path = Path(out_file)
    combined.to_csv(out_path, index=False)
    return str(out_path)


def ingest_pvgis(raw_pvgis_file: str, out_file: str, tz: str = 'Europe/Madrid') -> str:
    path = Path(raw_pvgis_file)
    df = _read_csv(path)
    if 'timestamp' not in df.columns or not any(c.lower().startswith('power') or c.lower().startswith('p') for c in df.columns):
        # Accept common PVGIS outputs but be defensive
        # Caller should supply a file with timestamp and power columns
        raise ValueError(f"PVGIS file {path} must contain 'timestamp' and a power column (kW)")
    # try to locate power column
    power_cols = [c for c in df.columns if c.lower().startswith('power') or c.lower().startswith('p')]
    power_col = power_cols[0]
    df = df.rename(columns={power_col: 'power_kw'})
    df = harmonize_timestamp(df, ts_col='timestamp', tz=tz)
    df.to_csv(out_file, index=False)
    return out_file


def ingest_price_series(raw_file: str, out_file: str, tz: str = 'Europe/Madrid', unit_hint: Optional[str] = None) -> str:
    path = Path(raw_file)
    df = _read_csv(path)
    # Accept common column names
    if 'timestamp' not in df.columns:
        raise ValueError(f"Price CSV {path} must contain a 'timestamp' column")
    price_cols = [c for c in df.columns if 'price' in c.lower() or 'precio' in c.lower() or 'value' in c.lower()]
    if not price_cols:
        # fallback: take second column
        price_col = df.columns[1]
    else:
        price_col = price_cols[0]
    df = df.rename(columns={price_col: 'price'})
    df = harmonize_timestamp(df, ts_col='timestamp', tz=tz)
    # Convert OMIE €/MWh to €/kWh if unit hint or large values
    if unit_hint == 'eur_mwh' or df['price'].max() > 100:
        df['price'] = df['price'] / 1000.0
    df.to_csv(out_file, index=False)
    return out_file


if __name__ == '__main__':
    # Minimal CLI to run ingestion for expected baseline files as listed in baseline.yaml
    import yaml
    cfg_path = Path('thesis-model/config/baseline.yaml')
    if not cfg_path.exists():
        print("Config file not found: thesis-model/config/baseline.yaml. Create it or run from repo root.")
        raise SystemExit(1)
    cfg = yaml.safe_load(open(cfg_path))
    out_dir = Path('thesis-model/data/processed')
    out_dir.mkdir(parents=True, exist_ok=True)

    # Ingest loads
    try:
        loads_in = cfg['community']['members_file']
        # If members_file points to combined file, ingest_loads will find it
        out_load = out_dir / 'loads_silver.csv'
        ingest_loads(str(Path(loads_in).parent), str(out_load), tz=cfg['simulation']['timezone'])
        print(f"Wrote: {out_load}")
    except Exception as e:
        print(f"Skipping load ingestion: {e}")

    # Ingest PVGIS
    try:
        pvgis_in = cfg['pv']['pvgis_1kw_file']
        out_pv = out_dir / 'pvgis_1kw_silver.csv'
        ingest_pvgis(pvgis_in, str(out_pv), tz=cfg['simulation']['timezone'])
        print(f"Wrote: {out_pv}")
    except Exception as e:
        print(f"Skipping PVGIS ingestion: {e}")

    # Ingest prices
    try:
        omie_in = cfg['prices']['omie_file']
        out_omie = out_dir / 'omie_silver.csv'
        ingest_price_series(omie_in, str(out_omie), tz=cfg['simulation']['timezone'], unit_hint=None)
        print(f"Wrote: {out_omie}")
    except Exception as e:
        print(f"Skipping OMIE ingestion: {e}")

    try:
        pvpc_imp = cfg['prices']['pvpc_import_file']
        out_imp = out_dir / 'pvpc_import_silver.csv'
        ingest_price_series(pvpc_imp, str(out_imp), tz=cfg['simulation']['timezone'])
        print(f"Wrote: {out_imp}")
    except Exception as e:
        print(f"Skipping PVPC import ingestion: {e}")

    try:
        pvpc_exp = cfg['prices']['pvpc_export_file']
        out_exp = out_dir / 'pvpc_export_silver.csv'
        ingest_price_series(pvpc_exp, str(out_exp), tz=cfg['simulation']['timezone'])
        print(f"Wrote: {out_exp}")
    except Exception as e:
        print(f"Skipping PVPC export ingestion: {e}")
