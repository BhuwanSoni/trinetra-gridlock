const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Turns a relative URL like "/evidence-images/AB12CD34_..._full.jpg" (as
// returned by GET /evidence and GET /challans) into an absolute URL the
// <img> tag can load. Returns null if there's nothing to show.
export const evidenceImageUrl = (relativeUrl) => {
  if (!relativeUrl) return null;
  if (/^https?:\/\//i.test(relativeUrl)) return relativeUrl;
  return `${BASE_URL}${relativeUrl}`;
};

async function apiFetch(endpoint, options = {}) {
  try {
    const res = await fetch(`${BASE_URL}${endpoint}`, {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    });
    if (!res.ok) throw new Error(`${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn(`[HMATES] ${endpoint} failed, using fallback:`, err.message);
    return null;
  }
}

// Falls back to mock data whenever the real API call fails or returns null
async function withFallback(promise, mock) {
  const result = await promise;
  return result === null || result === undefined ? mock : result;
}

// ─────────────────────────────────────────────────────────────────────────
// LEGACY MOCK CONSTANTS — kept exported only because other components you
// haven't shared yet (Dashboard.jsx, VehicleLookup.jsx, Hotspots.jsx, etc.)
// may still import these names directly. NONE of the getX()/fetchX()
// functions below fall back to these anymore — Analytics, Reports, and the
// Evidence Locker now show real backend data or an explicit empty state.
// If a component below isn't on the list above, search your codebase for
// `mockViolations`, `mockStats`, `mockHotspots`, `mockCameras`,
// `mockEvalMetrics`, `mockDailySummary`, `mockVehicles` and wire those call
// sites to the real getX() functions the same way Reports/Analytics were.
// ─────────────────────────────────────────────────────────────────────────

export const mockViolations = [
  { id: 'VIO-001', plate: 'KA01MN2345', type: 'No Helmet', camera: 'CAM-01', location: 'Silk Board Junction', time: '18:43', date: '17 Jun 2026', status: 'pending', confidence: 97 },
  { id: 'VIO-002', plate: 'KA03AB7890', type: 'Signal Jump', camera: 'CAM-02', location: 'Hebbal Flyover', time: '18:41', date: '17 Jun 2026', status: 'approved', confidence: 89 },
  { id: 'VIO-003', plate: 'KA05CD1122', type: 'Wrong Lane', camera: 'CAM-03', location: 'KR Puram Bridge', time: '18:38', date: '17 Jun 2026', status: 'pending', confidence: 94 },
  { id: 'VIO-004', plate: 'KA02EF3344', type: 'No Seatbelt', camera: 'CAM-06', location: 'Outer Ring Road', time: '18:35', date: '17 Jun 2026', status: 'rejected', confidence: 91 },
  { id: 'VIO-005', plate: 'KA04GH5566', type: 'Overspeeding', camera: 'CAM-03', location: 'KR Puram Bridge', time: '15:11', date: '17 Jun 2026', status: 'escalated', confidence: 86 },
  { id: 'VIO-006', plate: 'KA01MN2345', type: 'No Helmet', camera: 'CAM-01', location: 'Silk Board Junction', time: '12:30', date: '16 Jun 2026', status: 'approved', confidence: 98 },
  { id: 'VIO-007', plate: 'KA05PQ1234', type: 'Signal Jump', camera: 'CAM-02', location: 'Hebbal Flyover', time: '14:58', date: '16 Jun 2026', status: 'pending', confidence: 93 },
  { id: 'VIO-008', plate: 'KA03RS5678', type: 'No Helmet', camera: 'CAM-01', location: 'Silk Board Junction', time: '09:15', date: '15 Jun 2026', status: 'approved', confidence: 95 },
];

export const mockCameras = [
  { id: 'CAM-01', location: 'Silk Board Junction', status: 'live', violations: 34, fps: 24 },
  { id: 'CAM-02', location: 'Hebbal Flyover', status: 'live', violations: 21, fps: 24 },
  { id: 'CAM-03', location: 'KR Puram Bridge', status: 'live', violations: 17, fps: 30 },
  { id: 'CAM-04', location: 'Tin Factory Junction', status: 'offline', violations: 0, fps: 0 },
  { id: 'CAM-05', location: 'Marathahalli Bridge', status: 'degraded', violations: 8, fps: 12 },
  { id: 'CAM-06', location: 'Outer Ring Road', status: 'live', violations: 29, fps: 24 },
];

export const mockStats = {
  totalImagesProcessed: 14820,
  totalViolations: 1847,
  highRiskCases: 23,
  pendingReview: 94,
  resolvedToday: 312,
  activeCameras: 42,
  ocrAccuracy: 97.1,
  detectionAccuracy: 92.4,
};

export const mockHotspots = [
  { junction: 'Silk Board Junction', violations: 312, risk: 'critical', change: 18 },
  { junction: 'Hebbal Flyover', violations: 247, risk: 'high', change: 9 },
  { junction: 'KR Puram Bridge', violations: 189, risk: 'high', change: -4 },
  { junction: 'Outer Ring Road', violations: 201, risk: 'high', change: 6 },
  { junction: 'Tin Factory Junction', violations: 134, risk: 'medium', change: -7 },
  { junction: 'Marathahalli Bridge', violations: 98, risk: 'medium', change: 3 },
  { junction: 'Yeshwanthpur Junction', violations: 112, risk: 'medium', change: 5 },
  { junction: 'MG Road Signal', violations: 76, risk: 'low', change: -2 },
];

export const mockEvalMetrics = {
  overall: { accuracy: 92.4, precision: 90.8, recall: 89.6, f1: 90.2, map50: 91.3, map5095: 68.7 },
  byClass: [
    { label: 'No Helmet', precision: 94, recall: 92, f1: 93, map50: 95 },
    { label: 'Signal Jump', precision: 89, recall: 87, f1: 88, map50: 90 },
    { label: 'Wrong Lane', precision: 86, recall: 84, f1: 85, map50: 87 },
    { label: 'No Seatbelt', precision: 91, recall: 88, f1: 89, map50: 92 },
    { label: 'Overspeeding', precision: 88, recall: 85, f1: 86, map50: 89 },
  ],
  trend: [
    { epoch: 'v1', map50: 68 },
    { epoch: 'v2', map50: 76 },
    { epoch: 'v3', map50: 82 },
    { epoch: 'v4', map50: 87 },
    { epoch: 'v5', map50: 91 },
  ],
};

export const mockDailySummary = [
  { date: '13 Jun 2026', flagged: 312, resolved: 290, pending: 22 },
  { date: '14 Jun 2026', flagged: 278, resolved: 261, pending: 17 },
  { date: '15 Jun 2026', flagged: 401, resolved: 374, pending: 27 },
  { date: '16 Jun 2026', flagged: 334, resolved: 308, pending: 26 },
  { date: '17 Jun 2026', flagged: 458, resolved: 421, pending: 37 },
  { date: '18 Jun 2026', flagged: 389, resolved: 352, pending: 37 },
  { date: '19 Jun 2026', flagged: 245, resolved: 231, pending: 14 },
];

export const mockVehicles = {
  'RJ14CD1234': {
    plate: 'RJ14 CD 1234',
    vehicle: 'Honda Activa',
    owner: 'Rahul Sharma',
    riskLevel: 'high',
    totalViolations: 6,
    finesPending: 4200,
    lastSeen: '17 Jun 2026',
    history: [
      { type: 'No Helmet', location: 'Silk Board Junction', date: '12 Jan 2026', status: 'approved' },
      { type: 'Triple Riding', location: 'MG Road Signal', date: '15 Feb 2026', status: 'approved' },
      { type: 'Signal Jump', location: 'Hebbal Flyover', date: '28 Apr 2026', status: 'pending' },
    ],
  },
  'KA01MN2345': {
    plate: 'KA01 MN 2345',
    vehicle: 'Bajaj Pulsar',
    owner: 'Ananya Reddy',
    riskLevel: 'medium',
    totalViolations: 3,
    finesPending: 1500,
    lastSeen: '17 Jun 2026',
    history: [
      { type: 'No Helmet', location: 'Silk Board Junction', date: '03 Mar 2026', status: 'approved' },
      { type: 'No Helmet', location: 'Silk Board Junction', date: '17 Jun 2026', status: 'pending' },
    ],
  },
};

// ─────────────────────────────────────────────────────────────────────────
// REAL BACKEND ADAPTERS
//
// api.py (your FastAPI app) only exposes: /upload, /upload/video, /status/{id},
// /report, /search/plate|date|camera|violation/{x}, /challans, /health.
// There is no /violations, /cameras, /stats, /hotspots endpoint — those never
// existed on the backend, so the old getX() functions below always failed
// silently and fell back to mock data. This version calls the real routes
// and reshapes their JSON into what the components expect.
//
// Field names (record_id, plate_number, camera_id, total_fine, combined_risk,
// top_severity, review_status, violations[].violation_type/confidence) are
// inferred from dashboard.py's usage of the same records + the challan
// example in your README. Open http://localhost:8000/docs, run GET /report
// and GET /challans, and diff the real JSON against the `??` fallbacks below
// if your analytics.py/evidence.py use different key names.
// ─────────────────────────────────────────────────────────────────────────

const STATUS_MAP = {
  AUTO_APPROVED: 'approved',
  MANUAL_REVIEW: 'pending',
  REJECTED: 'rejected',
};

const toPercent = (c) => {
  if (c === undefined || c === null) return 90;
  return Math.round(c > 1 ? c : c * 100);
};

export const fetchReport = () => apiFetch('/report');
export const fetchChallans = (limit = 200) => apiFetch(`/challans?limit=${limit}`);
export const fetchEvidence = (limit = 200) => apiFetch(`/evidence?limit=${limit}`);
export const searchPlate = (plate) => apiFetch(`/search/plate/${encodeURIComponent(plate)}`);
export const searchCamera = (camId) => apiFetch(`/search/camera/${encodeURIComponent(camId)}`);
export const searchDate = (date) => apiFetch(`/search/date/${date}`);
export const checkHealth = () => apiFetch('/health');

// Real evidence records (annotated full image + vehicle crop + plate crop)
// for the Evidence Locker screen, sourced from GET /evidence — the actual
// JPEGs written by evidence.save_evidence(), not placeholder graphics.
export const getEvidenceRecords = async () => {
  const data = await fetchEvidence(200);
  if (!data?.records) return [];
  return data.records.map((r) => {
    const v0 = r.violations?.[0] ?? {};
    return {
      id: r.record_id,
      plate: r.plate_number ?? 'UNKNOWN',
      type: v0.violation_type ?? r.top_severity ?? 'Violation',
      camera: r.camera_id ?? '—',
      location: r.location ?? '—',
      timestamp: r.timestamp ?? null,
      date: (r.timestamp ?? '').slice(0, 10) || '—',
      time: (r.timestamp ?? '').slice(11, 16) || '—',
      status: STATUS_MAP[r.review_status] ?? STATUS_MAP[r.status] ?? 'pending',
      confidence: toPercent(v0.confidence),
      fine: r.total_fine ?? 0,
      risk: r.combined_risk ?? null,
      severity: r.top_severity ?? 'Medium',
      violations: r.violations ?? [],
      // Real image files served from the backend's evidence/images/ folder
      fullImage:    evidenceImageUrl(r.image_url),
      vehicleImage: evidenceImageUrl(r.vehicle_crop_url),
      plateImage:   evidenceImageUrl(r.plate_crop_url),
    };
  });
};

// One row per challan (a challan can bundle several fused violations for one
// vehicle — review_status lives at the challan level, not per-violation, so
// we don't explode it into multiple rows).
function challanToRow(challan, idx) {
  const v0 = challan.violations?.[0] ?? {};
  const extra = (challan.violations?.length ?? 1) - 1;
  const plate = challan.plate_number ?? 'UNKNOWN';
  return {
    id: challan.record_id ?? challan.challan_id ?? `CHN-${idx}`,
    plate,
    type: `${v0.violation_type ?? v0.type ?? challan.top_severity ?? 'Violation'}${extra > 0 ? ` +${extra} more` : ''}`,
    camera: challan.camera_id ?? challan.camera ?? '—',
    location: challan.location ?? challan.camera_id ?? '—',
    time: (challan.timestamp ?? challan.issued_at ?? '').slice(11, 16) || '—',
    date: (challan.timestamp ?? challan.issued_at ?? '').slice(0, 10) || '—',
    status: STATUS_MAP[challan.review_status] ?? (plate === 'UNKNOWN' ? 'pending' : 'approved'),
    confidence: toPercent(v0.confidence),
    fine: challan.total_fine ?? challan.total_fine_inr ?? 0,
    risk: challan.combined_risk ?? null,
    violationCount: challan.violations?.length ?? 1,
    // Real evidence images from the backend's /evidence-images static mount
    fullImage:    evidenceImageUrl(challan.image_url),
    vehicleImage: evidenceImageUrl(challan.vehicle_crop_url),
    plateImage:   evidenceImageUrl(challan.plate_crop_url),
  };
}

export const getViolations = async () => {
  const data = await fetchChallans(200);
  if (!data?.challans) return [];
  return data.challans.map(challanToRow);
};

// Note: /report has no fields for pendingReview, resolvedToday, ocrAccuracy,
// or detectionAccuracy (those are model-benchmark numbers, not enforcement
// stats). They come back as null until you add them to
// analytics.generate_summary_report() — the UI should render '—' for null,
// not a fake number.
export const getStats = async () => {
  const report = await fetchReport();
  if (!report) return null;
  const highRisk = report.repeat_offenders
    ? Object.values(report.repeat_offenders).filter((c) => c >= 3).length
    : null;
  return {
    totalImagesProcessed: report.total_records ?? null,
    totalViolations: report.total_violations ?? null,
    highRiskCases: highRisk,
    activeCameras: report.violations_by_camera
      ? Object.keys(report.violations_by_camera).length
      : null,
    pendingReview: null,   // not exposed by generate_summary_report() yet
    resolvedToday: null,   // not exposed by generate_summary_report() yet
    ocrAccuracy: null,     // model-eval metric, not a runtime stat
    detectionAccuracy: null,
    totalFinesInr: report.total_fines_inr ?? null,
    topViolation: report.top_violation ?? null,
  };
};

// junction = camera_id here, since /report only groups by camera, not by
// human-readable location name. risk tier is derived locally (relative to
// the busiest camera) since the backend doesn't classify risk per-hotspot.
export const getHotspots = async () => {
  const report = await fetchReport();
  if (!report?.violations_by_camera) return [];
  const entries = Object.entries(report.violations_by_camera).sort((a, b) => b[1] - a[1]);
  const max = entries[0]?.[1] ?? 1;
  return entries.map(([cam, count]) => ({
    junction: cam,
    violations: count,
    risk: count / max > 0.7 ? 'critical' : count / max > 0.45 ? 'high' : count / max > 0.2 ? 'medium' : 'low',
    change: null, // /report has no week-over-week comparison yet
  }));
};

export const getCameras = async () => {
  const report = await fetchReport();
  if (!report?.violations_by_camera) return [];
  return Object.entries(report.violations_by_camera).map(([id, violations]) => ({
    id, location: id, status: 'live', violations, fps: null,
  }));
};

// HMATES detects + flags vehicles; it does not store registered-owner data
// (no Vahan/RTO integration), so `owner` and `vehicle` model name are not
// available from the backend and are shown as placeholders.
export const lookupVehicle = async (plate) => {
  const data = await searchPlate(plate.replace(/\s/g, '').toUpperCase());
  if (!data?.records?.length) return null;
  const recs = [...data.records].sort((a, b) => (b.timestamp ?? '').localeCompare(a.timestamp ?? ''));
  const latest = recs[0];
  return {
    plate: latest.plate_number ?? plate,
    vehicle: latest.vehicle_type ?? '— (not tracked by HMATES)',
    owner: latest.owner ?? '— (requires RTO integration)',
    riskLevel: (latest.combined_risk ?? 0) >= 70 ? 'high' : (latest.combined_risk ?? 0) >= 40 ? 'medium' : 'low',
    riskScore: latest.combined_risk ?? null,
    totalViolations: recs.reduce((a, r) => a + (r.violations?.length ?? 1), 0),
    finesPending: recs.reduce((a, r) => a + (r.total_fine ?? 0), 0),
    lastSeen: (latest.timestamp ?? '').slice(0, 10),
    history: recs.flatMap((r) =>
      (r.violations?.length ? r.violations : [{ violation_type: r.top_severity }]).map((v) => ({
        type: v.violation_type ?? v.type ?? 'Violation',
        location: r.location ?? r.camera_id ?? '—',
        date: (r.timestamp ?? '').slice(0, 10),
        status: STATUS_MAP[r.review_status] ?? 'pending',
      }))
    ),
  };
};

// Requires the new POST /challans/{record_id}/review endpoint added to api.py
// (api.py originally had no way to persist a review decision at all).
export const reviewViolation = (id, action, notes = '') =>
  withFallback(
    apiFetch(`/challans/${id}/review`, { method: 'POST', body: JSON.stringify({ action, notes }) }),
    { success: true, persisted: false }
  );

export const exportViolationsCSV = (violations) => {
  const headers = ['Case ID', 'Plate', 'Type', 'Camera', 'Location', 'Date', 'Time', 'Confidence', 'Status'];
  const rows = violations.map(v => [v.id, v.plate, v.type, v.camera, v.location, v.date, v.time, `${v.confidence}%`, v.status]);
  return [headers, ...rows].map(r => r.join(',')).join('\n');
};

export const detectViolations = async (file, camera = 'CAM-01', location = 'Dashboard') => {
  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch(
      `${BASE_URL}/upload?camera=${encodeURIComponent(camera)}&location=${encodeURIComponent(location)}&save=true`,
      { method: 'POST', body: formData }
    );

    if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
    const data = await res.json();

    // Normalise the real API response shape → the shape React components expect
    // Real shape:  { status, camera, location, summary, violations, challans }
    // Expected:    { imageId, processedAt, ocr, vehicles, violations, qualityFlags, challans, summary }
    const firstChallan  = data.challans?.[0] ?? {};
    const plateText     = firstChallan.plate_number ?? 'UNKNOWN';

    return {
      // Identity
      imageId:      `IMG-${Date.now()}`,
      processedAt:  new Date().toISOString(),
      camera:       data.camera,
      location:     data.location,

      // OCR — pulled from the first challan; challans carry the resolved plate
      ocr: {
        plateText,
        confidence: plateText !== 'UNKNOWN' ? 95 : 0,
      },

      // Vehicles — reconstruct from challans (each challan = one vehicle)
      vehicles: (data.challans ?? []).map((ch, i) => ({
        id:         `v${i + 1}`,
        plate:      ch.plate_number,
        type:       ch.vehicle_type ?? 'Unknown',
        fine:       ch.total_fine_inr,
        risk:       ch.combined_risk ?? ch.risk_score ?? 0,
        severity:   ch.top_severity ?? 'Medium',
        confidence: toPercent(ch.violations?.[0]?.confidence ?? 0.9),
      })),

      // Violations — map from the real violation objects
      violations: (data.violations ?? []).map((v, i) => ({
        id:         `d${i + 1}`,
        type:       v.violation_type ?? v.type,
        confidence: toPercent(v.confidence ?? 0.9),
        plate:      v.plate_number ?? 'UNKNOWN',
        fine:       v.fine_inr ?? 0,
        severity:   v.severity ?? 'Medium',
      })),

      // Summary straight from the API
      summary: data.summary ?? {},

      // Challans straight from the API (useful for Review Queue)
      challans: data.challans ?? [],

      // Quality flags — not part of the current API response; default to false
      qualityFlags: { lowLight: false, motionBlur: false, rain: false },
    };

  } catch (err) {
    console.error('[HMATES] detectViolations error:', err);
    // Return a clearly-labelled error shape so the UI can surface it gracefully
    return {
      imageId:      `IMG-${Date.now()}`,
      processedAt:  new Date().toISOString(),
      error:        err.message,
      ocr:          { plateText: 'ERROR', confidence: 0 },
      vehicles:     [],
      violations:   [],
      challans:     [],
      summary:      {},
      qualityFlags: { lowLight: false, motionBlur: false, rain: false },
    };
  }
};