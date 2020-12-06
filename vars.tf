variable "billing_enforcer_project" {
  type = string
  description = "The project which will run the billing enforcement infrastrcuture (Pub/Subs & Enforcement GCFs)."
}

variable "billing_limits" {
  type = map(object({
    account_id = string
    enforce_limit = number
    include_credits = bool
  }))
  description = "A list of billing accounts with an enforcement limit amounts for each."
}

variable "enforcement_exempt_projects" {
  type = list(string)
  default = []
}

variable "gcf_source_bucket_name" {
  type = string
  description = "The name of the bucket to store the enforcer GCF function in."
}

variable "slack_token" {
  type = string
  default = ""
  description = "The API key used to post to slack. If not supplied, slack notifications are disabled."
}

variable "slack_channel" {
  type = string
  default = ""
  description = "The slack channel ID to post to. e.g."
}

output "billing_enforcer_service_account_email" {
  value = google_service_account.billing_enforcer.email
  description = "The email address of the Billing Enforcer service account. MUST be added as a Billing Account Admin to the billing account, to be able to disable billing on over-budget projects."
}
