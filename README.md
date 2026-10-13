# Sky Force: AI-Driven Predictive Airspace Analysis, Explainable Route Optimisation & Dynamic Rerouting

> **Operational & Safety Disclaimer:**  
> *Research prototype for simulation and decision support. Not approved for operational flight planning, navigation, or air traffic control.*

---

## 1. Project Overview & Research Identity

**Sky Force** is an academic research prototype investigating how aircraft observations, meteorological context, traffic-congestion forecasting, graph-based route optimization, and controlled event simulation work together to compare candidate flight routes and evaluate dynamic replanning outcomes.

### Core Research Questions
1. **Airspace Density Indicators**: Can discrete aircraft surveillance observations be aggregated into reliable spatial and temporal indicators of traffic density?
2. **Predictive Modeling**: Can machine-learning models estimate congestion for an upcoming time window and segment traversal time using leakage-safe, causal targets?
3. **Multi-Objective Graph Routing**: Does combining congestion forecasts, weather penalties, and uncertainty modifiers with a graph search algorithm produce superior candidate paths compared to distance-only baselines?
4. **Transparent Explainability**: Can route recommendations clearly articulate the trade-offs (distance, flight time, weather, congestion, closures, and risk) influencing their ranking?
5. **Dynamic Rerouting**: How does the routing engine adapt when airspace conditions change (corridor closures, convective storm cells, traffic surges) after departure?
6. **Scientific Benchmarking**: How do proposed methods evaluate against transparent heuristic baselines without overstating algorithmic capabilities?

---

## 2. What Has Been Completed So Far

### 2.1 Reference Audit & API Specifications
- Audited reference architectures:
  - `hemalii3/Flight-Route-Optimization-System`: Java/Spring Boot routing engine, multi-attribute cost formulations, temporal edge-closure pruning, and admissible great-circle A* heuristics.
  - `TUDelft-CNS-ATM/bluesky`: ATM simulator, headless server integration, performance coefficients.
  - `open-aviation/atmdata`, `fvalka/atc-reinforcement-learning`, `RonitM2k06/AeroLattice`, `EduMartinezz/Machine-Learning-Driven-Air-Traffic-Management`.
- Analyzed and documented external API specifications:
  - **OpenSky Network REST API**: OAuth2 Client Credentials token flow, `/states/all` 18-element state vector, and anonymous rate credit limits.
  - **Open-Meteo Historical Weather API**: Verified `/v1/archive` hourly variables and CC BY 4.0 terms.
  - **NOAA Aviation Weather Center API**: `/api/data/metar` endpoint parameters and rate limits.
  - **OurAirports Data**: Public domain repository (`Unlicense`) and schema.

### 2.2 Core Infrastructure & Security
- **Python 3.11 Environment & Packaging**: Pinned dependencies in [`backend/pyproject.toml`](backend/pyproject.toml) and [`requirements.txt`](requirements.txt).
- **Security & Git Ignore Rules**: [`.gitignore`](.gitignore) and [`.env.example`](.env.example) strictly isolate API keys, OAuth tokens, `.env` files, local databases (`*.db`, `*.sqlite`), and cached data dumps.
- **Typed Configuration**: [`backend/app/core/config.py`](backend/app/core/config.py) using `pydantic-settings` (`SKYFORCE_` prefix) defining database URLs, Indian subcontinent research grid parameters (`6°N–34°N`, `66°E–94°E`, `2.0°` cells, 15-minute windows), heuristic cruise speeds, and API endpoints.
- **Structured JSON Logging**: [`backend/app/core/logging.py`](backend/app/core/logging.py) emitting structured JSON-lines logs with ISO-8601 UTC millisecond timestamps.
- **API Error Model**: [`backend/app/core/errors.py`](backend/app/core/errors.py) providing a standardized error model that never leaks raw stack traces to clients.

