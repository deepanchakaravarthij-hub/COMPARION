# ADR 0002: Normalize Before Comparing

## Status

Accepted

## Context

Document differences are noisy when inputs vary by rotation, scan quality, margins, resolution, or rendering path. Comparing raw assets directly would inflate false positives.

## Decision

Normalize documents before diffing. Normalization includes rendering, orientation correction, deskewing, denoising, layout extraction, and coordinate normalization into the Unified Document Model.

## Consequences

- Diff engines can operate on more stable data.
- Benchmark reports must track normalization failures separately from true comparison failures.
- Engine changes should record false-positive impact when they modify normalization behavior.
