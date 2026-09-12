import { Card, Skeleton } from "@/components/ui";

export default function BriefLoading() {
  return (
    <div role="status" aria-live="polite">
      <span className="sr-only">Loading your Deadline Brief…</span>
      <h1 className="text-3xl font-bold tracking-tight">Deadline Brief</h1>
      <Skeleton className="mt-3 h-5 w-72 max-w-full" />
      <Card className="mt-6 p-6 sm:p-8">
        <Skeleton className="h-8 w-4/5" />
        <Skeleton className="mt-8 h-4 w-24" />
        <Skeleton className="mt-3 h-6 w-3/5" />
        <Skeleton className="mt-3 h-16 w-full" />
        <Skeleton className="mt-8 h-4 w-24" />
        <Skeleton className="mt-3 h-10 w-full" />
      </Card>
    </div>
  );
}
