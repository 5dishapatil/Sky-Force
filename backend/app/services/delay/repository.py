"""Repository for loading, indexing, and resolving flights, rotations, and airport contexts."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any
import math
import pandas as pd
from sqlalchemy import create_engine, text

from app.core.config import get_settings
from app.services.geospatial.geo import haversine_km
from app.services.geospatial.grid import Grid


class FlightDelayRepository:
    """In-memory cached repository indexing flight tracks, airframe rotations, and airport coordinates."""

    _instance: FlightDelayRepository | None = None

    def __init__(self) -> None:
        self.settings = get_settings()
        self.grid = Grid(
            self.settings.grid_lat_min,
            self.settings.grid_lat_max,
            self.settings.grid_lon_min,
            self.settings.grid_lon_max,
            self.settings.grid_deg,
        )
        self.airports: dict[str, dict[str, Any]] = {}  # node_id -> dict
        self.airports_by_iata: dict[str, dict[str, Any]] = {}
        self.flights: list[dict[str, Any]] = []  # all parsed flights
        self.flights_by_id: dict[str, dict[str, Any]] = {}
        self.flights_by_callsign: dict[str, list[dict[str, Any]]] = {}
        self.rotations_by_tail: dict[str, list[dict[str, Any]]] = {}
        self._loaded = False

    @classmethod
    def get_instance(cls) -> FlightDelayRepository:
        if cls._instance is None:
            cls._instance = cls()
            cls._instance.load()
        return cls._instance

    def load(self, force: bool = False) -> None:
        if self._loaded and not force:
            return

        engine = create_engine(self.settings.database_url)
        with engine.connect() as conn:
            # 1. Load airports
            ap_rows = conn.execute(text("SELECT node_id, iata, icao, name, latitude, longitude, country FROM airports")).fetchall()
            self.airports = {
                r.node_id: {
                    "node_id": r.node_id,
                    "iata": r.iata or r.node_id[:3],
                    "icao": r.icao or r.node_id,
                    "name": r.name,
                    "latitude": float(r.latitude),
                    "longitude": float(r.longitude),
                    "country": r.country,
                }
                for r in ap_rows
            }
            self.airports_by_iata = {a["iata"]: a for a in self.airports.values()}

            # 2. Load inferred tracks
            tracks_query = text(
                "SELECT track_id, source_aircraft_id, callsign, start_utc, end_utc, n_observations "
                "FROM inferred_tracks ORDER BY source_aircraft_id, start_utc"
            )
            track_rows = conn.execute(tracks_query).fetchall()

            # 3. Load start and end coordinates of tracks from observations
            obs_query = text(
                "SELECT track_id, timestamp_utc, latitude, longitude "
                "FROM aircraft_observations "
                "WHERE timestamp_utc IN (SELECT start_utc FROM inferred_tracks UNION SELECT end_utc FROM inferred_tracks)"
            )
            obs_rows = conn.execute(obs_query).fetchall()

        # Build start/end coords lookup per track
        start_coords: dict[str, tuple[float, float]] = {}
        end_coords: dict[str, tuple[float, float]] = {}
        for r in obs_rows:
            tid = r.track_id
            if not tid or r.latitude is None or r.longitude is None:
                continue
            lat, lon = float(r.latitude), float(r.longitude)
            if tid not in start_coords:
                start_coords[tid] = (lat, lon)
            else:
                end_coords[tid] = (lat, lon)

        # Helper to find closest airport
        def find_closest_airport(lat: float, lon: float) -> dict[str, Any]:
            best_ap = None
            min_d = float("inf")
            for ap in self.airports.values():
                d = (ap["latitude"] - lat) ** 2 + (ap["longitude"] - lon) ** 2
                if d < min_d:
                    min_d = d
                    best_ap = ap
            return best_ap or next(iter(self.airports.values()))

        # Parse flights
        parsed_flights: list[dict[str, Any]] = []
        for r in track_rows:
            tid = r.track_id
            tail = r.source_aircraft_id
            callsign = r.callsign or f"SFD{tid[-3:]}"
            flight_num_digits = "".join([c for c in callsign if c.isdigit()]) or "101"
            flight_number = f"SF {flight_num_digits}"

            s_coord = start_coords.get(tid, (28.55, 77.10))
            e_coord = end_coords.get(tid, (19.09, 72.86))
            orig_ap = find_closest_airport(*s_coord)
            dest_ap = find_closest_airport(*e_coord)

            # Ensure start_utc and end_utc have timezone
            s_utc = r.start_utc
            if isinstance(s_utc, str):
                s_utc = datetime.fromisoformat(s_utc)
            if s_utc.tzinfo is None:
                s_utc = s_utc.replace(tzinfo=timezone.utc)

            e_utc = r.end_utc
            if isinstance(e_utc, str):
                e_utc = datetime.fromisoformat(e_utc)
            if e_utc.tzinfo is None:
                e_utc = e_utc.replace(tzinfo=timezone.utc)

            dist_km = haversine_km(orig_ap["latitude"], orig_ap["longitude"], dest_ap["latitude"], dest_ap["longitude"])
            enroute_min = max(20.0, dist_km / 8.5)  # approx ~510 km/h block speed

            item = {
                "flight_id": tid,
                "flight_number": flight_number,
                "callsign": callsign,
                "airline": "SkyForce Airlines",
                "aircraft_tail": tail,
                "origin_id": orig_ap["node_id"],
                "origin_iata": orig_ap["iata"],
                "origin_name": orig_ap["name"],
                "origin_lat": orig_ap["latitude"],
                "origin_lon": orig_ap["longitude"],
                "destination_id": dest_ap["node_id"],
                "destination_iata": dest_ap["iata"],
                "destination_name": dest_ap["name"],
                "destination_lat": dest_ap["latitude"],
                "destination_lon": dest_ap["longitude"],
                "scheduled_departure_utc": s_utc,
                "scheduled_arrival_utc": s_utc + timedelta(minutes=enroute_min + 15),
                "actual_departure_utc": s_utc,
                "actual_arrival_utc": e_utc,
                "n_observations": r.n_observations,
                "distance_km": round(dist_km, 1),
                "enroute_eta_min": round(enroute_min, 1),
            }
            parsed_flights.append(item)

        self.flights = parsed_flights
        self.flights_by_id = {f["flight_id"]: f for f in self.flights}

        # Build index by callsign and flight number
        self.flights_by_callsign = {}
        for f in self.flights:
            cs = f["callsign"].upper()
            fn = f["flight_number"].replace(" ", "").upper()
            self.flights_by_callsign.setdefault(cs, []).append(f)
            self.flights_by_callsign.setdefault(fn, []).append(f)

        # Build aircraft rotations
        rotations: dict[str, list[dict[str, Any]]] = {}
        for f in sorted(self.flights, key=lambda x: (x["aircraft_tail"], x["scheduled_departure_utc"])):
            rotations.setdefault(f["aircraft_tail"], []).append(f)
        self.rotations_by_tail = rotations

        # Link inbound leg to each flight
        for tail, legs in self.rotations_by_tail.items():
            for i, leg in enumerate(legs):
                if i > 0:
                    prev_leg = legs[i - 1]
                    leg["inbound_flight_id"] = prev_leg["flight_id"]
                    leg["inbound_callsign"] = prev_leg["callsign"]
                    leg["inbound_arrival_utc"] = prev_leg["actual_arrival_utc"]
                    turnaround_buffer = (leg["scheduled_departure_utc"] - prev_leg["actual_arrival_utc"]).total_seconds() / 60.0
                    leg["turnaround_buffer_min"] = turnaround_buffer
                else:
                    leg["inbound_flight_id"] = None
                    leg["inbound_callsign"] = None
                    leg["inbound_arrival_utc"] = None
                    leg["turnaround_buffer_min"] = 120.0  # First leg of day / overnight stand

        self._loaded = True

    def search_flights(
        self,
        query: str | None = None,
        date_str: str | None = None,
        origin: str | None = None,
        destination: str | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> tuple[int, list[dict[str, Any]]]:
        """Search flights with optional text, date, and origin/destination filters."""
        self.load()
        results = self.flights

        if query:
            q_clean = query.strip().upper().replace(" ", "").replace("-", "")
            results = [
                f for f in results
                if q_clean in f["callsign"].upper()
                or q_clean in f["flight_number"].replace(" ", "").upper()
                or q_clean in f["origin_iata"].upper()
                or q_clean in f["destination_iata"].upper()
                or q_clean in f["aircraft_tail"].upper()
            ]

        if date_str:
            results = [f for f in results if f["scheduled_departure_utc"].strftime("%Y-%m-%d") == date_str]

        if origin:
            o_clean = origin.strip().upper()
            results = [f for f in results if f["origin_iata"] == o_clean or f["origin_id"] == o_clean]

        if destination:
            d_clean = destination.strip().upper()
            results = [f for f in results if f["destination_iata"] == d_clean or f["destination_id"] == d_clean]

        total = len(results)
        paginated = results[offset : offset + limit]
        return total, paginated

    def get_flight(self, flight_id: str) -> dict[str, Any] | None:
        self.load()
        return self.flights_by_id.get(flight_id)

    def get_alternatives(self, flight: dict[str, Any], limit: int = 5) -> list[dict[str, Any]]:
        self.load()
        orig = flight["origin_id"]
        dest = flight["destination_id"]
        fid = flight["flight_id"]
        t_dep = flight["scheduled_departure_utc"]
        window_start = t_dep - timedelta(hours=6)
        window_end = t_dep + timedelta(hours=12)

        candidates = [
            f for f in self.flights
            if f["origin_id"] == orig
            and f["destination_id"] == dest
            and f["flight_id"] != fid
            and window_start <= f["scheduled_departure_utc"] <= window_end
        ]
        candidates.sort(key=lambda x: abs((x["scheduled_departure_utc"] - t_dep).total_seconds()))
        return candidates[:limit]

    def get_departure_queue_size(self, origin_id: str, departure_utc: datetime, window_minutes: int = 30) -> int:
        """Count active aircraft scheduled to depart the same origin airport in the time window."""
        t_min = departure_utc - timedelta(minutes=window_minutes)
        t_max = departure_utc + timedelta(minutes=window_minutes)
        count = sum(
            1 for f in self.flights
            if f["origin_id"] == origin_id and t_min <= f["scheduled_departure_utc"] <= t_max
        )
        return max(1, count)

    def get_weather_at_airport(self, lat: float, lon: float, timestamp_utc: datetime) -> dict[str, Any]:
        """Fetch synthetic weather observation for airport's cell and time from SQLite."""
        cid = self.grid.cell_id(lat, lon)
        engine = create_engine(self.settings.database_url)
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT precipitation_mm, temperature_2m_c, wind_speed_10m_ms, wind_gusts_10m_ms, cloud_cover_pct "
                    "FROM weather_observations "
                    "WHERE location_id = :cid AND valid_time_utc <= :ts "
                    "ORDER BY valid_time_utc DESC LIMIT 1"
                ),
                {"cid": cid, "ts": timestamp_utc},
            ).fetchone()

        if row:
            precip = float(row.precipitation_mm or 0.0)
            gusts = float(row.wind_gusts_10m_ms or 0.0)
            clouds = float(row.cloud_cover_pct or 0.0)
            temp = float(row.temperature_2m_c or 24.0)
            wind = float(row.wind_speed_10m_ms or 3.0)
            severity = min(1.0, (precip / 15.0) * 0.6 + (gusts / 25.0) * 0.4)
            condition = (
                "Thunderstorm / Heavy Convective Rain" if precip > 12.0
                else "Scattered Showers / Rain" if precip > 3.0
                else "High Gusts / Windy" if gusts > 14.0
                else "Overcast" if clouds > 75.0
                else "Fair / VFR Clear"
            )
            return {
                "cell_id": cid,
                "condition": condition,
                "precipitation_mm": precip,
                "wind_speed_ms": wind,
                "wind_gusts_ms": gusts,
                "temperature_c": temp,
                "cloud_cover_pct": clouds,
                "severity_index": round(severity, 2),
            }

        return {
            "cell_id": cid,
            "condition": "Fair / VFR Clear",
            "precipitation_mm": 0.0,
            "wind_speed_ms": 3.5,
            "wind_gusts_ms": 5.0,
            "temperature_c": 25.0,
            "cloud_cover_pct": 20.0,
            "severity_index": 0.0,
        }

    def get_corridor_congestion(self, lat: float, lon: float, timestamp_utc: datetime) -> str:
        """Fetch corridor congestion category from spatial cells."""
        cid = self.grid.cell_id(lat, lon)
        engine = create_engine(self.settings.database_url)
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT observed_class FROM congestion_observations "
                    "WHERE cell_id = :cid AND window_start_utc <= :ts "
                    "ORDER BY window_start_utc DESC LIMIT 1"
                ),
                {"cid": cid, "ts": timestamp_utc},
            ).fetchone()
        return (row.observed_class if row and row.observed_class else "LOW")

