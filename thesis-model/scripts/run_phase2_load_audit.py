#!/usr/bin/env python3
"""
Phase 2 London-load audit runner.

Place at:
    thesis-model/scripts/run_phase2_load_audit.py

Run from thesis-model:
    python scripts/run_phase2_load_audit.py

What this script does
---------------------
1. Inspects and audits data/raw/load/load_hourly.csv.
2. Treats London load source timestamps as Europe/London.
3. Detects hourly versus 30-minute native resolution.
4. If 30-minute:
       - aggregates interval energy to hourly by SUM;
       - uses hour-ending timestamps;
       - does not silently fill incomplete hours.
5. Audits every household separately for 2012, 2013 and 2014.
6. Counts complete/incomplete households, missing timestamps,
   duplicates and null observations.
7. Audits OMIE, PVPC import, PVPC export and PVGIS for 2013/2014.
8. Checks exact joint Spanish timestamp coverage.
9. Determines whether 2013 or 2014 can be used as a common year.
10. Runs the existing src.preprocessing.audit_datasets module.
11. Runs pytest.
12. Writes:
       results/load_audit_summary.csv
       results/load_household_year_audit.csv
13. Prints the final Phase-2 decision.

Important rules
---------------
- No interpolation.
- No silent filling.
- No silent duplicate removal.
- No forced 24-hour DST days.
- London source timezone = Europe/London.
- Spanish target calendar = Europe/Madrid.
- Stored comparison timestamps = UTC.
- Price values remain EUR/MWh.
"""

from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

RAW_LOAD = (
    ROOT
    / "data"
    / "raw"
    / "load"
    / "load_hourly.csv"
)

RESULTS = ROOT / "results"
RESULTS.mkdir(parents=True, exist_ok=True)

LOAD_TZ = "Europe/London"
TARGET_TZ = "Europe/Madrid"

TARGET_YEARS = [2012, 2013, 2014]
CANDIDATE_SIMULATION_YEARS = [2013, 2014]

# Thesis model may require up to 50 households.
MINIMUM_COMPLETE_HOUSEHOLDS = 50

CHUNK_SIZE = 200_000


# ============================================================
# MASTER DATASET LOCATIONS
# ============================================================

MASTER_FILE_CANDIDATES = {
    "OMIE": [
        ROOT / "data" / "processed" / "omie.csv",
        ROOT / "data" / "raw" / "omie" / "omie.csv",
    ],
    "PVPC_import": [
        ROOT / "data" / "processed" / "pvpc_import.csv",
        ROOT / "data" / "raw" / "pvpc_import" / "pvpc_import.csv",
    ],
    "PVPC_export": [
        ROOT / "data" / "processed" / "pvpc_export.csv",
        ROOT / "data" / "raw" / "pvpc_export" / "pvpc_export.csv",
    ],
    "PVGIS": [
        ROOT / "data" / "processed" / "pvgis.csv",
        ROOT / "data" / "raw" / "pvgis" / "pvgis.csv",
    ],
}


# ============================================================
# GENERAL HELPERS
# ============================================================

