"""
Tests for ingest_pvpc.py

These tests use temporary directories only and will not modify your repository.
They add thesis-model/src/preprocessing to sys.path so that ingest_pvpc can be
imported directly without treating thesis-model as a package.
"""
import pytest
import pandas as pd
from pathlib import Path
import sys

# Add preprocessing directory to sys.path so we can import ingest_pvpc directly
PREPROCESSING_DIR = (
    Path(__file__).resolve().parents[1]  # thesis-model/tests -> parents[1] -> thesis-model
    / "src"
    / "preprocessing"
)
sys.path.insert(0, str(PREPROCESSING_DIR))

from ingest_pvpc import process_dataset, detect_encoding_and_read, sha256_of_file

# Helper writer
def write_csv(path: Path, content: str, encoding="utf-8"):
    path.write_text(content, encoding=encoding)

def make_semicolon_csv(indicator_id, geoid, geoname, timestamps, values, series_name=None):
    name = series_name if series_name is not None else "Test series"
    lines = ["id;name;geoid;geoname;value;datetime"]
    for ts, v in zip(timestamps, values):
        lines.append(f'{indicator_id};"{name}";{geoid};{geoname};{v};{ts}')
    return "\n".join(lines) + "\n"

@pytest.fixture
def tmp_repo_dir(tmp_path):
    base = tmp_path / "thesis-model"
    raw_import = base / "data" / "raw" / "pvpc_import"
    raw_export = base / "data" / "raw" / "pvpc_export"
    processed_silver = base / "data" / "processed" / "silver"
    processed_audit = base / "data" / "processed" / "audit"
    raw_import.mkdir(parents=True, exist_ok=True)
    raw_export.mkdir(parents=True, exist_ok=True)
    processed_silver.mkdir(parents=True, exist_ok=True)
    processed_audit.mkdir(parents=True, exist_ok=True)
    yield base

def test_semicolon_and_utf8sig_parsing_and_conversion(tmp_repo_dir):
    base = tmp_repo_dir
    src = base / "data" / "raw" / "pvpc_import"
    file = src / "sample.csv"
    timestamps = ["2024-01-01T00:00:00+01:00", "2024-01-01T01:00:00+01:00"]
    content = make_semicolon_csv(1001, "8741", "Península", timestamps, ["100.0", "-5.0"],
                                series_name="Término de facturación de energía activa del PVPC 2.0TD - Península")
    write_csv(file, content, encoding="utf-8-sig")
    out = base / "data" / "processed" / "silver" / "pvpc_import_silver.csv"
    res = process_dataset("import", src, out, "EUR/MWh")
    assert out.exists()
    df = pd.read_csv(out)
    assert pytest.approx(0.1) == float(df["price_eur_kwh"].iloc[0])
    assert pytest.approx(-0.005) == float(df["price_eur_kwh"].iloc[1])
    assert (df["price_original"].astype(float) < 0).sum() == 1
    assert set(df["indicator_id"].astype(int)) == {1001}
    manifest = base / "data" / "processed" / "audit" / "pvpc_raw_file_manifest.csv"
    assert manifest.exists()

def test_indicator_validation_import_rejects_wrong_id(tmp_repo_dir):
    base = tmp_repo_dir
    src = base / "data" / "raw" / "pvpc_import"
    f = src / "wrong.csv"
    content = make_semicolon_csv(1739, "8741", "Península", ["2024-01-01T00:00:00+01:00"], ["10"],
                                 series_name="Término de facturación de energía activa del PVPC 2.0TD - Península")
    write_csv(f, content)
    out = base / "data" / "processed" / "silver" / "pvpc_import_silver.csv"
    with pytest.raises(ValueError):
        process_dataset("import", src, out, "EUR/MWh")

