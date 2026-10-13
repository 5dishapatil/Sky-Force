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
  const { headers: requestHeaders, ...requestOptions } = options || {};
  let response: Response;

  try {
    response = await fetch(`${API_BASE}${endpoint}`, {
      ...requestOptions,
      headers: {
        Accept: 'application/json',
        ...(requestOptions.body ? { 'Content-Type': 'application/json' } : {}),
        ...requestHeaders,
      },
    });
  } catch (error) {
    const reason = error instanceof Error ? error.message : 'Network request failed';
    throw new Error(`API connection failed for ${endpoint}: ${reason}. Is the FastAPI server running on port 8000?`);
  }

  const responseText = await response.text();
  let payload: unknown = null;
  if (responseText) {
    try {
      payload = JSON.parse(responseText);
    } catch {
      payload = responseText;
    }
  }

  if (!response.ok) {
    const body = payload && typeof payload === 'object' ? payload as Record<string, unknown> : null;
    const nestedError = body?.error && typeof body.error === 'object' ? body.error as Record<string, unknown> : null;
    const detail = body?.detail || nestedError?.message || body?.message || (typeof payload === 'string' ? payload : null);
    throw new Error(typeof detail === 'string' ? detail : `HTTP ${response.status}: ${response.statusText}`);
  }

  if (payload === null) return null as T;
  return payload as T;
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
  getCongestionTimeSeries: (cellId: string) => fetchJson<any>(`/congestion/timeseries?cell_id=${encodeURIComponent(cellId)}`),
  
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
    fetchJson<any>(`/routes/pareto?origin=${encodeURIComponent(origin)}&destination=${encodeURIComponent(destination)}${scenarioId ? `&scenario_id=${encodeURIComponent(scenarioId)}` : ''}`),
  
  getScenarios: () => fetchJson<Scenario[]>('/scenarios'),
  activateScenario: (scenarioId: string) => fetchJson<Scenario>(`/scenarios/${encodeURIComponent(scenarioId)}/activate`, { method: 'POST' }),
  resetScenario: (scenarioId: string) => fetchJson<Scenario>(`/scenarios/${encodeURIComponent(scenarioId)}/reset`, { method: 'POST' }),
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
    fetchJson<ConflictScanResponse>(`/conflicts/latest?horizon_seconds=${encodeURIComponent(String(horizon))}&horiz_threshold_km=${encodeURIComponent(String(hThresh))}&vert_threshold_m=${encodeURIComponent(String(vThresh))}`),
  
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
