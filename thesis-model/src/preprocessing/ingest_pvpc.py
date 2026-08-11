#!/usr/bin/env python3
"""
PVPC ingestion utility.

No import-time filesystem side-effects. Audit and processed paths are derived
from the provided output_file inside process_dataset.

The module implements:
- robust CSV parsing;
- indicator validation;
- timezone-aware timestamp conversion;
- price-unit conversion;
- duplicate detection;
- raw-file manifests;
- ingestion summaries;
- audit outputs.

Validation errors are preserved as ValueError where appropriate so callers
and unit tests can distinguish invalid source data from runtime failures.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd


# ============================================================
# CONSTANTS
# ============================================================

ENCODINGS_TO_TRY = [
    "utf-8-sig",
    "utf-8",
    "latin-1",
    "cp1252",
]

SEPARATOR = ";"

LOCAL_TZ = "Europe/Madrid"

IMPORT_ID = 1001
EXPORT_ID = 1739


# ============================================================
# FILE HASHING
# ============================================================

def sha256_of_file(path: Path) -> str:
    """
    Calculate SHA-256 hash of a file.
    """

    h = hashlib.sha256()

    with path.open("rb") as f:

        for chunk in iter(
            lambda: f.read(8192),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


# ============================================================
# CSV READING
# ============================================================

def detect_encoding_and_read(
    path: Path,
) -> Tuple[pd.DataFrame, str, str]:
    """
    Read a semicolon-separated PVPC CSV using the first
    successful encoding from ENCODINGS_TO_TRY.
    """

    last_exc = None

    for enc in ENCODINGS_TO_TRY:

        try:

            df = pd.read_csv(
                path,
                sep=SEPARATOR,
                encoding=enc,
                engine="python",
                dtype=str,
            )

            return (
                df,
                enc,
                SEPARATOR,
            )

        except Exception as exc:

            last_exc = exc
            continue

    raise ValueError(
        f"Unable to read file {path} with any of "
        f"{ENCODINGS_TO_TRY}. "
        f"Last error: {last_exc}"
    )


# ============================================================
# REQUIRED COLUMN VALIDATION
# ============================================================

def validate_required_columns(
    df: pd.DataFrame,
    path: Path,
):
    """
    Validate mandatory raw PVPC columns.
    """

    required = [
        "value",
        "datetime",
        "id",
    ]

    missing = [
        column
        for column in required
        if column not in df.columns
    ]

    if missing:

        raise ValueError(
            f"Missing required column(s) "
            f"{missing} in {path}"
        )


# ============================================================
# TIMESTAMP PARSING
# ============================================================

def parse_and_enrich(
    df: pd.DataFrame,
    path: Path,
) -> pd.DataFrame:
    """
    Parse source timestamps and create UTC and
    Europe/Madrid timestamp fields.
    """

    df = df.copy()

    df["datetime_original"] = (
        df.get(
            "datetime",
            pd.Series(dtype=str),
        )
        .astype(str)
    )

    try:

        ts = pd.to_datetime(
            df["datetime"],
            utc=True,
            errors="raise",
        )

    except Exception as exc:

        raise ValueError(
            f"Invalid datetime values in "
            f"{path}: {exc}"
        ) from exc

    df["timestamp_utc"] = ts

    df["timestamp_local"] = (
        ts.dt.tz_convert(
            LOCAL_TZ
        )
    )

    return df


# ============================================================
# DUPLICATE DETECTION
# ============================================================

def mark_duplicates_global(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Flag:
    - exact duplicate rows;
    - duplicate UTC timestamps;
    - duplicate local wall-clock timestamps.
    """

    df = df.copy()

    serialised = (
        df.fillna("")
        .astype(str)
        .agg(
            "||".join,
            axis=1,
        )
    )

    row_hash = serialised.map(
        lambda value: hashlib.sha256(
            value.encode("utf-8")
        ).hexdigest()
    )

    df["__row_hash"] = row_hash

    duplicate_hashes = row_hash[
        row_hash.duplicated(
            keep=False
        )
    ]

    df["exact_duplicate_row"] = (
        df["__row_hash"].isin(
            set(
                duplicate_hashes
            )
        )
    )

    df["duplicate_utc_timestamp"] = (
        df["timestamp_utc"]
        .duplicated(
            keep=False
        )
    )

    local_wall_clock = (
        df["timestamp_local"]
        .dt.tz_localize(None)
    )

    df["duplicate_local_timestamp"] = (
        local_wall_clock
        .duplicated(
            keep=False
        )
    )

    df.drop(
        columns=[
            "__row_hash"
        ],
        inplace=True,
    )

    return df


# ============================================================
# PRICE CONVERSION
# ============================================================

