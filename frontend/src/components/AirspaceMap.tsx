import React, { useState } from 'react';
import { MapContainer, TileLayer, CircleMarker, Polyline, Polygon, Tooltip, Popup } from 'react-leaflet';
import type { Airport, RouteEdge, RouteDetail, CongestionCell } from '../types';
import { Eye, Layers } from 'lucide-react';

interface AirspaceMapProps {
  airports?: Airport[];
  edges?: RouteEdge[];
  primaryRoute?: RouteDetail | null;
  secondaryRoute?: RouteDetail | null;
  congestionCells?: CongestionCell[];
  aircraft?: any[];
  center?: [number, number];
  zoom?: number;
  height?: string;
  onAirportClick?: (airport: Airport) => void;
}

export const AirspaceMap: React.FC<AirspaceMapProps> = ({
  airports = [],
  edges = [],
  primaryRoute = null,
  secondaryRoute = null,
  congestionCells = [],
  aircraft = [],
  center = [21.5, 78.0], // Center over India
  zoom = 5,
  height = '580px',
  onAirportClick,
}) => {
  // Layer visibility toggles
  const [showAirports, setShowAirports] = useState(true);
  const [showAirways, setShowAirways] = useState(true);
  const [showCongestion, setShowCongestion] = useState(false);
  const [showAircraft, setShowAircraft] = useState(true);

  // Map airports by node_id for quick coordinates lookup
  const airportMap = new Map<string, Airport>();
  airports.forEach((a) => airportMap.set(a.node_id, a));

  const getCellColor = (cls: string) => {
    switch (cls) {
      case 'HIGH':
        return '#ef4444';
      case 'MEDIUM':
        return '#f59e0b';
      case 'LOW':
      default:
        return '#10b981';
    }
  };

  return (
    <div className="relative w-full rounded-xl overflow-hidden border border-aerospace-800 shadow-2xl bg-aerospace-950">
      {/* Layer Toggles Control Overlay */}
      <div className="absolute top-4 right-4 z-[1000] bg-aerospace-900/90 backdrop-blur-md border border-aerospace-700/80 rounded-lg p-2.5 shadow-xl text-xs space-y-2">
        <div className="flex items-center gap-1.5 font-semibold text-slate-200 pb-1 border-b border-aerospace-800 font-mono">
          <Layers className="w-3.5 h-3.5 text-cyan-400" />
          <span>AIRSPACE LAYERS</span>
        </div>
        <label className="flex items-center gap-2 cursor-pointer text-slate-300 hover:text-white">
          <input
            type="checkbox"
            checked={showAirports}
            onChange={(e) => setShowAirports(e.target.checked)}
            className="rounded bg-aerospace-950 border-aerospace-700 text-cyan-500 focus:ring-0"
          />
          <span>Airports ({airports.length})</span>
        </label>
        <label className="flex items-center gap-2 cursor-pointer text-slate-300 hover:text-white">
          <input
            type="checkbox"
            checked={showAirways}
            onChange={(e) => setShowAirways(e.target.checked)}
            className="rounded bg-aerospace-950 border-aerospace-700 text-cyan-500 focus:ring-0"
          />
          <span>Airway Edges ({edges.length})</span>
        </label>
        <label className="flex items-center gap-2 cursor-pointer text-slate-300 hover:text-white">
          <input
            type="checkbox"
            checked={showCongestion}
            onChange={(e) => setShowCongestion(e.target.checked)}
            className="rounded bg-aerospace-950 border-aerospace-700 text-cyan-500 focus:ring-0"
          />
          <span>Congestion Grid</span>
        </label>
        <label className="flex items-center gap-2 cursor-pointer text-slate-300 hover:text-white">
          <input
            type="checkbox"
            checked={showAircraft}
            onChange={(e) => setShowAircraft(e.target.checked)}
            className="rounded bg-aerospace-950 border-aerospace-700 text-cyan-500 focus:ring-0"
          />
          <span>Surveillance ({aircraft.length})</span>
        </label>
      </div>

      <MapContainer
        center={center}
        zoom={zoom}
        style={{ height, width: '100%' }}
        scrollWheelZoom={true}
      >
        {/* CartoDB Dark Matter Basemap */}
        <TileLayer
          attribution='&copy; <a href="https://carto.com/">CARTO</a> &copy; OpenStreetMap'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />

        {/* 1. Congestion Grid Cells */}
        {showCongestion &&
          congestionCells.map((c) => {
            const [[sLat, wLon], [nLat, eLon]] = c.bounds;
            const polyCoords: [number, number][] = [
              [sLat, wLon],
              [sLat, eLon],
              [nLat, eLon],
              [nLat, wLon],
            ];
            return (
              <Polygon
                key={c.cell_id}
                positions={polyCoords}
                pathOptions={{
                  color: getCellColor(c.predicted_class),
                  fillColor: getCellColor(c.predicted_class),
                  fillOpacity: 0.15,
                  weight: 1,
                  dashArray: '2, 4',
                }}
              >
                <Tooltip sticky>
                  <div className="font-mono text-xs">
                    <strong>Cell {c.cell_id}</strong>
                    <div>Density: {c.predicted_class}</div>
                    <div>Score: {c.congestion_score.toFixed(2)}</div>
                    <div>Count: {c.aircraft_count}</div>
                  </div>
                </Tooltip>
              </Polygon>
            );
          })}

        {/* 2. Candidate Airway Edges */}
        {showAirways &&
          edges.map((e) => {
            const u = airportMap.get(e.source_node);
            const v = airportMap.get(e.target_node);
            if (!u || !v) return null;
            return (
              <Polyline
                key={e.edge_id}
                positions={[
                  [u.latitude, u.longitude],
                  [v.latitude, v.longitude],
                ]}
                pathOptions={{
                  color: '#1e293b',
                  weight: 1.2,
                  opacity: 0.6,
                }}
              >
                <Tooltip sticky>
                  <span className="font-mono text-[11px]">
                    {e.edge_id} ({e.distance_km.toFixed(0)} km)
                  </span>
                </Tooltip>
              </Polyline>
            );
          })}

        {/* 3. Secondary Route (e.g. Baseline unperturbed or alternative) */}
        {secondaryRoute?.geometry && secondaryRoute.geometry.length > 1 && (
          <Polyline
            positions={secondaryRoute.geometry}
            pathOptions={{
              color: '#f59e0b',
              weight: 3.5,
              opacity: 0.85,
              dashArray: '6, 6',
            }}
          >
            <Tooltip sticky>
              <div className="font-mono text-xs">
                <strong>{secondaryRoute.label || 'Baseline Route'}</strong>
                <div>Distance: {secondaryRoute.totals?.distance_km} km</div>
                <div>ETA: {secondaryRoute.totals?.estimated_time_min} min</div>
              </div>
            </Tooltip>
          </Polyline>
        )}

        {/* 4. Primary Route (Active / Rerouted / Selected) */}
        {primaryRoute?.geometry && primaryRoute.geometry.length > 1 && (
          <Polyline
            positions={primaryRoute.geometry}
            pathOptions={{
              color: '#00f0ff',
              weight: 4.5,
              opacity: 0.95,
            }}
          >
            <Tooltip sticky>
              <div className="font-mono text-xs">
                <strong>{primaryRoute.label || 'Active Route'}</strong>
                <div>Distance: {primaryRoute.totals?.distance_km} km</div>
                <div>ETA: {primaryRoute.totals?.estimated_time_min} min</div>
                <div>Hops: {primaryRoute.totals?.hops}</div>
              </div>
            </Tooltip>
          </Polyline>
        )}

        {/* 5. Airports */}
        {showAirports &&
          airports.map((a) => (
            <CircleMarker
              key={a.node_id}
              center={[a.latitude, a.longitude]}
              radius={a.iata ? 5.5 : 3.5}
              pathOptions={{
                color: a.iata ? '#00f0ff' : '#64748b',
                fillColor: a.iata ? '#0b1329' : '#1e293b',
                fillOpacity: 0.9,
                weight: 1.8,
              }}
              eventHandlers={{
                click: () => onAirportClick?.(a),
              }}
            >
              <Tooltip direction="top" offset={[0, -5]} opacity={0.9}>
                <div className="font-mono text-xs">
                  <strong>{a.iata || a.node_id}</strong> - {a.name}
                </div>
              </Tooltip>
              <Popup>
                <div className="font-sans text-xs p-1 space-y-1">
                  <div className="font-bold text-cyan-400 font-mono text-sm">{a.node_id} ({a.iata || 'WP'})</div>
                  <div className="text-slate-200">{a.name}</div>
                  <div className="text-slate-400 font-mono text-[11px]">
                    Lat: {a.latitude.toFixed(4)}, Lon: {a.longitude.toFixed(4)}
                  </div>
                  {a.elevation_m && (
                    <div className="text-slate-400 text-[11px]">Elevation: {a.elevation_m}m</div>
                  )}
                </div>
              </Popup>
            </CircleMarker>
          ))}

        {/* 6. Surveillance Aircraft */}
        {showAircraft &&
          aircraft.map((ac, idx) => {
            if (!ac.latitude || !ac.longitude) return null;
            return (
              <CircleMarker
                key={ac.observation_id || `ac-${idx}`}
                center={[ac.latitude, ac.longitude]}
                radius={3}
                pathOptions={{
                  color: '#10b981',
                  fillColor: '#10b981',
                  fillOpacity: 0.8,
                  weight: 1,
                }}
              >
                <Tooltip>
                  <div className="font-mono text-xs">
                    <strong>{ac.callsign || ac.source_aircraft_id}</strong>
                    <div>Speed: {ac.ground_speed_mps ? `${(ac.ground_speed_mps * 3.6).toFixed(0)} km/h` : 'N/A'}</div>
                    <div>Alt: {ac.altitude_m ? `${ac.altitude_m.toFixed(0)} m` : 'N/A'}</div>
                  </div>
                </Tooltip>
              </CircleMarker>
            );
          })}
      </MapContainer>
    </div>
  );
};
