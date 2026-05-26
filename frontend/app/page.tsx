"use client";

import { AuthTokenForm } from "@/components/AuthTokenForm";
import { JobHistory } from "@/components/JobHistory";
import { MetricsStrip } from "@/components/MetricsStrip";
import { UploadPanel } from "@/components/UploadPanel";
import { getApiBaseUrl } from "@/lib/api-client";

export default function HomePage() {
  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand">
          <h1>COMPARION Diff Viewer</h1>
          <p>Native document comparison from upload to triage.</p>
          <MetricsStrip />
        </div>
        <AuthTokenForm />
      </header>
      <div className="grid home-grid">
        <UploadPanel />
        <JobHistory />
      </div>
      <p className="muted">API base: {getApiBaseUrl()}</p>
    </main>
  );
}
