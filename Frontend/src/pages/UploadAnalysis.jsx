import React, { useState, useRef } from 'react';
import {
  UploadCloud, Image as ImageIcon, Loader2, Car, AlertTriangle,
  ScanLine, Download, XCircle, RotateCcw
} from 'lucide-react';
import { detectViolations } from '../services/api';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const severityColor = (conf) =>
  conf >= 90 ? 'text-green-400' : conf >= 75 ? 'text-amber-400' : 'text-red-400';

function Dropzone({ onFile, previewUrl }) {
  const inputRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);

  const handleFiles = (files) => {
    const file = files?.[0];
    if (file && file.type.startsWith('image/')) onFile(file);
  };

  return (
    <div
      onClick={() => inputRef.current?.click()}
      onDragOver={e => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={e => { e.preventDefault(); setDragOver(false); handleFiles(e.dataTransfer.files); }}
      className={`card cursor-pointer rounded-xl flex flex-col items-center justify-center text-center transition-all duration-150 ${
        dragOver ? 'border-amber-500/50 bg-amber-500/5' : 'border-white/10'
      }`}
      style={{ height: 280, borderStyle: 'dashed', borderWidth: 1.5, overflow: 'hidden', position: 'relative' }}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={e => handleFiles(e.target.files)}
      />
      {previewUrl ? (
        <img src={previewUrl} alt="Upload preview" className="absolute inset-0 w-full h-full object-cover" />
      ) : (
        <>
          <UploadCloud size={28} className="text-amber-500 mb-3" />
          <p className="text-sm text-slate-300 font-medium mb-1">
            Drop a traffic image here, or click to browse
          </p>
          <p className="text-xs text-slate-600">JPG, PNG · single frame from a CCTV / ANPR camera</p>
        </>
      )}
    </div>
  );
}

