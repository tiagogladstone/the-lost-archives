# Deploy Troubleshooting for The Lost Archives

## Problem: New commits are not being deployed to Cloud Run

On 2026-02-02, it was observed that commit `ebfa6d2` was not deployed to the Cloud Run service. The running service was still an older version.

## Investigation

1.  **GitHub Actions:** There are no GitHub Actions workflows (`.github/workflows`) in the repository. This indicates that the automated deployment is not handled by GitHub Actions.
2.  **Cloud Build Configuration:** The `cloudbuild.yaml` and `Dockerfile` are present and correctly configured for a standard Cloud Run deployment.
3.  **Probable Cause:** The issue is most likely with the **Cloud Build Trigger**. The trigger, which is configured in the Google Cloud Console, is supposed to detect new commits to the repository and start the build process. It likely failed to fire or the subsequent build/deploy steps failed.

## How to Verify Builds in Google Cloud Console

1.  Go to the Google Cloud Console: [https://console.cloud.google.com](https://console.cloud.google.com)
2.  Navigate to **Cloud Build** -> **History**.
3.  Select your project (`project-75d9e1c4-e2a7-4da9-923`).
4.  Check the build history for any failed builds corresponding to the commit `ebfa6d2`. This will give you the logs and the reason for the failure.

## How to Deploy Manually

If the automated trigger is failing, you can deploy the latest version manually using a script.

### Using the Manual Script

A script `deploy-manual.sh` has been created to simplify this process.

1.  **Open your terminal.**
2.  **Navigate to the project directory:**
    ```bash
    cd /Users/clawdbot/clawd/projects/the-lost-archives/
    ```
3.  **Run the script:**
    ```bash
    ./deploy-manual.sh
    ```
4.  The script will guide you through:
    *   Logging into your Google Cloud account (a browser window will open).
    *   Setting the correct GCP project.
    *   Submitting the build.
5.  You can monitor the build progress in the Cloud Build history page mentioned above.

### Alternative: Direct Deploy with `gcloud run deploy`

As an alternative, you can build and deploy directly from your local source code using a single `gcloud` command. This is faster for smaller changes as it combines build and deploy steps.

```bash
gcloud run deploy lost-archives \
  --source . \
  --region us-central1 \
  --project project-75d9e1c4-e2a7-4da9-923 \
  --allow-unauthenticated \
  --memory 2Gi \
  --timeout 900
```
This command will build the container image from the current directory and deploy it to the `lost-archives` service.
