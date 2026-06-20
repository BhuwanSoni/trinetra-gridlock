import React, { useState } from 'react';

const junctions = [
  { name: 'Silk Board Junction', violations: 312, lat: 12.9170, lng: 77.6229, risk: 'critical' },
  { name: 'Hebbal Flyover', violations: 247, lat: 13.0450, lng: 77.5960, risk: 'high' },
  { name: 'KR Puram Bridge', violations: 189, lat: 13.0050, lng: 77.6950, risk: 'high' },
  { name: 'Tin Factory Junction', violations: 134, lat: 12.9900, lng: 77.6700, risk: 'medium' },
  { name: 'Marathahalli Bridge', violations: 98, lat: 12.9560, lng: 77.7010, risk: 'medium' },
  { name: 'Outer Ring Road (ORR)', violations: 201, lat: 12.9300, lng: 77.6850, risk: 'high' },
  { name: 'MG Road Signal', violations: 76, lat: 12.9757, lng: 77.6094, risk: 'low' },
  { name: 'Indiranagar 100ft Rd', violations: 59, lat: 12.9784, lng: 77.6408, risk: 'low' },
  { name: 'Yeshwanthpur Junction', violations: 112, lat: 13.0230, lng: 77.5540, risk: 'medium' },
  { name: 'Electronic City', violations: 88, lat: 12.8393, lng: 77.6770, risk: 'low' },
];

const riskColors = {
  critical: { dot: '#c62828', bg: '#fdecea', border: '#ef9a9a', label: '#c62828' },
  high:     { dot: '#e65100', bg: '#fff3e0', border: '#ffcc80', label: '#e65100' },
  medium:   { dot: '#f9a825', bg: '#fffde7', border: '#fff176', label: '#8a6000' },
  low:      { dot: '#2e7d32', bg: '#e8f5e9', border: '#a5d6a7', label: '#2e7d32' },
};

// Map junctions to relative x/y positions based on rough Bangalore coordinates
function latLngToXY(lat, lng) {
  const minLat = 12.83, maxLat = 13.06;
  const minLng = 77.54, maxLng = 77.72;
  const x = ((lng - minLng) / (maxLng - minLng)) * 100;
  const y = ((maxLat - lat) / (maxLat - minLat)) * 100;
  return { x, y };
}

