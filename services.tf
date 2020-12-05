provider "google" {
  project = vars.billing_enforcer_project
  region = "us-central1"
}

resource "google_project_service" "billing" {
  service = "cloudbilling.googleapis.com"
}

resource "google_project_service" "pubsub" {
  service = "pubsub.googleapis.com"
}

resource "google_project_service" "cloudfunctions" {
  service = "cloudfunctions.googleapis.com"
}

resource "google_project_service" "iam" {
  service = "iam.googleapis.com"
}

resource "google_project_service" "storage" {
  service = "storage.googleapis.com"
}
