# Sky Force: An AI-Driven Framework for Predictive Airspace Analysis, Explainable Route Optimisation, and Dynamic Rerouting

> **Operational & Safety Disclaimer:**  
> *Research prototype for simulation and decision support. Not approved for operational flight planning, navigation, or air traffic control.*

---

## 1. Project Identity & Purpose

**Sky Force** is an academic research prototype that investigates how historical and simulated aircraft observations, weather context, traffic-congestion prediction, graph-based route planning, and controlled event simulation can work together to compare candidate routes and estimate route outcomes.

### Core Research Questions
1. Can historical aircraft-position observations be transformed into useful spatial and temporal indicators of traffic density?
2. Can machine-learning models estimate congestion for a future time window and estimate segment travel time using properly defined, leakage-safe targets?
3. Does combining congestion estimates and weather-related cost modifiers with a graph-based planner produce more suitable candidate routes than distance-only routing under defined experimental conditions?
4. Can a route recommendation explain the cost, time, weather, congestion, closure, and risk factors that influenced its ranking?
5. How does a route planner behave when conditions change after a route is initially calculated?
6. How can these hypotheses be evaluated against transparent baseline methods without overstating the capabilities of the prototype?

---

## 2. Work Completed So Far

### 2.1 Reference Repository & Aviation API Investigation
Before writing application code, we audited the reference repositories and live public aviation APIs:

- **Primary Route-Optimisation Reference (`hemalii3/Flight-Route-Optimization-System`)**: Reviewed its graph model of airport nodes and directed flight segments, multi-factor cost formulation (`fuelCost + overflightCharge + weatherPenalty`), temporal edge-closure rules, admissible great-circle A* heuristic, and label-setting Pareto route search.
- **Air Traffic Simulation (`TUDelft-CNS-ATM/bluesky`)**: Verified Python packaging (`bluesky-simulator`), headless simulation support, and MIT licensing.
- **Open Aviation Data & ML References (`open-aviation/atmdata`, `fvalka/atc-reinforcement-learning`, `RonitM2k06/AeroLattice`, `EduMartinezz/Machine-Learning-Driven-Air-Traffic-Management`)**: Inspected kinematic feature formulations, spatial conflict proximity thresholds, and trajectory preprocessing conventions.
- **External API Specifications Audited**:
  - **OpenSky Network REST API**: Verified `/states/all` 18-field state vector schema, bounding-box query parameters (`lamin`, `lomin`, `lamax`, `lomax`), OAuth2 Client Credentials token flow, and anonymous rate/credit limits.
  - **Open-Meteo Historical Weather API**: Verified `/v1/archive` hourly variables (`temperature_2m`, `relative_humidity_2m`, `surface_pressure`, `precipitation`, `cloud_cover`, `wind_speed_10m`, `wind_direction_10m`, `wind_gusts_10m`, `wind_speed_100m`) and CC BY 4.0 non-commercial terms.
  - **NOAA Aviation Weather Center API**: Verified `/api/data/metar` endpoint parameters and rate limits.
  - **OurAirports Reference Dataset**: Verified public-domain dedication (`Unlicense`) and canonical CSV schema.

---

### 2.2 Backend Environment & Packaging
- Initialised the repository and Python `3.11.9` virtual environment.
- Created [`backend/pyproject.toml`](backend/pyproject.toml) and root [`requirements.txt`](requirements.txt) with pinned, verified dependencies (`fastapi`, `uvicorn`, `pydantic`, `pydantic-settings`, `pandas`, `numpy`, `scikit-learn`, `scipy`, `networkx`, `shapely`, `pyproj`, `joblib`, `httpx`, `SQLAlchemy`, `alembic`, `pyarrow`, `pytest`).
- Configured [`.gitignore`](.gitignore) and [`.env.example`](.env.example) so that API keys, OAuth2 client secrets, `.env` files, cached external API payloads, virtual environments, and local SQLite database files are never committed to Git.

