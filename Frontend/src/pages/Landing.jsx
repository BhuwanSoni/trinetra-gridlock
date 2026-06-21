import React from 'react';
import { color, font } from '../styles/theme';
 
const pipeline = [
  { step: '01', label: 'Traffic Frame', detail: 'CCTV / ANPR camera feed' },
  { step: '02', label: 'Multi-Model AI', detail: '9 Specialized YOLO Models' },
  { step: '03', label: 'Violation Engine', detail: 'Helmet · Phone · Seatbelt · Triple Riding' },

  { step: '04', label: 'OCR', detail: 'Plate text extraction' },
  { step: '05', label: 'Evidence Pack', detail: 'Annotated image + metadata' },
  { step: '06', label: 'Dashboard', detail: 'Review queue → fine issued' },
];
 
const dataset = [
  { label: 'Training Images', value: '100K+' },
  { label: 'AI Models', value: '9' },
  { label: 'Violation Types', value: '7' },
  { label: 'OCR Engines', value: '2' },
  { label: 'Detection Pipeline', value: 'YOLOv11' },
  { label: 'Risk Engine', value: 'XGBoost' },
];
 
const classes = ['Helmet', 'No Helmet', 'Seatbelt', 'Phone Usage', 'Triple Riding', 'Red Light', 'Illegal Parking', 'License Plate'];

const team = [
  { name: 'Bhuwan Soni', role: 'Model Configuration/ ML ops' },
  { name: 'Kanchi Soni', role: 'Model Training' },
  { name: 'Deepika Gill', role: 'Data Collection' },
  { name: 'Vaibhav Gupta', role: 'Frontend' },
];
 
const S = {
  page: { padding: '36px 40px', maxWidth: 920, margin: '0 auto', fontFamily: font.body },
  rule: { border: 'none', borderTop: `1px solid ${color.rule}`, margin: '36px 0' },
  eyebrow: { fontSize: 10.5, color: color.muted, textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 8 },
  card: { border: `1px solid ${color.rule}`, borderRadius: 3, background: color.paper },
};
 
