#!/usr/bin/env bash
# Verify the image that will be uploaded, including its nested renderer.
set -euo pipefail

DMG_PATH=${1:?Usage: verify-macos-dmg.sh DMG APP_VERSION BUILD_NUMBER}
APP_VERSION=${2:?Missing app version}
BUILD_NUMBER=${3:?Missing build number}
MOUNT_DIR=$(mktemp -d "${TMPDIR:-/tmp}/actrium-dmg.XXXXXX")
cleanup() {
  hdiutil detach "$MOUNT_DIR" >/dev/null 2>&1 || true
  rmdir "$MOUNT_DIR" 2>/dev/null || true
}
trap cleanup EXIT
hdiutil verify "$DMG_PATH"
hdiutil attach "$DMG_PATH" -readonly -nobrowse -mountpoint "$MOUNT_DIR"
test -d "$MOUNT_DIR/Actrium.app"
test -L "$MOUNT_DIR/Applications"
test "$(readlink "$MOUNT_DIR/Applications")" = /Applications

python3 - "$MOUNT_DIR/Actrium.app" "$APP_VERSION" "$BUILD_NUMBER" <<'PY'
import plistlib
from pathlib import Path
import subprocess
import sys

app, version, build = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
bundles = [app, *app.glob('Contents/Helpers/*.app')]
if not any(bundle.name == 'ActriumRenderer.app' for bundle in bundles):
    raise SystemExit('Missing ActriumRenderer.app')
for bundle in bundles:
    with (bundle / 'Contents/Info.plist').open('rb') as stream:
        info = plistlib.load(stream)
    for key, expected in [('CFBundleShortVersionString', version), ('CFBundleVersion', build),
                          ('LSMinimumSystemVersion', '26.1')]:
        if info.get(key) != expected:
            raise SystemExit(f'{bundle.name}: {key}={info.get(key)!r}, expected {expected!r}')
    binary = bundle / 'Contents/MacOS' / info['CFBundleExecutable']
    arch = subprocess.check_output(['lipo', '-archs', str(binary)], text=True).strip()
    if arch != 'arm64':
        raise SystemExit(f'{bundle.name}: expected arm64, got {arch}')
    print(f'Verified {bundle.name}: version={version} build={build} arch={arch} macOS>=26.1')
if not any(path.stat().st_size for path in app.rglob('system.jsbundle')):
    raise SystemExit('Missing production system.jsbundle')
PY
