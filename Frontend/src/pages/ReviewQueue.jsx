import React, { useState, useEffect } from 'react';
import { color, font } from '../styles/theme';
import { getViolations, reviewViolation } from '../services/api';
import { Loader2, AlertCircle, Plus, Minus, X, ChevronDown, ChevronUp } from 'lucide-react';

const API_BASE = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000';

// ── Fine schedule (matches rule_engine.py) ────────────────────────────────────
const FINE_SCHEDULE = {
  'Helmet Violation':            500,
  'Triple Riding':              1000,
  'Seat Belt Violation':         500,
  'Mobile Usage While Driving': 5000,
  'Red Light Violation':        1000,
  'Stop Line / Zebra Violation':  500,
  'Illegal Parking':             500,
  'Wrong Side Driving':         5000,
  'Pedestrian Signal Violation':  500,
  'Abnormal Driving Behaviour':  2000,
};

const ALL_VIOLATION_TYPES = Object.keys(FINE_SCHEDULE);

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Parse raw violations[] from the API into { type → { count, fine_per, severity, confidence } } */
function parseViolationCounts(violations = []) {
  const map = {};
  for (const v of violations) {
    const t = v.violation_type || v.type || 'Unknown';
    if (!map[t]) {
      map[t] = {
        count:      0,
        fine_per:   v.fine_amount ?? FINE_SCHEDULE[t] ?? 0,
        severity:   v.severity   ?? 'Medium',
        confidence: v.confidence ?? 0,
      };
    }
    map[t].count += 1;
  }
  return map;
}

/** Expand officer map back to a flat violations[] array for the API */
function expandToViolations(officerMap) {
  const out = [];
  for (const [type, meta] of Object.entries(officerMap)) {
    for (let i = 0; i < meta.count; i++) {
      out.push({
        violation_type: type,
        fine_amount:    meta.fine_per,
        severity:       meta.severity,
        confidence:     meta.confidence,
      });
    }
  }
  return out;
}

function totalFine(map) {
  return Object.values(map).reduce((s, m) => s + m.count * m.fine_per, 0);
}

// ── Sub-components ────────────────────────────────────────────────────────────

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

