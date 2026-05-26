# ADR 0003: Use Normalized Coordinates

## Status

Accepted

## Context

Reports need to render overlays across pages, slides, sheets, and images that may have different pixel dimensions or display sizes.

## Decision

Store coordinates as normalized values between 0 and 1 wherever possible. Raw pixel coordinates may be retained only as debug metadata.

## Consequences

- Frontend overlays can scale across viewport sizes.
- Golden fixtures can remain stable across rendering DPI changes.
- Parsers must include source dimensions when converting to normalized coordinates.
