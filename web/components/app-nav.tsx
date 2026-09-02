"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cx } from "@/components/ui";

const TABS = [
  { href: "/app", label: "Dashboard", pro: false },
  { href: "/app/brief", label: "Deadline Brief", pro: true },
  { href: "/app/simulator", label: "Simulator", pro: true },
  { href: "/app/chips", label: "Chips", pro: true },
  { href: "/app/leagues", label: "Leagues", pro: false },
  { href: "/app/account", label: "Account", pro: false },
] as const;

export function AppNav({ isPro }: { isPro: boolean }) {
  const pathname = usePathname();
  return (
    <nav aria-label="Your account" className="scroll-x -mx-4 px-4 sm:mx-0 sm:px-0">
      <ul className="flex gap-1 border-b border-border">
        {TABS.map((tab) => {
          const active =
            tab.href === "/app" ? pathname === "/app" : pathname.startsWith(tab.href);
          return (
            <li key={tab.href}>
              <Link
                href={tab.href}
                aria-current={active ? "page" : undefined}
                className={cx(
                  "inline-flex min-h-[44px] items-center whitespace-nowrap border-b-2 px-3 text-sm transition-colors",
                  active
                    ? "border-you text-ink"
                    : "border-transparent text-ink-dim hover:text-ink",
                )}
              >
                {tab.label}
                {tab.pro && !isPro ? (
                  <span
                    className="ml-1.5 text-[10px] uppercase tracking-wider text-ink-faint"
                    aria-label="Pro feature"
                  >
                    Pro
                  </span>
                ) : null}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
