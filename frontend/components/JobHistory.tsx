"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { fetchJobs } from "@/lib/api-client";
import { fileKindLabel } from "@/lib/viewer";

export function JobHistory() {
  const { data, error, isLoading, refetch } = useQuery({
    queryKey: ["jobs"],
    queryFn: () => fetchJobs({ limit: 20 }),
    refetchInterval: 15_000
  });

  return (
    <section className="panel">
      <div className="panel-header">
        <div className="controls">
          <div>
            <h2>Recent Jobs</h2>
            <p>Resume inspections and monitor queued work.</p>
          </div>
          <button className="button secondary" onClick={() => void refetch()} type="button">
            Refresh
          </button>
        </div>
      </div>
      <div className="panel-body">
        {isLoading ? <p className="muted">Loading jobs...</p> : null}
        {error ? <p className="badge danger">{error.message}</p> : null}
        {data?.items.length === 0 ? <p className="muted">No jobs yet.</p> : null}
        {data?.items.map((job) => (
          <Link className="job-row" href={`/jobs/${job.job_id}`} key={job.job_id}>
            <div>
              <strong>
                {job.file_a} vs {job.file_b}
              </strong>
              <p className="muted">{new Date(job.created_at).toLocaleString()}</p>
            </div>
            <div className="controls">
              <span className="badge">{fileKindLabel(job.file_type)}</span>
              <span className={`badge ${job.status === "failed" ? "danger" : ""}`}>{job.status}</span>
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}
