# Combined candidate c01 cold: full run succeeded, not yet 15 minutes

Run: https://github.com/kaito-harry/actrium/actions/runs/43217496737
Commit: 754a8c450f49c98f08c8c9935dd0cd1812681cba (same as baseline)
Branch: experiment/ci15-combined-candidate-c01
First attempt, no workflow rerun. Monitoring was read-only.

Ref-update request bounds supplied by coordinator: 12:23:40.661–12:23:45.923 UTC. Workflow created 12:23:47. All following elapsed values use workflow created_at, not claimed exact push time.

| Milestone | UTC | Elapsed | Baseline cold |
|---|---|---:|---:|
| Web ready | 12:26:14 | 2m27 | 6m50 |
| Original Gate success | 12:41:25 | 17m38 | 25m58 |
| MSRV success | 12:42:54 | 19m07 | 28m28 |
| Independent full complete | 12:43:00 | 19m13 | 28m33 |
| Workflow complete/update | 12:43:00 | 19m13 | 28m34 |

All 28 expanded jobs are present: 27 success, only original C# ARM signal-only skipped. Independent full-coverage check passed. Kotlin/Python/C-Go and other full domains actually executed. No product, harness or platform failure detected. Not CodeQL/optional all-platform coverage.

Single-pair change: Gate -8m20 (32.1%); whole workflow -9m21 (32.7%). These observations are not a P90 estimate, nor a guarantee that individual changes caused each job difference. Candidate still misses the <=15m target.

## Candidate behavior verified

- Web output cache miss and Swatinem false; free-space guard measured 92,024,786,944 bytes (>10GiB), skipped broad cleanup; shared prebuilt tool installation succeeded. Web compile took 1m37. Output ready in 2m27 meets the 3m budget in this sample.
- Candidate shared tools ran in the intended jobs; source-install alternatives were skipped.
- Standalone RFC-0400 invocation skipped in Rust. Rest assertion logged 'RFC-0400 timer selected in actr-hyper'; all 3804 rest tests passed (2 leaky), 74 skipped, actual tests 235.463s.
- Both realtime inventories asserted exact whole=195, heavy=24, network=171 partition. Build-heavy passed 24 tests, network passed 171, without RETRY/FLAKY lines. Exact union/disjoint check remained active.
- WebRTC check skipped, original Clippy and nextest succeeded.
- No E2E sccache, new serial producer, Swift or MSRV compatibility change.

## Remaining bottlenecks

MSRV job 16m37 was the final whole-workflow dependency. Rest job 15m02 was the final Gate dependency. Package E2E took 13m01 and completed 15m31 after workflow creation. Network 12m56, build-heavy 11m08, Swift 14m08, WebRTC 10m12, Rust 8m47. Thus further work must address remaining tails, not simply assume the improvements add to a 15-minute P90.

## Cache observations

Namespace isolation worked; package/cache reports are retained in JSON. Shared compiler cache reuse within this first cold cohort occurred and is legitimate. Actual sccache statistics and write errors are included per job. Do not characterize every job as zero-cache or infer reliable warm behavior merely from the branch label. No hypothesis about write-error causes has been proven.

Detailed metadata, step timings, compiler-cache JSON, cache-miss messages and inventory/test summaries: `combined-candidate-c01-cold.json`.
