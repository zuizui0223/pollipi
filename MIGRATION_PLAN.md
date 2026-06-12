# PolliPi Monorepo Migration Plan

This document tracks the migration covered by PR #9 and Issue #11.

The purpose of this PR is structural: make the monorepo layout the future development home and document the deployment artifact flow. It must not change the scientific/capture behavior by accident. Adaptive timelapse behavior, ROI tracking interpretation, and candidate-review methodology remain separate work tracked mainly in #1 and #8.

## Source Of Truth Decision

After this migration branch is accepted:

- `packages/server` is the maintained backend source of truth.
- `packages/web` is the maintained iPad/PWA source of truth.
- `packages/contracts` is the place to centralize shared API/browser types as the API stabilizes.
- `dist/pollipi_api_server.py` is the generated Raspberry Pi distribution artifact.
- Root-level `pollipi_api_server.py` and `web/` remain legacy / compatibility references during the migration. They should not be deleted in this PR.

The root files can later become one of these, but that should be a deliberate follow-up:

- generated outputs copied from `dist/` and `packages/web/dist/`,
- thin compatibility shims that preserve existing Pi import paths,
- or archived legacy references under `legacy/`.

They should not continue as manually edited source-of-truth files once `packages/server` and `packages/web` are accepted.

## Current Branch State

Implemented in PR #9:

- Root workspace configuration with `pnpm-workspace.yaml`, root `package.json`, and shared TypeScript config.
- `packages/server/src/visit_monitor_server` with app factory, config, API router, schemas, route modules, services, adapters, and distribution bundler.
- Restored main PolliPi API routes in the packaged server: `/start`, `/stop`, `/status`, `/device`, `/system`, `/latest`, `/preview`, `/mjpeg`, `/roi/suggest`, `/images`, `/exports/images.zip`, `/events`, and `/training/*`.
- Fake-camera smoke coverage in `packages/server/tests/test_api_smoke.py`.
- Single-file bundler at `visit_monitor_server.distribution.bundle_single_file` that writes `dist/pollipi_api_server.py`.
- `.github/workflows/server-ci.yml` that compile-checks server code, runs fake-camera pytest, builds the single-file artifact, compile-checks it, smoke-tests it, uploads it, and optionally runs a self-hosted Pi smoke test.
- `packages/web` rebuilt with Vite, Preact, Signals, vanilla-extract, typed API helpers, and component/state modules.
- `legacy/` retained as archived prototype/reference code.

Still intentionally not finalized in this PR:

- Removing root-level `pollipi_api_server.py` or root-level `web/`.
- Converting every deployment script to artifact-only deployment.
- Treating the root files as generated outputs.
- Hardware validation on real Picamera2/IMX500 devices unless a Pi runner or manual field test is available.
- Changing adaptive timelapse, ROI tracking, or candidate review behavior.

## Verification Commands

Install workspace dependencies from the repository root:

```bash
pnpm install
```

Server smoke test:

```bash
pnpm test:server
```

Direct equivalent:

```bash
cd packages/server
POLLIPI_FAKE_CAMERA=1 pytest -q
```

Server development run:

```bash
pnpm dev:server
```

Web type check and build:

```bash
pnpm check:web
pnpm build:web
```

The web build output is:

```text
packages/web/dist/
```

Build the Pi server artifact:

```bash
pnpm build:server
```

This writes:

```text
dist/pollipi_api_server.py
```

Smoke-test the generated artifact locally with fake camera:

```bash
POLLIPI_FAKE_CAMERA=1 POLLIPI_IMAGE_DIR="$(mktemp -d)" \
  python dist/pollipi_api_server.py --host 127.0.0.1 --port 8000
```

Or through Uvicorn:

```bash
POLLIPI_FAKE_CAMERA=1 POLLIPI_IMAGE_DIR="$(mktemp -d)" \
  python -m uvicorn --app-dir dist pollipi_api_server:app --host 127.0.0.1 --port 8000
```

## Artifact Deployment Model

Target deployment flow:

1. Build the server artifact.

   ```bash
   pnpm build:server
   ```

2. Build the web app.

   ```bash
   pnpm build:web
   ```

3. Copy the server artifact to the Pi using the existing compatibility filename.

   ```bash
   scp dist/pollipi_api_server.py pi@pollipi1.local:~/pollipi_timelapse/pollipi_api_server.py
   ```

4. Copy the web build to the Pi web asset directory.

   ```bash
   scp -r packages/web/dist pi@pollipi1.local:~/pollipi_timelapse/web
   ```

5. Restart the existing service.

   ```bash
   ssh pi@pollipi1.local "sudo systemctl restart pollipi.service"
   ```

6. Run post-deploy smoke checks.

   ```bash
   curl http://pollipi1.local:8000/device
   curl http://pollipi1.local:8000/status
   curl -X POST http://pollipi1.local:8000/start \
     -H "Content-Type: application/json" \
     -d '{"interval_sec": 30}'
   curl http://pollipi1.local:8000/images
   curl http://pollipi1.local:8000/latest --output latest.jpg
   curl -X POST http://pollipi1.local:8000/stop
   ```

This preserves the current Pi import path and systemd shape:

```bash
python -m uvicorn pollipi_api_server:app --host 0.0.0.0 --port 8000
```

while moving maintained backend code into `packages/server`.

## Root-Level Compatibility Policy

For this PR:

- Do not delete root-level `pollipi_api_server.py`.
- Do not delete root-level `web/`.
- Do not make root-level files the place for new backend or web feature work.
- Use root files only as legacy behavior references or temporary compatibility entrypoints.
- Document any divergence between root behavior and package behavior as migration risk.

Follow-up decision required after PR #9:

- Replace root `pollipi_api_server.py` with generated `dist/pollipi_api_server.py`, or keep a shim.
- Replace root `web/` with `packages/web/dist/`, or move the old root web app under `legacy/`.
- Update `install.sh`, `setup_device.sh`, `deploy_pollipi_pi.ps1`, `QUICKSTART.md`, and `DEVICE_ONBOARDING.md` to the final artifact/install flow.

## Acceptance Checklist Alignment

Issue #11 checklist mapping:

- `packages/server` is the backend source of truth: documented here and in README; package implementation exists.
- `packages/web` is the web UI source of truth: documented here and in README; package implementation exists.
- Fake-camera server smoke tests: `pnpm test:server` / `pytest packages/server`.
- Web type/build checks: `pnpm check:web` and `pnpm build:web`.
- Single-file artifact: `pnpm build:server` creates `dist/pollipi_api_server.py`.
- Pi hardware validation: still requires real hardware or a self-hosted Pi runner.
- Root deployment docs/scripts: partially documented here and in README; script conversion remains follow-up.
- Root-level file policy: preserve as legacy / compatibility for now; do not remove in this PR.

## Risks

- Picamera2, OpenCV, and IMX500 behavior still need Raspberry Pi validation. Fake-camera tests only verify the software exchange path.
- CSV schemas are compatibility surfaces. Do not rename or drop fields as part of a structural migration.
- The web app and server should keep endpoint paths stable during this migration. Versioned routes can be considered after behavior parity is established.
- The single-file artifact embeds repository Python modules only. Pi dependency installation must still provide FastAPI, Uvicorn, Picamera2, OpenCV, and other external libraries.
