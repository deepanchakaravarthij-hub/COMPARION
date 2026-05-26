from __future__ import annotations

from html import escape
from typing import Any


def build_html_report(job: dict[str, Any], result: dict[str, Any]) -> str:
    rows = []
    for category, changes in _group_changes(result["changes"]).items():
        if result["file_type"] in {"docx", "xlsx", "pptx"}:
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
  {_semantic_sections(result)}
  {_xlsx_sections(result)}
  {_pptx_sections(result)}
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
    order = [
        "sheet",
        "formula",
        "text",
        "formatting",
        "table",
        "image",
        "structure",
        "visual",
        "metadata",
        "file",
    ]
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
    for key in [
        "document",
        "sheet",
        "slide",
        "cell",
        "part",
        "paragraph",
        "run",
        "table",
        "row",
        "column",
        "image",
        "page",
    ]:
        value = source_ref.get(key)
        if value is not None:
            labels.append(f"{key}={value}")
    return ", ".join(labels)


def _xlsx_sections(result: dict[str, Any]) -> str:
    if result.get("file_type") != "xlsx":
        return ""
    xlsx_diagnostics = result.get("diagnostics", {}).get("xlsx", {})
    sheet_summary = xlsx_diagnostics.get("sheet_summary", [])
    changed_cells = xlsx_diagnostics.get("changed_cells", [])

    summary_rows = "\n".join(
        "<tr>"
        f"<td>{escape(item['sheet'])}</td>"
        f"<td>{escape(item['sheet_b'])}</td>"
        f"<td>{item['position_a']}</td>"
        f"<td>{item['position_b']}</td>"
        f"<td>{item['cells_a']}</td>"
        f"<td>{item['cells_b']}</td>"
        "</tr>"
        for item in sheet_summary
    ) or "<tr><td colspan='6'>No matched sheets.</td></tr>"

    cell_rows = "\n".join(
        "<tr>"
        f"<td>{escape(item['sheet'])}</td>"
        f"<td>{escape(item['cell'])}</td>"
        f"<td>{escape(item['kind'])}</td>"
        f"<td>{escape(str(item['old']))}</td>"
        f"<td>{escape(str(item['new']))}</td>"
        "</tr>"
        for item in changed_cells
    ) or "<tr><td colspan='5'>No changed cells.</td></tr>"

    return (
        "<h2>Sheet summary</h2>"
        "<table><thead><tr>"
        "<th>Sheet A</th><th>Sheet B</th><th>Position A</th><th>Position B</th>"
        "<th>Cells A</th><th>Cells B</th>"
        "</tr></thead><tbody>"
        f"{summary_rows}"
        "</tbody></table>"
        "<h2>Changed cells</h2>"
        "<table><thead><tr>"
        "<th>Sheet</th><th>Cell</th><th>Kind</th><th>Old</th><th>New</th>"
        "</tr></thead><tbody>"
        f"{cell_rows}"
        "</tbody></table>"
    )


def _pptx_sections(result: dict[str, Any]) -> str:
    if result.get("file_type") != "pptx":
        return ""
    pptx_diagnostics = result.get("diagnostics", {}).get("pptx", {})
    slide_summary = pptx_diagnostics.get("slide_summary", [])
    changed_objects = pptx_diagnostics.get("changed_objects", [])

    slide_rows = "\n".join(
        "<tr>"
        f"<td>{item['slide_a']}</td>"
        f"<td>{item['slide_b']}</td>"
        f"<td>{escape(str(item['title_a']))}</td>"
        f"<td>{escape(str(item['title_b']))}</td>"
        f"<td>{item['objects_a']}</td>"
        f"<td>{item['objects_b']}</td>"
        "</tr>"
        for item in slide_summary
    ) or "<tr><td colspan='6'>No matched slides.</td></tr>"

    object_rows = "\n".join(
        "<tr>"
        f"<td>{item['slide']}</td>"
        f"<td>{escape(item['kind'])}</td>"
        f"<td>{escape(str(item['object_a']))}</td>"
        f"<td>{escape(str(item['object_b']))}</td>"
        f"<td>{escape(str(item['type_a']))}</td>"
        f"<td>{escape(str(item['type_b']))}</td>"
        "</tr>"
        for item in changed_objects
    ) or "<tr><td colspan='6'>No changed objects.</td></tr>"

    return (
        "<h2>Slide summary</h2>"
        "<table><thead><tr>"
        "<th>Slide A</th><th>Slide B</th><th>Title A</th><th>Title B</th>"
        "<th>Objects A</th><th>Objects B</th>"
        "</tr></thead><tbody>"
        f"{slide_rows}"
        "</tbody></table>"
        "<h2>Object changes</h2>"
        "<table><thead><tr>"
        "<th>Slide</th><th>Change kind</th><th>Object A</th><th>Object B</th>"
        "<th>Type A</th><th>Type B</th>"
        "</tr></thead><tbody>"
        f"{object_rows}"
        "</tbody></table>"
    )


def _semantic_sections(result: dict[str, Any]) -> str:
    semantic = result.get("semantic")
    if not semantic:
        return ""
    summary = escape(str(semantic.get("summary", "")))
    provenance = semantic.get("provenance", {})
    confidence = provenance.get("confidence", 0.0)
    matches = semantic.get("semantic_matches", [])
    risk_summary = semantic.get("risk_summary", {})
    risk_count = risk_summary.get("high_risk_count", 0)
    risk_rows = "\n".join(
        "<tr>"
        f"<td>{escape(str(item.get('change_id')))}</td>"
        f"<td>{escape(str(item.get('domain')))}</td>"
        f"<td>{escape(str(item.get('reason')))}</td>"
        f"<td>{escape(str(item.get('severity')))}</td>"
        "</tr>"
        for item in risk_summary.get("items", [])
    ) or "<tr><td colspan='4'>No high-risk findings.</td></tr>"
    match_rows = "\n".join(
        "<tr>"
        f"<td>{escape(str(item.get('left_id')))}</td>"
        f"<td>{escape(str(item.get('right_id')))}</td>"
        f"<td>{escape(str(item.get('score')))}</td>"
        "</tr>"
        for item in matches[:20]
    ) or "<tr><td colspan='3'>No semantic matches.</td></tr>"
    return (
        "<h2>Semantic summary</h2>"
        f"<p>{summary}</p>"
        f"<p><strong>Semantic confidence:</strong> {confidence} | "
        f"<strong>High-risk findings:</strong> {risk_count}</p>"
        "<h3>Risk findings</h3>"
        "<table><thead><tr><th>Change</th><th>Domain</th><th>Reason</th><th>Severity</th>"
        "</tr></thead><tbody>"
        f"{risk_rows}"
        "</tbody></table>"
        "<h3>Semantic matches</h3>"
        "<table><thead><tr><th>Left</th><th>Right</th><th>Score</th></tr></thead><tbody>"
        f"{match_rows}"
        "</tbody></table>"
    )
