import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { OverviewView } from './views/OverviewView';
import { AirspaceExplorerView } from './views/AirspaceExplorerView';
import { RouteLabView } from './views/RouteLabView';
import { ScenarioStudioView } from './views/ScenarioStudioView';
import { CongestionIntelligenceView } from './views/CongestionIntelligenceView';
import { ConflictLabView } from './views/ConflictLabView';
import { ModelEvaluationView } from './views/ModelEvaluationView';
import { DataQualityView } from './views/DataQualityView';
import { DocumentationView } from './views/DocumentationView';
import { api } from './services/api';
import type { Airport, AirspaceNetwork, Scenario, ModelsStatusResponse, CongestionCell } from './types';

export function App() {
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [systemStatus, setSystemStatus] = useState<{ status: string; database: string; activeScenario?: string | null }>({
    status: 'ONLINE',
    database: 'SQLite (WAL)',
  });

  const [airports, setAirports] = useState<Airport[]>([]);
  const [network, setNetwork] = useState<AirspaceNetwork | null>(null);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [modelsStatus, setModelsStatus] = useState<ModelsStatusResponse | null>(null);
  const [congestionCells, setCongestionCells] = useState<CongestionCell[]>([]);
  const [aircraft, setAircraft] = useState<any[]>([]);

  // Initial Data Fetch
  useEffect(() => {
    const initApp = async () => {
      try {
        const [healthRes, apRes, netRes, scRes, modRes, cgRes, acRes] = await Promise.all([
          api.getHealth().catch(() => ({ status: 'ok', database: 'sqlite' })),
          api.getAirports().catch(() => []),
          api.getAirspaceNetwork().catch(() => null),
          api.getScenarios().catch(() => []),
          api.getModelsStatus().catch(() => null),
          api.getCongestionCells().catch(() => []),
          api.getAircraftObservations(150).catch(() => ({ observations: [] })),
        ]);

        const activeSc = scRes.find((s: Scenario) => s.is_active);
        setSystemStatus({
          status: healthRes.status || 'ONLINE',
          database: healthRes.database || 'SQLite',
          activeScenario: activeSc ? activeSc.name : null,
        });

        setAirports(apRes);
        setNetwork(netRes);
        setScenarios(scRes);
        setModelsStatus(modRes);
        setCongestionCells(cgRes);
        setAircraft(acRes.observations || []);
      } catch (err) {
        console.error('Initial data load error:', err);
      }
    };

    initApp();
  }, []);

  const refreshScenarios = async () => {
    try {
      const scRes = await api.getScenarios();
      setScenarios(scRes);
      const activeSc = scRes.find((s: Scenario) => s.is_active);
      setSystemStatus((prev) => ({
        ...prev,
        activeScenario: activeSc ? activeSc.name : null,
      }));
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="min-h-screen bg-aerospace-950 text-slate-100 flex flex-col font-sans selection:bg-cyan-500 selection:text-aerospace-950">
      {/* Top Navbar & Operational Disclaimer */}
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        systemStatus={systemStatus}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === 'overview' && (
          <OverviewView
            network={network}
            modelsStatus={modelsStatus}
            onNavigate={(tab) => setActiveTab(tab)}
          />
        )}

        {activeTab === 'explorer' && (
          <AirspaceExplorerView
            network={network}
            airports={airports}
            congestionCells={congestionCells}
            aircraft={aircraft}
          />
        )}

        {activeTab === 'routing' && (
          <RouteLabView
            network={network}
            airports={airports}
          />
        )}

        {activeTab === 'scenarios' && (
          <ScenarioStudioView
            scenarios={scenarios}
            onScenarioChange={refreshScenarios}
            airports={airports}
            network={network}
          />
        )}

        {activeTab === 'congestion' && (
          <CongestionIntelligenceView
            modelsStatus={modelsStatus}
          />
        )}

        {activeTab === 'conflicts' && (
          <ConflictLabView />
        )}

        {activeTab === 'evaluation' && (
          <ModelEvaluationView />
        )}

        {activeTab === 'quality' && (
          <DataQualityView />
        )}

        {activeTab === 'docs' && (
          <DocumentationView />
        )}
      </main>

      {/* Bottom Footer with Persistent Disclaimer */}
      <footer className="bg-aerospace-950 border-t border-aerospace-800/80 py-4 px-4 text-center text-xs text-slate-500 space-y-1">
        <p className="font-mono text-slate-400">
          Sky Force: AI-Driven Framework for Predictive Airspace Analysis, Explainable Route Optimisation & Dynamic Rerouting
        </p>
        <p className="text-[11px] text-amber-300/70 font-mono">
          Research prototype for simulation and decision support. Not approved for operational flight planning, navigation, or air traffic control.
        </p>
      </footer>
    </div>
  );
}

export default App;
