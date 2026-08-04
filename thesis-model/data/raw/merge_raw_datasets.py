#!/usr/bin/env python3
"""
merge_raw_datasets.py

Merge raw datasets in thesis-model/data/raw/omie, pvpc_export, pvpc_import into
one consolidated CSV per folder. This script is strict: it will stop on any
malformed file or if annual coverage for 2023, 2024, 2025 is incomplete.

Usage:
    python thesis-model/data/raw/merge_raw_datasets.py [--base-dir PATH]

By default base-dir is the repository root (one level above this script's
location). Output CSVs are written into the same raw directory.

Requirements:
    pip install pandas python-dateutil

Behavior highlights:
- Uses an explicit parser for OMIE MARGINALPDBC files (Year;Month;Day;MarketPeriod;MarginalPT;MarginalES).
  MarginalES is used as the Spanish dispatch price.
- Preserves delivery_date and market_period exactly as parsed.
- Does not assume every day has 24 periods; enforces expected period counts:
    - hourly files before 2025-10-01 => 24 periods
    - quarter-hourly files on/after 2025-10-01 => 96 periods
- Records metadata per source file: filename, file_size, sha256, mtime, status.
- Stops with a clear error if any file is malformed or if annual coverage is incomplete
  for years 2023, 2024, and 2025 (any missing delivery_date in those years).

"""
from __future__ import annotations

import argparse
from pathlib import Path
import hashlib
import csv
from datetime import date, timedelta, datetime
from dateutil import tz
import pandas as pd
from typing import Optional, Tuple, List
import sys

# Configuration
REQUIRED_YEARS = (2023, 2024, 2025)
QUARTER_HOURLY_START = date(2025, 10, 1)

# Folder names under data/raw
FOLDERS = ("omie", "pvpc_export", "pvpc_import")

# Helpers

def iso_utc_now():
    return datetime.utcnow().replace(tzinfo=tz.tzutc()).isoformat()


def sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


def expected_period_count_for_date(d: date) -> int:
    return 96 if d >= QUARTER_HOURLY_START else 24


# Strict OMIE parser (as provided)

def parse_marginalpdbc(path: str) -> pd.DataFrame:
    """Parse one OMIE MARGINALPDBC file without guessing its schema.

    Expects lines like:
      Year;Month;Day;MarketPeriod;MarginalPT;MarginalES;

    Returns a DataFrame with columns:
      delivery_date (date), market_period (int), marginal_pt_eur_mwh (float),
      marginal_es_eur_mwh (float), source_file (str)

    Raises ValueError on any validation failure.
    """

    records: list[dict] = []
    file_path = Path(path)

    text = file_path.read_text(encoding="latin-1")

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()

        if not line or line == "MARGINALPDBC;" or line == "*":
            continue

        fields = line.rstrip(";").split(";")

        if len(fields) != 6:
            raise ValueError(
                f"{file_path.name}, line {line_number}: "
                f"expected 6 fields, found {len(fields)}"
            )

        year, month, day, period, marginal_pt, marginal_es = fields

        records.append(
            {
                "delivery_date": pd.Timestamp(
                    year=int(year),
                    month=int(month),
                    day=int(day),
                ).date(),
                "market_period": int(period),
                "marginal_pt_eur_mwh": float(marginal_pt),
                "marginal_es_eur_mwh": float(marginal_es),
                "source_file": file_path.name,
            }
        )

    if not records:
        raise ValueError(f"No valid OMIE records found in {file_path}")

    df = pd.DataFrame(records)

    if df["market_period"].duplicated().any():
        raise ValueError(f"Duplicate market periods in {file_path.name}")

    return df


# PVPC parser: attempt common well-formed CSV patterns but be strict