function CaseListItem({ v, active, onClick }) {
  const violations = v.violations || [];
  const types      = [...new Set(violations.map(x => x.violation_type || x.type))];
  const label      = types[0] || v.type || v.violation || 'Unknown';
  const extra      = types.length - 1;
  return (
    <button
      onClick={onClick}
      style={{
        width: '100%', textAlign: 'left', display: 'block',
        padding: '10px 14px', border: 'none', borderBottom: `1px solid ${color.ruleLight}`,
        background: active ? color.paperSubtle : color.paper,
        borderLeft: `2px solid ${active ? color.ink : 'transparent'}`,
        cursor: 'pointer',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
        <span style={{ fontFamily: font.mono, fontWeight: 700, fontSize: 13, color: color.ink }}>
          {v.plate || 'UNKNOWN'}
        </span>
        <StatusChip status={v.status || 'pending'} />
      </div>
      <div style={{ fontSize: 12, color: color.text }}>
        {label}{extra > 0 ? ` +${extra} more` : ''}
      </div>
      <div style={{ fontSize: 11.5, color: color.muted, marginTop: 2 }}>
        {v.location || v.camera || '—'}
      </div>
    </button>
  );
}

function DataRow({ label, value, mono }) {
  return (
    <tr>
      <td style={{
        padding: '7px 12px', fontSize: 12, fontWeight: 600, color: color.muted,
        background: color.paperSubtle, width: 130, borderBottom: `1px solid ${color.ruleLight}`,
      }}>{label}</td>
      <td style={{
        padding: '7px 12px', fontSize: 13, color: color.ink,
        fontFamily: mono ? font.mono : font.body, fontWeight: mono ? 600 : 400,
        borderBottom: `1px solid ${color.ruleLight}`,
      }}>{value}</td>
    </tr>
  );
}

// ── Violation Editor ──────────────────────────────────────────────────────────

function ViolationEditor({ aiMap, officerMap, onChange }) {
  const [adding, setAdding] = useState(false);
  const [newType, setNewType] = useState(ALL_VIOLATION_TYPES[0]);

  const setCount = (type, delta) => {
    const current = officerMap[type]?.count ?? 0;
    const next    = Math.max(0, current + delta);
    if (next === 0) {
      const { [type]: _, ...rest } = officerMap;
      onChange(rest);
    } else {
      onChange({
        ...officerMap,
        [type]: { ...officerMap[type], count: next },
      });
    }
  };

  const addViolation = () => {
    if (!newType) return;
    onChange({
      ...officerMap,
      [newType]: officerMap[newType]
        ? { ...officerMap[newType], count: officerMap[newType].count + 1 }
        : { count: 1, fine_per: FINE_SCHEDULE[newType] ?? 500, severity: 'Medium', confidence: 1.0 },
    });
    setAdding(false);
  };

  const allTypes = [...new Set([...Object.keys(aiMap), ...Object.keys(officerMap)])];

  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{
        fontSize: 11, fontWeight: 700, color: color.muted,
        textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 8,
      }}>
        Detected Violations · Officer Review
      </div>

      {/* Header row */}
      <div style={{
        display: 'grid', gridTemplateColumns: '1fr 60px 90px 90px 60px',
        gap: 4, padding: '4px 8px', fontSize: 11, fontWeight: 600,
        color: color.muted, background: color.paperSubtle,
        borderBottom: `1px solid ${color.rule}`,
      }}>
        <span>Violation</span>
        <span style={{ textAlign: 'center' }}>AI</span>
        <span style={{ textAlign: 'center' }}>Officer</span>
        <span style={{ textAlign: 'right' }}>Fine/unit</span>
        <span style={{ textAlign: 'right' }}>Subtotal</span>
      </div>

      {allTypes.map(type => {
        const ai  = aiMap[type]?.count  ?? 0;
        const off = officerMap[type]?.count ?? 0;
        const fp  = officerMap[type]?.fine_per ?? aiMap[type]?.fine_per ?? FINE_SCHEDULE[type] ?? 0;
        const changed = off !== ai;
        return (
          <div key={type} style={{
            display: 'grid', gridTemplateColumns: '1fr 60px 90px 90px 60px',
            gap: 4, padding: '8px 8px',
            borderBottom: `1px solid ${color.ruleLight}`,
            background: changed ? '#fffbeb' : color.paper,
            alignItems: 'center',
          }}>
            {/* Label */}
            <div>
              <span style={{ fontSize: 12.5, color: color.ink }}>{type}</span>
              {changed && (
                <span style={{
                  marginLeft: 6, fontSize: 10, fontWeight: 700,
                  color: '#92400E', background: '#FEF3C7',
                  padding: '1px 5px', borderRadius: 2,
                }}>EDITED</span>
              )}
            </div>

            {/* AI count */}
            <span style={{
              textAlign: 'center', fontSize: 13, fontFamily: font.mono,
              color: color.muted,
            }}>{ai}</span>

            {/* Officer count with +/- */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4 }}>
              <button
                onClick={() => setCount(type, -1)}
                style={{
                  width: 22, height: 22, padding: 0, border: `1px solid ${color.rule}`,
                  borderRadius: 2, background: color.paperSubtle, cursor: 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: color.muted,
                }}
              ><Minus size={11} /></button>
              <span style={{ minWidth: 18, textAlign: 'center', fontSize: 13, fontFamily: font.mono, fontWeight: 700 }}>
                {off}
              </span>
              <button
                onClick={() => setCount(type, +1)}
                style={{
                  width: 22, height: 22, padding: 0, border: `1px solid ${color.rule}`,
                  borderRadius: 2, background: color.paperSubtle, cursor: 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: color.muted,
                }}
              ><Plus size={11} /></button>
            </div>

            {/* Fine per unit */}
            <span style={{
              textAlign: 'right', fontSize: 12, fontFamily: font.mono, color: color.muted,
            }}>₹{fp.toLocaleString()}</span>

            {/* Subtotal */}
            <span style={{
              textAlign: 'right', fontSize: 12, fontFamily: font.mono,
              fontWeight: 700, color: off > 0 ? color.ink : color.faint,
            }}>₹{(off * fp).toLocaleString()}</span>
          </div>
        );
      })}

      {/* Add violation row */}
      {adding ? (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '8px', borderBottom: `1px solid ${color.ruleLight}`,
          background: '#f0fdf4',
        }}>
          <select
            value={newType}
            onChange={e => setNewType(e.target.value)}
            style={{
              flex: 1, padding: '5px 8px', fontSize: 12.5,
              border: `1px solid ${color.rule}`, borderRadius: 2,
              background: color.paper, fontFamily: font.body,
            }}
          >
            {ALL_VIOLATION_TYPES.map(t => (
              <option key={t} value={t}>{t} (₹{(FINE_SCHEDULE[t] || 0).toLocaleString()})</option>
            ))}
          </select>
          <button
            onClick={addViolation}
            style={{
              padding: '5px 14px', fontSize: 12, fontWeight: 600,
              border: '1px solid #A7F3D0', borderRadius: 2,
              background: '#ECFDF5', color: '#065F46', cursor: 'pointer',
            }}
          >Add</button>
          <button
            onClick={() => setAdding(false)}
            style={{
              padding: '5px 10px', fontSize: 12,
              border: `1px solid ${color.rule}`, borderRadius: 2,
              background: color.paperSubtle, color: color.muted, cursor: 'pointer',
            }}
          ><X size={12} /></button>
        </div>
      ) : (
        <button
          onClick={() => setAdding(true)}
          style={{
            width: '100%', padding: '7px', fontSize: 12, fontWeight: 600,
            border: `1px dashed ${color.rule}`, borderRadius: 0,
            background: color.paperSubtle, color: color.muted,
            cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5,
          }}
        >
          <Plus size={11} /> Add Missed Violation
        </button>
      )}

      {/* Fine summary */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        padding: '10px 8px', background: color.ink, color: '#fff', marginTop: 0,
      }}>
        <span style={{ fontSize: 12, fontWeight: 600, opacity: 0.7 }}>
          OFFICER-APPROVED TOTAL
        </span>
        <span style={{ fontFamily: font.mono, fontWeight: 700, fontSize: 16 }}>
          ₹{totalFine(officerMap).toLocaleString()}
        </span>
      </div>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────

