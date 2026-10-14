# Sky Force: Interactive AI Airspace Intelligence, Dataset-Aware Route Optimization & Explainable Decisions

> **Operational & Safety Disclaimer:**  
> *Sky Force is an academic aviation intelligence and simulation research prototype. It is designed for strategic flow research, decision support, and route trade-off analysis. It is not approved for tactical air traffic separation or certified operational navigation.*

---

## 1. Project Overview & Core Mission

**Sky Force** is an interactive, full-stack aviation intelligence platform that demonstrates the complete data, machine learning, and decision-making pipeline behind modern airspace routing.

Rather than merely calculating a static geometric line between airports, Sky Force makes every routing factor visible, traceable, and explainable:
- Ingests and cleans multi-schema flight telemetry and gridded meteorological data across a **9-stage data quality pipeline**.
- Aggregates airspace into spatial cells ($2.0^\circ$ half-open intervals) and temporal sliding windows ($15\text{ minutes}$) to predict both **corridor congestion** and **airway segment flight duration (ETA)**.
- Solves multi-objective routing using $A^*$ search and **Pareto-optimal frontier discovery** across distance, flight duration, storm cell penalties, and congestion risk.
- Visualizes airspace in synchronous **2D (Leaflet)** and **interactive 3D (MapLibre GL JS + deck.gl)** with zero API tokens or external key dependencies.
- Explains routing decisions through dimensional cost attribution and natural language justifications with local LLM integration (Ollama / Phi-3) and deterministic fallback.

---

