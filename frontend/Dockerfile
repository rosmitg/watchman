# Multi-stage build for the Watchman frontend (React + Vite, served by nginx).
#
# Stage 1 builds the static bundle. The backend API URL and Supabase config are
# baked in at build time via build args (Vite inlines import.meta.env at build).
# The Supabase anon key is a public, browser-safe key. Stage 2 serves the bundle
# with nginx on port 8080 (Cloud Run's contract).

# ---------------------------------------------------------------------------
# Stage 1: build the static assets.
# ---------------------------------------------------------------------------
FROM node:20-alpine AS build

WORKDIR /app

# Install dependencies first to leverage Docker layer caching.
COPY package.json package-lock.json ./
RUN npm ci

# Copy the source and build config, then produce the production bundle.
COPY tsconfig.json vite.config.ts postcss.config.js tailwind.config.js index.html ./
COPY src ./src

# VITE_* values are inlined into the bundle at build time.
ARG VITE_API_URL
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_ANON_KEY
ENV VITE_API_URL=${VITE_API_URL} \
    VITE_SUPABASE_URL=${VITE_SUPABASE_URL} \
    VITE_SUPABASE_ANON_KEY=${VITE_SUPABASE_ANON_KEY}
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2: serve the static bundle with nginx.
# ---------------------------------------------------------------------------
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
