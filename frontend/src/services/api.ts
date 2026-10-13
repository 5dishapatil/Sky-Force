import type {
  AirspaceNetwork,
  CompareRoutesResponse,
  ConflictScanResponse,
  DynamicRerouteResponse,
  ModelsStatusResponse,
  RouteDetail,
  Scenario,
} from '../types';

const API_BASE = '/api';

export async function fetchJson<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || errorBody.error?.message || `HTTP ${res.status}: ${res.statusText}`);
  }
  return res.json();
}

export const api = {
  getHealth: () => fetchJson<{ status: string; app_name: string; database: string; disclaimer: string }>('/health'),
  getMeta: () => fetchJson<any>('/meta'),
  getDataSourcesStatus: () => fetchJson<any[]>('/data-sources/status'),
  getDataQualitySummary: () => fetchJson<any>('/data-quality/summary'),
  
  getAirports: () => fetchJson<any[]>('/airports'),
  getAirspaceNetwork: () => fetchJson<AirspaceNetwork>('/airports/network'),
  
  getAircraftObservations: (limit = 100) => fetchJson<any>(`/aircraft/observations?limit=${limit}`),
  getWeather: () => fetchJson<any>('/weather'),
  
  getCongestionCells: () => fetchJson<any[]>('/congestion/cells'),
  getCongestionTimeSeries: (cellId: string) => fetchJson<any>(`/congestion/timeseries?cell_id=${cellId}`),
  
  optimizeRoute: (payload: {
    origin: string;
    destination: string;
    algorithm?: string;
    objective?: string;
    weights?: Record<string, number>;
    scenario_id?: string;
  }) => fetchJson<RouteDetail>('/routes/optimize', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  
  compareRoutes: (payload: {
    origin: string;
    destination: string;
    algorithm?: string;
    objective?: string;
    scenario_id?: string;
  }) => fetchJson<CompareRoutesResponse>('/routes/compare', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  
  getParetoRoutes: (origin: string, destination: string, scenarioId?: string) =>
    fetchJson<any>(`/routes/pareto?origin=${origin}&destination=${destination}${scenarioId ? `&scenario_id=${scenarioId}` : ''}`),
  
  getScenarios: () => fetchJson<Scenario[]>('/scenarios'),
  activateScenario: (scenarioId: string) => fetchJson<Scenario>(`/scenarios/${scenarioId}/activate`, { method: 'POST' }),
  resetScenario: (scenarioId: string) => fetchJson<Scenario>(`/scenarios/${scenarioId}/reset`, { method: 'POST' }),
  dynamicReroute: (payload: {
    origin: string;
    destination: string;
    scenario_id: string;
    objective?: string;
    algorithm?: string;
  }) => fetchJson<DynamicRerouteResponse>('/scenarios/reroute', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  
  getLatestConflicts: (horizon = 300, hThresh = 9.26, vThresh = 300) =>
    fetchJson<ConflictScanResponse>(`/conflicts/latest?horizon_seconds=${horizon}&horiz_threshold_km=${hThresh}&vert_threshold_m=${vThresh}`),
  
  getModelsStatus: () => fetchJson<ModelsStatusResponse>('/models/status'),
  getModelsMetrics: () => fetchJson<any>('/models/metrics'),
  getFeatureImportance: () => fetchJson<any>('/models/feature-importance'),
  
  getExperiments: () => fetchJson<any[]>('/experiments'),
  runExperiment: (payload: { od_pairs: string[][]; scenario_ids: string[]; algorithm?: string }) =>
    fetchJson<any>('/experiments/run', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
};
