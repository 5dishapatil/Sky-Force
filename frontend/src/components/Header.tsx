import React from 'react';
import {
  Activity,
  AlertTriangle,
  BarChart3,
  BookOpen,
  ChevronRight,
  Clock,
  Database,
  FlaskConical,
  FolderGit2,
  Gauge,
  Layers,
  Map,
  Plane,
  Route,
  ShieldCheck,
  UploadCloud,
  Zap,
} from 'lucide-react';

interface HeaderProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  systemStatus: {
    status: string;
    database: string;
    activeScenario?: string | null;
  };
}

const navigationGroups = [
  {
    label: 'WORKSPACE',
    items: [
      { id: 'overview', label: 'Mission Control', icon: Gauge },
      { id: 'studio', label: 'Dataset Studio', icon: UploadCloud },
      { id: 'dataset-explorer', label: 'Dataset Lifecycle', icon: FolderGit2 },
      { id: 'explorer', label: 'Airspace Explorer', icon: Map },
      { id: 'routing', label: 'Route Optimization', icon: Route },
      { id: 'scenarios', label: 'Scenario Studio', icon: Zap },
    ],
  },
  {
    label: 'INTELLIGENCE',
    items: [
      { id: 'delay-intelligence', label: 'Flight Delay AI', icon: Clock },
      { id: 'congestion', label: 'Congestion AI', icon: BarChart3 },
      { id: 'evaluation', label: 'Model Evaluation', icon: FlaskConical },
    ],
  },
  {
    label: 'GUIDANCE & QA',
    items: [
      { id: 'quality', label: 'Data & QA', icon: ShieldCheck },
      { id: 'docs', label: 'Operator Guide & Docs', icon: BookOpen },
    ],
  },
];

export const tabLabels: Record<string, string> = Object.fromEntries(
  navigationGroups.flatMap((group) => group.items.map((item) => [item.id, item.label] as const)),
);

export const Header: React.FC<HeaderProps> = ({ activeTab, setActiveTab, systemStatus }) => {
  const normalizedStatus = (systemStatus.status || 'UNKNOWN').toLowerCase();
  const healthy = ['ok', 'online', 'healthy', 'operational'].includes(normalizedStatus);
  const checking = normalizedStatus === 'checking';

  return (
    <aside className="app-sidebar" aria-label="Main navigation">
      <button className="brand-lockup" onClick={() => setActiveTab('overview')} aria-label="Sky Force mission control">
        <span className="brand-mark"><Plane size={22} strokeWidth={2.2} /></span>
        <span className="brand-copy">
          <span className="brand-name">SKY FORCE</span>
          <span className="brand-subtitle">AIRSPACE INTELLIGENCE</span>
        </span>
      </button>

      <div className="sidebar-environment">
        <span className="environment-dot" />
        <span>RESEARCH ENVIRONMENT</span>
      </div>

      <nav className="sidebar-navigation">
        {navigationGroups.map((group) => (
          <div className="nav-group" key={group.label}>
            <div className="nav-group-label">{group.label}</div>
            {group.items.map((item) => {
              const Icon = item.icon;
              const selected = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  className={`nav-item${selected ? ' is-active' : ''}`}
                  aria-current={selected ? 'page' : undefined}
                  onClick={() => setActiveTab(item.id)}
                >
                  <Icon size={17} strokeWidth={1.8} />
                  <span>{item.label}</span>
                  {selected && <ChevronRight className="nav-chevron" size={15} />}
                </button>
              );
            })}
          </div>
        ))}
      </nav>

      <div className="sidebar-bottom">
        <div className="sidebar-status-card">
          <div className="status-card-heading">
            <Activity size={15} />
            <span>BACKEND STATUS</span>
          </div>
          <div className="status-card-row">
            <span className={`status-indicator ${healthy ? 'status-good' : checking ? 'status-pending' : 'status-bad'}`} />
            <span className="status-card-value">{healthy ? 'Connected' : checking ? 'Checking…' : 'Unavailable'}</span>
          </div>
          <div className="status-card-row status-muted-row">
            <Database size={13} />
            <span>Database</span>
            <strong>{systemStatus.database || 'Unknown'}</strong>
          </div>
          {systemStatus.activeScenario && (
            <div className="active-scenario-label" title={systemStatus.activeScenario}>
              <Zap size={12} /> Scenario active
            </div>
          )}
        </div>
        <div className="sidebar-build-label">V2.0 · MULTI-ROLE PLATFORM</div>
      </div>
    </aside>
  );
};
