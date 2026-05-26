# ADR 0001: Record Architecture Decisions

## Status

Accepted

## Context

COMPARION will make several implementation choices that affect accuracy, performance, and operability. The team needs a lightweight way to capture decisions and revisit them as benchmark evidence improves.

## Decision

Use Architecture Decision Records under `docs/adr/`. Each ADR should include status, context, decision, consequences, and follow-up notes when needed.

## Consequences

- Important choices are reviewable in pull requests.
- Reversing or superseding a choice should create a new ADR instead of rewriting history.
