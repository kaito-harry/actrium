# Phase 3: WebRTC and UniFFI experiment (2026-11-12)

Run: https://github.com/kaito-harry/actrium/actions/runs/43188883243

Only fork branch `experiment/ci15-phase3-audit-20261112` changed. Workflow commit `30d7b32ca2d7734408620338d2f5a777f23035cb`; all consumer checkouts pinned to source `9cf6a9e37eb7e51b879d3ceb39a2bf01af19dec9`. No upstream/main/existing PR or MSRV changes. No Rust compilation caches in these isolated jobs. Explicit Bash defaults preserve pipefail for tee pipelines. This is one controlled pair, not a P90 result.

## WebRTC

A job https://github.com/kaito-harry/actrium/actions/runs/43188883243/job/131082872221
B job https://github.com/kaito-harry/actrium/actions/runs/43188883243/job/131082871798

| Seconds | A check+Clippy+nextest | B Clippy+nextest |
|---|---:|---:|
| Check | 171 | omitted |
| Clippy | 61 | 179 |
| nextest compilation+tests | 315 | 344 |
| Measured command total | 547 | 523 |
| Linux preparation | 49 | 83 |
| Whole job | 624 | 635 |

Both passed. Cargo JSON compiler-artifact records, normalized to package ID, target name/kind/crate types, features and profile, contain exactly the same 740 unique units in A check, A Clippy and B Clippy. Normalized individual PASS names match exactly: 419/419, zero missing/extra, 1426 skipped in each original filter. Actual tests took 22.489s/22.909s.

Removing check is supported as a coverage-preserving simplification for this precise configuration. It saved only 24s in command totals here, and did not improve whole-job time (B 11s slower). Do not subtract all 171s of check or promise a 3min benefit. Test compilation and hosted-runner preparation variance dominate this sample. Build-unit identity is not a universal guarantee for future target/features/config changes.

## Swift UniFFI artifact

A source-install baseline https://github.com/kaito-harry/actrium/actions/runs/43188883243/job/131082872192
Producer retry https://github.com/kaito-harry/actrium/actions/runs/43188883243/job/131092171679
B consumer https://github.com/kaito-harry/actrium/actions/runs/43188883243/job/131094397397
Artifact https://github.com/kaito-harry/actrium/actions/runs/43188883243/artifacts/13930583174

Producer compiled official crates.io UniFFI 0.31.1 using cargo install --locked, Rust 1.99.0, macOS ARM64. It uploaded binary, SHA256SUMS, VERSION, ARCH and RUSTC manifest. Consumer verified content hash, architecture and full rustc identity, restored execute mode, executed --version and compared the result before using it. This is integrity checking of a trusted same-run artifact, not cryptographic publisher signing. All original Swift lint/header/typecheck, fresh same-source XCFramework/bindings generation, package build, mock-loran E2E and codegen build remained. Both A and B passed all 35 Swift Testing tests in 3 suites (the separate XCTest compatibility harness reports zero tests).

Measured:
- A source tool install: 103s; whole A job: 362s (6m02).
- Producer cold job: 261s (4m21), including 241s compile step and ~2s upload; artifact 2,947,376 bytes.
- B download plus manifest verification: 1s by step timestamps.
- B whole job: 639s (10m39). Its unrelated XCFramework step was 320s versus A 122s, so different runner performance makes whole-job subtraction invalid.
- Successful cold producer start 09:27:41 to B finish 09:44:00: 979s (16m19), including 79s gap between producer completion and B start.
- Original workflow creation 09:08:57 to final completion 09:44:00: 2103s (35m03), including initial platform failure, retry and queues.

First attempt producer never acquired a runner, had no steps, and was cancelled after 15m02. Public job annotations explicitly say "The job was not acquired by Runner of type hosted even after multiple attempts", "Internal server error" (correlation 2dcb6858-de88-44dc-975a-848ae42ca89c), and macOS ARM64 capacity constraints. Only that producer was retried once; its dependent consumer then ran. Successful A/WebRTC nodes in attempt 2 retain original timestamps and were not rerun. This is platform acquisition failure, not a product test failure, but cannot be omitted from user-visible elapsed-time/retry reporting.

Conclusion: ready UniFFI artifact distribution works and changes tool acquisition to about a second; building it anew in the PR critical path did not establish a speed win. To exploit reusable tools, use a separately produced, immutable version/architecture/toolchain artifact or cache with verified provenance and measure cold fallback honestly. This experiment does not validate a 15-minute end-to-end or P90 target.
