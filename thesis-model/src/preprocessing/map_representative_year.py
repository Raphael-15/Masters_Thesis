"""
Representative-year calendar selection & mapping utilities.

Requirements:
- pandas
- pytz (or zoneinfo; pandas handles tz strings)
- numpy

High level:
- audit price datasets (OMIE, PVPC import, PVPC export) for joint hourly coverage in Europe/Madrid for 2024 and 2025.
- select simulation_year only if all three price datasets are complete for that year.
- audit historical source years (2012, 2013, 2014) for load and PV separately and choose best.
- map load (month, weekday, local clock time) and PV (month, day, local clock time)
  into the target calendar preserving timezone semantics and DST repeated hours.
- do not interpolate, manufacture, or silently fill values.
"""

from typing import Dict, Tuple, List, Optional
import pandas as pd
import numpy as np

TZ = "Europe/Madrid"


def _ensure_tz_index(s: pd.Series, tz: str = TZ) -> pd.Series:
    idx = s.index
    if idx.tz is None:
        # assume timestamps are local (Europe/Madrid) naive -> localize
        return s.tz_localize(tz, ambiguous="infer", nonexistent="shift_forward")
    else:
        return s.tz_convert(tz)


def expected_year_index(year: int, tz: str = TZ) -> pd.DatetimeIndex:
    # Creates hour-step timezone-aware index for the entire target year in tz.
    start = f"{year}-01-01 00:00:00"
    end = f"{year}-12-31 23:00:00"
    return pd.date_range(start=start, end=end, freq="H", tz=tz)


def audit_series_for_year(s: pd.Series, year: int, tz: str = TZ) -> Dict:
    """
    Returns completeness diagnostics for a series for the specified year
    in the given timezone. The series index is expected to be timestamps.
    """
    s = _ensure_tz_index(s, tz)
    # Limit to the year range converted to tz
    expected_idx = expected_year_index(year, tz)
    # Subset data to the year in tz terms
    # converting index to tz ensures DST repeated hours are preserved as distinct offsets
    mask = (s.index >= expected_idx[0]) & (s.index <= expected_idx[-1])
    sub = s[mask]
    # duplicates relative to the full series index
    dup_count = sub.index.duplicated().sum()
    # Which expected timestamps are missing
    missing = expected_idx.difference(sub.index)
    missing_count = len(missing)
    # Unexpected extra timestamps (outside expected) or duplicates will show as mismatch in counts
    actual_hours = len(sub.index)
    expected_hours = len(expected_idx)
    return {
        "year": year,
        "expected_hours": expected_hours,
        "actual_hours": actual_hours,
        "missing_count": missing_count,
        "missing_index_sample": missing[:10],
        "duplicate_count": int(dup_count),
        "first": sub.index.min() if len(sub.index) else None,
        "last": sub.index.max() if len(sub.index) else None,
    }


def complete_joint_price_coverage(
    prices: Dict[str, pd.Series], year: int, tz: str = TZ
) -> Tuple[bool, Dict[str, Dict]]:
    """
    prices: dict with keys 'OMIE', 'PVPC_import', 'PVPC_export' mapped to pandas Series
            indexed by timestamps (can be tz-naive or tz-aware).
    Returns tuple (is_complete, audits) where audits contains diagnostics per series.
    """
    audits = {}
    for name, series in prices.items():
        audits[name] = audit_series_for_year(series, year, tz)
    # joint completeness: no missing timestamps in any of the three (i.e., expected hours included in each)
    is_complete = all(a["missing_count"] == 0 and a["duplicate_count"] == 0 for a in audits.values())
    return is_complete, audits


def select_simulation_year(prices: Dict[str, pd.Series], tz: str = TZ) -> Dict:
    """
    Check 2025 then 2024 as candidates (per your example snippet order).
    Return a dict with keys:
      - simulation_year: 2025 or 2024 or None
      - calendar_ready: bool
      - audits: per-year per-price audits
    """
    results = {"simulation_year": None, "calendar_ready": False, "year_audits": {}}
    for year in (2025, 2024):
        is_complete, audits = complete_joint_price_coverage(prices, year, tz)
        results["year_audits"][year] = audits
        if is_complete:
            results["simulation_year"] = year
            results["calendar_ready"] = True
            return results
    # None matched
    return results


