import React, { useState } from 'react';
import { 
  Compass, 
  Play, 
  BarChart2, 
  CheckCircle2, 
  AlertCircle, 
  Info, 
  Clock, 
  Navigation,
  CloudLightning,
  Activity,
  Layers
} from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import type { Airport, RouteDetail, CompareRoutesResponse, AirspaceNetwork } from '../types';
import { api } from '../services/api';
import { AirspaceMap } from '../components/AirspaceMap';

interface RouteLabViewProps {
  network: AirspaceNetwork | null;
  airports: Airport[];
}

export const RouteLabView: React.FC<RouteLabViewProps> = ({ network, airports }) => {
  const [origin, setOrigin] = useState<string>('VIDP');
  const [destination, setDestination] = useState<string>('VABB');
  const [algorithm, setAlgorithm] = useState<'dijkstra' | 'astar'>('dijkstra');
  const [objective, setObjective] = useState<string>('balanced');
  
  // Custom Weights
  const [weights, setWeights] = useState({
    distance: 0.25,
    time: 0.25,
    weather: 0.2,
    congestion: 0.2,
    uncertainty: 0.1,
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [routeResult, setRouteResult] = useState<RouteDetail | null>(null);
  const [compareResult, setCompareResult] = useState<CompareRoutesResponse | null>(null);

  const presets: Record<string, { label: string; desc: string; w: typeof weights }> = {
    distance: {
      label: 'Shortest Distance',
      desc: 'Pure minimum geodesic length',
      w: { distance: 1.0, time: 0, weather: 0, congestion: 0, uncertainty: 0 },
    },
    fastest: {
      label: 'Fastest Travel Time',
      desc: 'Minimizes segment travel minutes',
      w: { distance: 0, time: 1.0, weather: 0, congestion: 0, uncertainty: 0 },
    },
    weather: {
      label: 'Weather Avoidance',
      desc: 'Penalizes storm cells & convective weather',
      w: { distance: 0.5, time: 0, weather: 0.5, congestion: 0, uncertainty: 0 },
    },
    congestion: {
      label: 'Congestion Avoidance',
      desc: 'Penalizes high traffic density cells',
      w: { distance: 0.5, time: 0, weather: 0, congestion: 0.5, uncertainty: 0 },
    },
    balanced: {
      label: 'Composite Balanced',
      desc: 'Multi-factor trade-off',
      w: { distance: 0.25, time: 0.25, weather: 0.2, congestion: 0.2, uncertainty: 0.1 },
    },
  };

  const handleSelectPreset = (key: string) => {
    setObjective(key);
    if (presets[key]) {
      setWeights(presets[key].w);
    }
  };

  const handlePlanRoute = async () => {
    if (origin === destination) {
      setError('Origin and destination must differ.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await api.optimizeRoute({
        origin,
        destination,
        algorithm,
        objective,
        weights: objective === 'custom' ? weights : undefined,
      });
      setRouteResult(res);
      setCompareResult(null);
    } catch (err: any) {
      setError(err.message || 'Failed to optimize route');
    } finally {
      setLoading(false);
    }
  };

  const handleCompareAlternatives = async () => {
    if (origin === destination) {
      setError('Origin and destination must differ.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await api.compareRoutes({
        origin,
        destination,
        algorithm,
        objective,
      });
      setCompareResult(res);
      if (res.routes && res.routes.length > 0) {
        setRouteResult(res.routes[0]);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to compare route alternatives');
    } finally {
      setLoading(false);
    }
  };

  // Prepare chart data for cost breakdown
  const costChartData = routeResult?.cost_by_factor
    ? Object.entries(routeResult.cost_by_factor).map(([key, val]) => ({
        factor: key.toUpperCase(),
        cost: val,
      }))
    : [];

  const FACTOR_COLORS: Record<string, string> = {
    DISTANCE: '#3b82f6',
    TIME: '#06b6d4',
    WEATHER: '#f59e0b',
    CONGESTION: '#ef4444',
    UNCERTAINTY: '#8b5cf6',
  };

  return (
    <div className="space-y-6">
      {/* Top Controls Grid */}
      <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-5 shadow-lg">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-4 pb-4 border-b border-aerospace-800">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2 font-mono">
              <Compass className="w-5 h-5 text-cyan-400" />
              ROUTE OPTIMIZATION LAB
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Compare candidate routes under multi-factor edge costs using Dijkstra and A* search
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handlePlanRoute}
              disabled={loading}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-aerospace-950 font-bold text-xs font-mono transition shadow-md shadow-cyan-500/20 disabled:opacity-50"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              {loading ? 'OPTIMIZING...' : 'PLAN ROUTE'}
            </button>
            <button
              onClick={handleCompareAlternatives}
              disabled={loading}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-aerospace-800 hover:bg-aerospace-700 text-slate-200 border border-aerospace-600 font-medium text-xs font-mono transition disabled:opacity-50"
            >
              <BarChart2 className="w-3.5 h-3.5 text-cyan-400" />
              COMPARE ALTERNATIVES
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-950/60 border border-red-800/80 text-red-200 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Origin Airport */}
          <div>
            <label className="block text-xs font-mono text-slate-400 mb-1">ORIGIN (ICAO)</label>
            <select
              value={origin}
              onChange={(e) => setOrigin(e.target.value)}
              className="w-full bg-aerospace-950 border border-aerospace-700 rounded-lg px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-cyan-500"
            >
              {airports.map((a) => (
                <option key={a.node_id} value={a.node_id}>
                  {a.node_id} - {a.name} ({a.iata || 'WP'})
                </option>
              ))}
            </select>
          </div>

          {/* Destination Airport */}
          <div>
            <label className="block text-xs font-mono text-slate-400 mb-1">DESTINATION (ICAO)</label>
            <select
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
              className="w-full bg-aerospace-950 border border-aerospace-700 rounded-lg px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-cyan-500"
            >
              {airports.map((a) => (
                <option key={a.node_id} value={a.node_id}>
                  {a.node_id} - {a.name} ({a.iata || 'WP'})
                </option>
              ))}
            </select>
          </div>

          {/* Algorithm Toggle */}
          <div>
            <label className="block text-xs font-mono text-slate-400 mb-1">ALGORITHM</label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setAlgorithm('dijkstra')}
                className={`px-3 py-2 rounded-lg text-xs font-mono font-medium border transition ${
                  algorithm === 'dijkstra'
                    ? 'bg-cyan-500/15 border-cyan-500 text-cyan-300'
                    : 'bg-aerospace-950 border-aerospace-800 text-slate-400 hover:border-aerospace-700'
                }`}
              >
                Dijkstra
              </button>
              <button
                type="button"
                onClick={() => setAlgorithm('astar')}
                className={`px-3 py-2 rounded-lg text-xs font-mono font-medium border transition ${
                  algorithm === 'astar'
                    ? 'bg-cyan-500/15 border-cyan-500 text-cyan-300'
                    : 'bg-aerospace-950 border-aerospace-800 text-slate-400 hover:border-aerospace-700'
                }`}
              >
                A* (Admissible)
              </button>
            </div>
          </div>

          {/* Objective Preset */}
          <div>
            <label className="block text-xs font-mono text-slate-400 mb-1">OBJECTIVE PRESET</label>
            <select
              value={objective}
              onChange={(e) => handleSelectPreset(e.target.value)}
              className="w-full bg-aerospace-950 border border-aerospace-700 rounded-lg px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-cyan-500"
            >
              {Object.entries(presets).map(([k, p]) => (
                <option key={k} value={k}>
                  {p.label}
                </option>
              ))}
              <option value="custom">Custom Weights</option>
            </select>
          </div>
        </div>

        {/* Custom Sliders if active */}
        {objective === 'custom' && (
          <div className="mt-4 pt-4 border-t border-aerospace-800 grid grid-cols-2 sm:grid-cols-5 gap-3">
            {Object.keys(weights).map((factor) => (
              <div key={factor}>
                <div className="flex justify-between text-[11px] font-mono text-slate-400 mb-1">
                  <span className="capitalize">{factor}</span>
                  <span>{weights[factor as keyof typeof weights].toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={weights[factor as keyof typeof weights]}
                  onChange={(e) =>
                    setWeights({
                      ...weights,
                      [factor]: parseFloat(e.target.value),
                    })
                  }
                  className="w-full h-1 bg-aerospace-800 rounded-lg appearance-none cursor-pointer accent-cyan-400"
                />
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Main Map Visualization */}
      <AirspaceMap
        airports={airports}
        edges={network?.edges || []}
        primaryRoute={routeResult}
        secondaryRoute={compareResult?.routes?.find((r) => r.label.includes('distance')) || null}
        height="500px"
      />

      {/* Route Outcomes KPI Banner */}
      {routeResult?.found && routeResult.totals && (
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
          <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-3">
            <div className="text-[11px] font-mono text-slate-400">DISTANCE</div>
            <div className="text-lg font-bold font-mono text-white mt-0.5">
              {routeResult.totals.distance_km} <span className="text-xs text-slate-400">km</span>
            </div>
          </div>

          <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-3">
            <div className="text-[11px] font-mono text-slate-400">ESTIMATED TIME</div>
            <div className="text-lg font-bold font-mono text-cyan-300 mt-0.5">
              {routeResult.totals.estimated_time_min} <span className="text-xs text-slate-400">min</span>
            </div>
          </div>

          <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-3">
            <div className="text-[11px] font-mono text-slate-400">WEATHER EXP</div>
            <div className="text-lg font-bold font-mono text-amber-400 mt-0.5">
              {routeResult.totals.weather_exposure_km} <span className="text-xs text-slate-400">km</span>
            </div>
          </div>

          <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-3">
            <div className="text-[11px] font-mono text-slate-400">CONGESTION EXP</div>
            <div className="text-lg font-bold font-mono text-rose-400 mt-0.5">
              {routeResult.totals.congestion_exposure_km} <span className="text-xs text-slate-400">km</span>
            </div>
          </div>

          <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-3">
            <div className="text-[11px] font-mono text-slate-400">HOPS</div>
            <div className="text-lg font-bold font-mono text-slate-200 mt-0.5">
              {routeResult.totals.hops}
            </div>
          </div>

          <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-3">
            <div className="text-[11px] font-mono text-slate-400">EXPANDED NODES</div>
            <div className="text-lg font-bold font-mono text-purple-300 mt-0.5">
              {routeResult.search?.nodes_expanded || 0}
            </div>
          </div>

          <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-3">
            <div className="text-[11px] font-mono text-slate-400">SEARCH LATENCY</div>
            <div className="text-lg font-bold font-mono text-emerald-400 mt-0.5">
              {routeResult.search?.latency_ms?.toFixed(1) || 0} <span className="text-xs text-slate-400">ms</span>
            </div>
          </div>
        </div>
      )}

      {/* Route Details & Explainability Cards */}
      {routeResult?.found && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {/* Natural Language Explanation Card */}
          <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-5 shadow-lg space-y-3">
            <div className="flex items-center gap-2 text-cyan-400 font-mono text-xs font-semibold">
              <Info className="w-4 h-4" />
              <span>EXPLAINABILITY & FACTOR ATTRIBUTION</span>
            </div>
            <h3 className="text-sm font-bold text-white">Why was this route chosen?</h3>
            
            <div className="space-y-2">
              {routeResult.explanation?.map((item, idx) => (
                <div key={idx} className="p-2.5 rounded-lg bg-aerospace-950 border border-aerospace-800 text-xs text-slate-300 leading-relaxed flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
                  <span>{item}</span>
                </div>
              ))}
            </div>

            {/* Waypoint Itinerary */}
            <div className="pt-2 border-t border-aerospace-800">
              <div className="text-[11px] font-mono text-slate-400 mb-1.5 uppercase">Waypoint Sequence:</div>
              <div className="flex flex-wrap gap-1.5 font-mono text-xs">
                {routeResult.path?.map((node, i) => (
                  <span
                    key={i}
                    className={`px-2 py-0.5 rounded border ${
                      i === 0 || i === (routeResult.path?.length || 1) - 1
                        ? 'bg-cyan-950 text-cyan-300 border-cyan-800 font-bold'
                        : 'bg-aerospace-800 text-slate-300 border-aerospace-700'
                    }`}
                  >
                    {node}
                    {i < (routeResult.path?.length || 0) - 1 && ' →'}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Cost Breakdown Bar Chart */}
          <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-5 shadow-lg space-y-3">
            <div className="flex items-center justify-between text-xs font-mono text-slate-400">
              <span className="flex items-center gap-2 text-cyan-400 font-semibold">
                <BarChart2 className="w-4 h-4" />
                DIMENSIONLESS COST BREAKDOWN
              </span>
              <span>Total Score: {routeResult.totals?.composite_score.toFixed(4)}</span>
            </div>

            <div className="h-48 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={costChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <XAxis dataKey="factor" tick={{ fill: '#94a3b8', fontSize: 11, fontFamily: 'monospace' }} />
                  <YAxis tick={{ fill: '#94a3b8', fontSize: 11, fontFamily: 'monospace' }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0f1c3d',
                      borderColor: '#1d3269',
                      borderRadius: '8px',
                      color: '#e2e8f0',
                      fontSize: '12px',
                      fontFamily: 'monospace',
                    }}
                  />
                  <Bar dataKey="cost" radius={[4, 4, 0, 0]}>
                    {costChartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={FACTOR_COLORS[entry.factor] || '#3b82f6'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <p className="text-[11px] text-slate-400 font-mono">
              Components are dimensionless normalised lengths: length / ref_km scaled by active weights.
            </p>
          </div>
        </div>
      )}

      {/* Alternative Candidates Table if Compare was clicked */}
      {compareResult && compareResult.routes && (
        <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-5 shadow-lg space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white font-mono flex items-center gap-2">
              <Layers className="w-4 h-4 text-cyan-400" />
              MULTI-OBJECTIVE CANDIDATE COMPARISON
            </h3>
            <span className="text-xs font-mono text-slate-400">
              {compareResult.routes.length} Pareto alternatives generated
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-aerospace-950 text-slate-400 border-b border-aerospace-800">
                <tr>
                  <th className="py-2.5 px-3">Objective</th>
                  <th className="py-2.5 px-3">Distance</th>
                  <th className="py-2.5 px-3">ETA</th>
                  <th className="py-2.5 px-3">Weather Exp</th>
                  <th className="py-2.5 px-3">Congestion Exp</th>
                  <th className="py-2.5 px-3">Score</th>
                  <th className="py-2.5 px-3">Hops</th>
                  <th className="py-2.5 px-3">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-aerospace-800 text-slate-300">
                {compareResult.routes.map((r, i) => (
                  <tr key={i} className="hover:bg-aerospace-850/50 transition">
                    <td className="py-2.5 px-3 font-semibold text-cyan-300 capitalize">{r.label}</td>
                    <td className="py-2.5 px-3">{r.totals?.distance_km} km</td>
                    <td className="py-2.5 px-3">{r.totals?.estimated_time_min} min</td>
                    <td className="py-2.5 px-3 text-amber-400">{r.totals?.weather_exposure_km} km</td>
                    <td className="py-2.5 px-3 text-rose-400">{r.totals?.congestion_exposure_km} km</td>
                    <td className="py-2.5 px-3 font-bold text-white">{r.totals?.composite_score.toFixed(4)}</td>
                    <td className="py-2.5 px-3">{r.totals?.hops}</td>
                    <td className="py-2.5 px-3">
                      <button
                        onClick={() => setRouteResult(r)}
                        className="px-2 py-1 rounded bg-cyan-950 text-cyan-400 border border-cyan-800 hover:bg-cyan-900 text-[11px]"
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
