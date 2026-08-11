"""
Phase 2 dataset audit and simulation-calendar decision.

Final Phase-2 configuration:
- Simulation year: 2013
- Final load dataset:
    data/processed/load/load_2013_30_households.csv
- Load households: 30
- Load source timestamps: GMT/UTC
- Load behavioural timezone: Europe/London
- Spanish target timezone: Europe/Madrid
- Spanish inputs:
    OMIE
    PVPC import
    PVPC export
    PVGIS

This audit:
1. Audits the FINAL processed 30-household load dataset.
2. Validates household completeness for 2013.
3. Validates reconstruction metadata.
4. Audits all Spanish 2013 master datasets.
5. Performs the joint Spanish timestamp audit.
6. Writes the final Phase-2 CSV, Markdown and YAML outputs.

Important:
- Raw source data are never modified.
- Reconstructed load observations remain explicitly flagged.
- No interpolation or filling is performed by this audit.
"""

from pathlib import Path
import csv

import pandas as pd
import yaml


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

RESULTS_DIR = ROOT / "results"
CONFIG_DIR = ROOT / "config"

RESULTS_DIR.mkdir(
    parents=True,
    exist_ok=True
)

CONFIG_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# FINAL LOAD DATASET
# ============================================================

FINAL_LOAD_FILE = (
    PROCESSED_DIR
    / "load"
    / "load_2013_30_households.csv"
)

LOAD_METADATA_DIR = (
    PROCESSED_DIR
    / "load"
    / "metadata"
)

SELECTED_HOUSEHOLDS_FILE = (
    LOAD_METADATA_DIR
    / "selected_households_2013.csv"
)

RECONSTRUCTION_LOG_FILE = (
    LOAD_METADATA_DIR
    / "load_reconstruction_log_2013.csv"
)


# ============================================================
# SPANISH MASTER FILES
# ============================================================

MASTER_FILE_CANDIDATES = {
    "OMIE": [
        PROCESSED_DIR / "omie.csv",
        PROCESSED_DIR / "omie" / "omie.csv",
        RAW_DIR / "omie" / "omie.csv",
    ],

    "PVPC_import": [
        PROCESSED_DIR / "pvpc_import.csv",
        PROCESSED_DIR / "pvpc_import" / "pvpc_import.csv",
        RAW_DIR / "pvpc_import" / "pvpc_import.csv",
    ],

    "PVPC_export": [
        PROCESSED_DIR / "pvpc_export.csv",
        PROCESSED_DIR / "pvpc_export" / "pvpc_export.csv",
        RAW_DIR / "pvpc_export" / "pvpc_export.csv",
    ],

    "PVGIS": [
        PROCESSED_DIR / "pvgis.csv",
        PROCESSED_DIR / "pvgis" / "pvgis.csv",
        RAW_DIR / "pvgis" / "pvgis.csv",
    ],
}


# ============================================================
# CONFIGURATION
# ============================================================

SIMULATION_YEAR = 2013

LOAD_SOURCE_TZ = "UTC"
LOAD_LOCAL_TZ = "Europe/London"
TARGET_TZ = "Europe/Madrid"

EXPECTED_HOURS = 8760
EXPECTED_HOUSEHOLDS = 30
EXPECTED_LOAD_ROWS = (
    EXPECTED_HOUSEHOLDS
    * EXPECTED_HOURS
)

PRICE_UNIT = "EUR/MWh"


# ============================================================
# REQUIRED MODEL COLUMNS
# ============================================================

SPANISH_VALUE_COLUMNS = {
    "OMIE": [
        "marginal_es_eur_mwh",
    ],

    "PVPC_import": [
        "price_eur_mwh",
    ],

    "PVPC_export": [
        "price_eur_mwh",
    ],

    "PVGIS": [
        "pv_power_w_per_1kwp",
        "pv_generation_kwh_per_1kwp",
    ],
}


# ============================================================
# GENERAL HELPERS
# ============================================================

def print_header(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def expected_year_index(
    year,
    timezone,
):
    """
    Complete timezone-aware hourly local calendar.
    """

    start = pd.Timestamp(
        f"{year}-01-01 00:00:00",
        tz=timezone,
    )

    end = pd.Timestamp(
        f"{year + 1}-01-01 00:00:00",
        tz=timezone,
    )

    return pd.date_range(
        start=start,
        end=end,
        freq="h",
        inclusive="left",
    )


def find_existing_file(candidates):

    for path in candidates:

        if path.exists():
            return path

    return None


def normalize_boolean(series):
    """
    Robustly convert CSV boolean-like values to bool.
    """

    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)

    return (
        series
        .astype(str)
        .str.strip()
        .str.lower()
        .map(
            {
                "true": True,
                "false": False,
                "1": True,
                "0": False,
            }
        )
        .fillna(False)
        .astype(bool)
    )


