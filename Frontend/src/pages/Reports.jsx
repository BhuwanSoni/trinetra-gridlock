import React, { useState, useEffect } from 'react';
import { FileText, Calendar, FileSpreadsheet, Printer, Loader2 } from 'lucide-react';
import { fetchReport, getViolations, exportViolationsCSV } from '../services/api';

export default function Reports() {
  const [range, setRange] = useState('daily');
  const [dailySummary, setDailySummary] = useState([]);
  const [violations, setViolations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [live, setLive] = useState(false);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetchReport().then((report) => {
        if (!report?.daily_trend_7d) return;
        // report.daily_trend_7d only carries flagged counts, not resolved/pending —
        // those fields don't exist in generate_summary_report() yet.
        const summary = Object.entries(report.daily_trend_7d).map(([date, flagged]) => ({
          date, flagged, resolved: null, pending: null,
        }));
        setDailySummary(summary);
        setLive(true);
      }),
      getViolations().then(setViolations),
    ]).finally(() => setLoading(false));
  }, []);

  const totals = dailySummary.reduce((acc, d) => ({
    flagged: acc.flagged + (d.flagged ?? 0),
    resolved: acc.resolved + (d.resolved ?? 0),
    pending: acc.pending + (d.pending ?? 0),
  }), { flagged: 0, resolved: 0, pending: 0 });

  const handleExportCSV = () => {
    const csv = exportViolationsCSV(violations);
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `violations-report-${range}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleGeneratePDF = () => {
    // Real backend: POST /reports/pdf and stream the file back.
    // For the prototype, trigger the browser's print-to-PDF dialog.
    window.print();
  };

  return (
    <div className="p-6 animate-fadeInUp space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 style={{ fontFamily: 'Space Grotesk, sans-serif' }} className="text-xl font-semibold text-white">Reports</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Export violation data and summary statistics for enforcement records
            {loading ? ' · loading…' : live ? ' · live from /report' : ' · backend unreachable, no data to show'}
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={handleExportCSV} disabled={!violations.length} className="flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold text-teal-400 border border-teal-500/20 hover:bg-teal-500/10 transition-colors disabled:opacity-40 disabled:cursor-not-allowed">
            <FileSpreadsheet size={13} /> Export CSV
          </button>
          <button onClick={handleGeneratePDF} className="flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold bg-amber-500 text-black hover:bg-amber-400 transition-colors">
            <Printer size={13} /> Generate PDF
          </button>
        </div>
      </div>

      {/* Range toggle */}
      <div className="flex items-center gap-2">
        {['daily', 'weekly', 'monthly'].map(r => (
          <button
            key={r}
            onClick={() => setRange(r)}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold capitalize transition-colors ${
              range === r ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' : 'text-slate-500 border border-white/10 hover:border-white/20'
            }`}
          >
            {r} summary
          </button>
        ))}
      </div>

      {/* Totals */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Flagged', value: totals.flagged, color: 'text-amber-400' },
          { label: 'Resolved', value: totals.resolved, color: 'text-green-400' },
          { label: 'Pending', value: totals.pending, color: 'text-red-400' },
        ].map(s => (
          <div key={s.label} className="card p-4">
            <p className="text-xs text-slate-600 uppercase tracking-widest mb-1">{s.label} (last 7 days)</p>
            <p style={{ fontFamily: 'Space Grotesk, sans-serif' }} className={`text-2xl font-bold ${s.color}`}>{s.value.toLocaleString()}</p>
          </div>
        ))}
      </div>

      {/* Daily summary table */}
      <div className="card overflow-hidden">
        <div className="flex items-center gap-2 px-5 py-3.5 border-b border-white/5">
          <Calendar size={14} className="text-slate-500" />
          <p className="text-sm font-medium text-slate-300">Daily Summary</p>
        </div>
        <table className="w-full">
          <thead>
            <tr className="border-b border-white/5">
              {['Date', 'Flagged', 'Resolved', 'Pending', 'Resolution Rate'].map(h => (
                <th key={h} className="px-4 py-2.5 text-left text-xs text-slate-600 uppercase tracking-widest font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-sm text-slate-500">
                <Loader2 size={14} className="inline animate-spin mr-2" /> Loading from backend…
              </td></tr>
            ) : dailySummary.length === 0 ? (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-sm text-slate-500">
                No data yet — process some footage so /report has a daily_trend_7d to show.
              </td></tr>
            ) : dailySummary.map(d => (
              <tr key={d.date} className="border-b border-white/5 last:border-0 hover:bg-white/2 transition-colors">
                <td className="px-4 py-3 text-sm text-slate-300 font-medium">{d.date}</td>
                <td className="px-4 py-3 text-sm text-slate-400">{d.flagged}</td>
                <td className="px-4 py-3 text-sm text-slate-400">{d.resolved ?? '—'}</td>
                <td className="px-4 py-3 text-sm text-slate-400">{d.pending ?? '—'}</td>
                <td className="px-4 py-3 text-sm text-green-400 font-semibold">
                  {d.resolved != null && d.flagged ? `${((d.resolved / d.flagged) * 100).toFixed(1)}%` : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card px-4 py-3 border-l-2 border-l-teal-500 bg-teal-500/5 flex items-start gap-3">
        <FileText size={14} className="text-teal-400 mt-0.5 flex-shrink-0" />
        <p className="text-sm text-slate-400">
          CSV export now pulls from <span className="font-mono text-teal-400">GET /challans</span> via <span className="font-mono text-teal-400">getViolations()</span>.
          Resolved/Pending columns are blank because <span className="font-mono text-teal-400">generate_summary_report()</span> doesn't break <span className="font-mono text-teal-400">daily_trend_7d</span> down by review status yet — add that to <span className="font-mono text-teal-400">analytics.py</span> to fill them in.
          <span className="font-mono text-teal-400"> Generate PDF</span> still opens the browser print dialog — wire it to a real <span className="font-mono text-teal-400">/reports/pdf</span> endpoint once you build one.
        </p>
      </div>
    </div>
  );
}