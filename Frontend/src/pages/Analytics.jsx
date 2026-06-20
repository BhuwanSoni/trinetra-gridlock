import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, LineChart, Line } from 'recharts';
import { ShieldAlert, IndianRupee, Camera, Repeat, Flame, Loader2 } from 'lucide-react';
import { fetchReport } from '../services/api';

export default function Analytics() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [live, setLive] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetchReport()
      .then((data) => {
        if (data) {
          setReport(data);
          setLive(true);
        }
      })
      .finally(() => setLoading(false));
  }, []);

  const byCamera = report?.violations_by_camera
    ? Object.entries(report.violations_by_camera)
        .sort((a, b) => b[1] - a[1])
        .map(([camera, count]) => ({ camera, count }))
    : [];

  const repeatOffenders = report?.repeat_offenders
    ? Object.entries(report.repeat_offenders)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10)
        .map(([plate, count]) => ({ plate, count }))
    : [];

  const dailyTrend = report?.daily_trend_7d
    ? Object.entries(report.daily_trend_7d).map(([date, flagged]) => ({ date, flagged }))
    : [];

  const metricCards = [
    { label: 'Total Violations', value: report?.total_violations, icon: ShieldAlert, color: 'text-amber-400' },
    { label: 'Total Fines (₹)', value: report?.total_fines_inr, icon: IndianRupee, color: 'text-teal-400', currency: true },
    { label: 'Active Cameras', value: report?.violations_by_camera ? Object.keys(report.violations_by_camera).length : null, icon: Camera, color: 'text-sky-400' },
    { label: 'Repeat Offenders', value: report?.repeat_offenders ? Object.values(report.repeat_offenders).filter(c => c >= 3).length : null, icon: Repeat, color: 'text-purple-400' },
    { label: 'Top Violation', value: report?.top_violation, icon: Flame, color: 'text-red-400', text: true },
  ];

  return (
    <div className="p-6 animate-fadeInUp space-y-5">
      <div>
        <h1 style={{ fontFamily: 'Space Grotesk, sans-serif' }} className="text-xl font-semibold text-white">Analytics</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Enforcement analytics aggregated from saved evidence
          {loading ? ' · loading…' : live ? ' · live from /report' : ' · backend unreachable, no data to show'}
        </p>
      </div>

      {/* Metric cards — sourced from GET /report */}
      <div className="grid grid-cols-2 xl:grid-cols-5 gap-4">
        {metricCards.map(m => (
          <div key={m.label} className="card p-4">
            <m.icon size={15} className={`${m.color} mb-2`} />
            <p className="text-xs text-slate-600 uppercase tracking-widest mb-1">{m.label}</p>
            <p style={{ fontFamily: 'Space Grotesk, sans-serif' }} className={`${m.text ? 'text-base' : 'text-2xl'} font-bold ${m.color} truncate`}>
              {m.value == null ? '—' : m.currency ? `₹${Number(m.value).toLocaleString()}` : m.text ? m.value : Number(m.value).toLocaleString()}
            </p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        {/* Violations by camera */}
        <div className="card p-5">
          <p className="text-sm font-medium text-slate-300 mb-1">Violations by Camera</p>
          <p className="text-xs text-slate-600 mb-4">Flagged incidents per camera, all saved evidence</p>
          {byCamera.length === 0 ? (
            <EmptyChart loading={loading} />
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={byCamera} margin={{ top: 0, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1A2540" vertical={false} />
                <XAxis dataKey="camera" tick={{ fill: '#475569', fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#475569', fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
                <Tooltip contentStyle={{ background: '#131C2E', border: '1px solid #223055', borderRadius: 8, fontSize: 12 }} />
                <Bar dataKey="count" fill="#F59E0B" radius={[3, 3, 0, 0]} name="Violations" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* 7-day trend */}
        <div className="card p-5">
          <p className="text-sm font-medium text-slate-300 mb-1">7-Day Flagged Trend</p>
          <p className="text-xs text-slate-600 mb-4">Daily flagged-incident count from saved evidence</p>
          {dailyTrend.length === 0 ? (
            <EmptyChart loading={loading} />
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={dailyTrend} margin={{ top: 0, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1A2540" vertical={false} />
                <XAxis dataKey="date" tick={{ fill: '#475569', fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#475569', fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
                <Tooltip contentStyle={{ background: '#131C2E', border: '1px solid #223055', borderRadius: 8, fontSize: 12 }} />
                <Line type="monotone" dataKey="flagged" stroke="#22C55E" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Repeat offenders table */}
      <div className="card overflow-hidden">
        <div className="px-5 py-3.5 border-b border-white/5">
          <p className="text-sm font-medium text-slate-300">Repeat Offenders</p>
          <p className="text-xs text-slate-600 mt-0.5">Plates with the most flagged incidents across all saved evidence</p>
        </div>
        <table className="w-full">
          <thead>
            <tr className="border-b border-white/5">
              {['Plate', 'Flagged Incidents'].map(h => (
                <th key={h} className="px-4 py-2.5 text-left text-xs text-slate-600 uppercase tracking-widest font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={2} className="px-4 py-8 text-center text-sm text-slate-500">
                <Loader2 size={14} className="inline animate-spin mr-2" /> Loading from backend…
              </td></tr>
            ) : repeatOffenders.length === 0 ? (
              <tr><td colSpan={2} className="px-4 py-8 text-center text-sm text-slate-500">No repeat offenders in saved evidence yet.</td></tr>
            ) : repeatOffenders.map(r => (
              <tr key={r.plate} className="border-b border-white/5 last:border-0 hover:bg-white/2 transition-colors">
                <td className="px-4 py-3 text-sm text-slate-300 font-medium font-mono">{r.plate}</td>
                <td className="px-4 py-3 text-sm text-amber-400 font-semibold">{r.count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card px-4 py-3 border-l-2 border-l-teal-500 bg-teal-500/5 flex items-start gap-3">
        <ShieldAlert size={14} className="text-teal-400 mt-0.5 flex-shrink-0" />
        <p className="text-sm text-slate-400">
          This page now pulls entirely from <span className="font-mono text-teal-400">GET /report</span> (<span className="font-mono text-teal-400">generate_summary_report()</span>) —
          no mock numbers. The previous version showed model-evaluation metrics (precision, recall, mAP@50) that don't have a backend source:
          those are training-time numbers from your YOLO eval run, not something <span className="font-mono text-teal-400">analytics.py</span> computes from saved evidence.
          If you want them on this page, share the eval output (e.g. a <span className="font-mono text-teal-400">results.json</span>/<span className="font-mono text-teal-400">metrics.csv</span> from training) or add an endpoint that serves it, and I'll wire it in for real.
        </p>
      </div>
    </div>
  );
}

function EmptyChart({ loading }) {
  return (
    <div className="h-[220px] flex items-center justify-center text-sm text-slate-500">
      {loading ? (<><Loader2 size={14} className="inline animate-spin mr-2" /> Loading…</>) : 'No data yet — process some footage to populate this chart.'}
    </div>
  );
}