def convert_price_column(
    df: pd.DataFrame,
    unit_hint: str,
    path: Path,
) -> pd.DataFrame:
    """
    Convert raw PVPC prices to EUR/kWh while preserving
    the original price and original unit.
    """

    df = df.copy()

    try:

        df["price_original"] = (
            pd.to_numeric(
                df["value"],
                errors="raise",
            )
        )

    except Exception as exc:

        raise ValueError(
            f"Non-numeric price values "
            f"in {path}: {exc}"
        ) from exc

    if unit_hint not in (
        "EUR/MWh",
        "EUR/kWh",
    ):

        raise ValueError(
            "unit_hint must be "
            "'EUR/MWh' or 'EUR/kWh' "
            f"- got: {unit_hint}"
        )

    df["original_unit"] = (
        unit_hint
    )

    if unit_hint == "EUR/MWh":

        df["price_eur_kwh"] = (
            df["price_original"]
            / 1000.0
        )

        df["conversion_applied"] = (
            True
        )

    else:

        df["price_eur_kwh"] = (
            df["price_original"]
        )

        df["conversion_applied"] = (
            False
        )

    return df


# ============================================================
# INDICATOR VALIDATION
# ============================================================

def detect_indicator_and_validate(
    df: pd.DataFrame,
    dataset_type: str,
    path: Path,
) -> Tuple[
    int,
    List[str],
    List[str],
    List[str],
]:
    """
    Validate PVPC indicator ID, series name and geography.
    """

    if dataset_type not in (
        "import",
        "export",
    ):

        raise ValueError(
            "dataset_type must be "
            "'import' or 'export'. "
            f"Got: {dataset_type}"
        )

    ids = pd.to_numeric(
        df.get(
            "id",
            pd.Series(dtype=str),
        ),
        errors="coerce",
    )

    if ids.isna().any():

        raise ValueError(
            f"Non-numeric id values "
            f"in {path}"
        )

    unique_ids = sorted(
        set(
            int(value)
            for value
            in ids.unique()
        )
    )

    expected = (
        IMPORT_ID
        if dataset_type == "import"
        else EXPORT_ID
    )

    unexpected = [
        indicator_id
        for indicator_id
        in unique_ids
        if indicator_id != expected
    ]

    if unexpected:

        raise ValueError(
            f"Unexpected indicator IDs "
            f"in {path}: "
            f"found {unique_ids}, "
            f"expected only {expected}"
        )

    series_names = sorted(
        {
            value.strip()
            for value
            in df.get(
                "name",
                pd.Series(dtype=str),
            )
            .astype(str)
            .unique()
        }
    )

    geoids = sorted(
        {
            value
            for value
            in df.get(
                "geoid",
                pd.Series(dtype=str),
            )
            .astype(str)
            .unique()
            if value != ""
        }
    )

    geonames = sorted(
        {
            value
            for value
            in df.get(
                "geoname",
                pd.Series(dtype=str),
            )
            .astype(str)
            .unique()
            if value != ""
        }
    )

    if dataset_type == "import":

        required_series_sub = (
            "Término de facturación de energía "
            "activa del PVPC 2.0TD"
        )

        if not any(
            required_series_sub
            in series_name
            for series_name
            in series_names
        ):

            raise ValueError(
                "Import series name validation "
                f"failed for {path}. "
                f"Found series names: {series_names}. "
                "Must contain: "
                f"'{required_series_sub}'"
            )

        if (
            len(geonames) > 0
            and not any(
                "Península" in geography
                for geography
                in geonames
            )
        ):

            raise ValueError(
                "Import geography validation "
                f"failed for {path}. "
                f"geoname values: {geonames}. "
                "Expected 'Península' when "
                "geography is populated."
            )

    else:

        required_series_sub = (
            "Precio de la energía excedentaria "
            "del autoconsumo para el mecanismo "
            "de compensación simplificada"
        )

        if not any(
            required_series_sub
            in series_name
            for series_name
            in series_names
        ):

            raise ValueError(
                "Export series name validation "
                f"failed for {path}. "
                f"Found series names: "
                f"{series_names}. "
                "Must contain: "
                f"'{required_series_sub}'"
            )

    return (
        expected,
        series_names,
        geoids,
        geonames,
    )


# ============================================================
# RESOLUTION HELPERS
# ============================================================

def modal_timedelta(
    deltas: List[pd.Timedelta],
) -> Optional[pd.Timedelta]:
    """
    Return the modal timedelta.
    """

    if not deltas:
        return None

    counts = Counter(
        deltas
    )

    return (
        counts
        .most_common(1)[0][0]
    )


