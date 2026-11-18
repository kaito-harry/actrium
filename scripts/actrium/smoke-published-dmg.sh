#!/usr/bin/env bash
set -euo pipefail

test "$(uname -m)" = arm64
sw_vers
root=$(mktemp -d "${RUNNER_TEMP:-/tmp}/actrium-smoke.XXXXXX")
mount_dir="$root/mount"
app=/Applications/Actrium.app
test ! -e "$app"
server_pid=""
installed=false
cleanup() {
  if [[ -n "$server_pid" ]]; then
    kill "$server_pid" 2>/dev/null || true
  fi
  if "$installed"; then
    pkill -f '^/Applications/Actrium[.]app/Contents/' 2>/dev/null || true
    rm -rf "$app"
  fi
  hdiutil detach "$mount_dir" >/dev/null 2>&1 || true
  rm -rf "$root"
}
trap cleanup EXIT

name="Actrium_${RELEASE_TAG}_macos-arm64_unsigned.dmg"
base="$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/releases/download/$RELEASE_TAG"
for file in "$name" "$name.sha256"; do
  curl --fail --silent --show-error --location --retry 3 --max-time 60 "$base/$file" -o "$root/$file"
done
(
  cd "$root"
  shasum -a 256 -c "$name.sha256"
  printf '%s  %s\n' "$EXPECTED_SHA256" "$name" | shasum -a 256 -c -
)
bash "$(dirname "$0")/verify-macos-dmg.sh" "$root/$name" 0.10.7 "$BUILD_NUMBER"
mkdir "$mount_dir"
for attempt in {1..8}; do
  if attach_output=$(LC_ALL=C hdiutil attach "$root/$name" -readonly -nobrowse -mountpoint "$mount_dir" 2>&1); then
    echo "$attach_output"
    break
  fi
  echo "$attach_output" >&2
  if [[ "$attempt" -eq 8 || ("$attach_output" != *"Resource busy"* && "$attach_output" != *"Resource temporarily unavailable"*) ]]; then
    exit 1
  fi
  sleep 5
done
test "$(readlink "$mount_dir/Applications")" = /Applications
installed=true
ditto "$mount_dir/Actrium.app" "$mount_dir/Applications/Actrium.app"
hdiutil detach "$mount_dir"
echo "Copied Actrium.app through the DMG's Applications link and ejected the image"

cat >"$root/window.swift" <<'SWIFT'
import AppKit

let path = "/Applications/Actrium.app"
guard let app = NSWorkspace.shared.runningApplications.first(where: { $0.bundleURL?.path == path }),
      app.isFinishedLaunching,
      let windows = CGWindowListCopyWindowInfo(.optionOnScreenOnly, kCGNullWindowID) as? [[String: Any]],
      let window = windows.first(where: { window in
          guard (window[kCGWindowOwnerPID as String] as? Int32) == app.processIdentifier,
                (window[kCGWindowLayer as String] as? Int) == 0,
                let bounds = window[kCGWindowBounds as String] as? [String: Double]
          else { return false }
          return (bounds["Width"] ?? 0) >= 300 && (bounds["Height"] ?? 0) >= 200
      }),
      let id = window[kCGWindowNumber as String] as? Int
else { exit(1) }
print("\(app.processIdentifier) \(id)")
SWIFT
xcrun swiftc "$root/window.swift" -o "$root/window"

show_logs() {
  /usr/bin/log show --last 3m --style compact --predicate 'process == "Actrium" || process == "ActriumRenderer"' >"$root/launch.log" 2>&1 || true
}

await_window() {
  local window
  for _ in {1..30}; do
    if window=$("$root/window"); then
      printf '%s\n' "$window"
      return
    fi
    sleep 2
  done
  echo "Actrium did not create a visible browser window" >&2
  show_logs
  tail -n 100 "$root/launch.log" >&2
  return 1
}

capture_window() {
  local id=$1 file=$2
  local screenshots="${RUNNER_TEMP:-/tmp}/actrium-smoke-images"
  mkdir -p "$screenshots"
  if ! screencapture -x -l "$id" "$screenshots/$file.png"; then
    echo "Window screenshot unavailable: $file"
  fi
}

open -a "$app"
window=$(await_window)
read -r app_pid window_id <<<"$window"
echo "Normal launch created a visible browser window (pid=$app_pid)"
sleep 3
capture_window "$window_id" start-page
kill -TERM "$app_pid"
for _ in {1..10}; do
  if ! kill -0 "$app_pid" 2>/dev/null; then break; fi
  sleep 1
done
if kill -0 "$app_pid" 2>/dev/null; then
  echo "Actrium did not exit after the first launch"
  exit 1
fi

python3 - "$root" <<'PY' &
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import secrets
import sys

root = Path(sys.argv[1])
callback = "/js-ran-" + secrets.token_hex(12)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            body = f"""<!doctype html><meta charset="utf-8">
                <title>Actrium smoke test</title><h1>Actrium smoke test</h1>
                <script>addEventListener('load', () => fetch('{callback}'));</script>
            """.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == callback and "AppleWebKit" in self.headers.get("User-Agent", ""):
            self.send_response(204)
            self.end_headers()
            (root / "javascript-ok").write_text(self.headers["User-Agent"])
        else:
            self.send_error(404)

with HTTPServer(("127.0.0.1", 0), Handler) as server:
    (root / "port").write_text(str(server.server_port))
    server.serve_forever()
PY
server_pid=$!
for _ in {1..10}; do
  if [[ -s "$root/port" ]]; then break; fi
  sleep 1
done
open -a "$app" --args --url "http://127.0.0.1:$(cat "$root/port")/"
window=$(await_window)
read -r app_pid window_id <<<"$window"
for _ in {1..30}; do
  if [[ -s "$root/javascript-ok" ]]; then break; fi
  if ! kill -0 "$app_pid" 2>/dev/null; then break; fi
  sleep 2
done
capture_window "$window_id" web-page
if [[ ! -s "$root/javascript-ok" ]]; then
  echo "WebKit did not run the test page's JavaScript"
  show_logs
  tail -n 100 "$root/launch.log"
  exit 1
fi
sleep 5
test "$("$root/window")" = "$window"
echo "Installed Actrium loaded the local HTTP page and ran its JavaScript"
cat "$root/javascript-ok"
echo
