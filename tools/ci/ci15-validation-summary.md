# CI15 validation summary

Validated on Ferris using isolated branches of kaito-harry/actrium. No upstream/main/existing PR or MSRV commitment changed.

## Verdict
The plan contains useful changes, but full Rust PR P90 <=15 minutes is **not established**. Component experiments must not be added arithmetically to predict P90. The fastest batch1 Gate was13:33, while that workflow finished15:23 because MSRV was outside Gate dependencies. Cold batch1 regressed25:38→32:20; a later isolated E2E cache comparison did not reproduce a large causal sccache regression.

| Proposal | Evidence | Decision |
|---|---|---|
| Pinned prebuilt Wasm tools + timer consolidation | Successful runs; rest3804/realtime195 coverage retained | Good implementation candidates |
| Web cleanup reduction | Cold paired4:15→2:12; creation-to-ready2:15; sampled84GiB free | Strongest observed preparation improvement; retain disk-space fallback |
| realtime split | Whole17:46 vs split max14:31; exact195=24+171 coverage | Promising, increases runner-minutes; repeat/full-pipeline validation needed |
| E2E sccache | Warm benefit observed; cold isolation near-equal; many write failures | Fix cache reliability before crediting stable savings |
| CLI/Loran artifact reuse | All4 original scenarios pass; transfer15s plus31s packaging; serial full chain17:00 | Functional, not yet a speed win; third CLI-lib fixture still compiles1:55 |
| WebRTC Clippy-only | Same740 compilation units and419 passing tests; command savings24s, job11s slower | Safe simplification for tested configuration, not a large latency win |
| UniFFI distribution | Verified tool download1s and35Swift tests pass; cold producer4:21 | Reusable pre-produced tool plausible; building fresh in PR did not prove faster |
| MSRV | Rust1.95 compatibility remains; warm Rust cache hits0; omitted from Gate | Keep promise and report separately; investigate cache/critical path |
| #427 flaky recovery | Original failing wait identified; unchanged retries=0 | Split passes do not prove race fixed |
| CodeQL | Outside these CI Gate experiments | Needs separate all-check budget |

## Detailed evidence
- [Batch1 controlled four-run measurements](ci15-results.md), [JSON](ci15-results.json).
- [Batch2 Web/E2E/realtime experiments and batch3 static review](ci15-phase2-3-results.md), [JSON](ci15-phase2-3-results.json).
- [Exact-SHA fixture reuse](ci15-artifact-reuse.md), [JSON](ci15-artifact-reuse-metrics.json).
- [WebRTC and UniFFI runtime validation](ci15-phase3-report.md), [JSON](ci15-phase3-results.json).

The fixture harness initially used unsupported actr --version; the corrected --help run passed, and both histories are retained. UniFFI first failed to acquire a hosted macOS runner for15m02; retry succeeded, with original-run total35m03. These are not hidden from elapsed-time/reliability accounting. All experiments have finished.

## Remaining acceptance work
Choose and combine the useful changes, then measure representative cold/repeated-cache full PR runs including queueing, retries, first-pass rate, MSRV and an explicitly defined CodeQL scope. Repair cache writes and validate scenario fanout/third-fixture reuse before crediting E2E savings. Do not claim all changes or the15-minute P90 target are production-validated.
