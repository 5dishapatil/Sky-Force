"""Data-quality and cleaning layer for aircraft observations.

Every exclusion and every flag is counted and reported; nothing is silently
deleted. Unknown values stay NaN/None - an unknown altitude is NEVER filled
with zero.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from app.services.geospatial.geo import haversine_km_vec

OBS_COLUMNS = [
    "observation_id", "source", "is_synthetic", "source_aircraft_id", "callsign", "timestamp_utc",
    "latitude", "longitude", "altitude_m", "ground_speed_mps", "heading_deg", "vertical_rate_mps",
    "on_ground", "last_contact_utc",
]

MAX_GROUND_SPEED_MPS = 350.0     # ~680 kt: research plausibility bound for civil traffic
MAX_IMPLIED_SPEED_MPS = 400.0    # position-jump detection bound
ALT_MIN_M, ALT_MAX_M = -500.0, 16000.0
GAP_FLAG_S = 5 * 60              # flag gaps > 5 min within a track
TRACK_BREAK_S = 30 * 60          # gaps > 30 min start a new inferred track


@dataclass
class QualityReport:
    input_rows: int = 0
    retained_rows: int = 0
    dropped: dict[str, int] = field(default_factory=dict)
    flagged: dict[str, int] = field(default_factory=dict)
    missing_profile_pct: dict[str, float] = field(default_factory=dict)
    time_range_utc: list[str | None] = field(default_factory=lambda: [None, None])
    sources: dict[str, int] = field(default_factory=dict)
    thresholds: dict[str, float] = field(default_factory=dict)
    generated_at_utc: str = ""

    def to_dict(self) -> dict:
        return self.__dict__.copy()


def normalise_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure all internal columns exist with correct dtypes; parse times to UTC."""
    out = df.copy()
    for col in OBS_COLUMNS:
        if col not in out.columns:
            out[col] = np.nan
    out["timestamp_utc"] = pd.to_datetime(out["timestamp_utc"], utc=True, errors="coerce")
    out["last_contact_utc"] = pd.to_datetime(out["last_contact_utc"], utc=True, errors="coerce")
    for c in ["latitude", "longitude", "altitude_m", "ground_speed_mps", "heading_deg", "vertical_rate_mps"]:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    out["source_aircraft_id"] = out["source_aircraft_id"].astype(str).str.strip()
    out["callsign"] = out["callsign"].where(out["callsign"].notna(), None)
    if "data_quality_flags" not in out.columns:
        out["data_quality_flags"] = ""
    out["data_quality_flags"] = out["data_quality_flags"].fillna("")
    return out


def _add_flag(df: pd.DataFrame, mask: pd.Series, flag: str) -> None:
    m = mask.fillna(False).to_numpy(dtype=bool)
    cur = df["data_quality_flags"].to_numpy(dtype=object)
    cur[m] = [f"{c},{flag}" if c else flag for c in cur[m]]
    df["data_quality_flags"] = cur


def run_quality(df_in: pd.DataFrame) -> tuple[pd.DataFrame, QualityReport]:
    rep = QualityReport(input_rows=int(len(df_in)))
    rep.thresholds = {
        "max_ground_speed_mps": MAX_GROUND_SPEED_MPS, "max_implied_speed_mps": MAX_IMPLIED_SPEED_MPS,
        "altitude_min_m": ALT_MIN_M, "altitude_max_m": ALT_MAX_M, "gap_flag_s": GAP_FLAG_S,
        "track_break_s": TRACK_BREAK_S,
    }
    df = normalise_schema(df_in).reset_index(drop=True)

    # 1. invalid timestamps
    bad_ts = df["timestamp_utc"].isna()
    rep.dropped["invalid_timestamp"] = int(bad_ts.sum())
    df = df[~bad_ts]

    # 2. out-of-order delivery (detected in file order, before sorting)
    df = df.reset_index(drop=True)
    prev_ts = df.groupby("source_aircraft_id")["timestamp_utc"].shift(1)
    ooo = df["timestamp_utc"] < prev_ts
    _add_flag(df, ooo, "out_of_order_delivery")
    rep.flagged["out_of_order_delivery"] = int(ooo.sum())

    # 3. exact duplicates
    dup = df.duplicated(subset=["source_aircraft_id", "timestamp_utc", "latitude", "longitude"], keep="first")
    rep.dropped["duplicate"] = int(dup.sum())
    df = df[~dup]

    # 4. invalid coordinates
    bad_coord = (
        df["latitude"].isna() | df["longitude"].isna()
        | (df["latitude"] < -90) | (df["latitude"] > 90)
        | (df["longitude"] < -180) | (df["longitude"] > 180)
    )
    rep.dropped["invalid_coordinate"] = int(bad_coord.sum())
    df = df[~bad_coord]

    df = df.sort_values(["source_aircraft_id", "timestamp_utc"], kind="stable").reset_index(drop=True)

    # 5. implausible ground speed -> value set to NaN, row retained & flagged
    bad_spd = df["ground_speed_mps"] > MAX_GROUND_SPEED_MPS
    _add_flag(df, bad_spd, "implausible_speed")
    df.loc[bad_spd, "ground_speed_mps"] = np.nan
    rep.flagged["implausible_speed"] = int(bad_spd.sum())

    # 6. implausible altitude
    bad_alt = (df["altitude_m"] < ALT_MIN_M) | (df["altitude_m"] > ALT_MAX_M)
    _add_flag(df, bad_alt, "implausible_altitude")
    df.loc[bad_alt, "altitude_m"] = np.nan
    rep.flagged["implausible_altitude"] = int(bad_alt.sum())

    # 7. isolated position jumps (both legs implausible, bridging leg plausible)
    jump = _position_jumps(df)
    rep.dropped["position_jump"] = int(jump.sum())
    df = df[~jump].reset_index(drop=True)

    # 8. missing altitude (retained, NOT imputed)
    miss_alt = df["altitude_m"].isna()
    _add_flag(df, miss_alt, "missing_altitude")
    rep.flagged["missing_altitude"] = int(miss_alt.sum())

    # 9. gaps
    dt = df.groupby("source_aircraft_id")["timestamp_utc"].diff().dt.total_seconds()
    gap = (dt > GAP_FLAG_S) & (dt <= TRACK_BREAK_S)
    _add_flag(df, gap, "gap_gt_5min")
    rep.flagged["gap_gt_5min"] = int(gap.sum())
    rep.flagged["track_break_gt_30min"] = int((dt > TRACK_BREAK_S).sum())

    rep.retained_rows = int(len(df))
    rep.missing_profile_pct = {
        c: round(float(df[c].isna().mean() * 100), 3)
        for c in ["callsign", "altitude_m", "ground_speed_mps", "heading_deg", "vertical_rate_mps", "on_ground"]
    }
    if len(df):
        rep.time_range_utc = [df["timestamp_utc"].min().isoformat(), df["timestamp_utc"].max().isoformat()]
    rep.sources = {str(k): int(v) for k, v in df["source"].value_counts().items()}
    rep.generated_at_utc = datetime.now(timezone.utc).isoformat()
    return df, rep


