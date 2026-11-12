# CI15 batch 1 experiment

Pinned production source: cd2b600cc25cea0bf399fc1fb6ebd94a23ff586f.

The baseline and batch1 workflows use the same application source. Both select native Rust-core PR domains plus Package Runtime E2E explicitly; this is not every domain selected by a Cargo.toml change. They run only in their named experiment branches in the public fork, on standard GitHub-hosted runners. Production ci-gate.yml is untouched.

Batch1 changes only: use existing checksum-pinned prebuilt Wasm tools in six Linux jobs; add sccache to Package Runtime E2E; remove redundant Rust-job RFC-0400 compilation and assert the timer test is selected exactly once in the rest shard inventory. No production tests or retries are removed.

Each variant has a distinct experimental Web output, rust-cache and sccache namespace. Reusable SDK workflows retain their production cache configuration; report their actual hit state rather than calling those strictly cold. Baseline and candidate should run sequentially to avoid deliberate runner-slot contention. A repeat push to the same branch measures warm-cache behavior with unchanged application source.

Record workflow-created-to-Gate, workflow-created-to-last-job, job and step durations, actual cache hits, test counts and retries, and first-attempt outcome. GitHub created_at is not the exact user push timestamp. Small A/B samples validate mechanisms and identify regressions, not a P90 promise. The existing Gate does not include rust_msrv in needs; record MSRV and whole-workflow timing separately. Do not drop MSRV or silently change the 1.95 compatibility promise.

The experiment does not combine WebRTC checks, split realtime, change cleaning, or optimize Swift yet. Those belong to later measured batches.