export default function ReviewQueue() {
  const [violations, setViolations] = useState([]);
  const [selected,   setSelected]   = useState(null);
  const [remarks,    setRemarks]    = useState('');
  const [msg,        setMsg]        = useState({ text: '', ok: true });
  const [loading,    setLoading]    = useState(true);
  const [error,      setError]      = useState(false);
  const [saving,     setSaving]     = useState(false);

  // officer edit state: record_id → officerMap
  const [edits, setEdits] = useState({});

  useEffect(() => {
    setLoading(true);
    getViolations()
      .then(v => {
        const list = Array.isArray(v) ? v : [];
        setViolations(list);
        setSelected(list[0]?.id ?? null);
        setError(false);
        // seed editor from AI detections
        const initial = {};
        for (const item of list) {
          initial[item.id] = parseViolationCounts(item.violations || []);
        }
        setEdits(initial);
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, []);

  const pending = violations.filter(v => (v.status || 'pending') === 'pending');
  const sel     = violations.find(v => v.id === selected);

  // AI-detected map and officer map for selected record
  const aiMap      = sel ? parseViolationCounts(sel.violations || []) : {};
  const officerMap = (selected && edits[selected]) ? edits[selected] : aiMap;

  const setOfficerMap = (newMap) => {
    setEdits(prev => ({ ...prev, [selected]: newMap }));
  };

  const flash = (text, ok = true) => {
    setMsg({ text, ok });
    setTimeout(() => setMsg({ text: '', ok: true }), 4000);
  };

  const handle = async (action) => {
    if (!selected || saving) return;
    setSaving(true);

    const officerViolations = expandToViolations(officerMap);
    const officerTotal      = totalFine(officerMap);
    const aiViolations      = sel.violations || [];

    // 1. Send review status
    const res = await reviewViolation(selected, action, remarks);
    // 2. Send officer violation corrections
    try {
      await fetch(`${API_BASE}/challans/${selected}/violations`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          officer_violations: officerViolations,
          officer_total_fine: officerTotal,
          officer_remark:     remarks,
          ai_violations:      aiViolations,
        }),
      });
    } catch (_) {
      // Non-fatal: corrections stored locally if endpoint not yet wired
    }

    setViolations(prev => prev.map(v =>
      v.id === selected ? { ...v, status: action, fine: officerTotal } : v
    ));

    const persisted = res?.persisted !== false;
    flash(
      persisted
        ? `${selected} marked "${action}". Fine: ₹${officerTotal.toLocaleString()}.`
        : `${selected} marked "${action}" locally. Fine: ₹${officerTotal.toLocaleString()} (wire PUT /challans/${selected}/violations to persist).`,
      true,
    );
    setRemarks('');
    setSaving(false);
  };

  const btnBase = {
    flex: 1, padding: '9px 0', border: `1px solid ${color.rule}`,
    borderRadius: 2, fontSize: 13, fontWeight: 600, cursor: saving ? 'not-allowed' : 'pointer',
    fontFamily: font.body, opacity: saving ? 0.6 : 1,
  };

  return (
    <div style={{ display: 'flex', height: '100vh', fontFamily: font.body, overflow: 'hidden' }}>

      {/* ── Left: case list ── */}
      <div style={{
        width: 270, minWidth: 270, borderRight: `1px solid ${color.rule}`,
        display: 'flex', flexDirection: 'column', background: color.paper,
      }}>
        <div style={{ padding: '16px 14px', borderBottom: `1px solid ${color.rule}` }}>
          <div style={{ fontSize: 11, color: color.muted, textTransform: 'uppercase', letterSpacing: '0.07em' }}>
            Review Queue
          </div>
          <div style={{ fontFamily: font.display, fontSize: 20, fontWeight: 700, color: color.ink, marginTop: 2 }}>
            {loading ? '—' : `${pending.length} pending`}
          </div>
          <div style={{ fontSize: 11, color: error ? '#DC2626' : loading ? color.faint : '#16A34A', marginTop: 2 }}>
            {loading ? 'loading…' : error ? 'backend unreachable' : 'live from /challans'}
          </div>
        </div>

        <div style={{ flex: 1, overflowY: 'auto' }}>
          {loading && (
            <div style={{ padding: 24, textAlign: 'center', color: color.faint, fontSize: 13 }}>
              <Loader2 size={14} style={{ display: 'inline', marginRight: 6 }} /> Loading…
            </div>
          )}
          {!loading && error && (
            <div style={{ padding: 16 }}>
              <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start', padding: '10px 12px', border: '1px solid #fca5a5', borderRadius: 3, background: '#fef2f2' }}>
                <AlertCircle size={13} style={{ color: '#dc2626', flexShrink: 0, marginTop: 1 }} />
                <span style={{ fontSize: 12, color: '#991b1b' }}>Backend unreachable — start FastAPI to load cases.</span>
              </div>
            </div>
          )}
          {!loading && !error && violations.length === 0 && (
            <div style={{ padding: '28px 14px', textAlign: 'center', fontSize: 13, color: color.faint }}>
              No violations in queue yet.
            </div>
          )}
          {!loading && violations.map(v => (
            <CaseListItem
              key={v.id} v={v}
              active={selected === v.id}
              onClick={() => { setSelected(v.id); setRemarks(''); }}
            />
          ))}
        </div>
      </div>

      {/* ── Right: case detail ── */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '28px 32px', background: color.paperSubtle }}>

        {/* Flash message */}
        {msg.text && (
          <div style={{
            padding: '10px 14px', marginBottom: 16, fontSize: 13, borderRadius: 2,
            border: `1px solid ${msg.ok ? '#A7F3D0' : '#fca5a5'}`,
            background: msg.ok ? '#ECFDF5' : '#fef2f2',
            color: msg.ok ? '#065F46' : '#991b1b',
          }}>
            {msg.text}
          </div>
        )}

        {(loading || error || !sel) ? (
          <div style={{ color: color.muted, fontSize: 14, paddingTop: 60 }}>
            {loading ? 'Loading cases…' : error ? 'Backend unreachable.' : 'Select a case to review.'}
          </div>
        ) : (
          <div>
            {/* Title */}
            <div style={{ marginBottom: 20 }}>
              <div style={{ fontSize: 10.5, color: color.muted, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>
                {sel.id}
              </div>
              <h2 style={{ fontFamily: font.display, fontSize: 22, fontWeight: 700, color: color.ink, margin: 0 }}>
                {sel.type || sel.violation}
              </h2>
            </div>

            {/* Case metadata */}
            <table style={{
              width: '100%', borderCollapse: 'collapse',
              border: `1px solid ${color.rule}`, borderRadius: 3, overflow: 'hidden', marginBottom: 16,
            }}>
              <tbody>
                <DataRow label="Plate Number"  value={sel.plate || 'UNKNOWN'} mono />
                <DataRow label="Location"      value={sel.location || sel.camera || '—'} />
                <DataRow label="Date / Time"   value={sel.timestamp || `${sel.date || ''} ${sel.time || ''}`.trim() || '—'} />
                <DataRow label="Camera"        value={sel.camera || '—'} mono />
                <DataRow label="AI Confidence" value={sel.confidence != null ? `${sel.confidence}%` : '—'} mono />
                <DataRow label="Status"        value={<StatusChip status={sel.status || 'pending'} />} />
                <DataRow label="AI Fine"       value={sel.fine ? `₹${Number(sel.fine).toLocaleString()}` : '—'} mono />
              </tbody>
            </table>

            {/* ── Violation Editor ── */}
            <div style={{
              background: color.paper, border: `1px solid ${color.rule}`,
              borderRadius: 3, overflow: 'hidden', marginBottom: 16,
            }}>
              <ViolationEditor
                aiMap={aiMap}
                officerMap={officerMap}
                onChange={setOfficerMap}
              />
            </div>

            {/* Remarks */}
            <div style={{ marginBottom: 14 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: color.muted, display: 'block', marginBottom: 6 }}>
                Officer Remarks
              </label>
              <textarea
                rows={3}
                value={remarks}
                onChange={e => setRemarks(e.target.value)}
                placeholder="Add remarks for this case, e.g. 'Only 1 rider was using mobile. Other detections were false positives.'"
                style={{
                  width: '100%', padding: '8px 10px', fontSize: 13,
                  border: `1px solid ${color.rule}`, borderRadius: 2,
                  background: color.paper, color: color.ink, fontFamily: font.body,
                  resize: 'vertical', outline: 'none', boxSizing: 'border-box',
                }}
              />
            </div>

            {/* Action buttons */}
            <div style={{ display: 'flex', gap: 10 }}>
              <button onClick={() => handle('approved')} style={{
                ...btnBase, background: '#ECFDF5', color: '#065F46', border: '1px solid #A7F3D0',
              }}>
                {saving ? 'Saving…' : `Approve — ₹${totalFine(officerMap).toLocaleString()}`}
              </button>
              <button onClick={() => handle('rejected')} style={{
                ...btnBase, background: color.redBg, color: color.red, border: `1px solid ${color.redBorder}`,
              }}>Reject</button>
              <button onClick={() => handle('escalated')} style={{
                ...btnBase, background: '#EDE9FE', color: '#5B21B6', border: '1px solid #DDD6FE',
              }}>Escalate</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}