def print_header(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def find_existing_file(
    candidates: List[Path]
) -> Optional[Path]:
    for path in candidates:
        if path.exists():
            return path

    return None


def expected_year_index(
    year: int,
    timezone: str
) -> pd.DatetimeIndex:
    """
    Complete timezone-aware hourly calendar for one local year.

    2012 -> 8784 elapsed hours
    2013 -> 8760
    2014 -> 8760

    DST is preserved automatically.
    """

    start = pd.Timestamp(
        f"{year}-01-01 00:00:00",
        tz=timezone
    )

    end = pd.Timestamp(
        f"{year + 1}-01-01 00:00:00",
        tz=timezone
    )

    return pd.date_range(
        start=start,
        end=end,
        freq="h",
        inclusive="left"
    )


def safe_float(value):
    """
    Convert scalar result to float while preserving missing values.
    """

    if pd.isna(value):
        return None

    return float(value)


# ============================================================
# LOAD COLUMN DETECTION
# ============================================================

def detect_load_columns(
    sample: pd.DataFrame
) -> Tuple[str, str, str]:

    original_columns = list(sample.columns)

    normalized = {
        str(column).strip().lower(): column
        for column in original_columns
    }

    # --------------------------------------------------------
    # Household ID
    # --------------------------------------------------------

    id_candidates = [
        "lclid",
        "household_id",
        "household",
        "meter_id",
        "id",
    ]

    id_column = None

    for candidate in id_candidates:
        if candidate in normalized:
            id_column = normalized[candidate]
            break

    if id_column is None:
        raise ValueError(
            "Could not identify the household ID column. "
            f"Columns found: {original_columns}"
        )

    # --------------------------------------------------------
    # Timestamp
    # --------------------------------------------------------

    timestamp_candidates = [
        "datetime",
        "timestamp",
        "date_time",
        "time",
        "date",
    ]

    timestamp_column = None

    for candidate in timestamp_candidates:
        if candidate in normalized:
            timestamp_column = normalized[candidate]
            break

    if timestamp_column is None:
        raise ValueError(
            "Could not identify the timestamp column. "
            f"Columns found: {original_columns}"
        )

    # --------------------------------------------------------
    # Energy column
    # --------------------------------------------------------

    value_column = None

    for column in original_columns:

        lower = str(column).strip().lower()

        if (
            "kwh" in lower
            or "energy" in lower
            or "consumption" in lower
        ):
            value_column = column
            break

    if value_column is None:
        raise ValueError(
            "Could not identify the load-energy column. "
            f"Columns found: {original_columns}"
        )

    return (
        id_column,
        timestamp_column,
        value_column,
    )


# ============================================================
# LOAD FILE READING
# ============================================================

def read_load_minimal(
    path: Path
) -> Tuple[pd.DataFrame, str, str, str]:

    print_header("READING LONDON LOAD DATA")

    sample = pd.read_csv(
        path,
        nrows=500
    )

    sample.columns = (
        sample.columns
        .astype(str)
        .str.strip()
    )

    id_column, timestamp_column, value_column = (
        detect_load_columns(sample)
    )

    print("Load file:", path)
    print("Household ID column:", id_column)
    print("Timestamp column:", timestamp_column)
    print("Energy column:", value_column)

    frames = []

    use_columns = [
        id_column,
        timestamp_column,
        value_column,
    ]

    for chunk in pd.read_csv(
        path,
        usecols=use_columns,
        chunksize=CHUNK_SIZE
    ):

        chunk.columns = (
            chunk.columns
            .astype(str)
            .str.strip()
        )

        frames.append(chunk)

    load = pd.concat(
        frames,
        ignore_index=True
    )

    load = load.rename(
        columns={
            id_column: "household_id",
            timestamp_column: "timestamp_raw",
            value_column: "load_kwh",
        }
    )

    load["household_id"] = (
        load["household_id"]
        .astype("string")
        .str.strip()
    )

    if load["household_id"].isna().any():
        raise ValueError(
            "Null household IDs were detected."
        )

    load["load_kwh"] = pd.to_numeric(
        load["load_kwh"],
        errors="coerce"
    )

    print("Raw observations:", len(load))
    print(
        "Unique households:",
        load["household_id"].nunique()
    )
    print(
        "Raw null/non-numeric load values:",
        load["load_kwh"].isna().sum()
    )

    return (
        load,
        id_column,
        timestamp_column,
        value_column,
    )


# ============================================================
# LOAD TIMEZONE HANDLING
# ============================================================

def timestamps_have_explicit_timezone(
    series: pd.Series
) -> bool:

    sample = (
        series
        .dropna()
        .astype(str)
        .head(1000)
    )

    if len(sample) == 0:
        return False

    # Matches ISO timestamps ending with:
    # Z
    # +00:00
    # -0100
    pattern = r"(Z|[+-]\d{2}:?\d{2})$"

    return sample.str.contains(
        pattern,
        regex=True
    ).any()


def localize_naive_load_by_household(
    load: pd.DataFrame
) -> pd.DataFrame:
    """
    Localize naive source timestamps to Europe/London.

    This is intentionally done household-by-household so that
    ambiguous DST hours can be inferred from each household's
    chronological sequence.

    nonexistent='raise' is deliberate:
    we do NOT silently shift nonexistent DST timestamps.
    """

    load = load.copy()

    load["timestamp_naive"] = pd.to_datetime(
        load["timestamp_raw"],
        errors="coerce"
    )

    invalid_count = (
        load["timestamp_naive"]
        .isna()
        .sum()
    )

    print(
        "Invalid/unparseable timestamps:",
        invalid_count
    )

    if invalid_count > 0:

        print(
            "\nExample invalid timestamp values:"
        )

        print(
            load.loc[
                load["timestamp_naive"].isna(),
                ["household_id", "timestamp_raw"]
            ]
            .head(20)
        )

        # Explicit removal after reporting.
        load = load.loc[
            load["timestamp_naive"].notna()
        ].copy()

    localized_parts = []

    households = load.groupby(
        "household_id",
        sort=False
    )

    for household_id, group in households:

        group = (
            group
            .copy()
            .sort_values("timestamp_naive")
        )

        naive_index = pd.DatetimeIndex(
            group["timestamp_naive"]
        )

        try:

            localized_index = (
                naive_index.tz_localize(
                    LOAD_TZ,
                    ambiguous="infer",
                    nonexistent="raise"
                )
            )

        except Exception as exc:

            raise RuntimeError(
                "\nUnable to localize London load timestamps "
                f"for household {household_id!r}.\n"
                "The audit intentionally refuses to shift or "
                "guess DST timestamps silently.\n"
                f"Original error: {exc}"
            ) from exc

        group["timestamp_local"] = localized_index

        localized_parts.append(group)

    load = pd.concat(
        localized_parts,
        ignore_index=True
    )

    load = load.drop(
        columns=["timestamp_naive"]
    )

    return load


def normalize_load_timestamps(
    load: pd.DataFrame
) -> pd.DataFrame:

    print_header("NORMALIZING LOAD TIMESTAMPS")

    load = load.copy()

    explicit_timezone = (
        timestamps_have_explicit_timezone(
            load["timestamp_raw"]
        )
    )

    print(
        "Explicit timezone found in source timestamps:",
        explicit_timezone
    )

    if explicit_timezone:

        # Parse to absolute UTC instant first.
        load["timestamp_utc"] = pd.to_datetime(
            load["timestamp_raw"],
            utc=True,
            errors="coerce"
        )

        invalid_count = (
            load["timestamp_utc"]
            .isna()
            .sum()
        )

        print(
            "Invalid/unparseable timestamps:",
            invalid_count
        )

        if invalid_count > 0:

            print(
                load.loc[
                    load["timestamp_utc"].isna(),
                    ["household_id", "timestamp_raw"]
                ]
                .head(20)
            )

            load = load.loc[
                load["timestamp_utc"].notna()
            ].copy()

        load["timestamp_local"] = (
            load["timestamp_utc"]
            .dt.tz_convert(LOAD_TZ)
        )

    else:

        load = (
            localize_naive_load_by_household(
                load
            )
        )

        load["timestamp_utc"] = (
            load["timestamp_local"]
            .dt.tz_convert("UTC")
        )

    load = (
        load
        .sort_values(
            [
                "household_id",
                "timestamp_utc"
            ]
        )
        .reset_index(drop=True)
    )

    print(
        "First load timestamp:",
        load["timestamp_local"].min()
    )

    print(
        "Last load timestamp:",
        load["timestamp_local"].max()
    )

    return load


# ============================================================
# RESOLUTION DETECTION
# ============================================================

def detect_native_resolution_seconds(
    load: pd.DataFrame
) -> int:

    ordered = (
        load[
            [
                "household_id",
                "timestamp_utc"
            ]
        ]
        .sort_values(
            [
                "household_id",
                "timestamp_utc"
            ]
        )
    )

    differences = (
        ordered
        .groupby("household_id")[
            "timestamp_utc"
        ]
        .diff()
        .dt.total_seconds()
    )

    # Ignore duplicates and very large missing-data gaps
    # for resolution detection.
    reasonable = differences[
        (differences > 0)
        &
        (differences <= 7200)
    ]

    if reasonable.empty:
        raise ValueError(
            "Unable to infer native load resolution."
        )

    mode_values = reasonable.mode()

    if mode_values.empty:
        resolution = int(
            reasonable.median()
        )
    else:
        resolution = int(
            mode_values.iloc[0]
        )

    print(
        "Detected native resolution:",
        f"{resolution / 60:.0f} minutes"
    )

    return resolution


# ============================================================
# HOURLY LOAD PREPARATION
# ============================================================

def prepare_hourly_load(
    load: pd.DataFrame
) -> Tuple[pd.DataFrame, Dict[Tuple[str, int], int], int]:

    print_header("PREPARING HOURLY LOAD")

    load = load.copy()

    resolution_seconds = (
        detect_native_resolution_seconds(
            load
        )
    )

    # --------------------------------------------------------
    # Detect source duplicates BEFORE any aggregation.
    # --------------------------------------------------------

    source_duplicate_mask = (
        load.duplicated(
            subset=[
                "household_id",
                "timestamp_utc"
            ],
            keep="first"
        )
    )

    source_duplicate_excess = int(
        source_duplicate_mask.sum()
    )

    print(
        "Source duplicate observations:",
        source_duplicate_excess
    )

    # Count source duplicate excess by household/year.
    duplicate_rows = load.loc[
        source_duplicate_mask,
        [
            "household_id",
            "timestamp_local"
        ]
    ].copy()

    if len(duplicate_rows) > 0:

        duplicate_rows["year"] = (
            duplicate_rows[
                "timestamp_local"
            ]
            .dt.year
        )

        duplicate_by_household_year = (
            duplicate_rows
            .groupby(
                [
                    "household_id",
                    "year"
                ]
            )
            .size()
            .to_dict()
        )

    else:

        duplicate_by_household_year = {}

    # --------------------------------------------------------
    # Already hourly
    # --------------------------------------------------------

    if resolution_seconds == 3600:

        print(
            "Load file is already hourly. "
            "No temporal aggregation applied."
        )

        hourly = load[
            [
                "household_id",
                "timestamp_utc",
                "timestamp_local",
                "load_kwh"
            ]
        ].copy()

    # --------------------------------------------------------
    # 30-minute source
    # --------------------------------------------------------

    elif resolution_seconds == 1800:

        print(
            "30-minute source detected."
        )

        print(
            "Aggregating to hourly interval energy by SUM."
        )

        # Use UTC hour-ending timestamps.
        #
        # UTC is used here deliberately because elapsed-time
        # intervals remain unambiguous across DST transitions.
        load["hour_end_utc"] = (
            load["timestamp_utc"]
            .dt.ceil("h")
        )

        hourly = (
            load
            .groupby(
                [
                    "household_id",
                    "hour_end_utc"
                ],
                as_index=False
            )
            .agg(
                record_count=(
                    "load_kwh",
                    "size"
                ),
                non_null_count=(
                    "load_kwh",
                    "count"
                ),
                load_kwh=(
                    "load_kwh",
                    lambda values:
                        values.sum(
                            min_count=2
                        )
                )
            )
        )

        # Do not silently treat an incomplete hour as valid.
        incomplete_hour_mask = (
            (hourly["record_count"] != 2)
            |
            (hourly["non_null_count"] != 2)
        )

        hourly.loc[
            incomplete_hour_mask,
            "load_kwh"
        ] = pd.NA

        hourly = hourly.rename(
            columns={
                "hour_end_utc":
                "timestamp_utc"
            }
        )

        hourly["timestamp_local"] = (
            hourly["timestamp_utc"]
            .dt.tz_convert(LOAD_TZ)
        )

        print(
            "Hourly intervals created:",
            len(hourly)
        )

        print(
            "Incomplete hourly intervals left as null:",
            int(incomplete_hour_mask.sum())
        )

    else:

        raise ValueError(
            "Unexpected load resolution. "
            f"Detected {resolution_seconds} seconds. "
            "Expected either 1800 or 3600 seconds."
        )

    hourly = (
        hourly
        .sort_values(
            [
                "household_id",
                "timestamp_utc"
            ]
        )
        .reset_index(drop=True)
    )

    return (
        hourly,
        duplicate_by_household_year,
        resolution_seconds,
    )


# ============================================================
# HOUSEHOLD-YEAR AUDIT
# ============================================================

def audit_load_household_years(
    hourly: pd.DataFrame,
    source_duplicate_counts: Dict[
        Tuple[str, int],
        int
    ],
) -> Tuple[
    Dict[int, Dict],
    pd.DataFrame
]:

    print_header("HOUSEHOLD-YEAR LOAD AUDIT")

    households = sorted(
        hourly["household_id"]
        .dropna()
        .unique()
    )

    expected_indexes_utc = {}

    expected_hours = {}

    for year in TARGET_YEARS:

        expected_local = expected_year_index(
            year,
            LOAD_TZ
        )

        expected_indexes_utc[year] = (
            expected_local
            .tz_convert("UTC")
        )

        expected_hours[year] = len(
            expected_local
        )

        print(
            f"{year} expected elapsed hours:",
            expected_hours[year]
        )

    detail_rows = []

    summary = {}

    for year in TARGET_YEARS:

        summary[year] = {
            "complete_households": 0,
            "incomplete_households": 0,
            "missing_observations": 0,
            "duplicate_observations": 0,
            "null_observations": 0,
            "extra_observations": 0,
        }

    grouped = hourly.groupby(
        "household_id",
        sort=False
    )

    for household_id, household in grouped:

        household = household.copy()

        for year in TARGET_YEARS:

            expected_utc = (
                expected_indexes_utc[year]
            )

            start_utc = expected_utc[0]

            # Exclusive endpoint:
            end_utc = (
                pd.Timestamp(
                    f"{year + 1}-01-01 00:00:00",
                    tz=LOAD_TZ
                )
                .tz_convert("UTC")
            )

            household_year = household[
                (
                    household[
                        "timestamp_utc"
                    ] >= start_utc
                )
                &
                (
                    household[
                        "timestamp_utc"
                    ] < end_utc
                )
            ].copy()

            actual_index = pd.DatetimeIndex(
                household_year[
                    "timestamp_utc"
                ]
            )

            unique_index = (
                actual_index.drop_duplicates()
            )

            missing_index = (
                expected_utc.difference(
                    unique_index
                )
            )

            extra_index = (
                unique_index.difference(
                    expected_utc
                )
            )

            source_duplicate_count = int(
                source_duplicate_counts.get(
                    (
                        household_id,
                        year
                    ),
                    0
                )
            )

            null_count = int(
                household_year[
                    "load_kwh"
                ]
                .isna()
                .sum()
            )

            complete = (
                len(unique_index)
                == expected_hours[year]
                and len(missing_index) == 0
                and len(extra_index) == 0
                and source_duplicate_count == 0
                and null_count == 0
            )

            if complete:

                summary[year][
                    "complete_households"
                ] += 1

            else:

                summary[year][
                    "incomplete_households"
                ] += 1

            summary[year][
                "missing_observations"
            ] += len(missing_index)

            summary[year][
                "duplicate_observations"
            ] += source_duplicate_count

            summary[year][
                "null_observations"
            ] += null_count

            summary[year][
                "extra_observations"
            ] += len(extra_index)

            detail_rows.append(
                {
                    "household_id":
                        household_id,

                    "year":
                        year,

                    "first_timestamp":
                        (
                            household_year[
                                "timestamp_local"
                            ].min()
                            if len(
                                household_year
                            ) > 0
                            else None
                        ),

                    "last_timestamp":
                        (
                            household_year[
                                "timestamp_local"
                            ].max()
                            if len(
                                household_year
                            ) > 0
                            else None
                        ),

                    "observation_count":
                        len(household_year),

                    "unique_hour_count":
                        len(unique_index),

                    "expected_observation_count":
                        expected_hours[year],

                    "missing_timestamp_count":
                        len(missing_index),

                    "duplicate_observation_count":
                        source_duplicate_count,

                    "null_demand_count":
                        null_count,

                    "extra_timestamp_count":
                        len(extra_index),

                    "annual_demand_kwh":
                        safe_float(
                            household_year[
                                "load_kwh"
                            ].sum(
                                min_count=1
                            )
                        ),

                    "mean_hourly_demand_kwh":
                        safe_float(
                            household_year[
                                "load_kwh"
                            ].mean()
                        ),

                    "minimum_hourly_demand_kwh":
                        safe_float(
                            household_year[
                                "load_kwh"
                            ].min()
                        ),

                    "maximum_hourly_demand_kwh":
                        safe_float(
                            household_year[
                                "load_kwh"
                            ].max()
                        ),

                    "complete":
                        complete,
                }
            )

    detail = pd.DataFrame(
        detail_rows
    )

    for year in TARGET_YEARS:

        total_households = (
            summary[year][
                "complete_households"
            ]
            +
            summary[year][
                "incomplete_households"
            ]
        )

        if total_households > 0:

            summary[year][
                "percentage_complete"
            ] = (
                100
                *
                summary[year][
                    "complete_households"
                ]
                /
                total_households
            )

        else:

            summary[year][
                "percentage_complete"
            ] = 0.0

        print("\n", year)
        print(
            "Complete households:",
            summary[year][
                "complete_households"
            ]
        )
        print(
            "Incomplete households:",
            summary[year][
                "incomplete_households"
            ]
        )
        print(
            "Percentage complete:",
            round(
                summary[year][
                    "percentage_complete"
                ],
                2
            ),
            "%"
        )
        print(
            "Missing observations:",
            summary[year][
                "missing_observations"
            ]
        )
        print(
            "Duplicate observations:",
            summary[year][
                "duplicate_observations"
            ]
        )
        print(
            "Null observations:",
            summary[year][
                "null_observations"
            ]
        )

    return summary, detail


# ============================================================
# SPANISH MASTER DATASET AUDIT
# ============================================================

def load_master_dataset(
    name: str
) -> Tuple[Path, pd.DataFrame]:

    path = find_existing_file(
        MASTER_FILE_CANDIDATES[name]
    )

    if path is None:

        expected_locations = "\n".join(
            str(item)
            for item in
            MASTER_FILE_CANDIDATES[name]
        )

        raise FileNotFoundError(
            f"Could not locate master dataset {name}.\n"
            f"Checked:\n{expected_locations}"
        )

    df = pd.read_csv(path)

    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
    )

    if "timestamp_utc" not in df.columns:

        raise ValueError(
            f"{name}: timestamp_utc column "
            f"not found in {path}"
        )

    df["timestamp_utc"] = pd.to_datetime(
        df["timestamp_utc"],
        utc=True,
        errors="coerce"
    )

    invalid_timestamp_count = (
        df["timestamp_utc"]
        .isna()
        .sum()
    )

    if invalid_timestamp_count > 0:

        raise ValueError(
            f"{name}: "
            f"{invalid_timestamp_count} invalid "
            "timestamps detected in the master file."
        )

    return path, df


