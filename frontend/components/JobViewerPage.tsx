"use client";

import { useQueries, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { fetchArtifactLink, fetchJob, fetchResult } from "@/lib/api-client";
import { ViewerShell } from "./viewer/ViewerShell";

export function JobViewerPage({ jobId }: { jobId: string }) {
  const jobQuery = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => fetchJob(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "completed" || status === "failed" ? false : 2_000;
    }
  });
  const isComplete = jobQuery.data?.status === "completed";
  const resultQuery = useQuery({
    queryKey: ["result", jobId],
    queryFn: () => fetchResult(jobId),
    enabled: isComplete
  });
  const artifactQueries = useQueries({
    queries: (["a", "b"] as const).map((label) => ({
      queryKey: ["artifact-link", jobId, label],
      queryFn: () => fetchArtifactLink(jobId, label),
      enabled: isComplete
    }))
  });

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand">
          <h1>Job {jobId.slice(0, 8)}</h1>
          <p>Processing status, artifacts, and native diff viewer.</p>
        </div>
        <Link className="button secondary" href="/">
          New comparison
        </Link>
      </header>

      {jobQuery.isLoading ? <p className="panel panel-body">Loading job...</p> : null}
      {jobQuery.error ? <p className="badge danger">{jobQuery.error.message}</p> : null}

      {jobQuery.data && jobQuery.data.status !== "completed" ? (
        <section className="panel">
          <div className="panel-header">
            <h2>Status: {jobQuery.data.status}</h2>
            <p>
              {jobQuery.data.file_a} vs {jobQuery.data.file_b}
            </p>
          </div>
          <div className="panel-body">
            {jobQuery.data.error ? (
              <p className="badge danger">
                {jobQuery.data.error.code}: {jobQuery.data.error.message}
              </p>
            ) : (
              <p className="muted">Polling until the backend completes processing.</p>
            )}
          </div>
        </section>
      ) : null}

      {resultQuery.error ? <p className="badge danger">{resultQuery.error.message}</p> : null}
      {artifactQueries.some((query) => query.error) ? (
        <p className="badge danger">Unable to load one or more artifact links.</p>
      ) : null}

      {jobQuery.data &&
      resultQuery.data &&
      artifactQueries[0].data &&
      artifactQueries[1].data ? (
        <ViewerShell
          artifacts={{ a: artifactQueries[0].data, b: artifactQueries[1].data }}
          job={jobQuery.data}
          result={resultQuery.data}
        />
      ) : null}
    </main>
  );
}
