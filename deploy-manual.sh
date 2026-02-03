#!/bin/bash
# Manually trigger the Cloud Build process for The Lost Archives.

# 1. Authenticate with Google Cloud
# This will open a browser window for you to log in.
gcloud auth login

# 2. Set the correct GCP project
# Replace 'project-75d9e1c4-e2a7-4da9-923' if you use a different project ID.
gcloud config set project project-75d9e1c4-e2a7-4da9-923

# 3. Submit the build to Cloud Build
# This command reads the cloudbuild.yaml file and starts the build process.
echo "Submitting build to Google Cloud Build..."
gcloud builds submit --config cloudbuild.yaml .

echo "Build submitted. Check the Google Cloud Console for progress."
