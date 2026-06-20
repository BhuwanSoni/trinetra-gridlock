import React, { useState } from 'react';
import { Flame, TrendingUp, TrendingDown, MapPin, AlertTriangle } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { mockHotspots } from '../services/api';

const riskBadge = {
  critical: 'bg-red-500/15 text-red-400 border-red-500/25',
  high: 'bg-orange-500/15 text-orange-400 border-orange-500/25',
  medium: 'bg-amber-500/15 text-amber-400 border-amber-500/25',
  low: 'bg-green-500/15 text-green-400 border-green-500/25',
};

const riskBar = {
  critical: 'bg-red-500',
  high: 'bg-orange-500',
  medium: 'bg-amber-500',
  low: 'bg-green-500',
};

export default function HotspotAnalysis() {
  const [selected, setSelected] = useState(null);
  const maxViolations = Math.max(...mockHotspots.map(h => h.violations));

  return (
    <div className="p-6 animate-fadeInUp">
      <div className="mb-5">
        <h1 style={{ fontFamily: 'Space Grotesk, sans-serif' }} className="text-xl font-semibold text-white">Hotspot Analysis</h1>
        <p className="text-sm text-slate-500 mt-0.5">Junctions and roads with highest violation concentration</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
        {/* Ranked list */}
        <div className="xl:col-span-1 space-y-2">
          <p className="text-xs text-slate-600 uppercase tracking-widest px-1 mb-3">Ranked by violations</p>
          {mockHotspots.map((h, i) => (
            <div
              key={h.junction}
              onClick={() => setSelected(selected === h.junction ? null : h.junction)}
              className={`card card-glow cursor-pointer px-4 py-3.5 transition-all ${selected === h.junction ? 'border-amber-500/30 bg-amber-500/5' : ''}`}
            >
              <div className="flex items-center gap-3 mb-2">
                <span style={{ fontFamily: 'Space Grotesk, sans-serif' }} className="text-xl font-bold text-slate-700 w-6">
                  {String(i + 1).padStart(2, '0')}
                </span>
                <div className="flex-1">
                  <p className="text-sm text-slate-300 font-medium leading-tight">{h.junction}</p>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${riskBadge[h.risk]}`}>
                  {h.risk}
                </span>
              </div>

              <div className="flex items-center gap-3 pl-9">
                <div className="flex-1 h-1.5 rounded-full bg-navy-700">
                  <div
                    className={`h-full rounded-full ${riskBar[h.risk]}`}
                    style={{ width: `${(h.violations / maxViolations) * 100}%`, transition: 'width 0.6s ease' }}
                  ></div>
                </div>
                <span style={{ fontFamily: 'Space Grotesk, sans-serif' }} className="text-sm font-semibold text-slate-300 w-10 text-right">
                  {h.violations}
                </span>
                <span className={`flex items-center gap-0.5 text-xs ${h.change > 0 ? 'text-red-400' : 'text-green-400'}`}>
                  {h.change > 0 ? <TrendingUp size={11}/> : <TrendingDown size={11}/>}
                  {Math.abs(h.change)}%
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* Chart + Detail */}
        <div className="xl:col-span-2 space-y-4">
          {/* Bar chart */}
          <div className="card p-5">
            <p className="text-sm font-medium text-slate-300 mb-4">Violations by Junction</p>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={mockHotspots} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1A2540" vertical={false}/>
                <XAxis
                  dataKey="junction"
                  tick={{ fill: '#475569', fontSize: 10 }}
                  axisLine={false} tickLine={false}
                  tickFormatter={v => v.split(' ')[0]}
                />
                <YAxis tick={{ fill: '#475569', fontSize: 11 }} axisLine={false} tickLine={false}/>
                <Tooltip
                  contentStyle={{ background: '#131C2E', border: '1px solid #223055', borderRadius: 8, fontSize: 12 }}
                  labelStyle={{ color: '#94A3B8' }}
                  itemStyle={{ color: '#F59E0B' }}
                />
                <Bar dataKey="violations" fill="#F59E0B" radius={[3, 3, 0, 0]}/>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Simulated map placeholder */}
          <div className="card p-5">
            <div className="flex items-center justify-between mb-3">
              <p className="text-sm font-medium text-slate-300">Junction Map</p>
              <span className="text-xs text-slate-600">Connect backend to enable live mapping</span>
            </div>
            <div
              className="rounded-lg relative overflow-hidden"
              style={{ height: 220, background: '#0d1520', border: '1px solid #1A2540' }}
            >
              {/* Grid representing roads */}
              <div className="absolute inset-0" style={{
                backgroundImage: 'linear-gradient(rgba(34,211,238,0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(34,211,238,0.06) 1px, transparent 1px)',
                backgroundSize: '32px 32px'
              }}></div>

              {/* Hotspot pins */}
              {[
                { x: '25%', y: '35%', label: 'MG Road', risk: 'critical' },
                { x: '55%', y: '55%', label: 'Nehru Circle', risk: 'high' },
                { x: '75%', y: '25%', label: 'Airport Rd', risk: 'high' },
                { x: '40%', y: '70%', label: 'Station Rd', risk: 'medium' },
                { x: '80%', y: '65%', label: 'Vaishali', risk: 'medium' },
              ].map((pin, i) => (
                <div key={i} className="absolute flex flex-col items-center" style={{ left: pin.x, top: pin.y, transform: 'translate(-50%,-50%)' }}>
                  <div className={`w-3 h-3 rounded-full animate-pulse-slow ${riskBar[pin.risk]} shadow-lg`}
                    style={{ boxShadow: pin.risk === 'critical' ? '0 0 12px rgba(239,68,68,0.5)' : '0 0 8px rgba(245,158,11,0.4)' }}>
                  </div>
                  <div className="mt-1 text-xs px-1.5 py-0.5 rounded" style={{ background: 'rgba(11,17,32,0.9)', color: '#94a3b8', fontSize: 9, whiteSpace: 'nowrap' }}>
                    {pin.label}
                  </div>
                </div>
              ))}

              <div className="absolute bottom-3 right-3 text-xs text-slate-700">
                Schematic view · integrate Leaflet/MapBox for live map
              </div>
            </div>
          </div>

          {/* Insight cards */}
          <div className="grid grid-cols-3 gap-3">
            {[
              { label: 'Peak Hour', value: '6–7 PM', icon: AlertTriangle, color: 'text-red-400' },
              { label: 'Most Common', value: 'No Helmet', icon: Flame, color: 'text-amber-400' },
              { label: 'Rising Fast', value: 'Station Rd', icon: TrendingUp, color: 'text-orange-400' },
            ].map(item => (
              <div key={item.label} className="card p-4">
                <item.icon size={16} className={`${item.color} mb-2`}/>
                <p className="text-xs text-slate-600 mb-0.5">{item.label}</p>
                <p style={{ fontFamily: 'Space Grotesk, sans-serif' }} className={`text-sm font-semibold ${item.color}`}>{item.value}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
