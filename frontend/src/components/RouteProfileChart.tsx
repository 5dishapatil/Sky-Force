import React from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from 'recharts';
import type { RouteDetail, RouteSegment } from '../types';

interface RouteProfileChartProps {
  route: RouteDetail | null;
  selectedSegmentId: string | null;
  onSelectSegment: (segment: RouteSegment | null) => void;
}

export const RouteProfileChart: React.FC<RouteProfileChartProps> = ({
  route,
  selectedSegmentId,
  onSelectSegment,
}) => {
  if (!route || !route.segments || route.segments.length === 0) {
    return null;
  }

  // Construct along-track cumulative distance profile data
  let cumulativeDist = 0;
  const chartData = route.segments.map((seg, idx) => {
    const startKm = cumulativeDist;
    cumulativeDist += seg.distance_km;
    const midKm = (startKm + cumulativeDist) / 2;

    return {
      segmentId: seg.edge_id,
      fromNode: seg.from_node,
      toNode: seg.to_node,
      nodeLabel: `${seg.from_node}→${seg.to_node}`,
      startKm: Math.round(startKm),
      midKm: Math.round(midKm),
      endKm: Math.round(cumulativeDist),
      weatherSeverity: seg.weather_severity !== null ? Math.round(seg.weather_severity * 100) : 0,
      congestionScore: seg.congestion_score !== null ? Math.round(seg.congestion_score * 100) : 0,
      uncertaintyPct: Math.round(seg.uncertainty * 100),
      traversalTimeMin: Number(seg.time_min.toFixed(1)),
      segment: seg,
      isSelected: seg.edge_id === selectedSegmentId,
    };
  });

  return (
    <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-5 shadow-lg space-y-3 font-mono">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-cyan-400" />
            ALONG-TRACK HAZARD & DENSITY PROFILE
          </h3>
          <p className="text-[11px] text-slate-400 mt-0.5">
            Synchronized hazard progression: Click any point along the route to inspect and highlight the geographic segment.
          </p>
        </div>
        <div className="text-xs text-slate-400">
          Total Distance: <strong className="text-white">{Math.round(cumulativeDist)} km</strong>
        </div>
      </div>

      <div className="h-56 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={chartData}
            margin={{ top: 15, right: 15, left: -20, bottom: 20 }}
            onClick={(e: any) => {
              if (e && e.activePayload && e.activePayload.length > 0) {
                const seg = e.activePayload[0].payload.segment;
                onSelectSegment(seg);
              }
            }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis
              dataKey="endKm"
              tick={{ fill: '#94a3b8', fontSize: 10, fontFamily: 'monospace' }}
              label={{
                value: 'Cumulative Distance Along Track (km)',
                position: 'insideBottom',
                offset: -12,
                fill: '#64748b',
                fontSize: 10,
              }}
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fill: '#94a3b8', fontSize: 10, fontFamily: 'monospace' }}
              label={{
                value: 'Severity / Density (%)',
                angle: -90,
                position: 'insideLeft',
                fill: '#64748b',
                fontSize: 10,
              }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#0a1026',
                borderColor: '#1e3a8a',
                borderRadius: '8px',
                color: '#e2e8f0',
                fontSize: '11px',
                fontFamily: 'monospace',
              }}
              formatter={(val: any, name: any) => [
                `${val}%`,
                name === 'weatherSeverity' ? 'Weather Hazard Severity' : 'Congestion Density',
              ]}
              labelFormatter={(_, payload) => {
                if (payload && payload[0]) {
                  const d = payload[0].payload;
                  return `${d.nodeLabel} (${d.startKm} - ${d.endKm} km)`;
                }
                return '';
              }}
            />
            <Legend
              wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }}
              formatter={(value) => (
                <span className="text-slate-300">
                  {value === 'weatherSeverity'
                    ? 'Convective Weather Severity (%)'
                    : value === 'congestionScore'
                    ? 'Traffic Congestion Score (%)'
                    : 'Uncertainty (%)'}
                </span>
              )}
            />
            <Area
              type="monotone"
              dataKey="weatherSeverity"
              stroke="#f59e0b"
              fill="#f59e0b"
              fillOpacity={0.25}
              strokeWidth={2}
            />
            <Line
              type="monotone"
              dataKey="congestionScore"
              stroke="#f43f5e"
              strokeWidth={2.5}
              dot={{ r: 3, fill: '#f43f5e' }}
              activeDot={{ r: 6, fill: '#06b6d4', stroke: '#fff' }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {selectedSegmentId && (
        <div className="p-2 rounded bg-cyan-950/40 border border-cyan-800/60 text-[11px] text-cyan-200 flex items-center justify-between">
          <span>Active Highlighted Segment: <strong>{selectedSegmentId}</strong></span>
          <button
            onClick={() => onSelectSegment(null)}
            className="text-xs text-slate-400 hover:text-white underline ml-3"
          >
            Clear Selection
          </button>
        </div>
      )}
    </div>
  );
};
