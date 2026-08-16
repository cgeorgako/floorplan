---
name: Flask routing via api-server proxy
description: How the Flask app is exposed at root in the PNPM_WORKSPACE artifact routing setup
---

## Rule
There is exactly one gunicorn process, managed by the `Start application` workflow on port 5000. The artifact proxy routes `/` to the api-server (port 8080), which has a catch-all middleware in `artifacts/api-server/src/app.ts` that pipes all non-`/api` requests to `127.0.0.1:5000`.

**Why:** The PNPM_WORKSPACE + expertMode artifact router owns port 80 and routes by path to registered services. The `.replit` `[[ports]]` mapping (5000 → 80) is overridden by the artifact router when artifacts are present. A second gunicorn service in artifact.toml causes two gunicorn masters to fight over port 5000 (`--reuse-port` only works within one gunicorn instance, not across two).

**How to apply:**
- The artifact.toml for api-server lists one service (`localPort = 8080`) with `paths = ["/api", "/"]`.
- The proxy code is the catch-all at the bottom of `app.ts` — keep it below `app.use("/api", router)`.
- Never add a `localPort = 5000` service entry to any artifact.toml. Never add a second workflow that starts gunicorn on 5000.
- If the Flask app needs to move to a different port, update both the `Start application` workflow command and the proxy target in `app.ts`.
