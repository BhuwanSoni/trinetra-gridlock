import React from 'react';
import {
  LayoutDashboard, Camera, ClipboardCheck, Archive,
  Car, Flame, Activity, BarChart3, Shield, ChevronRight
} from 'lucide-react';

const navItems = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'live', label: 'Live Monitoring', icon: Camera },
  { id: 'review', label: 'Review Queue', icon: ClipboardCheck, badge: 128 },
  { id: 'evidence', label: 'Evidence Locker', icon: Archive },
  { id: 'vehicle', label: 'Vehicle Intel', icon: Car },
  { id: 'hotspots', label: 'Hotspot Analysis', icon: Flame },
  { id: 'camerahealth', label: 'Camera Health', icon: Shield },
  { id: 'insights', label: 'Operational Insights', icon: BarChart3 },
  { id: 'system', label: 'System Metrics', icon: Activity },
];

export default function Sidebar({ active, onNavigate }) {
  return (
    <aside
      style={{ width: 230, minWidth: 230 }}
      className="h-screen flex flex-col bg-navy-800 border-r border-white/5 sticky top-0 z-30"
    >
      {/* Logo */}
      <div className="px-5 py-5 border-b border-white/5">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-amber-500 flex items-center justify-center flex-shrink-0">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <circle cx="8" cy="8" r="5" stroke="#0B1120" strokeWidth="2"/>
              <circle cx="8" cy="8" r="2" fill="#0B1120"/>
              <line x1="8" y1="1" x2="8" y2="3" stroke="#0B1120" strokeWidth="1.5" strokeLinecap="round"/>
              <line x1="8" y1="13" x2="8" y2="15" stroke="#0B1120" strokeWidth="1.5" strokeLinecap="round"/>
              <line x1="1" y1="8" x2="3" y2="8" stroke="#0B1120" strokeWidth="1.5" strokeLinecap="round"/>
              <line x1="13" y1="8" x2="15" y2="8" stroke="#0B1120" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
          </div>
          <div>
            <div style={{ fontFamily: 'Space Grotesk, sans-serif' }} className="text-white font-semibold text-sm leading-tight">TRINETRA</div>
            <div className="text-xs text-slate-500 leading-tight">Traffic Intelligence OS</div>
          </div>
        </div>
      </div>

      {/* Live status */}
      <div className="px-5 py-3 border-b border-white/5">
        <div className="flex items-center gap-2">
          <span className="status-dot bg-success animate-blink"></span>
          <span className="text-xs text-slate-400">34 cameras live</span>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-3 px-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = active === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg mb-0.5 text-left transition-all duration-150 group ${
                isActive
                  ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-white/5 border border-transparent'
              }`}
            >
              <Icon size={16} className={isActive ? 'text-amber-400' : 'text-slate-500 group-hover:text-slate-300'} />
              <span className="text-sm font-medium flex-1">{item.label}</span>
              {item.badge && (
                <span className="text-xs bg-amber-500 text-black font-semibold px-1.5 py-0.5 rounded-full leading-none">
                  {item.badge}
                </span>
              )}
              {isActive && <ChevronRight size={12} className="text-amber-500" />}
            </button>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-white/5">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-full bg-teal-600 flex items-center justify-center text-xs font-semibold text-white">
            AK
          </div>
          <div>
            <div className="text-xs text-slate-300 font-medium">Arjun Kumar</div>
            <div className="text-xs text-slate-600">Traffic Officer</div>
          </div>
        </div>
      </div>
    </aside>
  );
}
