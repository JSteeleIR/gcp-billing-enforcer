resource "google_billing_budget" "enforce_billing_budgets" {
  for_each = var.billing_limits
  provider = google-beta

  billing_account = each.value.account_id
  display_name = "Enforcement Budget for ${each.key}."
  amount {
    specified_amount {
      currency_code = "USD"
      units = each.value.enforce_limit
    }

  }

  budget_filter {
    credit_types_treatment = each.value.include_credits ? "INCLUDE_ALL_CREDITS" : "EXLUCDE_ALL_CREDITS"
  }

  threshold_rules {
    # Alert at 50% Enforcement budget
    threshold_percent = 0.50
  }

  threshold_rules {
    # Alert at 75% Enforcement budget
    threshold_percent = 0.75
  }

  threshold_rules {
    # Alert at projected 100% Enforcement budget
    threshold_percent = 1.0
    spend_basis = "FORECASTED_SPEND"
  }

  threshold_rules {
    # Alert at 100% Enforcement budget
    threshold_percent = 1.0
  }

  all_updates_rule {
    pubsub_topic = google_pubsub_topic.billing_enforcement_topic.id
  }
}