---

### 2.3 Core Infrastructure (`backend/app/core/`)
- **[`config.py`](backend/app/core/config.py)**: Centralised typed `Settings` (`pydantic-settings`) using the `SKYFORCE_` environment variable prefix. Configures:
  - SQLite local fallback (`data/skyforce.db`) and PostgreSQL connection URLs.
  - Research grid bounds covering the Indian subcontinent (`6.0°N–34.0°N`, `66.0°E–94.0°E`, `2.0°` cell resolution, `15`-minute aggregation windows).
  - Heuristic cruise speed (`780.0 km/h`) and deterministic seed (`20260115`).
  - External API base URLs, timeouts, retry counts, and rate-limit intervals.
- **[`logging.py`](backend/app/core/logging.py)**: Structured JSON-lines logger (`JsonFormatter`) emitting UTC millisecond timestamps and structured context fields.
- **[`errors.py`](backend/app/core/errors.py)**: Standardized API error hierarchy (`SkyForceError`, `NotFoundError`, `ValidationFailed`, `ModelUnavailableError`, `ExternalSourceError`, `RateLimitedError`) and FastAPI exception handlers returning `{"error": {"code": ..., "message": ..., "details": ...}}` without leaking internal stack traces.

---

### 2.4 Database Schema & Session Management (`backend/app/db/`)
- **[`models.py`](backend/app/db/models.py)**: SQLAlchemy 2.x declarative ORM models with explicit provenance (`source`, `dataset`, `is_synthetic`) and composite indexes across 15 entity classes:
  - `Airport`, `Waypoint`, `RouteEdge`
  - `InferredTrack`, `AircraftObservation`, `WeatherObservation`
  - `SpatialCell`, `CongestionObservation`
  - `Scenario`, `ScenarioEvent`
  - `ModelArtifactMetadata`, `ExperimentRun`, `RouteEvaluation`
  - `DataSourceSnapshot`, `ConflictAnalysisRun`
- **[`session.py`](backend/app/db/session.py)**: Database engine and session factory supporting both SQLite (with `PRAGMA journal_mode=WAL` and `PRAGMA foreign_keys=ON`) and PostgreSQL, plus `as_utc()` timezone normalisation.

---

### 2.5 Geospatial & Research Grid Engine (`backend/app/services/geospatial/`)
- **[`geo.py`](backend/app/services/geospatial/geo.py)**: Spherical geodesy utilities using IUGG mean Earth radius ($R_1 = 6371.0088\text{ km}$):
  - `haversine_km` & vectorised `haversine_km_vec` (strictly satisfies the triangle inequality required for A* heuristic admissibility).
  - `initial_bearing_deg`, `interpolate_gc`, `sample_segment`, `destination_point`, `angle_diff_deg`, and local tangent-plane projection `local_enu_km`.
- **[`grid.py`](backend/app/services/geospatial/grid.py)**: Configurable spatial research grid (`Grid`) with documented half-open cell boundaries `[lat_min, lat_max) × [lon_min, lon_max)`, vectorised coordinate-to-cell mapping (`cell_ids_vec`), cell bounding boxes/centres, and great-circle segment cell traversal (`cells_along`).

---

