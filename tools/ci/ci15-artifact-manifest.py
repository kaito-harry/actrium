#!/usr/bin/env python3
"""Exact-run fixture provenance; artifacts are not cross-commit caches."""
import hashlib,json,os,pathlib,platform,subprocess,sys
mode,directory=sys.argv[1:]
base=pathlib.Path(directory)
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def expected():
    rust=subprocess.check_output(['rustc','-vV'],text=True)
    sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    assert sha == os.environ['GITHUB_SHA'], 'checkout/GITHUB_SHA mismatch'
    return dict(schema=1,commit=sha,target=next(x[6:] for x in rust.splitlines() if x.startswith('host: ')),toolchain=rust,os=platform.system(),machine=platform.machine(),cargo_lock=digest(pathlib.Path('Cargo.lock')),cli_features='default; backend=cdylib',loran_features='default; cargo test --no-run --bin loran',web_assets={p.name:digest(p) for p in sorted(pathlib.Path('crates/actr-cli/assets/web-runtime').iterdir()) if p.is_file()})
files=['bin/actr','bin/loran-fixture']
for name in files:
    assert (base/name).is_file() and os.access(base/name,os.X_OK), f'not executable: {name}'
if mode=='create':
    data=expected();data['files']={name:digest(base/name) for name in files}
    (base/'manifest.json').write_text(json.dumps(data,indent=2)+'\n')
elif mode=='verify':
    data=json.loads((base/'manifest.json').read_text());checks=expected()
    assert set(data)==set(checks)|{'files'}, 'unexpected manifest fields'
    for key,value in checks.items():
        assert data[key]==value, f'provenance mismatch: {key}'
    assert data['files']=={name:digest(base/name) for name in files}, 'binary checksum mismatch'
    print('Verified exact SHA, target, toolchain, lockfile, default features, Web assets, executable permissions and binary hashes')
else: raise SystemExit('expected create or verify')
