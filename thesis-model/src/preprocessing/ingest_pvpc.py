#!/usr/bin/env python3
"""
PVPC ingestion utility (corrected and safe for tests)

No import-time filesystem side-effects. Audit and processed paths are derived
from the provided output_file inside process_dataset. The module implements
robust parsing, validation and audit manifest merging as required.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from collections import Counter
from datetime import timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

# Constants
ENCODINGS_TO_TRY = ["utf-8-sig", "utf-8", "latin-1", "cp1252"]
SEPARATOR = ";"
LOCAL_TZ = "Europe/Madrid"
IMPORT_ID = 1001
EXPORT_ID = 1739


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def detect_encoding_and_read(path: Path) -> Tuple[pd.DataFrame, str, str]:
    last_exc = None
    for enc in ENCODINGS_TO_TRY:
        try:
            df = pd.read_csv(path, sep=SEPARATOR, encoding=enc, engine="python", dtype=str)
            return df, enc, SEPARATOR
        except Exception as e:
            last_exc = e
            continue
    raise ValueError(f"Unable to read file {path} with any of {ENCODINGS_TO_TRY}. Last error: {last_exc}")


def validate_required_columns(df: pd.DataFrame, path: Path):
    missing = [c for c in ["value", "datetime", "id"] if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required column(s) {missing} in {path}")


def parse_and_enrich(df: pd.DataFrame, path: Path) -> pd.DataFrame:
    df = df.copy()
    df["datetime_original"] = df.get("datetime", pd.Series(dtype=str)).astype(str)
    try:
        ts = pd.to_datetime(df["datetime"], utc=True, errors="raise")
    except Exception as e:
        raise ValueError(f"Invalid datetime values in {path}: {e}")
    df["timestamp_utc"] = ts
    df["timestamp_local"] = ts.dt.tz_convert(LOCAL_TZ)
    return df


def mark_duplicates_global(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    serialised = df.fillna("").astype(str).agg("||".join, axis=1)
    row_hash = serialised.map(lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest())
    df["__row_hash"] = row_hash
    dup_row_hashes = row_hash[row_hash.duplicated(keep=False)]
    df["exact_duplicate_row"] = df["__row_hash"].isin(set(dup_row_hashes))
    df["duplicate_utc_timestamp"] = df["timestamp_utc"].duplicated(keep=False)
    local_wall_clock = df["timestamp_local"].dt.tz_localize(None)
    df["duplicate_local_timestamp"] = local_wall_clock.duplicated(keep=False)
    df.drop(columns=["__row_hash"], inplace=True)
    return df


def convert_price_column(df: pd.DataFrame, unit_hint: str, path: Path) -> pd.DataFrame:
    df = df.copy()
    try:
        df["price_original"] = pd.to_numeric(df["value"], errors="raise")
    except Exception as e:
        raise ValueError(f"Non-numeric price values in {path}: {e}")
    if unit_hint not in ("EUR/MWh", "EUR/kWh"):
        raise ValueError(f"unit_hint must be 'EUR/MWh' or 'EUR/kWh' - got: {unit_hint}")
    df["original_unit"] = unit_hint
    if unit_hint == "EUR/MWh":
        df["price_eur_kwh"] = df["price_original"] / 1000.0
        df["conversion_applied"] = True
    else:
        df["price_eur_kwh"] = df["price_original"]
        df["conversion_applied"] = False
    return df


def detect_indicator_and_validate(df: pd.DataFrame, dataset_type: str, path: Path) -> Tuple[int, List[str], List[str], List[str]]:
    ids = pd.to_numeric(df.get("id", pd.Series(dtype=str)), errors="coerce")
    if ids.isna().any():
        raise ValueError(f"Non-numeric id values in {path}")
    unique_ids = sorted(set(int(x) for x in ids.unique()))
    expected = IMPORT_ID if dataset_type == "import" else EXPORT_ID
    unexpected = [i for i in unique_ids if i != expected]
    if unexpected:
        raise ValueError(f"Unexpected indicator IDs in {path}: found {unique_ids}, expected only {expected}")
    series_names = sorted({s.strip() for s in df.get("name", pd.Series(dtype=str)).astype(str).unique()})
    geoids = sorted({g for g in df.get("geoid", pd.Series(dtype=str)).astype(str).unique() if g != ""})
    geonames = sorted({g for g in df.get("geoname", pd.Series(dtype=str)).astype(str).unique() if g != ""})
    if dataset_type == "import":
        required_series_sub = "Término de facturación de energía activa del PVPC 2.0TD"
        if not any(required_series_sub in s for s in series_names):
            raise ValueError(f"Import series name validation failed for {path}. Found series names: {series_names}. Must contain: '{required_series_sub}'")
        if len(geonames) > 0 and not any("Península" in g for g in geonames):
            raise ValueError(f"Import geography validation failed for {path}. geoname values: {geonames}. Expected 'Península' when geography is populated.")
    else:
        required_series_sub = "Precio de la energía excedentaria del autoconsumo para el mecanismo de compensación simplificada"
        if not any(required_series_sub in s for s in series_names):
            raise ValueError(f"Export series name validation failed for {path}. Found series names: {series_names}. Must contain: '{required_series_sub}'")
    return expected, series_names, geoids, geonames


def modal_timedelta(deltas: List[pd.Timedelta]) -> Optional[pd.Timedelta]:
    if not deltas:
        return None
    cnt = Counter(deltas)
    most_common = cnt.most_common(1)[0][0]
    return most_common


def native_resolution_from_sorted_index(ts_index: pd.DatetimeIndex) -> str:
    if len(ts_index) < 2:
        return "unknown"
    diffs = ts_index.to_series().diff().dropna()
    diffs_pos = diffs[diffs > pd.Timedelta(0)]
    if len(diffs_pos) == 0:
        return "unknown"
    mode = modal_timedelta(list(diffs_pos))
    if mode is None:
        return "unknown"
    td = mode
    if td >= pd.Timedelta(days=1):
        return f"{int(td / pd.Timedelta(days=1))}D"
    elif td >= pd.Timedelta(hours=1):
        return f"{int(td / pd.Timedelta(hours=1))}H"
    elif td >= pd.Timedelta(minutes=1):
        return f"{int(td / pd.Timedelta(minutes=1))}min"
    else:
        return str(td)


def compute_time_audit(df: pd.DataFrame) -> Dict[str, object]:
    res = {}
    res["row_count"] = int(len(df))
    unique_utc = pd.to_datetime(df["timestamp_utc"], utc=True, errors="coerce").dropna().unique()
    res["unique_utc_timestamps"] = int(len(unique_utc))
    if len(unique_utc) > 0:
        start = min(unique_utc)
        end = max(unique_utc)
        res["coverage_start"] = pd.to_datetime(start).isoformat()
        res["coverage_end"] = pd.to_datetime(end).isoformat()
    else:
        res["coverage_start"] = None
        res["coverage_end"] = None
    ts_index = pd.DatetimeIndex(sorted(pd.to_datetime(df["timestamp_utc"], utc=True, errors="coerce").dropna()))
    res["native_resolution"] = native_resolution_from_sorted_index(ts_index)
    res["exact_duplicate_row_count"] = int(df.get("exact_duplicate_row", pd.Series(dtype=int)).sum())
    res["duplicate_utc_timestamp_count"] = int(df.get("duplicate_utc_timestamp", pd.Series(dtype=int)).sum())
    res["duplicate_local_timestamp_count"] = int(df.get("duplicate_local_timestamp", pd.Series(dtype=int)).sum())
    if res["native_resolution"].endswith("H") and res["coverage_start"] and res["coverage_end"]:
        freq = "H"
        expected_index = pd.date_range(start=res["coverage_start"], end=res["coverage_end"], freq=freq, tz="UTC")
        present = pd.DatetimeIndex(pd.to_datetime(df["timestamp_utc"], utc=True, errors="coerce").dropna())
        missing = expected_index.difference(present)
        res["missing_utc_period_count"] = int(len(missing))
        res["missing_utc_period_samples"] = [t.isoformat() for t in missing[:10]]
    else:
        res["missing_utc_period_count"] = None
        res["missing_utc_period_samples"] = []
    if len(ts_index) >= 2 and res["native_resolution"] != "unknown":
        native_td = pd.to_timedelta(res["native_resolution"].replace("H", "hours") if res["native_resolution"].endswith("H") else res["native_resolution"])
        diffs = ts_index.to_series().diff().dropna()
        diffs_pos = diffs[diffs > pd.Timedelta(0)]
        other_intervals = diffs_pos[diffs_pos != native_td]
        res["irregular_interval_count"] = int(len(other_intervals.unique()))
    else:
        res["irregular_interval_count"] = 0
    res["nulls_by_column"] = {col: int(df.get(col, pd.Series(dtype=object)).isna().sum()) for col in ["value", "datetime", "name", "geoid", "geoname"]}
    vals = pd.to_numeric(df.get("value", pd.Series(dtype=float)), errors="coerce").dropna()
    res["negative_price_count"] = int((vals < 0).sum())
    res["min_price_original"] = float(vals.min()) if len(vals) > 0 else None
    res["max_price_original"] = float(vals.max()) if len(vals) > 0 else None
    res["mean_price_original"] = float(vals.mean()) if len(vals) > 0 else None
    res["median_price_original"] = float(vals.median()) if len(vals) > 0 else None
    return res


def build_raw_file_manifest_row(path: Path, sha: str, encoding: Optional[str], sep: Optional[str], df: pd.DataFrame,
                                identical_hash_group: int, canonical_file: str, status: str, warnings: List[str]) -> Dict[str, object]:
    try:
        parsed = pd.to_datetime(df.get("datetime", pd.Series(dtype=str)), utc=True, errors="coerce").dropna()
        if len(parsed) > 0:
            coverage_start = parsed.min().isoformat()
            coverage_end = parsed.max().isoformat()
            unique_ts = int(parsed.nunique())
            dup_ts = int(len(parsed) - unique_ts)
        else:
            coverage_start = None
            coverage_end = None
            unique_ts = 0
            dup_ts = 0
    except Exception as e:
        coverage_start = None
        coverage_end = None
        unique_ts = 0
        dup_ts = 0
        warnings = warnings + [f"Manifest parsing error: {e}"]
    id_field = ";".join(sorted(set(df.get("id", pd.Series(dtype=str)).astype(str).unique()))) if len(df) > 0 else ""
    name_field = ";".join(sorted(set(df.get("name", pd.Series(dtype=str)).astype(str).unique()))) if len(df) > 0 else ""
    geoid_field = ";".join(sorted(set(df.get("geoid", pd.Series(dtype=str)).astype(str).unique()))) if len(df) > 0 else ""
    geoname_field = ";".join(sorted(set(df.get("geoname", pd.Series(dtype=str)).astype(str).unique()))) if len(df) > 0 else ""
    return {
        "dataset_type": "pvpc_import" if "pvpc_import" in str(path) else "pvpc_export",
        "relative_path": str(path),
        "sha256": sha,
        "file_size_bytes": int(path.stat().st_size) if path.exists() else None,
        "row_count": int(len(df)),
        "detected_encoding": encoding,
        "detected_separator": sep,
        "indicator_id": id_field,
        "series_name": name_field,
        "geoid": geoid_field,
        "geoname": geoname_field,
        "coverage_start": coverage_start,
        "coverage_end": coverage_end,
        "unique_timestamp_count": unique_ts,
        "duplicate_timestamp_count": int(dup_ts),
        "identical_hash_group": identical_hash_group,
        "canonical_file": canonical_file,
        "status": status,
        "warnings": ";".join(warnings),
    }


def merge_manifest(existing_manifest: Optional[Path], new_rows: List[Dict], dataset_type: str) -> pd.DataFrame:
    if existing_manifest is not None and existing_manifest.exists():
        try:
            existing_df = pd.read_csv(existing_manifest, dtype=str)
        except Exception:
            existing_df = pd.DataFrame()
    else:
        existing_df = pd.DataFrame()
    new_df = pd.DataFrame(new_rows)
    if not existing_df.empty and "dataset_type" in existing_df.columns:
        preserved = existing_df[existing_df["dataset_type"] != dataset_type]
        merged = pd.concat([preserved, new_df], ignore_index=True, sort=False)
    else:
        merged = new_df
    return merged


def merge_summary(existing_summary: Optional[Path], new_summary_rows: List[Dict], dataset_type: str) -> pd.DataFrame:
    if existing_summary is not None and existing_summary.exists():
        try:
            existing_df = pd.read_csv(existing_summary, dtype=str)
        except Exception:
            existing_df = pd.DataFrame()
    else:
        existing_df = pd.DataFrame()
    new_df = pd.DataFrame(new_summary_rows)
    if not existing_df.empty and "source_file" in existing_df.columns:
        preserved = existing_df[~existing_df["source_file"].str.contains(dataset_type, na=False)]
        merged = pd.concat([preserved, new_df], ignore_index=True, sort=False)
    else:
        merged = new_df
    return merged


def safe_isoformat_timestamp(ts):
    if pd.isna(ts):
        return ""
    if isinstance(ts, (pd.Timestamp, )):
        s = ts.isoformat()
        if " " in s:
            s = s.replace(" ", "T")
        return s
    try:
        t = pd.to_datetime(ts)
        return t.isoformat()
    except Exception:
        return str(ts)


def process_dataset(dataset_type: str, input_dir: Path, output_file: Path, unit_hint: str):
    input_dir = Path(input_dir)
    output_file = Path(output_file)
    if not input_dir.exists() or not any(input_dir.glob("*.csv")):
        raise FileNotFoundError(f"Input folder {input_dir} not found or contains no CSV files.")
    processed_root = output_file.parent.parent
    silver_dir = output_file.parent
    audit_dir = processed_root / "audit"
    silver_dir.mkdir(parents=True, exist_ok=True)
    audit_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = audit_dir / "pvpc_raw_file_manifest.csv"
    summary_path = audit_dir / "pvpc_ingestion_summary.csv"
    audit_txt_path = audit_dir / "pvpc_ingestion_audit.txt"
    files = sorted(list(input_dir.glob("*.csv")))
    file_hash_map: Dict[str, List[Path]] = {}
    for p in files:
        sha = sha256_of_file(p)
        file_hash_map.setdefault(sha, []).append(p)
    manifest_rows = []
    canonical_processed = []
    canonical_errors = []
    for group_id, (sha, paths) in enumerate(sorted(file_hash_map.items()), start=1):
        canonical = sorted(paths)[0]
        for p in paths:
            try:
                df_raw, enc, sep = detect_encoding_and_read(p)
                manifest_rows.append(build_raw_file_manifest_row(p, sha, enc, sep, df_raw, group_id, str(canonical), "ok", []))
            except Exception as e:
                manifest_rows.append(build_raw_file_manifest_row(p, sha, None, None, pd.DataFrame(), group_id, str(canonical), "error", [str(e)]))
        p = canonical
        try:
            df_raw, enc, sep = detect_encoding_and_read(p)
            validate_required_columns(df_raw, p)
            expected_id, series_names, geoids, geonames = detect_indicator_and_validate(df_raw, dataset_type, p)
            df = parse_and_enrich(df_raw, p)
            df = convert_price_column(df, unit_hint, p)
            df["dataset_type"] = "pvpc_import" if dataset_type == "import" else "pvpc_export"
            df["indicator_id"] = expected_id
            df["series_name"] = df.get("name", pd.Series(dtype=str)).astype(str)
            df["source_file"] = str(p)
            df["source_sha256"] = sha
            canonical_processed.append((p, sha, df, group_id, series_names, geonames))
        except Exception as e:
            canonical_errors.append((p, e))
            manifest_rows.append(build_raw_file_manifest_row(p, sha, enc if 'enc' in locals() else None, sep if 'sep' in locals() else None, pd.DataFrame(), group_id, str(p), "error", [str(e)]))
            continue
    if len(canonical_processed) == 0:

    # Preserve validation errors as ValueError so callers/tests
    # can distinguish invalid input data from runtime failures.
    if canonical_errors:

        # If there is a single canonical input and its failure
        # is a validation error, re-raise that original error.
        if (
            len(canonical_errors) == 1
            and isinstance(
                canonical_errors[0][1],
                ValueError
            )
        ):
            raise canonical_errors[0][1]

        msg_lines = [
            "No canonical input files processed successfully."
        ]

        for p, e in canonical_errors:
            msg_lines.append(
                f"Canonical file error: {p} -> "
                f"{type(e).__name__}: {e}"
            )

        raise RuntimeError(
            "\n".join(msg_lines)
        )

    raise RuntimeError(
        "No canonical input files processed successfully."
    )
    concatenated = []
    for p, sha, df, group_id, series_names, geonames in canonical_processed:
        df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True, errors="raise")
        df["timestamp_local"] = pd.to_datetime(df["timestamp_local"], errors="raise")
        concatenated.append(df)
    combined = pd.concat(concatenated, ignore_index=True, sort=False)
    combined = mark_duplicates_global(combined)
    conflicts = []
    grouped = combined.groupby("timestamp_utc", dropna=True)
    for ts, group in grouped:
        if len(group) <= 1:
            continue
        price_vals = sorted(set(group["price_original"].astype(str).tolist()))
        ids = sorted(set(group["indicator_id"].astype(str).tolist()))
        series_vals = sorted(set(group["series_name"].astype(str).tolist()))
        if len(price_vals) > 1 or len(ids) > 1 or len(series_vals) > 1:
            conflicts.append({
                "timestamp_utc": safe_isoformat_timestamp(ts),
                "prices": price_vals,
                "indicator_ids": ids,
                "series_names": series_vals,
                "source_files": list(group["source_file"].unique()),
            })
    if conflicts:
        err_msg = ["Conflicting observations detected at the same UTC timestamp:"]
        for c in conflicts:
            err_msg.append(json.dumps(c, ensure_ascii=False))
        raise ValueError("\n".join(err_msg))
    outcols = [
        "dataset_type", "indicator_id", "series_name", "geoid", "geoname",
        "datetime_original", "timestamp_utc", "timestamp_local",
        "price_original", "original_unit", "conversion_applied", "price_eur_kwh",
        "source_file", "source_sha256",
        "exact_duplicate_row", "duplicate_utc_timestamp", "duplicate_local_timestamp"
    ]
    for c in outcols:
        if c not in combined.columns:
            combined[c] = pd.NA
    silver_df = combined[outcols].copy()
    silver_df["timestamp_utc"] = silver_df["timestamp_utc"].apply(safe_isoformat_timestamp)
    silver_df["timestamp_local"] = silver_df["timestamp_local"].apply(safe_isoformat_timestamp)
    silver_df.to_csv(output_file, index=False)
    canonical_manifest_rows = []
    ingestion_summaries = []
    for p, sha, df, group_id, series_names, geonames in canonical_processed:
        time_audit = compute_time_audit(df.assign(timestamp_utc=pd.to_datetime(df["timestamp_utc"], utc=True)))
        summary = {
            "source_file": str(p),
            "sha256": sha,
            "identical_hash_group": group_id,
            "row_count": time_audit["row_count"],
            "unique_utc_timestamps": time_audit["unique_utc_timestamps"],
            "coverage_start": time_audit["coverage_start"],
            "coverage_end": time_audit["coverage_end"],
            "native_resolution": time_audit["native_resolution"],
            "exact_duplicate_row_count": time_audit["exact_duplicate_row_count"],
            "duplicate_utc_timestamp_count": time_audit["duplicate_utc_timestamp_count"],
            "duplicate_local_timestamp_count": time_audit["duplicate_local_timestamp_count"],
            "missing_utc_period_count": time_audit["missing_utc_period_count"],
            "negative_price_count": time_audit["negative_price_count"],
            "min_price_original": time_audit["min_price_original"],
            "max_price_original": time_audit["max_price_original"],
            "mean_price_original": time_audit["mean_price_original"],
            "median_price_original": time_audit["median_price_original"],
            "original_unit": df["original_unit"].iloc[0] if len(df) > 0 else None,
            "conversion_applied": bool(df["conversion_applied"].iloc[0]) if len(df) > 0 else None,
            "indicator_id": df["indicator_id"].iloc[0] if len(df) > 0 else None,
            "series_name_sample": ";".join(series_names[:3]) if series_names else "",
            "geographical_area_sample": ";".join(geonames[:3]) if geonames else "",
            "dataset_type": "pvpc_import" if dataset_type == "import" else "pvpc_export",
        }
        ingestion_summaries.append(summary)
        canonical_manifest_rows.append(build_raw_file_manifest_row(p, sha, None, None, df, group_id, str(p), "ok", []))
    merged_manifest = merge_manifest(manifest_path, manifest_rows, "pvpc_import" if dataset_type == "import" else "pvpc_export")
    merged_manifest.to_csv(manifest_path, index=False)
    merged_summary = merge_summary(summary_path, ingestion_summaries, "pvpc_import" if dataset_type == "import" else "pvpc_export")
    merged_summary.to_csv(summary_path, index=False)
    try:
        with open(audit_txt_path, "a", encoding="utf-8") as fh:
            fh.write(f"\n---- PVPC ingestion audit for dataset: {dataset_type} ----\n")
            for s in ingestion_summaries:
                fh.write(json.dumps(s, indent=2, ensure_ascii=False) + "\n")
            fh.write("\nRaw file manifest snapshot (new rows):\n")
            fh.write(pd.DataFrame(manifest_rows).to_string(index=False))
            fh.write("\n\n")
    except Exception:
        pass
    return {
        "silver_file": str(output_file),
        "raw_manifest": str(manifest_path),
        "summary_csv": str(summary_path),
        "audit_txt": str(audit_txt_path),
    }


def main(argv: Optional[List[str]] = None):
    import argparse, traceback, sys
    p = argparse.ArgumentParser(description="Ingest PVPC import/export CSVs into silver and produce audits (safe mode)")
    p.add_argument("--dataset", choices=["import", "export"], required=True, help="Which PVPC dataset to ingest")
    p.add_argument("--input", required=True, help="Input directory containing raw CSVs")
    p.add_argument("--output", required=True, help="Output silver CSV path")
    p.add_argument("--unit", required=True, choices=["EUR/MWh", "EUR/kWh"], help="Unit hint for numeric values in 'value' column")
    args = p.parse_args(argv)
    input_dir = Path(args.input)
    output_file = Path(args.output)
    try:
        res = process_dataset(args.dataset, input_dir, output_file, args.unit)
        print("Ingestion completed. Outputs:")
        for k, v in res.items():
            print(f"  {k}: {v}")
    except Exception as e:
        print("Ingestion failed:", file=sys.stderr)
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()
