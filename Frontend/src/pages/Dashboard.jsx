import React, { useState, useEffect } from 'react';
import { color, font } from '../styles/theme';
import { getStats, getViolations, getHotspots } from '../services/api';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const S = {
  page: { padding: '28px 32px', maxWidth: 1140, fontFamily: font.body },
  eyebrow: { fontSize: 11, color: color.muted, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 },
  rule: { border: 'none', borderTop: `1px solid ${color.rule}`, margin: '24px 0' },
  card: { border: `1px solid ${color.rule}`, borderRadius: 3, background: color.paper, overflow: 'hidden' },
  th: {
    padding: '8px 14px', fontSize: 11, fontWeight: 600, color: color.muted,
    background: color.paperSubtle, textAlign: 'left', textTransform: 'uppercase',
    letterSpacing: '0.06em', borderBottom: `1px solid ${color.rule}`,
  },
  td: { padding: '9px 14px', fontSize: 13, borderBottom: `1px solid ${color.ruleLight}` },
};

const statusLabel = {
  pending:   { color: '#92400E', bg: '#FEF3C7', border: '#FDE68A' },
  approved:  { color: '#065F46', bg: '#ECFDF5', border: '#A7F3D0' },
  rejected:  { color: color.red,  bg: color.redBg,  border: color.redBorder },
  escalated: { color: '#5B21B6', bg: '#EDE9FE', border: '#DDD6FE' },
};

function StatusChip({ status }) {
  const s = statusLabel[status] || statusLabel.pending;
  return (
    <span style={{
      fontSize: 11, fontWeight: 600, padding: '2px 7px', borderRadius: 2,
      background: s.bg, color: s.color, border: `1px solid ${s.border}`,
      textTransform: 'capitalize',
    }}>
      {status}
    </span>
  );
}

// Pipeline diagram shown on dashboard
const pipeline = [
  { step: '01', label: 'CCTV Frame',      detail: 'Live / uploaded feed' },
  { step: '02', label: 'YOLO11 Detect',   detail: '9 object classes' },
  { step: '03', label: 'Rule Engine',     detail: 'Violation classification' },
  { step: '04', label: 'DeepSORT Track',  detail: 'Vehicle tracking' },
  { step: '05', label: 'PaddleOCR',       detail: 'Plate text extraction' },
  { step: '06', label: 'Challan Gen',     detail: 'Evidence + fine issued' },
];

// Empty state placeholder for metric number
function Dash() {
  return <span style={{ color: color.faint }}>—</span>;
}

