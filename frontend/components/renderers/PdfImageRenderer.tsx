"use client";

import type { ArtifactLink, ChangeItem, JobResult } from "@/lib/types";
import { normalizedBoxStyle } from "@/lib/viewer";
import { useArtifactObjectUrl } from "./useArtifactObjectUrl";

interface PdfImageRendererProps {
  artifact: ArtifactLink;
  activeChange: ChangeItem | null;
  result: JobResult;
  title: string;
}

export function PdfImageRenderer({ artifact, activeChange, result, title }: PdfImageRendererProps) {
  const { objectUrl, error } = useArtifactObjectUrl(artifact);
  const isPdf = result.file_type === "pdf";

  return (
    <section className="panel viewer-pane">
      <div className="panel-header">
        <h3>{title}</h3>
        <p>Bounding boxes use normalized coordinates from the API result.</p>
      </div>
      <div className="panel-body">
        {error ? <p className="badge danger">{error}</p> : null}
        {!objectUrl ? <p className="muted">Loading artifact...</p> : null}
        {objectUrl ? (
          <div className="document-canvas">
            {isPdf ? (
              <iframe src={objectUrl} title={`${title} PDF artifact`} />
            ) : (
              // eslint-disable-next-line @next/next/no-img-element
              <img alt={`${title} artifact`} src={objectUrl} />
            )}
            {activeChange?.bbox ? (
              <span className="overlay-box" style={normalizedBoxStyle(activeChange.bbox)} />
            ) : null}
          </div>
        ) : null}
      </div>
    </section>
  );
}
