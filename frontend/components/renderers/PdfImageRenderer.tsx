"use client";

import type { ArtifactLink, ChangeItem, JobResult, PreviewManifest } from "@/lib/types";
import { normalizedBoxStyle } from "@/lib/viewer";
import { useArtifactObjectUrl } from "./useArtifactObjectUrl";
import { usePreviewPages } from "./usePreviewPages";

interface PdfImageRendererProps {
  allChanges?: ChangeItem[];
  artifact: ArtifactLink;
  activeChange: ChangeItem | null;
  document: "a" | "b";
  jobId: string;
  previewManifest: PreviewManifest | null;
  result: JobResult;
  title: string;
}

function overlayClass(change: ChangeItem, activeId: string | null): string {
  const base = "overlay-box";
  const tone =
    change.type === "removed"
      ? "overlay-removed"
      : change.type === "added"
        ? "overlay-added"
        : "overlay-modified";
  const text = change.category === "text" ? "overlay-text" : "";
  const active = change.id === activeId ? "overlay-active" : "";
  return [base, tone, text, active].filter(Boolean).join(" ");
}

function isVisibleOverlay(bbox: NonNullable<ChangeItem["bbox"]>, category?: string) {
  const area = bbox.width * bbox.height;
  if (category === "structure" && area >= 0.99) {
    return true;
  }
  return area > 0.0005 && area < 0.9;
}

function activePageNumber(change: ChangeItem | null) {
  if (!change) {
    return 1;
  }
  return change.source_ref.page ?? change.source_ref.slide ?? 1;
}

export function PdfImageRenderer({
  allChanges = [],
  artifact,
  activeChange,
  document,
  jobId,
  previewManifest,
  result,
  title
}: PdfImageRendererProps) {
  const { objectUrl, error } = useArtifactObjectUrl(artifact);
  const isPdf = result.file_type === "pdf";
  const isPptx = result.file_type === "pptx";
  const isDocx = result.file_type === "docx";
  const usesPageStack = isPdf || isPptx || isDocx;
  const pageCount = previewManifest?.page_count ?? (usesPageStack ? 0 : 1);
  const previewPages = usePreviewPages(jobId, document, usesPageStack ? pageCount : 0);
  const activePage = activePageNumber(activeChange);

  // Changes that belong to this document side and have a bbox
  const sideChanges = allChanges.filter(
    (c) => c.bbox != null && (c.source_ref.document === document || c.source_ref.document === "both")
  );

  return (
    <section className="document-pane">
      <div className="document-pane-header">
        <div>
          <h3>{title}</h3>
          <p>
            {isPdf
              ? `${pageCount || "-"} pages`
              : isPptx
                ? `${pageCount || "-"} slides`
                : isDocx
                  ? `${pageCount || "-"} pages`
                  : "Image preview"}
          </p>
        </div>
        <div className="document-page-control">
          <span>{activePage}</span>
          <span>/</span>
          <span>{pageCount || 1}</span>
        </div>
      </div>
      <div className="document-scroll">
        {error || previewPages.error ? (
          <p className="badge danger">{error || previewPages.error}</p>
        ) : null}
        {usesPageStack && !previewPages.pages.length ? (
          <p className="muted">
            {isPptx ? "Rendering slides..." : isDocx ? "Rendering document pages..." : "Rendering pages..."}
          </p>
        ) : null}
        {usesPageStack ? (
          <div className="page-stack">
            {previewPages.pages.map((page) => {
              const pageOverlays = sideChanges.filter(
                (c) => c.bbox?.page === page.page && isVisibleOverlay(c.bbox, c.category)
              );
              return (
                <div
                  className={`rendered-page ${activePage === page.page ? "current-page" : ""}`}
                  key={page.page}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img alt={`${title} page ${page.page}`} src={page.url} />
                  {pageOverlays.map((change) => (
                    <span
                      className={overlayClass(change, activeChange?.id ?? null)}
                      key={change.id}
                      style={normalizedBoxStyle(change.bbox)}
                    />
                  ))}
                  <span className="page-number">{page.page}</span>
                </div>
              );
            })}
          </div>
        ) : objectUrl ? (
          <div className="rendered-page image-page">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img alt={`${title} artifact`} src={objectUrl} />
            {sideChanges
              .filter((c) => c.bbox && isVisibleOverlay(c.bbox, c.category))
              .map((change) => (
                <span
                  className={overlayClass(change, activeChange?.id ?? null)}
                  key={change.id}
                  style={normalizedBoxStyle(change.bbox)}
                  title={change.message}
                />
              ))}
          </div>
        ) : (
          <p className="muted">Loading artifact...</p>
        )}
      </div>
    </section>
  );
}
