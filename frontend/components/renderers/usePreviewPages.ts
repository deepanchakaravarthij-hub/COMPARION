"use client";

import { useEffect, useState } from "react";
import { absoluteApiUrl, authHeaders, previewPagePath } from "@/lib/api-client";
import { recordTelemetry } from "@/lib/telemetry";

export interface PreviewPage {
  page: number;
  url: string;
}

export function usePreviewPages(jobId: string, label: "a" | "b", pageCount: number) {
  const [pages, setPages] = useState<PreviewPage[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    const objectUrls: string[] = [];

    async function loadPages() {
      try {
        setError("");
        setPages([]);
        const loadedPages: PreviewPage[] = [];
        for (let page = 1; page <= pageCount; page += 1) {
          const response = await fetch(absoluteApiUrl(previewPagePath(jobId, label, page)), {
            headers: authHeaders(),
            signal: controller.signal
          });
          if (!response.ok) {
            throw new Error(`Preview page ${page} failed with ${response.status}`);
          }
          const blob = await response.blob();
          const url = URL.createObjectURL(blob);
          objectUrls.push(url);
          loadedPages.push({ page, url });
        }
        setPages(loadedPages);
      } catch (caught) {
        if (!controller.signal.aborted) {
          const message = caught instanceof Error ? caught.message : "Preview fetch failed";
          recordTelemetry("renderer_error", { renderer: label, message });
          setError(message);
        }
      }
    }

    if (pageCount > 0) {
      void loadPages();
    }

    return () => {
      controller.abort();
      objectUrls.forEach((url) => URL.revokeObjectURL(url));
    };
  }, [jobId, label, pageCount]);

  return { pages, error };
}