def test_indicator_validation_export_accepts_and_rejects(tmp_repo_dir):
    base = tmp_repo_dir
    src = base / "data" / "raw" / "pvpc_export"
    good = src / "good.csv"
    bad = src / "bad.csv"
    good_content = make_semicolon_csv(1739, "8741", "Península", ["2024-01-02T00:00:00+01:00"], ["12"],
                                     series_name="Precio de la energía excedentaria del autoconsumo para el mecanismo de compensación simplificada - península")
    bad_content = make_semicolon_csv(1001, "8741", "Península", ["2024-01-02T00:00:00+01:00"], ["12"],
                                     series_name="Precio de la energía excedentaria del autoconsumo para el mecanismo de compensación simplificada - península")
    write_csv(good, good_content)
    write_csv(bad, bad_content)
    out = base / "data" / "processed" / "silver" / "pvpc_export_silver.csv"
    (bad).unlink()
    res = process_dataset("export", src, out, "EUR/MWh")
    assert Path(res["silver_file"]).exists()

def test_dst_repeated_hour_flagging_and_utc_distinct(tmp_repo_dir):
    base = tmp_repo_dir
    src = base / "data" / "raw" / "pvpc_import"
    f = src / "dst.csv"
    timestamps = [
        "2024-10-27T00:00:00+02:00",
        "2024-10-27T01:00:00+02:00",
        "2024-10-27T02:00:00+02:00",
        "2024-10-27T02:00:00+01:00",
        "2024-10-27T03:00:00+01:00",
    ]
    values = ["10", "10", "10", "20", "20"]
    content = make_semicolon_csv(1001, "8741", "Península", timestamps, values,
                                series_name="Término de facturación de energía activa del PVPC 2.0TD - Península")
    write_csv(f, content)
    out = base / "data" / "processed" / "silver" / "pvpc_import_silver.csv"
    res = process_dataset("import", src, out, "EUR/kWh")
    df = pd.read_csv(out)
    assert "duplicate_local_timestamp" in df.columns
    assert df["duplicate_local_timestamp"].astype(bool).sum() >= 1
    utc_times = df["timestamp_utc"].tolist()
    assert len(set(utc_times)) == len(utc_times)

def test_exact_duplicate_file_hash_and_canonical_selection(tmp_repo_dir):
    base = tmp_repo_dir
    src = base / "data" / "raw" / "pvpc_export"
    content = make_semicolon_csv(1739, "8741", "Península", ["2024-01-05T00:00:00+01:00", "2024-01-05T01:00:00+01:00"], ["50", "60"],
                                 series_name="Precio de la energía excedentaria del autoconsumo para el mecanismo de compensación simplificada")
    f1 = src / "a.csv"
    f2 = src / "b.csv"
    write_csv(f1, content)
    write_csv(f2, content)
    sha1 = sha256_of_file(f1)
    sha2 = sha256_of_file(f2)
    assert sha1 == sha2
    out = base / "data" / "processed" / "silver" / "pvpc_export_silver.csv"
    res = process_dataset("export", src, out, "EUR/MWh")
    assert Path(res["silver_file"]).exists()
    manifest = base / "data" / "processed" / "audit" / "pvpc_raw_file_manifest.csv"
    mf = pd.read_csv(manifest)
    assert str(f1) in mf["relative_path"].values
    assert str(f2) in mf["relative_path"].values
    summary = base / "data" / "processed" / "audit" / "pvpc_ingestion_summary.csv"
    sf = pd.read_csv(summary)
    assert any(str(f1) in str(s) or str(f2) in str(s) for s in sf["source_file"].astype(str).tolist())

def test_conflicting_prices_raise_error(tmp_repo_dir):
    base = tmp_repo_dir
    src = base / "data" / "raw" / "pvpc_import"
    f1 = src / "g1.csv"
    f2 = src / "g2.csv"
    ts = "2024-02-01T12:00:00+01:00"
    content1 = make_semicolon_csv(1001, "8741", "Península", [ts], ["10"],
                                  series_name="Término de facturación de energía activa del PVPC 2.0TD - Península")
    content2 = make_semicolon_csv(1001, "8741", "Península", [ts], ["20"],
                                  series_name="Término de facturación de energía activa del PVPC 2.0TD - Península")
    write_csv(f1, content1)
    write_csv(f2, content2)
    out = base / "data" / "processed" / "silver" / "pvpc_import_silver.csv"
    with pytest.raises(ValueError):
        process_dataset("import", src, out, "EUR/kWh")
