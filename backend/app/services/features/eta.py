"""Segment-ETA target extraction and features.

Target definition (``observed_segment_time_min``)
------------------------------------------------
For each inferred track, an observation "passes" a graph node when it is
within ``radius_km`` of the node. Within each contiguous run of such
observations the closest one is taken, and the passage time is refined by the
along-track offset ``d*cos(bearing_to_node - heading) / ground_speed``
(bounded to +/- one sample interval). Two consecutive passages A -> B where
the directed edge A->B exists in the graph yield one traversal with
``observed_segment_time_min = t_B - t_A``. Traversals with an internal data gap
longer than ``max_gap_s`` are excluded and counted.

Only information available at the ENTRY time is used as a feature.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from app.services.geospatial.geo import haversine_km_vec
from app.services.geospatial.grid import Grid

ETA_NUMERIC = [
    "segment_distance_km", "bearing_sin", "bearing_cos", "hour_sin", "hour_cos",
    "from_airport", "to_airport", "entry_speed_mps", "entry_altitude_m",
    "tailwind_proxy_ms", "weather_severity", "corridor_count_prev_window",
]
ETA_FEATURES = ETA_NUMERIC
ETA_TARGET = "observed_segment_time_min"


def extract_traversals(obs: pd.DataFrame, nodes: pd.DataFrame, edges: pd.DataFrame,
                       radius_km: float = 25.0, max_gap_s: float = 300.0, sample_s: float = 90.0) -> tuple[pd.DataFrame, dict]:
    node_ids = nodes.node_id.to_numpy()
    nlat = nodes.latitude.to_numpy(float)
    nlon = nodes.longitude.to_numpy(float)
    edge_set = set(zip(edges.source_node, edges.target_node))
    stats = {"tracks": 0, "passages": 0, "traversals": 0, "excluded_gap": 0, "non_edge_pairs": 0}
    rows = []
    cols = ["track_id", "source_aircraft_id", "timestamp_utc", "latitude", "longitude", "ground_speed_mps", "heading_deg", "altitude_m"]
    for tid, tr in obs[cols].sort_values(["track_id", "timestamp_utc"]).groupby("track_id", sort=False):
        stats["tracks"] += 1
        if len(tr) < 3:
            continue
        lat = tr.latitude.to_numpy(float)
        lon = tr.longitude.to_numpy(float)
        ts = tr.timestamp_utc.to_numpy("datetime64[ns]").astype("int64") / 1e9
        d = haversine_km_vec(lat[:, None], lon[:, None], nlat[None, :], nlon[None, :])
        near = d < radius_km
        if not near.any():
            continue
        passages = []
        for j in np.where(near.any(axis=0))[0]:
            idx = np.where(near[:, j])[0]
            runs = np.split(idx, np.where(np.diff(idx) > 1)[0] + 1)
            for run in runs:
                i = run[np.argmin(d[run, j])]
                gs = tr.ground_speed_mps.iat[i]
                hd = tr.heading_deg.iat[i]
                t = ts[i]
                if pd.notna(gs) and pd.notna(hd) and gs > 30:
                    y = math.sin(math.radians(nlon[j] - lon[i])) * math.cos(math.radians(nlat[j]))
                    x = (math.cos(math.radians(lat[i])) * math.sin(math.radians(nlat[j]))
                         - math.sin(math.radians(lat[i])) * math.cos(math.radians(nlat[j])) * math.cos(math.radians(nlon[j] - lon[i])))
                    brg = math.degrees(math.atan2(y, x))
                    along_km = d[i, j] * math.cos(math.radians(brg - hd))
                    t += float(np.clip(along_km * 1000 / gs, -sample_s, sample_s))
                passages.append((t, node_ids[j], i))
        passages.sort()
        stats["passages"] += len(passages)
        for (t_a, a, ia), (t_b, b, ib) in zip(passages[:-1], passages[1:]):
            if a == b:
                continue
            if (a, b) not in edge_set:
                stats["non_edge_pairs"] += 1
                continue
            seg_ts = ts[ia:ib + 1]
            if len(seg_ts) > 1 and np.max(np.diff(seg_ts)) > max_gap_s:
                stats["excluded_gap"] += 1
                continue
            rows.append({
                "track_id": tid, "source_aircraft_id": tr.source_aircraft_id.iat[0],
                "edge_id": f"{a}->{b}", "source_node": a, "target_node": b,
                "entry_time_utc": pd.Timestamp(t_a, unit="s", tz="UTC"),
                "exit_time_utc": pd.Timestamp(t_b, unit="s", tz="UTC"),
                ETA_TARGET: (t_b - t_a) / 60.0,
                "entry_speed_mps": tr.ground_speed_mps.iat[ia],
                "entry_altitude_m": tr.altitude_m.iat[ia],
            })
            stats["traversals"] += 1
    return pd.DataFrame(rows), stats


def build_eta_features(trav: pd.DataFrame, edges: pd.DataFrame, airports: set[str], weather: pd.DataFrame | None,
                       counts: pd.DataFrame | None, grid: Grid, pos: dict[str, tuple[float, float]],
                       window_min: int) -> pd.DataFrame:
    """Attach entry-time features. ``counts``: aggregated cell/window counts."""
    df = trav.merge(edges[["edge_id", "distance_km", "bearing_deg"]], on="edge_id", how="left")
    df = df.rename(columns={"distance_km": "segment_distance_km"})
    df["bearing_sin"] = np.sin(np.radians(df.bearing_deg))
    df["bearing_cos"] = np.cos(np.radians(df.bearing_deg))
    hour = df.entry_time_utc.dt.hour + df.entry_time_utc.dt.minute / 60
    df["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    df["hour_cos"] = np.cos(2 * np.pi * hour / 24)
    df["from_airport"] = df.source_node.isin(airports).astype(int)
    df["to_airport"] = df.target_node.isin(airports).astype(int)
    edge_cells = {e: grid.cells_along(*pos[u], *pos[v], step_km=40) for e, u, v in zip(edges.edge_id, edges.source_node, edges.target_node)}
    add_context_features(df, edge_cells, weather, counts, time_col="entry_time_utc", window_min=window_min)
    return df


def add_context_features(df: pd.DataFrame, edge_cells: dict[str, list[str]], weather: pd.DataFrame | None,
                         counts: pd.DataFrame | None, time_col: str, window_min: int) -> None:
    """In-place: tailwind proxy, weather severity and previous-window corridor count for each row.

    * weather: hourly cell record at floor(entry_time, 1h) for the first cell of the edge.
    * corridor count: mean unique-aircraft count over the edge's cells in the last COMPLETE
      window before entry (window_end <= floor(entry, window)).
    """
    from app.services.ingestion.synthetic_demo import weather_severity

    first_cell = df.edge_id.map(lambda e: edge_cells[e][0] if edge_cells.get(e) else None)
    if weather is not None and len(weather):
        w = weather.set_index(["location_id", "valid_time_utc"])
        key = pd.MultiIndex.from_arrays([first_cell, df[time_col].dt.floor("1h")])
        ws = w["wind_speed_100m_ms"].reindex(key).to_numpy() if "wind_speed_100m_ms" in w else np.full(len(df), np.nan)
        wd = w["wind_direction_10m_deg"].reindex(key).to_numpy()
        df["tailwind_proxy_ms"] = -ws * np.cos(np.radians(df.bearing_deg.to_numpy() - wd))
        df["weather_severity"] = weather_severity(
            w["precipitation_mm"].reindex(key).to_numpy(), w["wind_gusts_10m_ms"].reindex(key).to_numpy(),
            w["cloud_cover_pct"].reindex(key).to_numpy())
        df.loc[np.isnan(wd), "weather_severity"] = np.nan
    else:
        df["tailwind_proxy_ms"] = np.nan
        df["weather_severity"] = np.nan
    if counts is not None and len(counts):
        c = counts.set_index(["cell_id", "window_start_utc"])["aircraft_count"]
        prev_start = df[time_col].dt.floor(f"{window_min}min") - pd.Timedelta(minutes=window_min)
        vals = []
        for e, ps in zip(df.edge_id, prev_start):
            cells = edge_cells.get(e, [])
            vals.append(float(np.mean([c.get((cid, ps), 0) for cid in cells])) if cells else np.nan)
        df["corridor_count_prev_window"] = vals
    else:
        df["corridor_count_prev_window"] = np.nan
