# TRINETRA — Traffic Intelligence Operating System
### Gridlock 2.0 · Round 2

## Quick Start

```bash
# 1. Install dependencies
npm install

# 2. (Optional) Set your backend URL
cp .env.example .env
# Edit .env → REACT_APP_API_URL=http://your-backend/api

# 3. Run in development
npm start
```

Opens at http://localhost:3000

## Connecting to Your Backend

All API calls live in `src/services/api.js`.

Each function tries your real backend first, then falls back to mock data:

```js
export const getDashboard = () =>
  apiFetch('/dashboard') ?? Promise.resolve(mockDashboard);
```

Just set `REACT_APP_API_URL` in `.env` and your real endpoints will be used automatically.

## Pages
| Page | Route key | API function |
|---|---|---|
| Dashboard | dashboard | getDashboard() |
| Live Monitoring | live | getCameras() |
| Review Queue | review | getViolations(), reviewViolation() |
| Evidence Locker | evidence | getViolations() |
| Vehicle Intelligence | vehicle | getVehicle(plate) |
| Hotspot Analysis | hotspots | getHotspots() |
| Camera Health | camerahealth | getCameras() |
| Operational Insights | insights | — (charts) |
| System Metrics | system | getSystemMetrics() |

## Tech Stack
- React 18
- Tailwind CSS 3
- Recharts (charts)
- Lucide React (icons)
- Space Grotesk + Inter (fonts)
