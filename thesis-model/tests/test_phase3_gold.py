
from pathlib import Path
import math

import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]

GOLD_DIR = ROOT / "data" / "gold"
META_DIR = GOLD_DIR / "metadata"

GOLD_FILE = (
    GOLD_DIR
    / "hourly_member_inputs_2013.csv"
)

COMMUNITY_FILE = (
    GOLD_DIR
    / "community_configuration_2013.csv"
)

SCENARIO_FILE = (
    GOLD_DIR
    / "scenario_parameters_2013.csv"
)

SPANISH_FILE = (
    META_DIR
    / "spanish_hourly_inputs_2013.csv"
)

ALIGNED_LOAD_FILE = (
    GOLD_DIR
    / "staging"
    / "load_2013_30_households_madrid_aligned.csv"
)

HOUSEHOLD_METADATA_FILE = (
    META_DIR
    / "household_metadata_2013.csv"
)


@pytest.fixture(scope="module")
def gold():

    df = pd.read_csv(
        GOLD_FILE,
        low_memory=False,
    )

    df["timestamp_utc"] = pd.to_datetime(
        df["timestamp_utc"],
        utc=True,
        errors="coerce",
    )

    df["was_reconstructed"] = (
        df["was_reconstructed"]
        .astype(str)
        .str.strip()
        .str.lower()
        .isin(["true", "1", "yes"])
    )

    return df


@pytest.fixture(scope="module")
def community():

    return pd.read_csv(
        COMMUNITY_FILE
    )


@pytest.fixture(scope="module")
def scenarios():

    return pd.read_csv(
        SCENARIO_FILE
    )


@pytest.fixture(scope="module")
def spanish():

    df = pd.read_csv(
        SPANISH_FILE
    )

    df["timestamp_utc"] = pd.to_datetime(
        df["timestamp_utc"],
        utc=True,
        errors="coerce",
    )

    return df


def test_phase3_required_files_exist():

    required = [
        GOLD_FILE,
        COMMUNITY_FILE,
        SCENARIO_FILE,
        SPANISH_FILE,
        ALIGNED_LOAD_FILE,
        HOUSEHOLD_METADATA_FILE,
    ]

    assert all(
        path.exists()
        for path in required
    )


def test_gold_shape_and_uniqueness(gold):

    assert len(gold) == 262800
    assert gold["member_id"].nunique() == 30
    assert gold["timestamp_utc"].nunique() == 8760

    assert (
        gold.duplicated(
            subset=[
                "member_id",
                "timestamp_utc",
            ]
        ).sum()
        == 0
    )

    counts = (
        gold.groupby(
            "member_id"
        )[
            "timestamp_utc"
        ]
        .nunique()
    )

    assert (counts == 8760).all()


def test_gold_matches_madrid_2013_calendar(gold):

    expected = pd.date_range(
        start=pd.Timestamp(
            "2013-01-01 00:00:00",
            tz="Europe/Madrid",
        ),
        end=pd.Timestamp(
            "2014-01-01 00:00:00",
            tz="Europe/Madrid",
        ),
        freq="h",
        inclusive="left",
    ).tz_convert("UTC")

    actual = pd.DatetimeIndex(
        gold["timestamp_utc"]
        .drop_duplicates()
        .sort_values()
    )

    assert len(expected) == 8760
    assert len(
        expected.difference(actual)
    ) == 0
    assert len(
        actual.difference(expected)
    ) == 0


def test_gold_core_values(gold):

    columns = [
        "load_kwh",
        "allocation_coefficient",
        "pv_profile_kwh_per_kwp",
        "omie_eur_mwh",
        "pvpc_import_eur_mwh",
        "pvpc_export_eur_mwh",
    ]

    assert (
        gold[columns]
        .isna()
        .sum()
        .sum()
        == 0
    )

    assert (
        gold["load_kwh"] >= 0
    ).all()

    assert (
        gold["pv_profile_kwh_per_kwp"] >= 0
    ).all()

    assert math.isclose(
        gold["load_kwh"].sum(),
        117656.065866,
        rel_tol=0.0,
        abs_tol=1e-6,
    )


def test_reconstruction_provenance(gold):

    assert (
        gold[
            "was_reconstructed"
        ].sum()
        == 11990
    )

    reconstructed = gold[
        gold[
            "was_reconstructed"
        ]
    ]

    assert (
        reconstructed[
            "reconstruction_method"
        ].notna().all()
    )


