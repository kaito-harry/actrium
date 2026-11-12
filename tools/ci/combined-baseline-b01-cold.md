# Combined baseline b01 cold: full run succeeded

Run: https://github.com/kaito-harry/actrium/actions/runs/43212875382
Commit: 754a8c450f49c98f08c8c9935dd0cd1812681cba
Branch: experiment/ci15-combined-baseline-b01
First attempt, no workflow rerun. Monitor was read-only.

## Times

Workflow created 2026-11-12 11:52:28 UTC. This is enqueue/creation time, not verified push timestamp; parent separately records ref-update bounds.

- Web Runtime ready: 11:59:18, +6m50.
- Original Gate success: 12:18:26, +25m58.
- MSRV success: 12:20:56, 2m30 after Gate.
- Independent full-coverage complete success: 12:21:01, +28m33.
- Workflow completed/updated: 12:21:02, +28m34.

Full-mode target outputs confirmed true in determine logs. All 27 expanded jobs are present; 26 succeeded and only C# ARM64 signal-only was skipped as originally intended. Independent complete job succeeded, including determine and MSRV. Kotlin's four jobs, Python codegen/workload, TypeScript bindings/workload, C/Go, C# default fixture, Swift and all Rust paths actually ran. No experimental harness, product or platform failure detected. This scope still excludes CodeQL and optional full platform matrices.

## Main job durations

| Job | Time |
|---|---:|
| MSRV 1.95 | 21m35 |
| Rust | 18m59 |
| Package Runtime E2E | 18m07 |
| realtime | 16m45 |
| WebRTC | 14m30 |
| Swift | 13m45 |
| rest | 13m43 |
| Kotlin Android Native Build | 10m27 |

Rust was original Gate's final dependency. MSRV was full-workflow final dependency: its locked build took 15m, with installer/preparation costs adding approximately 6m. Both begin only after Web Runtime, which itself spent 1m46 on broad cleanup and 1m48 installing wasm-pack.

## Coverage/cache observations

- realtime: 195 tests passed, 1779 skipped by original filter, actual test duration 299.712s; no RETRY/FLAKY lines.
- rest: 3804 tests passed (2 reported leaky), 74 skipped, actual test duration 201.112s; no RETRY/FLAKY lines.
- Package cache logs explicitly show namespace-specific misses for npm/pip/Gradle and Web output. Swatinem reports false cache hits, including reusable Kotlin/C#. actions/cache returns an empty hit output on miss, corroborated by 'Cache not found' logs, not a hit.
- Cold cohort did have legitimate cross-job sccache reuse while the workflow ran. For example realtime had 628 Rust hits. Do not label each job individually cache-empty.
- sccache reported substantial cache_write_errors (Web 10, rest 692, realtime 740, Rust 1149, MSRV 693). These did not fail the workflow. Their cause is not established; simultaneous immutable-cache writers may contribute, but do not assume that. Hot-run effectiveness must be read from actual Rust hits/misses and errors, not namespace alone.

Raw job/step metadata, cache reports, compiler-cache JSON and test summaries are retained in `combined-baseline-b01-cold.json`. This is one baseline observation, not a P90 or confirmation of the 15-minute target.