### 2.6 Resilient Data Ingestion & Deterministic Synthetic World (`backend/app/services/ingestion/`)
- **[`http.py`](backend/app/services/ingestion/http.py)**: Shared HTTP client featuring thread-safe per-source rate throttling (`throttle`) and exponential backoff retry (`request_with_retry`) handling HTTP `429` and `5xx` responses cleanly.
- **[`ourairports.py`](backend/app/services/ingestion/ourairports.py) & [`scripts/ingest_airports.py`](backend/scripts/ingest_airports.py)**: Downloads the public-domain OurAirports dataset (`86,236` global rows inspected), extracts 19 major Indian airports (`VIDP`, `VABB`, `VOBL`, `VOMM`, `VOHS`, `VECC`, `VAAH`, `VAPO`, `VOGO`, `VIJP`, `VILK`, `VANP`, `VABP`, `VOCI`, `VEBS`, `VAID`, `VIAR`, `VEGT`, `VOTV`), and caches them offline in [`data/reference/airports_subset.csv`](data/reference/airports_subset.csv) with SHA-256 checksum and retrieval metadata in [`data/reference/airports_subset.meta.json`](data/reference/airports_subset.meta.json).
- **[`synthetic_demo.py`](backend/app/services/ingestion/synthetic_demo.py)**: Seeded, reproducible synthetic demonstration world generator (`generate_world`) producing:
  - **40 synthetic research waypoints** (`SFW01`–`SFW40`) and **276 directed candidate segments** (`k=4` nearest-neighbour graph with guaranteed weak connectivity).
  - **89 active corridor grid cells** and **17,622 hourly synthetic weather records** over an 8-day period, including 4 moving storm systems and a dimensionless `weather_severity` proxy in $[0, 1]$.
  - **3,678 synthetic flights** across **107 synthetic aircraft** (`SF0001`–`SF0107`, callsigns `SFDxxx`) generating **~276,000 position observations** at 90-second intervals with diurnal IST departure profiles, corridor traffic surges, wind tailwind/headwind effects, and two-pass congestion slowdowns.
  - **Logged Data-Fault Injector (`inject_faults`)**: Deterministically injects and logs ground-truth faults (`missing_altitude`, `invalid_coordinate`, `position_jump`, `implausible_speed`, `duplicate`, `dropout_gap`, `out_of_order`) to validate the data-quality pipeline.

---

### 2.7 Auditable Data Quality & Track Segmentation (`backend/app/services/preprocessing/`)
- **[`quality.py`](backend/app/services/preprocessing/quality.py)**:
  - `run_quality()`: 9-stage cleaning and validation pipeline that never silently drops data or zero-fills unknown altitudes. Produces a structured `QualityReport` tracking input rows, retained rows, dropped counts (`invalid_timestamp`, `duplicate`, `invalid_coordinate`, `position_jump`), flagged counts (`out_of_order_delivery`, `implausible_speed`, `implausible_altitude`, `missing_altitude`, `gap_gt_5min`, `track_break_gt_30min`), and per-column missingness percentages.
  - `segment_tracks()`: Infers continuous flight tracks (`<aircraft_id>-T<seq>`) using a 30-minute observation gap threshold and records segmentation metadata.

---

### 2.8 Leakage-Safe Feature Engineering (`backend/app/services/features/`)
- **[`congestion.py`](backend/app/services/features/congestion.py)**:
  - Aggregates unique aircraft counts (`aircraft_count`) and position report counts (`observation_count`) per `(cell_id, 15-min window)`.
  - Builds strictly causal lag features (`count_lag1`, `count_lag2`, `count_lag4`, `count_roll4_mean`, `traffic_change`), 8-neighbour spatial traffic counts (`neighbor_count`, `neighbor_count_lag1`), cyclical hour encodings (`hour_sin`, `hour_cos`), and causal hourly weather alignment (`floor(window_start, 1h)`).
  - Derives `LOW` / `MEDIUM` / `HIGH` research congestion thresholds (`q50` and `q85` of occupied windows) **exclusively on the training split** (`thresholds_from_training`).
  - Implements chronological train/validation/test partitioning (`chronological_split`) with target-window boundary purging so target windows never leak across split boundaries.
- **[`eta.py`](backend/app/services/features/eta.py)**:
  - `extract_traversals()`: Detects graph node passages within a 25 km radius, refines passage timestamps via along-track projection, filters out segments with internal telemetry gaps $> 300\text{ s}$, and computes `observed_segment_time_min`.
  - `build_eta_features()`: Attaches entry-time-only features (`segment_distance_km`, `bearing_sin`, `bearing_cos`, `hour_sin`, `hour_cos`, `from_airport`, `to_airport`, `entry_speed_mps`, `entry_altitude_m`, `tailwind_proxy_ms`, `weather_severity`, `corridor_count_prev_window`).

