variable "billing_enforcer_project" {
  type = stirng
  description = "The project which will run the billing enforcement infrastrcuture (Pub/Subs & Enforcement GCFs)."
}

variable "billing_limits" {
  type = map(object({
    account_id = string
    alert_limit = number
    enforce_limit = number
    include_credits = bool
  }))
  description = "A list of billing accounts with alert/enforcement amounts for each."
}

variable "enforcement_exempt_projects" {
  type = list(string)
  default = []
}

output "billing_enforcer_service_account_email" {
  value = google_service_account.billing_enforcer.email
  description = "The email address of the Billing Enforcer service account. MUST be added as a Billing Account Admin to the billing account, to be able to disable billing on over-budget projects."
}
