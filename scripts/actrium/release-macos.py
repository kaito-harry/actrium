#!/usr/bin/env python3
"""Resolve, validate, and publish browser-only macOS releases in the current repo."""

from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import tomllib
from urllib.parse import quote


# Generate eight-character tags; retain older twelve-character tags for backfills.
SNAPSHOT = re.compile(r"actrium-([0-9a-f]{8}(?:[0-9a-f]{4})?)")
VERSION = re.compile(r"v?([0-9]+\.[0-9]+\.[0-9]+)(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?")
NOTES_START = "<!-- actrium-macos-build:start -->"
NOTES_END = "<!-- actrium-macos-build:end -->"


def gh(*args: str, missing_ok: bool = False):
    result = subprocess.run(["gh", *args], capture_output=True, text=True)
    if result.returncode:
        if missing_ok and "(HTTP 404)" in result.stderr:
            return None
        raise RuntimeError(result.stderr.strip() or "GitHub operation failed")
    if args[0] == "api":
        return json.loads(result.stdout) if result.stdout.strip() else None
    return result.stdout.strip()


def api(path: str, *args: str, missing_ok: bool = False):
    return gh("api", f"repos/{os.environ['GITHUB_REPOSITORY']}/{path}", *args, missing_ok=missing_ok)


def tag_commit(tag: str) -> str | None:
    ref = api(f"git/ref/tags/{quote(tag, safe='')}", missing_ok=True)
    if ref is None:
        return None
    obj = ref["object"]
    for _ in range(10):
        if obj["type"] == "commit":
            return obj["sha"]
        if obj["type"] != "tag":
            break
        obj = api(f"git/tags/{obj['sha']}")["object"]
    raise ValueError(f"Tag {tag} does not resolve to a commit")


def release_for(tag: str):
    return api(f"releases/tags/{quote(tag, safe='')}", missing_ok=True)


def numeric_version(version: str) -> str:
    match = VERSION.fullmatch(version)
    if match is None:
        raise ValueError(f"Expected a semantic version, got {version!r}")
    return match[1]


def check_tag(tag: str, sha: str) -> bool:
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("source_sha must be a full 40-character commit SHA")
    if match := SNAPSHOT.fullmatch(tag):
        if not sha.startswith(match[1]):
            raise ValueError(f"Snapshot tag {tag} does not match source commit {sha}")
        return True
    if not VERSION.fullmatch(tag):
        raise ValueError("Expected actrium-<8 hex characters> (or a legacy 12-character snapshot) or a vX.Y.Z[-prerelease] tag")
    return False


def check_destination(tag: str, sha: str, create_snapshot: bool):
    snapshot = check_tag(tag, sha)
    if create_snapshot and not snapshot:
        raise ValueError("Only snapshot mode can create a new tag or release")
    actual = tag_commit(tag)
    if actual is not None and actual != sha:
        raise ValueError(f"Tag {tag} points to {actual}, expected {sha}; refusing to move it")
    release = release_for(tag)
    if not create_snapshot and (actual is None or release is None):
        raise ValueError(f"Both tag {tag} and its GitHub Release must already exist")
    if release is not None:
        if release["draft"]:
            raise ValueError(f"Release {tag} is a draft; publish it before replacing assets")
        if snapshot and not release["prerelease"]:
            raise ValueError(f"Snapshot release {tag} must already be a Pre-release")
    return actual, release


def resolve(args):
    if args.mode == "snapshot":
        sha = api("commits/main")["sha"]
        tag = f"actrium-{sha[:8]}"
    else:
        tag = args.tag
        if not (SNAPSHOT.fullmatch(tag) or VERSION.fullmatch(tag)):
            raise ValueError("existing-tag requires actrium-<8 hex characters>, a legacy 12-character snapshot, or vX.Y.Z[-prerelease]")
        sha = tag_commit(tag)
        if sha is None:
            raise ValueError(f"Existing tag {tag!r} was not found")
    snapshot = check_tag(tag, sha)
    check_destination(tag, sha, args.mode == "snapshot")
    if snapshot:
        content = api(f"contents/Cargo.toml?ref={sha}")
        cargo = tomllib.loads(base64.b64decode(content["content"]).decode())
        version = numeric_version(cargo["workspace"]["package"]["version"])
    else:
        version = numeric_version(tag)
    outputs = f"tag={tag}\nsource_sha={sha}\napp_version={version}\n"
    print(outputs, end="")
    with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
        output.write(outputs)


def context():
    tag, sha, version = (os.environ[name] for name in ("RELEASE_TAG", "RELEASE_SHA", "APP_VERSION"))
    check_tag(tag, sha)
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        raise ValueError("app_version must be numeric MAJOR.MINOR.PATCH")
    return tag, sha, version


def validate(args):
    tag, sha, version = context()
    actual = subprocess.check_output(["git", "-C", str(args.source), "rev-parse", "HEAD"], text=True).strip()
    if actual != sha:
        raise ValueError(f"Checked out {actual}, expected {sha}")
    if SNAPSHOT.fullmatch(tag):
        cargo = tomllib.loads((args.source / "Cargo.toml").read_text())
        expected = numeric_version(cargo["workspace"]["package"]["version"])
    else:
        expected = numeric_version(tag)
    if version != expected:
        raise ValueError(f"Application version {version} does not match {expected}")
    if os.environ["PUBLISH"] == "true":
        check_destination(tag, sha, os.environ["CREATE_SNAPSHOT"] == "true")


