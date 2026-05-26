"use client";

import type { ArtifactLink, ChangeItem, JobResult } from "@/lib/types";

interface FallbackRendererProps {
  artifact: ArtifactLink;
  activeChange: ChangeItem | null;
  document: "a" | "b";
  result: JobResult;
  title: string;
}

export function FallbackRenderer({ activeChange, document, result, title }: FallbackRendererProps) {
  const sideChanges = result.changes.filter((change) =>
    ["both", document].includes(change.source_ref.document)
  );

  return (
    <section className="panel viewer-pane">
      <div className="panel-header">
        <h3>{title}</h3>
        <p>Generic structured change rendering.</p>
      </div>
      <div className="panel-body">
        <div className="document-canvas structured-doc">
          {sideChanges.map((change) => (
            <article
              className={`structured-row ${activeChange?.id === change.id ? "highlight" : ""}`}
              key={`${document}-${change.id}`}
            >
              <span className="badge">{change.category}</span>
              <p>{change.message}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
