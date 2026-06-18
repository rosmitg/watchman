# ADR 001 — LangGraph over CrewAI

- **Status:** Accepted
- **Date:** 2026-06-18

## Context

Watchman runs a multi-agent pipeline of five agents (news, fundamentals,
sentiment, SEC, synthesis) that all read from and write to a shared state. We
need a framework that gives us explicit control over how that state flows
between agents, that is easy to debug and unit test, and that traces cleanly so
we can see what each agent did.

## Decision

Use **LangGraph** to orchestrate the agent pipeline.

## Reasoning

| Dimension       | LangGraph                              | CrewAI                              |
| --------------- | -------------------------------------- | ----------------------------------- |
| State control   | Explicit `TypedDict` state            | Implicit, passed via task context   |
| Execution model | Directed graph of nodes & edges        | Role-based delegation between agents |
| Observability   | Native LangSmith per-node traces       | Limited                             |
| Debugging       | Plain Python functions                 | Opaque agent-to-agent handoffs      |
| Flexibility     | Full control over edges & branching    | Convention-heavy                    |

CrewAI's role-based delegation is convenient for open-ended agent collaboration,
but our pipeline is a deterministic, ordered DAG. We want the state contract to
be the design, not an emergent property of agent conversations.

## Consequences

- Each agent is a plain `async` Python function — trivial to unit test in
  isolation.
- `WatchmanState` (a `TypedDict`) is the single source of truth that every node
  reads and updates.
- LangSmith gives us per-node traces for free, so we can see exactly what each
  agent produced during a run.
