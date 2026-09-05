# Base44 Dev Environment

## Stack
- **Frontend**: Create React App + craco (React 19), served by the webpack dev server on port 3000. Uses `@emergentbase/visual-edits` craco wrapper in dev mode.
- **Backend**: FastAPI (`backend/server.py`) on port 8000, run with `uvicorn --reload`.
- **Database**: MongoDB (compose service `mongo`).

## Running
```
docker compose -f docker-compose.base44.yml up -d --build
```
Verify:
- `curl http://localhost:8000/api/` → `{"message":"ProMão API"}`
- `curl http://localhost:3000/` → CRA index.html
- `docker compose -f docker-compose.base44.yml ps` → all services Up, mongo Healthy

## Non-obvious findings
- **Backend requirements are trimmed.** `backend/requirements.txt` lists private/internal wheels (`emergentintegrations`, `litellm` from a customer-assets URL) that are NOT on PyPI and are NOT imported by `server.py` or its tests. The Base44 build uses `backend/requirements.base44.txt` (only the packages actually imported) to avoid pulling those. If a new backend dependency is added to `server.py`, add it to `requirements.base44.txt` too.
- **Cross-origin wiring (two public ports).** The frontend calls `${REACT_APP_BACKEND_URL}/api` with `withCredentials: true`; the backend sets auth cookies as `SameSite=None; Secure` and has CORS (`allow_credentials=True`) echoing the request origin. Compose passes `REACT_APP_BACKEND_URL=https://8000-${BASE44_PUBLIC_HOST_SUFFIX}` to the frontend and `FRONTEND_URL=https://3000-${BASE44_PUBLIC_HOST_SUFFIX}` to the backend. Both port 3000 and 8000 are exposed publicly.
- **Dev server host allowlist.** `frontend/craco.config.js` sets `devServerConfig.allowedHosts = "all"` so the preview's external hostname (which changes per environment) is accepted; `HOST=0.0.0.0` is set via compose environment. Do not remove these or the preview will be blocked.
- **No lockfile.** `yarn install` resolves fresh on build; `node_modules` is preserved via an anonymous volume (`/app/node_modules`) so the bind mount doesn't mask it.
- **Live reload**: backend uses `uvicorn --reload`; frontend uses the CRA dev server with polling (`CHOKIDAR_USEPOLLING=true`) for bind-mount file watching.

## Secrets (optional)
`RESEND_API_KEY` and `SENDER_EMAIL` enable transactional email (Resend). Both are optional — `record_and_send_email` skips sending when they are absent, so the app works fully without them. Delivered via `/run/base44/app.env`.

## Local infra credentials (not secrets)
`MONGO_URL`, `DB_NAME`, and `JWT_SECRET` are generated/local and set in compose `environment:` (JWT_SECRET is a fixed dev value — fine for preview). They are NOT user-supplied external secrets.