export default function Landing({ onNavigate }) {
  return (
    <div style={S.page}>
      {/* Header */}
      <div style={{ marginBottom: 40 }}>
        <div style={{ ...S.eyebrow, color: color.red, letterSpacing: '0.14em' }}>TRINETRA</div>
        <h1 style={{
          fontFamily: font.display, fontSize: 34, fontWeight: 700,
          color: color.ink, margin: '6px 0 12px', lineHeight: 1.2,
        }}>
          Traffic Violation Detection System
        </h1>
        <p style={{ fontSize: 14, color: color.text, lineHeight: 1.6, maxWidth: 560, margin: 0 }}>
          Automated detection of traffic violations from CCTV footage — vehicle classification, 
          helmet and seatbelt compliance, licence plate OCR, and evidence generation for enforcement.
        </p>
        <div style={{ display: 'flex', gap: 10, marginTop: 20 }}>
          <button
            onClick={() => onNavigate('dashboard')}
            style={{
              padding: '8px 20px', border: `1px solid ${color.ink}`,
              background: color.ink, color: '#fff',
              borderRadius: 2, fontSize: 13, fontWeight: 600, cursor: 'pointer',
            }}
          >
            Open Dashboard
          </button>
          <button
            onClick={() => onNavigate('upload')}
            style={{
              padding: '8px 20px', border: `1px solid ${color.rule}`,
              background: color.paper, color: color.text,
              borderRadius: 2, fontSize: 13, cursor: 'pointer',
            }}
          >
            Try Detection Demo
          </button>
        </div>
      </div>
 
      <hr style={S.rule} />
 
      {/* Architecture pipeline — a real linear diagram */}
      <div style={{ marginBottom: 36 }}>
        <div style={S.eyebrow}>System Architecture</div>
        <div style={{ display: 'flex', alignItems: 'stretch', gap: 0, overflowX: 'auto' }}>
          {pipeline.map((step, i) => (
            <React.Fragment key={step.step}>
              <div style={{
                ...S.card, flex: 1, minWidth: 110, padding: '14px 14px 12px',
                display: 'flex', flexDirection: 'column', gap: 4,
              }}>
                <div style={{ fontFamily: font.mono, fontSize: 10, color: color.faint }}>{step.step}</div>
                <div style={{ fontSize: 12.5, fontWeight: 600, color: color.ink }}>{step.label}</div>
                <div style={{ fontSize: 11, color: color.muted, lineHeight: 1.4 }}>{step.detail}</div>
              </div>
              {i < pipeline.length - 1 && (
                <div style={{
                  display: 'flex', alignItems: 'center',
                  padding: '0 4px', color: color.faint, fontSize: 14,
                }}>
                  →
                </div>
              )}
            </React.Fragment>
          ))}
        </div>
        <p style={{ fontSize: 11.5, color: color.muted, marginTop: 10 }}>
          Each frame enters the pipeline at left and produces an evidence package at right — no manual review until step 6.
        </p>
      </div>
 
      <hr style={S.rule} />
 
      {/* Dataset & model numbers */}
      <div style={{ marginBottom: 36 }}>
        <div style={S.eyebrow}>Dataset & Model</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 12, marginBottom: 16 }}>
          {dataset.map(d => (
            <div key={d.label} style={{ ...S.card, padding: '14px 12px' }}>
              <div style={{ fontFamily: font.display, fontSize: 22, fontWeight: 700, color: color.ink }}>{d.value}</div>
              <div style={{ fontSize: 11, color: color.muted, marginTop: 3 }}>{d.label}</div>
            </div>
          ))}
        </div>
        <div style={{ ...S.card, padding: '14px 18px' }}>
          <div style={{ fontSize: 11.5, fontWeight: 600, color: color.muted, marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.07em' }}>
            Detection Classes
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {classes.map(c => (
              <span key={c} style={{
                fontFamily: font.mono, fontSize: 12, padding: '3px 9px',
                border: `1px solid ${color.rule}`, borderRadius: 2,
                color: color.text, background: color.paperSubtle,
              }}>
                {c}
              </span>
            ))}
          </div>
        </div>
      </div>
 
      <hr style={S.rule} />
 
      {/* Problem statement — concise */}
      <div style={{ marginBottom: 36 }}>
        <div style={S.eyebrow}>Problem Statement</div>
        <p style={{ fontSize: 14, color: color.text, lineHeight: 1.7, maxWidth: 680, margin: 0 }}>
          Bangalore's traffic enforcement relies on manual review of thousands of camera frames daily. 
          Officers cannot process this volume at speed. TRINETRA runs every frame through a detection 
          pipeline automatically — flagging violations, reading plates, and packaging evidence — so 
          officers only review confirmed cases, not raw footage.
        </p>
      </div>
 
      <hr style={S.rule} />
 
      {/* Team */}
      <div>
        <div style={S.eyebrow}>Team — Gridlock 2.0</div>
        <table style={{ width: '100%', borderCollapse: 'collapse', ...S.card }}>
          <thead>
            <tr style={{ borderBottom: `1px solid ${color.rule}`, background: color.paperSubtle }}>
              {['Name', 'Role'].map(h => (
                <th key={h} style={{
                  padding: '9px 16px', fontSize: 11, fontWeight: 600, color: color.muted,
                  textAlign: 'left', textTransform: 'uppercase', letterSpacing: '0.07em',
                }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {team.map((m, i) => (
              <tr key={m.name} style={{ borderBottom: i < team.length - 1 ? `1px solid ${color.ruleLight}` : 'none' }}>
                <td style={{ padding: '10px 16px', fontSize: 13, fontWeight: 600, color: color.ink }}>{m.name}</td>
                <td style={{ padding: '10px 16px', fontSize: 13, color: color.muted }}>{m.role}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}