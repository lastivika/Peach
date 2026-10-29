variable "region" {
  type        = string
  description = "Existing deployed value; preserve during import."
}
variable "site_url" {
  type        = string
  description = "Existing deployed value; preserve during import."
}
variable "google_client_id" {
  type        = string
  description = "Existing deployed value; preserve during import."
}
variable "google_client_secret" {
  type        = string
  description = "Sensitive workspace input; never commit."
  sensitive   = true
}
variable "cognito_domain_prefix" {
  type        = string
  description = "Existing deployed value; preserve during import."
}
variable "parser_role_name" {
  type        = string
  description = "Existing deployed value; preserve during import."
}
variable "parser_image_uri" {
  type        = string
  description = "Existing deployed value; preserve during import."
}
variable "parser_url_statement_id" {
  type        = string
  description = "Existing deployed value; preserve during import."
}
variable "parser_invoke_statement_id" {
  type        = string
  description = "Existing deployed value; preserve during import."
}
variable "budget_email" {
  type        = string
  description = "Sensitive workspace input; never commit."
  sensitive   = true
}
variable "report_bucket_name" {
  type        = string
  description = "Existing deployed value; preserve during import."
}
variable "report_queue_name" {
  type        = string
  description = "Existing deployed value; preserve during import."
}
variable "report_security_group_name" {
  type        = string
  description = "Existing deployed value; preserve during import."
}
variable "vpc_id" {
  type        = string
  description = "Existing deployed value; preserve during import."
}
variable "database_security_group_id" {
  type        = string
  description = "Existing deployed value; preserve during import."
}
variable "s3_prefix_list_id" {
  type        = string
  description = "Existing deployed value; preserve during import."
}
variable "database_url_secret_arn" {
  type        = string
  description = "Existing deployed value; preserve during import."
}
variable "report_image_uri" {
  type        = string
  description = "Existing deployed value; preserve during import."
}
variable "report_sender_email" {
  type        = string
  description = "Sensitive workspace input; never commit."
  sensitive   = true
}
variable "report_recipient_email" {
  type        = string
  description = "Sensitive workspace input; never commit."
  sensitive   = true
}
variable "report_created_rule_name" {
  type        = string
  description = "Existing deployed value; preserve during import."
}
variable "delivery_statement_id" {
  type        = string
  description = "Existing deployed value; preserve during import."
}
variable "scheduler_role_name" {
  type        = string
  description = "Existing deployed value; preserve during import."
}
variable "private_route_table_ids" {
  type = list(string)
}
variable "private_subnet_ids" {
  type = list(string)
}
variable "report_dlq_names" {
  type = map(string)
}
variable "report_role_names" {
  type = map(string)
}
variable "project_name" {
  type    = string
  default = "peach"
}
variable "parser_model" {
  type    = string
  default = "amazon.nova-pro-v1:0"
}
variable "parser_log_retention" {
  type    = number
  default = 14
}
variable "manage_s3_gateway_endpoint" {
  type    = bool
  default = true
}
variable "report_queue_enabled" {
  type    = bool
  default = false
}
variable "report_schedule_state" {
  type    = string
  default = "DISABLED"
}