---

## 3. Repository Structure

```text
sky-force/
├── README.md
├── requirements.txt
├── .gitignore
├── .env.example
├── data/
│   └── reference/
│       ├── airports_subset.csv
│       └── airports_subset.meta.json
└── backend/
    ├── pyproject.toml
    ├── scripts/
    │   └── ingest_airports.py
    ├── app/
    │   ├── core/
    │   │   ├── config.py
    │   │   ├── logging.py
    │   │   └── errors.py
    │   ├── db/
    │   │   ├── models.py
    │   │   └── session.py
    │   ├── services/
    │   │   ├── geospatial/
    │   │   │   ├── geo.py
    │   │   │   └── grid.py
    │   │   ├── ingestion/
    │   │   │   ├── http.py
    │   │   │   ├── ourairports.py
    │   │   │   └── synthetic_demo.py
    │   │   ├── preprocessing/
    │   │   │   └── quality.py
    │   │   ├── features/
    │   │   │   ├── congestion.py
    │   │   │   └── eta.py
    │   │   ├── models/
    │   │   ├── routing/
    │   │   ├── scenario_engine/
    │   │   ├── conflict_analysis/
    │   │   └── evaluation/
    │   ├── api/
    │   │   └── routes/
    │   ├── schemas/
    │   ├── repositories/
    │   └── utils/
    └── tests/
```

---

## 4. Requirements & Setup

### Prerequisites
- **Python**: `3.11` (verified on Python `3.11.9`)
- **Git**: `2.x+`

### Installation

```powershell
# 1. Create and activate a Python 3.11 virtual environment
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install required dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 3. (Optional) Copy environment configuration template
Copy-Item .env.example .env
```

### Refreshing Reference Airport Data (Optional — Cached Subset Included)
```powershell
cd backend
..\.venv\Scripts\python.exe scripts\ingest_airports.py
```

### Quick Smoke Test of Synthetic World & Feature Engineering
```powershell
cd backend
..\.venv\Scripts\python.exe -c "
from app.core.config import get_settings
from app.services.ingestion.ourairports import load_subset
from app.services.ingestion.synthetic_demo import generate_world
from app.services.geospatial.grid import grid_from_settings
from app.services.preprocessing.quality import run_quality, segment_tracks

s = get_settings()
df, _ = load_subset()
ap = df.rename(columns={'ident': 'node_id', 'latitude_deg': 'latitude', 'longitude_deg': 'longitude'})
w = generate_world(ap, grid_from_settings(s), s.demo_start_utc, s.demo_days, s.demo_flights_per_day, s.demo_sample_seconds, s.window_minutes, s.demo_seed)
clean_obs, report = run_quality(w.observations)
tracked_obs, tracks = segment_tracks(clean_obs)
print('Waypoints:', len(w.waypoints), 'Edges:', len(w.edges), 'Retained Obs:', report.retained_rows, 'Inferred Tracks:', len(tracks))
"
```

---

## 5. Security & Git Ignore Policy

All external API credentials, tokens, `.env` files, local databases, and raw/cached API responses are excluded via [`.gitignore`](.gitignore):
- `.env`, `.env.*` (except `.env.example`)
- `*credentials*.json`, `*secret*`, `*token*.json`, `*api_key*`, `*.pem`, `*.key`
- `data/raw/`, `data/interim/`, `data/processed/`, `data/synthetic/`, `data/cache/`, `*api_cache*`
- `*.db`, `*.sqlite`, `*.sqlite3`
- `.venv/`, `__pycache__/`, `node_modules/`, `*.joblib`
