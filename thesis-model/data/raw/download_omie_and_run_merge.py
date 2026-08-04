#!/usr/bin/env python3
"""
download_omie_and_run_merge.py

Download OMIE MARGINALPDBC files for 2023-01-01..2025-12-31 into
thesis-model/data/raw/omie, then run the existing strict merge script.

This script is intended to be run in CI (GitHub Actions) or locally. It
records metadata for each downloaded file and will stop on any download or
parse error to ensure strict coverage requirements are enforced.

Usage:
    python thesis-model/data/raw/download_omie_and_run_merge.py [--base-dir PATH]

"""
from __future__ import annotations

import argparse
from pathlib import Path
import requests
import hashlib
from datetime import date, timedelta, datetime
from dateutil import tz
import csv
import sys
import time
import subprocess

# Configuration
START_DATE = date(2023, 1, 1)
END_DATE = date(2025, 12, 31)
URL_TPL = "https://www.omie.es/sites/default/files/dados/{yyyy}/{mm}/marginalpdbc_{yyyymmdd}.{version}"
MAX_VERSION_PROBE = 12
DOWNLOAD_DIR_REL = Path("thesis-model") / "data" / "raw" / "omie"
METADATA_CSV = DOWNLOAD_DIR_REL / "download_metadata_omie.csv"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "omie-downloader/1.0 (+https://github.com/)"})


def sha256_bytes(b: bytes) -> str:
    import hashlib
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


def iso_utc_now():
    return datetime.utcnow().replace(tzinfo=tz.tzutc()).isoformat()


def probe_latest_version_for_date(d: date, timeout=10):
    yyyy = f"{d.year:04d}"
    mm = f"{d.month:02d}"
    yyyymmdd = f"{d.year:04d}{d.month:02d}{d.day:02d}"
    found = None
    for v in range(1, MAX_VERSION_PROBE + 1):
        url = URL_TPL.format(yyyy=yyyy, mm=mm, yyyymmdd=yyyymmdd, version=v)
        try:
            r = SESSION.head(url, timeout=timeout, allow_redirects=True)
            if r.status_code == 200:
                found = (v, url)
                continue
            if r.status_code in (403, 405):
                # try GET
                r2 = SESSION.get(url, timeout=timeout, stream=True)
                if r2.status_code == 200:
                    r2.close()
                    found = (v, url)
                    continue
        except requests.RequestException:
            try:
                r2 = SESSION.get(url, timeout=timeout, stream=True)
                if r2.status_code == 200:
                    r2.close()
                    found = (v, url)
                    continue
            except requests.RequestException:
                pass
    return None if found is None else max([found], key=lambda x: x[0])


def download_url(url: str, outpath: Path, timeout=60):
    r = SESSION.get(url, timeout=timeout)
    r.raise_for_status()
    content = r.content
    # Basic HTML detection
    start = content[:200].lstrip().lower()
    if start.startswith(b"<!doctype") or start.startswith(b"<html"):
        raise ValueError("Downloaded content appears to be HTML")
    outpath.write_bytes(content)
    meta = {
        "download_time_utc": iso_utc_now(),
        "file_size": len(content),
        "sha256": sha256_bytes(content),
    }
    return meta


def daterange(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def run_merge_script(base_dir: Path) -> int:
    # Run the already committed strict merge script
    script = base_dir / "thesis-model" / "data" / "raw" / "merge_raw_datasets.py"
    if not script.exists():
        print("Merge script not found at", script)
        return 2
    proc = subprocess.run([sys.executable, str(script)], cwd=base_dir)
    return proc.returncode


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-dir", default=None, help="Repo root base dir (defaults to repo root)")
    args = ap.parse_args(argv)

    # Determine base dir
    if args.base_dir:
        base = Path(args.base_dir).resolve()
    else:
        # assume script is inside repo; repo root is two levels up from thesis-model
        base = Path(__file__).resolve().parents[2]
    download_dir = base / DOWNLOAD_DIR_REL
    download_dir.mkdir(parents=True, exist_ok=True)

    metadata_rows = []
    errors = []

    for d in daterange(START_DATE, END_DATE):
        probe = probe_latest_version_for_date(d)
        if probe is None:
            errors.append((d, 'not_found', None))
            continue
        version, url = probe
        yyyymmdd = f"{d.year:04d}{d.month:02d}{d.day:02d}"
        filename = f"marginalpdbc_{yyyymmdd}.{version}"
        outpath = download_dir / filename
        try:
            meta = download_url(url, outpath)
            metadata_rows.append({
                'delivery_date': d.isoformat(),
                'source_url': url,
                'filename': filename,
                'version': version,
                'download_time_utc': meta['download_time_utc'],
                'file_size': meta['file_size'],
                'sha256': meta['sha256'],
                'status': 'ok',
                'error': ''
            })
            # be polite
            time.sleep(0.1)
        except Exception as e:
            metadata_rows.append({
                'delivery_date': d.isoformat(),
                'source_url': url,
                'filename': filename,
                'version': version,
                'download_time_utc': iso_utc_now(),
                'file_size': None,
                'sha256': None,
                'status': 'download_error',
                'error': str(e)
            })
            errors.append((d, 'download_error', str(e)))

    # Write metadata CSV
    with METADATA_CSV.open('w', newline='', encoding='utf-8') as f:
        fieldnames = ['delivery_date', 'source_url', 'filename', 'version', 'download_time_utc', 'file_size', 'sha256', 'status', 'error']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in metadata_rows:
            writer.writerow(r)

    if errors:
        print(f"Encountered {len(errors)} download errors. See {METADATA_CSV} for details. Aborting.")
        for e in errors[:10]:
            print("  ", e)
        sys.exit(1)

    # Run merge script
    rc = run_merge_script(base)
    if rc != 0:
        print("Merge script exited with code", rc)
        sys.exit(rc)

    # Commit results back to repository if running in CI (GITHUB_ACTIONS)
    if 'GITHUB_ACTIONS' in os.environ:
        # commit merged CSVs and metadata file
        try:
            import os
            repo_root = base
            # configure git
            subprocess.run(['git', 'config', 'user.name', 'github-actions[bot]'], cwd=repo_root, check=True)
            subprocess.run(['git', 'config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com'], cwd=repo_root, check=True)
            subprocess.run(['git', 'add', str(download_dir / 'download_metadata_omie.csv')], cwd=repo_root, check=True)
            subprocess.run(['git', 'add', str(base / 'thesis-model' / 'data' / 'raw' / 'merged_omie.csv')], cwd=repo_root, check=True)
            subprocess.run(['git', 'add', str(base / 'thesis-model' / 'data' / 'raw' / 'metadata_omie.csv')], cwd=repo_root, check=False)
            subprocess.run(['git', 'commit', '-m', 'Automated: download OMIE files and merge raw datasets'], cwd=repo_root, check=False)
            subprocess.run(['git', 'push'], cwd=repo_root, check=False)
        except Exception as e:
            print("Warning: failed to commit/push results in CI:", e)

    print("Download and merge completed successfully.")


if __name__ == '__main__':
    main()
