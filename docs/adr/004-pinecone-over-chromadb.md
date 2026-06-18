# ADR 004 — Pinecone over ChromaDB

- **Status:** Accepted
- **Date:** 2026-06-18

## Context

We store embeddings of news articles and SEC filings to support semantic search
and give the synthesis agent relevant historical context. We need a vector store
that fits our deployment model.

## Decision

Use **Pinecone** as the vector store.

## Reasoning

ChromaDB requires a persistent volume to hold its index. Cloud Run is stateless
and its containers are ephemeral — running ChromaDB there means either a sidecar
with a volume mount or a separate always-on instance, both of which add
operational complexity. Pinecone is a fully managed HTTP API with zero infra to
run and a generous free tier.

| Dimension              | Pinecone                  | ChromaDB                          |
| ---------------------- | ------------------------- | --------------------------------- |
| Cloud Run compatibility | Native (stateless HTTP)  | Needs persistent volume / sidecar |
| Ops overhead           | None (managed)            | Self-hosted, must manage storage  |
| Cost                   | Free tier, pay as you grow | "Free" but you run the infra      |
| Portability            | Vendor API                | Open source, self-hostable        |

We accept the vendor dependency in exchange for zero operational overhead on a
stateless platform.

## Consequences

- Pinecone API key lives in GCP Secret Manager.
- Embeddings use Voyage AI, consistent with the STK project.
- One Pinecone index per environment (dev / prod).
