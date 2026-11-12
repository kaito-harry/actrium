# Combined full-workflow experiment: publication-ready, not launched

Worktree: `/tmp/ci15-combined`, product source `9cf6a9e37eb7e51b879d3ceb39a2bf01af19dec9`.

## Files to publish together

New:
- `.github/workflows/ci15-combined.yml`
- `.github/workflows/ci15-combined-kotlin.yml`
- `.github/workflows/ci15-combined-csharp.yml`
- `.github/actions/ci15-web-space/action.yml`
- `.github/scripts/ci15-space-guard.py`
- `.github/scripts/ci15-assert-realtime.py`
- `.github/scripts/ci15-combined-test.py`

Already present in source and required unchanged:
- `.github/actions/install-wasm-tools/action.yml`
- `.github/scripts/assert-ci15-timer.py`

No production workflow/script, application code, MSRV promise or existing PR was changed. No branch/commit published and no experiment triggered by this work.

## A/B operation and coverage

One workflow serves both variants. Create baseline and candidate branch refs pointing at the SAME experiment commit/tree:
- `experiment/ci15-combined-baseline-c01`
- `experiment/ci15-combined-candidate-c01`

Vary cohort suffix for an independent cold namespace. Only the candidate-named branch activates optimizations. All consumer checkouts default to the exact triggering experiment commit. A determine step asserts application/product paths unchanged from source (excludes experiment/config `.github` and `tools/ci`). The original production `ci-gate.yml` is not rewritten, so its existing `ci_gate_test.py` tests still exercise the actual production configuration.

Original full-run target detection is forced through its `workflow_dispatch`/manual-full=true path. All original 21 top-level jobs remain, including Python codegen/workloads, Kotlin, C/Go, TypeScript, C#, Swift and MSRV. Original Gate job object is exactly equal, including its existing omission of MSRV. New independent `complete` job waits for all original top-level jobs including determine/Gate/MSRV and requires every result == success. It is not in original Gate's dependencies/timing. An unexpectedly skipped full domain cannot count as a valid all-green sample. C# internal ARM signal-only skip remains the original intended behavior. Full production CI Gate still does not mean CodeQL or every optional platform matrix.

Local Kotlin/C# reusable copies retain all original job/test behavior and default github.sha checkout. Local reusable workflow references resolve from the same caller commit. Namespace is passed explicitly as required workflow_call input; caller env inheritance is not assumed.

## Candidate-only changes

- Shared pinned prebuilt Wasm tools in the six previously validated jobs; baseline retains original installer commands.
- Remove standalone RFC-0400 Rust invocation only for candidate; assert exact selected timer in existing rest inventory.
- Web Runtime skips broad cleanup only when actual free space >=10 GiB, otherwise uses the original cleanup action. Only Web preparation is changed.
- Original realtime filter partitioned into build-heavy (rust_echo + dynclib_actor_e2e) and network (remaining realtime), on separate runners. Every candidate realtime shard materializes whole/heavy/network inventories from a single binary build and checks exact (binary-id,test-name) sets, nonempty, disjoint and union equality. Original retries unchanged. Rest unchanged except timer assertion.
- WebRTC check omitted only for candidate; original Clippy and nextest retained.
- NO added E2E sccache, serial producer, Swift optimization or MSRV change.

## Cache controls and measurement caveats

Namespace = full branch ref_name, applied to every actions/cache key/restore prefix, Swatinem prefix-key, and SCCACHE_GHA_VERSION, including reusable Kotlin/C# internals. Setup-node/python/java built-in package caches were replaced with identically scoped actions/cache stores in BOTH variants so npm/pip/Gradle do not silently read an unnamespaced production cache. This makes the baseline an instrumented production-command baseline, not byte-identical production cache plumbing. Package-manager toolchain/download/server and runner-image preinstalled files remain external uncontrolled warm state.

Each cache action reports actual cache-hit and outcome into logs/summary; sccache jobs report compiler cache statistics. A fresh namespace is not enough to assert every individual job was cold: jobs within the same first run can legitimately warm each other's shared compiler cache. Check actual outputs/errors.

For a warm observation, reuse branch namespace and source tree. A same-run rerun is useful but its created_at is the original cold push; do NOT call created_at-to-Gate on a rerun a fresh hot push measurement. Prefer a new empty commit with identical tree, shared by the baseline/candidate branch pair, for a separate hot push event. Record trigger/ref-update time independently of workflow created_at, which is only an enqueue proxy. Do not start 30 automatic runs before reviewing first full paired cold/hot behavior and unexpected skips/failures.

## Validation completed

- YAML parsed for all three workflows and composite action.
- Every original top-level job retained; original Gate deep-equal; complete includes MSRV and determine.
- Static matrix/filter branch paths and unique step IDs checked.
- All shell run bodies pass bash -n after substituting GitHub expressions; native explicit PowerShell preserved.
- Explicit cache scopes checked; no unnamespaced package-manager setup cache remains.
- Guard unit tests cover threshold-1, threshold, threshold+1 and invalid negative space; partition tests reject overlap/missing/extra/empty and ignore unselected/ignored cases. 3 tests pass.
- 52 production ci_gate_test cases pass locally. One SQLite integration test cannot run locally because sqlite3 is absent; original CI determine installs SQLite before the full suite, unchanged.
- Approved GitHub-hosted runner policy passes: 43 workflow files /188 runner jobs.
- Language/path policy passes.
- Independent second-agent scope/cache/Gate/partition review passed.
- actionlint not available; attempted Go installation was unsupported by the local Go command wrapper, so no actionlint success is claimed.

New workflow tests and paired CI runs remain necessary to verify actual runner allocation, cache behavior and full-domain execution. Nothing here establishes a 15-minute P90.
