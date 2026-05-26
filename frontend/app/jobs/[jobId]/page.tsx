import { JobViewerPage } from "@/components/JobViewerPage";

export default async function Page({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = await params;
  return <JobViewerPage jobId={jobId} />;
}
