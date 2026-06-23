# PolliPi 5-device deploy runbook (key-auth, latest `main`)

This is the manual runbook for distributing the latest `main` build to the five
Pi devices and controlling them from the iPad web app. The deploy itself (SSH +
`sudo`) is **run by the operator**, not from the agent environment, so no
password is ever placed in a command, file, or shell history.

- Base: `main` @ `7324335` (verify with `git log --oneline -1`).
- Devices (all confirmed reachable): `zuizui.local`, `zuizui2.local`,
  `zuizui3.local`, `zuizui4.local`, `zuizui5.local`.
- SSH user: `zuizui0223` (from `tools/fleet.gl-lan.example.json`).
- Fleet config written for you: `tools/fleet.local.json`.
- Dedicated deploy key generated: `~/.ssh/pollipi_deploy_ed25519[.pub]`.

> Security: the password shared in chat was **not** stored anywhere. After key
> auth is working, consider rotating that password.

## 0. Prerequisites (one-time, on the deploy PC)

Node + pnpm are required to build the web bundle (not currently installed):

```powershell
winget install OpenJS.NodeJS.LTS      # or nvm-windows
corepack enable                        # provides pnpm
node --version && pnpm --version
```

The PC must be on the GL LAN (`192.168.8.0/24`) for the live preflight check.

## 1. Register the deploy key on each Pi (one-time, password used here only)

```bash
PUB="$HOME/.ssh/pollipi_deploy_ed25519.pub"
for h in zuizui zuizui2 zuizui3 zuizui4 zuizui5; do
  ssh-copy-id -i "$PUB" "zuizui0223@${h}.local"   # prompts for the SSH password
done
```

Then point SSH at the key (append to `~/.ssh/config`):

```
Host zuizui.local zuizui2.local zuizui3.local zuizui4.local zuizui5.local
  User zuizui0223
  IdentityFile ~/.ssh/pollipi_deploy_ed25519
  IdentitiesOnly yes
```

Verify password-less login: `ssh zuizui3.local true && echo OK`.

## 2. Allow the one privileged command without a password ("権限上げる")

The deploy restarts the service with `sudo systemctl restart pollipi.service`.
For a non-interactive deploy, give `zuizui0223` NOPASSWD for **just that**
command on each Pi (least privilege — not full passwordless sudo):

```bash
# on each Pi, once:
echo 'zuizui0223 ALL=(root) NOPASSWD: /usr/bin/systemctl restart pollipi.service' \
  | sudo tee /etc/sudoers.d/pollipi-deploy
sudo chmod 440 /etc/sudoers.d/pollipi-deploy
```

(If you skip this, the deploy will hang waiting for a sudo password.)

## 3. Build the artifacts (on the deploy PC, at repo root)

```bash
pnpm install
pnpm build:web                          # -> packages/web/dist
pnpm --filter @visit-monitor/server build   # -> dist/pollipi_api_server.py (bundled, incl. analysis)
ls dist/pollipi_api_server.py packages/web/dist/index.html   # both must exist
```

## 4. Dry-run the fleet deploy (no changes made)

```bash
python tools/pollipi_fleet_deploy.py --config tools/fleet.local.json
```

Review the planned steps per device (prepare dir, backup, upload server + web,
restart service). It also records the expected git short-SHA.

## 5. Live deploy to all five

```bash
python tools/pollipi_fleet_deploy.py --config tools/fleet.local.json \
  --execute --confirm-live-deploy \
  --expected-git-commit "$(git rev-parse --short=12 HEAD)"
```

The tool backs up the current artifact/web on each Pi and has rollback steps if a
device fails. Capture the output.

## 6. Control from the iPad

Open the web console per device (PolliPi already serves on port 8000):

- `http://zuizui.local:8000`
- `http://zuizui2.local:8000` … `http://zuizui5.local:8000`

Confirm each device shows status, then start/stop a scheduled capture and view
the timelapse gallery. (If the web app is mounted under a sub-path rather than
`/`, the dry-run preflight output shows the `post_deploy_base_url`.)

## Notes / guardrails

- Live adaptive interval control stays **disabled**; mesh runs in shadow/logging
  mode only. Do not enable adaptive control until real-Pi shadow logs are
  reviewed (see `ADAPTIVE_TIMELAPSE_METHOD.md`).
- Deploys restart `pollipi.service`; a device mid-capture will briefly stop.
- `tools/fleet.local.json` contains no secrets but is environment-specific; keep
  it out of commits if you prefer (it is not added to git here).