export default function Heatmap() {
  const [selected, setSelected] = useState(null);
  const [filter, setFilter] = useState('all');

  const filtered = filter === 'all' ? junctions : junctions.filter(j => j.risk === filter);
  const max = Math.max(...junctions.map(j => j.violations));

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', padding: '24px 24px' }}>
      <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 4 }}>Hotspot Heatmap</h2>
      <p style={{ color: '#666', marginBottom: 20, fontSize: 13 }}>Junction-wise violation density across Bangalore — click any point for details</p>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: 24 }}>

        {/* Map area */}
        <div>
          {/* Filter */}
          <div style={{ display: 'flex', gap: 8, marginBottom: 14 }}>
            {['all', 'critical', 'high', 'medium', 'low'].map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                style={{
                  padding: '4px 12px', border: '1px solid #ddd', borderRadius: 3, fontSize: 12, fontWeight: 600,
                  background: filter === f ? '#111' : '#fff', color: filter === f ? '#fff' : '#444', cursor: 'pointer',
                  textTransform: 'capitalize',
                }}
              >
                {f}
              </button>
            ))}
          </div>

          {/* Schematic map */}
          <div style={{ border: '1px solid #ddd', borderRadius: 4, position: 'relative', height: 420, background: '#fafafa', overflow: 'hidden' }}>
            {/* Grid lines to simulate road network */}
            <svg width="100%" height="100%" style={{ position: 'absolute', top: 0, left: 0 }}>
              {/* Horizontal roads */}
              {[20, 40, 55, 70, 85].map(y => (
                <line key={y} x1="0" y1={`${y}%`} x2="100%" y2={`${y}%`} stroke="#e0e0e0" strokeWidth="1.5"/>
              ))}
              {/* Vertical roads */}
              {[15, 30, 50, 68, 82].map(x => (
                <line key={x} x1={`${x}%`} y1="0" x2={`${x}%`} y2="100%" stroke="#e0e0e0" strokeWidth="1.5"/>
              ))}
              {/* ORR - diagonal */}
              <line x1="10%" y1="85%" x2="90%" y2="20%" stroke="#ddd" strokeWidth="2" strokeDasharray="6 4"/>
            </svg>

            {/* Compass label */}
            <div style={{ position: 'absolute', top: 10, left: 10, fontSize: 10, color: '#bbb' }}>N ↑</div>
            <div style={{ position: 'absolute', bottom: 10, right: 10, fontSize: 10, color: '#bbb' }}>Schematic — not to scale</div>

            {/* Junction dots */}
            {junctions.map(j => {
              const { x, y } = latLngToXY(j.lat, j.lng);
              const r = riskColors[j.risk];
              const isFiltered = filter !== 'all' && j.risk !== filter;
              if (isFiltered) return null;
              const size = 10 + (j.violations / max) * 22;
              return (
                <div
                  key={j.name}
                  onClick={() => setSelected(selected === j.name ? null : j.name)}
                  style={{
                    position: 'absolute',
                    left: `${x}%`, top: `${y}%`,
                    transform: 'translate(-50%, -50%)',
                    width: size, height: size,
                    borderRadius: '50%',
                    background: r.dot,
                    opacity: 0.85,
                    cursor: 'pointer',
                    border: selected === j.name ? '2px solid #111' : '2px solid transparent',
                    zIndex: selected === j.name ? 10 : 1,
                    boxShadow: selected === j.name ? '0 0 0 3px rgba(0,0,0,0.15)' : 'none',
                  }}
                  title={`${j.name} — ${j.violations} violations`}
                >
                  {selected === j.name && (
                    <div style={{
                      position: 'absolute', bottom: '110%', left: '50%', transform: 'translateX(-50%)',
                      background: '#111', color: '#fff', fontSize: 11, padding: '4px 8px',
                      borderRadius: 3, whiteSpace: 'nowrap', zIndex: 20,
                    }}>
                      {j.name}: {j.violations}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Legend */}
          <div style={{ display: 'flex', gap: 16, marginTop: 12, fontSize: 12, color: '#555' }}>
            {Object.entries(riskColors).map(([k, v]) => (
              <span key={k} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                <span style={{ width: 10, height: 10, borderRadius: '50%', background: v.dot, display: 'inline-block' }}></span>
                <span style={{ textTransform: 'capitalize' }}>{k}</span>
              </span>
            ))}
            <span style={{ marginLeft: 8, color: '#aaa' }}>· Dot size = violation count</span>
          </div>
        </div>

        {/* Ranked table */}
        <div>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Ranked Junctions</h3>
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Junction</th>
                <th>Count</th>
                <th>Risk</th>
              </tr>
            </thead>
            <tbody>
              {[...junctions].sort((a, b) => b.violations - a.violations).map((j, i) => (
                <tr
                  key={j.name}
                  onClick={() => setSelected(selected === j.name ? null : j.name)}
                  style={{ cursor: 'pointer', background: selected === j.name ? '#f5f5f5' : undefined }}
                >
                  <td style={{ color: '#aaa', fontSize: 12 }}>{i + 1}</td>
                  <td style={{ fontSize: 12 }}>{j.name}</td>
                  <td style={{ fontWeight: 600 }}>{j.violations}</td>
                  <td>
                    <span style={{
                      fontSize: 11, fontWeight: 600, padding: '1px 6px', borderRadius: 3,
                      background: riskColors[j.risk].bg,
                      color: riskColors[j.risk].label,
                      border: `1px solid ${riskColors[j.risk].border}`,
                      textTransform: 'capitalize',
                    }}>{j.risk}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
