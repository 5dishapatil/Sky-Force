"""Regular latitude/longitude research grid.

A cell is a *research aggregation unit*; it is NOT an official ATC sector.

Boundary convention: a point belongs to the cell whose half-open interval
``[lat_min, lat_max) x [lon_min, lon_max)`` contains it. Points on the grid's
outer north/east edge are assigned to the last row/column.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from app.services.geospatial.geo import sample_segment


@dataclass(frozen=True)
class Grid:
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float
    deg: float

    @property
    def n_rows(self) -> int:
        return int(math.ceil((self.lat_max - self.lat_min) / self.deg))

    @property
    def n_cols(self) -> int:
        return int(math.ceil((self.lon_max - self.lon_min) / self.deg))

    def contains(self, lat: float, lon: float) -> bool:
        return self.lat_min <= lat <= self.lat_max and self.lon_min <= lon <= self.lon_max

    def row_col(self, lat: float, lon: float) -> tuple[int, int] | None:
        if not self.contains(lat, lon):
            return None
        r = min(int((lat - self.lat_min) // self.deg), self.n_rows - 1)
        c = min(int((lon - self.lon_min) // self.deg), self.n_cols - 1)
        return r, c

    @staticmethod
    def cell_id_from_rc(r: int, c: int) -> str:
        return f"R{r:02d}C{c:02d}"

    def cell_id(self, lat: float, lon: float) -> str | None:
        rc = self.row_col(lat, lon)
        return None if rc is None else self.cell_id_from_rc(*rc)

    def cell_ids_vec(self, lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
        lat = np.asarray(lat, dtype=float)
        lon = np.asarray(lon, dtype=float)
        inside = (lat >= self.lat_min) & (lat <= self.lat_max) & (lon >= self.lon_min) & (lon <= self.lon_max)
        r = np.clip(((lat - self.lat_min) // self.deg), 0, self.n_rows - 1)
        c = np.clip(((lon - self.lon_min) // self.deg), 0, self.n_cols - 1)
        out = np.empty(lat.shape, dtype=object)
        out[:] = None
        idx = np.where(inside & ~np.isnan(lat) & ~np.isnan(lon))[0]
        for i in idx:
            out[i] = self.cell_id_from_rc(int(r[i]), int(c[i]))
        return out

    def bounds(self, cell_id: str) -> tuple[float, float, float, float]:
        r, c = int(cell_id[1:3]), int(cell_id[4:6])
        lat0 = self.lat_min + r * self.deg
        lon0 = self.lon_min + c * self.deg
        return lat0, min(lat0 + self.deg, self.lat_max), lon0, min(lon0 + self.deg, self.lon_max)

    def center(self, cell_id: str) -> tuple[float, float]:
        a, b, c, d = self.bounds(cell_id)
        return (a + b) / 2, (c + d) / 2

    def cells_along(self, lat1: float, lon1: float, lat2: float, lon2: float, step_km: float = 25.0) -> list[str]:
        seen: list[str] = []
        for la, lo in sample_segment(lat1, lon1, lat2, lon2, step_km):
            cid = self.cell_id(la, lo)
            if cid and cid not in seen:
                seen.append(cid)
        return seen


def grid_from_settings(settings) -> Grid:  # noqa: ANN001
    return Grid(settings.grid_lat_min, settings.grid_lat_max, settings.grid_lon_min, settings.grid_lon_max, settings.grid_deg)
