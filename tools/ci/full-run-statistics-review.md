# Independent full-run scope and statistical review

Read-only review of original ci-gate.yml in `/tmp/ci15-combined`, base `9cf6a9e37eb7e51b879d3ceb39a2bf01af19dec9`. No jobs started.

## Scope

Full mode sets all 13 ci_targets.py outputs true: rust_core, e2e_rust, e2e_package_runtime, ts_binding, ts_workload, python_codegen, python_workload, swift_binding, kotlin_binding, csharp_binding, web_binding, c_go_workloads, release_related. release_related has no standalone job.

Original 21 top-level jobs: identity, determine, cli_web_assets, e2e_rust, e2e_package_runtime, audit, rust, test, rust_msrv, typescript, typescript_workload, python_codegen, python_workload, swift, kotlin, web, c_go_workloads, webrtc, cjk, csharp, gate.

Test expands to realtime/rest. Kotlin expands to script-check/native-build/test/gen-test. C# expands to Windows build and an expected skipped ARM64 signal-only job. Normally this means 26 listed expanded jobs, 25 executed; candidate realtime split adds one. Derive actual expectation from the final configuration.

Gate omissions:
- rust_msrv is absent from Gate needs/results. Report Gate and all-required/workflow completion separately.
- determine is in needs but absent from results. Gate allows skipped jobs, so determine failure followed by skipped domains can produce misleading green. External validation must require determine success and all expected domains actually execute.
- Full mode is all CI Gate domains, not all PR checks: CodeQL and independent workflows are excluded.
- Full mode does not imply full platform matrix: original C# caller does not enable full_matrix; ARM64 is skipped and signal-only/continue-on-error.
- Preserve baseline Gate semantics for comparison; label any strengthened experimental endpoint separately.

## Bounded sampling

First run four pilots: baseline cold/warm and candidate cold/warm. Both arms must use identical immutable application source and combined workflow tree, with branch-selectable changes. If warm measurement requires an empty commit, record that SHA differs but tree is identical.

Only expand if functional scope and measurement are valid and further measurements are useful. Cap candidate at five cold plus five warm observations, counting valid pilots toward the cap. Never repeat until obtaining five fast successes or delete slow/failing samples. Run full workflows sequentially to avoid deliberate account-concurrency interference; alternate/randomize A/B order if practical. Do not update a branch while its cancel-in-progress sample is running.

Each cold/warm pair needs an isolated new cache namespace for cold and identical namespace for warm. Cover Web, sccache, Rust caches, reusable Kotlin/C# caches and restore fallback keys. A SHA-only key defeats warming when empty commits change SHA. Inspect real hit/miss/write-error evidence and report partial-cold or ineffective-warm states. Do not purge unrelated caches.

## Timestamps and endpoints

Capture UTC immediately before ref-create/update request (`t_send`) and immediately after successful response (`t_receive`). Actual accepted push time is bounded by this interval. For Gate completion `c`, push-to-Gate duration is `[max(0,c-t_receive), max(0,c-t_send)]`. Record both bounds. Git author/committer timestamp is not push time.

Record workflow created_at -> Gate separately as a proxy, not exact push latency. Preserve first job start, Web ready, every job start/end/conclusion, Gate completion, all-required completion including MSRV, and workflow completion. updated_at can include bookkeeping: keep final job/check completed_at too. Server check completion does not measure browser paint latency.

Per observation store arm/cache state/cache pair, branch, SHA/tree, run ID, attempt number, all timestamps, expected/actual jobs and test counts, retries and cache metrics.

## Small-sample statistics

Report cold and warm separately for each arm: attempted n; valid measured n; invalid/harness n and explicit reasons; first-attempt all-required successes; eventual successes; every duration; min/max/median; nearest-rank sample P90.

Nearest-rank P90 is sorted rank ceil(0.9*n), one-based. For n=1..9 it is the maximum; n=10 uses rank9. Five cold and five warm produce two noisy maxima, not production-tail certification. Do not pool them into a 50/50 mixture unless that deployment weighting was independently justified in advance.

With five IID samples, chance that the sample maximum covers the population P90 is only 1-0.9^5 = 40.95%. Five sub-15-minute runs cannot establish population P90 <=15. Under ideal IID assumptions, 29/29 threshold successes are needed for a one-sided 95% binomial lower confidence bound above 90%; heterogeneous real workloads make generalization harder. Call the capped sample pilot/diagnostic evidence, not P90 verification.

For push-duration bounds, calculate sample P90 of lower bounds and upper bounds separately. Use the conservative upper bound when determining whether an individual push met budget.

## Failures, retries and equivalence

First-attempt success requires expected coverage and all required domains including MSRV, not merely green Gate. Track nextest FLAKY/retries even when the job succeeds.

An unresolved failed run has no observed time-to-green: mark right-censored/not attained, count it as a deadline miss, and never treat early failure time as fast success. Optionally report a failure-penalized empirical P90 using infinity for unresolved outcomes, explicitly labeled.

For rerun-to-green, elapsed time starts at the original push and includes failure plus rerun delay. Also report attempt-specific compute time diagnostically. Specify a bounded retry budget before expansion, e.g. one diagnostic rerun, and record failed-jobs-only versus all-job reruns. Collect prior successful jobs across attempts.

Harness errors remain in attempted counts and chronological report. Corrected workflows form new labeled versions; they are not silent replacements. State exclusions and their rationale before recomputing valid-sample summaries.

Assert full-domain execution; preserve feature filters, doctests, acceptance inventories and retry policies. For realtime split, assert selection union equals original and intersection empty. Job green alone does not establish equivalent coverage.

## Stop conditions

After four pilots, pause expansion for invalid coverage/harness, or repeated obvious budget misses with a known unresolved critical-path change. One miss is a measured miss, not population-P90 proof; further identical costly trials may nonetheless be low-value. Publish all samples and describe diagnostic stopping. Do not calculate selected-success P90.

Any code/workflow change starts a new frozen cohort. Final output must separate functional equivalence, observed latency changes, sample P90, unverified population P90, and checks outside CI Gate.

## Combined draft quick review

Read `ci15-combined.yml`, `ci15-combined-kotlin.yml`, and `ci15-combined-csharp.yml` before push. All original 21 top-level jobs remain; Gate is structurally identical. Added `complete` requires every top-level dependency to succeed, including determine and MSRV. Candidate uses build-heavy/network/rest versus baseline realtime/rest. The JSON partition assertion compares exact binary-id/test-name sets and rejects empty, overlapping, missing or extra selections.

Visible actions/cache keys and Swatinem prefixes have branch namespaces, with no restore fallback keys; reusable workflows receive the namespace explicitly. Baseline and candidate share the same experimental dependency-cache replacements for setup-node/python/java. This is a controlled experimental baseline, not byte-identical production cache behavior. Cold runs may still receive intra-run cross-job cache warming; document that distinction. The source-drift guard compares to the immutable base, excluding only experiment/config/report directories (.github and tools/ci).
