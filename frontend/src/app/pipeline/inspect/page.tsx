import { Suspense } from "react";
import InspectorClient from "./inspector-client";

interface InspectorPageProps {
  searchParams: Promise<{
    jobId?: string;
  }>;
}

export default function InspectorPage({
  searchParams,
}: InspectorPageProps) {
  return (
    <Suspense
      fallback={
        <main className="mx-auto max-w-[1600px] p-6">
          <p className="text-sm text-muted-foreground">
            Preparing DXF Engineering Inspector...
          </p>
        </main>
      }
    >
      <InspectorContent searchParams={searchParams} />
    </Suspense>
  );
}

async function InspectorContent({
  searchParams,
}: InspectorPageProps) {
  const params = await searchParams;

  return <InspectorClient jobId={params.jobId ?? ""} />;
}
