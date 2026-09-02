"use client";

import Link from "next/link";
import { useEffect } from "react";

import { Button, Card } from "@/components/ui";

/** Plain language, an id to quote, and never a stack trace. */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="mx-auto max-w-xl px-4 py-20 sm:px-6">
      <Card className="border-rival-dim p-6">
        <h1 className="text-2xl font-bold text-rival">Something went wrong</h1>
        <p className="mt-3 leading-relaxed text-ink-dim">
          This is on us, not on you. Trying again often works — this kind of failure is
          usually the FPL API being slow rather than anything permanent.
        </p>
        {error.digest ? (
          <p className="mt-4 text-sm text-ink-faint">
            Reference <span className="num">{error.digest}</span> — quote it to{" "}
            <a className="underline hover:text-ink" href="mailto:hello@overtake.app">
              hello@overtake.app
            </a>{" "}
            and we can find exactly what happened.
          </p>
        ) : null}
        <div className="mt-6 flex flex-wrap gap-2">
          <Button onClick={reset}>Try again</Button>
          <Link
            href="/"
            className="inline-flex min-h-[44px] items-center rounded-[8px] border border-border-strong px-4 py-2.5 text-sm transition-colors hover:border-ink-faint"
          >
            Back to the start
          </Link>
        </div>
      </Card>
    </div>
  );
}
