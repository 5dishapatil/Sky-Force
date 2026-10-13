import React, { useEffect, useState } from 'react';
import { 
  Zap, 
  RotateCcw, 
  ArrowRight, 
  CheckCircle, 
  AlertTriangle, 
  ShieldAlert, 
  Clock, 
  Flame, 
  CloudRain, 
  Radio, 
  Split 
} from 'lucide-react';
import type { Scenario, DynamicRerouteResponse, Airport, AirspaceNetwork } from '../types';
import { api } from '../services/api';
import { AirspaceMap } from '../components/AirspaceMap';

interface ScenarioStudioViewProps {
  scenarios: Scenario[];
  onScenarioChange: () => void;
  airports: Airport[];
  network: AirspaceNetwork | null;
}

export const ScenarioStudioView: React.FC<ScenarioStudioViewProps> = ({
  scenarios,
  onScenarioChange,
  airports,
  network,
}) => {
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>('');
  const [origin, setOrigin] = useState<string>('VIDP');
  const [destination, setDestination] = useState<string>('VABB');
  const [rerouteLoading, setRerouteLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [rerouteResult, setRerouteResult] = useState<DynamicRerouteResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const selectedScenario = scenarios.find((s) => s.id === selectedScenarioId) || scenarios.find((s) => s.is_active) || scenarios[0];

  useEffect(() => {
    if (!scenarios.length) {
      setSelectedScenarioId('');
      return;
    }
    if (!scenarios.some((scenario) => scenario.id === selectedScenarioId)) {
      setSelectedScenarioId((scenarios.find((scenario) => scenario.is_active) || scenarios[0]).id);
    }
  }, [scenarios, selectedScenarioId]);

  const handleActivate = async (id: string) => {
    setActionLoading(id);
    setError(null);
    try {
      await api.activateScenario(id);
      onScenarioChange();
    } catch (err: any) {
      setError(err.message || 'Failed to activate scenario');
    } finally {
      setActionLoading(null);
    }
  };

  const handleReset = async (id: string) => {
    setActionLoading(id);
    setError(null);
    try {
      await api.resetScenario(id);
      onScenarioChange();
    } catch (err: any) {
      setError(err.message || 'Failed to reset scenario');
    } finally {
      setActionLoading(null);
    }
  };

  const handleDynamicReroute = async () => {
    setRerouteLoading(true);
    setError(null);
    try {
      const res = await api.dynamicReroute({
        scenario_id: selectedScenario?.id || selectedScenarioId,
        origin,
        destination,
        objective: 'balanced',
        algorithm: 'dijkstra',
      });
      setRerouteResult(res);
    } catch (err: any) {
      setError(err.message || 'Failed to compute dynamic reroute');
    } finally {
      setRerouteLoading(false);
    }
  };

  const getEventIcon = (type: string) => {
    switch (type) {
      case 'edge_closure':
      case 'restricted_polygon':
        return ShieldAlert;
      case 'traffic_surge':
        return Flame;
      case 'weather_penalty_zone':
        return CloudRain;
      case 'stale_data':
        return Radio;
      default:
        return AlertTriangle;
    }
  };

  return (
    <div className="space-y-6">
      {/* Scenario Header */}
      <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-5 shadow-lg">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2 font-mono">
              <Zap className="w-5 h-5 text-amber-400" />
              SCENARIO STUDIO & DYNAMIC REROUTING
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Simulate non-mutating airspace disruptions and evaluate autonomous rerouting behavior
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleDynamicReroute}
              disabled={rerouteLoading || !selectedScenario}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-aerospace-950 font-bold text-xs font-mono transition shadow-md shadow-amber-500/20 disabled:opacity-50"
            >
              <Split className="w-4 h-4" />
              {rerouteLoading ? 'COMPUTING REROUTE...' : 'EVALUATE DYNAMIC REROUTE'}
            </button>
          </div>
        </div>

        {error && (
          <div className="mt-4 p-3 rounded-lg bg-red-950/60 border border-red-800/80 text-red-200 text-xs flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Scenario selector: compact choice grid above the baseline/alternative comparison. */}
      {scenarios.length === 0 ? (
        <div className="empty-state"><Zap size={22} /><h3>No scenarios returned by the API</h3><p>Check that the backend is running and that GET /api/scenarios returns the prebuilt scenarios.</p></div>
      ) : null}
      <div className="scenario-workspace">
        <div className="grid grid-cols-1 gap-3.5 scenario-grid">
        {scenarios.map((sc) => {
          const isSelected = selectedScenarioId === sc.id;
          return (
            <div
              role="button"
              tabIndex={0}
              key={sc.id}
              onClick={() => setSelectedScenarioId(sc.id)}
              onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); setSelectedScenarioId(sc.id); } }}
              aria-pressed={isSelected}
              className={`scenario-choice p-4 rounded-xl border cursor-pointer transition relative overflow-hidden text-left ${
                isSelected
                  ? 'bg-aerospace-850 border-amber-500/60 shadow-lg shadow-amber-500/5'
                  : 'bg-aerospace-900 border-aerospace-800 hover:border-aerospace-700'
              }`}
            >
              <div className="flex items-start justify-between gap-2 mb-2">
                <div className="font-mono text-xs font-bold text-white leading-tight">
                  {sc.name}
                </div>
                {sc.is_active ? (
                  <span className="shrink-0 px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-800 text-[10px] font-mono font-bold animate-pulse">
                    ACTIVE
                  </span>
                ) : (
                  <span className="shrink-0 px-2 py-0.5 rounded bg-aerospace-950 text-slate-500 border border-aerospace-800 text-[10px] font-mono">
                    IDLE
                  </span>
                )}
              </div>

              <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed mb-3">
                {sc.description}
              </p>

              <div className="flex items-center justify-between text-[11px] font-mono pt-3 border-t border-aerospace-800/60">
                <span className="text-slate-400">{sc.events?.length ?? 0} simulated event(s)</span>
                <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
                  {sc.is_active ? (
                    <button
                      onClick={() => handleReset(sc.id)}
                      disabled={actionLoading === sc.id}
                      className="px-2.5 py-1 rounded bg-aerospace-800 hover:bg-aerospace-700 text-slate-300 border border-aerospace-600 transition"
                    >
                      Reset
                    </button>
                  ) : (
                    <button
                      onClick={() => handleActivate(sc.id)}
                      disabled={actionLoading === sc.id}
                      className="px-2.5 py-1 rounded bg-amber-950 hover:bg-amber-900 text-amber-300 border border-amber-700 transition"
                    >
                      Activate
                    </button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
        </div>
        {!rerouteResult && (
          <aside className="surface-card scenario-map-preview">
            <div className="surface-card-heading">
              <div>
                <p className="eyebrow">SCENARIO CONTEXT</p>
                <h3>Airway network preview</h3>
                <p className="surface-subtitle">Select a scenario, activate it, then evaluate the reroute to compare baseline and adapted paths.</p>
              </div>
              <span className="status-tag tag-amber">SIMULATION</span>
            </div>
            <AirspaceMap
              airports={airports}
              waypoints={network?.waypoints || []}
              edges={network?.edges || []}
              height="500px"
            />
            <div className="scenario-preview-caption">
              <span><i className="legend-line legend-airway" /> Network edges</span>
              <span><i className="legend-dot legend-airport" /> Airport nodes</span>
            </div>
            <div className="scenario-selected-summary">
              <span className="scenario-summary-icon"><Zap size={16} /></span>
              <div><strong>{selectedScenario?.name || 'Choose a scenario'}</strong><p>{selectedScenario?.description || 'No scenario has been returned by the backend yet.'}</p></div>
            </div>
          </aside>
        )}
      </div>

      {/* Map Comparison & Delta Panel if Dynamic Reroute was Run */}
      {rerouteResult && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* Map showing baseline vs reroute */}
            <div className="lg:col-span-2">
              <AirspaceMap
                airports={airports}
                waypoints={network?.waypoints || []}
                edges={network?.edges || []}
                primaryRoute={rerouteResult.rerouted_route}
                secondaryRoute={rerouteResult.baseline_route}
                height="460px"
              />
              <div className="mt-2 flex items-center justify-between text-xs font-mono text-slate-400 px-1">
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-1.5">
                    <span className="w-3.5 h-1 bg-cyan-400 rounded" />
                    <span className="text-cyan-300 font-semibold">Rerouted Route (Scenario-Adapted)</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="w-3.5 h-1 bg-amber-500 rounded border-dashed" />
                    <span className="text-amber-300 font-semibold">Original Baseline Path</span>
                  </div>
                </div>
                <span>Hard closures excluded from search</span>
              </div>
            </div>

            {/* Delta Metrics & Explanation */}
            <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-5 space-y-4 shadow-xl">
              <div>
                <h3 className="text-sm font-bold text-white font-mono flex items-center gap-2">
                  <Split className="w-4 h-4 text-amber-400" />
                  REROUTE DELTA ANALYSIS
                </h3>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Comparison between baseline and disruption-adapted routes
                </p>
              </div>

              {/* Delta Cards */}
              <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                <div className="p-2.5 rounded-lg bg-aerospace-950 border border-aerospace-800">
                  <div className="text-slate-400 text-[10px]">DISTANCE DELTA</div>
                  <div className={`text-base font-bold mt-0.5 ${rerouteResult.delta.distance_km_delta > 0 ? 'text-amber-400' : 'text-slate-200'}`}>
                    {rerouteResult.delta.distance_km_delta > 0 ? '+' : ''}
                    {rerouteResult.delta.distance_km_delta} km
                  </div>
                </div>

                <div className="p-2.5 rounded-lg bg-aerospace-950 border border-aerospace-800">
                  <div className="text-slate-400 text-[10px]">TIME DELTA</div>
                  <div className={`text-base font-bold mt-0.5 ${rerouteResult.delta.estimated_time_min_delta > 0 ? 'text-amber-400' : 'text-slate-200'}`}>
                    {rerouteResult.delta.estimated_time_min_delta > 0 ? '+' : ''}
                    {rerouteResult.delta.estimated_time_min_delta} min
                  </div>
                </div>

                <div className="p-2.5 rounded-lg bg-aerospace-950 border border-aerospace-800">
                  <div className="text-slate-400 text-[10px]">PATH CHANGED</div>
                  <div className="text-base font-bold text-cyan-300 mt-0.5">
                    {rerouteResult.delta.path_changed ? 'YES (Diverged)' : 'NO (Identical)'}
                  </div>
                </div>

                <div className="p-2.5 rounded-lg bg-aerospace-950 border border-aerospace-800">
                  <div className="text-slate-400 text-[10px]">COMPOSITE SCORE DELTA</div>
                  <div className="text-base font-bold text-slate-200 mt-0.5">
                    {rerouteResult.delta.composite_score_delta.toFixed(4)}
                  </div>
                </div>
              </div>

              {/* Natural Language Explanation */}
              <div className="pt-2 border-t border-aerospace-800 space-y-2">
                <div className="text-[11px] font-mono text-slate-400 font-semibold uppercase">
                  Reasoning for Path Divergence:
                </div>
                <div className="space-y-1.5">
                  {rerouteResult.explanation.map((exp, idx) => (
                    <div key={idx} className="p-2 rounded bg-aerospace-950 border border-aerospace-800 text-xs text-slate-300 leading-relaxed">
                      {exp}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
