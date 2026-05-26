"use client";

import type { ArtifactLink, ChangeItem, JobResult } from "@/lib/types";
import { DocxRenderer } from "./DocxRenderer";
import { FallbackRenderer } from "./FallbackRenderer";
import { PdfImageRenderer } from "./PdfImageRenderer";
import { PptxRenderer } from "./PptxRenderer";
import { XlsxRenderer } from "./XlsxRenderer";

interface DiffRendererProps {
  artifactA: ArtifactLink;
  artifactB: ArtifactLink;
  activeChange: ChangeItem | null;
  document: "a" | "b";
  result: JobResult;
  title: string;
}

export function DiffRenderer({
  artifactA,
  artifactB,
  activeChange,
  document,
  result,
  title
}: DiffRendererProps) {
  const artifact = document === "a" ? artifactA : artifactB;

  if (result.file_type === "pdf" || result.file_type === "image") {
    return (
      <PdfImageRenderer
        activeChange={activeChange}
        artifact={artifact}
        result={result}
        title={title}
      />
    );
  }

  if (result.file_type === "docx") {
    return (
      <DocxRenderer
        activeChange={activeChange}
        artifact={artifact}
        document={document}
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

  if (result.file_type === "pptx") {
    return (
      <PptxRenderer
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