### 2.3 Database Layer & Migrations
- **SQLAlchemy 2.x ORM Models**: [`backend/app/db/models.py`](backend/app/db/models.py) with 15 entity tables covering airports, waypoints, route edges, inferred tracks, aircraft observations, weather observations, spatial cells, congestion observations, scenarios, scenario events, model metadata, experiment runs, and route evaluations. All tables feature source and synthetic provenance columns.
- **Alembic Migrations**: Fully configured in [`backend/alembic.ini`](backend/alembic.ini) and [`backend/alembic/`](backend/alembic/). Migration `0001_initial_schema.py` automatically generated and applied.
- **Session Management**: [`backend/app/db/session.py`](backend/app/db/session.py) supporting SQLite with WAL mode and foreign key enforcement alongside production PostgreSQL.

### 2.4 Geospatial & Spatial Grid Engine
- **Spherical Geodesy**: [`backend/app/services/geospatial/geo.py`](backend/app/services/geospatial/geo.py) implementing Haversine formula on mean Earth radius ($R_1 = 6371.0088\text{ km}$), initial bearing calculation, great-circle interpolation, along-track projections, and local ENU conversions.
- **Research Grid**: [`backend/app/services/geospatial/grid.py`](backend/app/services/geospatial/grid.py) implementing a configurable latitude/longitude grid with half-open boundary intervals `[lat_min, lat_max) × [lon_min, lon_max)`, vectorised point-to-cell assignment, 8-neighbor adjacency lookup, and great-circle segment cell traversal.

### 2.5 Resilient Data Ingestion & Bootstrap World
- **Resilient HTTP Client**: [`backend/app/services/ingestion/http.py`](backend/app/services/ingestion/http.py) with exponential backoff retry and thread-safe per-source rate throttling.
- **OurAirports Ingestion**: [`backend/app/services/ingestion/ourairports.py`](backend/app/services/ingestion/ourairports.py) caching 19 verified Indian airports in [`data/reference/airports_subset.csv`](data/reference/airports_subset.csv) with SHA-256 provenance in [`data/reference/airports_subset.meta.json`](data/reference/airports_subset.meta.json).
- **Deterministic Synthetic World Generator**: [`backend/app/services/ingestion/synthetic_demo.py`](backend/app/services/ingestion/synthetic_demo.py) generating 40 waypoints, 276 candidate segments, 89 corridor cells, 17,622 hourly weather records (with 4 moving storm systems), 3,678 flights across 107 aircraft (~276,000 position observations), and a logged ground-truth fault injector.
- **Automated Bootstrap Pipeline**: [`backend/app/services/ingestion/bootstrap.py`](backend/app/services/ingestion/bootstrap.py) & [`backend/scripts/bootstrap_demo.py`](backend/scripts/bootstrap_demo.py) providing an idempotent CLI command to initialize database tables, generate data, run quality cleaning, segment tracks, and write [`data/source_manifest.json`](data/source_manifest.json).

### 2.6 Data Quality & Leakage-Safe Feature Engineering
- **9-Stage Cleaning Pipeline**: [`backend/app/services/preprocessing/quality.py`](backend/app/services/preprocessing/quality.py) detecting invalid timestamps, out-of-order delivery, duplicates, coordinate violations, implausible speeds, altitude boundaries, and telemetry gaps without silently dropping records.
- **Track Segmentation**: Grouping continuous observations into inferred tracks (`<aircraft_id>-T<seq>`) using a 30-minute gap threshold.
- **Congestion Features**: [`backend/app/services/features/congestion.py`](backend/app/services/features/congestion.py) with causal lag features, 8-neighbor spatial context, cyclical hour encodings, causal weather alignment, and training-only quantile threshold derivation (`LOW`, `MEDIUM`, `HIGH`).
- **Segment-ETA Features**: [`backend/app/services/features/eta.py`](backend/app/services/features/eta.py) extracting observed traversals from node passages (25 km radius with along-track projection) and computing entry-time features.
- **Chronological Partitions**: [`backend/app/services/features/splits.py`](backend/app/services/features/splits.py) enforcing boundary-purged chronological train/validation/test splits.