## 2. System Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           SKY FORCE MISSION CONSOLE                             │
│                  React 19 + TypeScript + Vite + Tailwind CSS                    │
│      MapLibre GL + deck.gl (3D) • Leaflet (2D) • Recharts • Lucide Icons       │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │ HTTP REST / JSON
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              FASTAPI ASGI BACKEND                               │
│         Pydantic v2 • SQLite (WAL) / PostgreSQL • Structured JSON Logging       │
├───────────────────────┬──────────────────────────┬──────────────────────────────┤
│  SURVEILLANCE & QA    │     MACHINE LEARNING     │    GRAPH ROUTING & SCENARIOS │
│  • 9-Stage Cleanse    │  • Congestion Classifier │  • Multi-Objective A* / Dijs │
│  • Kinematic Filter   │    (RandomForest 3-Class)│  • Pareto Frontier Discovery │
│  • Track Segmentation │  • Segment ETA Regressor │  • Cost Model & Wx Penalty   │
│  • 2° Spatial Grid    │    (RandomForest Target) │  • Hard Disruption Closures  │
│  • CPA Conflict Scan  │  • SHA-256 Registry      │  • Dynamic Reroute Deltas    │
├───────────────────────┴──────────────────────────┴──────────────────────────────┤
│  DATASET STUDIO ENGINE                               EXPLAINABILITY SERVICE     │
│  • Multi-Schema CSV Upload (Flights/Weather/Grid)    • Factor Cost Attribution  │
│  • Spatiotemporal Weather-Flight Linkage             • Ollama / Phi-3 Local LLM │
│  • Dataset-Specific Route Isolation                  • Deterministic Fallback   │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        PERSISTENCE & EVALUATION LAYER                           │
│  • SQLite Database (skyforce.db) with Alembic Versioning                        │
│  • Parquet Archive Storage (Snappy Compressed)                                  │
│  • Structured Evaluation Center (ml/reports/*.csv, *.json, report.html)         │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Key Capabilities & Implemented Features

### 3.1 Multi-Schema Dataset Studio
- **Flexible Ingestion:** Upload and process custom CSVs with explicit schema selection:
  1. *Aircraft Observations* (`source_aircraft_id`, `timestamp_utc`, `latitude`, `longitude`, `altitude_m`, `ground_speed_mps`).
  2. *Weather Observations / Grids* (`latitude`, `longitude`, `valid_time_utc`, `precipitation_mm`, `wind_speed_10m_ms`).
  3. *Pre-aggregated Congestion Grids* (`cell_id`, `window_start_utc`, `aircraft_count`).
- **Interactive Mapping & Preview:** Visual column-mapping interface with real-time error validation.
- **Spatiotemporal Linkage:** Associative spatial grid and temporal window joining between independent flight datasets and weather feeds.
- **Dataset-Aware Optimization:** Parameterized dataset runs ensure route searches evaluate against specific uploaded datasets without unsafe global state mutation.

### 3.2 9-Stage Data Quality & Kinematic Scrubber
Every raw trajectory undergoes 9 sequential filters in `backend/app/services/preprocessing/quality.py`:
1. *Mandatory Header & Type Assertion* (drops missing identifiers or corrupt types).
2. *FIR Airspace Bounding* (bounds within Indian airspace $6.0^\circ\text{N}-38.0^\circ\text{N}$, $68.0^\circ\text{E}-98.0^\circ\text{E}$).
3. *Chronological Validity* (validates timestamps and strictly sorts sequence).
4. *Altitude Physical Envelope* ($-100\text{ m}$ to $15{,}000\text{ m}$).
5. *Ground Speed Envelope* ($0\text{ m/s}$ to $350\text{ m/s}$).
6. *Temporal Deduplication* (purges identical timestamp pings for the same aircraft).
7. *Kinematic Acceleration Limit* ($\Delta v / \Delta t \le 15\text{ m/s}^2$).
8. *Vertical Climb Rate Limit* ($|\Delta \text{alt} / \Delta t| \le 40\text{ m/s}$).
9. *Track Segmentation* (splits flights on transmission gaps $> 1{,}800\text{ seconds}$).

### 3.3 Zero-Key 3D Airspace & Synchronous 2D Maps
- **MapLibre GL JS + deck.gl:** Fully open-source 3D perspective viewer (`frontend/src/components/Airspace3DMap.tsx`).
- **OpenFreeMap Liberty Style:** Public vector basemap requiring **zero API keys or external tokens** (`https://tiles.openfreemap.org/styles/liberty`), backed by an automatic offline raster fallback.
- **Data-Driven 3D Layers:**
  - *Extruded Congestion Columns:* Height driven by model prediction ($\text{score} \times 25{,}000\text{ m}$), colored by class: Green (`LOW`), Amber (`MEDIUM`), Red (`HIGH`).
  - *Extruded Storm Columns:* Height driven by precipitation ($\text{precip\_mm} \times 1{,}200\text{ m}$) with rain intensity gradients.
  - *Elevated 3D Flight Paths:* Great-circle airway trajectories elevated to cruise altitudes ($8{,}000\text{ m} - 10{,}000\text{ m}$).
- **Bidirectional Chart & Inspector Sync:** Selecting an airway segment in 2D or 3D instantly synchronizes the **Along-Track Profile Chart** and the **Segment Cost Inspector**.

### 3.4 Multi-Objective Route Optimization & Pareto Frontier
- **Customizable Objectives:**
  - `distance`: Classical shortest path along Indian airway network.
  - `fastest`: Minimizes predicted segment flight duration.
  - `weather`: Heavy quadratic penalty for convective precipitation storm cells.
  - `congestion`: Avoids sectors predicted to experience high traffic density.
  - `balanced`: Balanced trade-off across time, distance, and environmental risk.
- **Admissible $A^*$ Heuristic:** Great-circle Haversine lower bound guarantees search optimality without overestimating true costs.
- **Pareto Frontier Discovery:** Computes non-dominated alternative candidate routes across competing objectives.
- **Coverage & Missing Data Penalties:** Unobserved weather or congestion regions incur non-zero missing-data penalties, preventing hazardous routes through unmonitored airspace.

### 3.5 Conflict Detection (CPA)
- Linear 3D forward projection scanning for aircraft pairs violating standard separation minimums ($9.26\text{ km}$ / $5\text{ NM}$ horizontal and $300\text{ m}$ / $1{,}000\text{ ft}$ vertical).
- Computes time to closest point of approach ($t_{\text{CPA}}$) and distance at closest point of approach ($d_{\text{CPA}}$).

### 3.6 Explainability with LLM & Deterministic Fallback
- Decomposes edge costs into percentage contributions (Distance, Flight Time, Storm Severity, Traffic Congestion).
- Automatically detects local **Ollama** (`phi3:latest`) for natural language trade-off justifications.
- Gracefully falls back to a deterministic, rule-based expert system if the LLM is absent or times out.

---

## 4. Machine Learning Models & Evaluation

The system trains, registers, and serves two Scikit-Learn pipelines stored with SHA-256 verification in `ml/artifacts/`:

### Model A: Airspace Congestion Classifier
- **Task:** 3-class classification forecasting traffic density proxy in a 2° grid cell for the next 15-minute window ($t + 15\text{ min}$).
- **Architecture:** `RandomForestClassifier` (200 trees, max depth 16, `class_weight='balanced_subsample'`).
- **Features:** 21 tabular features (temporal sin/cos, active aircraft count, causal lags $t-15\text{m}, t-30\text{m}, t-60\text{m}$, 1-hour rolling mean, spatial neighbor loads, wind speed/gusts, and precipitation).
- **Evaluation Performance (Held-out Chronological Test Split, $N = 16{,}999$):**
  - **Accuracy:** `84.70%` (vs Dummy baseline `88.29%` with 0% minority recall)
  - **Balanced Accuracy:** `71.39%`
  - **Macro F1-Score:** `0.6359`
  - **Multi-class Brier Score:** `0.1885`
  - **ROC-AUC (OvR Macro):** `0.9409`
  - **Critical Safety Rate:** When actual traffic is `HIGH`, the model misclassifies as `LOW` only **$1.49\%$ of the time** (9 out of 603 cases).

### Model B: Segment ETA Regressor
- **Task:** Continuous regression estimating airway segment traversal time in **minutes**.
- **Architecture:** `RandomForestRegressor` (200 trees, max depth 18, min samples leaf 2).
- **Features:** 12 features (segment distance, waypoint entry velocity, entry altitude, track bearing, airport departure/arrival flags, along-track headwind, crosswind, rainfall, and cell congestion score).
- **Evaluation Performance (Held-out Chronological Test Split, $N = 4{,}356$):**
  - **Mean Absolute Error (MAE):** **`0.9608 min`** ($\approx 57.6\text{ seconds}$, **71.7% error reduction** vs $3.395\text{ min}$ heuristic baseline)
  - **Root Mean Squared Error (RMSE):** **`1.6007 min`**
  - **Coefficient of Determination ($R^2$):** **`0.9368`** (explains $93.7\%$ of variance vs $48.7\%$ for distance heuristic)
  - **Median Absolute Error:** **`0.4906 min`** ($\approx 29.4\text{ seconds}$)
  - **90th Percentile Bound:** **`2.4672 min`**

---

## 5. Structured Evaluation Reporting & Chart-Ready Exports

Sky Force provides an automated evaluation export engine (`ml/generate_evaluation_reports.py`) that outputs structured numerical tables (CSV, JSON, and HTML) without requiring model retraining:

| Exported Artifact | Schema / Description |
| :--- | :--- |
| `ml/reports/congestion_metrics_summary.csv` | Table A: Overall classification metrics, test sample counts, interpretations |
| `ml/reports/congestion_classification_report.csv` | Table B: Per-class Precision, Recall, F1-Score, and Support for LOW, MED, HIGH |
| `ml/reports/congestion_confusion_matrix.csv` | Table C: Raw $3 \times 3$ held-out test confusion counts |
| `ml/reports/congestion_confusion_matrix_normalized.csv`| Table D: Row-normalized confusion matrix (class recall rates) |
| `ml/reports/congestion_feature_importance.csv` | Top feature rankings via Native MDI and Validation Permutation Importance |
| `ml/reports/congestion_learning_curve_data.csv` | Macro-F1 progression across chronological training subsets ($5\text{k}$ to $42.6\text{k}$ rows) |
| `ml/reports/congestion_model_comparison.csv` | Architecture comparison (Dummy vs Logistic Regression vs RF vs HistGradientBoosting) |
| `ml/reports/eta_metrics_summary.csv` | Table A: MAE, RMSE, $R^2$, Median Absolute Error, Mean Bias, baseline comparisons |
| `ml/reports/eta_error_summary.csv` | Table B: Signed and absolute error distribution percentiles (P10 to P99) |
| `ml/reports/eta_actual_vs_predicted.csv` | Table C: Row-level sample traversals with actual, predicted, and heuristic times |
| `ml/reports/eta_error_by_range.csv` | Table D: Prediction errors stratified across flight duration bins ($<15\text{m}$, $15-25\text{m}$, $25-35\text{m}$, $\ge 35\text{m}$) |
| `ml/reports/eta_feature_importance.csv` | Top feature rankings via Native MDI and Validation Permutation Importance |
| `ml/reports/eta_learning_curve_data.csv` | MAE progression across training subsets ($1\text{k}$ to $10.7\text{k}$ rows) |
| `ml/reports/eta_model_comparison.csv` | Architecture comparison (Heuristic vs Median vs Ridge vs RF vs HistGradientBoosting) |
| `ml/reports/model_metrics_summary.csv` | Consolidated long-form model comparison table |
| `ml/reports/training_summary.json` | Comprehensive metadata, timestamps, splits, and verified artifact hashes |
| `ml/reports/model_evaluation_report.html` | Standalone, pure-table HTML report (zero canvas/SVG graphics) |

---

## 6. Setup & Execution Guide

### 6.1 Prerequisites
- **Python**: `3.11.x` or `3.13.x`
- **Node.js**: `v20+` or `v24+` with `npm`
- **Git**

### 6.2 Backend Installation & Bootstrap

```powershell
# 1. Clone repository
git clone https://github.com/5dishapatil/Sky-Force.git
cd Sky-Force

# 2. Setup Python virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

# 3. Bootstrap database and demo environment
cd backend
python scripts/bootstrap_demo.py

# 4. Train models and generate baseline evaluation artifacts
python scripts/train_models.py

# 5. Run automated test suite (35 tests passing)
pytest tests -v

# 6. Start backend API server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 6.3 Frontend Console Execution

In a separate terminal window:

```powershell
cd frontend
npm install
npm run build    # Verify clean production TypeScript bundling
npm run dev      # Start Vite development server
```

- **Frontend Console:** [http://localhost:5173](http://localhost:5173)
- **Interactive Swagger Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **OpenAPI JSON Spec:** [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

### 6.4 Regenerating Evaluation Reports

To re-export all structured evaluation tables, CSVs, and the standalone HTML report without retraining models:

```powershell
python ml/generate_evaluation_reports.py
```

---

## 7. Automated Test Suite (35 Passing Tests)

The test suite (`pytest backend/tests -v`) validates end-to-end functionality across six test modules:
- `test_api_endpoints.py`: 12 tests validating all FastAPI route contracts, status endpoints, and benchmarks.
- `test_conflict_cpa.py`: 4 tests validating 3D kinematic Closest Point of Approach calculations.
- `test_dataset_and_explanation.py`: 4 tests validating dataset isolation and LLM explanation fallbacks.
- `test_geospatial.py`: 6 tests validating Haversine geodesy, initial bearings, and 2° grid cell half-open indexing.
- `test_multi_schema_and_weather_linking.py`: 4 tests validating multi-schema CSV uploads and spatiotemporal weather linking.
- `test_routing_algorithms.py`: 5 tests validating Dijkstra, $A^*$ admissibility, hard edge closures, and Pareto frontier optimization.

---

## 8. Third-Party Notices & Attribution
- **MapLibre GL JS**: Open-source mapping engine licensed under the 3-Clause BSD License.
- **OpenFreeMap**: Public vector tile basemap hosting based on OpenStreetMap data (`© OpenStreetMap contributors · OpenFreeMap`).
- **deck.gl**: WebGL data-driven geospatial visualization engine developed by the Open Visualization Collaboration (Linux Foundation).
- **OurAirports**: Airport coordinates and metadata dedicated to the Public Domain under The Unlicense.
- **Open-Meteo**: Weather APIs and sample atmospheric feeds licensed under CC BY 4.0.
