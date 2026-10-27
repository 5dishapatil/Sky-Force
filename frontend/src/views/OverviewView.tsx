import React from 'react';
import {
  Activity,
  ArrowRight,
  BookOpen,
  BrainCircuit,
  CloudLightning,
  Compass,
  Database,
  FolderGit2,
  GitBranch,
  HelpCircle,
  Map,
  MapPinned,
  Play,
  Route,
  ShieldCheck,
  Sparkles,
  UploadCloud,
  Waypoints,
  Zap,
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

  const workflowSteps = [
    {
      num: '01',
      title: 'Dataset Studio',
      tab: 'studio',
      tag: 'INGEST',
      color: 'border-cyan-500/40 text-cyan-400 bg-cyan-950/20',
      icon: UploadCloud,
      desc: 'Upload custom CSVs with multi-schema mapping and spatiotemporal weather linking.',
      actionLabel: 'Open Studio',
    },
    {
      num: '02',
      title: 'Airspace Explorer',
      tab: 'explorer',
      tag: 'SURVEILLANCE',
      color: 'border-blue-500/40 text-blue-400 bg-blue-950/20',
      icon: Map,
      desc: 'Visualize aircraft telemetry, 2° spatial grid density, and live storms in 2D or 3D.',
      actionLabel: 'View Airspace',
    },
    {
      num: '03',
      title: 'Scenario Studio',
      tab: 'scenarios',
      tag: 'DISRUPTIONS',
      color: 'border-amber-500/40 text-amber-400 bg-amber-950/20',
      icon: Zap,
      desc: 'Simulate severe convective storm cells, runway closures, and sector shutdowns.',
      actionLabel: 'Test Scenarios',
    },
    {
      num: '04',
      title: 'Route Optimization',
      tab: 'routing',
      tag: 'MULTI-OBJECTIVE',
      color: 'border-emerald-500/40 text-emerald-400 bg-emerald-950/20',
      icon: Route,
      desc: 'Solve A* / Dijkstra paths with Pareto frontiers, 3D deck.gl profiles, and LLM explanations.',
      actionLabel: 'Plan Route',
    },
    {
      num: '05',
      title: 'AI Intelligence & QA',
      tab: 'congestion',
      tag: 'VALIDATION',
      color: 'border-purple-500/40 text-purple-400 bg-purple-950/20',
      icon: BrainCircuit,
      desc: 'Examine Random Forest congestion forecasts, segment ETAs, and 9-stage scrubber QA.',
      actionLabel: 'Inspect Models',
    },
  ];

  return (
    <div className="space-y-6 page-overview">
      {/* Hero Banner */}
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
            <button type="button" className="action-secondary" onClick={() => onNavigate('docs')}>
              <BookOpen size={16} /> How to operate this project
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

      {/* 5-Step Interactive Operating Pipeline */}
      <section className="bg-gradient-to-r from-aerospace-900/95 via-aerospace-850 to-aerospace-900 border border-cyan-800/50 rounded-xl p-5 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4 pb-3 border-b border-aerospace-800">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse" />
              <h3 className="text-sm font-bold font-mono tracking-wider text-white uppercase flex items-center gap-2">
                OPERATIONAL PIPELINE & NAVIGATION WORKFLOW
              </h3>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              New to Sky Force? Follow this standard 5-step operational flow to operate every capability in this platform.
            </p>
          </div>
          <button
            type="button"
            onClick={() => onNavigate('docs')}
            className="self-start sm:self-auto inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-950/80 border border-cyan-600/60 text-cyan-300 text-xs font-semibold hover:bg-cyan-900/60 transition-all cursor-pointer shadow-sm"
          >
            <BookOpen size={13} />
            <span>Open Complete Operator Manual</span>
            <ArrowRight size={12} />
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-3">
          {workflowSteps.map((step) => {
            const StepIcon = step.icon;
            return (
              <div
                key={step.num}
                className={`flex flex-col justify-between p-3.5 rounded-lg border bg-aerospace-950/80 hover:bg-aerospace-900 transition-all group ${step.color.split(' ')[0]}`}
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono text-xs font-bold text-slate-400 group-hover:text-cyan-400 transition-colors">
                      {step.num}
                    </span>
                    <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded font-semibold border ${step.color}`}>
                      {step.tag}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 mb-1.5">
                    <StepIcon size={16} className={step.color.split(' ')[1]} />
                    <h4 className="text-xs font-bold text-slate-100 group-hover:text-white">
                      {step.title}
                    </h4>
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed font-sans mb-3">
                    {step.desc}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => onNavigate(step.tab)}
                  className="w-full mt-auto py-1.5 px-2.5 rounded bg-aerospace-800/80 hover:bg-cyan-600 text-slate-200 hover:text-white text-[11px] font-semibold transition-all inline-flex items-center justify-between cursor-pointer"
                >
                  <span>{step.actionLabel}</span>
                  <ArrowRight size={12} />
                </button>
              </div>
            );
          })}
        </div>
      </section>

      {/* Top Stats */}
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

      {/* Main Grid: Airspace Map + Side Panels */}
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

      {/* Quick Jump Grid */}
      <section className="quick-path-grid">
        <button type="button" className="quick-path-card" onClick={() => onNavigate('studio')}>
          <span className="quick-path-icon cyan-icon"><UploadCloud size={19} /></span>
          <span><strong>Dataset Studio</strong><small>Upload, map, and link custom CSV flight telemetry & weather.</small></span>
          <ArrowRight size={16} />
        </button>
        <button type="button" className="quick-path-card" onClick={() => onNavigate('routing')}>
          <span className="quick-path-icon blue-icon"><Route size={19} /></span>
          <span><strong>Route Optimization</strong><small>Calculate 2D/3D multi-objective routes with Pareto alternatives.</small></span>
          <ArrowRight size={16} />
        </button>
        <button type="button" className="quick-path-card" onClick={() => onNavigate('docs')}>
          <span className="quick-path-icon purple-icon"><BookOpen size={19} /></span>
          <span><strong>Operator Guide & Playbook</strong><small>Step-by-step instructions for every screen, feature, and viva Q&A.</small></span>
          <ArrowRight size={16} />
        </button>
      </section>
    </div>
  );
};
