# ForgeSight Web UI

Modern React-based web interface for ForgeSight inspection platform.

## Features

- **Authentication**: Register, sign in, store JWT, and clear expired sessions
- **Inspection List**: Browse all submitted inspections with component type and part ID
- **Inspection Upload**: Submit new inspections with image upload and metadata
- **Result Viewer**: Real-time result display with detection overlays and segmentation masks
- **Model Management**: Browse MLflow model versions and transition stages
- **Status Polling**: Auto-refresh inference job status while processing

## Tech Stack

- **React 18** — UI framework
- **TypeScript** — Type safety
- **Vite 8** — Build tool
- **Axios** — HTTP client
- **CSS3** — Styling (no build required)

## Setup

```bash
npm install
npm run dev          # Development server on http://localhost:3000
npm run build        # Production build
npm run preview      # Preview production build
npm test -- --run --passWithNoTests
```

## API Integration

The app connects to the ForgeSight API:

- **Default API Base**: `/api/v1`
- **Default media path**: `/media`
- **Docker**: Nginx proxies `/api` and `/media` to the API container
- **Local dev**: Vite proxies `/api` and `/media` to `VITE_API_PROXY_TARGET` or `http://localhost:8000`
- **Environment**: Set `VITE_API_URL` at build time to override the API base

## Project Structure

```
src/
  ├── main.tsx           # Entry point
  ├── App.tsx            # Main app component
  ├── index.css          # Global styles
  ├── App.css            # Layout styles
  ├── api.ts             # API client & types
  ├── pages/
  │   ├── AuthPanel.tsx             # Register/sign-in form
  │   ├── InspectionList.tsx      # List view
  │   ├── InspectionUpload.tsx    # Upload form
  │   ├── ModelManagement.tsx     # MLflow registry view
  │   └── ResultViewer.tsx        # Results view
  └── styles/
      └── ModelManagement.css
```

## Key Components

### AuthPanel
- Registers users through `/api/v1/auth/register`
- Signs in through `/api/v1/auth/login`
- Persists `access_token` and current user details in local storage

### InspectionList
- Displays all inspections in a card grid
- Loads from `/api/v1/inspections` API
- Click card to view detailed results

### InspectionUpload
- Form to create new inspection
- File upload with image selection
- Auto-submits inference job on completion

### ResultViewer
- Shows job status and inference results
- Real-time polling for job completion
- Displays detection overlay and segmentation mask images

### ModelManagement
- Loads registered MLflow models from `/api/v1/models/registry`
- Transitions model versions between stages through the API

## Next Steps

- [ ] Add filtering/search in inspection list
- [ ] Implement review workflow UI
- [ ] Add export/reporting features
