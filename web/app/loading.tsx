import { Skeleton } from "@/components/ui";

export default function Loading() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6">
      <Skeleton className="h-10 w-64" />
      <Skeleton className="mt-4 h-5 w-40" />
      <div className="mt-8 space-y-2">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-14 w-full" />
        ))}
      </div>
      <span className="sr-only">Loading</span>
    </div>
  );
}
