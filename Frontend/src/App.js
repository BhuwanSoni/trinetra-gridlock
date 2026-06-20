import React, { useState } from 'react';

import Sidebar from './pages/Sidebar';

import Landing from './pages/Landing';
import Dashboard from './pages/Dashboard';
import UploadAnalysis from './pages/UploadAnalysis';
import Violations from './pages/Violations';
import ReviewQueue from './pages/ReviewQueue';
import EvidenceLocker from './pages/EvidenceLocker';
import VehicleLookup from './pages/VehicleLookup';
import Analytics from './pages/Analytics';
import HotspotAnalysis from './pages/HotspotAnalysis';
import Reports from './pages/Reports';

const pages = {
  landing: Landing,
  dashboard: Dashboard,
  upload: UploadAnalysis,
  violations: Violations,
  review: ReviewQueue,
  evidence: EvidenceLocker,
  vehicle: VehicleLookup,
  analytics: Analytics,
  hotspots: HotspotAnalysis,
  reports: Reports,
};

export default function App() {
  const [page, setPage] = useState('landing');

  const Page = pages[page] || Landing;

  if (page === 'landing') {
    return <Landing onNavigate={setPage} />;
  }

  return (
    <div
      style={{
        display: 'flex',
        minHeight: '100vh',
        background: '#f8fafc',
      }}
    >
      <Sidebar active={page} onNavigate={setPage} />

      <main
        style={{
          flex: 1,
          padding: '24px',
          overflowY: 'auto',
        }}
      >
        <Page onNavigate={setPage} />

        <div
          style={{
            marginTop: '40px',
            paddingTop: '16px',
            borderTop: '1px solid #e5e7eb',
            fontSize: '12px',
            color: '#6b7280',
            display: 'flex',
            justifyContent: 'space-between',
          }}
        >
          <span>
            TRINETRA · AI Traffic Violation Detection System
          </span>

          <span>
            Gridlock 2.0 Hackathon
          </span>
        </div>
      </main>
    </div>
  );
}