def audit_spanish_dataset_year(
    name: str,
    df: pd.DataFrame,
    year: int,
) -> Dict:

    expected_local = expected_year_index(
        year,
        TARGET_TZ
    )

    expected_utc = (
        expected_local
        .tz_convert("UTC")
    )

    start_utc = expected_utc[0]

    end_utc = (
        pd.Timestamp(
            f"{year + 1}-01-01 00:00:00",
            tz=TARGET_TZ
        )
        .tz_convert("UTC")
    )

    year_df = df[
        (
            df["timestamp_utc"]
            >= start_utc
        )
        &
        (
            df["timestamp_utc"]
            < end_utc
        )
    ].copy()

    actual_index = pd.DatetimeIndex(
        year_df["timestamp_utc"]
    )

    duplicate_count = int(
        actual_index
        .duplicated()
        .sum()
    )

    unique_index = (
        actual_index.drop_duplicates()
    )

    missing = expected_utc.difference(
        unique_index
    )

    extra = unique_index.difference(
        expected_utc
    )

    value_columns = [
        column
        for column in year_df.columns
        if column != "timestamp_utc"
    ]

    null_count = int(
        year_df[
            value_columns
        ]
        .isna()
        .sum()
        .sum()
    )

    complete = (
        len(year_df) == len(expected_utc)
        and duplicate_count == 0
        and len(missing) == 0
        and len(extra) == 0
        and null_count == 0
    )

    return {
        "dataset": name,
        "year": year,
        "expected_hours":
            len(expected_utc),
        "actual_hours":
            len(year_df),
        "missing_count":
            len(missing),
        "extra_count":
            len(extra),
        "duplicate_count":
            duplicate_count,
        "null_count":
            null_count,
        "complete":
            complete,
        "index":
            unique_index,
    }


