# Baseline startup commands (Phase 0 + unified web)

## Main project (authoritative FastAPI)
```bash
source .venv/bin/activate
cd backend && python3 -m uvicorn main:app --reload --port 8000
```

## Unified React Operations Desk (ports friend UX onto main API)
```bash
# If 8000/5173 are busy, use 8001 + 5174:
cd backend && python3 -m uvicorn main:app --reload --host 127.0.0.1 --port 8001
cd web && npm run dev -- --host 127.0.0.1 --port 5174
# http://127.0.0.1:5174  (proxies /flood to :8001)
```

## Legacy static flood UI
```bash
python3 -m http.server 5500
# http://localhost:5500/flood.html
# http://localhost:5500/report.html
```

## Friend project (UX reference only — do not use its FastAPI stub)
```bash
cd ResqFlow-main
npm install
npm run dev
```
