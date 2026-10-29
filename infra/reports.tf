locals {
  lambda_trust = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Service = "lambda.amazonaws.com" }, Action = "sts:AssumeRole" }] })
  report_tags  = { PROJECT_NAME = var.project_name }
}
resource "aws_s3_bucket" "reports" {
  bucket = var.report_bucket_name
  tags   = local.report_tags
  lifecycle { prevent_destroy = true }
}
resource "aws_s3_bucket_ownership_controls" "reports" {
  bucket = aws_s3_bucket.reports.id
  rule { object_ownership = "BucketOwnerEnforced" }
}
resource "aws_s3_bucket_public_access_block" "reports" {
  bucket                  = aws_s3_bucket.reports.id
  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_server_side_encryption_configuration" "reports" {
  bucket = aws_s3_bucket.reports.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}
resource "aws_s3_bucket_lifecycle_configuration" "reports" {
  bucket = aws_s3_bucket.reports.id
  rule {
    id     = "expire-weekly-reports"
    status = "Enabled"
    filter { prefix = "reports/" }
    expiration { days = 90 }
  }
}
resource "aws_s3_bucket_notification" "reports" {
  bucket      = aws_s3_bucket.reports.id
  eventbridge = true
}
resource "aws_sqs_queue" "dlq" {
  for_each                  = var.report_dlq_names
  name                      = each.value
  max_message_size          = 1048576
  message_retention_seconds = 1209600
  sqs_managed_sse_enabled   = true
  tags                      = local.report_tags
}
resource "aws_sqs_queue" "reports" {
  name                       = var.report_queue_name
  visibility_timeout_seconds = 720
  max_message_size           = 1048576
  message_retention_seconds  = 1209600
  sqs_managed_sse_enabled    = true
  redrive_policy             = jsonencode({ deadLetterTargetArn = aws_sqs_queue.dlq["report"].arn, maxReceiveCount = 3 })
  tags                       = local.report_tags
}
resource "aws_sqs_queue_policy" "delivery" {
  queue_url = aws_sqs_queue.dlq["delivery"].url
  policy    = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Service = "events.amazonaws.com" }, Action = ["sqs:SendMessage"], Resource = aws_sqs_queue.dlq["delivery"].arn, Condition = { ArnEquals = { "aws:SourceArn" = aws_cloudwatch_event_rule.report_created.arn } } }] })
}
resource "aws_security_group" "report" {
  name        = var.report_security_group_name
  description = "Weekly report Lambda access to the existing Peach database."
  vpc_id      = var.vpc_id
  egress {
    protocol        = "tcp"
    from_port       = 5432
    to_port         = 5432
    security_groups = [var.database_security_group_id]
    description     = "PostgreSQL to the existing Peach database."
  }
  egress {
    protocol        = "tcp"
    from_port       = 443
    to_port         = 443
    prefix_list_ids = [var.s3_prefix_list_id]
    description     = "HTTPS to the S3 gateway endpoint route."
  }
  tags = local.report_tags
}
resource "aws_vpc_security_group_ingress_rule" "database" {
  security_group_id            = var.database_security_group_id
  referenced_security_group_id = aws_security_group.report.id
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
  description                  = "PostgreSQL from Peach weekly report Lambda."
}
resource "aws_vpc_endpoint" "s3" {
  count             = var.manage_s3_gateway_endpoint ? 1 : 0
  vpc_id            = var.vpc_id
  service_name      = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = var.private_route_table_ids
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Principal = "*", Action = ["s3:GetObject", "s3:PutObject"], Resource = "${aws_s3_bucket.reports.arn}/reports/*" },
    { Effect = "Allow", Principal = "*", Action = ["s3:ListBucket"], Resource = aws_s3_bucket.reports.arn, Condition = { StringLike = { "s3:prefix" = "reports/*" } } },
    { Effect = "Allow", Principal = "*", Action = ["s3:GetObject"], Resource = "arn:${data.aws_partition.current.partition}:s3:::prod-${var.region}-starport-layer-bucket/*" }
  ] })
}
resource "aws_iam_role" "report" {
  for_each           = var.report_role_names
  name               = each.value
  assume_role_policy = local.lambda_trust
}
resource "aws_iam_role_policy_attachment" "report_vpc" {
  role       = aws_iam_role.report["worker"].name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}
