# CI15 batch 1 validation (2026-11-12)

## Result
Batch 1 is not yet validated as an end-to-end cold-cache improvement or a P90 <=15 minute solution. All four measurements passed on their first attempt, but the cold candidate regressed.

| Run | Gate from workflow creation | Whole workflow | Web ready | Package E2E job |
|---|---:|---:|---:|---:|
| [Baseline cold](https://github.com/kaito-harry/actrium/actions/runs/43171949035) |25:38|25:38|5:48|15:40|
| [Batch 1 cold](https://github.com/kaito-harry/actrium/actions/runs/43175290302) |32:20|32:20|4:39|27:31|
| [Baseline warm](https://github.com/kaito-harry/actrium/actions/runs/43179482279) |16:34|16:35|0:24|16:01|
| [Batch 1 warm](https://github.com/kaito-harry/actrium/actions/runs/43181943749) |13:33|15:23|0:24|10:26|

MSRV is not a dependency of the existing Gate. Warm candidate MSRV finished last, so Gate <15 does not mean all workflow jobs <15. No support-policy change was made.

## Method
- Source upstream main cd2b600cc25cea0bf399fc1fb6ebd94a23ff586f.
- Isolated fork branches and copied workflows; original production CI and upstream PRs unchanged.
- Cold pair commit c4d3aad8122f750b8da97e996bc4c2fa8506b3db; warm pair empty commit 9cf6a9e37eb7e51b879d3ceb39a2bf01af19dec9. All four share tree 74e3f15455b92fc3e2431ce6be79a4516ff4385a. Warm is identical source tree, not identical commit SHA.
- Fixed Rust-core-plus-Package-E2E domain set, including Swift/WebRTC/TypeScript/Web/C#. Not every Cargo.toml-triggered domain and not CodeQL.
- Sequential runs on standard GitHub-hosted runners. Separate variant cache namespaces and no restore fallbacks. Initial jobs can prewarm shared caches within a run; reusable C# cache configuration is unchanged. “Cold” therefore refers to experiment namespaces, not proof of every possible cache miss.
- Times start at workflow created_at, not independently verified git push timestamp.
- Four samples cannot establish P90 or stable first-pass rate. Initial successful sample is 4/4, not a reliability guarantee.

## What worked
- Pinned checksum-verified prebuilt Wasm action executed successfully. Local actionlint, shell/YAML checks, installer execution and four timer-assertion fixtures passed.
- Cold Rust main-path finish improved from 25:31 to16:49. Cold Web preparation improved 5:48 to4:39, still beyond3:00.
- Rest ran3804 tests and realtime195, with all passing in each measured variant. Candidate asserts the RFC-0400 timer test is selected once in rest, and logs show it passed. Duplicate Rust-job compile/test was removed without omitting this test.
- Warm candidate E2E Rust sccache hits1315/misses487 vs cold hits3/misses1799. Warm CLI/Loran build1:44/1:20 vs cold5:21/5:00.

## Regression and uncertainty
Cold candidate Package E2E dominated at27:31 vs baseline15:40. Cold sccache reuse was negligible; write errors occurred, but baseline Rust jobs also had write errors. One pair does not isolate cache overhead from runner/network variation. Do not merge the complete batch as a demonstrated performance win yet. Post-job disk snapshots are not peak measurements and do not justify reducing cleanup.

## Historical context
Read-only audit of601 PR run records found30 successful full-Rust runs. Latest25 first-attempt-success sample: Gate P90 22.25min, workflow P90 22.43min. Including successful rerun histories produced Gate P90 26.15min. The completed success/failure sample first-pass rate was20/25, excluding cancelled/pending. These are heterogeneous domains/commits/caches, so percentile step savings cannot be subtracted to prove future P90.

## Next bounded experiments
1. Isolate cold Package E2E with otherwise identical sccache-off/on jobs and fresh namespaces; record compiler timings/cache statistics, disk samples and all test outcomes. Repeat before causal attribution.
2. Measure Web/Rust peak disk before reducing cleanup.
3. Use realtime test timings and inventory-union assertions to evaluate two isolated runners, accounting for duplicated compile cost.
4. Build CLI/Loran once at the same SHA, verify artifact digest/mode and measure upload/download before scenario fanout.
5. Verify WebRTC check/Clippy target-feature equivalence; inspect Swift install/build costs. Retain1.95 until an explicit support-policy decision. Gate/all-check deadline must be reported separately.
