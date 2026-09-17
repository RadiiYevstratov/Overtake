import { Card, Skeleton } from "@/components/ui";

/**
 * The shape of a brief before its words arrive.
 *
 * Used both while the page is being fetched and while a rewrite is being
 * written, so the two waits look identical — the reader learns one thing about
 * where the brief will appear, not two.
 */
export function BriefCardSkeleton({ label }: { label: string }) {
  return (
    <div role="status" aria-live="polite">
      <span className="sr-only">{label}</span>
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
