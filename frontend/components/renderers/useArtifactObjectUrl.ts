"use client";

import { useEffect, useState } from "react";
import { absoluteApiUrl, authHeaders } from "@/lib/api-client";
import { recordTelemetry } from "@/lib/telemetry";
import type { ArtifactLink } from "@/lib/types";

export function useArtifactObjectUrl(artifact: ArtifactLink) {
  const [objectUrl, setObjectUrl] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    let nextObjectUrl = "";

    async function loadArtifact() {
      try {
        setError("");
        const response = await fetch(absoluteApiUrl(artifact.url), {
          headers: authHeaders(),
          signal: controller.signal
        });
        if (!response.ok) {
          throw new Error(`Artifact fetch failed with ${response.status}`);
        }
        const blob = await response.blob();
        nextObjectUrl = URL.createObjectURL(blob);
        setObjectUrl(nextObjectUrl);
      } catch (caught) {
        if (!controller.signal.aborted) {
          const message = caught instanceof Error ? caught.message : "Artifact fetch failed";
          recordTelemetry("renderer_error", { renderer: artifact.label, message });
          setError(message);
        }
      }
    }

    void loadArtifact();

    return () => {
      controller.abort();
      if (nextObjectUrl) {
        URL.revokeObjectURL(nextObjectUrl);
      }
    };
  }, [artifact.label, artifact.url]);

  return { objectUrl, error };
}