# ============================================================
# AUDIT FINAL PROCESSED LOAD DATASET
# ============================================================

def audit_final_load():

    print_header(
        "AUDITING FINAL PROCESSED 2013 LOAD DATASET"
    )

    if not FINAL_LOAD_FILE.exists():

        raise FileNotFoundError(
            "Final processed load dataset not found:\n"
            f"{FINAL_LOAD_FILE}"
        )

    load = pd.read_csv(
        FINAL_LOAD_FILE,
        dtype={
            "household_id": "string",
            "reconstruction_method": "string",
        },
        low_memory=False,
    )

    load.columns = (
        load.columns
        .astype(str)
        .str.strip()
    )

    required_columns = [
        "household_id",
        "timestamp_utc",
        "timestamp_local",
        "load_kwh",
        "was_reconstructed",
        "reconstruction_method",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in load.columns
    ]

    if missing_columns:

        raise ValueError(
            "Final load dataset is missing required "
            f"columns: {missing_columns}"
        )

    # --------------------------------------------------------
    # Parse timestamps
    # --------------------------------------------------------

    load["timestamp_utc"] = pd.to_datetime(
        load["timestamp_utc"],
        utc=True,
        errors="coerce",
    )

    invalid_utc = int(
        load["timestamp_utc"]
        .isna()
        .sum()
    )

    # Rebuild London-local timestamp directly from UTC.
    # This avoids relying on CSV timezone parsing.
    load["timestamp_local"] = (
        load["timestamp_utc"]
        .dt.tz_convert(
            LOAD_LOCAL_TZ
        )
    )

    # --------------------------------------------------------
    # Numeric load
    # --------------------------------------------------------

    load["load_kwh"] = pd.to_numeric(
        load["load_kwh"],
        errors="coerce",
    )

    null_load = int(
        load["load_kwh"]
        .isna()
        .sum()
    )

    negative_load = int(
        (
            load["load_kwh"] < 0
        )
        .sum()
    )

    # --------------------------------------------------------
    # Reconstruction flag
    # --------------------------------------------------------

    load["was_reconstructed"] = (
        normalize_boolean(
            load["was_reconstructed"]
        )
    )

    reconstructed_hours = int(
        load[
            "was_reconstructed"
        ]
        .sum()
    )

    reconstructed_without_method = int(
        (
            load["was_reconstructed"]
            &
            load[
                "reconstruction_method"
            ].isna()
        )
        .sum()
    )

    reconstruction_share = (
        reconstructed_hours
        / len(load)
        * 100
        if len(load) > 0
        else 0.0
    )

    # --------------------------------------------------------
    # General structure
    # --------------------------------------------------------

    household_count = int(
        load[
            "household_id"
        ]
        .nunique()
    )

    duplicate_household_hours = int(
        load.duplicated(
            subset=[
                "household_id",
                "timestamp_utc",
            ],
            keep=False,
        )
        .sum()
    )

    # --------------------------------------------------------
    # Expected 2013 London calendar
    # --------------------------------------------------------

    expected_local = expected_year_index(
        SIMULATION_YEAR,
        LOAD_LOCAL_TZ,
    )

    expected_utc = (
        expected_local
        .tz_convert("UTC")
    )

    household_rows = []

    total_missing = 0
    total_extra = 0
    complete_households = 0

    for household_id, household in (
        load.groupby(
            "household_id",
            sort=True,
        )
    ):

        actual_index = pd.DatetimeIndex(
            household[
                "timestamp_utc"
            ]
        )

        unique_index = (
            actual_index
            .drop_duplicates()
            .sort_values()
        )

        missing = (
            expected_utc
            .difference(
                unique_index
            )
        )

        extra = (
            unique_index
            .difference(
                expected_utc
            )
        )

        duplicates = int(
            actual_index
            .duplicated()
            .sum()
        )

        nulls = int(
            household[
                "load_kwh"
            ]
            .isna()
            .sum()
        )

        reconstructed = int(
            household[
                "was_reconstructed"
            ]
            .sum()
        )

        complete = (
            len(household) == EXPECTED_HOURS
            and len(unique_index)
            == EXPECTED_HOURS
            and len(missing) == 0
            and len(extra) == 0
            and duplicates == 0
            and nulls == 0
        )

        if complete:
            complete_households += 1

        total_missing += len(missing)
        total_extra += len(extra)

        household_rows.append(
            {
                "household_id":
                    household_id,

                "observation_count":
                    len(household),

                "unique_hour_count":
                    len(unique_index),

                "expected_hours":
                    EXPECTED_HOURS,

                "missing_hours":
                    len(missing),

                "extra_hours":
                    len(extra),

                "duplicates":
                    duplicates,

                "nulls":
                    nulls,

                "reconstructed_hours":
                    reconstructed,

                "annual_demand_kwh":
                    float(
                        household[
                            "load_kwh"
                        ].sum()
                    ),

                "complete":
                    complete,
            }
        )

    household_audit = pd.DataFrame(
        household_rows
    )

    # --------------------------------------------------------
    # Final load completeness
    # --------------------------------------------------------

    load_complete = (
        len(load)
        == EXPECTED_LOAD_ROWS
        and household_count
        == EXPECTED_HOUSEHOLDS
        and complete_households
        == EXPECTED_HOUSEHOLDS
        and total_missing == 0
        and total_extra == 0
        and duplicate_household_hours == 0
        and invalid_utc == 0
        and null_load == 0
        and negative_load == 0
        and reconstructed_without_method == 0
    )

    print(
        "File:",
        FINAL_LOAD_FILE
    )

    print(
        "Households:",
        household_count
    )

    print(
        "Complete households:",
        complete_households
    )

    print(
        "Rows:",
        len(load)
    )

    print(
        "Expected rows:",
        EXPECTED_LOAD_ROWS
    )

    print(
        "Missing household-hours:",
        total_missing
    )

    print(
        "Duplicate household-hours:",
        duplicate_household_hours
    )

    print(
        "Null load values:",
        null_load
    )

    print(
        "Reconstructed hours:",
        reconstructed_hours
    )

    print(
        "Reconstruction share:",
        round(
            reconstruction_share,
            4,
        ),
        "%"
    )

    print(
        "Load complete:",
        load_complete
    )

    return {
        "data":
            load,

        "household_audit":
            household_audit,

        "source_file":
            str(
                FINAL_LOAD_FILE.relative_to(
                    ROOT
                )
            ),

        "start":
            (
                load[
                    "timestamp_utc"
                ].min()
            ),

        "end":
            (
                load[
                    "timestamp_utc"
                ].max()
            ),

        "observation_count":
            len(load),

        "expected_observation_count":
            EXPECTED_LOAD_ROWS,

        "household_count":
            household_count,

        "complete_households":
            complete_households,

        "missing_timestamps":
            total_missing,

        "extra_timestamps":
            total_extra,

        "duplicate_timestamps":
            duplicate_household_hours,

        "null_values":
            null_load,

        "negative_values":
            negative_load,

        "reconstructed_hours":
            reconstructed_hours,

        "reconstruction_share_percent":
            reconstruction_share,

        "reconstructed_without_method":
            reconstructed_without_method,

        "complete":
            load_complete,
    }


