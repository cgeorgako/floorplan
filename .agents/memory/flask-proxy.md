---
name: Flask routing via artifact service (sleep trick)
description: How the Flask app is exposed at root in the PNPM_WORKSPACE artifact routing setup without port conflicts
---

## Rule
Two artifact services in `artifacts/api-server/.replit-artifact/artifact.toml`:
1. **API Server** (`localPort = 8080`, `paths = ["/api"]`) — standard Node/Express, handles `/api/*`.
2. **Flask App** (`localPort = 5000`, `paths = ["/"]`) — routes all other paths to the Flask app.

In **development**, the Flask App service runs `sleep infinity`. The `Start application` workflow already owns port 5000, so the artifact proxy routes `/` there with no conflict.

In **production**, the Flask App service runs: `bash -c "cd /home/runner/workspace && pip install -r requirements.txt --quiet && exec gunicorn --bind=0.0.0.0:5000 webapp.app:app"`. No `Start application` workflow runs in production.

**Why:** The PNPM_WORKSPACE + expertMode artifact router owns port 80 and routes by path prefix to registered service ports. The `.replit` `[[ports]]` mapping (5000 → 80) is overridden. A second gunicorn in development causes port conflicts (`--reuse-port` only works within one gunicorn instance, not across two). A `sleep infinity` dev command avoids the conflict while keeping the service slot alive for the proxy.

**How to apply:**
- Never use a port-check script for the dev run command — there is a race condition where the check fires before `Start application` binds port 5000, causing a second gunicorn to start.
- Never add `--reuse-port` to the artifact Flask service gunicorn; only `Start application` uses it in dev.
- The schema validator requires BOTH a `[services.development]` run command AND a `[services.production.run]` for the service to be valid. A service with no development run at all fails schema validation.
- "Could not find run command" on Republish = a service has `paths` registered but no `[services.production.run]`.
