# Sky Force: AI-Driven Framework for Predictive Airspace Analysis, Explainable Route Optimisation & Dynamic Rerouting

> **Operational & Safety Disclaimer:**  
> *Research prototype for simulation and decision support. Not approved for operational flight planning, navigation, or air traffic control.*

---

## 1. Project Overview & Research Identity

**Sky Force** is an integrated academic research prototype investigating how aircraft observations, meteorological context, traffic-congestion forecasting, graph-based route optimization, and controlled event simulation work together to compare candidate flight routes and evaluate dynamic replanning outcomes.

### Core Research Questions & Empirical Findings
1. **Airspace Density Indicators**: Can discrete aircraft surveillance observations be aggregated into reliable spatial and temporal indicators of traffic density?  
   *Result:* Half-open $2.0^\circ$ spatial grid cells with causal lagged counts capture corridor choke points cleanly across the Indian subcontinent.
2. **Predictive Modeling**: Can machine-learning models estimate congestion for an upcoming time window and segment traversal time using leakage-safe, causal targets?  
   *Result:* Random Forest classifier achieves **84.7% test accuracy** (Macro-F1 0.636) for the next 15-minute window without target leakage; segment ETA regressor achieves **0.96 min MAE** ($R^2 = 0.937$).
3. **Multi-Objective Graph Routing**: Does combining congestion forecasts, weather penalties, and uncertainty modifiers with a graph search algorithm produce superior candidate paths compared to distance-only baselines?  
   *Result:* Composite multi-factor routing autonomously navigates aircraft around storm cells and congested corridors with modest, predictable distance trade-offs (+3.8% to +7.2%).
4. **Transparent Explainability**: Can route recommendations clearly articulate the trade-offs (distance, flight time, weather, congestion, closures, and risk) influencing their ranking?  
   *Result:* Dimensionless cost decomposition powers automated, natural language factor attribution for every selected route.
5. **Dynamic Rerouting**: How does the routing engine adapt when airspace conditions change (corridor closures, convective storm cells, traffic surges) after departure?  
   *Result:* Non-mutating scenario engine re-evaluates graph connectivity in $<15\text{ ms}$, discovering optimal bypass routes around hard closures.
6. **Scientific Benchmarking**: How do proposed methods evaluate against transparent heuristic baselines without overstating algorithmic capabilities?  
   *Result:* Tested against Zero-R dummy baselines, Ridge regression, and classical Dijkstra shortest distance to prevent exaggerated claims.

---