def audit_spanish_masters():
    print_header(
        "AUDITING SPANISH MASTER DATASETS"
    )

    loaded = {}

    paths = {}

    for name in [
        "OMIE",
        "PVPC_import",
        "PVPC_export",
        "PVGIS",
    ]:

        path, df = load_master_dataset(
            name
        )

        paths[name] = path
        loaded[name] = df

        print(
            f"{name}: {path}"
        )

    audits = {
        year: {}
        for year
        in CANDIDATE_SIMULATION_YEARS
    }

    joint = {}

    for year in CANDIDATE_SIMULATION_YEARS:

        print("\nYEAR", year)

        expected_count = len(
            expected_year_index(
                year,
                TARGET_TZ
            )
        )

        indexes = []

        for name, df in loaded.items():

            audit = (
                audit_spanish_dataset_year(
                    name,
                    df,
                    year
                )
            )

            audits[year][name] = audit

            indexes.append(
                audit["index"]
            )

            print(
                f"{name}: "
                f"rows={audit['actual_hours']}, "
                f"missing={audit['missing_count']}, "
                f"duplicates={audit['duplicate_count']}, "
                f"nulls={audit['null_count']}, "
                f"complete={audit['complete']}"
            )

        # Intersection
        intersection = indexes[0]

        for index in indexes[1:]:

            intersection = (
                intersection.intersection(
                    index
                )
            )

        # Union
        union = indexes[0]

        for index in indexes[1:]:

            union = union.union(index)

        all_complete = all(
            audits[year][name][
                "complete"
            ]
            for name
            in audits[year]
        )

        joint_complete = (
            all_complete
            and len(intersection)
            == expected_count
            and len(union)
            == expected_count
        )

        joint[year] = {
            "expected_hours":
                expected_count,
            "intersection_hours":
                len(intersection),
            "union_hours":
                len(union),
            "complete":
                joint_complete,
        }

        print(
            "Joint intersection:",
            len(intersection)
        )

        print(
            "Joint union:",
            len(union)
        )

        print(
            "Joint Spanish coverage complete:",
            joint_complete
        )

    return audits, joint, paths


