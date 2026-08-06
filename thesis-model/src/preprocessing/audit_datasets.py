"""
Phase 2 dataset audit and simulation-calendar decision.

- Audits raw datasets in these folders:
    thesis-model/data/raw/load/
    thesis-model/data/raw/pvgis/
    thesis-model/data/raw/omie/
    thesis-model/data/raw/pvpc_import/
    thesis-model/data/raw/pvpc_export/

- Produces:
    - results/dataset_audit.csv (machine-readable)
    - results/dataset_audit.md  (human-readable)
    - config/simulation_calendar.yaml (decision summary)
    - results/simulation_calendar_decision.md

Notes:
- Does NOT modify any data/raw files.
- Uses Europe/Madrid as canonical tz.
- Does not fill/interpolate/manufacture data.
"""

from pathlib import Path
import pandas as pd
import numpy as np
import yaml
import csv
import sys
import warnings
from datetime import timedelta

ROOT = Path(__file__).resolve().parents[2]  # thesis-model/
RAW_DIR = ROOT / "data" / "raw"
RESULTS_DIR = ROOT / "results"
CONFIG_DIR = ROOT / "config"

TZ = "Europe/Madrid"
PRICE_SERIES_KEYS = ["omie", "pvpc_import", "pvpc_export"]
LOAD_DIR = RAW_DIR / "load"
PVGIS_DIR = RAW_DIR / "pvgis"
OMIE_DIR = RAW_DIR / "omie"
PVPC_IMPORT_DIR = RAW_DIR / "pvpc_import"
PVPC_EXPORT_DIR = RAW_DIR / "pvpc_export"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _find_files(folder: Path, extensions=(".csv", ".parquet")):
    if not folder.exists():
        return []
    files = []
    for ext in extensions:
        files.extend(sorted(folder.glob(f"*{ext}")))
    return files


def _detect_timestamp_column(df, candidate_names=("timestamp", "time", "date", "datetime")):
    for c in df.columns:
        if c.lower() in candidate_names:
            return c
    for c in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[c]):
            return c
    return None


def _read_timestamps_from_csv(path: Path, ts_col_hint=None, chunksize=200_000):
    ts_list = []
    sample = pd.read_csv(path, nrows=200)
    if ts_col_hint and ts_col_hint in sample.columns:
        ts_col = ts_col_hint
    else:
        ts_col = _detect_timestamp_column(sample)
    if ts_col is None:
        raise ValueError(f"Could not find a timestamp column in {path.name}")
    parse_dates = [ts_col]
    for chunk in pd.read_csv(path, usecols=[ts_col], parse_dates=parse_dates, chunksize=chunksize):
        ts_list.append(chunk[ts_col].dropna())
    if not ts_list:
        return pd.DatetimeIndex([])
    ts = pd.concat(ts_list, ignore_index=True)
    return pd.to_datetime(ts)


def _tz_localize_to(timestamps: pd.DatetimeIndex, tz: str = TZ):
    if timestamps.tz is None:
        return timestamps.tz_localize(tz, ambiguous="infer", nonexistent="shift_forward")
    else:
        return timestamps.tz_convert(tz)


def _summarize_index(idx: pd.DatetimeIndex, tz: str = TZ):
    if len(idx) == 0:
        return dict(start=None, end=None, count=0, native_resolution=None)
    idx = _tz_localize_to(idx, tz)
    start = idx.min()
    end = idx.max()
    count = len(idx)
    diffs = idx.to_series().diff().dropna().dt.total_seconds()
    if len(diffs) == 0:
        res = None
    else:
        res_seconds = int(diffs.mode().iloc[0]) if not diffs.mode().empty else int(diffs.median())
        res = pd.to_timedelta(res_seconds, unit="s")
    return dict(start=start, end=end, count=count, native_resolution=res)


def _audit_timestamps_index(idx: pd.DatetimeIndex, year: int = None, tz: str = TZ):
    if len(idx) == 0:
        return dict(missing_count=None, duplicate_count=0, missing_sample=[])
    idx = _tz_localize_to(idx, tz)
    dup_count = idx.duplicated().sum()
    missing_count = None
    missing_sample = []
    if year is not None:
        expected = pd.date_range(f"{year}-01-01 00:00:00", f"{year}-12-31 23:00:00", freq="H", tz=tz)
        missing = expected.difference(idx)
        missing_count = len(missing)
        missing_sample = list(missing[:10])
    return dict(missing_count=int(missing_count) if missing_count is not None else None, duplicate_count=int(dup_count), missing_sample=missing_sample)


