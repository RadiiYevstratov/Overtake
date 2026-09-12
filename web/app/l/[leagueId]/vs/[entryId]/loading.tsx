import { Card, Skeleton } from "@/components/ui";

export default function DossierLoading() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6" role="status" aria-live="polite">
      <span className="sr-only">Loading the dossier…</span>
      <Skeleton className="h-10 w-80 max-w-full" />
      <Skeleton className="mt-3 h-5 w-64 max-w-full" />
      <Card className="mt-8 p-6">
        <Skeleton className="h-6 w-40" />
        <Skeleton className="mt-4 h-24 w-full" />
      </Card>
      <Card className="mt-4 p-6">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="mt-4 h-32 w-full" />
      </Card>
    </div>
  );
}
