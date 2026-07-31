# Deploy runbook: hdb-avm (Render API + Vercel frontend)

Config files are already committed (`render.yaml`, `web/vercel.json`). Everything
below needs your own account/browser — I can't create accounts or click through
OAuth consent screens on your behalf. Each step says exactly what to click.

## 1. Deploy the API on Render

1. Go to https://render.com → sign up (GitHub login is easiest — no card required
   for the free plan).
2. Dashboard → **New** → **Blueprint**.
3. Connect the `bryan2804/hdb-avm` GitHub repo (Render will ask for repo access
   via GitHub OAuth — approve it).
4. Render will detect `render.yaml` at the repo root and show one service:
   `hdb-avm-api` (Docker, free plan, health check `/health`).
5. It will prompt you for `HDB_CORS_ORIGINS` (marked `sync: false` in the
   blueprint so it's never overwritten by future pushes). Leave it as
   `["http://localhost:5173"]` for now — you'll come back and set the real
   value in step 3.
6. Click **Apply**. First build takes a few minutes (installs `.[api]`, copies
   `models/` + the two CSVs per the existing Dockerfile).
7. Once live, note the URL — something like `https://hdb-avm-api.onrender.com`.
8. Sanity check immediately:
   ```bash
   curl https://hdb-avm-api.onrender.com/health
   ```
   Expect `{"status":"ok"}` or similar 200 response.

**Free-tier behavior to expect:** the instance spins down after 15 minutes of
no traffic. The next request pays a cold-start cost — could be 30-60s+ while
it rebuilds the container context. This is why the frontend now shows a
"waking up" message after 4 seconds of loading (see `web/src/App.tsx`) instead
of looking broken.

## 2. Deploy the frontend on Vercel

1. Go to https://vercel.com → sign up with GitHub (no card required for
   Hobby plan).
2. **Add New** → **Project** → import `bryan2804/hdb-avm`.
3. Before deploying, click **Edit** next to Root Directory → select `web`.
   (`web/vercel.json` handles build/output/install commands once the root is
   set correctly — Vercel will auto-detect the Vite framework.)
4. Add an environment variable:
   - Key: `VITE_API_URL`
   - Value: the Render URL from step 1, e.g. `https://hdb-avm-api.onrender.com`
     (no trailing slash)
   - Scope: Production (and Preview if you want preview deploys to also hit
     the live API)
5. Click **Deploy**.
6. Once live, note the URL — something like `https://hdb-avm.vercel.app`.

## 3. Close the CORS loop

Now that you have the real Vercel URL:

1. Back in the Render dashboard → `hdb-avm-api` service → **Environment**.
2. Edit `HDB_CORS_ORIGINS` to a JSON list containing the real Vercel URL:
   ```
   ["https://hdb-avm.vercel.app"]
   ```
   (pydantic-settings parses this env var as JSON — must be a bracketed list,
   not a bare string.)
3. Save. Render redeploys automatically with the new value.

## 4. Verify end to end

```bash
# 1. Health check
curl https://hdb-avm-api.onrender.com/health

# 2. Real valuation request (adjust town/flat_type to values from /api/v1/metadata)
curl -X POST https://hdb-avm-api.onrender.com/api/v1/valuations \
  -H "Content-Type: application/json" \
  -d '{"town":"QUEENSTOWN","flat_type":"4 ROOM","floor_area_sqm":95,"storey":8,"remaining_lease_years":70}'
```

Then open `https://hdb-avm.vercel.app` in a browser:
- Form should load with towns/flat types populated (confirms `/api/v1/metadata`
  call succeeded, no CORS error).
- Submit a valuation, confirm the result + SHAP breakdown + trends chart render.
- Open browser dev tools → Network tab if anything looks wrong — a CORS
  failure will show as a failed OPTIONS/fetch with a console error naming the
  blocked origin.

Report back to me (or paste me the URLs) once both are live and I'll do a
second independent check from my end (curl + browser) and update the README
hero line to link the live app, replacing "FastAPI + React deployment in
progress."

## Rollback / troubleshooting notes

- If Render's free build ever times out or fails on the 65MB-adjacent context,
  check `.dockerignore` is excluding the full training CSV — it already does
  per the existing Dockerfile comment ("only the artifacts serving needs").
- If Vercel's build fails on `tsc -b`, it's a real typecheck error — same as
  CI would catch, not a hosting issue.
- If `/health` is fine but `/api/v1/valuations` 500s in production but not
  locally, check Render logs — most likely cause is a `models/` artifact not
  copied correctly by the Docker COPY step (unlikely, but worth ruling out
  first).
