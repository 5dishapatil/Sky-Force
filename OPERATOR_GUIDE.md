# Sky Force — Operator Navigation & Execution Guide

Welcome to **Sky Force**, an interactive full-stack AI Airspace Intelligence and Dynamic Route Optimization platform.

This guide provides a clear, step-by-step walkthrough explaining **how the system works**, **how to navigate each screen**, and **how to operate the end-to-end routing and ML features**.

---

## 1. Quick Start: Launching the Applications

To operate Sky Force locally, run the backend API server and the frontend console in two separate terminals.

### Terminal 1: Backend API Server
```powershell
cd backend
..\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
- **FastAPI Interactive Swagger Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **API Health Check:** [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)

### Terminal 2: Mission Console (Frontend)
```powershell
cd frontend
npm run dev
```
- **Sky Force Mission Console:** [http://localhost:5173](http://localhost:5173)

---

## 2. Standard 5-Step Operator Workflow

When you open [http://localhost:5173](http://localhost:5173), follow this sequential pipeline to experience the full intelligence system:

```text
┌─────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│ 01 · DATASET    │ ──> │ 02 · AIRSPACE       │ ──> │ 03 · SCENARIO       │
│     STUDIO      │     │     EXPLORER        │     │     STUDIO          │
│ Ingest & Link   │     │ 2D & 3D Perspective │     │ Inject Disruptions  │
└─────────────────┘     └─────────────────────┘     └─────────────────────┘
                                                               │
                                                               ▼
