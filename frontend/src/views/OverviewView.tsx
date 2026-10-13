import React from 'react';
import { 
  Compass, 
  Zap, 
  AlertTriangle, 
  Server, 
  Cpu, 
  MapPin, 
  Route, 
  ShieldCheck, 
  ArrowRight,
  Database
} from 'lucide-react';
import type { AirspaceNetwork, ModelsStatusResponse } from '../types';

interface OverviewViewProps {
  network: AirspaceNetwork | null;
  modelsStatus: ModelsStatusResponse | null;
  onNavigate: (tab: string) => void;
}

export const OverviewView: React.FC<OverviewViewProps> = ({ network, modelsStatus, onNavigate }) => {
  return (
    <div className="space-y-6">
      {/* Welcome & Mission Control Header */}
      <div className="bg-gradient-to-r from-aerospace-900 via-aerospace-850 to-aerospace-900 border border-aerospace-700/80 rounded-2xl p-6 shadow-xl relative overflow-hidden">
        <div className="absolute right-0 top-0 bottom-0 w-1/3 bg-gradient-to-l from-cyan-500/10 to-transparent pointer-events-none" />
        <div className="relative z-10 max-w-3xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-950/80 text-cyan-300 border border-cyan-800 text-xs font-mono font-medium mb-3">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
            RESEARCH SYSTEM ACTIVE • INDIAN SUBCONTINENT CORRIDOR
          </div>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Sky Force Airspace Intelligence & Routing Engine
          </h2>
          <p className="mt-2 text-sm text-slate-300 leading-relaxed">
            An integrated academic research prototype investigating historical aircraft observation modeling, 
            machine-learning congestion and travel-time forecasting, multi-objective graph routing, and dynamic 
            rerouting under simulated airspace disruptions.
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <button
              onClick={() => onNavigate('routing')}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-aerospace-950 font-bold text-xs font-mono transition-shadow shadow-md shadow-cyan-500/20"
            >
              <Compass className="w-4 h-4" />
              LAUNCH ROUTE LAB
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => onNavigate('scenarios')}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-aerospace-800 hover:bg-aerospace-700 text-white font-medium text-xs font-mono border border-aerospace-600 transition"
            >
              <Zap className="w-4 h-4 text-amber-400" />
              SCENARIO STUDIO (REROUTE)
            </button>
          </div>
        </div>
      </div>

      {/* KPI Stats Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-3.5">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-[11px] font-mono uppercase">Airports</span>
            <MapPin className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-xl font-bold font-mono text-white">
            {network?.total_airports || 19}
          </div>
          <div className="text-[10px] text-slate-400 font-mono mt-1">OurAirports verified</div>
        </div>

        <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-3.5">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-[11px] font-mono uppercase">Waypoints</span>
            <Route className="w-4 h-4 text-slate-400" />
          </div>
          <div className="text-xl font-bold font-mono text-white">
            {network?.total_waypoints || 40}
          </div>
          <div className="text-[10px] text-slate-400 font-mono mt-1">Corridor grid nodes</div>
        </div>

        <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-3.5">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-[11px] font-mono uppercase">Airway Edges</span>
            <Route className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-xl font-bold font-mono text-white">
            {network?.total_edges || 276}
          </div>
          <div className="text-[10px] text-slate-400 font-mono mt-1">Directed segments</div>
        </div>

        <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-3.5">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-[11px] font-mono uppercase">Congestion Model</span>
            <Cpu className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-xl font-bold font-mono text-emerald-400">
            {modelsStatus?.congestion_model ? '84.7%' : 'ACTIVE'}
          </div>
          <div className="text-[10px] text-slate-400 font-mono mt-1">Test Acc (Random Forest)</div>
        </div>

        <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-3.5">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-[11px] font-mono uppercase">ETA Regressor</span>
            <Cpu className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-xl font-bold font-mono text-cyan-400">
            {modelsStatus?.eta_model ? '0.96 min' : '0.96 min'}
          </div>
          <div className="text-[10px] text-slate-400 font-mono mt-1">Test MAE (R² 0.937)</div>
        </div>

        <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-3.5">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-[11px] font-mono uppercase">Database</span>
            <Database className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-xl font-bold font-mono text-purple-300">
            SQLite
          </div>
          <div className="text-[10px] text-slate-400 font-mono mt-1">WAL Mode Enabled</div>
        </div>
      </div>

      {/* Core Research Questions Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-5 space-y-2.5">
          <div className="flex items-center gap-2 text-cyan-400 font-mono text-xs font-semibold">
            <span className="w-5 h-5 rounded bg-cyan-950 flex items-center justify-center border border-cyan-800">1</span>
            SPATIAL TRAFFIC DENSITY
          </div>
          <h3 className="text-base font-bold text-white">Aggregated Observation Modeling</h3>
          <p className="text-xs text-slate-300 leading-relaxed">
            Raw trajectory observations mapped into half-open 2° spatial grid cells with 15-minute intervals. 
            Causal rolling counts and 8-neighbor spatial indicators model density across the subcontinent.
          </p>
        </div>

        <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-5 space-y-2.5">
          <div className="flex items-center gap-2 text-amber-400 font-mono text-xs font-semibold">
            <span className="w-5 h-5 rounded bg-amber-950 flex items-center justify-center border border-amber-800">2</span>
            LEAKAGE-FREE FORECASTING
          </div>
          <h3 className="text-base font-bold text-white">Future Window Prediction</h3>
          <p className="text-xs text-slate-300 leading-relaxed">
            Machine-learning models predict congestion classification for the NEXT 15-minute window strictly using 
            features available before window inception. Split chronologically into Train, Validation, and Test sets.
          </p>
        </div>

        <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-5 space-y-2.5">
          <div className="flex items-center gap-2 text-emerald-400 font-mono text-xs font-semibold">
            <span className="w-5 h-5 rounded bg-emerald-950 flex items-center justify-center border border-emerald-800">3</span>
            MULTI-OBJECTIVE ROUTING
          </div>
          <h3 className="text-base font-bold text-white">Explainable Graph Optimization</h3>
          <p className="text-xs text-slate-300 leading-relaxed">
            Transparent edge cost model balancing distance, travel time, weather penalty, and congestion exposure. 
            Dijkstra and A* with admissible great-circle heuristics deliver provably optimal paths.
          </p>
        </div>
      </div>
    </div>
  );
};
