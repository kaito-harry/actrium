# CI15: exact-SHA E2E fixture reuse experiment

## Scope and method

Fork-only branch: `experiment/ci15-artifact-20261112`. Original source is main `cd2b600cc25cea0bf399fc1fb6ebd94a23ff586f`, experimental base `9cf6a9e37eb7e51b879d3ceb39a2bf01af19dec9`. No upstream or existing PR was changed.

The experiment is a bounded three-job chain, not a complete CI Gate run: Web Runtime -> CLI/Loran fixture producer -> sequential four-scenario consumer. All jobs use `ubuntu-24.04` GitHub-hosted runners. E2E producer and consumer have no sccache or Rust target cache; Web has its own isolated cache namespace. Do not treat this as a P90 estimate or claim full-PR latency from it.

Producer uses the original default-feature `cargo build --manifest-path crates/actr-cli/Cargo.toml --bin actr` and `cargo test --no-run --message-format=json --manifest-path crates/loran-server/Cargo.toml --bin loran`, with the original separate target directories. It packages the CLI and test-only Loran fixture in a permission-preserving tar, with a manifest matching exact checkout/GitHub SHA, Rust verbose version, host target, OS/arch, Cargo.lock, declared feature/build configuration, Web asset hashes, executable permissions and binary SHA256. Consumer independently verifies these before use. Loran's test list must contain `package_runtime_fixture`.

The optional `ACTR_CLI_BIN` input leaves default build behavior unchanged and explicitly rejects the v2-component backend, which needs different CLI features. Existing `LORAN_BIN` support is reused. The consumer retains isolation/HTTPS checks and all four original scenarios: runtime legacy, runtime provider HTTPS, runtime external HTTPS, and key rotation legacy. It does not use `REALM_STAGE=profile`, which would skip runtime Echo.

Local checks: all workflow shell steps and modified run.sh pass `bash -n`; manifest Python compiles; a fixture test verifies successful provenance validation and rejection after binary tampering.

## Initial run: harness failure, not a product regression

Run: https://github.com/kaito-harry/actrium/actions/runs/43188976534
Commit: `e339df9a3bd955299d27995c18bdf7b109eb6c23`

- Created 09:09:35 UTC, Web finished 09:13:54 (4:19 from creation; job 4:15).
- Producer 09:13:57–09:21:08 (7:11). Cleanup 2:09; CLI cold build 2:04; Loran cold build 2:00; tar/manifest approximately 22 seconds.
- Archive: 211,017,030 bytes compressed, directory 914,818,389 bytes. Upload step 3 seconds.
- Consumer downloaded in 2 seconds and successfully verified provenance and binary hashes; extraction/verification step reached that point within 7 seconds.
- The added `actr --version` smoke command failed because this CLI disables its version flag (`crates/actr-cli/src/cli.rs:47`). This was my experiment error. All four scenarios were skipped, so this run does **not** establish functional reuse.

Correction changes only the smoke invocation to supported `actr --help`. It rebuilds fixtures for the new SHA rather than accepting prior-SHA artifacts.

## Corrected run

Run: https://github.com/kaito-harry/actrium/actions/runs/43191443512
Commit: `0710167e96af85ec8cdcf473c387fdb6eae5f188`

**Success.** Created 09:26:12 UTC, finished 09:43:12: **17:00 elapsed**. Web cache was warm; E2E compilation remained uncached. This is not a complete CI Gate run and does not prove a speedup over a controlled baseline.

| Component | Measured time |
|---|---:|
| Web job (cache hit) | 0:12 |
| Producer job | 7:54 |
| CLI cold compilation within producer | 2:50 |
| Loran fixture cold compilation within producer | 2:58 |
| Manifest/tar after compilation | about 0:31 |
| Fixture upload | 0:05 |
| Consumer job | 8:41 |
| Consumer cleanup alone | 1:49 |
| Fixture download | 0:05 |
| Extract, manifest/hash verification, CLI/fixture probes | 0:05 |
| Runtime legacy scenario | 3:17 |
| Runtime provider + external scenarios | 2:44 |
| Key rotation legacy scenario | 0:07 |

Compressed tar: 211,016,750 bytes. The consumer verified the exact SHA, toolchain/host, lockfile, feature declarations, Web assets, binary hashes and executable bits. It logged `Using caller-provided actr CLI` and `Using caller-provided loran test fixture` for each of all four scenarios, followed by each scenario's success message. Publisher-key isolation and HTTPS/certificate rejection checks also passed. No CLI executable or Loran fixture rebuild took place in the consumer.

**A third build remains:** provider setup calls `cargo test -p actr-cli --lib --no-run` in `tests/e2e/actr/package-runtime-echo/lib/realm-scenarios.sh:72` to produce `realm_runtime_join_fixture`. It took **1:55** on the consumer. The subsequent external scenario reused that local build (0.20 seconds). This is distinct from the two transferred binaries; the experiment does not claim that all fixture/guest compilation was removed.

## Conclusions and next decision

1. Exact-SHA CLI + Loran fixture transfer is functionally validated on separate runners, including all original scenarios and security checks. Transfer itself was small relative to compilation: 5 seconds upload + 5 seconds download + 5 seconds extraction/validation, plus approximately 31 seconds packaging.
2. Moving builds into a serial producer is not by itself an end-to-end optimization. The producer consumed 7:54 and the consumer 8:41; added runner cleanup/setup is visible. Do not advertise only the consumer time as the E2E critical path.
3. A fan-out experiment must account for duplicated guest compilation and the separate CLI lib fixture, which currently reuse target directories in the sequential job. One useful next candidate is also publishing the exact same-build CLI lib fixture, with explicit input/provenance checks, before comparing sequential versus per-scenario runners.
4. Keep scenario isolation: default ports are fixed, so parallel scenarios should use independent runners rather than backgrounding the current shell script on one machine. Preserve provider/external HTTPS, legacy, key rotation, and runtime Echo rather than substituting profile-only checks.
5. The initial unsupported smoke-command error is preserved above. It is a harness failure, not evidence of a product failure or successful functional reuse. One corrected successful run is not a first-pass reliability estimate, P90 estimate, or confirmation of the 15-minute full-PR goal.

Machine-readable step timings: `artifact-reuse-metrics.json`.