def parse_pvpc_file(path: str) -> pd.DataFrame:
    """Parse PVPC export/import files.

    Strategy:
    - Try reading with separator ';', then ',', then '\t'.
    - Expect columns that allow extraction of a date column and an hour/period column
      and a price column. Typical column names: Fecha, Hora, Precio, 'PT', 'ES', 'PVPC'.
    - If none of the simple parses succeed, raise ValueError (do not fallback to
      generic numeric token extraction).

    Returns DataFrame with columns: delivery_date (date), market_period (int), price_eur_mwh (float), source_file
    """
    p = Path(path)

    tried_errors: List[str] = []
    for sep in (';', ',', '\t'):
        try:
            df = pd.read_csv(p, sep=sep, encoding='latin-1')
        except Exception as e:
            tried_errors.append(f"sep={sep}: {e}")
            df = None
        if df is None:
            continue
        # Normalize column names to lowercase
        cols = {c: c.lower() for c in df.columns}
        df.columns = [c.lower() for c in df.columns]

        # Try to find date column
        date_col = None
        for candidate in ('fecha', 'date', 'delivery_date'):
            if candidate in df.columns:
                date_col = candidate
                break
        # Find hour/period column
        hour_col = None
        for candidate in ('hora', 'hour', 'period', 'marketperiod', 'market_period'):
            if candidate in df.columns:
                hour_col = candidate
                break
        # Find price column
        price_col = None
        for candidate in ('precio', 'price', 'pvpc', 'es', 'marginal_es'):
            if candidate in df.columns:
                price_col = candidate
                break

        if price_col is None:
            # Try last column as price
            price_col = df.columns[-1]

        # Require at least date and price; hour/period is optional (we will infer if missing)
        if date_col is None:
            tried_errors.append(f"sep={sep}: no date column found")
            continue

        # Parse date column
        try:
            parsed_dates = pd.to_datetime(df[date_col], dayfirst=True, errors='coerce')
            if parsed_dates.isna().all():
                tried_errors.append(f"sep={sep}: date parse failed for column {date_col}")
                continue
            df['delivery_date'] = parsed_dates.dt.date
        except Exception as e:
            tried_errors.append(f"sep={sep}: date parse exception {e}")
            continue

        # Parse hour/period
        if hour_col is not None and hour_col in df.columns:
            try:
                df['market_period'] = pd.to_numeric(df[hour_col], errors='coerce').astype('Int64')
            except Exception:
                df['market_period'] = None
        else:
            # infer: if there are 24 or 96 rows per date and each date repeats, build market_period
            gp = df.groupby('delivery_date')
            counts = gp.size()
            # If counts are uniform and equal to 24 or 96 we can set market_period from 1..n
            if len(counts) > 0 and counts.nunique() == 1 and counts.iloc[0] in (24, 96):
                n = int(counts.iloc[0])
                df = df.sort_values('delivery_date')
                df['market_period'] = gp.cumcount() + 1
            else:
                # leave market_period as missing; we will error later if required
                df['market_period'] = None

        # Parse price column
        try:
            df['price_eur_mwh'] = pd.to_numeric(df[price_col].astype(str).str.replace(',','.'), errors='coerce')
        except Exception as e:
            tried_errors.append(f"sep={sep}: price parse exception {e}")
            continue

        # Build output
        out = df[['delivery_date', 'market_period', 'price_eur_mwh']].copy()
        out['source_file'] = p.name

        # Validate that at least some numeric prices exist
        if out['price_eur_mwh'].notna().sum() == 0:
            tried_errors.append(f"sep={sep}: no numeric prices parsed")
            continue

        return out

    raise ValueError(f"Failed to parse PVPC file {p.name}. Attempts: {tried_errors}")


# Merge workflow

