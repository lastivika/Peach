#!/usr/bin/env python3
"""Reject a JSON Terraform migration plan unless it exclusively imports resources."""
import json
import sys
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('plan')
parser.add_argument('--expected-imports', type=int)
parser.add_argument('--allow-sensitivity-only', action='store_true')
args = parser.parse_args()
plan = json.load(open(args.plan))
if plan.get('errored') or plan.get('complete') is False or plan.get('deferred_changes'):
    sys.exit('REJECT: incomplete, errored or deferred plan')
failures = []
imports = 0
metadata_updates = 0
def has_unknown(value):
    if isinstance(value, dict):
        return any(has_unknown(v) for v in value.values())
    if isinstance(value, list):
        return any(has_unknown(v) for v in value)
    return value is True

for resource in plan.get('resource_changes', []):
    if resource.get('mode') == 'data':
        continue
    change = resource['change']
    imports += bool(change.get('importing'))
    if change['actions'] != ['no-op']:
        sensitivity_only = (
            args.allow_sensitivity_only
            and change['actions'] == ['update']
            and 'before' in change and 'after' in change
            and change['before'] == change['after']
            and not has_unknown(change.get('after_unknown'))
            and change.get('before_sensitive') != change.get('after_sensitive')
            and not change.get('replace_paths')
        )
        if sensitivity_only:
            metadata_updates += 1
        else:
            failures.append((resource['address'], change['actions']))
if failures:
    for address, actions in failures:
        print(f'REJECT: {address}: {actions}', file=sys.stderr)
    sys.exit(1)
if not imports:
    sys.exit('REJECT: no resource imports in migration plan')
if args.expected_imports is not None and imports != args.expected_imports:
    sys.exit(f'REJECT: expected {args.expected_imports} imports, found {imports}')
print(f'PASS: {imports} imports; {metadata_updates} sensitivity-only updates; zero resource value changes, creates or destroys')