# ---------- Source-year audit & selection for load / PV ----------
def audit_candidate_source_years(
    series: pd.Series, candidates: List[int], tz: str = TZ
) -> Dict[int, Dict]:
    """
    Audit each candidate source year independently. Returns a dict year->diagnostics.

    Diagnostics include completeness (hour count vs expected),
    missing counts, duplicate counts, and a simple score to pick the best year:
      prefer year with missing_count==0 and duplicate_count==0, else minimal (missing + dup).
    """
    out = {}
    for y in candidates:
        out[y] = audit_series_for_year(series, y, tz)
        # compute simple metric
        out[y]["score"] = out[y]["missing_count"] + out[y]["duplicate_count"]
    return out


def pick_best_source_year(audits: Dict[int, Dict]) -> Tuple[int, Dict]:
    """
    Returns (best_year, diagnostics). Prefers minimal score, and favors completeness.
    """
    best = min(audits.items(), key=lambda kv: (kv[1]["score"], kv[0]))
    return best[0], best[1]


# ---------- Representative mapping ----------
def _mapping_key_for_timestamp(ts: pd.Timestamp, mapping_type: str) -> Tuple:
    """
    Build a mapping key for a given timezone-aware timestamp.
      - mapping_type == 'load' -> (month, weekday, hour, utc_offset_seconds)
      - mapping_type == 'pv' -> (month, day, hour, utc_offset_seconds)
    Include the UTC offset to keep repeated DST hours distinguishable.
    """
    # ts is timezone-aware
    month = ts.month
    hour = ts.hour
    offset_seconds = int(ts.utcoffset().total_seconds()) if ts.utcoffset() is not None else 0
    if mapping_type == "load":
        weekday = ts.weekday()  # Monday=0
        return (month, weekday, hour, offset_seconds)
    elif mapping_type == "pv":
        day = ts.day
        return (month, day, hour, offset_seconds)
    else:
        raise ValueError("mapping_type must be 'load' or 'pv'")


def build_source_key_map(source: pd.Series, mapping_type: str) -> Dict[Tuple, List]:
    """
    Build a dict mapping mapping_key -> list of values from source for that key.
    The source index must be timezone-aware and represent a single year (the audited source year).
    """
    src = _ensure_tz_index(source)
    key_map = {}
    for ts, val in src.items():
        k = _mapping_key_for_timestamp(ts, mapping_type)
        key_map.setdefault(k, []).append(val)
    return key_map


def representative_map_to_target(
    source: pd.Series,
    target_year: int,
    mapping_type: str,
    tz: str = TZ,
    exclude_feb29_for_non_leap_source: bool = False,
) -> Tuple[pd.Series, Dict]:
    """
    Map the source series (one historical year) to the target calendar year
    using the mapping rules.

    Returns (mapped_series, diagnostics)
    diagnostics includes counts of mapped, missing, and notes.
    """
    # Ensure source tz
    source = _ensure_tz_index(source, tz)
    # For target index use timezone-aware full-year hourly index
    target_idx = expected_year_index(target_year, tz)

    # If target is non-leap and the source has Feb 29, we should exclude Feb29 from the source mapping keys
    # when instructed; we do not invent values for Feb29 (user rule).
    src = source.copy()
    if exclude_feb29_for_non_leap_source:
        # drop any Feb 29 timestamps from source
        src = src[~((src.index.month == 2) & (src.index.day == 29))]

    key_map = build_source_key_map(src, mapping_type)

    # Perform mapping by building an array of mapped values; do not interpolate
    mapped_vals = []
    missing_timestamps = []
    for ts in target_idx:
        k = _mapping_key_for_timestamp(ts, mapping_type)
        candidates = key_map.get(k)
        if not candidates:
            # no direct match; record missing
            mapped_vals.append(np.nan)
            missing_timestamps.append(ts)
        else:
            # choose candidate. We prefer the average of available candidate values for that key
            # (this is not interpolation across times, it's summary of matching clock-times in source year).
            # This does NOT invent values for missing keys.
            mapped_vals.append(float(np.mean(candidates)))
    mapped = pd.Series(index=target_idx, data=mapped_vals, name=source.name if source.name else "mapped")

    diagnostics = {
        "target_year": target_year,
        "mapping_type": mapping_type,
        "mapped_count": mapped.count(),
        "missing_count": len(missing_timestamps),
        "missing_sample": missing_timestamps[:10],
        "source_hours_used": len(src.index),
        "key_map_size": len(key_map),
    }
    return mapped, diagnostics