def native_resolution_from_sorted_index(
    ts_index: pd.DatetimeIndex,
) -> str:
    """
    Determine the modal positive interval between timestamps.
    """

    if len(ts_index) < 2:
        return "unknown"

    diffs = (
        ts_index
        .to_series()
        .diff()
        .dropna()
    )

    positive_diffs = diffs[
        diffs > pd.Timedelta(0)
    ]

    if len(positive_diffs) == 0:
        return "unknown"

    mode = modal_timedelta(
        list(
            positive_diffs
        )
    )

    if mode is None:
        return "unknown"

    td = mode

    if td >= pd.Timedelta(days=1):

        return (
            f"{int(td / pd.Timedelta(days=1))}D"
        )

    if td >= pd.Timedelta(hours=1):

        return (
            f"{int(td / pd.Timedelta(hours=1))}H"
        )

    if td >= pd.Timedelta(minutes=1):

        return (
            f"{int(td / pd.Timedelta(minutes=1))}min"
        )

    return str(td)


# ============================================================
# TIME AUDIT
# ============================================================

def compute_time_audit(
    df: pd.DataFrame,
) -> Dict[str, object]:
    """
    Calculate timestamp, duplicate, missing-period and
    price statistics for an ingested PVPC dataset.
    """

    res: Dict[str, object] = {}

    res["row_count"] = int(
        len(df)
    )

    parsed_utc = pd.to_datetime(
        df["timestamp_utc"],
        utc=True,
        errors="coerce",
    )

    unique_utc = (
        parsed_utc
        .dropna()
        .unique()
    )

    res["unique_utc_timestamps"] = int(
        len(unique_utc)
    )

    if len(unique_utc) > 0:

        start = min(
            unique_utc
        )

        end = max(
            unique_utc
        )

        res["coverage_start"] = (
            pd.to_datetime(
                start
            )
            .isoformat()
        )

        res["coverage_end"] = (
            pd.to_datetime(
                end
            )
            .isoformat()
        )

    else:

        res["coverage_start"] = None
        res["coverage_end"] = None

    ts_index = pd.DatetimeIndex(
        sorted(
            parsed_utc
            .dropna()
        )
    )

    res["native_resolution"] = (
        native_resolution_from_sorted_index(
            ts_index
        )
    )

    res["exact_duplicate_row_count"] = int(
        df.get(
            "exact_duplicate_row",
            pd.Series(dtype=int),
        )
        .sum()
    )

    res["duplicate_utc_timestamp_count"] = int(
        df.get(
            "duplicate_utc_timestamp",
            pd.Series(dtype=int),
        )
        .sum()
    )

    res["duplicate_local_timestamp_count"] = int(
        df.get(
            "duplicate_local_timestamp",
            pd.Series(dtype=int),
        )
        .sum()
    )

    # --------------------------------------------------------
    # Missing UTC periods
    # --------------------------------------------------------

    if (
        str(
            res["native_resolution"]
        ).endswith("H")
        and res["coverage_start"]
        and res["coverage_end"]
    ):

        # Lower-case "h" prevents pandas FutureWarning.
        freq = "h"

        expected_index = pd.date_range(
            start=res[
                "coverage_start"
            ],
            end=res[
                "coverage_end"
            ],
            freq=freq,
            tz="UTC",
        )

        present = pd.DatetimeIndex(
            parsed_utc
            .dropna()
        )

        missing = (
            expected_index
            .difference(
                present
            )
        )

        res["missing_utc_period_count"] = int(
            len(missing)
        )

        res["missing_utc_period_samples"] = [
            timestamp.isoformat()
            for timestamp
            in missing[:10]
        ]

    else:

        res["missing_utc_period_count"] = None

        res["missing_utc_period_samples"] = []

    # --------------------------------------------------------
    # Irregular intervals
    # --------------------------------------------------------

    if (
        len(ts_index) >= 2
        and res[
            "native_resolution"
        ] != "unknown"
    ):

        resolution_text = str(
            res[
                "native_resolution"
            ]
        )

        if resolution_text.endswith("H"):

            native_td = pd.to_timedelta(
                resolution_text.replace(
                    "H",
                    "hours",
                )
            )

        else:

            native_td = pd.to_timedelta(
                resolution_text
            )

        diffs = (
            ts_index
            .to_series()
            .diff()
            .dropna()
        )

        positive_diffs = diffs[
            diffs > pd.Timedelta(0)
        ]

        other_intervals = (
            positive_diffs[
                positive_diffs
                != native_td
            ]
        )

        res["irregular_interval_count"] = int(
            len(
                other_intervals
                .unique()
            )
        )

    else:

        res["irregular_interval_count"] = 0

    # --------------------------------------------------------
    # Nulls
    # --------------------------------------------------------

    res["nulls_by_column"] = {
        column: int(
            df.get(
                column,
                pd.Series(dtype=object),
            )
            .isna()
            .sum()
        )
        for column
        in [
            "value",
            "datetime",
            "name",
            "geoid",
            "geoname",
        ]
    }

    # --------------------------------------------------------
    # Price statistics
    # --------------------------------------------------------

    values = (
        pd.to_numeric(
            df.get(
                "value",
                pd.Series(dtype=float),
            ),
            errors="coerce",
        )
        .dropna()
    )

    res["negative_price_count"] = int(
        (
            values < 0
        ).sum()
    )

    res["min_price_original"] = (
        float(
            values.min()
        )
        if len(values) > 0
        else None
    )

    res["max_price_original"] = (
        float(
            values.max()
        )
        if len(values) > 0
        else None
    )

    res["mean_price_original"] = (
        float(
            values.mean()
        )
        if len(values) > 0
        else None
    )

    res["median_price_original"] = (
        float(
            values.median()
        )
        if len(values) > 0
        else None
    )

    return res


