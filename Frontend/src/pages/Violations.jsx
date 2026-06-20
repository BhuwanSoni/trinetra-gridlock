import React, { useState, useEffect } from 'react';
import { color, font } from '../styles/theme';
import { getViolations } from '../services/api';
import { Loader2, AlertCircle } from 'lucide-react';

const violationTypes = ['No Helmet', 'Signal Jump', 'Wrong Lane', 'No Seatbelt', 'Overspeeding',
                        'Helmet Violation', 'Red Light', 'Speed Violation'];
const statuses = ['pending', 'approved', 'rejected', 'escalated'];

const statusStyle = {
  pending:   { color: '#92400E', bg: '#FEF3C7', border: '#FDE68A' },
  approved:  { color: '#065F46', bg: '#ECFDF5', border: '#A7F3D0' },
  rejected:  { color: color.red,  bg: color.redBg, border: color.redBorder },
  escalated: { color: '#5B21B6', bg: '#EDE9FE', border: '#DDD6FE' },
};

function StatusChip({ status }) {
  const s = statusStyle[status] || statusStyle.pending;
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

const S = {
  th: {
    padding: '8px 12px', fontSize: 11, fontWeight: 600, color: color.muted,
    background: color.paperSubtle, textAlign: 'left', textTransform: 'uppercase',
    letterSpacing: '0.06em', borderBottom: `1px solid ${color.rule}`,
    whiteSpace: 'nowrap',
  },
  td: { padding: '9px 12px', fontSize: 13, borderBottom: `1px solid ${color.ruleLight}` },
};

export default function Violations() {
  const [allViolations, setAllViolations] = useState([]);
  const [loading,       setLoading]       = useState(true);
  const [error,         setError]         = useState(false);
  const [type,          setType]          = useState('all');
  const [status,        setStatus]        = useState('all');
  const [search,        setSearch]        = useState('');

  useEffect(() => {
    setLoading(true);
    getViolations()
      .then(data => {
        setAllViolations(Array.isArray(data) ? data : []);
        setError(false);
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, []);

  // Derive violation types from real data
  const dynamicTypes = [...new Set(allViolations.map(v => v.type || v.violation).filter(Boolean))];
  const typeOptions  = dynamicTypes.length > 0 ? dynamicTypes : violationTypes;

  const filtered = allViolations.filter(v => {
    const vtype   = v.type || v.violation || '';
    const vstatus = v.status || 'pending';
    const vplate  = v.plate || '';
    return (
      (type   === 'all' || vtype   === type)   &&
      (status === 'all' || vstatus === status) &&
      (search === '' || vplate.includes(search.toUpperCase()))
    );
  });

  const inputStyle = {
    padding: '6px 10px', border: `1px solid ${color.rule}`, borderRadius: 2,
    fontSize: 12.5, background: color.paperSubtle, color: color.ink,
    fontFamily: font.body, outline: 'none',
  };

  return (
    <div style={{ padding: '28px 32px', maxWidth: 1100, fontFamily: font.body }}>
      {/* Header */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 10.5, color: color.muted, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>
          Violation Records ·{' '}
          <span style={{ color: loading ? color.faint : error ? '#DC2626' : '#16A34A' }}>
            {loading ? 'loading…' : error ? 'backend unreachable' : 'live from /challans'}
          </span>
        </div>
        <h1 style={{ fontFamily: font.display, fontSize: 24, fontWeight: 700, color: color.ink, margin: 0 }}>
          Violations
        </h1>
      </div>

      {/* Error banner */}
      {!loading && error && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 10,
          padding: '12px 16px', marginBottom: 18,
          border: '1px solid #fca5a5', borderRadius: 3, background: '#fef2f2',
        }}>
          <AlertCircle size={14} style={{ color: '#dc2626', flexShrink: 0 }} />
          <span style={{ fontSize: 13, color: '#991b1b' }}>
            Backend unreachable — could not load violations from <code>GET /challans</code>. Start FastAPI to see real records.
          </span>
        </div>
      )}

      {/* Filter bar */}
      <div style={{
        display: 'flex', gap: 10, marginBottom: 18, flexWrap: 'wrap',
        padding: '12px 14px', border: `1px solid ${color.rule}`, borderRadius: 3,
        background: color.paperSubtle, alignItems: 'center',
      }}>
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search plate…"
          style={{ ...inputStyle, width: 160, fontFamily: font.mono, textTransform: 'uppercase' }}
        />
        <select value={type} onChange={e => setType(e.target.value)} style={inputStyle}>
          <option value="all">All types</option>
          {typeOptions.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
        <select value={status} onChange={e => setStatus(e.target.value)} style={inputStyle}>
          <option value="all">All statuses</option>
          {statuses.map(s => <option key={s} value={s} style={{ textTransform: 'capitalize' }}>{s}</option>)}
        </select>
        {(type !== 'all' || status !== 'all' || search !== '') && (
          <button
            onClick={() => { setType('all'); setStatus('all'); setSearch(''); }}
            style={{ ...inputStyle, color: color.red, cursor: 'pointer', marginLeft: 'auto' }}
          >
            Clear filters
          </button>
        )}
        <span style={{ marginLeft: 'auto', fontSize: 12, color: color.muted }}>
          {filtered.length} of {allViolations.length} records
        </span>
      </div>

      {/* Table */}
      <div style={{ border: `1px solid ${color.rule}`, borderRadius: 3, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              {['Case ID', 'Plate', 'Violation', 'Location', 'Camera', 'Date / Time', 'Conf.', 'Status'].map(h => (
                <th key={h} style={S.th}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={8} style={{ ...S.td, textAlign: 'center', padding: 32, color: color.muted }}>
                  <Loader2 size={14} style={{ display: 'inline', marginRight: 8, animation: 'spin 1s linear infinite' }} />
                  Loading from backend…
                </td>
              </tr>
            )}
            {!loading && filtered.length === 0 && (
              <tr>
                <td colSpan={8} style={{ ...S.td, textAlign: 'center', color: color.muted, padding: 32 }}>
                  {error
                    ? 'Backend unreachable.'
                    : allViolations.length === 0
                      ? 'No violations recorded yet — process some footage first.'
                      : 'No violations match these filters.'}
                </td>
              </tr>
            )}
            {!loading && filtered.map((v, i) => {
              const vtype = v.type || v.violation || '—';
              const ts    = v.timestamp || `${v.date || ''} ${v.time || ''}`.trim() || '—';
              return (
                <tr key={v.id || i} style={{ background: i % 2 === 0 ? color.paper : color.paperSubtle }}>
                  <td style={{ ...S.td, fontFamily: font.mono, fontSize: 11, color: color.muted }}>{v.id || '—'}</td>
                  <td style={{ ...S.td, fontFamily: font.mono, fontWeight: 700, fontSize: 12 }}>{v.plate || 'UNKNOWN'}</td>
                  <td style={{ ...S.td }}>{vtype}</td>
                  <td style={{ ...S.td, color: color.muted, fontSize: 12 }}>{v.location || '—'}</td>
                  <td style={{ ...S.td, color: color.muted, fontSize: 12 }}>{v.camera || '—'}</td>
                  <td style={{ ...S.td, color: color.muted, fontSize: 12 }}>
                    {ts.length > 19 ? ts.slice(0, 19).replace('T', ' ') : ts}
                  </td>
                  <td style={{ ...S.td, fontWeight: 600, fontFamily: font.mono }}>
                    {v.confidence != null ? `${v.confidence}%` : '—'}
                  </td>
                  <td style={S.td}><StatusChip status={v.status || 'pending'} /></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}