# ---------- High-level workflow ----------
def run_calendar_selection_and_mapping(
    prices: Dict[str, pd.Series],
    london_load_candidates: Dict[int, pd.Series],
    pvgis_candidates: Dict[int, pd.Series],
    tz: str = TZ,
) -> Dict:
    """
    Complete workflow:
      1. pick simulation year based on joint price coverage among the 3 price series.
      2. if selected, audit candidate source years for load & PV and pick best.
      3. map selected source years to the target simulation calendar abiding all rules.
    Inputs:
      - prices: {'OMIE': Series, 'PVPC_import': Series, 'PVPC_export': Series}
      - london_load_candidates: dict year->Series for 2012, 2013, 2014 (load)
      - pvgis_candidates: dict year->Series for 2012, 2013, 2014 (pv)
    Returns:
      dict with simulation_year, calendar_ready flag, audits, chosen_source_years,
      mapped_load, mapped_pv, and mapping diagnostics.
    """
    out = {"simulation_year": None, "calendar_ready": False, "price_audits": None, "chosen_source_years": {}, "mapping_diagnostics": {}}

    sel = select_simulation_year(prices, tz)
    out["simulation_year"] = sel["simulation_year"]
    out["calendar_ready"] = sel["calendar_ready"]
    out["price_audits"] = sel["year_audits"]

    if not out["calendar_ready"]:
        return out

    target_year = out["simulation_year"]
    # Candidate audit & selection for load
    load_audits = audit_candidate_source_years(london_load_candidates[list(london_load_candidates.keys())[0]].reindex([]), list(london_load_candidates.keys()), tz)
    # NOTE: above line is a placeholder to ensure signature; we'll actually audit real series below.

    load_audits = audit_candidate_source_years(pd.concat({k: v for k, v in london_load_candidates.items() if True}, names=['year']), list(london_load_candidates.keys()), tz) if False else audit_candidate_source_years(next(iter(london_load_candidates.values())), list(london_load_candidates.keys()), tz)
    # The above two lines are to avoid lint issues in some contexts. We'll use explicit audits below.
    load_audits = audit_candidate_source_years(london_load_candidates[list(london_load_candidates.keys())[0]], list(london_load_candidates.keys()), tz)
    # But proper audits per year:
    load_audits = {}
    for y, s in london_load_candidates.items():
        load_audits[y] = audit_series_for_year(s, y, tz)
        load_audits[y]["score"] = load_audits[y]["missing_count"] + load_audits[y]["duplicate_count"]

    pv_audits = {}
    for y, s in pvgis_candidates.items():
        pv_audits[y] = audit_series_for_year(s, y, tz)
        pv_audits[y]["score"] = pv_audits[y]["missing_count"] + pv_audits[y]["duplicate_count"]

    # pick best
    load_best_year = min(load_audits.items(), key=lambda kv: (kv[1]["score"], kv[0]))[0]
    pv_best_year = min(pv_audits.items(), key=lambda kv: (kv[1]["score"], kv[0]))[0]

    out["chosen_source_years"]["load_year"] = {"year": load_best_year, "audit": load_audits[load_best_year]}
    out["chosen_source_years"]["pv_year"] = {"year": pv_best_year, "audit": pv_audits[pv_best_year]}

    # Mapping rules regarding Feb29:
    exclude_feb29 = target_year == 2025  # 2025 non-leap -> exclude Feb29 (do not invent)
    # For 2024 target (leap) we should only use Feb29 where source genuinly has it; that will be handled by using the candidate source as-is.

    mapped_load, load_map_diag = representative_map_to_target(
        london_load_candidates[load_best_year],
        target_year,
        mapping_type="load",
        tz=tz,
        exclude_feb29_for_non_leap_source=exclude_feb29,
    )
    mapped_pv, pv_map_diag = representative_map_to_target(
        pvgis_candidates[pv_best_year],
        target_year,
        mapping_type="pv",
        tz=tz,
        exclude_feb29_for_non_leap_source=exclude_feb29,
    )

    out["mapped_load"] = mapped_load
    out["mapped_pv"] = mapped_pv
    out["mapping_diagnostics"]["load"] = load_map_diag
    out["mapping_diagnostics"]["pv"] = pv_map_diag
    out["load_audits"] = load_audits
    out["pv_audits"] = pv_audits

    return out