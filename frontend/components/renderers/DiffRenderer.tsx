"use client";

import type { ArtifactLink, ChangeItem, JobResult, PreviewManifest } from "@/lib/types";
import { FallbackRenderer } from "./FallbackRenderer";
import { PdfImageRenderer } from "./PdfImageRenderer";
import { XlsxRenderer } from "./XlsxRenderer";

interface DiffRendererProps {
  allChanges?: ChangeItem[];
  artifactA: ArtifactLink;
  artifactB: ArtifactLink;
  activeChange: ChangeItem | null;
  document: "a" | "b";
  jobId: string;
  previewManifest: PreviewManifest | null;
  result: JobResult;
  title: string;
}

export function DiffRenderer({
  allChanges,
  artifactA,
  artifactB,
  activeChange,
  document,
  jobId,
  previewManifest,
  result,
  title
}: DiffRendererProps) {
  const artifact = document === "a" ? artifactA : artifactB;

  if (
    result.file_type === "pdf" ||
    result.file_type === "image" ||
    result.file_type === "pptx" ||
    result.file_type === "docx"
  ) {
    return (
      <PdfImageRenderer
        allChanges={allChanges}
        activeChange={activeChange}
        artifact={artifact}
        document={document}
        jobId={jobId}
        previewManifest={previewManifest}
        result={result}
        title={title}
      />
    );
  }

  if (result.file_type === "xlsx") {
    return (
      <XlsxRenderer
        activeChange={activeChange}
        artifact={artifact}
        document={document}
        result={result}
        title={title}
      />
    );
  }

  return (
    <FallbackRenderer
      activeChange={activeChange}
      artifact={artifact}
      document={document}
      result={result}
      title={title}
    />
  );
}
