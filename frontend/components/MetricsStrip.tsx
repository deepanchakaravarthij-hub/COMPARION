"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchMetrics } from "@/lib/api-client";

export function MetricsStrip() {
  const { data } = useQuery({
    queryKey: ["metrics"],
    queryFn: fetchMetrics,
    refetchInterval: 30_000,
    retry: false
  });

  if (!data) {
    return null;
  }

  return (
    <div className="metrics-strip" aria-label="Operational metrics">
      <span className="badge">Queue depth {data.queue_depth}</span>
      <span className="badge">Failure rate {(data.failure_rate * 100).toFixed(1)}%</span>
      <span className={`badge ${data.alerts.length ? "danger" : "success"}`}>
        Alerts {data.alerts.length}
      </span>
    </div>
  );
}
