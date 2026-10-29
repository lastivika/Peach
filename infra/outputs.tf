output "cognito_user_pool_id" {
  value = aws_cognito_user_pool.main.id
}
output "cognito_client_id" {
  value = aws_cognito_user_pool_client.web.id
}
output "cognito_domain" {
  value = "${aws_cognito_user_pool_domain.main.domain}.auth.${var.region}.amazoncognito.com"
}
output "parser_url" {
  value = aws_lambda_function_url.parser.function_url
}
output "parser_name" {
  value = aws_lambda_function.parser.function_name
}
output "report_bucket_name" {
  value = aws_s3_bucket.reports.id
}
output "report_queue_url" {
  value = aws_sqs_queue.reports.url
}
output "report_queue_dlq_url" {
  value = aws_sqs_queue.dlq["report"].url
}
output "report_schedule_arn" {
  value = aws_scheduler_schedule.reports.arn
}
