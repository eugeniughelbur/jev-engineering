#!/usr/bin/env bash
# Run the gate as a background service on macOS, starting at login.
#
#   ./service/install.sh            install and start
#   ./service/install.sh uninstall  stop and remove
#
# It writes a launchd job that keeps serve.py alive on 127.0.0.1:8787.
# Nothing listens on a public interface.

set -euo pipefail

LABEL="io.theaioperator.jev-engineering"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOGDIR="$HOME/.jev-gate"

if [ "${1:-install}" = "uninstall" ]; then
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  rm -f "$PLIST"
  echo "removed $LABEL"
  exit 0
fi

command -v uv >/dev/null || { echo "uv not found. brew install uv"; exit 1; }
mkdir -p "$LOGDIR" "$(dirname "$PLIST")"

# The key has to reach the job, and launchd does not read your shell profile.
KEY="${OPENROUTER_API_KEY:-${TYPESAFE_API_KEY:-}}"
if [ -z "$KEY" ]; then
  echo "set OPENROUTER_API_KEY in this shell first, so the job inherits it"
  exit 1
fi

cat > "$PLIST" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$(command -v uv)</string>
    <string>run</string>
    <string>--directory</string>
    <string>$ROOT</string>
    <string>serve.py</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>OPENROUTER_API_KEY</key><string>$KEY</string>
    <key>JEV_GATE_MODE</key><string>${JEV_GATE_MODE:-observe}</string>
    <key>JEV_GATE_HOST</key><string>127.0.0.1</string>
    <key>JEV_GATE_PORT</key><string>${JEV_GATE_PORT:-8787}</string>
    <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
  </dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$LOGDIR/service.out.log</string>
  <key>StandardErrorPath</key><string>$LOGDIR/service.err.log</string>
</dict>
</plist>
PLIST_EOF

chmod 600 "$PLIST"   # it holds your key
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

echo "installed $LABEL"
echo "health:  curl -s localhost:${JEV_GATE_PORT:-8787}/health"
echo "logs:    $LOGDIR/service.err.log"
echo "stop:    ./service/install.sh uninstall"
