# ClauseLens React Frontend

This folder contains the responsive React UI. It uses the existing FastAPI backend; the analysis engine and data processing remain in Python.

## Windows / VS Code development

Keep two terminals open from the project root.

### Terminal 1 — API backend

```powershell
.venv\Scripts\Activate.ps1
python scripts/serve.py
```

### Terminal 2 — React UI

```powershell
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173` in the browser. Vite proxies `/api/*` requests to the backend at `http://127.0.0.1:8000`.

## Build the UI for the Python server

```powershell
cd frontend
npm install
npm run build
cd ..
python scripts/serve.py
```

When `frontend/dist/index.html` exists, FastAPI serves the compiled React UI at `http://127.0.0.1:8000`. If the compiled UI is absent, the original HTML UI stays available as a fallback.

## Features currently connected to the backend

- Analyze pasted agreement text or upload PDF, DOCX and TXT files.
- Choose English or Hinglish explanations.
- Load the backend's rental-agreement or offer-and-bond sample.
- Review saved reports, view clause details and risk indicators, ask questions about the agreement, and delete reports.
- Save report shortcuts in browser local storage.
- Print a report; choose “Save as PDF” in the browser print dialog.

The interface is responsive for desktop, tablet and mobile layouts. Risk flags are screening indicators, not legal advice.
