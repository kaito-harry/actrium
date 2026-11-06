#!/usr/bin/env python3
"""Compare two run.py output directories, including executed function locations."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import struct

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('baseline', type=Path)
parser.add_argument('experiment', type=Path)
args = parser.parse_args()

def load(directory):
    metadata = json.loads((directory / 'metadata.json').read_text())
    summary = json.loads((directory / 'summary.json').read_text())
    prefix = metadata['repo'].rstrip('/') + '/'
    functions = defaultdict(int)
    data = json.loads((directory / 'coverage.json').read_text())
    for group in data['data']:
        for function in group['functions']:
            if not function['filenames'] or not function['regions']:
                continue
            filename = function['filenames'][0]
            if not filename.startswith(prefix):
                continue
            region = function['regions'][0]
            # Region end coordinates and mangled names can change with rustc.
            key = (filename.removeprefix(prefix), region[0], region[1])
            functions[key] += function['count']
    versions = []
    for profile in summary['profiles']:
        raw = Path(profile['path']).read_bytes()
        versions.append(struct.unpack('<Q', raw[8:16])[0] & 0xffffffff)
    summary['raw_profile_versions'] = sorted(set(versions))
    summary['executed_function_starts'] = sum(count > 0 for count in functions.values())
    return summary, functions

baseline, a = load(args.baseline)
experiment, b = load(args.experiment)
hit_a = {key for key, count in a.items() if count}
hit_b = {key for key, count in b.items() if count}
result = {
    'baseline': baseline,
    'experiment': experiment,
    'shared_executed_function_starts': len(hit_a & hit_b),
    'equal_execution_counts': sum(a[key] == b[key] for key in hit_a & hit_b),
    'baseline_only_executed_starts': sorted(hit_a - hit_b),
    'experiment_only_executed_starts': sorted(hit_b - hit_a),
    'changed_execution_counts': [
        {'location': key, 'baseline': a[key], 'experiment': b[key]}
        for key in sorted(hit_a & hit_b) if a[key] != b[key]
    ],
}
print(json.dumps(result, indent=2))
