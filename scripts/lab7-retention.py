#!/usr/bin/env python3
"""Prepare retention-only templates from private live snapshots; performs no AWS writes."""
import copy
import json
import os
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'submission/lab7/private'

class CfnLoader(yaml.SafeLoader):
    pass

def intrinsic(loader, tag, node):
    if isinstance(node, yaml.ScalarNode):
        value = loader.construct_scalar(node)
    elif isinstance(node, yaml.SequenceNode):
        value = loader.construct_sequence(node)
    else:
        value = loader.construct_mapping(node)
    key = tag if tag in ('Ref', 'Condition') else 'Fn::' + tag
    if tag == 'GetAtt' and isinstance(value, str):
        value = value.split('.', 1)
    return {key: value}

CfnLoader.add_multi_constructor('!', intrinsic)

def retained(original):
    result = copy.deepcopy(original)
    result.setdefault('Metadata', {}).setdefault('AWSToolsMetrics', {})['AWSAgentToolkit'] = 'aws-cloudformation@3'
    for resource in result['Resources'].values():
        resource['DeletionPolicy'] = 'Retain'
        resource['UpdateReplacePolicy'] = 'Retain'
    # Do not change Properties, names, parameters, outputs, or conditions.
    for key, resource in original['Resources'].items():
        assert result['Resources'][key].get('Properties') == resource.get('Properties')
    return result

def main():
    os.umask(0o077)
    for name in ('auth', 'reports', 'ai'):
        snapshot = json.loads((PRIVATE / f'{name}-template.json').read_text())['TemplateBody']
        template = yaml.load(snapshot, Loader=CfnLoader) if isinstance(snapshot, str) else snapshot
        updated = retained(template)
        body = json.dumps(updated, indent=2) + '\n'
        assert len(body.encode()) < 51200, 'Use an S3 template URL for a larger template'
        path = PRIVATE / f'{name}-retain.json'
        path.write_text(body)
        path.chmod(0o600)
        stack = json.loads((PRIVATE / f'{name}-stack.json').read_text())['Stacks'][0]
        parameters = [{'ParameterKey': p['ParameterKey'], 'UsePreviousValue': True} for p in stack.get('Parameters', [])]
        parameter_path = PRIVATE / f'{name}-previous-parameters.json'
        parameter_path.write_text(json.dumps(parameters, indent=2) + '\n')
        parameter_path.chmod(0o600)
        print(f'{name}: {len(updated["Resources"])} resources retained; properties unchanged')

if __name__ == '__main__':
    main()