export default function Dashboard({ onNavigate }) {
  const [stats,      setStats]      = useState(null);
  const [violations, setViolations] = useState([]);
  const [hotspots,   setHotspots]   = useState([]);
  const [live,       setLive]       = useState(false);
  const [loading,    setLoading]    = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([getStats(), getViolations(), getHotspots()])
      .then(([s, v, h]) => {
        if (cancelled) return;
        setStats(s);
        setViolations(v || []);
        setHotspots(h || []);
        setLive(true);
      })
      .catch(() => {
        // leave nulls — show disconnected state
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  const recent      = violations.slice(0, 8);
  const topHotspots = [...hotspots].sort((a, b) => b.violations - a.violations).slice(0, 6);

  const primaryMetrics = [
    {
      label: 'Frames Processed',
      value: stats ? stats.totalImagesProcessed?.toLocaleString() : null,
      sub: 'analysed today',
    },
    {
      label: 'Violations Detected',
      value: stats ? stats.totalViolations?.toLocaleString() : null,
      sub: stats ? `${stats.pendingReview ?? '—'} pending review` : 'pending review',
      red: true,
    },
    {
      label: 'OCR / Detection',
      value: stats ? `${stats.ocrAccuracy ?? '—'}% / ${stats.detectionAccuracy ?? '—'}%` : null,
      sub: 'plate read · violation confidence',
    },
  ];

  return (
    <div style={S.page}>

      {/* ── Page header ── */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ ...S.eyebrow, display: 'flex', alignItems: 'center', gap: 8 }}>
          <span>TRINETRA · Enforcement Overview</span>
          <span style={{ color: loading ? color.faint : live ? '#16A34A' : '#DC2626' }}>
            {loading ? '· connecting…' : live ? '· live backend' : '· backend unreachable'}
          </span>
        </div>
        <h1 style={{ fontFamily: font.display, fontSize: 26, fontWeight: 700, color: color.ink, margin: 0 }}>
          Today's Summary
        </h1>
        <p style={{ fontSize: 13, color: color.muted, marginTop: 4 }}>
          Automated detection · Jaipur traffic network ·{' '}
          {new Date().toLocaleDateString('en-IN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
        </p>
      </div>

      {/* ── Primary stats ── */}
      <div style={{ ...S.card, padding: '22px 28px', marginBottom: 24 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 0 }}>
          {primaryMetrics.map((item, i) => (
            <div key={item.label} style={{
              padding: '8px 0',
              borderLeft: i > 0 ? `1px solid ${color.rule}` : 'none',
              paddingLeft: i > 0 ? 28 : 0,
            }}>
              <div style={{ fontSize: 11, color: color.muted, textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 6 }}>
                {item.label}
              </div>
              <div style={{
                fontFamily: font.display, fontSize: 32, fontWeight: 700,
                color: item.red ? color.red : color.ink, lineHeight: 1.1,
              }}>
                {item.value ?? <Dash />}
              </div>
              <div style={{ fontSize: 12, color: color.muted, marginTop: 4 }}>{item.sub}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Pipeline diagram ── */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ ...S.eyebrow }}>Detection Pipeline</div>
        <div style={{ display: 'flex', alignItems: 'stretch', gap: 0, overflowX: 'auto' }}>
          {pipeline.map((step, i) => (
            <React.Fragment key={step.step}>
              <div style={{
                ...S.card, flex: 1, minWidth: 110, padding: '12px 12px 10px',
                display: 'flex', flexDirection: 'column', gap: 4,
              }}>
                <div style={{ fontFamily: font.mono, fontSize: 10, color: color.faint }}>{step.step}</div>
                <div style={{ fontSize: 12, fontWeight: 600, color: color.ink }}>{step.label}</div>
                <div style={{ fontSize: 11, color: color.muted }}>{step.detail}</div>
              </div>
              {i < pipeline.length - 1 && (
                <div style={{ display: 'flex', alignItems: 'center', padding: '0 3px', color: color.faint, fontSize: 14 }}>
                  →
                </div>
              )}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* ── Two-column: violations + hotspots ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: 20 }}>

        {/* Recent violations */}
        <div style={S.card}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 14px', borderBottom: `1px solid ${color.rule}` }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: color.ink }}>Recent Violations</span>
            <button
              onClick={() => onNavigate?.('violations')}
              style={{ fontSize: 12, color: color.muted, background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline' }}
            >
              View all
            </button>
          </div>
          {!live && !loading ? (
            <div style={{ padding: '28px 14px', textAlign: 'center', fontSize: 13, color: color.faint }}>
              Backend unreachable — start FastAPI to see live violations
            </div>
          ) : recent.length === 0 && !loading ? (
            <div style={{ padding: '28px 14px', textAlign: 'center', fontSize: 13, color: color.faint }}>
              No violations recorded yet
            </div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  {['Plate', 'Violation', 'Location', 'Status'].map(h => (
                    <th key={h} style={S.th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {recent.map((v, i) => (
                  <tr key={v.id} style={{ background: i % 2 === 0 ? color.paper : color.paperSubtle }}>
                    <td style={{ ...S.td, fontFamily: font.mono, fontWeight: 600, fontSize: 12 }}>{v.plate}</td>
                    <td style={{ ...S.td, color: color.text }}>{v.type || v.violation}</td>
                    <td style={{ ...S.td, color: color.muted, fontSize: 12 }}>{v.location || v.camera || '—'}</td>
                    <td style={S.td}><StatusChip status={v.status || 'pending'} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Top hotspots */}
        <div style={S.card}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 14px', borderBottom: `1px solid ${color.rule}` }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: color.ink }}>Top Hotspot Junctions</span>
            <button
              onClick={() => onNavigate?.('hotspots')}
              style={{ fontSize: 12, color: color.muted, background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline' }}
            >
              View map
            </button>
          </div>
          {topHotspots.length === 0 ? (
            <div style={{ padding: '28px 14px', textAlign: 'center', fontSize: 13, color: color.faint }}>
              {live ? 'No hotspot data yet' : 'Backend unreachable'}
            </div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  {['#', 'Junction', 'Today'].map(h => (
                    <th key={h} style={S.th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {topHotspots.map((h, i) => (
                  <tr key={h.junction || i} style={{ background: i % 2 === 0 ? color.paper : color.paperSubtle }}>
                    <td style={{ ...S.td, color: color.faint, fontSize: 12, width: 32 }}>{i + 1}</td>
                    <td style={{ ...S.td, color: color.text }}>{h.junction}</td>
                    <td style={{ ...S.td, fontWeight: 700, fontFamily: font.mono, fontSize: 13, color: color.ink }}>
                      {h.violations}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* ── Secondary quick stats ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginTop: 20 }}>
        {[
          { label: 'High Risk Cases',  value: stats?.highRiskCases,  note: 'repeat offenders' },
          { label: 'Pending Review',   value: stats?.pendingReview,   note: 'awaiting officer' },
          { label: 'Resolved Today',   value: stats?.resolvedToday,   note: 'fines issued' },
        ].map(item => (
          <div key={item.label} style={{ ...S.card, padding: '14px 18px' }}>
            <div style={{ fontSize: 11, color: color.muted, textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 4 }}>
              {item.label}
            </div>
            <div style={{ fontFamily: font.display, fontSize: 24, fontWeight: 700, color: color.ink }}>
              {item.value != null ? item.value : <Dash />}
            </div>
            <div style={{ fontSize: 11.5, color: color.faint, marginTop: 2 }}>{item.note}</div>
          </div>
        ))}
      </div>

      {/* ── Tech stack footnote ── */}
      <div style={{
        marginTop: 20, padding: '12px 16px',
        border: `1px solid ${color.rule}`, borderRadius: 3,
        background: color.paperSubtle,
        fontSize: 12, color: color.muted,
        display: 'flex', gap: 16, flexWrap: 'wrap',
      }}>
        {['YOLO11 · 9-class detector', 'DeepSORT tracking', 'PaddleOCR + EasyOCR fallback',
          'XGBoost risk scoring', 'SHA-256 evidence hashing', 'FastAPI backend'].map(tag => (
          <span key={tag} style={{
            fontFamily: font.mono, fontSize: 11,
            padding: '2px 8px', border: `1px solid ${color.rule}`, borderRadius: 2,
            background: color.paper, color: color.text,
          }}>
            {tag}
          </span>
        ))}
      </div>
    </div>
  );
}