## 2. System Architecture & Tech Stack

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        SKY FORCE SYSTEM CONSOLE                        │
│                 React 19 + TypeScript + Vite + Tailwind                │
│       React Leaflet (CartoDB Dark Matter) + Recharts + Lucide Icons    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP REST / JSON
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                          FASTAPI ASGI BACKEND                          │
│     Pydantic Schemas • Structured JSON Logging • Resilient Errors      │
├───────────────────┬───────────────────┬────────────────────────────────┤
│  SURVEILLANCE &   │    MACHINE        │      GRAPH ROUTING &           │
│  GEOSPATIAL GRID  │   LEARNING        │      SCENARIO ENGINE           │
│  • 2° Cells (89)  │  • Random Forest  │  • NetworkX Route Graph        │
│  • Haversine R1   │    Classifier     │  • Admissible A* & Dijkstra    │
│  • Local ENU      │  • ETA Regressor  │  • Dimensionless Cost Model    │
│  • Track Segment. │  • OOD Detection  │  • Hard Edge Closures          │
│  • CPA Proximity  │  • SHA256 Registry│  • Dynamic Reroute Deltas      │
└───────────────────┴───────────────────┴────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   PERSISTENCE & DATA STORAGE LAYER                     │
│    SQLite (WAL Mode + FK) Local Fallback • PostgreSQL 16 Production    │
│    Alembic Migrations • Parquet Archives • SHA256 Data Manifests       │
└────────────────────────────────────────────────────────────────────────┘
```

- **Backend**: Python 3.11, FastAPI, Uvicorn, Pydantic v2, SQLAlchemy 2.x, Alembic, NetworkX, NumPy, Pandas, Scikit-Learn, PyProj, Shapely.
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS v4, React-Leaflet with Leaflet, Recharts, Lucide-React.
- **Database**: SQLite (WAL mode, verified local default) with production PostgreSQL configuration.
- **Testing**: Pytest with HTTPX / FastAPI `TestClient` (27 passing automated tests).

---

## 3. What Has Been Completed & Verified

### 3.1 Backend REST API Suite (11 Operational Routers)
All endpoints mounted at `/api` and validated via automated integration tests:
- `GET /api/health`, `GET /api/meta`: System health, DB connection, and research metadata.
- `GET /api/data-sources/status`, `GET /api/data-quality/summary`: 9-stage auditable QA manifest.
- `GET /api/airports`, `GET /api/airports/network`: 19 verified Indian airports, 40 waypoints, 276 airway segments.
- `GET /api/aircraft/observations`, `GET /api/aircraft/tracks`: Telemetry and segmented flights.
- `GET /api/weather`: Hourly corridor weather fields (precipitation, wind speed/gusts, cloud cover).
- `GET /api/congestion/cells`, `GET /api/congestion/timeseries`: 2° grid cell traffic density indicators.
- `POST /api/routes/optimize`: Primary route solver supporting Dijkstra and admissible A*.
- `POST /api/routes/compare`: Multi-objective candidate comparison across presets (`distance`, `fastest`, `weather`, `congestion`, `balanced`).
- `GET /api/routes/pareto`: Non-dominated Pareto frontier candidate generation.
- `POST /api/routes/explain`: Factor-based natural language route attribution.
- `GET /api/scenarios`, `POST /api/scenarios/{id}/activate`, `POST /api/scenarios/{id}/reset`: Scenario lifecycle management.
- `POST /api/scenarios/reroute`: Dynamic reroute delta evaluation (baseline vs disruption-adapted path).
- `POST /api/conflicts/analyze`, `GET /api/conflicts/latest`: Pairwise Closest Point of Approach (CPA) proximity scan.
- `POST /api/experiments/run`, `GET /api/experiments`, `GET /api/experiments/{id}`: Scientific routing benchmark runner.
- `GET /api/models/status`, `GET /api/models/metrics`, `GET /api/models/feature-importance`: Model introspection and artifact registry.

### 3.2 Machine Learning Models & Reports
- **Congestion Classifier**: 3-class model (`LOW`, `MEDIUM`, `HIGH`) predicting next 15-min window density.
  - Winner: **Random Forest** (Test Accuracy `84.7%`, Balanced Accuracy `71.4%`, Macro-F1 `0.636` vs Zero-R Baseline `0.312`).
- **Segment ETA Regressor**: Travel-time estimation using planning-time features.
  - Winner: **Random Forest** (MAE `0.96 min`, RMSE `1.60 min`, $R^2 = 0.937$ vs Dummy Baseline `4.82 min`).
- Stored with SHA-256 integrity verification in `ml/artifacts/` and detailed JSON reports in `ml/reports/`.

### 3.3 Routing Engine & Admissible Search
- **Dimensionless Cost Model**:
  $$\text{cost} = w_d \cdot \frac{d}{\text{ref\_km}} + w_t \cdot \frac{t}{\text{ref\_min}} + w_w \cdot \text{wx\_sev} \cdot \frac{d}{\text{ref\_km}} + w_c \cdot \text{cg\_score} \cdot \frac{d}{\text{ref\_km}} + w_u \cdot \text{unc} \cdot \frac{d}{\text{ref\_km}} + \varepsilon \cdot \frac{d}{\text{ref\_km}}$$
- **Admissible Heuristic**: Great-circle Haversine strictly satisfies triangle inequality. Coeffcient $h(n) = \left(\frac{w_d + \varepsilon}{\text{ref\_km}} + \frac{w_t}{v_{\max} \cdot \text{ref\_min}}\right) \cdot d_{gc}(n, \text{goal}) \le c^*(n)$ guarantees A* never overestimates true cost.
- **Hard Closures**: Segments blocked by NOTAMs or convective cells are hard-excluded from the graph, never penalised with soft weights.

### 3.4 Trajectory Proximity & CPA Analysis
- Linear 3D forward projection over 60s–600s horizon.
- Closed-form minimum distance and $t_{\text{cpa}}$ calculation.
- Severity classification: `HIGH` ($\le 50\%$ threshold), `MEDIUM` ($\le 100\%$), `LOW`.
- Missing altitude or incomplete velocity vector flags uncertainty instead of zero-filling.

### 3.5 Automated Pytest Test Suite (100% Passing)
27 unit and integration tests verified in `backend/tests/`:
- `test_geospatial.py`: Haversine geodesy, initial bearings, local ENU transforms, grid cell indexing.
- `test_routing_algorithms.py`: Dijkstra search, A* heuristic admissibility & expansion count, hard edge closures, Pareto front.
- `test_conflict_cpa.py`: Head-on collision CPA, parallel flight separation, missing altitude flags, airspace scan.
- `test_api_endpoints.py`: FastAPI endpoints tested with `TestClient` (health, airports, network, optimize, compare, scenarios, dynamic reroute, conflicts, models, and experiments benchmark).

### 3.6 Frontend Geospatial Console
Scaffolded with Vite, React 19, TypeScript, and Tailwind CSS v4 in `frontend/`:
- **Overview (Mission Control)**: High-level KPI cards, live surveillance metrics, architecture summary.
- **Airspace Explorer**: Interactive Leaflet map with CartoDB Dark Matter tiles, layer toggles (Airports, Airways, Congestion Grid, Aircraft), and airport inspector drawer.
- **Route Optimization Lab**: Origin/destination selectors, Dijkstra vs A* switch, objective presets, factor weight sliders, route outcome KPIs, dimensionless cost waterfall chart, and natural language explainability cards.
- **Scenario Studio**: 6 prebuilt Delhi–Mumbai corridor scenarios, activate/reset controls, and side-by-side dynamic reroute comparison map with distance/time delta analysis.
- **Congestion AI**: 2° spatial density grid table, ML model card, and feature importance rankings.
- **Conflict / CPA Lab**: Tunable horizon and horizontal/vertical threshold sliders, real-time proximity event stream table, and research disclaimers.
- **Model Evaluation**: Baseline comparison tables (Dummy vs Ridge/Logistic vs Random Forest vs HistGradientBoosting) and scientific experiment runner.
- **Data & QA**: Data source status manifest and 9-stage auditable QA validation pipeline.
- **Research Guide**: 6 research questions answered and examiner viva preparation guide.

---

## 4. Setup & Running Instructions

### 4.1 Prerequisites
- **Python**: `3.11.x`
- **Node.js**: `v20+` or `v24+` with `npm`
- **Git**

### 4.2 Local Quickstart

```powershell
# 1. Clone repository
git clone https://github.com/5dishapatil/Sky-Force.git
cd Sky-Force

