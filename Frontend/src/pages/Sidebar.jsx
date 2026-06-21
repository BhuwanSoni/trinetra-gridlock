import React from 'react';
import {
  LayoutDashboard, UploadCloud, ListChecks, ClipboardCheck,
  BarChart3, FileText, Archive,
} from 'lucide-react';
import { color, font } from '../styles/theme';
 
const navItems = [
  { id: 'dashboard',      label: 'Dashboard',        icon: LayoutDashboard },
  { id: 'upload',         label: 'Upload Analysis',   icon: UploadCloud },
  { id: 'violations',     label: 'Violations',        icon: ListChecks },
  { id: 'review',         label: 'Review Queue',      icon: ClipboardCheck, badge: 41 },
  { id: 'analytics',      label: 'Analytics',         icon: BarChart3 },
  { id: 'reports',        label: 'Reports',           icon: FileText },
  { id: 'evidence', label: 'Evidence Locker', icon: Archive },
];
 
export default function Sidebar({ active, onNavigate }) {
  return (
    <aside style={{
      width: 210, minWidth: 210, height: '100vh', position: 'sticky', top: 0,
      background: color.paper, borderRight: `1px solid ${color.rule}`,
      display: 'flex', flexDirection: 'column', fontFamily: font.body,
      zIndex: 10,
    }}>
      {/* Wordmark block */}
      <div style={{ padding: '18px 16px 14px', borderBottom: `1px solid ${color.rule}` }}>
        <div style={{
          fontFamily: font.display, fontSize: 17, fontWeight: 700,
          color: color.ink, letterSpacing: '0.04em',
        }}>
          TRINETRA
        </div>
        <div style={{
          fontFamily: font.body, fontSize: 10.5, color: color.muted,
          letterSpacing: '0.06em', textTransform: 'uppercase', marginTop: 3,
          lineHeight: 1.4,
        }}>
          Traffic Enforcement · Bengaluru
        </div>
      </div>
 
      {/* System status */}
      <div style={{
        padding: '8px 16px', borderBottom: `1px solid ${color.rule}`,
        display: 'flex', alignItems: 'center', gap: 6,
      }}>
        <span style={{
          width: 6, height: 6, borderRadius: '50%',
          background: color.muted, display: 'inline-block', flexShrink: 0,
        }} />
        <span style={{ fontSize: 11, color: color.muted, fontFamily: font.body }}>
          Pipeline connected
        </span>
      </div>
 
      {/* Nav */}
      <nav style={{ flex: 1, overflowY: 'auto', padding: '8px 6px' }}>
        {navItems.map(item => {
          const Icon = item.icon;
          const isActive = active === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              style={{
                width: '100%', display: 'flex', alignItems: 'center', gap: 9,
                padding: '7px 10px', marginBottom: 1, border: 'none',
                borderRadius: 2,
                borderLeft: `2px solid ${isActive ? color.ink : 'transparent'}`,
                background: isActive ? color.paperSubtle : 'transparent',
                cursor: 'pointer', textAlign: 'left',
                transition: 'background 0.1s',
              }}
            >
              <Icon
                size={13}
                color={isActive ? color.ink : color.muted}
                strokeWidth={isActive ? 2 : 1.6}
              />
              <span style={{
                fontSize: 12.5, fontFamily: font.body,
                fontWeight: isActive ? 600 : 400,
                color: isActive ? color.ink : color.text,
                flex: 1,
              }}>
                {item.label}
              </span>
              {item.badge != null && (
                <span style={{
                  fontFamily: font.mono, fontSize: 10, color: color.muted,
                  border: `1px solid ${color.rule}`, borderRadius: 2,
                  padding: '1px 5px',
                }}>
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>
 
      {/* Hackathon badge */}
      <div style={{
        padding: '10px 16px', borderTop: `1px solid ${color.rule}`,
      }}>
        <div style={{ fontSize: 11.5, fontWeight: 600, color: color.ink, fontFamily: font.body }}>
          Gridlock 2.0
        </div>
        <div style={{ fontSize: 10.5, color: color.muted, marginTop: 1 }}>
          Bangalore Traffic Police
        </div>
      </div>
    </aside>
  );
}