def process_folder(base_raw: Path, folder: str) -> Tuple[pd.DataFrame, List[dict]]:
    """Process one folder and return merged DataFrame and metadata records.

    Metadata records contain: filename, file_size, sha256, mtime_iso, status, error
    """
    folder_path = base_raw / folder
    if not folder_path.exists():
        raise FileNotFoundError(f"Required folder not found: {folder_path}")

    metadata = []
    frames = []
    processed_dates = set()

    for p in sorted(folder_path.iterdir()):
        if p.is_dir() or p.name.startswith('.'):
            continue
        try:
            # read bytes for hashing
            content = p.read_bytes()
            file_sha = sha256_bytes(content)
            file_size = p.stat().st_size
            mtime = datetime.utcfromtimestamp(p.stat().st_mtime).replace(tzinfo=tz.tzutc()).isoformat()

            if folder == 'omie':
                # Use strict parser
                df = parse_marginalpdbc(str(p))
                # Use marginal_es as Spanish price
                out = df[['delivery_date', 'market_period', 'marginal_es_eur_mwh']].copy()
                out = out.rename(columns={'marginal_es_eur_mwh': 'price_eur_mwh'})
            elif folder in ('pvpc_export', 'pvpc_import'):
                out = parse_pvpc_file(str(p))
            else:
                raise RuntimeError(f"Unsupported folder: {folder}")

            # validate expected period counts per date in this file and collect delivery dates
            for d, group in out.groupby('delivery_date'):
                cnt = int(group.shape[0])
                expected = expected_period_count_for_date(d)
                if cnt != expected:
                    raise ValueError(f"File {p.name}: delivery_date {d} has {cnt} periods, expected {expected}")

            # success: attach metadata columns
            out['source_filename'] = p.name
            out['file_size'] = file_size
            out['sha256'] = file_sha
            out['file_mtime_utc'] = mtime

            frames.append(out)
            for d in out['delivery_date'].unique():
                processed_dates.add(d)

            metadata.append({
                'filename': p.name,
                'file_size': file_size,
                'sha256': file_sha,
                'mtime_utc': mtime,
                'status': 'ok',
                'error': ''
            })
        except Exception as e:
            metadata.append({
                'filename': p.name,
                'file_size': p.stat().st_size if p.exists() else None,
                'sha256': sha256_bytes(p.read_bytes()) if p.exists() else None,
                'mtime_utc': datetime.utcfromtimestamp(p.stat().st_mtime).replace(tzinfo=tz.tzutc()).isoformat() if p.exists() else None,
                'status': 'error',
                'error': str(e)
            })
            # Stop immediately on error as requested
            raise

    if not frames:
        raise ValueError(f"No files parsed successfully in folder {folder_path}")

    merged = pd.concat(frames, ignore_index=True)
    merged = merged.sort_values(['delivery_date', 'market_period']).reset_index(drop=True)
    return merged, metadata


def check_annual_coverage(dates_set: set) -> List[int]:
    missing_years = []
    for yr in REQUIRED_YEARS:
        start = date(yr, 1, 1)
        end = date(yr, 12, 31)
        expected = {d for d in (start + timedelta(days=i) for i in range((end-start).days + 1))}
        if not expected.issubset(dates_set):
            missing_years.append(yr)
    return missing_years


def write_metadata_csv(out_path: Path, records: List[dict]):
    with out_path.open('w', newline='', encoding='utf-8') as f:
        fieldnames = ['filename', 'file_size', 'sha256', 'mtime_utc', 'status', 'error']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            writer.writerow(r)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--base-dir', default=None, help='Path to repository root (overrides auto-detection)')
    args = ap.parse_args(argv)

    # Determine base dir: if provided use that; otherwise repo root = two parents up from this script
    script_path = Path(__file__).resolve()
    if args.base_dir:
        base = Path(args.base_dir).resolve()
    else:
        # script is in thesis-model/data/raw/merge_raw_datasets.py -> repo root is 3 levels up
        base = script_path.parents[3]
    raw_dir = base / 'thesis-model' / 'data' / 'raw'
    if not raw_dir.exists():
        raise FileNotFoundError(f"Raw data directory not found: {raw_dir}")

    overall_dates = set()
    all_metadata = {}

    try:
        for folder in FOLDERS:
            print(f"Processing folder: {folder}")
            merged, metadata = process_folder(raw_dir, folder)
            # save merged CSV
            out_csv = raw_dir / f"merged_{folder}.csv"
            merged.to_csv(out_csv, index=False, encoding='utf-8')
            print(f"Wrote merged CSV: {out_csv}")
            # write metadata
            meta_csv = raw_dir / f"metadata_{folder}.csv"
            write_metadata_csv(meta_csv, metadata)
            print(f"Wrote metadata CSV: {meta_csv}")

            all_metadata[folder] = metadata
            overall_dates.update(pd.to_datetime(merged['delivery_date']).dt.date.unique())

        # Check annual coverage across merged data (require that for each of REQUIRED_YEARS, all days present in overall_dates)
        missing_years = check_annual_coverage(overall_dates)
        if missing_years:
            raise RuntimeError(f"Annual coverage incomplete for years: {missing_years}. Aborting as requested.")

        print("All folders processed and merged successfully. Annual coverage complete for 2023-2025.")
        print("Merged files written into:")
        for folder in FOLDERS:
            print(" ", raw_dir / f"merged_{folder}.csv")

    except Exception as e:
        print("ERROR during processing:", e)
        print("No partial output will be assumed valid. Inspect metadata CSVs for details.")
        sys.exit(1)


if __name__ == '__main__':
    main()