# ============================================================
# AUDIT LOAD METADATA
# ============================================================

def audit_load_metadata(
    load_result,
):

    print_header(
        "AUDITING LOAD SELECTION AND RECONSTRUCTION METADATA"
    )

    selection_valid = False
    reconstruction_log_valid = False

    # --------------------------------------------------------
    # Selected household register
    # --------------------------------------------------------

    if SELECTED_HOUSEHOLDS_FILE.exists():

        selected = pd.read_csv(
            SELECTED_HOUSEHOLDS_FILE
        )

        if "selected" in selected.columns:

            selected["selected"] = (
                normalize_boolean(
                    selected["selected"]
                )
            )

            selected = selected[
                selected["selected"]
            ].copy()

        selected_ids = set(
            selected[
                "household_id"
            ].astype(str)
        )

        load_ids = set(
            load_result[
                "data"
            ][
                "household_id"
            ].astype(str)
        )

        reconstructed_metadata_total = int(
            pd.to_numeric(
                selected[
                    "reconstructed_hours"
                ],
                errors="coerce",
            )
            .fillna(0)
            .sum()
        )

        selection_valid = (
            len(selected) == 30
            and selected_ids == load_ids
            and reconstructed_metadata_total
            == load_result[
                "reconstructed_hours"
            ]
        )

    else:

        selected = None

    # --------------------------------------------------------
    # Reconstruction log
    # --------------------------------------------------------

    if RECONSTRUCTION_LOG_FILE.exists():

        reconstruction_log = pd.read_csv(
            RECONSTRUCTION_LOG_FILE
        )

        reconstruction_log_valid = (
            len(reconstruction_log)
            == load_result[
                "reconstructed_hours"
            ]
        )

        if (
            "reconstruction_method"
            in reconstruction_log.columns
        ):

            reconstruction_log_valid = (
                reconstruction_log_valid
                and
                reconstruction_log[
                    "reconstruction_method"
                ]
                .notna()
                .all()
            )

    else:

        reconstruction_log = None

    metadata_valid = (
        selection_valid
        and reconstruction_log_valid
    )

    print(
        "Selection register valid:",
        selection_valid
    )

    print(
        "Reconstruction log valid:",
        reconstruction_log_valid
    )

    print(
        "Metadata valid:",
        metadata_valid
    )

    return {
        "selection_valid":
            selection_valid,

        "reconstruction_log_valid":
            reconstruction_log_valid,

        "metadata_valid":
            metadata_valid,
    }


