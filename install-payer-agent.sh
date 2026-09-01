#!/usr/bin/env bash
#
# Install the demo payer API as a launchd agent, so it is running whenever the
# machine is. Without it the demo agents' tools fail on a fresh boot, which is a
# poor thing to discover in front of a client.
#
#   demo/install-payer-agent.sh       install and start
#   demo/install-payer-agent.sh -u    stop and remove
#
set -euo pipefail

LABEL="ai.indicus.payer-api"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$REPO/backend/.venv/bin/uvicorn"
LOG_DIR="$REPO/demo/.logs"

uninstall() {
  # bootout returns non-zero when nothing is loaded, which is fine here.
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  rm -f "$PLIST"
  echo "Removed $LABEL."
}

if [[ "${1:-}" == "-u" || "${1:-}" == "--uninstall" ]]; then
  uninstall
  exit 0
fi

if [[ ! -x "$PYTHON" ]]; then
  echo "Cannot find $PYTHON — create the backend virtualenv first." >&2
  exit 1
fi

mkdir -p "$HOME/Library/LaunchAgents" "$LOG_DIR"

cat > "$PLIST" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON</string>
    <string>payer_api:app</string>
    <string>--app-dir</string>
    <string>$REPO/demo</string>
    <string>--host</string>
    <string>127.0.0.1</string>
    <string>--port</string>
    <string>8300</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$REPO/demo</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>$LOG_DIR/payer-api.log</string>
  <key>StandardErrorPath</key>
  <string>$LOG_DIR/payer-api.err</string>
</dict>
</plist>
PLIST_EOF

# Reinstalling should replace cleanly rather than fail on an already-loaded label.
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
launchctl kickstart -k "gui/$(id -u)/$LABEL"

echo "Installed $LABEL — binds 127.0.0.1:8300, restarts on boot and on crash."
echo "Logs: $LOG_DIR/payer-api.log"

for _ in $(seq 1 20); do
  if curl -fsS --max-time 2 http://127.0.0.1:8300/claims/CLM-88421 >/dev/null 2>&1; then
    echo "Responding on http://127.0.0.1:8300"
    exit 0
  fi
  sleep 0.5
done

echo "Installed, but it did not answer within 10s. Check $LOG_DIR/payer-api.err." >&2
exit 1
