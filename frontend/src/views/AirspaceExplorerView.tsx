import React, { useState } from 'react';
import { 
  Layers, 
  MapPin, 
  Route, 
  Plane, 
  Info, 
  ArrowRight, 
  Check 
} from 'lucide-react';
import type { Airport, AirspaceNetwork, CongestionCell } from '../types';
import { AirspaceMap } from '../components/AirspaceMap';

interface AirspaceExplorerViewProps {
  network: AirspaceNetwork | null;
  airports: Airport[];
  congestionCells: CongestionCell[];
  aircraft: any[];
  onSelectAirportForRouting?: (icao: string, role: 'origin' | 'destination') => void;
}

export const AirspaceExplorerView: React.FC<AirspaceExplorerViewProps> = ({
  network,
  airports,
  congestionCells,
  aircraft,
  onSelectAirportForRouting,
}) => {
  const [selectedAirport, setSelectedAirport] = useState<Airport | null>(null);

  const connectedEdges = selectedAirport && network
    ? network.edges.filter(
        (e) => e.source_node === selectedAirport.node_id || e.target_node === selectedAirport.node_id
      )
    : [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-5 shadow-lg">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2 font-mono">
              <Layers className="w-5 h-5 text-cyan-400" />
              AIRSPACE GEOSPATIAL EXPLORER
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Interactive map of the Indian subcontinent route network, surveillance telemetry, and research grid cells
            </p>
          </div>
          <div className="flex items-center gap-3 text-xs font-mono">
            <span className="text-slate-400">CORRIDOR BBOX: 6°–34°N, 66°–94°E</span>
          </div>
        </div>
      </div>

      {/* Main Map + Side Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-5">
        <div className="lg:col-span-3">
          <AirspaceMap
            airports={airports}
            waypoints={network?.waypoints || []}
            edges={network?.edges || []}
            congestionCells={congestionCells}
            aircraft={aircraft}
            height="620px"
            onAirportClick={(a) => setSelectedAirport(a)}
          />
        </div>

        {/* Airport Inspector Sidebar */}
        <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-5 space-y-4 shadow-lg flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-cyan-400 font-mono text-xs font-semibold pb-2 border-b border-aerospace-800">
              <MapPin className="w-4 h-4" />
              <span>NODE INSPECTOR</span>
            </div>

            {selectedAirport ? (
              <div className="space-y-3">
                <div>
                  <div className="text-xl font-bold font-mono text-white flex items-center gap-2">
                    {selectedAirport.node_id}
                    {selectedAirport.iata && (
                      <span className="text-xs px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800">
                        {selectedAirport.iata}
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-slate-300 mt-0.5">{selectedAirport.name}</div>
                  <div className="text-[11px] text-slate-400 font-mono mt-0.5">
                    {selectedAirport.country || 'India'}
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-aerospace-950 border border-aerospace-800 space-y-1.5 text-xs font-mono">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Latitude:</span>
                    <span className="text-slate-200">{selectedAirport.latitude.toFixed(4)}°N</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Longitude:</span>
                    <span className="text-slate-200">{selectedAirport.longitude.toFixed(4)}°E</span>
                  </div>
                  {selectedAirport.elevation_m !== undefined && (
                    <div className="flex justify-between">
                      <span className="text-slate-500">Elevation:</span>
                      <span className="text-slate-200">{selectedAirport.elevation_m} m</span>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span className="text-slate-500">Connected Airways:</span>
                    <span className="text-cyan-400 font-bold">{connectedEdges.length}</span>
                  </div>
                </div>

                {/* Connected Airways List */}
                <div>
                  <div className="text-[11px] font-mono text-slate-400 mb-1.5 uppercase">Adjacent Segments:</div>
                  <div className="space-y-1 max-h-40 overflow-y-auto pr-1">
                    {connectedEdges.map((e) => (
                      <div
                        key={e.edge_id}
                        className="px-2 py-1 rounded bg-aerospace-950 border border-aerospace-800 text-[11px] font-mono flex items-center justify-between text-slate-300"
                      >
                        <span>{e.edge_id}</span>
                        <span className="text-slate-400">{e.distance_km.toFixed(0)} km</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="py-12 text-center text-slate-500 text-xs font-sans">
                <MapPin className="w-8 h-8 text-slate-700 mx-auto mb-2" />
                Click any airport node on the map to inspect its flight network connections.
              </div>
            )}
          </div>

          {selectedAirport && onSelectAirportForRouting && (
            <div className="pt-3 border-t border-aerospace-800 grid grid-cols-2 gap-2">
              <button
                onClick={() => onSelectAirportForRouting(selectedAirport.node_id, 'origin')}
                className="px-3 py-2 rounded bg-cyan-950 hover:bg-cyan-900 text-cyan-300 border border-cyan-800 text-xs font-mono transition"
              >
                Set as Origin
              </button>
              <button
                onClick={() => onSelectAirportForRouting(selectedAirport.node_id, 'destination')}
                className="px-3 py-2 rounded bg-aerospace-800 hover:bg-aerospace-700 text-slate-200 border border-aerospace-600 text-xs font-mono transition"
              >
                Set as Dest
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
