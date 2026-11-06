#!/usr/bin/env python3
"""Run all browser coverage tests against the real Issuer fixture.

Requires cargo-llvm-cov, matching wasm-bindgen CLI, Chrome/ChromeDriver,
protoc, and a wasm-capable clang. Installs nothing and starts no CI jobs.
Use a separate checkout and target directory for each matrix entry.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import tomllib
import urllib.request

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[3])
parser.add_argument('--toolchain', default='nightly-2026-11-06')
parser.add_argument('--out', type=Path, required=True)
parser.add_argument('--target', type=Path, required=True)
parser.add_argument('--fixture-binary', type=Path)
parser.add_argument('--chrome-binary', type=Path)
args = parser.parse_args()
repo, out = args.repo.resolve(), args.out.resolve()
out.mkdir(parents=True, exist_ok=True)
env = os.environ.copy()
env['CARGO_TARGET_DIR'] = str(args.target.resolve())
env['CARGO_TARGET_WASM32_UNKNOWN_UNKNOWN_RUNNER'] = 'wasm-bindgen-test-runner'
env['CARGO_TARGET_WASM32_UNKNOWN_UNKNOWN_RUSTFLAGS'] = (
    '-Cinstrument-coverage -Zno-profiler-runtime -Clink-args=--no-gc-sections '
    '--cfg=wasm_bindgen_unstable_test_coverage'
)
env['WASM_BINDGEN_USE_BROWSER'] = '1'
env['ACTR_MATRIX_OUT'] = str(out)
cargo = ['cargo', '+' + args.toolchain]
web = repo / 'packages/actr-web'

def run(command, log, cwd=web):
    with (out / log).open('w') as stream:
        subprocess.run(command, cwd=cwd, env=env, stdout=stream,
                       stderr=subprocess.STDOUT, check=True, timeout=600)

lock = tomllib.loads((web / 'Cargo.lock').read_text())
metadata = {
    'repo': str(repo),
    'lockfile_sha256': hashlib.sha256((web / 'Cargo.lock').read_bytes()).hexdigest(),
    'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip(),
    'rust': subprocess.check_output(['rustc', '+' + args.toolchain, '-vV'], text=True),
    'runner': subprocess.check_output(['wasm-bindgen-test-runner', '--version'], text=True).strip(),
    'cargo_llvm_cov': subprocess.check_output(['cargo', 'llvm-cov', '--version'], text=True).strip(),
    'chromedriver': subprocess.check_output([env.get('CHROMEDRIVER', 'chromedriver'), '--version'], env=env, text=True).strip(),
    'dependencies': [p for p in lock['package'] if p['name'] in {'minicov', 'wasm-bindgen-test', 'wasm-bindgen'}],
}
if args.chrome_binary:
    metadata['chrome'] = subprocess.check_output([str(args.chrome_binary), '--version'], text=True).strip()
(out / 'metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
fixture_binary = args.fixture_binary
if fixture_binary is None:
    run(cargo + ['test', '-p', 'loran-issuer', '--test', 'integration_test',
                 '--no-run', '--locked', '--message-format=json'], 'fixture-build.json', repo)
    for line in (out / 'fixture-build.json').read_text().splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get('executable') and event['target']['name'] == 'integration_test':
            fixture_binary = Path(event['executable'])
assert fixture_binary, 'missing fixture executable'

# Chrome creates Unix sockets in TMPDIR: use a short path independent of checkout.
with tempfile.TemporaryDirectory(prefix='acov-', dir='/tmp') as temporary:
    temp = Path(temporary)
    env.update({key: temporary for key in ('TMPDIR', 'TMP', 'TEMP')})
    options = {'args': ['user-data-dir=' + str(temp / 'profile'), 'disable-extensions']}
    if args.chrome_binary:
        options['binary'] = str(args.chrome_binary.resolve())
    config = temp / 'webdriver.json'
    config.write_text(json.dumps({'goog:chromeOptions': options}))
    env['WASM_BINDGEN_TEST_WEBDRIVER_JSON'] = str(config)
    ready = temp / 'ready'
    env['ACTR_WEB_FIXTURE_READY'] = str(ready)
    with (out / 'fixture.log').open('w') as fixture_log:
        fixture = subprocess.Popen([str(fixture_binary.resolve()), '--ignored', '--exact',
                                    'web_issuer_http_fixture', '--nocapture'],
                                   cwd=repo, env=env, stdout=fixture_log, stderr=subprocess.STDOUT)
        try:
            for _ in range(150):
                if ready.exists():
                    break
                assert fixture.poll() is None, 'fixture exited before readiness'
                time.sleep(.1)
            assert ready.exists(), 'fixture readiness timeout'
            env['ACTR_WEB_ISSUER_URL'] = ready.read_text().strip()
            packages = ['--target', 'wasm32-unknown-unknown', '-p', 'actr-web-common', '-p', 'actr-dom-bridge']
            run(cargo + ['llvm-cov', 'clean', '--workspace'], 'clean.log')
            run(cargo + ['llvm-cov', 'test', '--locked'] + packages +
                ['--all-features', '--tests', '--lcov', '--output-path', str(out / 'lcov.info')], 'test.log')
            run(cargo + ['llvm-cov', 'report'] + packages +
                ['--html', '--output-dir', str(out / 'html')], 'html.log')
            run(cargo + ['llvm-cov', 'report'] + packages +
                ['--json', '--output-path', str(out / 'coverage.json')], 'json.log')
            assert fixture.wait(timeout=15) == 0, 'fixture failed'
        finally:
            if fixture.poll() is None:
                try:
                    urllib.request.urlopen(ready.read_text().strip() + '/stop', timeout=2).read()
                except Exception:
                    pass
                try:
                    fixture.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    fixture.terminate()
                    fixture.wait(timeout=5)

totals = {key: 0 for key in ('LF', 'LH', 'FNF', 'FNH')}
for line in (out / 'lcov.info').read_text().splitlines():
    key, _, value = line.partition(':')
    if key in totals:
        totals[key] += int(value)
profiles = list(args.target.resolve().rglob('*.profraw'))
summary = {'lcov': totals, 'profiles': [{'path': str(p), 'bytes': p.stat().st_size} for p in profiles]}
(out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
assert profiles and all(p.stat().st_size for p in profiles), 'missing/empty profiles'
assert totals['LF'] > 0 and totals['LH'] > 0 and totals['FNH'] > 0, 'zero coverage'
print(json.dumps(summary, indent=2))
