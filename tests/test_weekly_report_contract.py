"""Preserve the report retry, data-access and schedule contracts in Terraform."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = (ROOT / 'infra/reports.tf').read_text()


def resource(kind, name):
    match = re.search(rf'(?ms)^resource "{kind}" "{name}" {{\n(.*?)(?=^resource |^data |\Z)', TEMPLATE)
    if match is None:
        raise AssertionError(f'Missing {kind}.{name}')
    return match.group(1)


class WeeklyReportContract(unittest.TestCase):
    def test_report_queue_retry_and_visibility(self):
        queue = resource('aws_sqs_queue', 'reports')
        self.assertRegex(queue, r'visibility_timeout_seconds\s*= 720')
        self.assertIn('maxReceiveCount = 3', queue)
        self.assertIn('aws_sqs_queue.dlq["report"].arn', queue)
        self.assertRegex(resource('aws_lambda_function', 'report_worker'), r'timeout\s*= 120')

    def test_failure_destinations_and_retries(self):
        for kind, name, dlq, retries in [('aws_cloudwatch_event_target', 'report_delivery', 'delivery', 5), ('aws_lambda_function_event_invoke_config', 'delivery', 'delivery', 2), ('aws_scheduler_schedule', 'reports', 'scheduler', 5)]:
            block = resource(kind, name)
            self.assertIn(f'aws_sqs_queue.dlq["{dlq}"].arn', block)
            self.assertRegex(block, rf'maximum_retry_attempts\s*= {retries}')

    def test_disabled_mapping_and_s3_events(self):
        mapping = resource('aws_lambda_event_source_mapping', 'reports')
        self.assertIn('maximum_concurrency = 2', mapping)
        self.assertRegex(mapping, r'enabled\s*= var.report_queue_enabled')
        self.assertIn('eventbridge = true', resource('aws_s3_bucket_notification', 'reports'))
        rule = resource('aws_cloudwatch_event_rule', 'report_created')
        self.assertIn('source = ["aws.s3"]', rule)
        self.assertIn('prefix = "reports/"', rule)

    def test_scheduler_trust_and_access_scope(self):
        role = resource('aws_iam_role', 'scheduler')
        for expected in ['scheduler.amazonaws.com', 'sts:AssumeRole', 'aws:SourceAccount', 'aws:SourceArn', 'aws_scheduler_schedule_group.reports.arn']:
            self.assertIn(expected, role)
        policy = resource('aws_iam_role_policy', 'scheduler')
        self.assertIn('Action = ["sqs:SendMessage"]', policy)
        self.assertNotRegex(policy, r'ses:|s3:|secretsmanager:|rds:')

    def test_report_list_is_prefix_scoped(self):
        for kind, name in [('aws_vpc_endpoint', 's3'), ('aws_iam_role_policy', 'report_objects')]:
            block = resource(kind, name)
            self.assertIn('Action = ["s3:ListBucket"]', block)
            self.assertIn('"s3:prefix" = "reports/*"', block)


if __name__ == '__main__':
    unittest.main()