# ============================================================
# RAW FILE MANIFEST
# ============================================================

def build_raw_file_manifest_row(
    path: Path,
    sha: str,
    encoding: Optional[str],
    sep: Optional[str],
    df: pd.DataFrame,
    identical_hash_group: int,
    canonical_file: str,
    status: str,
    warnings: List[str],
) -> Dict[str, object]:
    """
    Build one raw-file manifest record.
    """

    try:

        parsed = (
            pd.to_datetime(
                df.get(
                    "datetime",
                    pd.Series(dtype=str),
                ),
                utc=True,
                errors="coerce",
            )
            .dropna()
        )

        if len(parsed) > 0:

            coverage_start = (
                parsed.min()
                .isoformat()
            )

            coverage_end = (
                parsed.max()
                .isoformat()
            )

            unique_ts = int(
                parsed.nunique()
            )

            dup_ts = int(
                len(parsed)
                - unique_ts
            )

        else:

            coverage_start = None
            coverage_end = None
            unique_ts = 0
            dup_ts = 0

    except Exception as exc:

        coverage_start = None
        coverage_end = None
        unique_ts = 0
        dup_ts = 0

        warnings = (
            warnings
            + [
                f"Manifest parsing error: {exc}"
            ]
        )

    id_field = (
        ";".join(
            sorted(
                set(
                    df.get(
                        "id",
                        pd.Series(dtype=str),
                    )
                    .astype(str)
                    .unique()
                )
            )
        )
        if len(df) > 0
        else ""
    )

    name_field = (
        ";".join(
            sorted(
                set(
                    df.get(
                        "name",
                        pd.Series(dtype=str),
                    )
                    .astype(str)
                    .unique()
                )
            )
        )
        if len(df) > 0
        else ""
    )

    geoid_field = (
        ";".join(
            sorted(
                set(
                    df.get(
                        "geoid",
                        pd.Series(dtype=str),
                    )
                    .astype(str)
                    .unique()
                )
            )
        )
        if len(df) > 0
        else ""
    )

    geoname_field = (
        ";".join(
            sorted(
                set(
                    df.get(
                        "geoname",
                        pd.Series(dtype=str),
                    )
                    .astype(str)
                    .unique()
                )
            )
        )
        if len(df) > 0
        else ""
    )

    return {
        "dataset_type":
            (
                "pvpc_import"
                if "pvpc_import"
                in str(path)
                else "pvpc_export"
            ),

        "relative_path":
            str(path),

        "sha256":
            sha,

        "file_size_bytes":
            (
                int(
                    path.stat().st_size
                )
                if path.exists()
                else None
            ),

        "row_count":
            int(
                len(df)
            ),

        "detected_encoding":
            encoding,

        "detected_separator":
            sep,

        "indicator_id":
            id_field,

        "series_name":
            name_field,

        "geoid":
            geoid_field,

        "geoname":
            geoname_field,

        "coverage_start":
            coverage_start,

        "coverage_end":
            coverage_end,

        "unique_timestamp_count":
            unique_ts,

        "duplicate_timestamp_count":
            int(
                dup_ts
            ),

        "identical_hash_group":
            identical_hash_group,

        "canonical_file":
            canonical_file,

        "status":
            status,

        "warnings":
            ";".join(
                warnings
            ),
    }


# ============================================================
# MANIFEST MERGING
# ============================================================

