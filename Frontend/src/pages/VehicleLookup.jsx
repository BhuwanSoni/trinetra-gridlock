import React, { useState } from 'react';
import { mockViolations } from '../services/api';

const vehicleDB = {
  'KA14CD1234': { owner: 'Mohan Lal Sharma', vehicle: 'Honda Activa 6G', color: 'Blue', rto: 'Bangalore RTO' },
  'KA45AB5678': { owner: 'Priya Singh', vehicle: 'TVS Jupiter', color: 'Red', rto: 'Bangalore RTO' },
  'KA14EF9012': { owner: 'Rajesh Kumar', vehicle: 'Maruti Swift', color: 'White', rto: 'Bangalore RTO' },
};

const statusStyle = (s) => ({
  padding: '2px 8px', borderRadius: 3, fontSize: 12, fontWeight: 600,
  border: '1px solid #bbb', background: '#f5f5f5', color: '#111',
});

export default function VehicleLookup() {
  const [query, setQuery] = useState('');
  const [searched, setSearched] = useState(false);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);

  const handleSearch = () => {
    const plate = query.replace(/\s/g, '').toUpperCase();
    setSearched(true);
    const info = vehicleDB[plate] || null;
    setResult(info ? { ...info, plate } : null);
    const vios = mockViolations.filter(v => v.plate.replace(/\s/g, '') === plate);
    setHistory(vios);
  };

  const riskLevel = history.length >= 3 ? 'High' : history.length >= 1 ? 'Medium' : 'Low';
  const riskColor = riskLevel === 'High' ? '#c62828' : riskLevel === 'Medium' ? '#e65100' : '#2e7d32';

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', padding: '24px 24px' }}>
      <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 4 }}>Vehicle Lookup</h2>
      <p style={{ color: '#666', marginBottom: 24, fontSize: 13 }}>Search a vehicle by plate number to view its full violation history</p>

      {/* Search box */}
      <div style={{ border: '1px solid #ddd', borderRadius: 4, padding: 20, marginBottom: 24, background: '#fafafa', maxWidth: 500 }}>
        <label style={{ fontSize: 13, fontWeight: 600, display: 'block', marginBottom: 8 }}>Enter Plate Number</label>
        <div style={{ display: 'flex', gap: 10 }}>
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
            placeholder="e.g. KA14CD1234"
            style={{ flex: 1, textTransform: 'uppercase', letterSpacing: 1 }}
          />
          <button
            onClick={handleSearch}
            style={{ padding: '7px 20px', background: '#111', color: '#fff', border: 'none', borderRadius: 3, fontWeight: 600 }}
          >
            Search
          </button>
        </div>
        <p style={{ fontSize: 12, color: '#888', marginTop: 8 }}>Try: KA14CD1234 &nbsp;·&nbsp; KA45AB5678 &nbsp;·&nbsp; KA14EF9012</p>
      </div>

      {searched && !result && (
        <div style={{ border: '1px solid #ddd', padding: '20px 24px', borderRadius: 4, color: '#666', fontSize: 14 }}>
          No vehicle record found for this plate number.
        </div>
      )}

      {result && (
        <div>
          {/* Vehicle info */}
          <div style={{ border: '1px solid #ddd', borderRadius: 4, padding: 20, marginBottom: 20 }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 14 }}>Vehicle Information</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 0 }}>
              <table>
                <tbody>
                  {[
                    ['Plate Number', result.plate],
                    ['Owner Name', result.owner],
                    ['Vehicle', result.vehicle],
                    ['Colour', result.color],
                    ['Registered RTO', result.rto],
                  ].map(([k, v]) => (
                    <tr key={k}>
                      <td style={{ background: '#f5f5f5', fontWeight: 600, width: 150 }}>{k}</td>
                      <td style={{ fontFamily: k === 'Plate Number' ? 'monospace' : undefined, fontWeight: k === 'Plate Number' ? 600 : 400 }}>{v}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div style={{ paddingLeft: 24, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 8 }}>
                <div style={{ fontSize: 13, color: '#555', marginBottom: 4 }}>Risk Assessment</div>
                <div style={{ fontSize: 28, fontWeight: 700, color: riskColor }}>{riskLevel} Risk</div>
                <div style={{ fontSize: 13, color: '#666' }}>{history.length} violation(s) on record</div>
                {history.length >= 3 && (
                  <div style={{ fontSize: 12, color: '#c62828', marginTop: 4 }}>
                    ⚠ Repeat offender — recommend escalation to senior officer
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Violation history */}
          <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 12 }}>Violation History ({history.length})</h3>
          {history.length === 0 ? (
            <p style={{ color: '#888', fontSize: 13 }}>No violations on record for this vehicle.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Case ID</th>
                  <th>Violation Type</th>
                  <th>Location</th>
                  <th>Date</th>
                  <th>Time</th>
                  <th>Camera</th>
                  <th>Confidence</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {history.map(v => (
                  <tr key={v.id}>
                    <td style={{ fontFamily: 'monospace', fontSize: 12, color: '#555' }}>{v.id}</td>
                    <td>{v.type}</td>
                    <td style={{ color: '#555' }}>{v.location}</td>
                    <td style={{ color: '#555' }}>{v.date}</td>
                    <td style={{ color: '#555' }}>{v.time}</td>
                    <td style={{ color: '#555' }}>{v.camera}</td>
                    <td style={{ fontWeight: 600 }}>{v.confidence}%</td>
                    <td><span style={statusStyle(v.status)}>{v.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