export default function UploadAnalysis() {
  const [file,       setFile]       = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [status,     setStatus]     = useState('idle'); // idle | analyzing | done | error
  const [result,     setResult]     = useState(null);

  const handleFile = (f) => {
    setFile(f);
    setResult(null);
    setStatus('idle');
    const reader = new FileReader();
    reader.onload = () => setPreviewUrl(reader.result);
    reader.readAsDataURL(f);
  };

  const runDetection = async () => {
    if (!file) return;
    setStatus('analyzing');
    try {
      const res = await detectViolations(file);
      setResult(res);
      setStatus('done');
    } catch {
      setStatus('error');
    }
  };

  const reset = () => {
    setFile(null);
    setPreviewUrl(null);
    setResult(null);
    setStatus('idle');
  };

  // Resolve the annotated image URL from backend response
  const annotatedUrl = result?.annotated_image
    ? result.annotated_image.startsWith('http')
      ? result.annotated_image
      : `${API_BASE}${result.annotated_image.startsWith('/') ? '' : '/'}${result.annotated_image}`
    : null;

  const downloadEvidence = () => {
    if (!result) return;
    const payload = {
      imageId:        result.imageId || result.id,
      processedAt:    result.processedAt || result.timestamp,
      plate:          result.ocr?.plateText || result.plate,
      ocrConfidence:  result.ocr?.confidence,
      vehicles:       result.vehicles || [],
      violations:     result.violations || [],
      annotated_image: result.annotated_image,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = `${payload.imageId || 'evidence'}-package.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="p-6 animate-fadeInUp">
      <div className="mb-5">
        <h1 style={{ fontFamily: 'Space Grotesk, sans-serif' }} className="text-xl font-semibold text-white">
          Upload Analysis
        </h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Run a traffic image through the YOLO11 pipeline — vehicles, violations, plate OCR
        </p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">

        {/* Left: upload + annotated result */}
        <div className="card p-5">
          <p className="text-xs text-slate-600 uppercase tracking-widest mb-3">Image Input</p>

          {/* Show backend annotated image when done; otherwise show dropzone/preview */}
          {status === 'done' && annotatedUrl ? (
            <div className="relative rounded-xl overflow-hidden" style={{ height: 280 }}>
              <img
                src={annotatedUrl}
                alt="Annotated detection output"
                className="absolute inset-0 w-full h-full object-contain"
                style={{ background: '#0a0f1a' }}
              />
              <div className="absolute top-2 right-2 text-xs px-2 py-1 rounded font-mono"
                style={{ background: 'rgba(0,0,0,0.6)', color: '#94a3b8', fontSize: 10 }}>
                BACKEND ANNOTATED
              </div>
            </div>
          ) : (
            <Dropzone onFile={handleFile} previewUrl={previewUrl} />
          )}

          <div className="flex gap-2 mt-4">
            <button
              onClick={runDetection}
              disabled={!file || status === 'analyzing'}
              className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-semibold bg-amber-500 text-black hover:bg-amber-400 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              {status === 'analyzing' ? (
                <><Loader2 size={15} className="animate-spin" /> Analyzing…</>
              ) : (
                <><ScanLine size={15} /> Run Detection</>
              )}
            </button>
            <button
              onClick={reset}
              className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm text-slate-400 border border-white/10 hover:border-white/20 transition-colors"
            >
              <RotateCcw size={14} /> Reset
            </button>
          </div>

          {result?.qualityFlags && (
            <div className="mt-3 flex flex-wrap gap-2">
              {result.qualityFlags.lowLight   && <span className="text-xs px-2 py-1 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">Low light</span>}
              {result.qualityFlags.motionBlur && <span className="text-xs px-2 py-1 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">Motion blur</span>}
              {result.qualityFlags.rain       && <span className="text-xs px-2 py-1 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">Rain / occlusion</span>}
            </div>
          )}
        </div>

        {/* Right: results */}
        <div className="space-y-4">
          {status === 'idle' && (
            <div className="card p-8 h-full flex flex-col items-center justify-center text-center gap-2" style={{ minHeight: 280 }}>
              <ImageIcon size={26} className="text-slate-700" />
              <p className="text-sm text-slate-500">Upload an image and run detection to see results</p>
              <p className="text-xs text-slate-700">YOLO11 bounding boxes, OCR, violations, and confidence scores will appear here</p>
            </div>
          )}

          {status === 'analyzing' && (
            <div className="card p-8 h-full flex flex-col items-center justify-center text-center gap-3" style={{ minHeight: 280 }}>
              <Loader2 size={24} className="text-amber-400 animate-spin" />
              <p className="text-sm text-slate-400">Running YOLO11 + OCR pipeline…</p>
            </div>
          )}

          {status === 'done' && result && (
            <>
              {/* OCR result */}
              <div className="card p-5">
                <p className="text-xs text-slate-600 uppercase tracking-widest mb-3">License Plate (OCR)</p>
                <div className="flex items-center justify-between">
                  <span style={{ fontFamily: 'Space Grotesk, sans-serif' }}
                    className="text-2xl font-bold text-white font-mono tracking-wide">
                    {result.ocr?.plateText || result.plate || 'NOT DETECTED'}
                  </span>
                  {result.ocr?.confidence != null && (
                    <span className={`text-sm font-semibold ${severityColor(result.ocr.confidence)}`}>
                      {result.ocr.confidence}% confidence
                    </span>
                  )}
                </div>
              </div>

              {/* Detected vehicles */}
              {(result.vehicles || []).length > 0 && (
                <div className="card p-5">
                  <p className="text-xs text-slate-600 uppercase tracking-widest mb-3">
                    Detected Vehicles ({result.vehicles.length})
                  </p>
                  <div className="space-y-2">
                    {result.vehicles.map((v, i) => (
                      <div key={i} className="flex items-center gap-3 px-3 py-2 rounded-lg bg-navy-900/60">
                        <Car size={14} className="text-slate-500" />
                        <span className="text-sm text-slate-300 flex-1">{v.type || v.class}</span>
                        {v.confidence != null && (
                          <span className={`text-xs font-semibold ${severityColor(v.confidence)}`}>
                            {v.confidence}%
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Detected violations */}
              <div className="card p-5">
                <p className="text-xs text-slate-600 uppercase tracking-widest mb-3">
                  Detected Violations ({(result.violations || []).length})
                </p>
                {(result.violations || []).length === 0 ? (
                  <p className="text-sm text-green-400">✓ No violations detected</p>
                ) : (
                  <div className="space-y-2">
                    {result.violations.map((v, i) => (
                      <div key={i}
                        className="flex items-center gap-3 px-3 py-2.5 rounded-lg border-l-2 border-l-red-500 bg-red-500/5">
                        <AlertTriangle size={14} className="text-red-400 flex-shrink-0" />
                        <span className="text-sm text-slate-300 flex-1">{v.type || v.violation}</span>
                        {v.confidence != null && (
                          <span className={`text-xs font-semibold ${severityColor(v.confidence)}`}>
                            {v.confidence}%
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Download */}
              <button
                onClick={downloadEvidence}
                className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-semibold text-teal-400 border border-teal-500/20 hover:bg-teal-500/10 transition-colors"
              >
                <Download size={14} /> Download Evidence Package
              </button>
            </>
          )}

          {status === 'error' && (
            <div className="card p-5 flex items-center gap-3 border-l-2 border-l-red-500 bg-red-500/5">
              <XCircle size={16} className="text-red-400" />
              <p className="text-sm text-slate-400">
                Detection failed — check that FastAPI is running at{' '}
                <span className="font-mono text-red-400">{API_BASE}</span> and the{' '}
                <span className="font-mono">POST /detect</span> endpoint is live.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}