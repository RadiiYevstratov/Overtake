import { Skeleton } from "@/components/ui";

/**
 * Shown the instant a tab is clicked, while the server renders the page. The
 * navigation stays put above it, so the click visibly registers straight away
 * instead of the old page sitting there looking frozen.
 */
export default function Loading() {
  return (
    <div role="status" aria-live="polite">
      <span className="sr-only">Loading…</span>
      <Skeleton className="h-9 w-64 max-w-full" />
      <Skeleton className="mt-3 h-5 w-96 max-w-full" />
      <div className="mt-8 grid gap-4 sm:grid-cols-2">
        <Skeleton className="h-40" />
        <Skeleton className="h-40" />
      </div>
      <Skeleton className="mt-4 h-64" />
    </div>
  );
}
