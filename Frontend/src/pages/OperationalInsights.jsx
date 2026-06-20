import React from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis } from 'recharts';
import { TrendingUp, TrendingDown, Lightbulb, AlertTriangle } from 'lucide-react';

const weeklyData = [
  { day: 'Mon', violations: 312, resolved: 289 },
  { day: 'Tue', violations: 278, resolved: 260 },
  { day: 'Wed', violations: 401, resolved: 370 },
  { day: 'Thu', violations: 334, resolved: 310 },
  { day: 'Fri', violations: 456, resolved: 420 },
  { day: 'Sat', violations: 389, resolved: 350 },
  { day: 'Sun', violations: 247, resolved: 230 },
];

const radarData = [
  { metric: 'Helmet', A: 88 },
  { metric: 'Signal', A: 72 },
  { metric: 'Speed', A: 55 },
  { metric: 'Lane', A: 65 },
  { metric: 'Seatbelt', A: 45 },
  { metric: 'Parking', A: 30 },
];

const recommendations = [
  { type: 'deploy', text: 'Deploy additional unit at MG Road Junction — violations up 18% this week', priority: 'high' },
  { type: 'review', text: '14 cases pending for over 2 hours — reassign to Officer B shift', priority: 'medium' },
  { type: 'maintenance', text: 'CAM-05 frame rate degraded — schedule field inspection before peak hours', priority: 'medium' },
  { type: 'offender', text: 'RJ14 CD 1234 flagged 3 times in 4 days — escalate to enforcement', priority: 'high' },
];

const priorityStyle = {
  high: 'border-l-red-500 bg-red-500/5',
  medium: 'border-l-amber-500 bg-amber-500/5',
  low: 'border-l-teal-500 bg-teal-500/5',
};

export default function OperationalInsights() {
  return (
    <div className="p-6 animate-fadeInUp space-y-5">
      <div>
        <h1 style={{ fontFamily: 'Space Grotesk, sans-serif' }} className="text-xl font-semibold text-white">Operational Insights</h1>
        <p className="text-sm text-slate-500 mt-0.5">Weekly trends, enforcement efficiency, and actionable recommendations</p>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        {[
          { label: 'Peak Day', value: 'Friday', sub: '456 violations', trend: 'up' },
          { label: 'Resolution Rate', value: '91.8%', sub: '+2.3% vs last week', trend: 'up' },
          { label: 'Avg Review Time', value: '11.4 min', sub: '−1.2 min vs last week', trend: 'down' },
          { label: 'Emerging Risk', value: 'Station Rd', sub: '+22% violations', trend: 'up' },
        ].map(k => (
          <div key={k.label} className="card p-4">
            <p className="text-xs text-slate-600 uppercase tracking-widest mb-2">{k.label}</p>
            <p style={{ fontFamily: 'Space Grotesk, sans-serif' }} className="text-xl font-bold text-white mb-1">{k.value}</p>
            <div className="flex items-center gap-1.5">
              {k.trend === 'up' ? <TrendingUp size={11} className="text-green-400"/> : <TrendingDown size={11} className="text-red-400"/>}
              <span className="text-xs text-slate-500">{k.sub}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
        {/* Weekly trend chart */}
        <div className="card p-5 xl:col-span-2">
          <p className="text-sm font-medium text-slate-300 mb-4">Weekly — Violations vs Resolved</p>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={weeklyData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1A2540" vertical={false}/>
              <XAxis dataKey="day" tick={{ fill: '#475569', fontSize: 11 }} axisLine={false} tickLine={false}/>
              <YAxis tick={{ fill: '#475569', fontSize: 11 }} axisLine={false} tickLine={false}/>
              <Tooltip contentStyle={{ background: '#131C2E', border: '1px solid #223055', borderRadius: 8, fontSize: 12 }}/>
              <Line type="monotone" dataKey="violations" stroke="#F59E0B" strokeWidth={2} dot={false}/>
              <Line type="monotone" dataKey="resolved" stroke="#22C55E" strokeWidth={2} dot={false} strokeDasharray="4 2"/>
            </LineChart>
          </ResponsiveContainer>
          <div className="flex gap-4 mt-3">
            <div className="flex items-center gap-1.5 text-xs text-slate-500">
              <div className="w-6 h-0.5 bg-amber-400"></div> Total Flagged
            </div>
            <div className="flex items-center gap-1.5 text-xs text-slate-500">
              <div className="w-6 h-0.5 bg-green-400" style={{ backgroundImage: 'repeating-linear-gradient(90deg, #22C55E 0,#22C55E 4px,transparent 4px,transparent 6px)' }}></div> Resolved
            </div>
          </div>
        </div>

        {/* Radar chart */}
        <div className="card p-5">
          <p className="text-sm font-medium text-slate-300 mb-4">Violation Category Spread</p>
          <ResponsiveContainer width="100%" height={200}>
            <RadarChart data={radarData}>
              <PolarGrid stroke="#1A2540"/>
              <PolarAngleAxis dataKey="metric" tick={{ fill: '#475569', fontSize: 10 }}/>
              <PolarRadiusAxis tick={false} axisLine={false}/>
              <Radar name="Violations" dataKey="A" stroke="#0EA5E9" fill="#0EA5E9" fillOpacity={0.15}/>
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Recommendations */}
      <div className="card p-5">
        <div className="flex items-center gap-2 mb-4">
          <Lightbulb size={15} className="text-amber-400"/>
          <p className="text-sm font-medium text-slate-300">System Recommendations</p>
        </div>
        <div className="space-y-2">
          {recommendations.map((r, i) => (
            <div key={i} className={`card border-l-2 px-4 py-3 ${priorityStyle[r.priority]}`}>
              <div className="flex items-start gap-3">
                <AlertTriangle size={13} className={r.priority === 'high' ? 'text-red-400 mt-0.5 flex-shrink-0' : 'text-amber-400 mt-0.5 flex-shrink-0'}/>
                <p className="text-sm text-slate-400">{r.text}</p>
                <span className={`ml-auto text-xs px-2 py-0.5 rounded-full flex-shrink-0 font-medium ${
                  r.priority === 'high' ? 'bg-red-500/10 text-red-400' : 'bg-amber-500/10 text-amber-400'
                }`}>{r.priority}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
