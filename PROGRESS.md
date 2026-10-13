# Sky Force — Build Progress Tracker

Legend: ✅ done & verified · 🟡 implemented, pending test execution · ⬜ to-do · ⛔ blocked (external)

_Last updated: 2026-10-13_

---

## Phase 1 — Inspect, Initialise, Run
| Item | Status | Notes |
|---|---|---|
| Environment inspection | ✅ | Python 3.11.9, Node 24.19, npm 11.17, Git 2.54. **No Docker / PostgreSQL installed** → SQLite fallback is the verified local path. |
| Reference repo + API research | ✅ | Documented in `README.md`. BlueSky needs `numpy<2.4` → conflicts with this env; kept optional. |
| Backend venv + deps | ✅ | `sky-force/.venv` configured and verified. |
| Config, logging, error model | ✅ | `backend/app/core/{config,logging,errors}.py` with typed pydantic-settings. |
| ORM schema | ✅ | `backend/app/db/models.py` with 15 entity tables and full provenance columns. |
| Alembic migrations | ✅ | `backend/alembic/` configured, `0001_initial_schema.py` generated and applied. |
| FastAPI app + health | ⬜ | To be implemented in next step. |
| Frontend shell | ⬜ | To be implemented in next step. |

---

## Phase 2 — Demo Data & Map
| Item | Status | Notes |
|---|---|---|
| OurAirports real fetch (19 airports) | ✅ | 86,236 rows downloaded, subset cached with SHA-256 hash in `data/reference/`. |
| Synthetic world generator | ✅ | 40 waypoints, 276 edges, ~276k observations, 3,678 flights. |
| Bootstrap pipeline | ✅ | Idempotent pipeline: generation → QA cleaning (276k raw → 274.6k clean) → 3,678 track segmentation → 24.4k congestion cell-windows → 17.2k ETA traversals → DB persistence → source manifest. |
| Map visualisation | ⬜ | Interactive Leaflet layer with route & congestion rendering. |

---

## Phase 3 — Routing Engine
| Item | Status | Notes |
|---|---|---|
| Directed Route Graph | ✅ | `backend/app/services/routing/graph.py` with NetworkX representation and reference scales. |
| Edge Attributes & Context | ✅ | `backend/app/services/routing/context.py` tracking per-edge weather, traffic, and uncertainty. |
| Dimensionless Cost Model | ✅ | `backend/app/services/routing/cost_model.py` with distance, time, weather, congestion, and uncertainty components. |
| Dijkstra & Admissible A* Search | ✅ | `backend/app/services/routing/search.py` with provably admissible heuristic lower bounds and expansion tracking. |
| Route Planner & Alternatives | ✅ | `backend/app/services/routing/planner.py` calculating labeled alternatives (`distance`, `fastest`, `weather`, `congestion`, `balanced`) and Pareto candidates. |
| Data-driven Route Explanations | ✅ | `backend/app/services/routing/explain.py` generating transparent natural-language trade-off rationales. |
| Context Provider & Runtime Fallbacks | ✅ | `backend/app/services/routing/providers.py` integrating ML predictions, observed proxies, and heuristic fallbacks. |

---

## Phase 4 — Ingestion & Quality
| Item | Status | Notes |
|---|---|---|
| Data-quality layer + track segmentation | ✅ | `backend/app/services/preprocessing/quality.py`: 9-stage auditable cleaning report. |
| Congestion + ETA feature engineering | ✅ | `backend/app/services/features/{congestion,eta,splits}.py`: causal lags, training-only thresholds, entry-time features. |
| OpenSky adapter (live + file import) | ⬜ | Optional real-world live connector / file loader. |
| Open-Meteo adapter | ⬜ | Live / historical archive connector. |
| NOAA AWC METAR adapter | ⬜ | Aviation weather METAR connector. |
| Source manifest | ✅ | `data/source_manifest.json` tracking checksums, row counts, and data provenance. |

---

