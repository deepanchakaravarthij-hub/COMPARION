"use client";

import type { SemanticPayload } from "@/lib/types";

export function RiskPanel({ semantic }: { semantic?: SemanticPayload | null }) {
  if (!semantic) {
    return (
      <div className="risk-card">
        <strong>Semantic layer</strong>
        <p className="muted">No semantic metadata was returned for this result.</p>
      </div>
    );
  }

  const findings = semantic.risk_summary?.findings ?? [];

  return (
    <div className="risk-card">
      <div className="controls">
        <strong>Risk Summary</strong>
        <span className={`badge ${semantic.risk_summary?.high_risk_count ? "danger" : "success"}`}>
          High risk {semantic.risk_summary?.high_risk_count ?? 0}
        </span>
      </div>
      {Array.isArray(semantic.summary) && semantic.summary.length ? (
        <ul>
          {semantic.summary.map((item, index) => (
            <li key={`${item}-${index}`}>{item}</li>
          ))}
        </ul>
      ) : null}
      {findings.length ? (
        <div className="grid">
          {findings.slice(0, 5).map((finding, index) => (
            <div className="structured-row" key={`${finding.change_id ?? "finding"}-${index}`}>
              <strong>{finding.domain ?? "risk"}</strong>
              <p>{finding.reason ?? "Risk rule matched this change."}</p>
              {finding.change_id ? <span className="badge">{finding.change_id}</span> : null}
            </div>
          ))}
        </div>
      ) : (
        <p className="muted">No rule-based risk findings.</p>
      )}
    </div>
  );
}
