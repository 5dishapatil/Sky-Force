"""Deterministic SYNTHETIC demonstration world.

Everything produced here is synthetic and labelled as such:

* research-only waypoints ("SFWnn") and candidate segments (k-nearest-neighbour
  links) - NOT real airways;
* an hourly synthetic weather field on the research grid;
* synthetic aircraft trajectories ("SFxxxx" identifiers, "SFD" callsigns which
  are deliberately not valid ICAO 24-bit addresses / airline codes);
* a small fraction of deliberately injected data faults so the data-quality
  layer has something real to detect (ground truth kept in ``fault_log``).

Generator assumptions (documented in docs/data_dictionary.md):
* Departures follow a diurnal profile in IST (UTC+05:30).
* Flights follow the distance-shortest (75 %) or 2nd-shortest (25 %) graph path.
* Ground speed = true-airspeed profile + 3 x along-track synthetic wind
  (stands in for stronger winds aloft) - congestion slowdown - weather slowdown.
* Congestion slowdown uses unique-aircraft counts from a first generation pass.

Same seed => byte-identical outputs.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import networkx as nx
import numpy as np
import pandas as pd

from app.services.geospatial.geo import (
    haversine_km,
    initial_bearing_deg,
    interpolate_gc,
)
from app.services.geospatial.grid import Grid

HUB_WEIGHTS = {
    "VIDP": 10, "VABB": 9, "VOBL": 8, "VOHS": 6, "VOMM": 6, "VECC": 6, "VAAH": 4, "VAPO": 4,
    "VOGO": 3, "VOCI": 3, "VIJP": 3, "VILK": 3, "VEGT": 2, "VANP": 2, "VEBS": 2, "VAID": 2,
    "VABP": 1.5, "VOTV": 2, "VIAR": 1.5,
}
MAJOR_HUBS = ["VIDP", "VABB", "VOBL", "VOHS", "VOMM", "VECC"]

# Hourly departure intensity in IST (index = IST hour)
IST_PROFILE = np.array([0.35, 0.2, 0.15, 0.15, 0.3, 0.7, 1.3, 1.6, 1.6, 1.4, 1.2, 1.1,
                        1.0, 1.0, 1.0, 1.1, 1.2, 1.4, 1.5, 1.5, 1.3, 1.0, 0.8, 0.55])


@dataclass
class SyntheticWorld:
    airports: pd.DataFrame
    waypoints: pd.DataFrame
    edges: pd.DataFrame
    weather: pd.DataFrame
    observations: pd.DataFrame
    flights: pd.DataFrame
    fault_log: pd.DataFrame
    meta: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------------

def build_waypoints(airports: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    n = 0
    for lat in np.arange(9.0, 31.5, 3.0):
        for lon in np.arange(70.5, 92.0, 3.0):
            la = float(lat + rng.uniform(-0.45, 0.45))
            lo = float(lon + rng.uniform(-0.45, 0.45))
            d = min(haversine_km(la, lo, a.latitude, a.longitude) for a in airports.itertuples())
            if 90.0 <= d <= 420.0:
                n += 1
                rows.append({
                    "node_id": f"SFW{n:02d}", "name": f"Research waypoint {n:02d}",
                    "latitude": round(la, 4), "longitude": round(lo, 4), "kind": "research_synthetic",
                    "source": "synthetic_demo",
                    "provenance": "Deterministic synthetic research-only waypoint (seeded jittered lattice). Not a real navigation fix.",
                })
    return pd.DataFrame(rows)


def build_edges(nodes: pd.DataFrame, k: int = 4, max_km: float = 650.0) -> pd.DataFrame:
    coords = nodes[["node_id", "latitude", "longitude"]].to_numpy()
    pairs: set[tuple[str, str]] = set()
    for i, (nid, la, lo) in enumerate(coords):
        dists = sorted(
            ((haversine_km(la, lo, la2, lo2), nid2) for j, (nid2, la2, lo2) in enumerate(coords) if j != i)
        )
        for d, nid2 in dists[:k]:
            if d <= max_km:
                pairs.add((nid, nid2))
                pairs.add((nid2, nid))
    # Guarantee weak connectivity by linking nearest components.
    g = nx.Graph()
    g.add_nodes_from(nodes["node_id"])
    g.add_edges_from(pairs)
    pos = {r.node_id: (r.latitude, r.longitude) for r in nodes.itertuples()}
    comps = list(nx.connected_components(g))
    while len(comps) > 1:
        a, b = comps[0], comps[1]
        best = min(((haversine_km(*pos[u], *pos[v]), u, v) for u in a for v in b))
        pairs.add((best[1], best[2]))
        pairs.add((best[2], best[1]))
        g.add_edge(best[1], best[2])
        comps = list(nx.connected_components(g))
    rows = []
    for u, v in sorted(pairs):
        (la1, lo1), (la2, lo2) = pos[u], pos[v]
        rows.append({
            "edge_id": f"{u}->{v}", "source_node": u, "target_node": v,
            "distance_km": round(haversine_km(la1, lo1, la2, lo2), 3),
            "bearing_deg": round(initial_bearing_deg(la1, lo1, la2, lo2), 2),
            "is_synthetic": True,
            "provenance": "Synthetic candidate segment (k-nearest-neighbour link). NOT an approved airway.",
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Weather
# ---------------------------------------------------------------------------

STORMS = [
    # (start_hour, duration_h, lat0, lon0, dlat/h, dlon/h, radius_km, peak_precip_mm_h)
    (30, 20, 19.5, 86.0, -0.06, -0.20, 260, 11.0),
    (78, 16, 15.0, 74.0, 0.10, 0.12, 220, 9.0),
    (150, 22, 23.0, 79.0, 0.04, -0.15, 280, 12.0),
    (176, 14, 25.5, 82.0, -0.05, -0.10, 240, 10.0),
]


def build_weather(grid: Grid, cells: list[str], start: datetime, hours: int, rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    for h in range(hours):
        t = start + timedelta(hours=h)
        ist_h = (t.hour + 5.5) % 24
        for cid in cells:
            la, lo = grid.center(cid)
            base_dir = 270 + 35 * math.sin(2 * math.pi * (la - 8) / 26) + 10 * math.sin(2 * math.pi * h / 37)
            ws = 4.0 + 2.5 * math.sin(2 * math.pi * (ist_h - 9) / 24) + 0.12 * (la - 8) + rng.normal(0, 0.6)
            precip, cloud, gust_extra = 0.0, 20 + 15 * math.sin(2 * math.pi * (ist_h - 14) / 24) + rng.normal(0, 5), 0.0
            for s0, dur, slat, slon, dla, dlo, rad, peak in STORMS:
                if s0 <= h < s0 + dur:
                    k = h - s0
                    d = haversine_km(la, lo, slat + dla * k, slon + dlo * k)
                    life = math.sin(math.pi * (k + 0.5) / dur)
                    inten = life * math.exp(-((d / rad) ** 2))
                    precip += peak * inten
                    cloud += 85 * inten
                    gust_extra += 14 * inten
            ws = max(0.3, ws)
            rows.append({
                "location_id": cid, "latitude": la, "longitude": lo, "valid_time_utc": t,
                "temperature_2m_c": round(31 - 0.55 * (la - 8) + 4 * math.sin(2 * math.pi * (ist_h - 9) / 24) + rng.normal(0, 0.5), 2),
                "relative_humidity_2m_pct": round(float(np.clip(55 + 25 * min(1, precip / 3) + rng.normal(0, 5), 5, 100)), 1),
                "surface_pressure_hpa": round(1008 - 3 * min(1, precip / 5) + rng.normal(0, 0.8), 1),
                "precipitation_mm": round(max(0.0, precip + (rng.normal(0, 0.05) if precip > 0.1 else 0)), 2),
                "cloud_cover_pct": round(float(np.clip(cloud, 0, 100)), 1),
                "wind_speed_10m_ms": round(ws, 2),
                "wind_direction_10m_deg": round(base_dir % 360, 1),
                "wind_gusts_10m_ms": round(ws * 1.45 + gust_extra + abs(rng.normal(0, 0.5)), 2),
                "wind_speed_100m_ms": round(ws * 1.35, 2),
            })
    df = pd.DataFrame(rows)
    df["valid_time_utc"] = pd.to_datetime(df["valid_time_utc"], utc=True)
    return df


def weather_severity(precip_mm, gust_ms, cloud_pct):  # noqa: ANN001, ANN201
    """Dimensionless weather-exposure proxy in [0, 1] (documented research heuristic)."""
    p = np.minimum(np.asarray(precip_mm, dtype=float) / 6.0, 1.0)
    g = np.minimum(np.maximum(np.asarray(gust_ms, dtype=float) - 10.0, 0.0) / 15.0, 1.0)
    c = np.asarray(cloud_pct, dtype=float) / 100.0
    return np.clip(0.55 * p + 0.30 * g + 0.15 * c, 0.0, 1.0)


# ---------------------------------------------------------------------------
# Flights
# ---------------------------------------------------------------------------

def _schedule(start: datetime, days: int, per_day: int, rng: np.random.Generator) -> list[dict]:
    codes = list(HUB_WEIGHTS)
    w = np.array([HUB_WEIGHTS[c] for c in codes], dtype=float)
    w /= w.sum()
    utc_profile = np.array([IST_PROFILE[int((h + 5.5) % 24)] for h in range(24)])
    utc_profile /= utc_profile.sum()
    flights = []
    for d in range(days):
        day0 = start + timedelta(days=d)
        n_today = int(per_day * (1.0 + 0.04 * math.sin(d)))
        hours = rng.choice(24, size=n_today, p=utc_profile)
        for hr in hours:
            o, de = rng.choice(codes, size=2, replace=False, p=w)
            dep = day0 + timedelta(hours=int(hr), seconds=int(rng.integers(0, 3600)))
            flights.append({"origin": str(o), "destination": str(de), "dep": dep, "surge": False})
        # Deterministic synthetic traffic surges (labelled)
        surges = {2: ("VIDP", "VABB", 13, 4, 28), 7: ("VIDP", "VOBL", 7, 3, 26), 5: ("VABB", "VECC", 9, 3, 18)}
        if d in surges:
            a, b, h0, dur, n = surges[d]
            for i in range(n):
                o, de = (a, b) if i % 2 == 0 else (b, a)
                dep = day0 + timedelta(hours=h0, seconds=int(rng.integers(0, dur * 3600)))
                flights.append({"origin": o, "destination": de, "dep": dep, "surge": True})
    flights.sort(key=lambda f: f["dep"])
    return flights


def _path_geometry(path: list[str], pos: dict[str, tuple[float, float]]):  # noqa: ANN202
    segs = []
    cum = [0.0]
    for u, v in zip(path[:-1], path[1:]):
        d = haversine_km(*pos[u], *pos[v])
        segs.append((u, v, d))
        cum.append(cum[-1] + d)
    return segs, cum


def _point_at(s: float, segs, cum, pos):  # noqa: ANN001, ANN202
    i = int(np.searchsorted(cum, s, side="right") - 1)
    i = min(max(i, 0), len(segs) - 1)
    u, v, d = segs[i]
    f = 0.0 if d == 0 else min(1.0, max(0.0, (s - cum[i]) / d))
    la, lo = interpolate_gc(*pos[u], *pos[v], f)
    tla, tlo = pos[v]
    brg = initial_bearing_deg(la, lo, tla, tlo) if f < 0.999 else initial_bearing_deg(*pos[u], tla, tlo)
    return la, lo, brg


def _profiles(s: float, total: float, cruise_alt: float) -> tuple[float, float]:
    climb = min(0.25 * total, 220.0)
    desc = min(0.30 * total, 260.0)
    if s < climb:
        f = s / climb
        return 420 + 400 * f, cruise_alt * f
    if s > total - desc:
        f = max(0.0, (total - s) / desc)
        return 420 + 400 * f, cruise_alt * f
    return 820.0, cruise_alt


def _fly(flight: dict, path: list[str], pos, wx_lookup, density, grid: Grid, dt_s: int,
         window_min: int, start: datetime, rng: np.random.Generator) -> list[tuple]:
    segs, cum = _path_geometry(path, pos)
    total = cum[-1]
    cruise_alt = float(flight["cruise_alt"])
    t = flight["dep"]
    s = 0.0
    out = []
    prev_alt = 0.0
    while s < total:
        la, lo, brg = _point_at(s, segs, cum, pos)
        tas, alt = _profiles(s, total, cruise_alt)
        cid = grid.cell_id(la, lo)
        hr = int((t - start).total_seconds() // 3600)
        wdir, wspd, sev = wx_lookup.get((cid, hr), (270.0, 4.0, 0.0))
        tail_ms = -wspd * math.cos(math.radians(brg - wdir)) * 3.0
        win = int((t - start).total_seconds() // (window_min * 60))
        dens = density.get((cid, win), 0) if density is not None else 0
        slow = 1.0 - min(0.18, 0.012 * max(0, dens - 3)) - 0.10 * sev
        gs_kmh = max(250.0, (tas + tail_ms * 3.6) * slow)
        vrate = (alt - prev_alt) / dt_s if out else 0.0
        out.append((t, la, lo, alt, gs_kmh / 3.6, brg, vrate))
        prev_alt = alt
        s += gs_kmh * dt_s / 3600.0
        t = t + timedelta(seconds=dt_s)
        if len(out) > 2000:
            break
    # final point at destination
    la, lo = pos[path[-1]]
    out.append((t, la, lo, 0.0, 420 / 3.6, initial_bearing_deg(*pos[segs[-1][0]], la, lo), -prev_alt / dt_s))
    return out


def generate_world(airports: pd.DataFrame, grid: Grid, start: datetime, days: int, flights_per_day: int,
                   sample_s: int, window_min: int, seed: int) -> SyntheticWorld:
    rng = np.random.default_rng(seed)
    wps = build_waypoints(airports, rng)
    nodes = pd.concat([
        airports[["node_id", "latitude", "longitude"]],
        wps[["node_id", "latitude", "longitude"]],
    ], ignore_index=True)
    edges = build_edges(nodes)
    pos = {r.node_id: (float(r.latitude), float(r.longitude)) for r in nodes.itertuples()}
    g = nx.DiGraph()
    for e in edges.itertuples():
        g.add_edge(e.source_node, e.target_node, w=e.distance_km)

    corridor = sorted({c for e in edges.itertuples() for c in grid.cells_along(*pos[e.source_node], *pos[e.target_node])})
    hours = days * 24 + 6
    weather = build_weather(grid, corridor, start, hours, rng)
    sev = weather_severity(weather.precipitation_mm, weather.wind_gusts_10m_ms, weather.cloud_cover_pct)
    hr_idx = ((weather.valid_time_utc - pd.Timestamp(start)).dt.total_seconds() // 3600).astype(int)
    wx_lookup = {
        (cid, int(h)): (float(wd), float(ws), float(sv))
        for cid, h, wd, ws, sv in zip(weather.location_id, hr_idx, weather.wind_direction_10m_deg, weather.wind_speed_100m_ms, sev)
    }

    sched = _schedule(start, days, flights_per_day, rng)
    path_cache: dict[tuple[str, str], list[list[str]]] = {}
    fleet_free: list[tuple[datetime, str]] = []
    n_fleet = 0
    flights = []
    for i, f in enumerate(sched):
        key = (f["origin"], f["destination"])
        if key not in path_cache:
            gen = nx.shortest_simple_paths(g, *key, weight="w")
            path_cache[key] = [next(gen), next(gen, None)]
        p1, p2 = path_cache[key]
        path = p2 if (p2 is not None and rng.random() < 0.25) else p1
        # aircraft assignment: earliest-free aircraft, else a new airframe
        fleet_free.sort()
        if fleet_free and fleet_free[0][0] <= f["dep"]:
            _, ac = fleet_free.pop(0)
        else:
            n_fleet += 1
            ac = f"SF{n_fleet:04d}"
        f.update({
            "flight_index": i, "aircraft": ac, "callsign": f"SFD{100 + (i % 900)}", "path": path,
            "cruise_alt": float(rng.choice([9450, 10050, 10650, 11250, 11850])),
            "rng_seed": int(rng.integers(0, 2**31 - 1)),
        })
        flights.append(f)
        # availability: conservative block time (path km at 550 km/h) + 50 min turnaround
        path_km = sum(haversine_km(*pos[u], *pos[v]) for u, v in zip(path[:-1], path[1:]))
        fleet_free.append((f["dep"] + timedelta(hours=path_km / 550.0, minutes=50), ac))

    def run_pass(density):  # noqa: ANN001, ANN202
        recs = []
        for f in flights:
            frng = np.random.default_rng(f["rng_seed"])
            pts = _fly(f, f["path"], pos, wx_lookup, density, grid, sample_s, window_min, start, frng)
            for (t, la, lo, alt, gs, hd, vr) in pts:
                recs.append((f["flight_index"], f["aircraft"], f["callsign"], t, la, lo, alt, gs, hd, vr))
        return pd.DataFrame(recs, columns=["flight_index", "source_aircraft_id", "callsign", "timestamp_utc",
                                           "latitude", "longitude", "altitude_m", "ground_speed_mps",
                                           "heading_deg", "vertical_rate_mps"])

    first = run_pass(None)
    first["cell"] = grid.cell_ids_vec(first.latitude.to_numpy(), first.longitude.to_numpy())
    first["win"] = ((first.timestamp_utc - start).dt.total_seconds() // (window_min * 60)).astype(int)
    density = first.groupby(["cell", "win"]).source_aircraft_id.nunique().to_dict()
    obs = run_pass(density)

    # measurement noise
    nrng = np.random.default_rng(seed + 1)
    n = len(obs)
    obs["latitude"] = obs.latitude + nrng.normal(0, 0.0018, n)
    obs["longitude"] = obs.longitude + nrng.normal(0, 0.0018, n)
    obs["ground_speed_mps"] = (obs.ground_speed_mps + nrng.normal(0, 1.5, n)).round(2)
    obs["heading_deg"] = ((obs.heading_deg + nrng.normal(0, 0.8, n)) % 360).round(2)
    obs["altitude_m"] = (obs.altitude_m + nrng.normal(0, 8, n)).clip(lower=0).round(1)
    obs["vertical_rate_mps"] = obs.vertical_rate_mps.round(2)
    obs["timestamp_utc"] = pd.to_datetime(obs.timestamp_utc, utc=True)
    obs["on_ground"] = False
    obs["last_contact_utc"] = obs["timestamp_utc"]
    obs["source"] = "synthetic_demo"
    obs["is_synthetic"] = True
    obs = obs.sort_values(["timestamp_utc", "source_aircraft_id"], kind="stable").reset_index(drop=True)
    obs["observation_id"] = [f"SYN-{i:07d}" for i in range(len(obs))]

    obs, faults = inject_faults(obs, np.random.default_rng(seed + 2))

    flights_df = pd.DataFrame([{
        "flight_index": f["flight_index"], "aircraft": f["aircraft"], "callsign": f["callsign"],
        "origin": f["origin"], "destination": f["destination"], "dep_utc": f["dep"],
        "path": "|".join(f["path"]), "surge": f["surge"], "cruise_alt_m": f["cruise_alt"],
    } for f in flights])

    meta = {
        "seed": seed, "start_utc": start.isoformat(), "days": days, "flights": len(flights),
        "fleet_size": n_fleet, "sample_seconds": sample_s, "corridor_cells": len(corridor),
        "storms": [dict(zip(["start_hour", "duration_h", "lat0", "lon0", "dlat_h", "dlon_h", "radius_km", "peak_precip_mm_h"], s)) for s in STORMS],
        "injected_faults": faults["fault"].value_counts().to_dict() if len(faults) else {},
    }
    return SyntheticWorld(airports, wps, edges, weather, obs, flights_df, faults, meta)


def inject_faults(obs: pd.DataFrame, rng: np.random.Generator) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Inject a small, logged fraction of realistic data faults (synthetic QA ground truth)."""
    obs = obs.copy()
    n = len(obs)
    log = []
    # missing altitude (2 %)
    idx = rng.choice(n, size=int(0.02 * n), replace=False)
    obs.loc[idx, "altitude_m"] = np.nan
    obs.loc[idx, "vertical_rate_mps"] = np.nan
    log += [{"observation_id": obs.observation_id[i], "fault": "missing_altitude"} for i in idx]
    # invalid coordinates (0.1 %)
    idx = rng.choice(n, size=int(0.001 * n), replace=False)
    obs.loc[idx, "latitude"] = 91.5
    log += [{"observation_id": obs.observation_id[i], "fault": "invalid_coordinate"} for i in idx]
    # position jumps (0.1 %)
    idx = rng.choice(n, size=int(0.001 * n), replace=False)
    obs.loc[idx, "latitude"] = obs.loc[idx, "latitude"] + 3.0
    log += [{"observation_id": obs.observation_id[i], "fault": "position_jump"} for i in idx]
    # implausible speed (0.05 %)
    idx = rng.choice(n, size=int(0.0005 * n), replace=False)
    obs.loc[idx, "ground_speed_mps"] = 520.0
    log += [{"observation_id": obs.observation_id[i], "fault": "implausible_speed"} for i in idx]
    # transmission dropouts: remove 6-12 consecutive points in ~3 % of flights
    obs = obs.sort_values(["source_aircraft_id", "timestamp_utc"], kind="stable").reset_index(drop=True)
    flights = np.sort(obs.flight_index.unique())
    drop_f = rng.choice(flights, size=max(1, int(0.03 * len(flights))), replace=False)
    to_drop = []
    for fi in drop_f:
        rows = obs.index[obs.flight_index == fi].to_numpy()
        if len(rows) > 30:
            k = int(rng.integers(6, 13))
            s0 = int(rng.integers(10, len(rows) - k - 5))
            to_drop.extend(rows[s0:s0 + k])
            log.append({"observation_id": f"flight:{fi}", "fault": "dropout_gap"})
    obs = obs.drop(index=to_drop).reset_index(drop=True)
    # exact duplicates (0.3 %), delivered right after the original
    idx = rng.choice(len(obs), size=int(0.003 * len(obs)), replace=False)
    dups = obs.loc[idx].copy()
    log += [{"observation_id": oid, "fault": "duplicate"} for oid in dups.observation_id]
    obs = pd.concat([obs, dups]).sort_index(kind="stable").reset_index(drop=True)
    # out-of-order delivery: swap ~0.1 % of adjacent rows belonging to the same aircraft
    order = np.arange(len(obs))
    cand = rng.choice(len(obs) - 1, size=int(0.001 * len(obs)), replace=False)
    ids = obs.source_aircraft_id.to_numpy()
    ts = obs.timestamp_utc.to_numpy()
    for i in sorted(cand):
        if ids[order[i]] == ids[order[i + 1]] and ts[order[i]] != ts[order[i + 1]]:
            order[i], order[i + 1] = order[i + 1], order[i]
            log.append({"observation_id": obs.observation_id[order[i]], "fault": "out_of_order"})
    obs = obs.iloc[order].reset_index(drop=True)
    return obs, pd.DataFrame(log)