### 2.7 Machine Learning Pipelines & Artifact Registry
- **Checksum-Verified Registry**: [`backend/app/services/models/registry.py`](backend/app/services/models/registry.py) ensuring only validated models matching training SHA-256 hashes are loaded, with out-of-distribution feature flagging.
- **3-Class Congestion Classifier**: [`backend/app/services/models/training.py`](backend/app/services/models/training.py) training Dummy, Logistic Regression, Random Forest, and HistGradientBoosting models, selecting the best model via validation Macro-F1 score, and generating confusion matrices and calibration reliability curves.
- **Segment-ETA Regressor**: [`backend/app/services/models/training.py`](backend/app/services/models/training.py) benchmarking Ridge, Random Forest, and HistGradientBoosting models against heuristic distance/speed baselines with MAE, RMSE, and $R^2$ metrics.
- **Pipeline Runner & CLI**: [`backend/app/services/models/pipeline.py`](backend/app/services/models/pipeline.py) & [`backend/scripts/train_models.py`](backend/scripts/train_models.py).

### 2.8 Route Graph, Cost Model & Optimisation
- **NetworkX Route Graph**: [`backend/app/services/routing/graph.py`](backend/app/services/routing/graph.py) representing airport and waypoint nodes and candidate segments with scale normalization references.
- **Dimensionless Cost Model**: [`backend/app/services/routing/cost_model.py`](backend/app/services/routing/cost_model.py) combining normalized distance, time, weather exposure, congestion penalties, and data uncertainty. Enforces hard edge exclusions for closed segments.
- **Search Algorithms**: [`backend/app/services/routing/search.py`](backend/app/services/routing/search.py) implementing Dijkstra and goal-directed A* with provably admissible heuristic lower bounds and node expansion counters.
- **Route Planner & Alternatives**: [`backend/app/services/routing/planner.py`](backend/app/services/routing/planner.py) generating primary routes, labeled objective alternatives (`distance`, `fastest`, `weather`, `congestion`, `balanced`), and non-dominated Pareto candidates.
- **Natural Language Explanations**: [`backend/app/services/routing/explain.py`](backend/app/services/routing/explain.py) deriving human-readable rationale statements directly from route attributes and baseline comparisons.
- **Context Provider**: [`backend/app/services/routing/providers.py`](backend/app/services/routing/providers.py) dynamically assembling per-edge contexts from weather and ML predictions with graceful heuristic fallbacks.

### 2.9 Scenario Engine & Dynamic Rerouting
- **Event Applicator**: [`backend/app/services/scenario_engine/events.py`](backend/app/services/scenario_engine/events.py) applying non-mutating event transformations (edge closures, restricted polygons, traffic surges, weather penalty zones, stale data).
- **Prebuilt Demonstration Scenarios**: [`backend/app/services/scenario_engine/prebuilt.py`](backend/app/services/scenario_engine/prebuilt.py) providing 6 deterministic scenarios on the Delhi–Mumbai corridor (`clear`, `corridor-congestion`, `corridor-closure`, `weather-zone`, `combined`, `restricted-area`).

---

## 3. Remaining Tasks (To-Do Roadmap)

The remaining work is structured into the following focused milestones:

### ⬜ Phase 1: REST API Endpoints (FastAPI)
- [ ] Health and System Metadata: `GET /api/health`, `GET /api/meta`, `GET /api/data-sources/status`.
- [ ] Airspace Data: `GET /api/airports`, `GET /api/aircraft/observations`, `GET /api/weather`, `GET /api/data-quality/summary`.
- [ ] Congestion Intelligence: `GET /api/congestion/cells`, `GET /api/congestion/timeseries`, `POST /api/congestion/predict`.
- [ ] Route Optimisation: `POST /api/routes/optimize`, `POST /api/routes/compare`, `GET /api/routes/pareto`, `POST /api/routes/explain`.
- [ ] Scenario Management: `GET /api/scenarios`, `POST /api/scenarios`, `POST /api/scenarios/{id}/activate`, `POST /api/scenarios/{id}/reset`, `POST /api/scenarios/{id}/reroute`.
- [ ] Experiments & Evaluations: `POST /api/experiments/run`, `GET /api/experiments`, `GET /api/experiments/{id}/report`.

