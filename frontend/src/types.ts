export interface Airport {
  node_id: string;
  icao?: string;
  iata?: string;
  name: string;
  latitude: number;
  longitude: number;
  country?: string;
  elevation_m?: number;
  source?: string;
  provenance?: string;
}

export interface Waypoint {
  node_id: string;
  name: string;
  latitude: number;
  longitude: number;
  kind?: string;
  source?: string;
}

export interface RouteEdge {
  edge_id: string;
  source_node: string;
  target_node: string;
  distance_km: number;
  bearing_deg: number;
  is_synthetic?: boolean;
}

export interface AirspaceNetwork {
  airports: Airport[];
  waypoints: Waypoint[];
  edges: RouteEdge[];
  total_airports: number;
  total_waypoints: number;
  total_edges: number;
}

export interface CostWeights {
  distance: number;
  time: number;
  weather: number;
  congestion: number;
  uncertainty: number;
}

export interface RouteTotals {
  distance_km: number;
  estimated_time_min: number;
  weather_exposure_km: number;
  congestion_exposure_km: number;
  mean_uncertainty: number;
  composite_score: number;
  hops: number;
  closed_edges_in_route: number;
}

export interface RouteSegment {
  edge_id: string;
  from_node: string;
  to_node: string;
  distance_km: number;
  time_min: number;
  time_source: string;
  weather_severity: number | null;
  weather_source: string;
  congestion_score: number | null;
  congestion_class: string | null;
  congestion_probs: Record<string, number> | null;
  congestion_source: string;
  uncertainty: number;
  closed: boolean;
  closure_reasons: string[];
  event_ids: string[];
  flags: string[];
  cost_components: Record<string, number>;
  weighted_cost: Record<string, number>;
  cost_total: number;
}

export interface RouteDetail {
  found: boolean;
  label: string;
  algorithm: string;
  route_id?: string;
  path?: string[];
  geometry?: [number, number][];
  totals?: RouteTotals;
  cost_by_factor?: Record<string, number>;
  segments?: RouteSegment[];
  provenance?: Record<string, string[]>;
  search?: {
    nodes_expanded: number;
    latency_ms: number;
    search_cost?: number;
  };
  explanation?: string[];
  reason?: string;
}

export interface CompareRoutesResponse {
  origin: string;
  destination: string;
  scenario_id?: string;
  selected_objective: string;
  algorithm: string;
  routes: RouteDetail[];
  closed_edges_avoided: { edge_id: string; reasons: string[] }[];
  explanation: string[];
}

export interface ScenarioEvent {
  id: string;
  name: string;
  description: string;
  event_type: string;
  start_time_utc: string;
  end_time_utc: string;
  enabled: boolean;
  scope: Record<string, any>;
  severity: number;
  source_status: string;
}

export interface Scenario {
  id: string;
  name: string;
  description: string;
  is_prebuilt: boolean;
  is_active: boolean;
  seed: number;
  scenario_time_utc: string;
  created_at: string;
  updated_at: string;
  events: ScenarioEvent[];
}

export interface DynamicRerouteDelta {
  path_changed: boolean;
  distance_km_delta: number;
  estimated_time_min_delta: number;
  weather_penalty_delta: number;
  congestion_penalty_delta: number;
  composite_score_delta: number;
}

export interface DynamicRerouteResponse {
  scenario_id: string;
  scenario_name: string;
  origin: string;
  destination: string;
  baseline_route: RouteDetail;
  rerouted_route: RouteDetail;
  delta: DynamicRerouteDelta;
  explanation: string[];
  affected_events: any[];
}

export interface ConflictEvent {
  event_id: string;
  aircraft_1: string;
  callsign_1?: string;
  aircraft_2: string;
  callsign_2?: string;
  observation_time_utc: string;
  current_horizontal_dist_km: number;
  current_vertical_diff_m?: number | null;
  cpa_time_seconds: number;
  cpa_horizontal_dist_km: number;
  cpa_vertical_diff_m?: number | null;
  severity: 'LOW' | 'MEDIUM' | 'HIGH';
  is_projected: boolean;
  data_uncertainty_flags: string[];
  disclaimer: string;
}

export interface ConflictScanResponse {
  timestamp_utc: string;
  aircraft_scanned: number;
  pairs_evaluated: number;
  proximity_events_found: number;
  events: ConflictEvent[];
  parameters: Record<string, any>;
  disclaimer: string;
}

export interface CongestionCell {
  cell_id: string;
  aircraft_count: number;
  predicted_class: 'LOW' | 'MEDIUM' | 'HIGH';
  congestion_score: number;
  confidence?: number;
  center_lat: number;
  center_lon: number;
  bounds: [[number, number], [number, number]];
}

export interface ModelInfo {
  name: string;
  kind: string;
  version: string;
  task: string;
  metrics: Record<string, any>;
  feature_names: string[];
  feature_count: number;
  sha256: string;
  is_loaded: boolean;
}

export interface ModelsStatusResponse {
  status: string;
  congestion_model: ModelInfo | null;
  eta_model: ModelInfo | null;
  training_summary: Record<string, any>;
  disclaimer: string;
}
