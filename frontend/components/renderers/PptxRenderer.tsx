"use client";

import type { ArtifactLink, ChangeItem, JobResult } from "@/lib/types";
import { normalizedBoxStyle } from "@/lib/viewer";

interface PptxRendererProps {
  artifact: ArtifactLink;
  activeChange: ChangeItem | null;
  document: "a" | "b";
  result: JobResult;
  title: string;
}

export function PptxRenderer({ activeChange, document, result, title }: PptxRendererProps) {
  const slides = result.viewer_hints?.anchors.slides.length
    ? result.viewer_hints.anchors.slides
    : unique(result.changes.map((change) => change.source_ref.slide).filter(isNumber));
  const activeSlide = activeChange?.source_ref.slide ?? slides[0] ?? 1;
  const slideChanges = result.changes.filter(
    (change) =>
      change.source_ref.slide === activeSlide &&
      ["both", document].includes(change.source_ref.document)
  );

  return (
    <section className="panel viewer-pane">
      <div className="panel-header">
        <h3>{title} Presentation</h3>
        <p>Slide timeline with object-level text, table, image, and visual anchors.</p>
      </div>
      <div className="panel-body">
        <div className="controls">
          {slides.map((slide) => (
            <span className={`badge ${slide === activeSlide ? "success" : ""}`} key={slide}>
              Slide {slide}
            </span>
          ))}
        </div>
        <div className="document-canvas">
          <div className="slide-frame">
            <h3>Slide {activeSlide}</h3>
            {slideChanges.map((change, index) => (
              <article
                className={`structured-row ${activeChange?.id === change.id ? "highlight" : ""}`}
                key={`${document}-${change.id}`}
                style={{ marginTop: index * 8 }}
              >
                <span className="badge">{change.category}</span>
                <p>{change.message}</p>
              </article>
            ))}
            {activeChange?.bbox ? (
              <span className="overlay-box" style={normalizedBoxStyle(activeChange.bbox)} />
            ) : null}
          </div>
        </div>
      </div>
    </section>
  );
}

function isNumber(value: number | null | undefined): value is number {
  return typeof value === "number";
}

function unique(values: number[]) {
  return [...new Set(values)];
}
