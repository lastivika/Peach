#!/usr/bin/env python3
"""Read-only snapshot of the three stacks; artifacts may contain secrets."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'submission/lab7/private'
STACKS = {'auth': 'peach-cognito', 'reports': 'peach-weekly-meetings-report', 'ai': 'peach-ai'}

def aws(*args):
    result = subprocess.run(['aws', *args, '--profile', os.environ.get('AWS_PROFILE', 'peach-lab'), '--region', os.environ.get('AWS_REGION', 'us-east-1'), '--output', 'json'], check=True, capture_output=True, text=True)
    return json.loads(result.stdout)

def save(name, value):
    path = DEST / name
    path.write_text(json.dumps(value, indent=2) + '\n')
    path.chmod(0o600)

def main():
    os.umask(0o077)
    DEST.mkdir(parents=True, exist_ok=True)
    save('identity.json', aws('sts', 'get-caller-identity'))
    for key, stack in STACKS.items():
        save(f'{key}-stack.json', aws('cloudformation', 'describe-stacks', '--stack-name', stack))
        save(f'{key}-resources.json', aws('cloudformation', 'list-stack-resources', '--stack-name', stack))
        save(f'{key}-template.json', aws('cloudformation', 'get-template', '--stack-name', stack, '--template-stage', 'Original'))
        print(f'{key}: saved stack, resource IDs and original template privately')

if __name__ == '__main__':
    main()
