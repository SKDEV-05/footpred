import { Suspense } from "react";
import MatchDetailClient from "./MatchDetailClient";

async function MatchDetail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <MatchDetailClient matchId={id} />;
}

export default function MatchDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  return (
    <Suspense
      fallback={
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="animate-pulse space-y-8">
            <div className="h-8 bg-white/5 rounded w-1/4" />
            <div className="h-40 bg-white/5 rounded border border-white/10" />
          </div>
        </div>
      }
    >
      <MatchDetail params={params} />
    </Suspense>
  );
}
