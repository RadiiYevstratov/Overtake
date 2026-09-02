import type { Metadata } from "next";

import { UnsubscribeForm } from "@/components/unsubscribe-form";
import { Card } from "@/components/ui";

export const metadata: Metadata = {
  title: "Unsubscribe",
  robots: { index: false, follow: false },
};

export default async function UnsubscribePage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string }>;
}) {
  const { token } = await searchParams;
  return (
    <div className="mx-auto max-w-md px-4 py-20 sm:px-6">
      <h1 className="text-3xl font-bold tracking-tight">Turn these emails off</h1>
      <p className="mt-3 leading-relaxed text-ink-dim">
        One click, no questions, and nothing else about your account changes.
      </p>
      <Card className="mt-6 p-6">
        <UnsubscribeForm token={token ?? null} />
      </Card>
    </div>
  );
}
