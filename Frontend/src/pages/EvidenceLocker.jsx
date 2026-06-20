import React, { useState, useEffect } from 'react';
import { Archive, Download, Eye, Search, Loader2, AlertCircle, X } from 'lucide-react';
import { color, font } from '../styles/theme';

// ── Firebase ──────────────────────────────────────────────────────────────────
import { db, storage } from '../firebase';
import { collection, getDocs, query, orderBy } from 'firebase/firestore';
import { ref, getDownloadURL } from 'firebase/storage';

async function resolveStorageUrl(image_name) {
  if (!image_name) return null;
  try {
    const path = image_name.startsWith('gs://')
      ? image_name.replace(/^gs:\/\/[^/]+\//, '')
      : image_name;
    return await getDownloadURL(ref(storage, path));
  } catch {
    return null;
  }
}

async function fetchFromFirebase() {
  const snap = await getDocs(
    query(collection(db, 'challans'), orderBy('issued_at', 'desc'))
  );
  const records = await Promise.all(
    snap.docs.map(async d => {
      const data = { id: d.id, ...d.data() };
      data._imageUrl = data.image_url;
      return data;
    })
  );
  return records;
}

// ── Status styling (inline, matching your theme) ──────────────────────────────
const statusChip = {
  pending:   { color: '#92400E', bg: '#FEF3C7', border: '#FDE68A' },
  approved:  { color: '#065F46', bg: '#ECFDF5', border: '#A7F3D0' },
  rejected:  { color: '#991B1B', bg: '#FEF2F2', border: '#FCA5A5' },
  escalated: { color: '#5B21B6', bg: '#EDE9FE', border: '#DDD6FE' },
};

function StatusChip({ status }) {
  const s = statusChip[status] || statusChip.pending;
  return (
    <span style={{
      fontSize: 11, fontWeight: 600, padding: '2px 7px', borderRadius: 2,
      background: s.bg, color: s.color, border: `1px solid ${s.border}`,
      textTransform: 'capitalize', whiteSpace: 'nowrap',
    }}>
      {status || 'pending'}
    </span>
  );
}

// ── Evidence Card ─────────────────────────────────────────────────────────────
function EvidenceCard({ v, onView }) {
  const [imgError, setImgError] = useState(false);
  const imageUrl = v._imageUrl || null;

  const S = {
    card: {
      border: `1px solid ${color.rule}`,
      borderRadius: 3,
      background: color.paper,
      overflow: 'hidden',
    },
    imgBox: {
      height: 160,
      background: '#0a0f1a',
      position: 'relative',
      overflow: 'hidden',
    },
    badge: {
      position: 'absolute', fontSize: 9, padding: '2px 6px', borderRadius: 2,
      background: 'rgba(0,0,0,0.7)', fontFamily: font.mono,
    },
    body: { padding: '12px 14px' },
    meta: { fontSize: 11, color: color.muted, marginTop: 2, marginBottom: 8 },
    grid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 12px', marginBottom: 10 },
    kLabel: { fontSize: 11, color: color.muted },
    kVal:   { fontSize: 11, color: color.text, fontWeight: 500 },
    actions: { display: 'flex', gap: 8, marginTop: 4 },
    btn: {
      flex: 1, padding: '6px 0', fontSize: 12, fontWeight: 600,
      border: `1px solid ${color.rule}`, borderRadius: 2,
      background: color.paperSubtle, color: color.text,
      cursor: 'pointer', textAlign: 'center', textDecoration: 'none',
      display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4,
    },
  };

  return (
    <div style={S.card}>
      {/* Image */}
      <div style={S.imgBox}>
        {imageUrl && !imgError ? (
          <img
            src={imageUrl}
            alt={`Evidence ${v.id}`}
            style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
            onError={() => setImgError(true)}
          />
        ) : (
          <div style={{
            position: 'absolute', inset: 0,
            display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center', gap: 6,
          }}>
            <AlertCircle size={20} color={color.faint} />
            <span style={{ fontSize: 11, color: color.faint }}>No image</span>
          </div>
        )}
        <div style={{ ...S.badge, top: 8, left: 8, color: '#94a3b8' }}>
          {imageUrl && !imgError ? 'ANNOTATED' : 'NO IMAGE'}
        </div>
        <div style={{ ...S.badge, top: 8, right: 8, color: color.muted }}>
          {v.camera || 'CAM-??'}
        </div>
      </div>

      {/* Body */}
      <div style={S.body}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
          <span style={{ fontFamily: font.mono, fontWeight: 700, fontSize: 14, color: color.ink }}>
            {v.plate || 'UNKNOWN'}
          </span>
          <StatusChip status={v.status} />
        </div>

        <div style={S.meta}>
          {v.id} · {v.violation || v.type || '—'}
        </div>

        <div style={S.grid}>
          {[
            ['Confidence', v.confidence != null ? `${v.confidence}%` : '—'],
            ['Camera',     v.camera || '—'],
            ['Time',       v.timestamp ? String(v.timestamp).slice(11, 19) : (v.time || '—')],
            ['Fine',       v.fine ? `₹${Number(v.fine).toLocaleString()}` : '—'],
          ].map(([k, val]) => (
            <div key={k}>
              <span style={S.kLabel}>{k}: </span>
              <span style={S.kVal}>{val}</span>
            </div>
          ))}
        </div>

        <div style={S.actions}>
          <button onClick={() => onView(v)} style={{ ...S.btn, color: '#0D9488', borderColor: '#0D9488' }}>
            <Eye size={11} /> View
          </button>
          {imageUrl && !imgError && (
            <a href={imageUrl} download target="_blank" rel="noreferrer" style={{ ...S.btn }}>
              <Download size={11} /> Export
            </a>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Detail Modal ──────────────────────────────────────────────────────────────
function DetailModal({ v, onClose }) {
  if (!v) return null;
  const imageUrl = v._imageUrl || null;

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 50,
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24,
      background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)',
    }}>
      <div style={{
        width: '100%', maxWidth: 640, maxHeight: '90vh',
        background: color.paper, border: `1px solid ${color.rule}`,
        borderRadius: 3, overflow: 'auto', padding: 24,
      }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <span style={{ fontFamily: font.display, fontSize: 17, fontWeight: 700, color: color.ink }}>
            Evidence — {v.id}
          </span>
          <button onClick={onClose} style={{
            background: 'none', border: `1px solid ${color.rule}`, borderRadius: 2,
            padding: '4px 10px', cursor: 'pointer', color: color.muted, fontSize: 12,
            display: 'flex', alignItems: 'center', gap: 4,
          }}>
            <X size={12} /> Close
          </button>
        </div>

        {/* Full image */}
        {imageUrl && (
          <div style={{ borderRadius: 3, overflow: 'hidden', border: `1px solid ${color.rule}`, marginBottom: 16 }}>
            <img src={imageUrl} alt="Evidence" style={{ width: '100%', objectFit: 'contain', maxHeight: 320, display: 'block', background: '#0a0f1a' }} />
          </div>
        )}

        {/* Fields grid */}
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 16,
        }}>
          {[
            ['Case ID',    v.id],
            ['Plate',      v.plate || 'UNKNOWN'],
            ['Violation',  v.violation || v.type || '—'],
            ['Camera',     v.camera || '—'],
            ['Timestamp',  v.timestamp || v.time || '—'],
            ['Status',     v.status || 'pending'],
            ['Confidence', v.confidence != null ? `${v.confidence}%` : '—'],
            ['Fine',       v.fine ? `₹${Number(v.fine).toLocaleString()}` : '—'],
          ].map(([k, val]) => (
            <div key={k} style={{
              padding: '8px 10px', background: color.paperSubtle,
              border: `1px solid ${color.rule}`, borderRadius: 2,
            }}>
              <div style={{ fontSize: 10.5, color: color.muted, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 2 }}>{k}</div>
              <div style={{ fontSize: 13, color: color.ink, fontWeight: 600 }}>{String(val)}</div>
            </div>
          ))}
        </div>

        {/* Download */}
        {imageUrl && (
          <a href={imageUrl} download target="_blank" rel="noreferrer" style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
            padding: '9px 0', border: `1px solid ${color.rule}`, borderRadius: 2,
            fontSize: 13, fontWeight: 600, color: '#0D9488',
            textDecoration: 'none', background: color.paperSubtle,
          }}>
            <Download size={14} /> Download Evidence Image
          </a>
        )}
      </div>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────