# ============================================================
# SIMULATION YEAR DECISION
# ============================================================

def determine_simulation_year(
    load_summary: Dict[int, Dict],
    spanish_joint: Dict[int, Dict],
):

    print_header(
        "SIMULATION CALENDAR DECISION"
    )

    load_usable = {}

    common_year_usable = {}

    for year in (
        CANDIDATE_SIMULATION_YEARS
    ):

        load_usable[year] = (
            load_summary[year][
                "complete_households"
            ]
            >= MINIMUM_COMPLETE_HOUSEHOLDS
        )

        common_year_usable[year] = (
            load_usable[year]
            and spanish_joint[year][
                "complete"
            ]
        )

        print(
            f"{year}: "
            f"complete load households="
            f"{load_summary[year]['complete_households']}, "
            f"load usable="
            f"{load_usable[year]}, "
            f"Spanish inputs complete="
            f"{spanish_joint[year]['complete']}, "
            f"common year usable="
            f"{common_year_usable[year]}"
        )

    usable_years = [
        year
        for year
        in CANDIDATE_SIMULATION_YEARS
        if common_year_usable[year]
    ]

    selected_year = None

    selection_reason = ""

    if len(usable_years) == 1:

        selected_year = usable_years[0]

        selection_reason = (
            f"{selected_year} is the only "
            "candidate year satisfying both "
            "Spanish joint coverage and the "
            f"minimum {MINIMUM_COMPLETE_HOUSEHOLDS} "
            "complete London household profiles."
        )

    elif len(usable_years) == 2:

        # Better load quality wins.
        #
        # Order:
        # 1. more complete households
        # 2. fewer missing observations
        # 3. fewer duplicate observations
        # 4. fewer null observations
        # 5. earlier year as transparent tie-breaker
        #
        def quality_key(year):

            stats = load_summary[year]

            return (
                -stats[
                    "complete_households"
                ],
                stats[
                    "missing_observations"
                ],
                stats[
                    "duplicate_observations"
                ],
                stats[
                    "null_observations"
                ],
                year,
            )

        selected_year = min(
            usable_years,
            key=quality_key
        )

        selection_reason = (
            f"Both 2013 and 2014 satisfy the "
            "common-year criteria. "
            f"{selected_year} was selected using "
            "the load-quality ranking: more complete "
            "households, then fewer missing values, "
            "duplicates and nulls."
        )

    else:

        selection_reason = (
            "Neither 2013 nor 2014 satisfies "
            "the complete common-year criteria. "
            "Representative-year mapping remains "
            "necessary."
        )

    calendar_ready = (
        selected_year is not None
    )

    representative_mapping_required = (
        not calendar_ready
    )

    print(
        "\nSelected simulation year:",
        selected_year
    )

    print(
        "Calendar ready:",
        calendar_ready
    )

    print(
        "Representative mapping required:",
        representative_mapping_required
    )

    print(
        "Selection reason:",
        selection_reason
    )

    return {
        "load_usable":
            load_usable,

        "common_year_usable":
            common_year_usable,

        "selected_year":
            selected_year,

        "calendar_ready":
            calendar_ready,

        "representative_mapping_required":
            representative_mapping_required,

        "selection_reason":
            selection_reason,
    }


