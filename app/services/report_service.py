from __future__ import annotations

from html import escape
from typing import Any


def build_html_report(job: dict[str, Any], result: dict[str, Any]) -> str:
    rows = []
    for category, changes in _group_changes(result["changes"]).items():
        if result["file_type"] == "docx":
            rows.append(
                '<tr class="group">'
                f'<td colspan="7">{escape(category.title())} changes ({len(changes)})</td>'
                "</tr>"
            )
        for change in changes:
            rows.append(
                "<tr>"
                f"<td>{escape(change['id'])}</td>"
                f"<td>{escape(change['type'])}</td>"
                f"<td>{escape(change['category'])}</td>"
                f"<td>{escape(change['severity'])}</td>"
                f"<td>{change['confidence']:.2f}</td>"
                f"<td>{escape(_source_ref(change.get('source_ref', {})))}</td>"
                f"<td>{escape(change['message'])}</td>"
                "</tr>"
            )

    change_rows = "\n".join(rows) or ('<tr><td colspan="7">No changes detected.</td></tr>')

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>COMPARION Report {escape(job["job_id"])}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 2rem; color: #1f2937; }}
    h1 {{ font-size: 1.6rem; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; }}
    th, td {{ border: 1px solid #d1d5db; padding: 0.5rem; text-align: left; }}
    th {{ background: #f3f4f6; }}
    .summary {{ padding: 1rem; background: #eef2ff; border-left: 4px solid #4f46e5; }}
    .group td {{ background: #f9fafb; font-weight: bold; }}
  </style>
</head>
<body>
  <h1>COMPARION Report</h1>
  <p><strong>Job:</strong> {escape(job["job_id"])}</p>
  <p><strong>Files:</strong> {escape(job["file_a"])} vs {escape(job["file_b"])}</p>
  <p><strong>File type:</strong> {escape(result["file_type"])}</p>
  <div class="summary">{escape(result["summary"])}</div>
  <table>
    <thead>
      <tr>
        <th>ID</th>
        <th>Type</th>
        <th>Category</th>
        <th>Severity</th>
        <th>Confidence</th>
        <th>Source</th>
        <th>Message</th>
      </tr>
    </thead>
    <tbody>
      {change_rows}
    </tbody>
  </table>
</body>
</html>
"""


def _group_changes(changes: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    order = ["text", "formatting", "table", "image", "structure", "visual", "metadata", "file"]
    for category in order:
        category_changes = [change for change in changes if change["category"] == category]
        if category_changes:
            grouped[category] = category_changes
    for change in changes:
        grouped.setdefault(change["category"], [])
        if change not in grouped[change["category"]]:
            grouped[change["category"]].append(change)
    return grouped


def _source_ref(source_ref: dict[str, Any]) -> str:
    if not source_ref:
        return ""

    labels = []
    for key in ["document", "part", "paragraph", "run", "table", "row", "column", "image", "page"]:
        value = source_ref.get(key)
        if value is not None:
            labels.append(f"{key}={value}")
    return ", ".join(labels)
