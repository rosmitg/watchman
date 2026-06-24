#!/usr/bin/env bash
#
# One-time GCP project setup for Watchman.
#
# Provisions everything the Cloud Run deployment depends on: APIs, Artifact
# Registry, the runtime service account and its roles, Secret Manager secrets
# (with placeholder values you must populate afterwards), Cloud SQL, the
# application database, and Memorystore Redis.
#
# This script is idempotent-ish but assumes a fresh project. Review each step
# before running — it creates billable resources. Run it yourself; the assistant
# does not execute gcloud.
#
#   ./setup.sh
#
set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PROJECT_ID="watchman-500414"
REGION="australia-southeast1"
REPO="watchman"
SERVICE_ACCOUNT_NAME="watchman-sa"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
SQL_INSTANCE="watchman-db"
SQL_DATABASE="watchman"
SQL_TIER="db-g1-small"
REDIS_INSTANCE="watchman-redis"

# All secrets the Cloud Run service expects (see cloudbuild.yaml --set-secrets).
SECRETS=(
  ANTHROPIC_API_KEY
  SUPABASE_URL
  SUPABASE_ANON_KEY
  SUPABASE_SERVICE_ROLE_KEY
  SUPABASE_JWT_SECRET
  DATABASE_URL
  REDIS_URL
  ALPACA_API_KEY
  ALPACA_SECRET_KEY
  NEWS_API_KEY
  PINECONE_API_KEY
  VOYAGE_API_KEY
  LANGCHAIN_API_KEY
  HUGGINGFACE_API_KEY
)

echo "Configuring gcloud for project ${PROJECT_ID}..."
gcloud config set project "${PROJECT_ID}"

# ---------------------------------------------------------------------------
# 1. Enable the APIs this stack relies on.
# ---------------------------------------------------------------------------
echo "Enabling required APIs..."
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  redis.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  cloudscheduler.googleapis.com

# ---------------------------------------------------------------------------
# 2. Artifact Registry: a Docker repo to hold the backend image.
# ---------------------------------------------------------------------------
echo "Creating Artifact Registry repo '${REPO}'..."
gcloud artifacts repositories create "${REPO}" \
  --repository-format=docker \
  --location="${REGION}" \
  --description="Watchman container images"

# ---------------------------------------------------------------------------
# 3. Runtime service account + IAM roles.
#    - run.invoker:               allows Cloud Scheduler (using this SA) to call
#                                 the Cloud Run service.
#    - cloudsql.client:           lets the service connect to Cloud SQL.
#    - secretmanager.secretAccessor: lets the service read its secrets at runtime.
# ---------------------------------------------------------------------------
echo "Creating service account '${SERVICE_ACCOUNT_EMAIL}'..."
gcloud iam service-accounts create "${SERVICE_ACCOUNT_NAME}" \
  --display-name="Watchman Cloud Run runtime"

for ROLE in roles/run.invoker roles/cloudsql.client roles/secretmanager.secretAccessor; do
  echo "Granting ${ROLE} to the service account..."
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="${ROLE}"
done

# ---------------------------------------------------------------------------
# 4. Secret Manager: create each secret with a placeholder value.
#    Populate the real values afterwards (see README "Secrets").
# ---------------------------------------------------------------------------
echo "Creating secrets with placeholder values..."
for SECRET in "${SECRETS[@]}"; do
  if gcloud secrets describe "${SECRET}" >/dev/null 2>&1; then
    echo "  ${SECRET} already exists, skipping."
  else
    echo "  Creating ${SECRET}..."
    printf 'PLACEHOLDER_CHANGE_ME' | gcloud secrets create "${SECRET}" \
      --replication-policy="automatic" \
      --data-file=-
  fi
done

# ---------------------------------------------------------------------------
# 5. Cloud SQL: a small Postgres 16 instance for the application database.
#    db-g1-small is the cheapest shared-core tier — fine for dev/early prod.
# ---------------------------------------------------------------------------
echo "Creating Cloud SQL instance '${SQL_INSTANCE}' (this takes several minutes)..."
gcloud sql instances create "${SQL_INSTANCE}" \
  --database-version=POSTGRES_16 \
  --tier="${SQL_TIER}" \
  --region="${REGION}"

echo "Creating database '${SQL_DATABASE}'..."
gcloud sql databases create "${SQL_DATABASE}" \
  --instance="${SQL_INSTANCE}"

# Reminder: create an application DB user and put the full async DATABASE_URL
# (with the Cloud SQL socket host) into the DATABASE_URL secret. See README.

# ---------------------------------------------------------------------------
# 6. Memorystore Redis: basic tier, 1GB, for caching and the alert pub/sub.
# ---------------------------------------------------------------------------
echo "Creating Memorystore Redis instance '${REDIS_INSTANCE}'..."
gcloud redis instances create "${REDIS_INSTANCE}" \
  --size=1 \
  --region="${REGION}" \
  --tier=basic \
  --redis-version=redis_7_0

echo
echo "Setup complete. Next steps:"
echo "  1. Populate every secret in Secret Manager with real values (see README)."
echo "  2. Build the DATABASE_URL and REDIS_URL secrets from the created instances."
echo "  3. Connect the GitHub repo as a Cloud Build trigger (see README)."
