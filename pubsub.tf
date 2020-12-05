resource "google_pubsub_topic" "billing_enforcement_topic" {
  name = "billing-enforcer-queue"
}

resource "google_service_account" "billing_enforcer" {
  account_id = "billing-enforcer"
  display_name = "Billing Enforcer"
  description "Account used to enforce billing/budget limits on projects."
}

resoruce "google_pubsub_topic_iam_binding" "billing-enforcer" {
  project = google_pubsub_topic.billing_enforcement_topic.project
  topic = google_pubsub_topic.billing_enforcement_topic.name
  role = "roles/pubsub.subscriber"
  members = [
    contcat("serviceAccount:", google_service_account.billing_enforcer.email)
  ]
}

resource "google_cloudfunctions_function" "billing_enforcer" {
  name = "billing_enforcer"
  description = "GCF responsible for disabling billing on projects that have reached their budgeted limit."

  runtime = python37
  available_memory_mb = 128
  event_trigger {
    event_type = "google.pubsub.topic.publish"
    resource = google_pubsub_topic.billing_enforcement_topic.id
  }

  service_account_email = google_service_account.billing_enforcer.email

  source_archive_bucket = google_storage_bucket.enforcer-gcf-source.name
  source_archive_object = google_storage_bucket_object.enforcer-source-archive.name

  entry_point = "stop_billing"

  environment_variables = {
   # Exclude the billing enforcer project from enforcement, so it doesn't kill itself.
   ENFORCE_EXEMPT_PROJECTS = join(",", flatten([vars.billing_enforcer_project, vars.enforcement_exempt_projects]))
   SLACK_ACCESS_TOKEN = vars.slack_token
   SLACK_CHANNEL = vars.slack_channel
  }
}

resource "google_storage_bucket" "enforcer-gcf-source" {
  name = "pvj-enforcer-gcf-source"
  location = "US"

  uniform_bucket_level_access = true
}

data "archive_file" "enforcer-source" {
  type = "zip"
  source_dir = "./enforcer-source"
  output_path = "./enforcer-source.zip"
}


resource "google_storage_bucket_object" "enforcer-source-archive" {
  name = "index.zip"
  bucket = google_storage_bucket.enforcer-gcf-source.name
  source = "./enforcer-source.zip"
}
