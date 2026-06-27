# Watchman — GCP Deployment

Watchman runs as **two Cloud Run services**, backed by **Cloud SQL** (Postgres
16), **Memorystore Redis**, **Secret Manager** for configuration, and
**Cloud Build** for CI/CD. Everything lives in project `watchman-gcp`, region
`australia-southeast1`.

```
                                                   ┌─► watchman-frontend (nginx/React)
GitHub (main) ──► Cloud Build ──► Artifact Registry ┤
                                                   └─► watchman-backend (FastAPI) ──► Cloud SQL
                                                                │  └──────────────► Memorystore Redis
                                                                └─────────────────► Secret Manager
Cloud Scheduler ──(daily 7am)──► watchman-backend /api/v1/brief/generate
```

## Two-service architecture

- **`watchman-frontend`** — the React/Vite single-page app, built to static
  files and served by **nginx** on port 8080. It has no server-side runtime and
  no secrets. The backend Cloud Run URL is **baked into the bundle at build
  time** via the Docker `--build-arg VITE_API_URL=...` (Vite inlines
  `import.meta.env` at build), so the browser calls the backend directly — nginx
  does not proxy. Changing the backend URL therefore requires a rebuild, not just
  a redeploy.
- **`watchman-backend`** — the FastAPI app on port 8000, wired to Cloud SQL,
  Memorystore Redis, and Secret Manager, and reachable by Cloud Scheduler.

Both images are built and deployed by the single `cloudbuild.yaml` pipeline and
share the `watchman-sa` runtime service account.

## Prerequisites

- The [`gcloud` CLI](https://cloud.google.com/sdk/docs/install) installed and
  authenticated: `gcloud auth login`.
- Owner/Editor (or equivalent granular) access to the `watchman-gcp` project, and
  billing enabled on it.
- Docker installed locally if you want to build/push images by hand.

## First-time setup

Run the provisioning script once. It enables APIs and creates the Artifact
Registry repo, the runtime service account and its roles, all Secret Manager
secrets (with placeholders), the Cloud SQL instance + `watchman` database, and
the Memorystore Redis instance:

```bash
cd infra/gcp
./setup.sh
```

The script creates billable resources and Cloud SQL/Redis take several minutes.
Review it before running. It is safe to re-run for secrets (it skips existing
ones) but Cloud SQL/Redis creation will error if those already exist — comment
out those steps on a re-run.

## Secrets

`setup.sh` creates every secret with the placeholder value `PLACEHOLDER_CHANGE_ME`.
Populate each with the real value before the service will work. Add a new version
to a secret with:

```bash
printf 'THE_REAL_VALUE' | gcloud secrets versions add SECRET_NAME --data-file=-
```

| Secret | What goes in it |
| --- | --- |
| `ANTHROPIC_API_KEY` | Anthropic API key (synthesis + agents) |
| `SUPABASE_URL` | Supabase project URL, e.g. `https://xxxx.supabase.co` |
| `SUPABASE_ANON_KEY` | Supabase anon/public key |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service-role key |
| `SUPABASE_JWT_SECRET` | Supabase JWT secret |
| `DATABASE_URL` | Async Postgres URL using the Cloud SQL socket (see below) |
| `REDIS_URL` | `redis://<MEMORYSTORE_HOST>:6379/0` (get host from `gcloud redis instances describe`) |
| `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` | Alpaca trading API credentials |
| `NEWS_API_KEY` | NewsAPI key |
| `PINECONE_API_KEY` | Pinecone API key |
| `VOYAGE_API_KEY` | Voyage AI embeddings key |
| `LANGCHAIN_API_KEY` | LangSmith API key |
| `HUGGINGFACE_API_KEY` | HuggingFace API key |

### Building `DATABASE_URL` for Cloud SQL

Cloud Run mounts the instance socket at
`/cloudsql/watchman-gcp:australia-southeast1:watchman-db`. The async URL uses
that path as the `host` query parameter (note the empty host before `/`):

```
postgresql+asyncpg://APP_USER:APP_PASSWORD@/watchman?host=/cloudsql/watchman-gcp:australia-southeast1:watchman-db
```

Create the `APP_USER` first:

```bash
gcloud sql users create APP_USER --instance=watchman-db --password=APP_PASSWORD
```

## Cloud Build trigger setup (connect GitHub repo)

The canonical deploy path is a Cloud Build trigger that fires on push to `main`:

1. Connect the GitHub repo (first time only):
   `gcloud builds connections` / Cloud Console → Cloud Build → Repositories →
   **Connect repository**, and authorize the Google Cloud Build GitHub App.
2. Create the trigger:

   ```bash
   gcloud builds triggers create github \
     --name=watchman-deploy \
     --repo-owner=rosmitg \
     --repo-name=watchman \
     --branch-pattern='^main$' \
     --build-config=infra/gcp/cloudbuild.yaml
   ```

When triggered this way, `$COMMIT_SHA` is populated automatically and the image
is tagged with it.

### GitHub Actions alternative (Workload Identity Federation)

`.github/workflows/ci.yml` also has a `deploy` job that runs on push to `main`
after tests pass. It authenticates with WIF and runs `gcloud builds submit`
against `cloudbuild.yaml`. It needs two repo secrets:

- `GCP_WORKLOAD_IDENTITY_PROVIDER` — full provider resource name, e.g.
  `projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/POOL/providers/PROVIDER`
- `GCP_SERVICE_ACCOUNT` — the deploy service account email (must have
  `roles/cloudbuild.builds.editor`, `roles/run.admin`, and
  `roles/iam.serviceAccountUser` on the runtime SA).

See the [WIF setup guide](https://github.com/google-github-actions/auth#setting-up-workload-identity-federation)
to create the pool/provider and bind the service account to the repo.

## Scheduler & auth

`scheduler.yaml` defines the `watchman-daily-brief` Cloud Scheduler job (7am
`Australia/Sydney`) that POSTs to `/api/v1/brief/generate` with a service-account
**OIDC token**.

> **Known gap:** that OIDC token is a Google-signed identity token used for Cloud
> Run IAM (`run.invoker`). The application's `/api/v1/brief/generate` endpoint
> currently authenticates with a **Supabase JWT** (`get_current_user_id`) and is
> scoped to a single user, so the scheduled call will not authenticate against
> the app as-is. Before relying on the schedule, resolve this — e.g. add a
> machine/cron auth path on the backend that accepts the Google OIDC token and
> generates briefs for all users, or have the scheduler call a dedicated internal
> endpoint. Tracked as a follow-up.

## Local vs production differences

| | Local / CI | Production (Cloud Run) |
| --- | --- | --- |
| Postgres | TCP: `postgresql+asyncpg://watchman:watchman@localhost:5432/watchman` | Cloud SQL Unix socket: `...@/watchman?host=/cloudsql/watchman-gcp:australia-southeast1:watchman-db` |
| Redis | `redis://localhost:6379/0` | Memorystore host: `redis://<MEMORYSTORE_HOST>:6379/0` |
| Config | `.env` file / CI env vars | Secret Manager (wired via Cloud Run `--set-secrets`) |
| Engine | plain async engine | `pool_pre_ping`, small pool (see `app/core/database.py`) |

The backend auto-detects the Cloud SQL socket via `settings.is_cloud_sql`
(true when `DATABASE_URL` contains `/cloudsql/`) and adjusts the engine
accordingly — no code change needed to switch environments, only the
`DATABASE_URL` value.
