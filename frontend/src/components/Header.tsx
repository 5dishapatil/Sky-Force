import React from 'react';
import { 
  Plane, 
  Layers, 
  Compass, 
  Zap, 
  BarChart3, 
  AlertTriangle, 
  FlaskConical, 
  ShieldCheck, 
  BookOpen, 
  Activity 
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

export const Header: React.FC<HeaderProps> = ({ activeTab, setActiveTab, systemStatus }) => {
  const tabs = [
    { id: 'overview', label: 'Overview', icon: Plane },
    { id: 'explorer', label: 'Airspace Map', icon: Layers },
    { id: 'routing', label: 'Route Lab', icon: Compass },
    { id: 'scenarios', label: 'Scenario Studio', icon: Zap },
    { id: 'congestion', label: 'Congestion AI', icon: BarChart3 },
    { id: 'conflicts', label: 'Conflict / CPA', icon: AlertTriangle },
    { id: 'evaluation', label: 'Model Metrics', icon: FlaskConical },
    { id: 'quality', label: 'Data & QA', icon: ShieldCheck },
    { id: 'docs', label: 'Research Guide', icon: BookOpen },
  ];

  return (
    <header className="sticky top-0 z-50 bg-aerospace-950/95 backdrop-blur border-b border-aerospace-800">
      {/* Required Operational Disclaimer Banner */}
      <div className="bg-amber-950/80 border-b border-amber-800/60 px-4 py-1 text-xs text-amber-200 flex items-center justify-between">
        <div className="flex items-center gap-2 font-medium">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
          <span>
            <strong>RESEARCH PROTOTYPE DISCLAIMER:</strong> For simulation and decision support only. 
            Not approved for operational flight planning, navigation, or air traffic control.
          </span>
        </div>
        <div className="hidden sm:flex items-center gap-3 text-[11px] text-amber-300/80 font-mono">
          <span>REGION: VIDP-VABB (India)</span>
          <span>MODE: Synthetic Research Stream</span>
        </div>
      </div>

      {/* Main Bar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Branding */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-cyan-500 to-aerospace-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
              <Plane className="w-5 h-5 text-white -rotate-45" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold tracking-wider text-white font-mono">SKY FORCE</h1>
                <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800 font-mono">
                  v1.0 Academic
                </span>
              </div>
              <p className="text-xs text-slate-400 hidden md:block">
                AI Airspace Analysis, Explainable Routing & Dynamic Rerouting
              </p>
            </div>
          </div>

          {/* System Status Indicators */}
          <div className="hidden lg:flex items-center gap-4 text-xs font-mono">
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-aerospace-900 border border-aerospace-700">
              <Activity className="w-3 h-3 text-emerald-400 animate-pulse" />
              <span className="text-slate-300">SYSTEM:</span>
              <span className="text-emerald-400 font-bold uppercase">{systemStatus.status || 'ONLINE'}</span>
            </div>
            
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-aerospace-900 border border-aerospace-700 text-slate-300">
              <span>DB:</span>
              <span className="text-cyan-300 uppercase">{systemStatus.database || 'SQLite (WAL)'}</span>
            </div>

            {systemStatus.activeScenario && (
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-amber-950/60 border border-amber-700 text-amber-300">
                <Zap className="w-3 h-3 text-amber-400" />
                <span>SCENARIO ACTIVE</span>
              </div>
            )}
          </div>
        </div>

        {/* Tab Navigation */}
        <nav className="flex space-x-1 overflow-x-auto py-2 scrollbar-none border-t border-aerospace-850">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium whitespace-nowrap transition-colors ${
                  isActive
                    ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/40 shadow-sm shadow-cyan-500/10'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-aerospace-900'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-cyan-400' : 'text-slate-400'}`} />
                {tab.label}
              </button>
            );
          })}
        </nav>
      </div>
    </header>
  );
};
