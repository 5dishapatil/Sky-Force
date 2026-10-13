import React from 'react';
import {
  Activity,
  ArrowRight,
  BrainCircuit,
  Database,
  GitBranch,
  MapPinned,
  Route,
  ShieldCheck,
  Waypoints,
} from 'lucide-react';
import type { Airport, AirspaceNetwork, CongestionCell, ModelsStatusResponse } from '../types';
import { AirspaceMap } from '../components/AirspaceMap';

interface OverviewViewProps {
  network: AirspaceNetwork | null;
  airports: Airport[];
  modelsStatus: ModelsStatusResponse | null;
  congestionCells: CongestionCell[];
  aircraft: Record<string, unknown>[];
  onNavigate: (tab: string) => void;
}

const formatCount = (value: number | undefined | null) => value == null ? '—' : value.toLocaleString();

export const OverviewView: React.FC<OverviewViewProps> = ({
  network,
  airports,
  modelsStatus,
  congestionCells,
  aircraft,
  onNavigate,
}) => {
  const congestionLoaded = modelsStatus?.congestion_model?.is_loaded === true;
  const etaLoaded = modelsStatus?.eta_model?.is_loaded === true;
  const loadedModels = [congestionLoaded, etaLoaded].filter(Boolean).length;

  const statCards = [
    { label: 'Airports', value: formatCount(network?.total_airports ?? (airports.length || null)), sub: 'Reference nodes', icon: MapPinned, accent: 'cyan' },
    { label: 'Waypoints', value: formatCount(network?.total_waypoints), sub: 'Intermediate nodes', icon: Waypoints, accent: 'blue' },
    { label: 'Airway segments', value: formatCount(network?.total_edges), sub: 'Graph connections', icon: GitBranch, accent: 'violet' },
    { label: 'ML models loaded', value: modelsStatus ? `${loadedModels} / 2` : '—', sub: modelsStatus ? `${congestionLoaded ? 'Classifier ready' : 'Classifier unavailable'} · ${etaLoaded ? 'ETA ready' : 'ETA unavailable'}` : 'Model status unavailable', icon: BrainCircuit, accent: modelsStatus && loadedModels === 2 ? 'green' : 'amber' },
  ];

  return (
    <div className="space-y-5 page-overview">
      <section className="overview-intro">
        <div className="overview-intro-copy">
          <div className="section-kicker"><span className="kicker-dot" /> AIRSPACE DECISION SUPPORT · INDIA</div>
          <h2>See the airspace.<br /><span>Anticipate what changes next.</span></h2>
          <p>
            Explore aircraft observations, inspect machine-learning forecasts, and compare routes under
            weather, congestion, and simulated corridor disruptions.
          </p>
          <div className="overview-actions">
            <button type="button" className="action-primary" onClick={() => onNavigate('routing')}>
              <Route size={16} /> Plan a route <ArrowRight size={15} />
            </button>
            <button type="button" className="action-secondary" onClick={() => onNavigate('congestion')}>
              <BrainCircuit size={16} /> Inspect ML models
            </button>
          </div>
        </div>
        <div className="overview-intro-mark" aria-hidden="true">
          <div className="radar-ring radar-ring-one" />
          <div className="radar-ring radar-ring-two" />
          <div className="radar-ring radar-ring-three" />
          <div className="radar-sweep" />
          <div className="radar-center"><Route size={25} /></div>
          <span className="radar-point radar-point-a" />
          <span className="radar-point radar-point-b" />
          <span className="radar-point radar-point-c" />
        </div>
      </section>

      <section className="stats-grid" aria-label="System summary">
        {statCards.map((card) => {
          const Icon = card.icon;
          return (
            <article className={`stat-card accent-${card.accent}`} key={card.label}>
              <div className="stat-card-top"><span>{card.label}</span><Icon size={17} /></div>
              <div className="stat-card-value">{card.value}</div>
              <div className="stat-card-subtitle">{card.sub}</div>
            </article>
          );
        })}
      </section>

      <section className="overview-grid">
        <article className="surface-card overview-map-card">
          <div className="surface-card-heading">
            <div>
              <p className="eyebrow">GEOSPATIAL WORKSPACE</p>
              <h3>Airspace network</h3>
              <p className="surface-subtitle">Select an airport marker or use the map layers to inspect the corridor.</p>
            </div>
            <button className="text-action" type="button" onClick={() => onNavigate('explorer')}>Open explorer <ArrowRight size={14} /></button>
          </div>
          <AirspaceMap
            airports={airports}
            waypoints={network?.waypoints || []}
            edges={network?.edges || []}
            congestionCells={congestionCells}
            aircraft={aircraft}
            height="440px"
          />
          <div className="map-legend-row">
            <span><i className="legend-dot legend-airport" /> Airports</span>
            <span><i className="legend-line legend-airway" /> Airways</span>
            <span><i className="legend-dot legend-aircraft" /> Observations</span>
            <span><i className="legend-dot legend-congestion" /> Congestion overlay (toggle on map)</span>
          </div>
        </article>

        <aside className="overview-side-stack">
          <article className="surface-card model-status-card">
            <div className="surface-card-heading compact-heading">
              <div><p className="eyebrow">INFERENCE READINESS</p><h3>Model status</h3></div>
              <BrainCircuit size={19} className="text-cyan-300" />
            </div>
            <div className="model-status-row">
              <div className="model-status-icon"><Activity size={16} /></div>
              <div className="model-status-copy"><strong>Congestion classifier</strong><span>{modelsStatus?.congestion_model?.name || (modelsStatus ? 'Model metadata unavailable' : 'Awaiting model status')}</span></div>
              <span className={`status-tag ${congestionLoaded ? 'tag-good' : 'tag-muted'}`}>{!modelsStatus ? 'STATUS UNKNOWN' : congestionLoaded ? 'LOADED' : 'NOT LOADED'}</span>
            </div>
            <div className="model-status-row">
              <div className="model-status-icon model-status-icon-blue"><Route size={16} /></div>
              <div className="model-status-copy"><strong>Segment ETA regressor</strong><span>{modelsStatus?.eta_model?.name || (modelsStatus ? 'Model metadata unavailable' : 'Awaiting model status')}</span></div>
              <span className={`status-tag ${etaLoaded ? 'tag-good' : 'tag-muted'}`}>{!modelsStatus ? 'STATUS UNKNOWN' : etaLoaded ? 'LOADED' : 'NOT LOADED'}</span>
            </div>
            {!modelsStatus && <p className="inline-note"><Database size={14} /> Model status is unavailable. Check that the backend and model artifacts are ready.</p>}
            <button type="button" className="full-width-link" onClick={() => onNavigate('evaluation')}>View evaluation evidence <ArrowRight size={14} /></button>
          </article>

          <article className="surface-card pipeline-card">
            <div className="surface-card-heading compact-heading">
              <div><p className="eyebrow">END-TO-END FLOW</p><h3>From observations to routes</h3></div>
              <GitBranch size={19} className="text-cyan-300" />
            </div>
            <div className="pipeline-steps">
              <div className="pipeline-step"><span className="pipeline-step-number">01</span><span><strong>Ingest & validate</strong><small>Observations · weather · QA</small></span></div>
              <div className="pipeline-connector" />
              <div className="pipeline-step"><span className="pipeline-step-number">02</span><span><strong>Predict</strong><small>Congestion class · segment ETA</small></span></div>
              <div className="pipeline-connector" />
              <div className="pipeline-step"><span className="pipeline-step-number">03</span><span><strong>Optimize & evaluate</strong><small>A* / Dijkstra · scenario rerouting</small></span></div>
            </div>
            <div className="provenance-note"><ShieldCheck size={15} /><span>Research dataset. Synthetic and observed records must remain clearly distinguished.</span></div>
            <button type="button" className="full-width-link" onClick={() => onNavigate('quality')}>Inspect data & provenance <ArrowRight size={14} /></button>
          </article>
        </aside>
      </section>

      <section className="quick-path-grid">
        <button type="button" className="quick-path-card" onClick={() => onNavigate('congestion')}>
          <span className="quick-path-icon cyan-icon"><BrainCircuit size={19} /></span>
          <span><strong>Congestion Intelligence</strong><small>Inspect model readiness, predictions, and feature importance.</small></span>
          <ArrowRight size={16} />
        </button>
        <button type="button" className="quick-path-card" onClick={() => onNavigate('routing')}>
          <span className="quick-path-icon blue-icon"><Route size={19} /></span>
          <span><strong>Route Optimization</strong><small>Compare distance, travel time, weather, and congestion costs.</small></span>
          <ArrowRight size={16} />
        </button>
        <button type="button" className="quick-path-card" onClick={() => onNavigate('scenarios')}>
          <span className="quick-path-icon amber-icon"><Activity size={19} /></span>
          <span><strong>Disruption Simulation</strong><small>Activate a scenario and compare a rerouted path.</small></span>
          <ArrowRight size={16} />
        </button>
      </section>
    </div>
  );
};