# ============================================================
# RUN EXISTING PROJECT AUDIT
# ============================================================

def run_existing_audit():
    print_header(
        "RUNNING EXISTING PHASE 2 AUDIT"
    )

    command = [
        sys.executable,
        "-m",
        "src.preprocessing.audit_datasets",
    ]

    print(
        "Command:",
        " ".join(command)
    )

    process = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    print(
        "\nAUDIT STDOUT"
    )

    print(
        process.stdout
        if process.stdout
        else "(no stdout)"
    )

    if process.stderr:

        print(
            "\nAUDIT STDERR",
            file=sys.stderr
        )

        print(
            process.stderr,
            file=sys.stderr
        )

    print(
        "Audit return code:",
        process.returncode
    )

    return process


# ============================================================
# RUN TESTS
# ============================================================

def run_tests():
    print_header(
        "RUNNING PYTEST"
    )

    command = [
        sys.executable,
        "-m",
        "pytest",
        "tests",
        "-q",
    ]

    print(
        "Command:",
        " ".join(command)
    )

    process = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    print(
        "\nPYTEST STDOUT"
    )

    print(
        process.stdout
        if process.stdout
        else "(no stdout)"
    )

    if process.stderr:

        print(
            "\nPYTEST STDERR",
            file=sys.stderr
        )

        print(
            process.stderr,
            file=sys.stderr
        )

    print(
        "Pytest return code:",
        process.returncode
    )

    return process