def audit_folder(folder: Path, role_hint: str = None):
    rows = []
    files = _find_files(folder)
    if not files:
        rows.append({
            "provider": folder.name,
            "source_file": None,
            "start": None,
            "end": None,
            "native_resolution": None,
            "observation_count": 0,
            "timezone": None,
            "unit": None,
            "missing_timestamps_2024": None,
            "missing_timestamps_2025": None,
            "duplicate_timestamps": 0,
            "final_role": role_hint or folder.name
        })
        return rows

    for f in files:
        try:
            ts_idx = _read_timestamps_from_csv(f)
        except Exception:
            df = pd.read_csv(f, parse_dates=True, infer_datetime_format=True)
            ts_col = _detect_timestamp_column(df)
            if ts_col is None:
                raise
            ts_idx = pd.to_datetime(df[ts_col])

        summary = _summarize_index(ts_idx, TZ)
        tz_str = str(summary["start"].tz) if summary["start"] is not None else None
        unit = None
        sample = pd.read_csv(f, nrows=20)
        for c in sample.columns:
            if "price" in c.lower() or "precio" in c.lower():
                if sample[c].abs().max() > 100:
                    unit = "eur_mwh"
                else:
                    unit = "eur_kwh"
            if c.lower().startswith("power") or c.lower().startswith("p_") or "pv" in c.lower():
                unit = "kw"
            if c.lower().startswith("load") or "kwh" in c.lower():
                unit = "kwh"

        ts_audit_2024 = _audit_timestamps_index(ts_idx, year=2024, tz=TZ)
        ts_audit_2025 = _audit_timestamps_index(ts_idx, year=2025, tz=TZ)

        rows.append({
            "provider": folder.name,
            "source_file": f.name,
            "start": summary["start"].isoformat() if summary["start"] is not None else None,
            "end": summary["end"].isoformat() if summary["end"] is not None else None,
            "native_resolution": str(summary["native_resolution"]) if summary["native_resolution"] is not None else None,
            "observation_count": int(summary["count"]),
            "timezone": tz_str,
            "unit": unit,
            "missing_timestamps_2024": ts_audit_2024["missing_count"],
            "missing_timestamps_2025": ts_audit_2025["missing_count"],
            "duplicate_timestamps": ts_audit_2024["duplicate_count"],
            "final_role": role_hint or folder.name
        })
    return rows


def run_audit():
    audit_rows = []
    audit_rows += audit_folder(LOAD_DIR, role_hint="load")
    audit_rows += audit_folder(PVGIS_DIR, role_hint="pv")
    audit_rows += audit_folder(OMIE_DIR, role_hint="price_omie")
    audit_rows += audit_folder(PVPC_IMPORT_DIR, role_hint="price_pvpc_import")
    audit_rows += audit_folder(PVPC_EXPORT_DIR, role_hint="price_pvpc_export")

    csv_path = RESULTS_DIR / "dataset_audit.csv"
    keys = ["provider", "source_file", "start", "end", "native_resolution", "observation_count",
            "timezone", "unit", "missing_timestamps_2024", "missing_timestamps_2025", "duplicate_timestamps", "final_role"]
    with open(csv_path, "w", newline="", encoding="utf8") as fh:
        writer = csv.DictWriter(fh, fieldnames=keys)
        writer.writeheader()
        for r in audit_rows:
            writer.writerow(r)

    md_path = RESULTS_DIR / "dataset_audit.md"
    with open(md_path, "w", encoding="utf8") as fh:
        fh.write("# Dataset audit\n\n")
        fh.write("|provider|source_file|start|end|obs|tz|unit|missing_2024|missing_2025|dups|role|\n")
        fh.write("|-|-|-|-|-|-|-|-|-|-|-|\n")
        for r in audit_rows:
            fh.write("|{provider}|{source_file}|{start}|{end}|{observation_count}|{timezone}|{unit}|{missing_timestamps_2024}|{missing_timestamps_2025}|{duplicate_timestamps}|{final_role}|\n".format(**{k: (v if v is not None else "") for k,v in r.items()}))

    provider_map = { (r["provider"], r["source_file"]): r for r in audit_rows if r["source_file"] is not None }
    price_rows = { r["final_role"]: r for r in audit_rows if r["final_role"] and r["final_role"].startswith("price_") }
    decision = {"simulation_year": None, "calendar_ready": False, "timezone": TZ, "reason": None, "price_audits": {}}
    for year in (2025, 2024):
        all_ok = True
        for key in ("price_omie", "price_pvpc_import", "price_pvpc_export"):
            r = price_rows.get(key)
            if r is None or r.get(f"missing_timestamps_{year}") is None:
                all_ok = False
                break
            if int(r.get(f"missing_timestamps_{year}") or 1) != 0 or int(r.get("duplicate_timestamps") or 0) != 0:
                all_ok = False
                break
            decision["price_audits"][key] = {
                "source_file": r["source_file"],
                "missing": int(r.get(f"missing_timestamps_{year}")),
                "duplicates": int(r.get("duplicate_timestamps"))
            }
        if all_ok:
            decision["simulation_year"] = year
            decision["calendar_ready"] = True
            decision["reason"] = f"All price series have complete joint hourly coverage for {year} in {TZ}"
            break
    if not decision["calendar_ready"]:
        decision["reason"] = "At least one price series is incomplete for both 2025 and 2024; do not declare calendar ready."

    cfg = {
        "simulation_year": decision["simulation_year"],
        "calendar_ready": decision["calendar_ready"],
        "timezone": decision["timezone"],
        "reason": decision["reason"],
        "price_audits": decision["price_audits"],
    }
    yaml_path = CONFIG_DIR / "simulation_calendar.yaml"
    with open(yaml_path, "w", encoding="utf8") as fh:
        yaml.safe_dump(cfg, fh, sort_keys=False)

    dec_md = RESULTS_DIR / "simulation_calendar_decision.md"
    with open(dec_md, "w", encoding="utf8") as fh:
        fh.write("# Simulation calendar decision\n\n")
        fh.write(f"- timezone: {decision['timezone']}\n")
        fh.write(f"- calendar_ready: {decision['calendar_ready']}\n")
        fh.write(f"- simulation_year: {decision['simulation_year']}\n")
        fh.write(f"- reason: {decision['reason']}\n\n")
        fh.write("## Price audits\n\n")
        for k, v in decision["price_audits"].items():
            fh.write(f"- {k}: {v}\n")

    print("Wrote:", csv_path, md_path, yaml_path, dec_md)
    return dict(csv=str(csv_path), md=str(md_path), yaml=str(yaml_path), decision_markdown=str(dec_md))


if __name__ == "__main__":
    run_audit()
