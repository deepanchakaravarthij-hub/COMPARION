"use client";

import { useEffect, useMemo, useState } from "react";
import type { ArtifactLink, ChangeItem, JobResult, JobStatusResponse } from "@/lib/types";
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
}

export function ViewerShell({ job, result, artifacts }: ViewerShellProps) {
  const [activeChange, setActiveChange] = useState<ChangeItem | null>(result.changes[0] ?? null);
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
    <div className="grid">
      <section className="panel">
        <div className="panel-header">
          <div className="controls">
            <div>
              <h2>{result.summary}</h2>
              <p>
                {job.file_a} vs {job.file_b}
              </p>
            </div>
            <span className="badge">{fileKindLabel(result.file_type)}</span>
            <span className="badge">{result.result_schema_version}</span>
            <span className="badge">{result.changes.length} changes</span>
          </div>
        </div>
        <div className="panel-body">
          <div className="controls">
            <button
              className="button secondary"
              onClick={() =>
                setActiveChange(result.changes[Math.max(activeIndex - 1, 0)] ?? activeChange)
              }
              type="button"
            >
              Previous
            </button>
            <button
              className="button secondary"
              onClick={() =>
                setActiveChange(
                  result.changes[Math.min(activeIndex + 1, result.changes.length - 1)] ??
                    activeChange
                )
              }
              type="button"
            >
              Next
            </button>
            <span className="muted">Use Up/Down or j/k to navigate.</span>
          </div>
        </div>
      </section>
      <div className="viewer-grid">
        <DiffRenderer
          activeChange={activeChange}
          artifactA={artifacts.a}
          artifactB={artifacts.b}
          document="a"
          result={result}
          title="Original"
        />
        <DiffRenderer
          activeChange={activeChange}
          artifactA={artifacts.a}
          artifactB={artifacts.b}
          document="b"
          result={result}
          title="Updated"
        />
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