# ============================================================
# WRITE LOAD RESULTS
# ============================================================

def write_load_results(
    load_summary: Dict[int, Dict],
    detail: pd.DataFrame,
    overall_start,
    overall_end,
    n_households: int,
    resolution_seconds: int,
):

    print_header(
        "WRITING LOAD AUDIT OUTPUTS"
    )

    # --------------------------------------------------------
    # Household-year detail
    # --------------------------------------------------------

    detail_file = (
        RESULTS
        / "load_household_year_audit.csv"
    )

    detail.to_csv(
        detail_file,
        index=False
    )

    print(
        "Wrote:",
        detail_file
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    summary_file = (
        RESULTS
        / "load_audit_summary.csv"
    )

    with open(
        summary_file,
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.writer(file)

        writer.writerow(
            [
                "load_start",
                "load_end",
                "unique_households",
                "native_resolution_minutes",
            ]
        )

        writer.writerow(
            [
                overall_start,
                overall_end,
                n_households,
                resolution_seconds / 60,
            ]
        )

        writer.writerow([])

        writer.writerow(
            [
                "year",
                "complete_households",
                "incomplete_households",
                "percentage_complete",
                "missing_observations",
                "duplicate_observations",
                "null_observations",
                "extra_observations",
            ]
        )

        for year in TARGET_YEARS:

            stats = load_summary[year]

            writer.writerow(
                [
                    year,
                    stats[
                        "complete_households"
                    ],
                    stats[
                        "incomplete_households"
                    ],
                    stats[
                        "percentage_complete"
                    ],
                    stats[
                        "missing_observations"
                    ],
                    stats[
                        "duplicate_observations"
                    ],
                    stats[
                        "null_observations"
                    ],
                    stats[
                        "extra_observations"
                    ],
                ]
            )

    print(
        "Wrote:",
        summary_file
    )


# ============================================================
# DISPLAY CURRENT YAML
# ============================================================

def show_simulation_calendar_yaml():

    yaml_file = (
        ROOT
        / "config"
        / "simulation_calendar.yaml"
    )

    print_header(
        "CURRENT simulation_calendar.yaml"
    )

    if not yaml_file.exists():

        print(
            "File not found:",
            yaml_file
        )

        return

    print(
        yaml_file.read_text(
            encoding="utf-8"
        )
    )


# ============================================================
# FINAL OUTPUT
# ============================================================

def print_final_output(
    load_summary,
    decision,
    spanish_joint,
    load_start,
    load_end,
    n_households,
    audit_process,
    test_process,
):

    print("\n")
    print("=" * 78)
    print("---FINAL-OUTPUT---")
    print("=" * 78)

    print(
        "1) Load dataset start date:",
        load_start
    )

    print(
        "2) Load dataset end date:",
        load_end
    )

    print(
        "3) Number of unique households:",
        n_households
    )

    counter = 4

    for year in TARGET_YEARS:

        stats = load_summary[year]

        print(
            f"\n{counter}) {year} load audit:"
        )

        print(
            "   complete_households:",
            stats[
                "complete_households"
            ]
        )

        print(
            "   incomplete_households:",
            stats[
                "incomplete_households"
            ]
        )

        print(
            "   percentage_complete:",
            round(
                stats[
                    "percentage_complete"
                ],
                2
            )
        )

        print(
            "   missing_observations:",
            stats[
                "missing_observations"
            ]
        )

        print(
            "   duplicate_observations:",
            stats[
                "duplicate_observations"
            ]
        )

        print(
            "   null_observations:",
            stats[
                "null_observations"
            ]
        )

        counter += 1

    print(
        "\n7) 2013 usable:",
        decision[
            "common_year_usable"
        ][2013]
    )

    print(
        "8) 2014 usable:",
        decision[
            "common_year_usable"
        ][2014]
    )

    print(
        "9) Selected simulation year:",
        decision[
            "selected_year"
        ]
    )

    print(
        "10) calendar_ready:",
        decision[
            "calendar_ready"
        ]
    )

    print(
        "11) Representative-year mapping required:",
        decision[
            "representative_mapping_required"
        ]
    )

    selected_year = (
        decision[
            "selected_year"
        ]
    )

    if selected_year is not None:

        joint = (
            spanish_joint[
                selected_year
            ]
        )

        print(
            "12) Final joint Spanish timestamp audit:"
        )

        print(
            "    expected_hours:",
            joint[
                "expected_hours"
            ]
        )

        print(
            "    intersection_hours:",
            joint[
                "intersection_hours"
            ]
        )

        print(
            "    union_hours:",
            joint[
                "union_hours"
            ]
        )

        print(
            "    complete:",
            joint[
                "complete"
            ]
        )

    else:

        print(
            "12) Final joint Spanish timestamp audit:"
        )

        print(
            "    No final year selected."
        )

    print(
        "13) pytest result:",
        (
            "PASS"
            if test_process.returncode == 0
            else "FAIL"
        ),
        f"(return code {test_process.returncode})"
    )

    print(
        "\nExisting audit return code:",
        audit_process.returncode
    )

    print(
        "\nSelection reason:"
    )

    print(
        decision[
            "selection_reason"
        ]
    )

    print("\n---END---")


# ============================================================
# MAIN
# ============================================================

def main():

    print_header(
        "PHASE 2 LOAD + CALENDAR AUDIT"
    )

    print(
        "Repository root:",
        ROOT
    )

    # --------------------------------------------------------
    # Check load file
    # --------------------------------------------------------

    if not RAW_LOAD.exists():

        raise FileNotFoundError(
            f"Load file not found:\n{RAW_LOAD}"
        )

    # --------------------------------------------------------
    # Read minimal load columns
    # --------------------------------------------------------

    load, _, _, _ = (
        read_load_minimal(
            RAW_LOAD
        )
    )

    # --------------------------------------------------------
    # Timestamp normalization
    # --------------------------------------------------------

    load = normalize_load_timestamps(
        load
    )

    # --------------------------------------------------------
    # Hourly preparation
    # --------------------------------------------------------

    (
        hourly_load,
        source_duplicate_counts,
        resolution_seconds,
    ) = prepare_hourly_load(
        load
    )

    load_start = (
        hourly_load[
            "timestamp_local"
        ]
        .min()
    )

    load_end = (
        hourly_load[
            "timestamp_local"
        ]
        .max()
    )

    n_households = int(
        hourly_load[
            "household_id"
        ]
        .nunique()
    )

    # --------------------------------------------------------
    # Household-year audit
    # --------------------------------------------------------

    (
        load_summary,
        load_detail,
    ) = audit_load_household_years(
        hourly_load,
        source_duplicate_counts,
    )

    # --------------------------------------------------------
    # Write independent load audit outputs
    # --------------------------------------------------------

    write_load_results(
        load_summary=load_summary,
        detail=load_detail,
        overall_start=load_start,
        overall_end=load_end,
        n_households=n_households,
        resolution_seconds=resolution_seconds,
    )

    # --------------------------------------------------------
    # Spanish master datasets
    # --------------------------------------------------------

    (
        spanish_audits,
        spanish_joint,
        spanish_paths,
    ) = audit_spanish_masters()

    # --------------------------------------------------------
    # Independent common-year decision
    # --------------------------------------------------------

    decision = determine_simulation_year(
        load_summary,
        spanish_joint,
    )

    # --------------------------------------------------------
    # Run existing Phase 2 audit
    # --------------------------------------------------------

    audit_process = (
        run_existing_audit()
    )

    # --------------------------------------------------------
    # Run tests
    # --------------------------------------------------------

    test_process = (
        run_tests()
    )

    # --------------------------------------------------------
    # Display YAML produced by project audit
    # --------------------------------------------------------

    show_simulation_calendar_yaml()

    # --------------------------------------------------------
    # Final concise output
    # --------------------------------------------------------

    print_final_output(
        load_summary=load_summary,
        decision=decision,
        spanish_joint=spanish_joint,
        load_start=load_start,
        load_end=load_end,
        n_households=n_households,
        audit_process=audit_process,
        test_process=test_process,
    )


if __name__ == "__main__":
    main()