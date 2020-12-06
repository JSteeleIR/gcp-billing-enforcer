terraform {
  required_providers {
    google = {
      source = "hashicorp/google"
      version = ">= 3.49.0"
    }
    googlebeta = {
      source = "hashicorp/google-beta"
      version = ">= 3.49.0"
    }
  }
}

resource "google_project_service" "billing" {
  project = var.billing_enforcer_project
  service = "cloudbilling.googleapis.com"
}

resource "google_project_service" "billingbudgets" {
  project = var.billing_enforcer_project
  service = "billingbudgets.googleapis.com"
}

resource "google_project_service" "pubsub" {
  project = var.billing_enforcer_project
  service = "pubsub.googleapis.com"
}

resource "google_project_service" "cloudfunctions" {
  project = var.billing_enforcer_project
  service = "cloudfunctions.googleapis.com"
}

resource "google_project_service" "cloudbuild" {
  project = var.billing_enforcer_project
  service = "cloudbuild.googleapis.com"
}

resource "google_project_service" "iam" {
  project = var.billing_enforcer_project
  service = "iam.googleapis.com"
}

resource "google_project_service" "storage" {
  project = var.billing_enforcer_project
  service = "storage.googleapis.com"
}
