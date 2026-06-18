# ADR 002 — Redis for the alert queue & brief cache

- **Status:** Accepted
- **Date:** 2026-06-18

## Context

Alerts are generated asynchronously by a background scheduler, but they need to
reach connected WebSocket clients quickly. Separately, briefs are expensive to
regenerate (multiple agents + LLM calls), so re-running the pipeline on every
request is wasteful. We need a fast, decoupled mechanism for both.

## Decision

Use **Redis (GCP Memorystore)** for both the alert queue and the brief cache.

## Reasoning

- **Alert queue:** Redis Lists give us a simple producer-consumer queue. The
  scheduler `RPUSH`es alerts; the WebSocket layer `LPOP`s and pushes them to
  clients. This decouples alert *generation* from alert *delivery*.
- **Brief cache:** Cache generated briefs with a 12-hour TTL so repeated reads
  don't re-run the pipeline.

### Alternatives considered

- **PostgreSQL as a queue** — workable but polling-based, which adds latency and
  load.
- **GCP Pub/Sub** — overengineered for a single-region app at this scale.
- **In-memory queue** — lost on restart and doesn't survive multiple instances.

## Consequences

- Adds Memorystore to the infrastructure footprint.
- The scheduler is fully decoupled from the API/WebSocket layer.
- The brief cache must be invalidated when a user's portfolio changes.