def merge_manifest(
    existing_manifest: Optional[Path],
    new_rows: List[Dict],
    dataset_type: str,
) -> pd.DataFrame:
    """
    Merge new manifest rows while preserving records
    belonging to the other PVPC dataset type.
    """

    if (
        existing_manifest is not None
        and existing_manifest.exists()
    ):

        try:

            existing_df = pd.read_csv(
                existing_manifest,
                dtype=str,
            )

        except Exception:

            existing_df = (
                pd.DataFrame()
            )

    else:

        existing_df = (
            pd.DataFrame()
        )

    new_df = pd.DataFrame(
        new_rows
    )

    if (
        not existing_df.empty
        and "dataset_type"
        in existing_df.columns
    ):

        preserved = existing_df[
            existing_df[
                "dataset_type"
            ] != dataset_type
        ]

        merged = pd.concat(
            [
                preserved,
                new_df,
            ],
            ignore_index=True,
            sort=False,
        )

    else:

        merged = new_df

    return merged


# ============================================================
# SUMMARY MERGING
# ============================================================

def merge_summary(
    existing_summary: Optional[Path],
    new_summary_rows: List[Dict],
    dataset_type: str,
) -> pd.DataFrame:
    """
    Merge ingestion summaries while preserving records
    belonging to the other dataset type.
    """

    if (
        existing_summary is not None
        and existing_summary.exists()
    ):

        try:

            existing_df = pd.read_csv(
                existing_summary,
                dtype=str,
            )

        except Exception:

            existing_df = (
                pd.DataFrame()
            )

    else:

        existing_df = (
            pd.DataFrame()
        )

    new_df = pd.DataFrame(
        new_summary_rows
    )

    if (
        not existing_df.empty
        and "dataset_type"
        in existing_df.columns
    ):

        preserved = existing_df[
            existing_df[
                "dataset_type"
            ] != dataset_type
        ]

        merged = pd.concat(
            [
                preserved,
                new_df,
            ],
            ignore_index=True,
            sort=False,
        )

    elif (
        not existing_df.empty
        and "source_file"
        in existing_df.columns
    ):

        preserved = existing_df[
            ~existing_df[
                "source_file"
            ]
            .astype(str)
            .str.contains(
                dataset_type,
                na=False,
            )
        ]

        merged = pd.concat(
            [
                preserved,
                new_df,
            ],
            ignore_index=True,
            sort=False,
        )

    else:

        merged = new_df

    return merged


# ============================================================
# TIMESTAMP SERIALISATION
# ============================================================

def safe_isoformat_timestamp(
    ts,
):
    """
    Convert timestamp-like value to ISO-8601 text.
    """

    if pd.isna(ts):
        return ""

    if isinstance(
        ts,
        pd.Timestamp,
    ):

        return (
            ts.isoformat()
            .replace(
                " ",
                "T",
            )
        )

    try:

        timestamp = pd.to_datetime(
            ts
        )

        return (
            timestamp
            .isoformat()
            .replace(
                " ",
                "T",
            )
        )

    except Exception:

        return str(ts)


# ============================================================
# MAIN DATASET PROCESSOR
# ============================================================

