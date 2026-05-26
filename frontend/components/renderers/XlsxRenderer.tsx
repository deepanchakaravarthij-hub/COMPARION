"use client";

import type { ArtifactLink, ChangeItem, JobResult } from "@/lib/types";

interface XlsxRendererProps {
  artifact: ArtifactLink;
  activeChange: ChangeItem | null;
  document: "a" | "b";
  result: JobResult;
  title: string;
}

export function XlsxRenderer({ activeChange, document, result, title }: XlsxRendererProps) {
  const sheets = result.viewer_hints?.anchors.sheets.length
    ? result.viewer_hints.anchors.sheets
    : unique(result.changes.map((change) => change.source_ref.sheet).filter(isString));
  const activeSheet = activeChange?.source_ref.sheet ?? sheets[0] ?? "Workbook";
  const sheetChanges = result.changes.filter(
    (change) =>
      change.source_ref.sheet === activeSheet &&
      ["both", document].includes(change.source_ref.document)
  );

  return (
    <section className="panel viewer-pane">
      <div className="panel-header">
        <h3>{title} Workbook</h3>
        <p>Sheet and cell anchors drive the grid highlights.</p>
      </div>
      <div className="panel-body">
        <div className="controls">
          {sheets.map((sheet) => (
            <span className={`badge ${sheet === activeSheet ? "success" : ""}`} key={sheet}>
              {sheet}
            </span>
          ))}
        </div>
        <div className="document-canvas">
          <table className="sheet-grid">
            <thead>
              <tr>
                <th>{activeSheet}</th>
                <th>Category</th>
                <th>Change</th>
              </tr>
            </thead>
            <tbody>
              {sheetChanges.map((change) => (
                <tr
                  className={activeChange?.id === change.id ? "highlight" : ""}
                  data-cell={change.source_ref.cell ?? undefined}
                  key={`${document}-${change.id}`}
                >
                  <th>{change.source_ref.cell ?? "sheet"}</th>
                  <td>{change.category}</td>
                  <td>{change.message}</td>
                </tr>
              ))}
              {sheetChanges.length === 0 ? (
                <tr>
                  <td colSpan={3}>No XLSX changes for this sheet.</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

function unique(values: string[]) {
  return [...new Set(values)];
}

function isString(value: string | null | undefined): value is string {
  return typeof value === "string";
}
