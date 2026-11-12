"""Validate selected (binary-id, test-name) identities, not only counts."""
import json
import sys


def selected(inventory):
    items = []
    for suite in inventory['rust-suites'].values():
        for name, case in suite.get('testcases', {}).items():
            if not case['ignored'] and case['filter-match']['status'] == 'matches':
                items.append((suite['binary-id'], name))
    if len(items) != len(set(items)):
        raise ValueError('duplicate selected test identities')
    return set(items)


def verify(whole, heavy, network):
    if not whole or not heavy or not network:
        raise ValueError('all realtime partitions must be nonempty')
    if heavy & network:
        raise ValueError(f'overlapping realtime tests: {sorted(heavy & network)}')
    if heavy | network != whole:
        raise ValueError(f'missing={sorted(whole-(heavy|network))}; extra={sorted((heavy|network)-whole)}')
    print(f'Realtime partition verified: whole={len(whole)} build-heavy={len(heavy)} network={len(network)}')


if __name__ == '__main__':
    if len(sys.argv) != 4:
        raise SystemExit('expected whole, build-heavy, network nextest JSON files')
    verify(*(selected(json.load(open(p))) for p in sys.argv[1:]))
