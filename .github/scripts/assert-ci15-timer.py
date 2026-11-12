import json,sys
inventory=json.load(open(sys.argv[1]))
name='timer::tests::inv24_production_timer_calls_and_inventory_do_not_drift'
found=[]
for suite in inventory['rust-suites'].values():
    case=suite.get('testcases',{}).get(name)
    if suite['package-name']=='actr-hyper' and suite['kind']=='lib' and case and not case['ignored'] and case['filter-match']['status']=='matches':
        found.append(suite['binary-id'])
assert len(found)==1, f'RFC-0400 timer test must be selected exactly once: {found}'
print(f'RFC-0400 timer selected in {found[0]}')