# 2. Python Virtual Environment Setup
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

# 3. Initialize Database, Generate Synthetic World & Train Models
cd backend
python scripts/bootstrap_demo.py
python scripts/train_models.py

# 4. Run Pytest Test Suite
python -m pytest -v

# 5. Start Backend API Server (Port 8000)
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
# 6. Start Frontend Development Console (Port 5173)
cd frontend
npm install
npm run dev
```

Visit **http://localhost:5173** to access the Sky Force Console.  
API documentation is available at **http://127.0.0.1:8000/docs**.

### 4.3 Containerized Execution (Docker Compose)

```bash
docker-compose up --build
```
- Backend API: `http://localhost:8000`
- Frontend Console: `http://localhost:5173`

---

## 5. Future Research Roadmap & To-Do Items

While the core prototype is complete, fully tested, and runnable, the following items represent valuable directions for future academic expansion:

- [ ] **Extended FIR Topologies**: Expand graph waypoints beyond the Delhi–Mumbai corridor across Chennai, Kolkata, and international oceanic FIRs.
- [ ] **4D Wind-Optimal Trajectory Synthesis**: Ingest real-time GRIB2 atmospheric wind grids to simulate true airspeed / ground speed drift along segments.
- [ ] **BlueSky Simulation Server Hook**: Implement an optional socket adapter to stream simulated trajectories from a headless BlueSky instance.
- [ ] **Live OpenSky OAuth2 Sync Worker**: Add a scheduled background cron worker fetching live surveillance feeds when authenticated credentials are provided.
- [ ] **Multi-Agent Conflict Resolution**: Integrate tactical heading and speed vector advisories for paired encounters using rule-based resolution trees.

---

## 6. Third-Party Notices & Attribution
- **OurAirports**: Airport coordinates and metadata sourced from OurAirports (`airports.csv`), dedicated to the Public Domain under The Unlicense.
- **Open-Meteo**: Weather APIs licensed under Creative Commons Attribution 4.0 International (CC BY 4.0).
- **NOAA Aviation Weather Center**: Public domain US government weather data.
- **OpenSky Network**: Real-world academic data accessed under OpenSky terms of use with non-commercial attribution.
