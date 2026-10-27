import React from 'react';
import { User, Compass, Sparkles, CheckCircle2 } from 'lucide-react';
import type { UserRole } from '../types';

interface RoleSwitcherProps {
  currentRole: UserRole;
  onRoleChange: (role: UserRole) => void;
}

export const RoleSwitcher: React.FC<RoleSwitcherProps> = ({ currentRole, onRoleChange }) => {
  return (
    <div className="inline-flex items-center p-1 rounded-lg bg-aerospace-950 border border-cyan-800/60 shadow-md">
      <button
        type="button"
        onClick={() => onRoleChange('passenger')}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all cursor-pointer ${
          currentRole === 'passenger'
            ? 'bg-gradient-to-r from-cyan-600 to-blue-600 text-white shadow-sm font-bold'
            : 'text-slate-400 hover:text-slate-200 hover:bg-aerospace-900/60'
        }`}
        title="Switch to Passenger Experience: Plain-English flight status and departure delay estimates"
      >
        <User size={13} className={currentRole === 'passenger' ? 'text-white' : 'text-slate-400'} />
        <span>Passenger Portal</span>
      </button>

      <button
        type="button"
        onClick={() => onRoleChange('operations')}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all cursor-pointer ${
          currentRole === 'operations'
            ? 'bg-gradient-to-r from-blue-700 to-indigo-700 text-white shadow-sm font-bold'
            : 'text-slate-400 hover:text-slate-200 hover:bg-aerospace-900/60'
        }`}
        title="Switch to Aviation Operations Console: Full airspace surveillance, ML models, and route lab"
      >
        <Compass size={13} className={currentRole === 'operations' ? 'text-white' : 'text-slate-400'} />
        <span>Operations Console</span>
      </button>
    </div>
  );
};