def process_dataset(
    dataset_type: str,
    input_dir: Path,
    output_file: Path,
    unit_hint: str,
):
    """
    Ingest one PVPC dataset type and produce:
    - Silver dataset;
    - raw-file manifest;
    - ingestion summary;
    - text audit.
    """

    # --------------------------------------------------------
    # Validate arguments
    # --------------------------------------------------------

    if dataset_type not in (
        "import",
        "export",
    ):

        raise ValueError(
            "dataset_type must be "
            "'import' or 'export'. "
            f"Got: {dataset_type}"
        )

    input_dir = Path(
        input_dir
    )

    output_file = Path(
        output_file
    )

    if (
        not input_dir.exists()
        or not any(
            input_dir.glob(
                "*.csv"
            )
        )
    ):

        raise FileNotFoundError(
            f"Input folder {input_dir} "
            "not found or contains "
            "no CSV files."
        )

    # --------------------------------------------------------
    # Output directories
    # --------------------------------------------------------

    processed_root = (
        output_file
        .parent
        .parent
    )

    silver_dir = (
        output_file.parent
    )

    audit_dir = (
        processed_root
        / "audit"
    )

    silver_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    audit_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    manifest_path = (
        audit_dir
        / "pvpc_raw_file_manifest.csv"
    )

    summary_path = (
        audit_dir
        / "pvpc_ingestion_summary.csv"
    )

    audit_txt_path = (
        audit_dir
        / "pvpc_ingestion_audit.txt"
    )

    # --------------------------------------------------------
    # Discover files
    # --------------------------------------------------------

    files = sorted(
        list(
            input_dir.glob(
                "*.csv"
            )
        )
    )

    # --------------------------------------------------------
    # Group identical files by SHA-256
    # --------------------------------------------------------

    file_hash_map: Dict[
        str,
        List[Path],
    ] = {}

    for path in files:

        sha = sha256_of_file(
            path
        )

        file_hash_map.setdefault(
            sha,
            [],
        ).append(
            path
        )

    manifest_rows = []

    canonical_processed = []

    canonical_errors = []

    # --------------------------------------------------------
    # Process one canonical file per identical-hash group
    # --------------------------------------------------------

    for (
        group_id,
        (
            sha,
            paths,
        ),
    ) in enumerate(
        sorted(
            file_hash_map.items()
        ),
        start=1,
    ):

        canonical = sorted(
            paths
        )[0]

        # Record all physical files in manifest
        for path in paths:

            try:

                (
                    raw_manifest_df,
                    manifest_encoding,
                    manifest_separator,
                ) = detect_encoding_and_read(
                    path
                )

                manifest_rows.append(
                    build_raw_file_manifest_row(
                        path=path,
                        sha=sha,
                        encoding=manifest_encoding,
                        sep=manifest_separator,
                        df=raw_manifest_df,
                        identical_hash_group=group_id,
                        canonical_file=str(
                            canonical
                        ),
                        status="ok",
                        warnings=[],
                    )
                )

            except Exception as exc:

                manifest_rows.append(
                    build_raw_file_manifest_row(
                        path=path,
                        sha=sha,
                        encoding=None,
                        sep=None,
                        df=pd.DataFrame(),
                        identical_hash_group=group_id,
                        canonical_file=str(
                            canonical
                        ),
                        status="error",
                        warnings=[
                            str(exc)
                        ],
                    )
                )

        # ----------------------------------------------------
        # Process canonical file
        # ----------------------------------------------------

        path = canonical

        try:

            (
                df_raw,
                encoding,
                separator,
            ) = detect_encoding_and_read(
                path
            )

            validate_required_columns(
                df_raw,
                path,
            )

            (
                expected_id,
                series_names,
                geoids,
                geonames,
            ) = detect_indicator_and_validate(
                df_raw,
                dataset_type,
                path,
            )

            df = parse_and_enrich(
                df_raw,
                path,
            )

            df = convert_price_column(
                df,
                unit_hint,
                path,
            )

            df["dataset_type"] = (
                "pvpc_import"
                if dataset_type == "import"
                else "pvpc_export"
            )

            df["indicator_id"] = (
                expected_id
            )

            df["series_name"] = (
                df.get(
                    "name",
                    pd.Series(
                        dtype=str
                    ),
                )
                .astype(str)
            )

            df["source_file"] = str(
                path
            )

            df["source_sha256"] = (
                sha
            )

            canonical_processed.append(
                (
                    path,
                    sha,
                    df,
                    group_id,
                    series_names,
                    geonames,
                )
            )

        except Exception as exc:

            canonical_errors.append(
                (
                    path,
                    exc,
                )
            )

            manifest_rows.append(
                build_raw_file_manifest_row(
                    path=path,
                    sha=sha,
                    encoding=(
                        encoding
                        if "encoding"
                        in locals()
                        else None
                    ),
                    sep=(
                        separator
                        if "separator"
                        in locals()
                        else None
                    ),
                    df=pd.DataFrame(),
                    identical_hash_group=group_id,
                    canonical_file=str(
                        path
                    ),
                    status="error",
                    warnings=[
                        str(exc)
                    ],
                )
            )

            continue

    # ========================================================
    # HANDLE COMPLETE INGESTION FAILURE
    # ========================================================

    if len(
        canonical_processed
    ) == 0:

        # ----------------------------------------------------
        # Preserve a single validation ValueError.
        #
        # This is important because callers/tests must be able
        # to distinguish invalid source data from a general
        # processing/runtime failure.
        # ----------------------------------------------------

        if canonical_errors:

            if (
                len(
                    canonical_errors
                ) == 1
                and isinstance(
                    canonical_errors[
                        0
                    ][1],
                    ValueError,
                )
            ):

                raise canonical_errors[
                    0
                ][1]

            # Multiple failures or non-validation failures.
            msg_lines = [
                "No canonical input files "
                "processed successfully."
            ]

            for (
                error_path,
                error,
            ) in canonical_errors:

                msg_lines.append(
                    "Canonical file error: "
                    f"{error_path} -> "
                    f"{type(error).__name__}: "
                    f"{error}"
                )

            raise RuntimeError(
                "\n".join(
                    msg_lines
                )
            )

        raise RuntimeError(
            "No canonical input files "
            "processed successfully."
        )

    # ========================================================
    # COMBINE CANONICAL DATA
    # ========================================================

    concatenated = []

    for (
        path,
        sha,
        df,
        group_id,
        series_names,
        geonames,
    ) in canonical_processed:

        df[
            "timestamp_utc"
        ] = pd.to_datetime(
            df[
                "timestamp_utc"
            ],
            utc=True,
            errors="raise",
        )

        # Rebuild local timestamp from UTC to ensure
        # one consistent timezone-aware dtype.
        df[
            "timestamp_local"
        ] = (
            df[
                "timestamp_utc"
            ]
            .dt.tz_convert(
                LOCAL_TZ
            )
        )

        concatenated.append(
            df
        )

    combined = pd.concat(
        concatenated,
        ignore_index=True,
        sort=False,
    )

    combined = (
        mark_duplicates_global(
            combined
        )
    )

    # ========================================================
    # CONFLICT CHECK
    # ========================================================

    conflicts = []

    grouped = combined.groupby(
        "timestamp_utc",
        dropna=True,
    )

    for (
        timestamp,
        group,
    ) in grouped:

        if len(group) <= 1:
            continue

        price_values = sorted(
            set(
                group[
                    "price_original"
                ]
                .astype(str)
                .tolist()
            )
        )

        indicator_ids = sorted(
            set(
                group[
                    "indicator_id"
                ]
                .astype(str)
                .tolist()
            )
        )

        series_values = sorted(
            set(
                group[
                    "series_name"
                ]
                .astype(str)
                .tolist()
            )
        )

        if (
            len(
                price_values
            ) > 1
            or len(
                indicator_ids
            ) > 1
            or len(
                series_values
            ) > 1
        ):

            conflicts.append(
                {
                    "timestamp_utc":
                        safe_isoformat_timestamp(
                            timestamp
                        ),

                    "prices":
                        price_values,

                    "indicator_ids":
                        indicator_ids,

                    "series_names":
                        series_values,

                    "source_files":
                        list(
                            group[
                                "source_file"
                            ]
                            .unique()
                        ),
                }
            )

    if conflicts:

        error_lines = [
            "Conflicting observations "
            "detected at the same "
            "UTC timestamp:"
        ]

        for conflict in conflicts:

            error_lines.append(
                json.dumps(
                    conflict,
                    ensure_ascii=False,
                )
            )

        raise ValueError(
            "\n".join(
                error_lines
            )
        )

    # ========================================================
    # SILVER DATASET
    # ========================================================

    output_columns = [
        "dataset_type",
        "indicator_id",
        "series_name",
        "geoid",
        "geoname",
        "datetime_original",
        "timestamp_utc",
        "timestamp_local",
        "price_original",
        "original_unit",
        "conversion_applied",
        "price_eur_kwh",
        "source_file",
        "source_sha256",
        "exact_duplicate_row",
        "duplicate_utc_timestamp",
        "duplicate_local_timestamp",
    ]

    for column in output_columns:

        if column not in combined.columns:

            combined[
                column
            ] = pd.NA

    silver_df = combined[
        output_columns
    ].copy()

    silver_df[
        "timestamp_utc"
    ] = silver_df[
        "timestamp_utc"
    ].apply(
        safe_isoformat_timestamp
    )

    silver_df[
        "timestamp_local"
    ] = silver_df[
        "timestamp_local"
    ].apply(
        safe_isoformat_timestamp
    )

    silver_df.to_csv(
        output_file,
        index=False,
    )

    # ========================================================
    # INGESTION SUMMARY
    # ========================================================

    ingestion_summaries = []

    for (
        path,
        sha,
        df,
        group_id,
        series_names,
        geonames,
    ) in canonical_processed:

        audit_df = df.copy()

        audit_df[
            "timestamp_utc"
        ] = pd.to_datetime(
            audit_df[
                "timestamp_utc"
            ],
            utc=True,
            errors="raise",
        )

        # Ensure duplicate flags are available to the audit.
        audit_df = (
            mark_duplicates_global(
                audit_df
            )
        )

        time_audit = (
            compute_time_audit(
                audit_df
            )
        )

        summary = {
            "source_file":
                str(
                    path
                ),

            "sha256":
                sha,

            "identical_hash_group":
                group_id,

            "row_count":
                time_audit[
                    "row_count"
                ],

            "unique_utc_timestamps":
                time_audit[
                    "unique_utc_timestamps"
                ],

            "coverage_start":
                time_audit[
                    "coverage_start"
                ],

            "coverage_end":
                time_audit[
                    "coverage_end"
                ],

            "native_resolution":
                time_audit[
                    "native_resolution"
                ],

            "exact_duplicate_row_count":
                time_audit[
                    "exact_duplicate_row_count"
                ],

            "duplicate_utc_timestamp_count":
                time_audit[
                    "duplicate_utc_timestamp_count"
                ],

            "duplicate_local_timestamp_count":
                time_audit[
                    "duplicate_local_timestamp_count"
                ],

            "missing_utc_period_count":
                time_audit[
                    "missing_utc_period_count"
                ],

            "negative_price_count":
                time_audit[
                    "negative_price_count"
                ],

            "min_price_original":
                time_audit[
                    "min_price_original"
                ],

            "max_price_original":
                time_audit[
                    "max_price_original"
                ],

            "mean_price_original":
                time_audit[
                    "mean_price_original"
                ],

            "median_price_original":
                time_audit[
                    "median_price_original"
                ],

            "original_unit":
                (
                    df[
                        "original_unit"
                    ].iloc[0]
                    if len(df) > 0
                    else None
                ),

            "conversion_applied":
                (
                    bool(
                        df[
                            "conversion_applied"
                        ].iloc[0]
                    )
                    if len(df) > 0
                    else None
                ),

            "indicator_id":
                (
                    df[
                        "indicator_id"
                    ].iloc[0]
                    if len(df) > 0
                    else None
                ),

            "series_name_sample":
                (
                    ";".join(
                        series_names[:3]
                    )
                    if series_names
                    else ""
                ),

            "geographical_area_sample":
                (
                    ";".join(
                        geonames[:3]
                    )
                    if geonames
                    else ""
                ),

            "dataset_type":
                (
                    "pvpc_import"
                    if dataset_type
                    == "import"
                    else "pvpc_export"
                ),
        }

        ingestion_summaries.append(
            summary
        )

    # ========================================================
    # SAVE MANIFEST
    # ========================================================

    current_dataset_type = (
        "pvpc_import"
        if dataset_type
        == "import"
        else "pvpc_export"
    )

    merged_manifest = (
        merge_manifest(
            manifest_path,
            manifest_rows,
            current_dataset_type,
        )
    )

    merged_manifest.to_csv(
        manifest_path,
        index=False,
    )

    # ========================================================
    # SAVE INGESTION SUMMARY
    # ========================================================

    merged_summary = (
        merge_summary(
            summary_path,
            ingestion_summaries,
            current_dataset_type,
        )
    )

    merged_summary.to_csv(
        summary_path,
        index=False,
    )

    # ========================================================
    # TEXT AUDIT
    # ========================================================

    try:

        with open(
            audit_txt_path,
            "a",
            encoding="utf-8",
        ) as file:

            file.write(
                "\n---- PVPC ingestion audit "
                f"for dataset: "
                f"{dataset_type} ----\n"
            )

            for summary in (
                ingestion_summaries
            ):

                file.write(
                    json.dumps(
                        summary,
                        indent=2,
                        ensure_ascii=False,
                    )
                    + "\n"
                )

            file.write(
                "\nRaw file manifest "
                "snapshot (new rows):\n"
            )

            file.write(
                pd.DataFrame(
                    manifest_rows
                )
                .to_string(
                    index=False
                )
            )

            file.write(
                "\n\n"
            )

    except Exception:
        # Audit text output should not make
        # the ingestion itself fail.
        pass

    # ========================================================
    # RETURN OUTPUT PATHS
    # ========================================================

    return {
        "silver_file":
            str(
                output_file
            ),

        "raw_manifest":
            str(
                manifest_path
            ),

        "summary_csv":
            str(
                summary_path
            ),

        "audit_txt":
            str(
                audit_txt_path
            ),
    }


