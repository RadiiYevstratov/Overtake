import Link from "next/link";

import { Card } from "@/components/ui";

/**
 * The paywall, wherever it appears. Always states what the feature does, both
 * prices, and never uses guilt or urgency copy.
 */
export function UpgradePrompt({
  feature,
  description,
  returnTo,
}: {
  feature: string;
  description: string;
  returnTo?: string;
}) {
  return (
    <Card className="p-8 text-center">
      <h2 className="text-2xl font-semibold">{feature} is part of Pro</h2>
      <p className="mx-auto mt-3 max-w-lg leading-relaxed text-ink-dim">
        {description}
      </p>
      <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
        <Link
          href={returnTo ? `/pricing?next=${encodeURIComponent(returnTo)}` : "/pricing"}
          className="inline-flex min-h-[44px] items-center rounded-[8px] bg-you px-5 py-2.5 text-sm font-semibold text-[#06231a] transition-colors hover:bg-[#4ae8a5]"
        >
          See the plans
        </Link>
        <span className="text-sm text-ink-faint">
          €4.99 a month · €29.99 for the season
        </span>
      </div>
    </Card>
  );
}