def _position_jumps(df: pd.DataFrame) -> pd.Series:
    dt0 = df.groupby("source_aircraft_id")["timestamp_utc"].diff().dt.total_seconds()
    seg = (dt0.isna() | (dt0 > TRACK_BREAK_S)).cumsum()
    g = df.groupby(seg)
    lat, lon, t = df["latitude"], df["longitude"], df["timestamp_utc"]
    plat, plon, pt = g["latitude"].shift(1), g["longitude"].shift(1), g["timestamp_utc"].shift(1)
    nlat, nlon, nt = g["latitude"].shift(-1), g["longitude"].shift(-1), g["timestamp_utc"].shift(-1)

    def speed(a_lat, a_lon, a_t, b_lat, b_lon, b_t):  # noqa: ANN001, ANN202
        d = haversine_km_vec(a_lat.to_numpy(float), a_lon.to_numpy(float), b_lat.to_numpy(float), b_lon.to_numpy(float)) * 1000
        s = (b_t - a_t).dt.total_seconds().to_numpy(float)
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.where(s > 0, d / s, np.inf)

    v_in = speed(plat, plon, pt, lat, lon, t)
    v_out = speed(lat, lon, t, nlat, nlon, nt)
    v_bridge = speed(plat, plon, pt, nlat, nlon, nt)
    in_bad = np.nan_to_num(v_in, nan=0) > MAX_IMPLIED_SPEED_MPS
    out_bad = np.nan_to_num(v_out, nan=0) > MAX_IMPLIED_SPEED_MPS
    bridge_ok = np.nan_to_num(v_bridge, nan=np.inf) <= MAX_IMPLIED_SPEED_MPS
    has_prev = plat.notna().to_numpy()
    has_next = nlat.notna().to_numpy()
    jump = (in_bad & out_bad & bridge_ok) | (in_bad & has_prev & ~has_next)
    return pd.Series(jump & has_prev, index=df.index)


def segment_tracks(df: pd.DataFrame, gap_s: int = TRACK_BREAK_S) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Infer track IDs: same aircraft identifier, split where the gap exceeds ``gap_s``.

    The result is an *inferred* track identifier - NOT an airline flight number.
    """
    out = df.sort_values(["source_aircraft_id", "timestamp_utc"], kind="stable").copy()
    dt = out.groupby("source_aircraft_id")["timestamp_utc"].diff().dt.total_seconds()
    new_track = dt.isna() | (dt > gap_s)
    seq = new_track.groupby(out["source_aircraft_id"]).cumsum().astype(int)
    out["track_id"] = out["source_aircraft_id"] + "-T" + seq.map(lambda k: f"{k:03d}")
    summary = (
        out.groupby("track_id")
        .agg(source_aircraft_id=("source_aircraft_id", "first"), callsign=("callsign", "first"),
             start_utc=("timestamp_utc", "min"), end_utc=("timestamp_utc", "max"),
             n_observations=("timestamp_utc", "size"))
        .reset_index()
    )
    summary["method"] = f"aircraft-id + gap>{gap_s // 60}min segmentation"
    return out, summary