### ⬜ Phase 2: Simplified Conflict & Proximity Lab
- [ ] Relative-motion pairwise analysis computing closest-point-of-approach (CPA), horizontal distance, and vertical separation over forecast horizons.
- [ ] Configurable prototype proximity thresholds (labeled research proxies, not certified ATC standards).
- [ ] Uncertainty and stale surveillance flagging.

### ⬜ Phase 3: Automated Test Suite (Pytest)
- [ ] **Geospatial & Graph Tests**: Haversine triangle inequality, bearing calculations, grid cell boundary assignments.
- [ ] **Routing Tests**: Dijkstra optimality, A* heuristic admissibility ($h(n) \le c^*(n)$), closure exclusion, disconnected graph handling, invalid weight rejection.
- [ ] **Data Quality & ML Tests**: Time-leakage validation, duplicate handling, schema validation, artifact checksum verification.
- [ ] **Scenario Engine Tests**: Event activation, edge blocking, reset verification.
- [ ] **API Tests**: FastAPI `TestClient` route validation and error status codes.

### ⬜ Phase 4: Frontend Geospatial Console (React + TypeScript)
- [ ] Setup React + Vite + Tailwind CSS + Lucide React frontend shell.
- [ ] **Airspace Explorer**: Interactive Leaflet map displaying airport nodes, candidate segments, route paths, congestion heatmaps, and simulated restriction polygons.
- [ ] **Route Lab UI**: Origin/destination selectors, algorithm switches (Dijkstra vs. A*), objective weight sliders, route alternative cards, and segment cost waterfall charts.
- [ ] **Scenario Studio UI**: Prebuilt scenario activator, synthetic event builder, and side-by-side rerouting comparison panel.
- [ ] **Congestion & ML Dashboard**: Time-series charts, confusion matrix, and feature importance bar charts using Recharts.

### ⬜ Phase 5: Containerization & Complete Documentation
- [ ] `Dockerfile` for backend and frontend.
- [ ] `docker-compose.yml` linking FastAPI backend, Vite frontend, and PostgreSQL.
- [ ] Academic Viva Guide ([`docs/viva_guide.md`](docs/viva_guide.md)) with Mermaid architecture, ML, and routing sequence diagrams.

---

## 4. Setup & Running Instructions

### 4.1 Prerequisites
- **Python**: `3.11.x`
- **Node.js**: `v20+` or `v24+` with `npm`
- **Git**

### 4.2 Installation & Initialization

```powershell
# 1. Clone repository
git clone https://github.com/5dishapatil/Sky-Force.git
cd Sky-Force

# 2. Set up virtual environment and install dependencies
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt

# 3. Initialize database, generate synthetic world, and seed scenarios
cd backend
python scripts/bootstrap_demo.py

# 4. Train machine learning models
python scripts/train_models.py
```

### 4.3 Verifying Completed Modules

To verify the routing engine and scenario closures directly from Python:

```powershell
python -c "
from app.core.config import get_settings
from app.db.session import session_scope
from app.services.routing.graph import build_graph
from app.services.routing.planner import RoutePlanner
from app.services.routing.cost_model import CostWeights
from app.services.routing.providers import ContextBuilder, DataStore
from app.services.scenario_engine.events import apply_events
from app.services.geospatial.grid import grid_from_settings
import pandas as pd

s = get_settings()
print('Sky Force environment verified successfully!')
"
```

---

## 5. Third-Party Notices & Data Attribution
- **OurAirports**: Airport coordinates and metadata sourced from OurAirports (`airports.csv`), dedicated to the Public Domain under The Unlicense.
- **Open-Meteo**: Weather APIs licensed under Creative Commons Attribution 4.0 International (CC BY 4.0).
- **NOAA Aviation Weather Center**: Public domain US government weather data.
- **OpenSky Network**: Real-world academic data accessed under OpenSky terms of use with non-commercial attribution.
