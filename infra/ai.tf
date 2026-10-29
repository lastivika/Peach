resource "aws_cloudwatch_log_group" "parser" {
  name              = "/aws/lambda/${var.project_name}-agenda-parser"
  retention_in_days = var.parser_log_retention
  tags              = { PROJECT_NAME = var.project_name, Lab7Evidence = "vcs-apply" }
}

resource "aws_iam_role" "parser" {
  name               = var.parser_role_name
  assume_role_policy = local.lambda_trust
  tags               = { PROJECT_NAME = var.project_name }
}
resource "aws_iam_role_policy" "parser" {
  name = "ParseAndLogOnly"
  role = aws_iam_role.parser.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = "bedrock:InvokeModel", Resource = "arn:${data.aws_partition.current.partition}:bedrock:${var.region}::foundation-model/${var.parser_model}", Condition = { StringEquals = { "aws:RequestedRegion" = var.region } } },
    { Effect = "Allow", Action = ["logs:CreateLogStream", "logs:PutLogEvents"], Resource = "${aws_cloudwatch_log_group.parser.arn}:*" }
  ] })
}
resource "aws_lambda_function" "parser" {
  function_name = "${var.project_name}-agenda-parser"
  package_type  = "Image"
  image_uri     = var.parser_image_uri
  architectures = ["arm64"]
  role          = aws_iam_role.parser.arn
  timeout       = 30
  memory_size   = 512
  image_config { command = ["app.ai.agenda_lambda.handler"] }
  environment {
    variables = {
      COGNITO_REGION                = var.region
      COGNITO_USER_POOL_ID          = aws_cognito_user_pool.main.id
      COGNITO_CLIENT_ID             = aws_cognito_user_pool_client.web.id
      PARSER_MODEL                  = var.parser_model
      PARSER_INPUT_USD_PER_MILLION  = "0.8"
      PARSER_OUTPUT_USD_PER_MILLION = "3.2"
    }
  }
  tags = { PROJECT_NAME = var.project_name }
}
resource "aws_lambda_function_url" "parser" {
  function_name      = aws_lambda_function.parser.function_name
  authorization_type = "NONE"
  cors {
    allow_origins = [var.site_url]
    allow_methods = ["POST"]
    allow_headers = ["authorization", "content-type"]
    max_age       = 300
  }
}
resource "aws_lambda_permission" "parser_url" {
  statement_id           = var.parser_url_statement_id
  function_name          = aws_lambda_function.parser.function_name
  action                 = "lambda:InvokeFunctionUrl"
  principal              = "*"
  function_url_auth_type = "NONE"
}
resource "aws_lambda_permission" "parser_invoke" {
  statement_id             = var.parser_invoke_statement_id
  function_name            = aws_lambda_function.parser.function_name
  action                   = "lambda:InvokeFunction"
  principal                = "*"
  invoked_via_function_url = true
}
resource "aws_budgets_budget" "ai" {
  name         = "${var.project_name}-lab6-monthly"
  tags         = { PROJECT_NAME = var.project_name }
  budget_type  = "COST"
  time_unit    = "MONTHLY"
  limit_amount = "5"
  limit_unit   = "USD"
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 5
    threshold_type             = "ABSOLUTE_VALUE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.budget_email]
  }
}
