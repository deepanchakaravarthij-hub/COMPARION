"use client";

import { useEffect, useMemo, useState } from "react";
import { downloadComparisonPdf } from "@/lib/api-client";
import type {
  ArtifactLink,
  ChangeItem,
  JobResult,
  JobStatusResponse,
  PreviewManifest
} from "@/lib/types";
import { recordTelemetry } from "@/lib/telemetry";
import { fileKindLabel } from "@/lib/viewer";
import { ChangeList } from "./ChangeList";
import { RiskPanel } from "./RiskPanel";
import { DiffRenderer } from "../renderers/DiffRenderer";

interface ViewerShellProps {
  job: JobStatusResponse;
  result: JobResult;
  artifacts: {
    a: ArtifactLink;
    b: ArtifactLink;
  };
  previewManifests: {
    a: PreviewManifest | null;
    b: PreviewManifest | null;
  };
}

export function ViewerShell({ job, result, artifacts, previewManifests }: ViewerShellProps) {
  const [activeChange, setActiveChange] = useState<ChangeItem | null>(result.changes[0] ?? null);
  const [downloadError, setDownloadError] = useState("");
  const [filters, setFilters] = useState({
    category: "",
    severity: "",
    semanticLabel: "",
    search: ""
  });
  const activeIndex = useMemo(
    () => result.changes.findIndex((change) => change.id === activeChange?.id),
    [activeChange?.id, result.changes]
  );
  const exportFilename = `${job.file_a} \u2192 ${job.file_b} - Draftable.pdf`;

  useEffect(() => {
    recordTelemetry("viewer_first_render", {
      jobId: job.job_id,
      fileType: result.file_type,
      renderer: result.viewer_hints?.renderer.type ?? result.file_type
    });
  }, [job.job_id, result.file_type, result.viewer_hints?.renderer.type]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "ArrowDown" || event.key === "j") {
        event.preventDefault();
        setActiveChange(result.changes[Math.min(activeIndex + 1, result.changes.length - 1)] ?? null);
      }
      if (event.key === "ArrowUp" || event.key === "k") {
        event.preventDefault();
        setActiveChange(result.changes[Math.max(activeIndex - 1, 0)] ?? null);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [activeIndex, result.changes]);

  return (
    <div className="draftable-shell">
      <section className="comparison-toolbar">
        <div className="toolbar-title">
          <strong>{job.file_a}</strong>
          <span className="muted">vs</span>
          <strong>{job.file_b}</strong>
        </div>
        <div className="toolbar-actions">
          <button className="toolbar-button" type="button">Print</button>
          <button
            className="toolbar-button"
            disabled={result.file_type !== "pdf"}
            onClick={() => {
              setDownloadError("");
              void downloadComparisonPdf(job.job_id, exportFilename).catch((error: unknown) => {
                setDownloadError(error instanceof Error ? error.message : "Download failed");
              });
            }}
            type="button"
          >
            Download PDF
          </button>
          <button className="toolbar-button active" type="button">Side By Side</button>
          <button className="toolbar-button" type="button">Single</button>
          <button className="toolbar-button" type="button">Scroll Lock</button>
          <button className="toolbar-button" type="button">Full Screen</button>
        </div>
        <div className="toolbar-actions">
          <button
            className="toolbar-button"
            onClick={() =>
              setActiveChange(result.changes[Math.max(activeIndex - 1, 0)] ?? activeChange)
            }
            type="button"
          >
            Previous Change
          </button>
          <button
            className="toolbar-button"
            onClick={() =>
              setActiveChange(
                result.changes[Math.min(activeIndex + 1, result.changes.length - 1)] ??
                  activeChange
              )
            }
            type="button"
          >
            Next Change
          </button>
        </div>
      </section>
      <section className="comparison-summary">
        <div className="controls">
            <div>
              <h2>{result.summary}</h2>
              <p>
                {job.file_a} \u2192 {job.file_b} | Export name: {exportFilename}
              </p>
              {downloadError ? <p className="badge danger">{downloadError}</p> : null}
            </div>
            <span className="badge">{fileKindLabel(result.file_type)}</span>
            <span className="badge">{result.result_schema_version}</span>
            <span className="badge">{result.changes.length} changes</span>
        </div>
      </section>
      <div className="viewer-grid">
        <DiffRenderer
          allChanges={result.changes}
          activeChange={activeChange}
          artifactA={artifacts.a}
          artifactB={artifacts.b}
          document="a"
          jobId={job.job_id}
          previewManifest={previewManifests.a}
          result={result}
          title="Original"
        />
        <DiffRenderer
          allChanges={result.changes}
          activeChange={activeChange}
          artifactA={artifacts.a}
          artifactB={artifacts.b}
          document="b"
          jobId={job.job_id}
          previewManifest={previewManifests.b}
          result={result}
          title="Updated"
        />
        <div className="diff-minimap" aria-label="Document difference map">
          {result.changes.slice(0, 80).map((change, index) => (
            <button
              className={`minimap-mark ${change.severity} ${
                activeChange?.id === change.id ? "active" : ""
              }`}
              key={change.id}
              onClick={() => setActiveChange(change)}
              style={{ top: `${Math.min(96, (index / Math.max(1, result.changes.length)) * 100)}%` }}
              title={change.message}
              type="button"
            />
          ))}
        </div>
        <div className="grid">
          <ChangeList
            activeChangeId={activeChange?.id ?? null}
            changes={result.changes}
            filters={filters}
            onActiveChange={setActiveChange}
            onFiltersChange={setFilters}
          />
          <RiskPanel semantic={result.semantic} />
        </div>
      </div>
    </div>
  );
}
