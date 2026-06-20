import React, { useState, useEffect } from 'react';
import { Activity, Cpu, Eye, Clock, CheckCircle2, AlertTriangle } from 'lucide-react';
import { mockSystemMetrics } from '../services/api';

function Gauge({ value, label, color = '#F59E0B' }) {
  const r = 38;
  const circ = 2 * Math.PI * r;
  const dash = (value / 100) * circ * 0.75;
  const gap = circ - dash;

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width="100" height="80" viewBox="0 0 100 80">
        {/* Track */}
        <circle cx="50" cy="60" r={r} fill="none" stroke="#1A2540" strokeWidth="8"
          strokeDasharray={`${circ * 0.75} ${circ * 0.25}`}
          strokeDashoffset={circ * 0.125}
          strokeLinecap="round"
        />
        {/* Fill */}
        <circle cx="50" cy="60" r={r} fill="none" stroke={color} strokeWidth="8"
          strokeDasharray={`${dash} ${circ - dash}`}
          strokeDashoffset={circ * 0.125}
          strokeLinecap="round"
          style={{ transition: 'stroke-dasharray 1s ease' }}
        />
        <text x="50" y="58" textAnchor="middle" fill="white" fontSize="14" fontWeight="700" fontFamily="Space Grotesk, sans-serif">
          {value}%
        </text>
      </svg>
      <p className="text-xs text-slate-500 text-center leading-tight">{label}</p>
    </div>
  );
}

function MetricRow({ label, value, unit, icon: Icon, good }) {
  return (
    <div className="flex items-center gap-3 px-4 py-3 border-b border-white/5 last:border-0 hover:bg-white/2 transition-colors">
      <Icon size={14} className="text-slate-600 flex-shrink-0"/>
      <span className="text-sm text-slate-400 flex-1">{label}</span>
      <span style={{ fontFamily: 'Space Grotesk, sans-serif' }} className={`text-sm font-semibold ${good ? 'text-green-400' : 'text-amber-400'}`}>
        {value}{unit}
      </span>
    </div>
  );
}

export default function SystemMetrics() {
  const [metrics] = useState(mockSystemMetrics);
  const [uptime, setUptime] = useState(0);

  useEffect(() => {
    let n = 0;
    const t = setInterval(() => {
      n++;
      setUptime(n);
      if (n >= 997) clearInterval(t);
    }, 2);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="p-6 animate-fadeInUp space-y-5">
      <div>
        <h1 style={{ fontFamily: 'Space Grotesk, sans-serif' }} className="text-xl font-semibold text-white">System Metrics</h1>
        <p className="text-sm text-slate-500 mt-0.5">Model confidence, detection performance, and system uptime</p>
      </div>

      {/* Uptime hero */}
      <div className="card p-5 flex items-center gap-6">
        <div>
          <p className="text-xs text-slate-600 uppercase tracking-widest mb-1">System Uptime</p>
          <p style={{ fontFamily: 'Space Grotesk, sans-serif' }} className="text-5xl font-bold text-green-400">
            {(uptime / 10).toFixed(1)}<span className="text-2xl text-slate-600">%</span>
          </p>
        </div>
        <div className="flex-1 h-px bg-white/5"></div>
        <div className="grid grid-cols-3 gap-6">
          {[
            { label: 'Frames/Day', value: '14,820', color: 'text-teal-400' },
            { label: 'Avg Latency', value: '340ms', color: 'text-amber-400' },
            { label: 'False Positive', value: '2.8%', color: 'text-green-400' },
          ].map(m => (
            <div key={m.label} className="text-center">
              <p style={{ fontFamily: 'Space Grotesk, sans-serif' }} className={`text-xl font-bold ${m.color}`}>{m.value}</p>
              <p className="text-xs text-slate-600 mt-0.5">{m.label}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Gauges */}
      <div className="card p-6">
        <p className="text-sm font-medium text-slate-300 mb-5">Model Performance</p>
        <div className="grid grid-cols-3 xl:grid-cols-5 gap-4">
          <Gauge value={92} label="Detection Confidence" color="#F59E0B"/>
          <Gauge value={97} label="OCR Accuracy" color="#22D3EE"/>
          <Gauge value={96} label="System Health" color="#22C55E"/>
          <Gauge value={74} label="Low-Light Perf." color="#0EA5E9"/>
          <Gauge value={88} label="Plate Coverage" color="#A78BFA"/>
        </div>
      </div>

      {/* Detailed metrics table */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div className="card overflow-hidden">
          <div className="px-4 py-3 border-b border-white/5">
            <p className="text-sm font-medium text-slate-300">Detection Engine</p>
          </div>
          <MetricRow label="Model Confidence" value="92.4" unit="%" icon={Eye} good={true}/>
          <MetricRow label="Avg Detection Time" value="340" unit="ms" icon={Clock} good={true}/>
          <MetricRow label="False Positive Rate" value="2.8" unit="%" icon={AlertTriangle} good={true}/>
          <MetricRow label="Frames Processed (today)" value="14,820" unit="" icon={Activity} good={true}/>
          <MetricRow label="OCR Accuracy" value="97.1" unit="%" icon={CheckCircle2} good={true}/>
        </div>

        <div className="card overflow-hidden">
          <div className="px-4 py-3 border-b border-white/5">
            <p className="text-sm font-medium text-slate-300">Infrastructure</p>
          </div>
          <MetricRow label="CPU Usage" value="34" unit="%" icon={Cpu} good={true}/>
          <MetricRow label="GPU Utilization" value="71" unit="%" icon={Activity} good={true}/>
          <MetricRow label="Memory Usage" value="58" unit="%" icon={Activity} good={true}/>
          <MetricRow label="Disk (Evidence Store)" value="67" unit="%" icon={Activity} good={true}/>
          <MetricRow label="API Response Time" value="120" unit="ms" icon={Clock} good={true}/>
        </div>
      </div>

      {/* API connection note */}
      <div className="card px-4 py-3 border-l-2 border-l-teal-500 bg-teal-500/5 flex items-start gap-3">
        <Activity size={14} className="text-teal-400 mt-0.5 flex-shrink-0"/>
        <p className="text-sm text-slate-400">
          These metrics use mock data. Set <span className="font-mono text-teal-400">REACT_APP_API_URL</span> in your <span className="font-mono text-teal-400">.env</span> file and update <span className="font-mono text-teal-400">src/services/api.js → getSystemMetrics()</span> to connect your backend.
        </p>
      </div>
    </div>
  );
}
