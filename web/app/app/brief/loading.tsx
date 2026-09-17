import { BriefCardSkeleton } from "@/components/brief-skeleton";
import { Skeleton } from "@/components/ui";

export default function BriefLoading() {
  return (
    <div>
      <h1 className="text-3xl font-bold tracking-tight">Deadline Brief</h1>
      <Skeleton className="mt-3 h-5 w-72 max-w-full" />
      <BriefCardSkeleton label="Loading your Deadline Brief…" />
    </div>
  );
}
