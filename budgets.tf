resource "google_billing_budget" "alert_billing_budgets" {
  for_each = vars.billing_limits

  billing_account = each.account_id
  display_name = "Alert Budget for ${{each.key}}, Account: ${{each.account_id}}"
  amount {
    specified_amount {
      currency_code = "USD"
      units = each.alert_limit
    }

  }

  budget_filter {
    credit_types_treatment = each.include_credits ? "INCLUDE_ALL_CREDITS" : "EXLUCDE_ALL_CREDITS"
  }

  threshold_rules {
    # Alert at 50% of alert budget spent
    threshold_percent = 0.5
  }
  threshold_rules {
    # Alert at 75% of alert budget spent
    threshold_percent = 0.75
  }
}


resource "google_billing_budget" "enforce_billing_budgets_alerts" {
  for_each = vars.billing_limits

  billing_account = each.account_id
  display_name = "Projected Enforcment Budget for ${{each.key}}, Account: ${{each.account_id}}"
  amount {
    specified_amount {
      currency_code = "USD"
      units = each.enforce_limit
    }

  }

  budget_filter {
    credit_types_treatment = each.include_credits ? "INCLUDE_ALL_CREDITS" : "EXLUCDE_ALL_CREDITS"
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
}

resource "google_billing_budget" "enforce_billing_budgets" {
  for_each = vars.billing_limits

  billing_account = each.account_id
  display_name = "Enforcment Budget for ${{each.key}}, Account: ${{each.account_id}}"
  amount {
    specified_amount {
      currency_code = "USD"
      units = each.enforce_limit
    }

  }

  budget_filter {
    credit_types_treatment = each.include_credits ? "INCLUDE_ALL_CREDITS" : "EXLUCDE_ALL_CREDITS"
  }

  threshold_rules {
    # Alert at 100% Enforcement budget
    threshold_percent = 1.0
  }

  all_updates_rule {
    pubsub_topic = google_pubsub_topic.billing_enforcement_topic.id
  }
}
