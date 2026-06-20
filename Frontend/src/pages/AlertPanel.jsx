import React, { useState, useEffect, useRef } from 'react';
import { Loader2, AlertCircle, RefreshCw } from 'lucide-react';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const POLL_INTERVAL = 5000; // ms

async function fetchLatestChallans() {
  const r = await fetch(`${API_BASE}/challans`);
  if (!r.ok) throw new Error('not ok');
  const data = await r.json();
  // accept array or { challans: [...] }
  const list = Array.isArray(data) ? data : (data.challans || []);
  // sort newest first by timestamp
  return list.sort((a, b) => {
    const ta = a.timestamp || a.time || '';
    const tb = b.timestamp || b.time || '';
    return tb.localeCompare(ta);
  });
}

export default function AlertPanel() {
  const [alerts,  setAlerts]  = useState([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(false);
  const [paused,  setPaused]  = useState(false);
  const [filter,  setFilter]  = useState('all');
  const [newIds,  setNewIds]  = useState(new Set());

  const pausedRef   = useRef(false);
  const prevIdsRef  = useRef(new Set());
  const violationTypes = [...new Set(alerts.map(a => a.type || a.violation).filter(Boolean))];

  useEffect(() => { pausedRef.current = paused; }, [paused]);

  const poll = async (isManual = false) => {
    if (pausedRef.current && !isManual) return;
    try {
      const data = await fetchLatestChallans();
      const incomingIds = new Set(data.map(a => a.id));
      const fresh = new Set([...incomingIds].filter(id => !prevIdsRef.current.has(id)));

      if (fresh.size > 0 || isManual) {
        setAlerts(data.slice(0, 50));
        setNewIds(fresh);
        prevIdsRef.current = incomingIds;
        setError(false);
        setTimeout(() => setNewIds(new Set()), 2500);
      }
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    poll(true); // initial load
    const t = setInterval(() => poll(), POLL_INTERVAL);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filtered = filter === 'all'
    ? alerts
    : alerts.filter(a => (a.type || a.violation) === filter);

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', padding: '24px 24px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 4 }}>
        <h2 style={{ fontSize: 18, fontWeight: 700 }}>Real-Time Alert Panel</h2>
        {!error && (
          <span style={{ background: '#c62828', color: '#fff', fontSize: 11, fontWeight: 700, padding: '2px 8px', borderRadius: 10 }}>
            LIVE
          </span>
        )}
        {error && (
          <span style={{ background: '#888', color: '#fff', fontSize: 11, fontWeight: 700, padding: '2px 8px', borderRadius: 10 }}>
            OFFLINE
          </span>
        )}
      </div>
      <p style={{ color: '#666', marginBottom: 20, fontSize: 13 }}>
        Live challans from backend · polling every {POLL_INTERVAL / 1000}s
        {error && ' · backend unreachable'}
      </p>

      {/* Controls */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 16, flexWrap: 'wrap', alignItems: 'center' }}>
        <select
          value={filter}
          onChange={e => setFilter(e.target.value)}
          style={{ fontSize: 13 }}
        >
          <option value="all">All Types</option>
          {violationTypes.map(t => <option key={t} value={t}>{t}</option>)}
        </select>

        <button
          onClick={() => setPaused(p => !p)}
          style={{
            padding: '6px 14px', border: '1px solid #ddd', borderRadius: 3, fontSize: 13, fontWeight: 600,
            background: paused ? '#111' : '#fff', color: paused ? '#fff' : '#333', cursor: 'pointer',
          }}
        >
          {paused ? '▶  Resume' : '⏸  Pause'}
        </button>

        <button
          onClick={() => poll(true)}
          style={{ padding: '6px 14px', border: '1px solid #ddd', borderRadius: 3, fontSize: 13, background: '#fff', color: '#333', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}
        >
          <RefreshCw size={12} /> Refresh
        </button>

        <span style={{ marginLeft: 'auto', fontSize: 13, color: '#888' }}>
          {filtered.length} alert(s) shown
        </span>
      </div>

      {/* States */}
      {loading && (
        <div style={{ padding: 32, textAlign: 'center', color: '#aaa', fontSize: 13, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
          <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} /> Loading from backend…
        </div>
      )}

      {!loading && error && (
        <div style={{ padding: '20px 24px', border: '1px solid #fca5a5', borderRadius: 4, background: '#fef2f2', display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
          <AlertCircle size={16} style={{ color: '#dc2626' }} />
          <span style={{ fontSize: 13, color: '#991b1b' }}>
            Cannot reach <code style={{ background: '#fee2e2', padding: '1px 4px', borderRadius: 2 }}>{API_BASE}/challans</code>.
            Start FastAPI and add a <code style={{ background: '#fee2e2', padding: '1px 4px', borderRadius: 2 }}>GET /challans</code> endpoint.
          </span>
        </div>
      )}

      {/* Alert feed */}
      {!loading && (
        <div style={{ border: '1px solid #ddd', borderRadius: 4, overflow: 'hidden' }}>
          {/* Header row */}
          <div style={{ display: 'grid', gridTemplateColumns: '140px 1fr 140px 90px 90px 80px 70px', background: '#f5f5f5', borderBottom: '1px solid #ddd' }}>
            {['Timestamp', 'Plate · Location', 'Violation', 'Camera', 'Confidence', 'Status', ''].map((h, i) => (
              <div key={i} style={{ padding: '8px 12px', fontSize: 12, fontWeight: 600, color: '#555' }}>{h}</div>
            ))}
          </div>

          {filtered.length === 0 && (
            <div style={{ padding: '28px', textAlign: 'center', color: '#aaa', fontSize: 13 }}>
              {error ? 'Backend unreachable — no alerts to show.' : 'No alerts yet — process some footage to populate this feed.'}
            </div>
          )}

          {filtered.map((a, idx) => {
            const isNew = newIds.has(a.id);
            const ts    = a.timestamp || a.time || '—';
            const plate = a.plate || 'UNKNOWN';
            const loc   = a.location || a.camera || '—';
            const type  = a.type || a.violation || '—';
            const cam   = a.camera || '—';
            const conf  = a.confidence != null ? `${a.confidence}%` : '—';
            const stat  = a.status || 'pending';

            return (
              <div
                key={a.id || idx}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '140px 1fr 140px 90px 90px 80px 70px',
                  borderBottom: '1px solid #f0f0f0',
                  background: isNew ? '#fffbf0' : '#fff',
                  transition: 'background 0.5s',
                }}
              >
                <div style={{ padding: '9px 12px', fontSize: 11, color: '#888', fontFamily: 'monospace' }}>
                  {ts.length > 19 ? ts.slice(0, 19).replace('T', ' ') : ts}
                </div>
                <div style={{ padding: '9px 12px' }}>
                  <span style={{ fontWeight: 600, fontSize: 13, fontFamily: 'monospace' }}>{plate}</span>
                  <span style={{ fontSize: 12, color: '#777' }}> · {loc}</span>
                </div>
                <div style={{ padding: '9px 12px', fontSize: 13 }}>{type}</div>
                <div style={{ padding: '9px 12px', fontSize: 12, color: '#666' }}>{cam}</div>
                <div style={{ padding: '9px 12px', fontSize: 13, fontWeight: 600 }}>{conf}</div>
                <div style={{ padding: '9px 12px' }}>
                  <span style={{
                    fontSize: 11, fontWeight: 600, padding: '2px 6px', borderRadius: 3,
                    background: stat === 'approved' ? '#ECFDF5' : stat === 'rejected' ? '#FEF2F2' : '#fff8e1',
                    color:      stat === 'approved' ? '#065F46' : stat === 'rejected' ? '#991b1b' : '#e65100',
                    border:     stat === 'approved' ? '1px solid #A7F3D0' : stat === 'rejected' ? '1px solid #fca5a5' : '1px solid #ffcc80',
                    textTransform: 'capitalize',
                  }}>
                    {stat}
                  </span>
                </div>
                <div style={{ padding: '9px 12px' }}>
                  {isNew && (
                    <span style={{ fontSize: 10, fontWeight: 700, background: '#c62828', color: '#fff', padding: '2px 6px', borderRadius: 3 }}>
                      NEW
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <p style={{ marginTop: 14, fontSize: 12, color: '#aaa' }}>
        Showing {filtered.length} alert(s) from real challan records.{' '}
        {paused ? 'Feed is paused.' : `Auto-refreshes every ${POLL_INTERVAL / 1000}s.`}
      </p>
    </div>
  );
}