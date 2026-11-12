# Combined full-domain CI15 pilots: status and evidence

## Current status
Three pilots finished. No experiment is currently running on behalf of this validation thread. Further sampling was paused after an independently operated ChatGPT experiment was discovered in the same fork, to avoid duplicate runs and uncontrolled runner/cache competition. The owner confirmed that other work exists. No other experiment was modified or cancelled.

**The combined candidate is faster in the measured cold pair, but P90 <=15 minutes is not validated.** The planned fourth clean repeated-cache candidate pilot and additional cohorts have NOT been completed.

## Scope and fixed configuration
Product source:9cf6a9e37eb7e51b879d3ceb39a2bf01af19dec9 (upstream main cd2b600). Combined experiment tree:51e44f2f45e1b00c4419d69bb1aa292e5009f79c.
Cold A/B share commit754a8c450f49c98f08c8c9935dd0cd1812681cba. Repeat-cache baseline uses empty commit2ba1410cbf7ba2671f1634ab4728729a53228e1a with identical tree.

Original full_run domains, all21 top-level jobs and original Gate semantics retained. An independent complete job additionally requires every original job, including determine/MSRV, to succeed. Kotlin/Python/C-Go and all original test scopes execute. C# ARM signal-only remains the original expected skip; CodeQL is a separate workflow and is NOT covered.

Candidate: checksum-pinned prebuilt Wasm tools; duplicate timer consolidation with rest inventory assertion; Web cleanup only below10GiB free; exact195=24+171 realtime split; Clippy-only WebRTC after prior coverage validation. No new serial artifact producer, no E2E sccache addition, no MSRV downgrade or test removal.

## Measurements

| Sample | Created→Gate | Created→workflow end | Ref-update→Gate interval | Ref-update→workflow interval |
|---|---:|---:|---:|---:|
| Baseline cold |25:58|28:34|25:59.2–26:02.4|28:35.2–28:38.4|
| Candidate cold |17:38|19:13|17:39.1–17:44.3|19:14.1–19:19.3|
| Baseline repeat-cache, confounded |24:06|26:50|24:07.5–24:14.4|26:51.5–26:58.4|

The request/response UTC bounds bracket the actual remote ref update; they are not invented exact push timestamps. Complete GitHub timestamps and request bounds are in combined-pilot-metrics.json.

Runs:
- https://github.com/kaito-harry/actrium/actions/runs/43212875382
- https://github.com/kaito-harry/actrium/actions/runs/43217496737
- https://github.com/kaito-harry/actrium/actions/runs/43220724283

Cold candidate improved workflow elapsed9:21 (~32.7%) and Gate8:20 (~32.1%) versus this baseline. Cold Web ready2:27 versus6:50, with actual asset-cache miss and successful disk guard; Rust job8:47 versus18:59. Candidate rest3804 and realtime24+171 all passed with no observed internal retries. Last candidate Gate dependency was rest15:02; MSRV16:37 finished later and set full completion19:13. This misses the15-minute target.

## Cache and contention findings
Cold namespaces were isolated, including local reusable Kotlin/C# workflows, with actual cache logs checked. Within-run sharing still permits small hits; “cold” is not a claim that every byte originated uncached.

The repeat-cache baseline did not become reliably warm. The exact Web cache key saved in the cold run was reported Cache not found in the repeated run; source, hash and ref did not change. Some Kotlin/WebRTC/Rust dependency caches hit, many others missed. MSRV Rust hits0/misses739, write errors554. Do not label this a clean all-hot comparison.

Another independent run,43220491524 on experiment/ci15-combined-candidate-native-c02, began12:43:17, overlapping baseline repeat at12:44:48. Several jobs queued144–257seconds. Public cache API showed about11.97GB active caches and thousands of entries during this interval; this does not prove why a particular cache disappeared. The exact cause of eviction/missing restore is unresolved.

Read-only diff shows native-c02 adds debug-info=0 and64GiB native cleanup guards. It is a DIFFERENT configuration and its measurements must not be pooled with c01. No communication with that external agent or modification of its work occurred.

## Reliability and P90
Workflow-attempt success:3/3, all run_attempt=1; no manual reruns in these pilots.
Test-level zero-retry success is different: the repeat-cache baseline had one distinct rest test fail initially and pass on automatic retry:
loran-server::relay_only regular_launcher_serves_static_relay_without_database_alone_or_with_ice, relay_only.rs:320 Protocol(ResetWithoutClosingHandshake).
The failed first execution and later pass are retained; it is not a clean zero-retry sample. No claim about its root cause is made.

Each baseline/candidate/cache-condition stratum currently has n=1. A nearest-rank empirical P90 at n=1 is merely that single observation; it provides no useful production percentile validation. Pooling these different variants, cache states and contention conditions would produce a misleading number. The candidate's only cold observation already exceeds15minutes. Do not filter out failures, cache misses, queueing or slower results.

Even5 samples per cold/warm stratum make empirical P90 the maximum. Approximately29 representative independent all-under-threshold observations would be needed for a one-sided95% bound that at least90% meet the threshold; fixed-source repeats still do not represent the population of changing PRs.

## Next step
Coordinate the independent work so one clearly versioned candidate and its baseline can be sampled without deliberately overlapping experiments. Preserve real queue/cache behavior as labeled production-like evidence, but keep controlled comparisons separate. Resolve MSRV/rest critical path and cache reliability, then complete repeated cold/cache cohorts and report actual sample counts, per-stratum P90, first-workflow-attempt and zero-test-retry rates. No promise of a completed P90 validation is made here.

No upstream/main/existing PR or MSRV commitment was changed.