# ============================================================
# LOAD SPANISH MASTER DATASET
# ============================================================

def load_spanish_master(name):

    path = find_existing_file(
        MASTER_FILE_CANDIDATES[
            name
        ]
    )

    if path is None:

        checked = "\n".join(
            str(path)
            for path
            in MASTER_FILE_CANDIDATES[
                name
            ]
        )

        raise FileNotFoundError(
            f"{name} master dataset "
            "could not be found.\n"
            f"Checked:\n{checked}"
        )

    df = pd.read_csv(
        path
    )

    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
    )

    if "timestamp_utc" not in df.columns:

        raise ValueError(
            f"{name}: timestamp_utc "
            f"not found in {path}"
        )

    df[
        "timestamp_utc"
    ] = pd.to_datetime(
        df[
            "timestamp_utc"
        ],
        utc=True,
        errors="coerce",
    )

    invalid_timestamps = int(
        df[
            "timestamp_utc"
        ]
        .isna()
        .sum()
    )

    if invalid_timestamps > 0:

        raise ValueError(
            f"{name}: "
            f"{invalid_timestamps} invalid "
            "timestamps found."
        )

    return path, df


# ============================================================
# AUDIT SPANISH DATASET FOR 2013
# ============================================================

def audit_spanish_dataset(
    name,
    path,
    df,
):

    expected_local = expected_year_index(
        SIMULATION_YEAR,
        TARGET_TZ,
    )

    expected_utc = (
        expected_local
        .tz_convert("UTC")
    )

    start_utc = expected_utc[0]

    end_utc = (
        pd.Timestamp(
            f"{SIMULATION_YEAR + 1}"
            "-01-01 00:00:00",
            tz=TARGET_TZ,
        )
        .tz_convert("UTC")
    )

    year_df = df[
        (
            df[
                "timestamp_utc"
            ] >= start_utc
        )
        &
        (
            df[
                "timestamp_utc"
            ] < end_utc
        )
    ].copy()

    actual_index = pd.DatetimeIndex(
        year_df[
            "timestamp_utc"
        ]
    )

    duplicates = int(
        actual_index
        .duplicated()
        .sum()
    )

    unique_index = (
        actual_index
        .drop_duplicates()
        .sort_values()
    )

    missing = (
        expected_utc
        .difference(
            unique_index
        )
    )

    extra = (
        unique_index
        .difference(
            expected_utc
        )
    )

    required_values = (
        SPANISH_VALUE_COLUMNS[
            name
        ]
    )

    missing_columns = [
        column
        for column
        in required_values
        if column
        not in year_df.columns
    ]

    if missing_columns:

        raise ValueError(
            f"{name}: required column(s) "
            f"missing: {missing_columns}"
        )

    for column in required_values:

        year_df[column] = (
            pd.to_numeric(
                year_df[column],
                errors="coerce",
            )
        )

    null_values = int(
        year_df[
            required_values
        ]
        .isna()
        .sum()
        .sum()
    )

    complete = (
        len(year_df)
        == EXPECTED_HOURS
        and len(unique_index)
        == EXPECTED_HOURS
        and len(missing) == 0
        and len(extra) == 0
        and duplicates == 0
        and null_values == 0
    )

    print(
        f"{name}: "
        f"rows={len(year_df)}, "
        f"missing={len(missing)}, "
        f"extra={len(extra)}, "
        f"duplicates={duplicates}, "
        f"nulls={null_values}, "
        f"complete={complete}"
    )

    return {
        "dataset":
            name,

        "path":
            path,

        "source_file":
            str(
                path.relative_to(
                    ROOT
                )
            ),

        "start":
            (
                year_df[
                    "timestamp_utc"
                ].min()
            ),

        "end":
            (
                year_df[
                    "timestamp_utc"
                ].max()
            ),

        "observation_count":
            len(year_df),

        "expected_observation_count":
            EXPECTED_HOURS,

        "missing_timestamps":
            len(missing),

        "extra_timestamps":
            len(extra),

        "duplicate_timestamps":
            duplicates,

        "null_values":
            null_values,

        "complete":
            complete,

        "index":
            unique_index,
    }


