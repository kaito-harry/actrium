# CI15 batches 2–3: bounded validation (2026-11-12)

## Conclusions
Two isolated batch-2 changes now have positive first-run evidence: skip broad SDK cleanup for Web preparation, and split realtime into build-heavy/network runners. These are individual-job experiments, NOT a combined full-CI/P90 result. Cold E2E sccache did not reproduce the earlier large regression; its reliable warm-cache behavior remains unresolved.

## Web cleanup, same-SHA cold A/B
[Run43185918273](https://github.com/kaito-harry/actrium/actions/runs/43185918273)

| Variant | Job | From workflow creation | Actual Web build | Cleanup |
|---|---:|---:|---:|---:|
| Original |4:15|4:18|1:18|2:26|
| Skip broad cleanup |2:12|2:15|1:36|0|

Both artifacts passed the existing integrity/sync checks. Independent variant cache namespaces; asset cache misses confirmed. Skipping cleanup saved2:03 end-to-end despite slower compilation, meeting3:00 in this sample. Every10-second disk samples in the no-cleanup job showed maximum used64,458,117,120 bytes and minimum free90,419,294,208 bytes (~84.2GiB). This is a sampled high-water mark, not continuous peak telemetry. Measurement covered checkout through artifact upload before post-job cache saves. Runner root reported154,894,188,544 bytes total. Do not generalize to different images, heavy Rust jobs, or promise this free-space margin on every runner. A production change should keep a free-space guard/fallback rather than unconditionally delete cleanup everywhere.

## Cold E2E cache isolation
[Run43184701912](https://github.com/kaito-harry/actrium/actions/runs/43184701912)

Same SHA and same Web artifact; independent runners; no Rust target-cache restore. Existing signing isolation, HTTPS rejection, legacy runtime, provider/external Realms and key rotation checks all passed.

| Variant | Job | Cleanup | Three runtime scenario steps |
|---|---:|---:|---:|
| sccache off |17:06|1:50|14:28|
| sccache on |16:46|1:12|14:55|

Cold Rust cache hits3/misses1799; cache write errors1619. The on job finished20 seconds sooner, but its setup was faster; scenario work was27 seconds slower. This one pair provides no evidence of a major causal regression from sccache. It does not explain away the earlier27:31 cold candidate or prove meaningful cold benefit. First CLI/Loran builds off2:51/3:00, on3:12/3:06. Investigate write failures, repeat paired measurements and alternate order/runners before acceptance.

## Realtime disjoint partition
[Run43184865860](https://github.com/kaito-harry/actrium/actions/runs/43184865860)

| Variant | Job | Compilation | Test wall time | Passed |
|---|---:|---:|---:|---:|
| Whole realtime |17:46|9:57|353.645s|195|
| Build-heavy: rust_echo + dynclib_actor_e2e |14:31|9:22|178.577s|24|
| Network: remaining realtime |12:04|6:30|162.826s|171|

Every runner built the original whole realtime inventory and asserted exact set union, empty intersection, and counts195=24+171 using (binary-id,test-name). Selected tests ran with original features, nextest concurrency and retry policy. The two-runner critical path was14:31 versus17:46 whole, a3:15 observed saving. Test wall-time reduction alone was~2:55. Compilation variance remains material, and this increases runner-minutes. Web preparation preceded these jobs; the split jobs still did NOT satisfy14:30 from push/workflow start. No combined pipeline result has been measured yet.

### #427 failure is not repaired by splitting
Original failure: [job131010462505](https://github.com/Actrium/actrium/actions/runs/43166232123/job/131010462505).
The test was connection_governance_production::production_answerer_repeated_soft_hard_cycles_do_not_accumulate_lanes. After close_lane, waiting for sendable plus a newer pc_generation yielded None and unwrap failed at crates/actr-hyper/tests/support/connection_governance_production.rs:353. Current code still has this logic. nextest explicitly retains retries=0. Partition passes reduce neither this to a confirmed root cause nor prove the recovery race fixed; collect cycle/role/generation/final-state evidence under stress.

## Artifact reuse: feasible design, not implemented/measured
Package E2E run.sh currently clears ACTR_CLI_BIN and unconditionally cargo-builds CLI, while LORAN_BIN accepts an external test fixture. Simply passing artifacts would not reuse CLI. Add an explicit validated CLI input, build the original CLI/default features and Loran test fixture once, bind manifest to SHA/target/toolchain/Cargo.lock/features/digest, tar to preserve executable bits, and measure transfer before fanout. Subsequent scenarios already reuse the same target directory. Distinct scenarios use fixed ports and should run on separate runners, not concurrently on one host. Profile mode skips Echo and is not a valid faster substitute.

## Batch3 feasibility, read-only evidence
- WebRTC check and Clippy static flags agree: Rust1.99, actr-hyper, all-targets, same host/default features; Clippy adds warnings-deny. No project cfg(clippy) branch found. A Clippy-only experiment is reasonable, but deleting check does not save its entire2:48: Clippy must still compile dependencies. Warm nextest step5:15 included just21.83 seconds of tests (419 passed). Actual compiler-unit coverage and full Clippy-only run remain unverified.
- Swift cold UniFFI0.31.1 install3:13; XCFramework5:01 included libactr compile4:41 and only~19 seconds generation/packaging. CI already builds macOS only and reuses the host staticlib. Prioritize version/architecture-pinned tool cache and Rust build cache, not nonexistent duplicate iOS compilation.
- Rust1.95 remains an explicit compatibility commitment in Cargo manifests, code generator, docs and workflow regression tests. Do not remove the job just to meet the budget. Gate currently omits MSRV.
- Batch1 second-run MSRV had Rust hits0/misses739 and cache write errors579. It was not effective warm Rust-cache validation, despite the repeated-run label.

## Acceptance remaining
Combine only validated candidates in one bounded fork workflow; verify full domain coverage and first-pass results, cache-write reliability, cold/warm repeated runs and actual push timestamps. Measure artifact transfer and batch3 candidates before crediting savings. At least a representative repeated PR sample, not these few jobs, is needed for P90. CodeQL remains outside CI Gate scope and no upstream/production workflow has been changed.
