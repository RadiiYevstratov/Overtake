import Link from "next/link";

import { Countdown } from "@/components/countdown";
import { serverFetchOrNull } from "@/lib/api";
import type { Me, SeasonMeta } from "@/lib/types";

/**
 * The deadline is a clock, not a feature. It is persistent in the header
 * because it is the product's heartbeat and the ritual the user already has.
 */
export async function SiteHeader() {
  const [meta, me] = await Promise.all([
    serverFetchOrNull<SeasonMeta>("/meta/season", { revalidate: 300 }),
    serverFetchOrNull<Me>("/me"),
  ]);

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-base/95 backdrop-blur supports-[backdrop-filter]:bg-base/80">
      <div className="mx-auto flex h-14 max-w-6xl items-center gap-4 px-4 sm:px-6">
        <Link
          href={me ? "/app" : "/"}
          className="text-sm font-bold tracking-tight text-ink"
        >
          OVERTAKE
        </Link>

        {meta?.next_deadline_utc ? (
          <Countdown
            deadline={meta.next_deadline_utc}
            gameweek={meta.next_gameweek}
          />
        ) : null}

        <nav aria-label="Main" className="ml-auto flex items-center gap-1 text-sm">
          {me ? (
            <>
              <HeaderLink href="/app">Dashboard</HeaderLink>
              <HeaderLink href="/app/account" className="hidden sm:inline-flex">
                Account
              </HeaderLink>
              {!me.plan.is_pro ? (
                <Link
                  href="/pricing"
                  className="ml-1 inline-flex min-h-[36px] items-center rounded-[8px] bg-you px-3 py-1.5 text-sm font-semibold text-[#06231a] transition-colors hover:bg-[#4ae8a5]"
                >
                  Go Pro
                </Link>
              ) : null}
            </>
          ) : (
            <>
              <HeaderLink href="/how-it-works" className="hidden sm:inline-flex">
                How it works
              </HeaderLink>
              <HeaderLink href="/pricing">Pricing</HeaderLink>
              <Link
                href="/signin"
                className="ml-1 inline-flex min-h-[36px] items-center rounded-[8px] border border-border-strong px-3 py-1.5 text-sm transition-colors hover:border-ink-faint"
              >
                Sign in
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}

function HeaderLink({
  href,
  children,
  className = "",
}: {
  href: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <Link
      href={href}
      className={`inline-flex min-h-[36px] items-center rounded-[8px] px-3 py-1.5 text-ink-dim transition-colors hover:bg-surface-2 hover:text-ink ${className}`}
    >
      {children}
    </Link>
  );
}
