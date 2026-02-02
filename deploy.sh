#!/bin/bash
set -e

PROJECT_ID="the-lost-archives"  # Ajustar se necessário
REGION="us-central1"
SERVICE_NAME="lost-archives"

echo "Building Docker image..."
docker build -t gcr.io/$PROJECT_ID/$SERVICE_NAME .

echo "Pushing to Container Registry..."
docker push gcr.io/$PROJECT_ID/$SERVICE_NAME

echo "Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --timeout 900 \
  --set-env-vars "GOOGLE_API_KEY=$GOOGLE_API_KEY,PEXELS_API_KEY=$PEXELS_API_KEY"

echo "Done! Service URL:"
gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)'