# ============================================================
# AUDIT ALL SPANISH MASTER DATASETS
# ============================================================

def audit_spanish_inputs():

    print_header(
        "AUDITING 2013 SPANISH MASTER DATASETS"
    )

    results = {}

    for name in [
        "OMIE",
        "PVPC_import",
        "PVPC_export",
        "PVGIS",
    ]:

        path, df = (
            load_spanish_master(
                name
            )
        )

        results[name] = (
            audit_spanish_dataset(
                name,
                path,
                df,
            )
        )

    # --------------------------------------------------------
    # Joint timestamp intersection and union
    # --------------------------------------------------------

    indexes = [
        results[name][
            "index"
        ]
        for name
        in results
    ]

    intersection = indexes[0]

    for index in indexes[1:]:

        intersection = (
            intersection
            .intersection(index)
        )

    union = indexes[0]

    for index in indexes[1:]:

        union = (
            union
            .union(index)
        )

    all_complete = all(
        result["complete"]
        for result
        in results.values()
    )

    joint_complete = (
        all_complete
        and len(intersection)
        == EXPECTED_HOURS
        and len(union)
        == EXPECTED_HOURS
    )

    print(
        "\nJoint Spanish intersection:",
        len(intersection)
    )

    print(
        "Joint Spanish union:",
        len(union)
    )

    print(
        "Joint Spanish coverage complete:",
        joint_complete
    )

    return {
        "datasets":
            results,

        "intersection_hours":
            len(intersection),

        "union_hours":
            len(union),

        "complete":
            joint_complete,
    }


# ============================================================
# BUILD MACHINE-READABLE AUDIT TABLE
# ============================================================

