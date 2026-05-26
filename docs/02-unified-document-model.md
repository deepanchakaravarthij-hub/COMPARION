# Unified Document Model (UDM)

## Core node
- `doc_id`, `version_id`, `format`
- `pages[]` or `sheets[]` or `slides[]`
- `blocks[]` each with:
  - `block_id`
  - `type` (paragraph, table, image, signature, stamp, chart, shape, cell)
  - `text`
  - `bbox_norm`
  - `confidence`
  - `style`
  - `metadata`

## Why
UDM enables one diff/report pipeline across file types.
