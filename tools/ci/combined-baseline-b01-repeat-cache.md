# Baseline b01 repeat-cache run: successful, mixed caches and external overlap

Run: https://github.com/kaito-harry/actrium/actions/runs/43220724283
Commit: 2ba1410cbf7ba2671f1634ab4728729a53228e1a, empty commit on the exact same experiment tree as cold baseline/candidate.
Branch: experiment/ci15-combined-baseline-b01 (same cache namespace as cold baseline).
Ref update request: 12:44:39.633–12:44:46.548 UTC. Workflow created 12:44:48.

## Outcome and elapsed times

All 27 expanded jobs accounted for: 26 success, only original C# ARM signal-only skipped. Independent complete confirms all full domains, determine and MSRV success. No workflow-level retry. A nextest automatic test retry occurred, detailed below.

- Web ready 12:50:09: 5m21.
- Original Gate success 13:08:54: 24m06.
- MSRV complete 13:11:30: 26m42.
- Independent complete 13:11:37: 26m49.
- Workflow complete/update 13:11:38: 26m50.

Elapsed is from workflow creation, not an invented exact push timestamp. Package E2E was the original Gate's last dependency, MSRV was the full-workflow last dependency.

## Known confound: external concurrent run

Coordinator verified another independent ChatGPT workflow, native-c02 run43220491524, created12:43:17, overlapped this run. No change or cancellation was made to that independent work. Queue durations here include MSRV257s, Kotlin Binding241s, rest218s, Rust195s, realtime145s, Package E2E144s. This sample remains a real observation, but is not a clean isolated hot-cache causal comparison. Keep it labeled; do not silently discard cache misses or queues.

## Same-key Web cache miss verified

Cold baseline logged saving the following complete key at11:59:16.253:

`experiment/ci15-combined-baseline-b01-cli-web-runtime-v5-rust1.99.0-wp0.15.0-pc29.3-d76141b61155a01b16f12c40f083e1d6344cf793171e368cbffca75cb45d4273`

This repeat run logged `Cache not found` for exactly that key at12:45:16.473, then saved it again at12:50:06.953. Branch, namespace and source hash were unchanged. The cold output save did occur; the repeated ready-cache miss is real, not a new key. Root cause of disappearance/eviction is not established by these logs. Coordinator separately observed repository cache capacity pressure, but no direct eviction trace was available.

Actual hit mix:
- true: Web and WebRTC Swatinem, Kotlin codegen Swatinem and Kotlin Gradle build outputs.
- miss: Web output, Swift UniFFI, npm/pip/Gradle dependency caches, most other Swatinem caches.
- Compiler cache statistics retained per job in JSON. A label alone does not establish warm behavior.

## Test flake preserved

Rest summary: 3804 passed, 1 flaky, 2 leaky, 74 skipped.
`loran-server::relay_only regular_launcher_serves_static_relay_without_database_alone_or_with_ice` first failed at13:06:48 with panic at `crates/loran-server/tests/relay_only.rs:320:60`: unwrap of `Protocol(ResetWithoutClosingHandshake)`. It passed on attempt2/3 under the unchanged existing nextest retry configuration. This is an original test/product path failure, not the experimental partition/space harness. Its underlying cause has not been established. Count workflow first-attempt success separately from test-level no-retry success.

Realtime:195/195 passed with no reported retry. Full-domain verification succeeded. This observation does not validate a 15-minute P90, and no further run was started by the monitor.

Detailed metadata, cache keys, queue durations, compiler stats and retry/error lines: `combined-baseline-b01-repeat-cache.json`.