def asset_paths(directory: Path, tag: str):
    snapshot = SNAPSHOT.fullmatch(tag)
    suffix = snapshot[1][:8] if snapshot else tag
    dmg = directory / f"Actrium-{suffix}.dmg"
    return dmg, dmg.with_suffix(".dmg.sha256")


def filename(args):
    tag, _, _ = context()
    print(asset_paths(args.assets, tag)[0].name)


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def metadata(args):
    tag, sha, version = context()
    dmg, checksum = asset_paths(args.assets, tag)
    checksum.write_text(f"{digest(dmg)}  {dmg.name}\n")
    repo = os.environ["GITHUB_REPOSITORY"]
    run_url = f"{os.environ['GITHUB_SERVER_URL']}/{repo}/actions/runs/{os.environ['GITHUB_RUN_ID']}"
    info = dict(tag=tag, source_sha=sha, app_version=version,
                build_number=os.environ["BUILD_NUMBER"],
                built_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                run_url=run_url)
    (args.assets / "actrium-build.json").write_text(json.dumps(info, indent=2) + "\n")


def snapshot_notes(info, old_body: str) -> str:
    block = "\n".join([
        NOTES_START,
        "## Actrium macOS snapshot",
        "",
        f"- Source commit: `{info['source_sha']}`",
        f"- Built at (UTC): {info['built_at']}",
        f"- App version: `{info['app_version']}`; build: `{info['build_number']}`",
        "- Requires Apple Silicon (arm64) and macOS 26.1 or later.",
        "- Unsigned and not notarized; Gatekeeper may block installation. See `macos/README.md` for installation limitations.",
        "- Realm credentials require a stable signing identity; unsigned snapshots can prompt repeatedly for Keychain access.",
        f"- Build: {info['run_url']}",
        "- Verify the DMG with its accompanying `.sha256` file.",
        NOTES_END,
    ])
    pattern = re.compile(re.escape(NOTES_START) + r".*?" + re.escape(NOTES_END), re.DOTALL)
    if pattern.search(old_body):
        return pattern.sub(lambda _: block, old_body)
    return (old_body.rstrip() + "\n\n" + block).strip() + "\n"


def publish(args):
    tag, sha, version = context()
    dmg, checksum = asset_paths(args.assets, tag)
    if checksum.read_text() != f"{digest(dmg)}  {dmg.name}\n":
        raise ValueError("DMG checksum mismatch; refusing to publish")
    info = json.loads((args.assets / "actrium-build.json").read_text())
    if (info["tag"], info["source_sha"], info["app_version"]) != (tag, sha, version):
        raise ValueError("Build provenance does not match the requested release")
    create = os.environ["CREATE_SNAPSHOT"] == "true"
    actual, release = check_destination(tag, sha, create)
    if actual is None:
        try:
            api("git/refs", "--method", "POST", "-f", f"ref=refs/tags/{tag}", "-f", f"sha={sha}")
        except RuntimeError:
            # Another publisher may have created the ref; never force-update it.
            if tag_commit(tag) != sha:
                raise
    repo = os.environ["GITHUB_REPOSITORY"]
    if SNAPSHOT.fullmatch(tag):
        with tempfile.TemporaryDirectory() as directory:
            notes = Path(directory) / "notes.md"
            old_body = (release["body"] or "") if release else ""
            notes.write_text(snapshot_notes(info, old_body))
            if release is None:
                try:
                    gh("release", "create", tag, "--repo", repo, "--verify-tag", "--target", sha,
                       "--title", f"Actrium macOS {tag}", "--notes-file", str(notes),
                       "--prerelease", "--latest=false")
                except RuntimeError:
                    # On retry a release may exist even if the response was lost.
                    _, release = check_destination(tag, sha, False)
                    if release is None:
                        raise
            else:
                gh("release", "edit", tag, "--repo", repo, "--notes-file", str(notes),
                   "--prerelease", "--latest=false")
    check_destination(tag, sha, False)
    # gh --clobber only replaces these exact names and keeps all other assets.
    gh("release", "upload", tag, str(dmg), str(checksum), "--repo", repo, "--clobber")


def report(args):
    tag, sha, version = context()
    publish_enabled = os.environ["PUBLISH"] == "true"
    success = os.environ["BUILD_RESULT"] == "success" and (
        not publish_enabled or os.environ["PUBLISH_RESULT"] == "success")
    status = "success" if success else "failure"
    mode = "publish" if publish_enabled else "dry_run"
    report_version = os.environ["REPORT_VERSION"]
    numeric_version(report_version)
    url = f"{os.environ['GITHUB_SERVER_URL']}/{os.environ['GITHUB_REPOSITORY']}/releases/tag/{tag}"
    if not publish_enabled:
        url = f"{os.environ['GITHUB_SERVER_URL']}/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ['GITHUB_RUN_ID']}"
    args.assets.mkdir(parents=True, exist_ok=True)
    state = args.assets / f"release-train-v{report_version}.publish-actrium-macos.state.tsv"
    state.write_text("\t".join(["Actrium macOS arm64 DMG", "publish-actrium-macos", "binary",
                               version, status, mode, url, sha]) + "\n")
    with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a") as summary:
        summary.write(f"Actrium macOS `{tag}`: **{status}** ({mode}). [Result]({url})\n\nSource: `{sha}`\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["resolve", "validate", "filename", "metadata", "publish", "report"])
    parser.add_argument("--mode", choices=["snapshot", "existing-tag"], default="snapshot")
    parser.add_argument("--tag", default="")
    parser.add_argument("--source", type=Path, default=Path("."))
    parser.add_argument("--assets", type=Path, default=Path("artifacts"))
    args = parser.parse_args()
    globals()[args.stage](args)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        sys.exit(f"::error::{error}")