def build_dataset_audit_rows(
    load_result,
    spanish_result,
):

    rows = []

    # --------------------------------------------------------
    # Final processed load
    # --------------------------------------------------------

    rows.append(
        {
            "dataset":
                "load",

            "provider":
                "Low Carbon London / UK Power Networks",

            "source_file":
                load_result[
                    "source_file"
                ],

            "year":
                SIMULATION_YEAR,

            "start_timestamp":
                load_result[
                    "start"
                ].isoformat(),

            "end_timestamp":
                load_result[
                    "end"
                ].isoformat(),

            "native_resolution":
                "1 hour",

            "observation_count":
                load_result[
                    "observation_count"
                ],

            "expected_observation_count":
                load_result[
                    "expected_observation_count"
                ],

            "timezone":
                (
                    "UTC source; "
                    "Europe/London behavioural clock"
                ),

            "unit":
                "kWh per household-hour",

            "missing_timestamps":
                load_result[
                    "missing_timestamps"
                ],

            "duplicate_timestamps":
                load_result[
                    "duplicate_timestamps"
                ],

            "null_values":
                load_result[
                    "null_values"
                ],

            "complete":
                load_result[
                    "complete"
                ],

            "final_role":
                "residential demand",

            "notes":
                (
                    f"30 selected households; "
                    f"{load_result['reconstructed_hours']} "
                    "hours explicitly reconstructed "
                    f"({load_result['reconstruction_share_percent']:.4f}% "
                    "of household-hour observations)."
                ),
        }
    )

    # --------------------------------------------------------
    # Spanish datasets
    # --------------------------------------------------------

    provider_map = {
        "OMIE":
            "OMIE",

        "PVPC_import":
            "Red Eléctrica de España / ESIOS",

        "PVPC_export":
            "Red Eléctrica de España / ESIOS",

        "PVGIS":
            "European Commission JRC PVGIS",
    }

    role_map = {
        "OMIE":
            "dispatch price signal",

        "PVPC_import":
            "retail import price",

        "PVPC_export":
            "surplus compensation price",

        "PVGIS":
            "PV generation profile",
    }

    unit_map = {
        "OMIE":
            "EUR/MWh",

        "PVPC_import":
            "EUR/MWh",

        "PVPC_export":
            "EUR/MWh",

        "PVGIS":
            "W/kWp and kWh/kWp per hour",
    }

    for name, result in (
        spanish_result[
            "datasets"
        ].items()
    ):

        rows.append(
            {
                "dataset":
                    name,

                "provider":
                    provider_map[
                        name
                    ],

                "source_file":
                    result[
                        "source_file"
                    ],

                "year":
                    SIMULATION_YEAR,

                "start_timestamp":
                    result[
                        "start"
                    ].isoformat(),

                "end_timestamp":
                    result[
                        "end"
                    ].isoformat(),

                "native_resolution":
                    "1 hour",

                "observation_count":
                    result[
                        "observation_count"
                    ],

                "expected_observation_count":
                    result[
                        "expected_observation_count"
                    ],

                "timezone":
                    "UTC storage; Europe/Madrid calendar",

                "unit":
                    unit_map[
                        name
                    ],

                "missing_timestamps":
                    result[
                        "missing_timestamps"
                    ],

                "duplicate_timestamps":
                    result[
                        "duplicate_timestamps"
                    ],

                "null_values":
                    result[
                        "null_values"
                    ],

                "complete":
                    result[
                        "complete"
                    ],

                "final_role":
                    role_map[
                        name
                    ],

                "notes":
                    "",
            }
        )

    return rows


# ============================================================
# WRITE OUTPUTS
# ============================================================