def test_allocation_closure_and_consistency(
    gold,
    community,
):

    assert len(community) == 30

    assert math.isclose(
        community[
            "allocation_coefficient"
        ].sum(),
        1.0,
        rel_tol=0.0,
        abs_tol=1e-12,
    )

    gold_alloc = (
        gold[
            [
                "member_id",
                "allocation_coefficient",
            ]
        ]
        .drop_duplicates()
        .sort_values(
            "member_id"
        )
        .reset_index(
            drop=True
        )
    )

    config_alloc = (
        community[
            [
                "member_id",
                "allocation_coefficient",
            ]
        ]
        .sort_values(
            "member_id"
        )
        .reset_index(
            drop=True
        )
    )

    merged = gold_alloc.merge(
        config_alloc,
        on="member_id",
        suffixes=(
            "_gold",
            "_config",
        ),
        validate="one_to_one",
    )

    difference = (
        merged[
            "allocation_coefficient_gold"
        ]
        -
        merged[
            "allocation_coefficient_config"
        ]
    )

    assert (
        difference.abs().max()
        < 1e-12
    )


def test_community_configuration(community):

    assert (
        community[
            "number_of_members"
        ]
        == 30
    ).all()

    counts = (
        community[
            "consumption_cluster"
        ]
        .value_counts()
    )

    assert counts.get(
        "low",
        0,
    ) == 10

    assert counts.get(
        "medium",
        0,
    ) == 10

    assert counts.get(
        "high",
        0,
    ) == 10

    assert (
        community[
            "community_composition_case"
        ].nunique()
        == 1
    )


def test_spanish_hourly_inputs(spanish):

    assert len(spanish) == 8760

    assert (
        spanish[
            "timestamp_utc"
        ].nunique()
        == 8760
    )

    assert math.isclose(
        spanish[
            "pv_profile_kwh_per_kwp"
        ].sum(),
        1564.40318,
        rel_tol=0.0,
        abs_tol=1e-6,
    )

    assert (
        spanish[
            "omie_eur_mwh"
        ].lt(0).sum()
        == 247
    )


def test_scenario_register_structure(scenarios):

    assert len(scenarios) == 17

    assert (
        scenarios[
            "scenario_id"
        ].nunique()
        == 17
    )

    counts = (
        scenarios[
            "scenario_family"
        ]
        .value_counts()
    )

    assert counts.get(
        "No-DER",
        0,
    ) == 1

    assert counts.get(
        "PV-only",
        0,
    ) == 4

    assert counts.get(
        "PV-BESS",
        0,
    ) == 12

    assert (
        scenarios[
            "number_of_members"
        ]
        == 30
    ).all()

    assert (
        "community_size"
        not in scenarios.columns
    )

    pv_bess = scenarios[
        scenarios[
            "scenario_family"
        ]
        == "PV-BESS"
    ]

    assert set(
        pv_bess[
            "battery_capacity_kwh"
        ].unique()
    ) == {150.0}

    assert set(
        pv_bess[
            "battery_capex_eur_per_kwh"
        ].unique()
    ) == {
        350.0,
        450.0,
        550.0,
    }


def test_reference_cases_and_price_units(
    scenarios,
    gold,
):

    reference = (
        scenarios[
            "is_reference_case"
        ]
        .astype(str)
        .str.strip()
        .str.lower()
        .isin(
            [
                "true",
                "1",
                "yes",
            ]
        )
    )

    assert set(
        scenarios.loc[
            reference,
            "scenario_id",
        ]
    ) == {
        "NO_DER_REFERENCE",
        "PV_ONLY_PV050",
        "PV_BESS_PV050_CAPEX450",
    }

    required_price_columns = {
        "omie_eur_mwh",
        "pvpc_import_eur_mwh",
        "pvpc_export_eur_mwh",
    }

    assert required_price_columns.issubset(
        gold.columns
    )

    assert (
        "omie_eur_per_kwh"
        not in gold.columns
    )

    assert (
        "pvpc_import_eur_per_kwh"
        not in gold.columns
    )

    assert (
        "pvpc_export_eur_per_kwh"
        not in gold.columns
    )