resource "aws_iam_role_policy" "report_objects" {
  name = "write-report-objects"
  role = aws_iam_role.report["worker"].id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["s3:GetObject", "s3:PutObject"], Resource = "${aws_s3_bucket.reports.arn}/reports/*" },
    { Effect = "Allow", Action = ["s3:ListBucket"], Resource = aws_s3_bucket.reports.arn, Condition = { StringLike = { "s3:prefix" = "reports/*" } } }
  ] })
}
resource "aws_iam_role_policy" "report_queue" {
  name   = "consume-report-queue"
  role   = aws_iam_role.report["worker"].id
  policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Action = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:ChangeMessageVisibility", "sqs:GetQueueAttributes"], Resource = aws_sqs_queue.reports.arn }] })
}
resource "aws_cloudwatch_log_group" "report" {
  for_each          = toset(["worker", "delivery"])
  name              = "/aws/lambda/${var.project_name}-weekly-report-${each.key}"
  retention_in_days = 7
}
resource "aws_iam_role_policy" "report_logs" {
  for_each = { worker = "write-report-logs", delivery = "write-delivery-logs" }
  name     = each.value
  role     = aws_iam_role.report[each.key].id
  policy   = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Action = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"], Resource = "${aws_cloudwatch_log_group.report[each.key].arn}:*" }] })
}
resource "aws_iam_role_policy" "delivery" {
  name = "read-report-and-send-email"
  role = aws_iam_role.report["delivery"].id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["s3:GetObject"], Resource = "${aws_s3_bucket.reports.arn}/reports/*" },
    { Effect = "Allow", Action = ["ses:SendEmail", "ses:SendRawEmail"], Resource = "arn:${data.aws_partition.current.partition}:ses:${var.region}:${data.aws_caller_identity.current.account_id}:identity/${var.report_sender_email}" }
  ] })
}
resource "aws_iam_role_policy" "delivery_failures" {
  name   = "route-delivery-failures-to-dlq"
  role   = aws_iam_role.report["delivery"].id
  policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Action = ["sqs:SendMessage"], Resource = aws_sqs_queue.dlq["delivery"].arn }] })
}
data "aws_secretsmanager_secret_version" "database" {
  secret_id = var.database_url_secret_arn
}
resource "aws_lambda_function" "report_worker" {
  function_name = "${var.project_name}-weekly-report-worker"
  package_type  = "Image"
  image_uri     = var.report_image_uri
  architectures = ["arm64"]
  memory_size   = 512
  timeout       = 120
  role          = aws_iam_role.report["worker"].arn
  image_config { command = ["app.weekly_report.worker.handler"] }
  vpc_config {
    subnet_ids         = var.private_subnet_ids
    security_group_ids = [aws_security_group.report.id]
  }
  environment {
    variables = {
      DATABASE_URL  = data.aws_secretsmanager_secret_version.database.secret_string
      DB_POOLING    = "false"
      APP_ENV       = "production"
      REPORT_BUCKET = aws_s3_bucket.reports.id
    }
  }
  tags       = local.report_tags
  depends_on = [aws_vpc_security_group_ingress_rule.database]
}
resource "aws_lambda_event_source_mapping" "reports" {
  event_source_arn        = aws_sqs_queue.reports.arn
  function_name           = aws_lambda_function.report_worker.arn
  enabled                 = var.report_queue_enabled
  batch_size              = 1
  function_response_types = ["ReportBatchItemFailures"]
  scaling_config { maximum_concurrency = 2 }
}
resource "aws_lambda_function" "report_delivery" {
  function_name = "${var.project_name}-weekly-report-delivery"
  package_type  = "Image"
  image_uri     = var.report_image_uri
  architectures = ["arm64"]
  memory_size   = 256
  timeout       = 30
  role          = aws_iam_role.report["delivery"].arn
  image_config { command = ["app.weekly_report.delivery.handler"] }
  environment {
    variables = {
      REPORT_BUCKET    = aws_s3_bucket.reports.id
      REPORT_SENDER    = var.report_sender_email
      REPORT_RECIPIENT = var.report_recipient_email
    }
  }
  tags = local.report_tags
}
resource "aws_cloudwatch_event_rule" "report_created" {
  name          = var.report_created_rule_name
  description   = "Send a weekly CSV attachment and private link when a report is written."
  event_pattern = jsonencode({ source = ["aws.s3"], "detail-type" = ["Object Created"], detail = { bucket = { name = [aws_s3_bucket.reports.id] }, object = { key = [{ prefix = "reports/" }] } } })
}
resource "aws_cloudwatch_event_target" "report_delivery" {
  rule      = aws_cloudwatch_event_rule.report_created.name
  target_id = "ReportEmailDelivery"
  arn       = aws_lambda_function.report_delivery.arn
  dead_letter_config { arn = aws_sqs_queue.dlq["delivery"].arn }
  retry_policy {
    maximum_event_age_in_seconds = 3600
    maximum_retry_attempts       = 5
  }
}
resource "aws_lambda_permission" "report_delivery" {
  statement_id   = var.delivery_statement_id
  function_name  = aws_lambda_function.report_delivery.function_name
  action         = "lambda:InvokeFunction"
  principal      = "events.amazonaws.com"
  source_account = data.aws_caller_identity.current.account_id
  source_arn     = aws_cloudwatch_event_rule.report_created.arn
}
resource "aws_lambda_function_event_invoke_config" "delivery" {
  function_name                = aws_lambda_function.report_delivery.function_name
  qualifier                    = "$LATEST"
  maximum_event_age_in_seconds = 3600
  maximum_retry_attempts       = 2
  destination_config {
    on_failure { destination = aws_sqs_queue.dlq["delivery"].arn }
  }
}
resource "aws_scheduler_schedule_group" "reports" {
  name = "${var.project_name}-weekly-reports"
}
resource "aws_iam_role" "scheduler" {
  name               = var.scheduler_role_name
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Service = "scheduler.amazonaws.com" }, Action = "sts:AssumeRole", Condition = { StringEquals = { "aws:SourceAccount" = data.aws_caller_identity.current.account_id }, ArnLike = { "aws:SourceArn" = aws_scheduler_schedule_group.reports.arn } } }] })
}
resource "aws_iam_role_policy" "scheduler" {
  name   = "enqueue-report-and-capture-failures"
  role   = aws_iam_role.scheduler.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Action = ["sqs:SendMessage"], Resource = [aws_sqs_queue.reports.arn, aws_sqs_queue.dlq["scheduler"].arn] }] })
}
resource "aws_scheduler_schedule" "reports" {
  name                         = "${var.project_name}-weekly-meetings"
  group_name                   = aws_scheduler_schedule_group.reports.name
  description                  = "Queue a report for the previous complete ISO week at 07:00 Europe/Kyiv every Monday."
  state                        = var.report_schedule_state
  schedule_expression          = "cron(0 7 ? * MON *)"
  schedule_expression_timezone = "Europe/Kyiv"
  flexible_time_window { mode = "OFF" }
  target {
    arn      = aws_sqs_queue.reports.arn
    role_arn = aws_iam_role.scheduler.arn
    input    = "{\"source\":\"schedule\"}"
    dead_letter_config { arn = aws_sqs_queue.dlq["scheduler"].arn }
    retry_policy {
      maximum_event_age_in_seconds = 3600
      maximum_retry_attempts       = 5
    }
  }
}
