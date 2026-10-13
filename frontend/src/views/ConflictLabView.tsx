import React, { useState, useEffect } from 'react';
import { 
  AlertTriangle, 
  ShieldAlert, 
  Play, 
  Clock, 
  HelpCircle, 
  Sliders, 
  Search,
  CheckCircle2
} from 'lucide-react';
import type { ConflictScanResponse, ConflictEvent } from '../types';
import { api } from '../services/api';

export const ConflictLabView: React.FC = () => {
  const [horizon, setHorizon] = useState<number>(300);
  const [horizThresh, setHorizThresh] = useState<number>(9.26);
  const [vertThresh, setVertThresh] = useState<number>(300);
  const [scanData, setScanData] = useState<ConflictScanResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleScan = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getLatestConflicts(horizon, horizThresh, vertThresh);
      setScanData(res);
    } catch (err: any) {
      setError(err.message || 'Failed to scan conflicts');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    handleScan();
  }, []);

  const getSeverityBadge = (sev: string) => {
    switch (sev) {
      case 'HIGH':
        return 'bg-red-950 text-red-300 border-red-800 animate-pulse font-bold';
      case 'MEDIUM':
        return 'bg-amber-950 text-amber-300 border-amber-800 font-semibold';
      case 'LOW':
      default:
        return 'bg-emerald-950 text-emerald-300 border-emerald-800';
    }
  };

  return (
    <div className="space-y-6">
      {/* Required Conflict Prototype Disclaimer Banner */}
      <div className="bg-amber-950/60 border border-amber-800/80 rounded-xl p-4 text-xs text-amber-200 flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <div className="font-bold font-mono tracking-wide">
            EXPERIMENTAL CLOSEST POINT OF APPROACH (CPA) PROTOTYPE
          </div>
          <p className="leading-relaxed text-amber-200/90 font-sans">
            This module computes simplified linear trajectory proximity for visualization and research demonstration. 
            It is <strong>NOT</strong> an operational air traffic separation assurance, collision-avoidance, or tactical ATC system. 
            Thresholds configured below are user-tunable prototype proximity parameters, not certified separation standards.
          </p>
        </div>
      </div>

      {/* Control Panel */}
      <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-5 shadow-lg">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-4 pb-4 border-b border-aerospace-800">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2 font-mono">
              <ShieldAlert className="w-5 h-5 text-amber-400" />
              AIRSPACE PROXIMITY & CPA SCANNER
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Linear 3D forward projection over short horizons to evaluate potential airspace convergences
            </p>
          </div>

          <button
            onClick={handleScan}
            disabled={loading}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-aerospace-950 font-bold text-xs font-mono transition shadow-md shadow-amber-500/20 disabled:opacity-50"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            {loading ? 'CALCULATING CPA...' : 'RUN CPA SCAN'}
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-950/60 border border-red-800 text-red-200 text-xs">
            {error}
          </div>
        )}

        {/* Sliders */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
          <div>
            <div className="flex justify-between text-xs font-mono text-slate-400 mb-1.5">
              <span>FORECAST HORIZON</span>
              <span className="text-white font-bold">{horizon} s ({(horizon / 60).toFixed(1)} min)</span>
            </div>
            <input
              type="range"
              min="60"
              max="600"
              step="30"
              value={horizon}
              onChange={(e) => setHorizon(parseInt(e.target.value))}
              className="w-full h-1.5 bg-aerospace-800 rounded-lg appearance-none cursor-pointer accent-amber-400"
            />
            <span className="text-[10px] text-slate-500 font-mono">Default 300s (5 minutes)</span>
          </div>

          <div>
            <div className="flex justify-between text-xs font-mono text-slate-400 mb-1.5">
              <span>HORIZONTAL THRESHOLD</span>
              <span className="text-white font-bold">{horizThresh.toFixed(1)} km (~{(horizThresh / 1.852).toFixed(1)} NM)</span>
            </div>
            <input
              type="range"
              min="3"
              max="20"
              step="0.5"
              value={horizThresh}
              onChange={(e) => setHorizThresh(parseFloat(e.target.value))}
              className="w-full h-1.5 bg-aerospace-800 rounded-lg appearance-none cursor-pointer accent-amber-400"
            />
            <span className="text-[10px] text-slate-500 font-mono">Standard proxy ~5 Nautical Miles</span>
          </div>

          <div>
            <div className="flex justify-between text-xs font-mono text-slate-400 mb-1.5">
              <span>VERTICAL THRESHOLD</span>
              <span className="text-white font-bold">{vertThresh.toFixed(0)} m (~{(vertThresh * 3.28084).toFixed(0)} ft)</span>
            </div>
            <input
              type="range"
              min="100"
              max="1000"
              step="50"
              value={vertThresh}
              onChange={(e) => setVertThresh(parseFloat(e.target.value))}
              className="w-full h-1.5 bg-aerospace-800 rounded-lg appearance-none cursor-pointer accent-amber-400"
            />
            <span className="text-[10px] text-slate-500 font-mono">Standard proxy ~1,000 feet</span>
          </div>
        </div>
      </div>

      {/* Summary KPI Cards */}
      {scanData && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono">
          <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-3.5">
            <div className="text-[11px] text-slate-400">AIRCRAFT SCANNED</div>
            <div className="text-xl font-bold text-white mt-1">{scanData.aircraft_scanned}</div>
            <div className="text-[10px] text-slate-500 mt-0.5">Surveillance observations</div>
          </div>

          <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-3.5">
            <div className="text-[11px] text-slate-400">PAIRS EVALUATED</div>
            <div className="text-xl font-bold text-slate-200 mt-1">{scanData.pairs_evaluated}</div>
            <div className="text-[10px] text-slate-500 mt-0.5">Combinatorial pairs N(N-1)/2</div>
          </div>

          <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-3.5">
            <div className="text-[11px] text-slate-400">PROXIMITY EVENTS</div>
            <div className="text-xl font-bold text-amber-400 mt-1">{scanData.proximity_events_found}</div>
            <div className="text-[10px] text-slate-500 mt-0.5">Within configured bounds</div>
          </div>

          <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-3.5">
            <div className="text-[11px] text-slate-400">HIGH SEVERITY</div>
            <div className="text-xl font-bold text-red-400 mt-1">
              {scanData.events.filter((e) => e.severity === 'HIGH').length}
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">Under 50% threshold</div>
          </div>
        </div>
      )}

      {/* Events Table */}
      <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-5 shadow-lg space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-white font-mono flex items-center gap-2">
            <Clock className="w-4 h-4 text-amber-400" />
            PROXIMITY & CONVERGENCE EVENT STREAM
          </h3>
          <span className="text-xs font-mono text-slate-400">
            {scanData?.events?.length || 0} event(s) recorded
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-aerospace-950 text-slate-400 border-b border-aerospace-800">
              <tr>
                <th className="py-2.5 px-3">Event ID</th>
                <th className="py-2.5 px-3">Pair (Aircraft 1 vs 2)</th>
                <th className="py-2.5 px-3">Current Dist</th>
                <th className="py-2.5 px-3">Time to CPA (t_cpa)</th>
                <th className="py-2.5 px-3">Dist at CPA</th>
                <th className="py-2.5 px-3">Vert Diff</th>
                <th className="py-2.5 px-3">Severity</th>
                <th className="py-2.5 px-3">Uncertainty Flags</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-aerospace-800 text-slate-300">
              {scanData?.events?.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-500">
                    No pairwise proximity events detected within the active thresholds.
                  </td>
                </tr>
              ) : (
                scanData?.events.map((e) => (
                  <tr key={e.event_id} className="hover:bg-aerospace-850/50 transition">
                    <td className="py-2 px-3 text-slate-400 text-[11px] truncate max-w-[120px]">{e.event_id}</td>
                    <td className="py-2 px-3 font-semibold text-white">
                      <span className="text-cyan-300">{e.callsign_1 || e.aircraft_1}</span>
                      <span className="text-slate-500 mx-1">↔</span>
                      <span className="text-amber-300">{e.callsign_2 || e.aircraft_2}</span>
                    </td>
                    <td className="py-2 px-3">{e.current_horizontal_dist_km.toFixed(1)} km</td>
                    <td className="py-2 px-3 text-cyan-300 font-bold">{e.cpa_time_seconds.toFixed(0)} s</td>
                    <td className="py-2 px-3 font-bold text-white">{e.cpa_horizontal_dist_km.toFixed(2)} km</td>
                    <td className="py-2 px-3 text-slate-300">
                      {e.cpa_vertical_diff_m != null ? `${e.cpa_vertical_diff_m.toFixed(0)} m` : 'Unknown'}
                    </td>
                    <td className="py-2 px-3">
                      <span className={`px-2 py-0.5 rounded border text-[10px] ${getSeverityBadge(e.severity)}`}>
                        {e.severity}
                      </span>
                    </td>
                    <td className="py-2 px-3">
                      {e.data_uncertainty_flags.length > 0 ? (
                        <div className="flex flex-wrap gap-1">
                          {e.data_uncertainty_flags.map((f, i) => (
                            <span key={i} className="px-1.5 py-0.2 rounded bg-purple-950 text-purple-300 border border-purple-800 text-[9px]">
                              {f}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-slate-500 text-[10px]">None</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
