"use client";

import type { ArtifactLink, ChangeItem, JobResult } from "@/lib/types";
import { sourceLabel } from "@/lib/viewer";

interface DocxRendererProps {
  artifact: ArtifactLink;
  activeChange: ChangeItem | null;
  document: "a" | "b";
  result: JobResult;
  title: string;
}

export function DocxRenderer({ activeChange, document, result, title }: DocxRendererProps) {
  const docChanges = result.changes.filter((change) =>
    ["both", document].includes(change.source_ref.document)
  );

  return (
    <section className="panel viewer-pane">
      <div className="panel-header">
        <h3>{title} DOCX Structure</h3>
        <p>Paragraph, run, table, image, and structure anchors from source references.</p>
      </div>
      <div className="panel-body">
        <div className="document-canvas structured-doc">
          {docChanges.map((change) => (
            <article
              className={`structured-row ${activeChange?.id === change.id ? "highlight" : ""}`}
              data-change-id={change.id}
              key={`${document}-${change.id}`}
            >
              <div className="controls">
                <span className="badge">{change.category}</span>
                <span className="badge">{sourceLabel(change.source_ref)}</span>
              </div>
              <p>{change.message}</p>
            </article>
          ))}
          {docChanges.length === 0 ? <p className="muted">No DOCX changes for this side.</p> : null}
        </div>
      </div>
    </section>
  );
}
