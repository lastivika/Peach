"""Verify the migration gate rejects changes that could duplicate or lose resources."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/check-migration-plan.py'

class MigrationPlanGate(unittest.TestCase):
    def run_plan(self, changes, *args):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json') as f:
            json.dump({'resource_changes': changes}, f)
            f.flush()
            return subprocess.run([sys.executable, str(SCRIPT), f.name, *args], capture_output=True, text=True)

    def resource(self, actions, importing=False):
        change = {'actions': actions}
        if importing:
            change['importing'] = {'id': 'existing-bucket'}
        return {'address': 'aws_s3_bucket.reports', 'mode': 'managed', 'change': change}

    def test_import_only_is_accepted(self):
        self.assertEqual(self.run_plan([self.resource(['no-op'], True)]).returncode, 0)

    def test_create_update_delete_and_replacement_are_rejected(self):
        for actions in [['create'], ['update'], ['delete'], ['delete', 'create']]:
            with self.subTest(actions=actions):
                self.assertNotEqual(self.run_plan([self.resource(actions, True)]).returncode, 0)

    def test_empty_or_no_import_plan_is_rejected(self):
        self.assertNotEqual(self.run_plan([]).returncode, 0)
        self.assertNotEqual(self.run_plan([self.resource(['no-op'])]).returncode, 0)

    def test_approved_sensitivity_only_update(self):
        r = self.resource(['update'], True)
        r['change'].update(before={'value': 'same'}, after={'value': 'same'},
                           before_sensitive={}, after_sensitive={'value': True})
        self.assertNotEqual(self.run_plan([r]).returncode, 0)
        self.assertEqual(self.run_plan([r], '--allow-sensitivity-only', '--expected-imports', '1').returncode, 0)
        r['change']['after'] = {'value': 'changed'}
        self.assertNotEqual(self.run_plan([r], '--allow-sensitivity-only').returncode, 0)

    def test_unknown_values_and_wrong_import_count_rejected(self):
        r = self.resource(['update'], True)
        r['change'].update(before={}, after={}, before_sensitive={},
                           after_sensitive={'value': True}, after_unknown={'nested': [True]})
        self.assertNotEqual(self.run_plan([r], '--allow-sensitivity-only').returncode, 0)
        self.assertNotEqual(self.run_plan([self.resource(['no-op'], True)], '--expected-imports', '49').returncode, 0)

if __name__ == '__main__':
    unittest.main()
