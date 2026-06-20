import React from 'react';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer, Legend
} from 'recharts';

const hourly = [
  { hour: '6am', violations: 38 }, { hour: '7am', violations: 94 },
  { hour: '8am', violations: 142 }, { hour: '9am', violations: 119 },
  { hour: '10am', violations: 76 }, { hour: '11am', violations: 61 },
  { hour: '12pm', violations: 88 }, { hour: '1pm', violations: 73 },
  { hour: '2pm', violations: 65 }, { hour: '3pm', violations: 79 },
  { hour: '4pm', violations: 112 }, { hour: '5pm', violations: 148 },
  { hour: '6pm', violations: 161 }, { hour: '7pm', violations: 107 },
  { hour: '8pm', violations: 64 }, { hour: '9pm', violations: 38 },
];

const weekly = [
  { day: 'Mon', violations: 312, resolved: 290 },
  { day: 'Tue', violations: 278, resolved: 261 },
  { day: 'Wed', violations: 401, resolved: 374 },
  { day: 'Thu', violations: 334, resolved: 308 },
  { day: 'Fri', violations: 458, resolved: 421 },
  { day: 'Sat', violations: 389, resolved: 352 },
  { day: 'Sun', violations: 245, resolved: 231 },
];

const byType = [
  { name: 'No Helmet', value: 1102 },
  { name: 'Signal Jump', value: 643 },
  { name: 'Wrong Lane', value: 521 },
  { name: 'No Seatbelt', value: 389 },
  { name: 'Overspeeding', value: 192 },
];

const GREYS = ['#111', '#444', '#777', '#999', '#bbb'];

const tipStyle = { background: '#fff', border: '1px solid #ddd', borderRadius: 4, fontSize: 12, padding: '6px 10px' };

export default function Charts() {
  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', padding: '24px 24px' }}>
      <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 4 }}>Charts & Analytics</h2>
      <p style={{ color: '#666', marginBottom: 28, fontSize: 13 }}>Visual breakdown of violation patterns across Bangalore — today and this week</p>

      {/* Chart 1 - Hourly */}
      <div style={{ border: '1px solid #ddd', borderRadius: 4, padding: 20, marginBottom: 24 }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>Violations by Hour — Today</h3>
        <p style={{ fontSize: 12, color: '#888', marginBottom: 16 }}>Peak hours are typically 8–9am and 5–7pm during rush hour</p>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={hourly} margin={{ top: 0, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false}/>
            <XAxis dataKey="hour" tick={{ fill: '#888', fontSize: 11 }} axisLine={false} tickLine={false}/>
            <YAxis tick={{ fill: '#888', fontSize: 11 }} axisLine={false} tickLine={false}/>
            <Tooltip contentStyle={tipStyle}/>
            <Bar dataKey="violations" fill="#111" radius={[2, 2, 0, 0]}/>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 24 }}>
        {/* Chart 2 - Weekly */}
        <div style={{ border: '1px solid #ddd', borderRadius: 4, padding: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>Weekly — Flagged vs Resolved</h3>
          <p style={{ fontSize: 12, color: '#888', marginBottom: 16 }}>Resolution rate this week: ~92%</p>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={weekly} margin={{ top: 0, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false}/>
              <XAxis dataKey="day" tick={{ fill: '#888', fontSize: 11 }} axisLine={false} tickLine={false}/>
              <YAxis tick={{ fill: '#888', fontSize: 11 }} axisLine={false} tickLine={false}/>
              <Tooltip contentStyle={tipStyle}/>
              <Legend iconSize={10} wrapperStyle={{ fontSize: 12 }}/>
              <Line type="monotone" dataKey="violations" stroke="#111" strokeWidth={2} dot={false} name="Flagged"/>
              <Line type="monotone" dataKey="resolved" stroke="#888" strokeWidth={2} dot={false} strokeDasharray="5 3" name="Resolved"/>
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Chart 3 - By type pie */}
        <div style={{ border: '1px solid #ddd', borderRadius: 4, padding: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>By Violation Type</h3>
          <p style={{ fontSize: 12, color: '#888', marginBottom: 16 }}>No Helmet accounts for nearly 38% of all cases</p>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={byType}
                dataKey="value"
                nameKey="name"
                cx="45%"
                cy="50%"
                outerRadius={75}
                innerRadius={35}
              >
                {byType.map((_, i) => <Cell key={i} fill={GREYS[i]}/>)}
              </Pie>
              <Tooltip contentStyle={tipStyle}/>
              <Legend iconSize={10} wrapperStyle={{ fontSize: 11 }}/>
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Summary table */}
      <div style={{ border: '1px solid #ddd', borderRadius: 4, padding: 20 }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 14 }}>Summary Table — This Week</h3>
        <table>
          <thead>
            <tr>
              <th>Day</th>
              <th>Total Flagged</th>
              <th>Resolved</th>
              <th>Pending</th>
              <th>Resolution Rate</th>
            </tr>
          </thead>
          <tbody>
            {weekly.map(w => (
              <tr key={w.day}>
                <td style={{ fontWeight: 600 }}>{w.day}</td>
                <td>{w.violations}</td>
                <td>{w.resolved}</td>
                <td>{w.violations - w.resolved}</td>
                <td style={{ fontWeight: 600 }}>{((w.resolved / w.violations) * 100).toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
