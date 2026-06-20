import React, { useState } from 'react';
import { Search, AlertTriangle, Shield, Car, Clock, Loader2 } from 'lucide-react';
import { lookupVehicle } from '../services/api';

const riskColors = {
  high: { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/20', dot: 'bg-red-500' },
  medium: { bg: 'bg-amber-500/10', text: 'text-amber-400', border: 'border-amber-500/20', dot: 'bg-amber-500' },
  low: { bg: 'bg-green-500/10', text: 'text-green-400', border: 'border-green-500/20', dot: 'bg-green-500' },
};

export default function VehicleIntelligence() {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState(null);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    const plate = query.trim();
    if (!plate) return;
    setLoading(true);
    setSearched(true);
    const data = await lookupVehicle(plate);
    setResult(data);
    setLoading(false);
  };

  const risk = result ? riskColors[result.riskLevel] : null;

  return (
    <div className="p-6 animate-fadeInUp">
      <div className="mb-6">
        <h1 style={{ fontFamily: 'Space Grotesk, sans-serif' }} className="text-xl font-semibold text-white">Vehicle Intelligence</h1>
        <p className="text-sm text-slate-500 mt-0.5">Full violation history and risk profile by plate number — pulled from GET /search/plate</p>
      </div>

      {/* Search */}
      <div className="card p-5 mb-5">
        <p className="text-xs text-slate-500 mb-3 uppercase tracking-widest">Plate Lookup</p>
        <div className="flex gap-3">
          <input
            className="flex-1 px-4 py-2.5 text-sm bg-navy-900/60 border border-white/10 rounded-lg text-slate-300 placeholder-slate-600 focus:outline-none focus:border-amber-500/40 font-mono uppercase"
            placeholder="e.g. RJ14 CD 1234"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
          />
          <button
            onClick={handleSearch}
            disabled={loading}
            className="px-5 py-2.5 rounded-lg bg-amber-500 text-black text-sm font-semibold hover:bg-amber-400 disabled:opacity-50 transition-colors flex items-center gap-2"
          >
            {loading ? <Loader2 size={14} className="animate-spin"/> : <Search size={14}/>} Search
          </button>
        </div>
        <p className="text-xs text-slate-700 mt-2">Searches violation records only — HMATES has no RTO/Vahan integration for owner name or vehicle model.</p>
      </div>

      {searched && !loading && !result && (
        <div className="card p-8 flex flex-col items-center gap-3 text-center">
          <Car size={28} className="text-slate-700"/>
          <p className="text-sm text-slate-500">No record found for this plate</p>
          <p className="text-xs text-slate-700">The vehicle may not have any registered violations, or the backend is unreachable</p>
        </div>
      )}

      {result && (
        <div className="space-y-4 animate-fadeInUp">
          {/* Profile header */}
          <div className="card p-5">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-navy-700 flex items-center justify-center">
                  <Car size={22} className="text-slate-400"/>
                </div>
                <div>
                  <p style={{ fontFamily: 'Space Grotesk, sans-serif' }} className="text-xl font-bold text-white font-mono">{result.plate}</p>
                  <p className="text-sm text-slate-400 mt-0.5">{result.vehicle}</p>
                  <p className="text-xs text-slate-600 mt-0.5">{result.owner}</p>
                </div>
              </div>
              <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border ${risk.bg} ${risk.border}`}>
                <span className={`status-dot ${risk.dot}`}></span>
                <span className={`text-xs font-semibold uppercase ${risk.text}`}>{result.riskLevel} risk</span>
              </div>
            </div>

            <div className="grid grid-cols-4 gap-3 mt-5">
              {[
                { label: 'Total Violations', value: result.totalViolations, accent: 'text-red-400' },
                { label: 'Total Fines', value: `₹${result.finesPending.toLocaleString()}`, accent: 'text-amber-400' },
                { label: 'Last Seen', value: result.lastSeen || '—', accent: 'text-teal-400' },
                { label: 'Risk Score', value: result.riskScore != null ? `${result.riskScore}/100` : '—', accent: 'text-red-400' },
              ].map(item => (
                <div key={item.label} className="bg-navy-900/60 rounded-lg p-3">
                  <p className="text-xs text-slate-600 mb-1">{item.label}</p>
                  <p style={{ fontFamily: 'Space Grotesk, sans-serif' }} className={`text-lg font-bold ${item.accent}`}>{item.value}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Violation history */}
          <div className="card p-5">
            <p className="text-sm font-medium text-slate-300 mb-4">Violation History</p>
            <div className="space-y-2">
              {result.history.length === 0 && (
                <p className="text-sm text-slate-600">No individual violation records returned.</p>
              )}
              {result.history.map((h, i) => (
                <div key={i} className="flex items-center gap-4 px-3 py-2.5 rounded-lg hover:bg-white/3 border border-transparent hover:border-white/5 transition-all">
                  <div className="w-1 self-stretch rounded-full flex-shrink-0" style={{ background: h.status === 'approved' ? '#22C55E' : h.status === 'rejected' ? '#EF4444' : '#F59E0B' }}></div>
                  <div className="flex-1">
                    <p className="text-sm text-slate-300 font-medium">{h.type}</p>
                    <p className="text-xs text-slate-600">{h.location} · {h.date}</p>
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    h.status === 'approved' ? 'bg-green-500/10 text-green-400' :
                    h.status === 'rejected' ? 'bg-red-500/10 text-red-400' :
                    'bg-amber-500/10 text-amber-400'
                  }`}>{h.status}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}