def write_outputs(
    load_result,
    metadata_result,
    spanish_result,
):

    audit_rows = (
        build_dataset_audit_rows(
            load_result,
            spanish_result,
        )
    )

    # --------------------------------------------------------
    # Final decision
    # --------------------------------------------------------

    calendar_ready = (
        load_result[
            "complete"
        ]
        and metadata_result[
            "metadata_valid"
        ]
        and spanish_result[
            "complete"
        ]
    )

    representative_mapping_required = False

    if calendar_ready:

        selection_reason = (
            "2013 selected as the common simulation year. "
            "The final processed 30-household load dataset "
            "contains 8,760 hourly observations per household, "
            "and OMIE, PVPC import, PVPC export and PVGIS all "
            "provide complete 2013 hourly coverage."
        )

    else:

        selection_reason = (
            "2013 inputs failed one or more final Phase-2 "
            "validation checks. Calendar must not be declared "
            "ready until all checks pass."
        )

    # --------------------------------------------------------
    # CSV
    # --------------------------------------------------------

    csv_path = (
        RESULTS_DIR
        / "dataset_audit.csv"
    )

    fieldnames = [
        "dataset",
        "provider",
        "source_file",
        "year",
        "start_timestamp",
        "end_timestamp",
        "native_resolution",
        "observation_count",
        "expected_observation_count",
        "timezone",
        "unit",
        "missing_timestamps",
        "duplicate_timestamps",
        "null_values",
        "complete",
        "final_role",
        "notes",
    ]

    with open(
        csv_path,
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        writer.writerows(
            audit_rows
        )

    # --------------------------------------------------------
    # Household audit
    # --------------------------------------------------------

    household_path = (
        RESULTS_DIR
        / "load_household_year_audit.csv"
    )

    load_result[
        "household_audit"
    ].to_csv(
        household_path,
        index=False,
    )

    # --------------------------------------------------------
    # Markdown dataset audit
    # --------------------------------------------------------

    md_path = (
        RESULTS_DIR
        / "dataset_audit.md"
    )

    with open(
        md_path,
        "w",
        encoding="utf-8",
    ) as file:

        file.write(
            "# Phase 2 Dataset Audit\n\n"
        )

        file.write(
            "## Executive summary\n\n"
        )

        file.write(
            f"- Simulation year: {SIMULATION_YEAR}\n"
        )

        file.write(
            f"- Final load households: "
            f"{load_result['household_count']}\n"
        )

        file.write(
            f"- Complete load households: "
            f"{load_result['complete_households']}\n"
        )

        file.write(
            f"- Final load rows: "
            f"{load_result['observation_count']}\n"
        )

        file.write(
            f"- Reconstructed household-hours: "
            f"{load_result['reconstructed_hours']}\n"
        )

        file.write(
            f"- Reconstruction share: "
            f"{load_result['reconstruction_share_percent']:.4f}%\n"
        )

        file.write(
            f"- Load metadata valid: "
            f"{metadata_result['metadata_valid']}\n"
        )

        file.write(
            f"- Joint Spanish coverage complete: "
            f"{spanish_result['complete']}\n"
        )

        file.write(
            f"- Calendar ready: "
            f"{calendar_ready}\n\n"
        )

        file.write(
            "## Dataset table\n\n"
        )

        file.write(
            "|Dataset|Year|Observed|Expected|"
            "Missing|Duplicates|Nulls|Complete|\n"
        )

        file.write(
            "|-|-:|-:|-:|-:|-:|-:|-|\n"
        )

        for row in audit_rows:

            file.write(
                f"|{row['dataset']}|"
                f"{row['year']}|"
                f"{row['observation_count']}|"
                f"{row['expected_observation_count']}|"
                f"{row['missing_timestamps']}|"
                f"{row['duplicate_timestamps']}|"
                f"{row['null_values']}|"
                f"{row['complete']}|\n"
            )

        file.write(
            "\n## Load reconstruction note\n\n"
        )

        file.write(
            "The final 2013 load dataset contains 30 household "
            "profiles. Originally missing observations were "
            "reconstructed explicitly during preprocessing and "
            "remain identified by the `was_reconstructed` and "
            "`reconstruction_method` fields. No additional "
            "imputation is performed by this audit.\n"
        )

        file.write(
            "\n## Timezone note\n\n"
        )

        file.write(
            "Low Carbon London source timestamps are interpreted "
            "as GMT/UTC. Europe/London is retained as the "
            "behavioural local-clock reference. Spanish market "
            "and PV data are evaluated against the Europe/Madrid "
            "2013 calendar and stored in UTC.\n"
        )

    # --------------------------------------------------------
    # YAML
    # --------------------------------------------------------

    yaml_path = (
        CONFIG_DIR
        / "simulation_calendar.yaml"
    )

    config = {
        "timezone":
            TARGET_TZ,

        "candidate_years": [
            SIMULATION_YEAR,
        ],

        "selected_year":
            (
                SIMULATION_YEAR
                if calendar_ready
                else None
            ),

        "calendar_ready":
            bool(
                calendar_ready
            ),

        "approach":
            "common_year",

        "selection_reason":
            selection_reason,

        "price_unit":
            PRICE_UNIT,

        "load_source_timezone":
            LOAD_SOURCE_TZ,

        "load_behavior_timezone":
            LOAD_LOCAL_TZ,

        "target_timezone":
            TARGET_TZ,

        "expected_hours":
            EXPECTED_HOURS,

        "load_households":
            load_result[
                "household_count"
            ],

        "load_complete_households":
            load_result[
                "complete_households"
            ],

        "load_total_rows":
            load_result[
                "observation_count"
            ],

        "load_expected_rows":
            EXPECTED_LOAD_ROWS,

        "load_complete":
            bool(
                load_result[
                    "complete"
                ]
            ),

        "load_reconstructed_hours":
            load_result[
                "reconstructed_hours"
            ],

        "load_reconstruction_share_percent":
            round(
                load_result[
                    "reconstruction_share_percent"
                ],
                6,
            ),

        "load_metadata_valid":
            bool(
                metadata_result[
                    "metadata_valid"
                ]
            ),

        "joint_price_coverage_complete":
            bool(
                all(
                    spanish_result[
                        "datasets"
                    ][name][
                        "complete"
                    ]
                    for name in [
                        "OMIE",
                        "PVPC_import",
                        "PVPC_export",
                    ]
                )
            ),

        "joint_spanish_inputs_complete":
            bool(
                spanish_result[
                    "complete"
                ]
            ),

        "joint_spanish_intersection_hours":
            spanish_result[
                "intersection_hours"
            ],

        "joint_spanish_union_hours":
            spanish_result[
                "union_hours"
            ],

        "representative_year_mapping_required":
            representative_mapping_required,

        "load_alignment_note":
            (
                "London demand is a behavioural proxy. "
                "Source timestamps are GMT/UTC and local "
                "behaviour is interpreted in Europe/London; "
                "the final simulation uses the 2013 "
                "Europe/Madrid calendar."
            ),
    }

    with open(
        yaml_path,
        "w",
        encoding="utf-8",
    ) as file:

        yaml.safe_dump(
            config,
            file,
            sort_keys=False,
            allow_unicode=True,
        )

    # --------------------------------------------------------
    # Decision Markdown
    # --------------------------------------------------------

    decision_path = (
        RESULTS_DIR
        / "simulation_calendar_decision.md"
    )

    with open(
        decision_path,
        "w",
        encoding="utf-8",
    ) as file:

        file.write(
            "# Simulation Calendar Decision\n\n"
        )

        file.write(
            f"- Selected year: "
            f"{SIMULATION_YEAR if calendar_ready else 'None'}\n"
        )

        file.write(
            f"- Calendar ready: "
            f"{calendar_ready}\n"
        )

        file.write(
            "- Approach: common historical year\n"
        )

        file.write(
            "- Representative-year mapping required: "
            f"{representative_mapping_required}\n"
        )

        file.write(
            f"- Final load households: "
            f"{load_result['household_count']}\n"
        )

        file.write(
            f"- Complete load households: "
            f"{load_result['complete_households']}\n"
        )

        file.write(
            f"- Reconstructed load hours: "
            f"{load_result['reconstructed_hours']}\n"
        )

        file.write(
            f"- Joint Spanish intersection: "
            f"{spanish_result['intersection_hours']}\n"
        )

        file.write(
            f"- Joint Spanish union: "
            f"{spanish_result['union_hours']}\n\n"
        )

        file.write(
            "## Decision rationale\n\n"
        )

        file.write(
            selection_reason
            + "\n"
        )

        file.write(
            "\n## Methodological note\n\n"
        )

        file.write(
            "The final residential demand dataset contains "
            "30 complete 2013 hourly household profiles. "
            "Reconstructed observations remain explicitly "
            "flagged and documented in the processed dataset "
            "and reconstruction metadata. The audit does not "
            "silently fill or alter any observation.\n"
        )

    print_header(
        "PHASE 2 OUTPUTS"
    )

    print(
        "Wrote:",
        csv_path
    )

    print(
        "Wrote:",
        household_path
    )

    print(
        "Wrote:",
        md_path
    )

    print(
        "Wrote:",
        yaml_path
    )

    print(
        "Wrote:",
        decision_path
    )

    return {
        "calendar_ready":
            calendar_ready,

        "selected_year":
            (
                SIMULATION_YEAR
                if calendar_ready
                else None
            ),

        "csv":
            csv_path,

        "markdown":
            md_path,

        "yaml":
            yaml_path,

        "decision_markdown":
            decision_path,
    }


# ============================================================
# MAIN AUDIT
# ============================================================

def run_audit():

    print_header(
        "PHASE 2 FINAL DATASET AUDIT"
    )

    print(
        "Simulation year:",
        SIMULATION_YEAR
    )

    # --------------------------------------------------------
    # Final load
    # --------------------------------------------------------

    load_result = (
        audit_final_load()
    )

    # --------------------------------------------------------
    # Metadata
    # --------------------------------------------------------

    metadata_result = (
        audit_load_metadata(
            load_result
        )
    )

    # --------------------------------------------------------
    # Spanish datasets
    # --------------------------------------------------------

    spanish_result = (
        audit_spanish_inputs()
    )

    # --------------------------------------------------------
    # Write final outputs
    # --------------------------------------------------------

    final_result = (
        write_outputs(
            load_result,
            metadata_result,
            spanish_result,
        )
    )

    print_header(
        "FINAL PHASE 2 STATUS"
    )

    print(
        "Selected year:",
        final_result[
            "selected_year"
        ]
    )

    print(
        "Calendar ready:",
        final_result[
            "calendar_ready"
        ]
    )

    if final_result[
        "calendar_ready"
    ]:

        print(
            "Phase 2 dataset/calendar audit: PASS"
        )

    else:

        print(
            "Phase 2 dataset/calendar audit: FAIL"
        )

    return final_result


if __name__ == "__main__":
    run_audit()
