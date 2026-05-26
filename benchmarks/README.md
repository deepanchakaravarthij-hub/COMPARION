# Benchmark Fixtures

This folder defines the fixture layout for repeatable comparison testing.

## Layout

```text
benchmarks/
  fixtures/
    pdf/
    image/
    scanned/
    docx/
    xlsx/
    pptx/
  expected/
```

## Naming

Use paired files with a shared case prefix:

```text
case-001-a.pdf
case-001-b.pdf
case-001-expected.json
```

## Rules

- Keep synthetic fixtures small enough for CI.
- Do not commit confidential documents.
- Include a short note for each fixture describing the intended change.
- Record benchmark deltas when normalization or diff logic changes.
