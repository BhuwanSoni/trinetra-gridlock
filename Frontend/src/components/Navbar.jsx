import React from 'react';

const pages = [
  { id: 'landing', label: 'Home' },
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'live', label: 'Live Cameras' },
  { id: 'violations', label: 'Violations' },
  { id: 'review', label: 'Review Queue' },
  { id: 'heatmap', label: 'Heatmap' },
  { id: 'charts', label: 'Charts' },
  { id: 'alerts', label: 'Alert Panel' },
  { id: 'cameras', label: 'Camera Status' },
  { id: 'vehicle', label: 'Vehicle Lookup' },
];

export default function Navbar({ active, onNavigate }) {
  return (
    <div>
      {/* Top strip */}
      <div style={{ background: '#1a1a1a', color: '#fff', padding: '7px 24px', fontSize: 12 }}>
        <div style={{ maxWidth: 1100, margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>Traffic Enforcement Management System — Bangalore Traffic Police</span>
          <span style={{ color: '#aaa' }}>
            Officer: Arjun Kumar &nbsp;|&nbsp; {new Date().toLocaleDateString('en-IN', { dateStyle: 'medium' })}
          </span>
        </div>
      </div>

      {/* Header */}
      <div style={{ background: '#fff', borderBottom: '2px solid #111', padding: '12px 24px' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto', display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{ width: 38, height: 38, background: '#111', borderRadius: 4, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
            <span style={{ color: '#fff', fontSize: 17, fontWeight: 700 }}>T</span>
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 17, letterSpacing: '-0.3px' }}>TRINETRA</div>
            <div style={{ fontSize: 11, color: '#666', marginTop: 1 }}>Traffic Intelligence System · Bangalore · Gridlock 2.0</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <div style={{ background: '#f5f5f5', borderBottom: '1px solid #ddd', overflowX: 'auto' }}>
        <div style={{ display: 'flex', minWidth: 'max-content', maxWidth: 1100, margin: '0 auto' }}>
          {pages.map(p => (
            <button
              key={p.id}
              onClick={() => onNavigate(p.id)}
              style={{
                padding: '9px 16px',
                background: active === p.id ? '#111' : 'transparent',
                color: active === p.id ? '#fff' : '#444',
                border: 'none',
                borderRight: '1px solid #ddd',
                fontWeight: active === p.id ? 600 : 400,
                fontSize: 13,
                cursor: 'pointer',
                whiteSpace: 'nowrap',
              }}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
