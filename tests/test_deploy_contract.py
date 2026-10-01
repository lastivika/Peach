"""Exercise release safety with fake AWS responses; never calls a real cloud API."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SHA = "a" * 40
FAKE_TOOL = r'''#!/usr/bin/env python3
import json, os, pathlib, sys
args = sys.argv[1:]
with open(os.environ['CALL_LOG'], 'a') as f:
    f.write(json.dumps([pathlib.Path(sys.argv[0]).name] + args) + '\n')
if pathlib.Path(sys.argv[0]).name != 'aws':
    raise SystemExit(0)
cmd = ' '.join(args)
if cmd.startswith('sts get-caller-identity'):
    print('arn:aws:iam::123456789012:root' if os.environ['SCENARIO'] == 'root' else
          'arn:aws:iam::123456789012:user/lab' if 'Arn' in args else '123456789012')
elif cmd.startswith('acm describe-certificate'):
    print('ISSUED')
elif cmd.startswith('cloudformation describe-stacks'):
    query = args[args.index('--query')+1]
    outputs = {'ClusterName': 'peach-ecs', 'ServiceName': 'peach-backend',
               'TaskDefinitionArn': 'arn:aws:ecs:us-east-1:123456789012:task-definition/peach-backend:2',
               'TaskSecurityGroupId': 'sg-task', 'AlbDnsName': 'alb.example.com', 'ApiUrl': 'https://api.example.com'}
    for key, value in outputs.items():
        if key in query:
            print(value)
            break
    else:
        raise SystemExit('unexpected stack output: ' + query)
elif cmd.startswith('ecs run-task'):
    print(json.dumps({'failures': [{'reason': 'capacity'}]} if os.environ['SCENARIO'] == 'capacity'
                     else {'tasks': [{'taskArn': 'arn:aws:ecs:us-east-1:123456789012:task/peach-ecs/test'}]}))
elif cmd.startswith('ecs describe-tasks'):
    print('1' if os.environ['SCENARIO'] == 'migration' else '0')
elif cmd.startswith('ecs describe-services'):
    print('old-revision' if os.environ['SCENARIO'] == 'rollback'
          else 'arn:aws:ecs:us-east-1:123456789012:task-definition/peach-backend:2')
'''


class DeployContract(unittest.TestCase):
    def run_deploy(self, scenario):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "scripts").mkdir()
            (root / "bin").mkdir()
            shutil.copy(ROOT / "scripts/deploy-backend.sh", root / "scripts")
            for command in ["aws", "docker", "curl", "git"]:
                tool = root / "bin" / command
                tool.write_text(FAKE_TOOL)
                tool.chmod(0o755)
            env = dict(os.environ)
            env.update({
                "PATH": str(root / "bin") + os.pathsep + env["PATH"],
                "CALL_LOG": str(root / "calls.jsonl"), "SCENARIO": scenario,
                "API_DOMAIN_NAME": "api.example.com", "API_CERTIFICATE_ARN": "arn:test",
                "COGNITO_USER_POOL_ID": "pool", "COGNITO_CLIENT_ID": "client",
                "API_CORS_ORIGINS": "https://app.example.com", "IMAGE_TAG": SHA,
                "DATABASE_URL_SECRET_ARN": "arn:secret", "DATABASE_SECURITY_GROUP_ID": "sg-db",
                "AWS_VPC_ID": "vpc-test", "AWS_SUBNET_IDS": "subnet-a,subnet-b",
            })
            result = subprocess.run(["bash", str(root / "scripts/deploy-backend.sh")],
                                    env=env, capture_output=True, text=True, timeout=20)
            calls = [json.loads(line) for line in (root / "calls.jsonl").read_text().splitlines()]
            saved = (root / ".env").read_text() if (root / ".env").exists() else ""
            return result, calls, saved

    def test_migration_failure_does_not_promote_or_save_url(self):
        result, calls, saved = self.run_deploy("migration")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Migration failed", result.stderr)
        self.assertFalse(any("DesiredCount=1" in call for call in calls))
        self.assertEqual(saved, "")

    def test_capacity_failure_does_not_promote(self):
        result, calls, saved = self.run_deploy("capacity")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any("DesiredCount=1" in call for call in calls))
        self.assertEqual(saved, "")

    def test_success_migrates_before_promotion_and_saves_verified_url(self):
        result, calls, saved = self.run_deploy("success")
        self.assertEqual(result.returncode, 0, result.stderr)
        migration = next(i for i, call in enumerate(calls) if call[1:3] == ["ecs", "run-task"])
        promotion = next(i for i, call in enumerate(calls) if "DesiredCount=1" in call)
        self.assertLess(migration, promotion)
        self.assertIn("BACKEND_URL=https://api.example.com", saved)
        self.assertTrue(any(SHA in " ".join(call) for call in calls))

    def test_ecs_rollback_is_not_reported_as_success(self):
        result, _, saved = self.run_deploy("rollback")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("rolled back", result.stderr)
        self.assertEqual(saved, "")

    def test_root_is_rejected_before_resource_changes(self):
        result, calls, _ = self.run_deploy("root")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("non-root", result.stderr)
        self.assertTrue(all(call[1:3] == ["sts", "get-caller-identity"] for call in calls))


if __name__ == "__main__":
    unittest.main()