## Phase 5 — Machine Learning
| Item | Status | Notes |
|---|---|---|
| Checksum-Verified Model Registry | ✅ | `backend/app/services/models/registry.py` with strict SHA-256 validation and out-of-distribution detection. |
| Congestion Classifiers (Dummy/LR/RF/HGB) | ✅ | `backend/app/services/models/training.py`: chronological split, macro F1 selection, reliability calibration. |
| Segment-ETA Regressors (Median/Heuristic/Ridge/RF/HGB) | ✅ | `backend/app/services/models/training.py`: MAE/RMSE/R² evaluation against heuristic baseline. |
| Model Training Pipeline & CLI | ✅ | `backend/app/services/models/pipeline.py` & `backend/scripts/train_models.py`. |
| Artifacts + Registry + Explainability | ✅ | Versioned artifact saving, permutation importance, and metadata export. |

---

## Phase 6 — Scenario Engine & Dynamic Rerouting
| Item | Status | Notes |
|---|---|---|
| Scenario Events & Applicator | ✅ | `backend/app/services/scenario_engine/events.py`: closures, restricted polygons, traffic surges, weather zones, stale data. |
| Prebuilt Demo Scenarios | ✅ | `backend/app/services/scenario_engine/prebuilt.py`: 6 seeded Delhi–Mumbai corridor scenarios. |
| Dynamic Rerouting & Comparison | ⬜ | Endpoints to activate events, recalculate routes, and generate delta comparisons. |

---

## Phase 7 — Simplified Conflict & Trajectory Lab
| Item | Status | Notes |
|---|---|---|
| CPA / Proximity Risk Module | ⬜ | Pairwise closest-point-of-approach (CPA) trajectory analysis with prototype proximity thresholds. |
| Visual Trajectory Playback | ⬜ | Time-stepped trajectory viewer on the frontend map. |

---

## Phase 8 — REST API Endpoints
| Item | Status | Notes |
|---|---|---|
| Core / Health / Metadata | ⬜ | `/api/health`, `/api/meta`, `/api/data-sources/status`. |
| Airports & Airspace | ⬜ | `/api/airports`, `/api/aircraft/observations`, `/api/weather`. |
| Congestion & Models | ⬜ | `/api/congestion/cells`, `/api/congestion/predict`, `/api/models/status`. |
| Route Optimization & Explanations | ⬜ | `/api/routes/optimize`, `/api/routes/compare`, `/api/routes/pareto`, `/api/routes/explain`. |
| Scenario Management | ⬜ | `/api/scenarios`, `/api/scenarios/{id}/activate`, `/api/scenarios/{id}/reset`. |
| Experiments & Evaluation | ⬜ | `/api/experiments/run`, `/api/experiments/{id}/report`. |

---

## Phase 9 — Frontend & Visualisations
| Item | Status | Notes |
|---|---|---|
| React + Vite + Tailwind + Lucide Shell | ⬜ | Professional dark navy geospatial research console. |
| Interactive Leaflet Map | ⬜ | Airport nodes, candidate segments, route geometries, weather, restrictions, and traffic layers. |
| Analytical Charts (Recharts) | ⬜ | Route comparison bar charts, segment cost waterfall, congestion distributions, ML confusion matrix, and ETA residual plots. |
| Route Lab & Scenario Studio UI | ⬜ | Interactive forms for origin/destination selection, objective weight sliders, and scenario toggling. |

---

## Phase 10 — Automated Testing & Deliverables
| Item | Status | Notes |
|---|---|---|
| Routing Unit Tests | ⬜ | Dijkstra vs. A*, A* admissibility, closed-edge avoidance, disconnected graph handling. |
| Data Quality & Geodesy Tests | ⬜ | Haversine vs. PyProj, coordinate validation, duplicate detection, leakage safety. |
| ML & Registry Tests | ⬜ | Schema validation, checksum verification, model loading. |
| API Integration Tests | ⬜ | FastAPI test client verification. |
| Documentation & Final Viva Guide | ⬜ | `docs/architecture.md`, `docs/data_dictionary.md`, `docs/model_card.md`, `docs/viva_guide.md`. |
