# LLVM 23.1.5 + minicov 0.3.9 experiment

This branch tests coverage collection, not a production toolchain upgrade.
Base: upstream Actrium/actrium main `5cc8b8511904f39f7743f2d9389706d78cdcc482`.
The only dependency change is minicov 0.3.8 -> 0.3.9 in the web lockfile.
No main branch, pull request, or GitHub Actions run was changed or created.

## Observed results, 2026-11-06

Both entries used the same source revision, 54 browser tests (24 DOM bridge,
29 common, one live Issuer test), and the same real native Issuer fixture.
The fixture was rebuilt from this source revision, used real Issuer/Signer
handlers and SQLite, and exited successfully in both entries. Both runs used
Chromium/ChromeDriver 156.0.8078.79, wasm-bindgen CLI/runner 0.2.126,
wasm-bindgen-test 0.3.76, cargo-llvm-cov 0.9.1, and a wasm-capable clang 19.1.7.
The C profiling runtime itself is not coverage-instrumented.

| Measurement | LLVM 22 control | LLVM 23 experiment |
| --- | --- | --- |
| Rust toolchain | nightly-2026-04-01 | nightly-2026-11-06 |
| rustc | 1.96.0-nightly, 48cc71ee8 (2026-03-31) | 1.101.0-nightly, 249c1e4e3 (2026-11-05) |
| LLVM | 22.1.2 | 23.1.5 |
| minicov | 0.3.8 | 0.3.9 |
| Browser tests | 54 passed | 54 passed |
| Nonempty raw profiles | 3, format v10 | 3, format v11 |
| Covered / instrumented lines | 1338 / 4742 (28.22%) | 1293 / 4670 (27.69%) |
| Covered / instrumented functions (LCOV) | 169 / 695 | 169 / 701 |
| LCOV, HTML, JSON export | passed | passed |
| Executed source function start locations | 173 | 173 |

All 173 executed source function locations were present in both runs, with
identical execution counts after aggregating instantiations at each source
start position. There were no lost/gained executed start locations and no
profile/function mismatch warnings in test or export logs. This checks more
than file existence or a nonzero global total. `compare.py` retains the exact
comparison method; the 173 location aggregates differ from LLVM's 169 counted
covered functions because they use a different grouping/filtering rule.

The zero-coverage/function-data failure described in wasm-bindgen PR #5283
was **not reproduced with this exact pair and workload**. LLVM 23 emits a
different coverage mapping: total instrumented lines/functions and some region
boundaries differ. Percentages across compiler versions are therefore not
directly interchangeable. Passing this workload is not proof for arbitrary
Wasm crates, all LLVM 23 releases, Node runners, or other browsers.

## Dependency provenance and constraints

All dependencies are crates.io packages; no git/path/vendor override was used.
The published wasm-bindgen-test 0.3.76 manifest declares `minicov = "0.3.8"`
(a caret requirement), not `=0.3.8`. Its original package/checksum was retained.
Therefore `cargo update -p minicov --precise 0.3.9` is valid for this lockfile.
The exact `=0.3.8` pin added later to wasm-bindgen's git source in
[PR #5283](https://github.com/wasm-bindgen/wasm-bindgen/pull/5283) is a different
dependency source. A consumer of that exact git pin cannot use this simple
lockfile-only change; it would need a deliberate test-crate manifest patch.

Checksums:

- wasm-bindgen-test 0.3.76: `2a0d555ca874445df8d314f94f5c948a4e74e5418f332c89f660a3d8310a96f4`
- wasm-bindgen 0.2.126: `4b067c0c11094aef6b7a801c1e34a26affafdf3d051dba08456b868789aaf9a4`
- minicov 0.3.9: `c3aa3aa12b448ac225b3102217d1ac5cc717908f02722926524b0599c933c7a0`
- minicov 0.3.9 crate VCS revision: `03886b886ce16b9309ddd38e4824970e70fc0588`

## Reproduction

Install the two dated toolchains with `wasm32-unknown-unknown` and
`llvm-tools-preview`, plus the matching wasm-bindgen CLI, cargo-llvm-cov,
protoc, wasm-capable clang, and a matching Chrome/ChromeDriver pair.
Use Python 3.11+. `clang` must be on PATH because minicov's build script
explicitly invokes it, even if `CC_wasm32_unknown_unknown` is configured.

```sh
python3 tools/experiments/wasm-coverage/run.py \
  --out /tmp/coverage-llvm23-results \
  --target /tmp/coverage-llvm23-target \
  --chrome-binary /path/to/chrome
```

The runner starts the real fixture, waits for readiness, sets its URL **before
compilation**, and runs the original `--all-features --tests` scope. It cleans
old profiles before testing and writes LCOV, HTML, LLVM JSON, metadata, and a
summary. Chrome's temporary directory is under a short `/tmp/acov-*` path to
avoid the previously diagnosed Unix socket path limit. The fixture and temporary
profile are cleaned on success and failure.

For the control, use a separate worktree at the base commit with its original
minicov 0.3.8 lockfile, and pass `--repo /path/to/control`,
`--toolchain nightly-2026-04-01`, and separate output/target directories.
For identical fixture provenance, pass the same `--fixture-binary` to both runs;
this experiment used a fixture built with LLVM 23 from the base source.

```sh
python3 tools/experiments/wasm-coverage/compare.py \
  /path/to/control-results /path/to/experiment-results > comparison.json
```

`results.json` preserves this run's metadata, profile sizes/versions, and function
comparison. Large profiles, generated reports, and absolute machine paths are
not committed. No Actions run was needed; any future CI reproduction must run
in kaito-harry/actrium, not the upstream repository.
