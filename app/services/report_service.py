from __future__ import annotations

from html import escape
from typing import Any


def build_html_report(job: dict[str, Any], result: dict[str, Any]) -> str:
    rows = []
    for change in result["changes"]:
        rows.append(
            "<tr>"
            f"<td>{escape(change['id'])}</td>"
            f"<td>{escape(change['type'])}</td>"
            f"<td>{escape(change['category'])}</td>"
            f"<td>{escape(change['severity'])}</td>"
            f"<td>{change['confidence']:.2f}</td>"
            f"<td>{escape(change['message'])}</td>"
            "</tr>"
        )

    change_rows = "\n".join(rows) or ('<tr><td colspan="6">No changes detected.</td></tr>')

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
