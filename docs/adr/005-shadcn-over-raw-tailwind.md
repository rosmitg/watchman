# ADR 005 — shadcn/ui over raw Tailwind

- **Status:** Accepted
- **Date:** 2026-06-18

## Context

The Watchman frontend needs a consistent set of UI components — cards, badges,
alerts, modals, toasts — to present briefs and live alerts. We want
production-quality, accessible components without spending the project's time
budget on CSS craftsmanship.

## Decision

Use **shadcn/ui** for UI components.

## Reasoning

shadcn/ui copies component source directly into `src/components/ui/`, so we own
the code outright and can modify it freely — there's no opaque dependency to
fight. Components are built on Radix UI primitives, which handle accessibility
(ARIA attributes, keyboard navigation, focus management) correctly out of the
box, and ship with production-quality defaults that keep the design consistent.

### Alternatives considered

- **Raw Tailwind** — maximum flexibility, but building accessible cards, modals,
  and toasts from scratch is hours of work we'd rather spend on AI engineering.
- **Chakra / MUI** — opinionated and heavy; harder to customize to a bespoke
  design.
- **Headless UI** — solid but less comprehensive than Radix; fewer primitives.

For a portfolio project meant to demonstrate AI engineering depth rather than CSS
craftsmanship, shadcn/ui is the right tradeoff.

## Consequences

- Components are installed individually via `npx shadcn-ui`.
- Tailwind config is extended with CSS variables for theming.
- Zustand handles application state; shadcn/ui is used for UI only.
