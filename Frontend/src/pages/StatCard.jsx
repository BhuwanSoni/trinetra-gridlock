import React from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';

export default function StatCard({ label, value, sub, trend, trendUp, icon: Icon, accent = 'amber' }) {
  const accentMap = {
    amber: 'text-amber-400',
    teal: 'text-teal-400',
    danger: 'text-red-400',
    success: 'text-green-400',
  };
  return (
    <div className="card card-glow p-5 animate-fadeInUp">
      <div className="flex items-start justify-between mb-3">
        <span className="text-xs text-slate-500 uppercase tracking-widest font-medium">{label}</span>
        {Icon && <Icon size={16} className={`${accentMap[accent]} opacity-70`} />}
      </div>
      <div style={{ fontFamily: 'Space Grotesk, sans-serif' }} className={`text-3xl font-bold ${accentMap[accent]} leading-none mb-1`}>
        {value}
      </div>
      <div className="flex items-center gap-1.5 mt-2">
        {trend !== undefined && (
          trendUp
            ? <TrendingUp size={12} className="text-green-400" />
            : <TrendingDown size={12} className="text-red-400" />
        )}
        <span className="text-xs text-slate-500">{sub}</span>
      </div>
    </div>
  );
}
