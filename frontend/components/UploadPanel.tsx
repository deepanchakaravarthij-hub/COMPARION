"use client";

import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { submitComparison } from "@/lib/api-client";
import { recordTelemetry } from "@/lib/telemetry";

const SUPPORTED_EXTENSIONS = new Set(["pdf", "png", "jpg", "jpeg", "tif", "tiff", "bmp", "webp", "docx", "xlsx", "pptx"]);

export function UploadPanel() {
  const router = useRouter();
  const [fileA, setFileA] = useState<File | null>(null);
  const [fileB, setFileB] = useState<File | null>(null);
  const [idempotencyKey, setIdempotencyKey] = useState("");

  const mutation = useMutation({
    mutationFn: submitComparison,
    onSuccess: (response) => {
      recordTelemetry("compare_submit_completed", { jobId: response.job_id });
      router.push(`/jobs/${response.job_id}`);
    }
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!fileA || !fileB || !isSupportedPair(fileA, fileB)) {
      return;
    }
    const requestKey = idempotencyKey || createIdempotencyKey();
    setIdempotencyKey(requestKey);
    recordTelemetry("compare_submit_started");
    mutation.mutate({ fileA, fileB, idempotencyKey: requestKey });
  }

  const validation = validationMessage(fileA, fileB);

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Upload Documents</h2>
        <p>Compare same-type pairs across PDF, image, DOCX, XLSX, and PPTX.</p>
      </div>
      <form className="panel-body" onSubmit={handleSubmit}>
        <div className="drop-zone">
          <label htmlFor="file-a">Original document</label>
          <input
            id="file-a"
            name="file-a"
            onChange={(event) => setFileA(event.target.files?.[0] ?? null)}
            type="file"
          />
          {fileA ? <strong>{fileA.name}</strong> : <span className="muted">Select file A</span>}
        </div>
        <div className="drop-zone">
          <label htmlFor="file-b">Updated document</label>
          <input
            id="file-b"
            name="file-b"
            onChange={(event) => setFileB(event.target.files?.[0] ?? null)}
            type="file"
          />
          {fileB ? <strong>{fileB.name}</strong> : <span className="muted">Select file B</span>}
        </div>
        {validation ? <p className="badge warning">{validation}</p> : null}
        {mutation.error ? <p className="badge danger">{mutation.error.message}</p> : null}
        <div className="controls">
          <button className="button" disabled={Boolean(validation) || mutation.isPending} type="submit">
            {mutation.isPending ? "Submitting..." : "Compare files"}
          </button>
          <span className="muted">
            Idempotency key: {idempotencyKey ? idempotencyKey.slice(0, 8) : "created on submit"}
          </span>
        </div>
      </form>
    </section>
  );
}

function validationMessage(fileA: File | null, fileB: File | null) {
  if (!fileA || !fileB) {
    return "Choose both files to start.";
  }
  if (!isSupportedPair(fileA, fileB)) {
    return "Files must be the same supported type.";
  }
  return "";
}

function isSupportedPair(fileA: File, fileB: File) {
  const extensionA = extension(fileA.name);
  const extensionB = extension(fileB.name);
  const normalizedA = normalizeImageExtension(extensionA);
  const normalizedB = normalizeImageExtension(extensionB);
  return SUPPORTED_EXTENSIONS.has(extensionA) && normalizedA === normalizedB;
}

function extension(filename: string) {
  return filename.split(".").pop()?.toLowerCase() ?? "";
}

function normalizeImageExtension(extensionName: string) {
  return ["png", "jpg", "jpeg", "tif", "tiff", "bmp", "webp"].includes(extensionName)
    ? "image"
    : extensionName;
}

function createIdempotencyKey() {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `ui-${Date.now()}`;
}
