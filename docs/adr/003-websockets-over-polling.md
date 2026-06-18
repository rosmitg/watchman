# ADR 003 — WebSockets over HTTP polling

- **Status:** Accepted
- **Date:** 2026-06-18

## Context

Alerts in Watchman are time-sensitive — a significant price move or breaking
filing is only useful if the user sees it fast. We need sub-second delivery of
alerts to the frontend.

## Decision

Use **WebSockets** via FastAPI's native WebSocket support.

## Reasoning

| Dimension   | WebSockets                          | HTTP polling                          |
| ----------- | ----------------------------------- | ------------------------------------- |
| Latency     | Push, sub-second                    | Pull, bounded by polling interval     |
| Server load | One persistent connection per client | N requests/minute per client          |
| Complexity  | Connection lifecycle management      | Trivially simple                      |
| UX          | Instant, live updates               | Laggy or wasteful depending on interval |

Polling at 30s is too slow for time-sensitive alerts; polling at 5s hammers the
API for data that usually hasn't changed. FastAPI ships with first-class
WebSocket support, so the server side is straightforward.

### Alternatives considered

- **Server-Sent Events (SSE)** — unidirectional; fine for push but we want a
  bidirectional channel for client acks/subscriptions.
- **GCP Pub/Sub + polling** — overengineered for this use case.

## Consequences

- The frontend must manage the WebSocket connection lifecycle (reconnects,
  backoff).
- Cloud Run request/idle timeouts must be configured to allow long-lived
  connections.
- Zustand holds alert state on the client, updated as messages arrive.
