# Actrium for macOS

This directory contains the native macOS browser host, its view service,
shared IPC sources, Xcode projects, and platform-specific tests.

Shared React Native runtime code lives in `../packages/actrium`; Keel lives in
`../packages/keel`; shared Apple packages live in
`../packages/actrium-platform/apple`. The Xcode project and bundle scripts
reference those monorepo paths directly.

From the repository root, compile an unsigned debug build for verification:

```sh
npm run verify:macos
```

For an interactive build that uses Realm credentials, keep a fixed signing
identity across rebuilds:

```sh
IDENTITY_NAME="Apple Development: Your Name (TEAMID)" npm run build:macos
```

The local build and DMG packager both use `scripts/sign-app.sh`: nested
libraries and frameworks, the renderer helper, then the main app. Both process
entitlement files are preserved, and signing must pass
`codesign --verify --deep --strict`. `KEYCHAIN_PATH` can select the keychain
containing the signing identity. Local builds disable secure timestamps;
distribution builds retain them.

`verify:macos` only checks compilation. Opening its unsigned build can cause
repeated Realm Keychain prompts after recompilation: ad hoc code identities
are tied to a single binary. The signed build command rejects missing or ad
hoc identities rather than silently producing an interactive unsigned app.
Changing from an old ad hoc build to a signed build can still require one-time
authorization of the existing Realm credential.

CI Gate selects the macOS Host checks for changes under `macos/` and the
shared build entry points. `bash macos/scripts/test-host.sh` runs the native
focus/blur/resize regression and signs disposable nested bundle fixtures.
These checks do not read Realm private keys or require signing certificates.

Runtime bundles can be generated independently with
`npm run bundle:macos:system`.

## Package a DMG

`scripts/package-dmg.sh` builds a Release app and packages it into a DMG.
Without signing credentials it produces an unsigned DMG:

```sh
# From the repository root
npm run package:macos:dmg -- --unsigned
```

To sign and notarize, provide a Developer ID identity and notarization
credentials (see `scripts/package-dmg.sh --help`):

```sh
IDENTITY_NAME="Developer ID Application: Example (TEAMID)" \
USER_NAME="apple-id@example.com" \
TEAM_ID="TEAMID" \
ACCOUNT_PASSWORD="app-specific-password" \
  macos/scripts/package-dmg.sh
```

Artifacts are written to `macos/dist/` (`Actrium_<tag>.dmg`).

## Publish a browser snapshot from a fork

Enable Actions in your fork, then open **Actions → Release Actrium macOS →
Run workflow** and keep the default `snapshot` mode. The workflow must be on
the fork's default branch before GitHub displays the manual entry point.
No Apple credentials or extra GitHub secrets are required. Repository policy
must allow the workflow's `GITHUB_TOKEN` to write contents and releases.

The workflow resolves **your repository's `main`** once and checks out that
full SHA, even when another workflow branch is selected. Its tag is
`actrium-` followed by the first **12** hexadecimal characters of that SHA,
for example `actrium-a1b2c3d4e5f6`. It builds an unsigned Release app on an
Apple Silicon macOS 26 runner with Xcode 26.1, including the minified production
JavaScript bundle and local ActriumCore/ActriumVault XCFrameworks.

Only after packaging and image verification succeed does it create the tag
and a GitHub **Pre-release**, explicitly excluding it from Latest. Repeating
the same commit reuses both and replaces only these two attachments:

- `Actrium_<tag>_macos-arm64_unsigned.dmg`
- `Actrium_<tag>_macos-arm64_unsigned.dmg.sha256`

A new `main` commit produces a new snapshot. A tag that points to another
commit causes a clear failure and is never moved. Builds for the same tag
serialize across the manual workflow and Release Train. An upload failure
leaves the tag and release in place so a rerun can recover.

Snapshot app versions use the numeric `MAJOR.MINOR.PATCH` part of the pinned
source's Cargo workspace version; build numbers use the caller's Actions run
number. Release notes record the full SHA, UTC build time, version, build
link, and platform requirements. Reruns update the managed build-information
section while retaining other snapshot notes.

For a missing or damaged attachment, select `existing-tag` and enter a tag
whose GitHub Release already exists. Supported tags are `actrium-<12 hex
characters>` and `vX.Y.Z` (optionally with a prerelease suffix, such as
`v0.10.7-rc.1`; the `v` is optional). Both lightweight and annotated tags are
resolved to a pinned commit. Versioned releases use the tag's numeric version
and keep their existing notes, prerelease status, and Latest status. This mode
never creates a missing tag or release.

Both paths call `.github/workflows/_actrium-macos-release.yml`; they do not
invoke SDK, CLI, or Loran publishing. Release Train calls that same reusable
workflow after creating its release and includes the DMG result in its
consolidated report. A train `dry_run` builds and verifies the DMG, saves it
as an Actions artifact, and performs no tag or release writes. Actions also
retain build provenance (`actrium-build.json`) and the packaging log.

### Install and verify an unsigned snapshot

These first-release images support **Apple Silicon and macOS 26.1 or later**.
They have no Developer ID signature or Apple notarization. macOS Gatekeeper
may refuse to open them, and organization policy may prevent an override.
After verifying a download you trust, mount the DMG, drag `Actrium.app` onto
the `Applications` link, and use **System Settings → Privacy & Security →
Open Anyway** if macOS offers it. Do not disable Gatekeeper globally.

Download both attachments into the same directory and check integrity:

```sh
shasum -a 256 -c Actrium_<tag>_macos-arm64_unsigned.dmg.sha256
```

The workflow mounts the final read-only image and verifies the app and
`/Applications` link, app and renderer versions/build numbers, arm64
executables, minimum macOS version, and the bundled JavaScript before writing
the SHA-256 file. A checksum verifies download integrity, not publisher
identity. Unsigned snapshots can repeatedly prompt for Realm Keychain access
after replacement; use a local build with a stable signing identity for
interactive Realm credentials as described above.