export default function EvidenceLocker() {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);
  const [search,  setSearch]  = useState('');
  const [viewing, setViewing] = useState(null);

  useEffect(() => {
    setLoading(true);
    fetchFromFirebase()
      .then(data => { setRecords(data); setError(null); })
      .catch(err => {
        console.error('Firebase fetch failed:', err);
        setError('Could not load from Firebase. Check your firebase.js config and Firestore rules.');
      })
      .finally(() => setLoading(false));
  }, []);

  const filtered = records.filter(v => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      (v.plate || '').toUpperCase().includes(search.toUpperCase()) ||
      (v.violation || v.type || '').toLowerCase().includes(q) ||
      (v.id || '').toLowerCase().includes(q)
    );
  });

  const S = {
    page: { padding: '28px 32px', maxWidth: 1140, fontFamily: font.body },
    eyebrow: { fontSize: 11, color: color.muted, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 },
    searchInput: {
      padding: '7px 10px 7px 30px', border: `1px solid ${color.rule}`, borderRadius: 2,
      fontSize: 12.5, background: color.paperSubtle, color: color.ink,
      fontFamily: font.body, outline: 'none', width: 240,
    },
    emptyCard: {
      border: `1px solid ${color.rule}`, borderRadius: 3, background: color.paper,
      padding: '48px 24px', textAlign: 'center', color: color.muted, fontSize: 13,
    },
    errCard: {
      border: '1px solid #fca5a5', borderLeft: '3px solid #DC2626',
      borderRadius: 3, background: '#fef2f2',
      padding: '16px 20px', display: 'flex', gap: 10, alignItems: 'flex-start',
    },
  };

  return (
    <div style={S.page}>
      <DetailModal v={viewing} onClose={() => setViewing(null)} />

      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={S.eyebrow}>Evidence Locker</div>
        <h1 style={{ fontFamily: font.display, fontSize: 26, fontWeight: 700, color: color.ink, margin: '4px 0 6px' }}>
          Case Evidence
        </h1>
        <p style={{ fontSize: 13, color: color.muted, margin: 0 }}>
          Annotated images and case data from Firebase ·{' '}
          {loading ? 'loading…' : error ? 'error' : `${records.length} records`}
        </p>
      </div>

      {/* Search + count */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
        <div style={{ position: 'relative' }}>
          <Search size={13} style={{ position: 'absolute', left: 9, top: '50%', transform: 'translateY(-50%)', color: color.muted }} />
          <input
            style={S.searchInput}
            placeholder="Search plate, violation, or case ID…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <div style={{ fontSize: 12, color: color.muted, display: 'flex', alignItems: 'center', gap: 5, marginLeft: 'auto' }}>
          <Archive size={13} />
          {filtered.length} of {records.length} records
        </div>
      </div>

      {/* States */}
      {loading && (
        <div style={{ padding: '64px 0', textAlign: 'center', color: color.muted, fontSize: 13, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
          <Loader2 size={15} style={{ animation: 'spin 1s linear infinite' }} /> Loading evidence from Firebase…
        </div>
      )}

      {!loading && error && (
        <div style={S.errCard}>
          <AlertCircle size={15} style={{ color: '#DC2626', flexShrink: 0, marginTop: 1 }} />
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#991B1B', marginBottom: 3 }}>Firebase Error</div>
            <div style={{ fontSize: 13, color: '#991B1B' }}>{error}</div>
          </div>
        </div>
      )}

      {!loading && !error && records.length === 0 && (
        <div style={S.emptyCard}>
          <Archive size={24} style={{ color: color.faint, marginBottom: 10 }} />
          <div>No evidence records yet</div>
          <div style={{ fontSize: 12, color: color.faint, marginTop: 4 }}>
            Add documents to the <code style={{ fontFamily: font.mono }}>evidence</code> collection in Firestore to populate this page.
          </div>
        </div>
      )}

      {!loading && !error && filtered.length === 0 && records.length > 0 && (
        <div style={S.emptyCard}>No records match your search.</div>
      )}

      {!loading && !error && filtered.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 16 }}>
          {filtered.map((v, i) => (
            <EvidenceCard key={v.id || i} v={v} onView={setViewing} />
          ))}
        </div>
      )}
    </div>
  );
}