# ============================================================
# COMMAND-LINE INTERFACE
# ============================================================

def main(
    argv: Optional[
        List[str]
    ] = None,
):
    """
    Command-line interface.
    """

    import sys
    import traceback

    parser = argparse.ArgumentParser(
        description=(
            "Ingest PVPC import/export CSVs "
            "into Silver and produce audit "
            "outputs."
        )
    )

    parser.add_argument(
        "--dataset",
        choices=[
            "import",
            "export",
        ],
        required=True,
        help=(
            "Which PVPC dataset "
            "to ingest."
        ),
    )

    parser.add_argument(
        "--input",
        required=True,
        help=(
            "Input directory "
            "containing raw CSVs."
        ),
    )

    parser.add_argument(
        "--output",
        required=True,
        help=(
            "Output Silver CSV path."
        ),
    )

    parser.add_argument(
        "--unit",
        required=True,
        choices=[
            "EUR/MWh",
            "EUR/kWh",
        ],
        help=(
            "Unit hint for numeric "
            "values in the 'value' column."
        ),
    )

    args = parser.parse_args(
        argv
    )

    input_dir = Path(
        args.input
    )

    output_file = Path(
        args.output
    )

    try:

        result = process_dataset(
            args.dataset,
            input_dir,
            output_file,
            args.unit,
        )

        print(
            "Ingestion completed. Outputs:"
        )

        for key, value in (
            result.items()
        ):

            print(
                f"  {key}: {value}"
            )

    except Exception:

        print(
            "Ingestion failed:",
            file=sys.stderr,
        )

        traceback.print_exc()

        sys.exit(2)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
