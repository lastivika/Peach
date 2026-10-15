"""Local CloudFormation contract checks for the report's retry paths."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = (ROOT / "infra/weekly-meetings-report.yaml").read_text()


def resource(name: str) -> str:
    match = re.search(
        rf"(?ms)^  {re.escape(name)}:\n(.*?)(?=^  [A-Za-z][A-Za-z0-9]*:\n|\Z)",
        TEMPLATE,
    )
    if match is None:
        raise AssertionError(f"CloudFormation resource {name} is missing")
    return match.group(1)


class WeeklyReportContract(unittest.TestCase):
    def test_report_queue_uses_three_receives_and_adequate_visibility(self):
        queue = resource("ReportQueue")
        self.assertIn("VisibilityTimeout: 720", queue)
        self.assertIn("deadLetterTargetArn: !GetAtt ReportQueueDlq.Arn", queue)
        self.assertIn("maxReceiveCount: 3", queue)
        self.assertIn("Timeout: 120", resource("ReportFunction"))

    def test_delivery_and_scheduler_failures_have_dlq_destinations(self):
        event_rule = resource("ReportCreatedRule")
        self.assertIn("Arn: !GetAtt DeliveryDlq.Arn", event_rule)
        self.assertIn("MaximumRetryAttempts: 5", event_rule)

        async_failure = resource("DeliveryAsyncFailureConfig")
        self.assertIn("MaximumRetryAttempts: 2", async_failure)
        self.assertIn("Destination: !GetAtt DeliveryDlq.Arn", async_failure)

        schedule = resource("WeeklySchedule")
        self.assertIn("Arn: !GetAtt SchedulerDlq.Arn", schedule)
        self.assertIn("State: !Ref ScheduleState", schedule)

    def test_event_source_concurrency_and_s3_event_configuration(self):
        mapping = resource("ReportQueueMapping")
        self.assertIn("MaximumConcurrency: 2", mapping)
        self.assertNotIn("ReservedConcurrentExecutions", resource("ReportFunction"))

        bucket = resource("ReportBucket")
        self.assertIn("EventBridgeEnabled: true", bucket)
        event_rule = resource("ReportCreatedRule")
        self.assertIn("source: [aws.s3]", event_rule)
        self.assertIn("prefix: reports/", event_rule)

    def test_scheduler_trust_is_scoped_to_its_schedule_group(self):
        role = resource("SchedulerRole")
        self.assertIn("Service: scheduler.amazonaws.com", role)
        self.assertIn("Action: sts:AssumeRole", role)
        self.assertIn("aws:SourceAccount: !Ref AWS::AccountId", role)
        self.assertIn("aws:SourceArn: !GetAtt SchedulerGroup.Arn", role)
        self.assertNotIn(":schedule/", role)
        self.assertIn("Action: [sqs:SendMessage]", role)
        self.assertIn("!GetAtt ReportQueue.Arn, !GetAtt SchedulerDlq.Arn", role)
        self.assertNotRegex(role, r"ses:|s3:|secretsmanager:|rds:")

        schedule = resource("WeeklySchedule")
        self.assertIn("GroupName: !Ref SchedulerGroup", schedule)
        self.assertIn("RoleArn: !GetAtt SchedulerRole.Arn", schedule)

    def test_schedule_arn_output_uses_group_and_schedule_names(self):
        self.assertRegex(
            TEMPLATE,
            r'ScheduleArn:\n    Value: !Sub "arn:\$\{AWS::Partition\}:scheduler:'
            r"\$\{AWS::Region\}:\$\{AWS::AccountId\}:schedule/"
            r'\$\{SchedulerGroup\}/\$\{ProjectName\}-weekly-meetings"',
        )
        self.assertNotIn("!GetAtt WeeklySchedule.Arn", TEMPLATE)

    def test_report_list_permission_is_scoped_to_report_prefix(self):
        endpoint = resource("S3GatewayEndpoint")
        self.assertRegex(
            endpoint,
            r"(?s)Action: \[s3:ListBucket\].*?Resource: !GetAtt ReportBucket\.Arn"
            r".*?s3:prefix: reports/\*",
        )

        role = resource("ReportFunctionRole")
        self.assertRegex(
            role,
            r"(?s)Action: \[s3:ListBucket\].*?Resource: !GetAtt ReportBucket\.Arn"
            r".*?s3:prefix: reports/\*",
        )


if __name__ == "__main__":
    unittest.main()