┌─────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│ 06 · DELAY AI   │ <── │ 05 · AI INTEL       │ <── │ 04 · ROUTE          │
│   & PASSENGER   │     │     & METRICS       │     │     OPTIMIZATION    │
│ Multi-Role Hub  │     │ Explain & Verify    │     │ A* & Pareto Frontier│
└─────────────────┘     └─────────────────────┘     └─────────────────────┘
```

---

### Step 1: Ingest & Select Telemetry (Dataset Studio & Lifecycle)
- **Navigation:** Click **Dataset Studio** or **Dataset Lifecycle** in the left sidebar.
- **What it does:** Allows uploading custom CSV files for flight telemetry, gridded weather, or pre-aggregated congestion.
- **Key Actions:**
  1. Select Schema: *Aircraft Observations*, *Weather Observations*, or *Congestion Grid*.
  2. Auto-Map Columns: The visual mapper matches CSV headers to required fields (`latitude`, `longitude`, `timestamp_utc`, `altitude_m`, `ground_speed_mps`).
  3. Spatiotemporal Linking: Links weather cells to trajectories within $2.0^\circ$ spatial grid cells and 15-minute time windows.
  4. Active Dataset Selection: Choose which dataset parameterizes subsequent route calculations without mutating global state.

---

### Step 2: Inspect Indian Airspace (Airspace Explorer)
- **Navigation:** Click **Airspace Explorer** in the left sidebar.
- **What it does:** Interactive geospatial surveillance across Indian airspace ($6^\circ\text{N}-38^\circ\text{N}, 68^\circ\text{E}-98^\circ\text{E}$) with zero external API token dependencies.
- **Key Actions:**
  1. **2D vs 3D Switcher:** Toggle the perspective switch in the upper right.
  2. **3D Deck.gl Perspective:**
     - **Congestion Columns:** Hexagonal/grid columns extruded vertically ($0\text{m} - 25{,}000\text{m}$).
     - **Color Encoding:** Green (`LOW` density), Amber (`MEDIUM` density), Red (`HIGH` density).
     - **Camera Controls:** Right-click + drag to tilt and orbit pitch and bearing; scroll to zoom in/out.
  3. **Airspace Corridors:** Click any airport marker or airway line to view its connected waypoints and node properties.

---

### Step 3: Inject Disruptions & Storms (Scenario Studio)
- **Navigation:** Click **Scenario Studio** in the left sidebar.
- **What it does:** Simulates adverse weather and operational disruptions to evaluate route adaptability.
- **Key Actions:**
  1. **Select a Scenario:**
     - *Nominal Baseline:* Standard operational conditions.
     - *Monsoon Thunderstorm Front:* Convective storm cells across central India.
     - *Delhi Hub Restriction:* Capacity cuts and sector-level congestion spikes.
  2. **Observe Rerouting Delays:** The dynamic rerouter calculates diverging waypoints in $<15\text{ ms}$, enforcing hard corridor closures.

---

### Step 4: Solve & Compare Multi-Objective Routes (Route Optimization)
- **Navigation:** Click **Route Optimization** in the left sidebar.
- **What it does:** The primary research interface. Solves optimal airway paths using multi-objective $A^*$ search and computes Pareto-optimal frontiers.
- **Key Actions:**
  1. **Pick Origin & Destination:** Select `VIDP (Indira Gandhi Intl, Delhi)` and `VABB (Chhatrapati Shivaji Intl, Mumbai)`.
  2. **Select Objective Preset:**
     - `Shortest Distance`: Classical geodesic length along airway network.
     - `Fastest ETA`: Minimizes ML-predicted airway segment flight duration.
     - `Weather Avoidance`: Heavy quadratic penalty for storm rain cells.
     - `Congestion Avoidance`: Bypasses sectors predicted as high traffic density.
     - `Balanced`: Multi-factor composite cost trade-off.
  3. **Run Optimization:** Click **Run Optimization**.
  4. **Inspect Pareto Alternatives:** Click candidate routes to compare distance trade-offs vs time saved and weather avoided.
  5. **Bidirectional Segment Inspector:** Click any segment along the trajectory in 2D or 3D to inspect along-track altitude, wind components (headwind/crosswind), and cost decomposition.
  6. **AI Explanation:** Read natural language justification explaining why the route was chosen over alternatives.

---

### Step 5: Verify Machine Learning Intelligence (Congestion AI & Evaluation)
- **Navigation:** Click **Congestion AI** or **Model Evaluation** in the left sidebar.
- **What it does:** Inspects model weights, feature importances, and chronological out-of-sample test results.
- **Key Indicators:**
  - **Congestion Classifier (Random Forest 3-Class):**
    - Out-of-sample Test Accuracy: **84.70%** (Balanced Accuracy: **71.39%**, Macro F1: **0.6359**).
    - Critical Safety Guarantee: When actual traffic is `HIGH`, misclassification as `LOW` is only **1.49%**.
  - **Segment ETA Regressor (Random Forest):**
    - Test Set MAE: **0.9608 min** ($\approx 57.6\text{ seconds}$).
    - Explained Variance ($R^2$): **0.9368** (vs 0.487 for distance heuristics).
  - **Feature Importance:** Causal traffic density lags ($t-15\text{m}, t-30\text{m}$) and along-track winds are the primary predictive drivers.

---

### Step 6: Flight Delay Intelligence & Passenger Experience (Sky Force 2.0)
- **Role Switcher:** Use the role switch in the top header or banner to toggle between:
  1. **Passenger Portal:** Plain-language flight status, calibrated delay intervals, 8-stage operational progress, transparent evidence tags (Confirmed, Model-inferred, Unavailable), and alternative flights.
  2. **Operations Console (`delay-intelligence`):** Fleet-level delay distribution, deep-dive flight inspector, what-if scenario simulator, Route Lab connection, and Data Readiness Report.
- **Key Actions in Flight Delay Intelligence:**
  1. **Select a Flight:** Choose from active flight tracks or filter by status (`All`, `Delayed > 15m`, `High Uncertainty`).
  2. **Inspect Contributing Factors Waterfall:** Trace how inbound delay, ground turnaround deficit, airport departure queue, departure weather, and en-route convective weather contribute to the expected delay.
  3. **8-Stage Operational Progress:** Trace the flight through chronological milestones: Inbound Aircraft Turnaround -> Flight Dispatch -> Passenger Boarding -> Gate Pushback -> Taxi-Out -> Runway Takeoff -> En-Route Flight -> Arrival.
  4. **Run What-If Operational Simulation:** Adjust inbound delay (+/- min), airport queue size, weather severity, or ATC departure slot holds to see real-time impact on departure delay, taxi duration, and takeoff time.
  5. **Bridge to Route Lab:** Click **"Open Route Lab for this Flight"** to load the flight's origin and destination directly into the Multi-Objective Route Optimization solver.
  6. **Inspect Data Readiness:** Click **"Data Readiness & Production Gap Report"** to review the honest audit of which inputs are operational telemetry vs simulated proxies.

---

## 3. Academic Defense & Viva Quick Reference

Accessible via **Operator Guide & Docs** (`docs`) in the sidebar:
- **RQ1 (Spatial Aggregation):** 2.0° half-open grid intervals cleanly capture corridor chokepoints.
- **RQ2 (Chronological Partitions):** Day 1–4 train, 5–6 val, 7–8 test prevents future-to-past data leakage.
- **RQ3 (Multi-Objective Routing):** Storm avoidance routes aircraft around cells with only +3.8% to +7.2% distance overhead.
- **RQ4 (Admissible A* Heuristic):** Scaled Haversine spherical distance guarantees $h(n) \le c^*(n)$ without overestimating true costs.
- **RQ5 (Hard Closures):** Closed corridors are strictly removed from graph candidate edges, preventing unsafe penetrations.
- **RQ6 (Event Target Separation):** Gate off-block pushback delay ($STD \to \text{Off-Block}$) is strictly distinguished from runway take-off time ($STD + \text{Taxi-Out} + \text{QueueHold}$). Route optimization optimizes en-route airborne flight time ($t_\text{air}$) but does not retroactively resolve ground turnaround deficits.

---

## 4. Key Endpoints Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/health` | Service health and database connection status |
| `GET` | `/api/v1/airspace/network` | Full graph of airports, waypoints, and airway edges |
| `POST` | `/api/v1/routing/plan` | Solves single route under specified weights |
| `POST` | `/api/v1/routing/compare` | Compares objectives and returns Pareto frontier |
| `GET` | `/api/v1/models/status` | Verified SHA-256 hashes and loaded pipeline status |
| `POST` | `/api/v1/datasets/upload` | Ingests custom CSV telemetry with schema mapping |
| `GET` | `/api/delay/flights` | Search flight tracks with query, airline, date, origin/destination |
| `GET` | `/api/delay/flights/{id}` | Detailed flight delay prediction, intervals, and factor decomposition |
| `GET` | `/api/delay/flights/{id}/timeline` | 8-stage operational chronological departure progress |
| `GET` | `/api/delay/flights/{id}/alternatives` | Same-day alternative flight options between origin and destination |
| `POST` | `/api/delay/predict` | What-if scenario simulation across operational stress factors |
| `GET` | `/api/delay/dashboard` | Fleet-wide delay summary, attention queues, and airport status |
| `GET` | `/api/delay/readiness` | Comprehensive production data gap & telemetry readiness audit |

