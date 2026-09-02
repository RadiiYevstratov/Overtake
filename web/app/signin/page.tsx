import type { Metadata } from "next";

import { SignInForm } from "@/components/signin-form";
import { Card } from "@/components/ui";

export const metadata: Metadata = {
  title: "Sign in",
  description: "Sign in to Overtake with a link. No password to remember.",
  robots: { index: false, follow: false },
};

export default async function SignInPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string; error?: string }>;
}) {
  const { next, error } = await searchParams;
  return (
    <div className="mx-auto max-w-md px-4 py-16 sm:px-6">
      <h1 className="text-3xl font-bold tracking-tight">Sign in to Overtake</h1>
      <p className="mt-3 leading-relaxed text-ink-dim">
        We email you a link. There is no password to forget, and no password of yours
        for us to lose.
      </p>

      {error === "link_invalid" ? (
        <div
          role="alert"
          className="mt-6 rounded-[8px] border border-rival-dim bg-[#1e1010] px-4 py-3 text-sm text-rival"
        >
          That link had already been used or had expired. Request a new one below and
          it will work.
        </div>
      ) : null}

      <Card className="mt-6 p-6">
        <SignInForm next={next ?? null} />
      </Card>

      <p className="mt-6 text-sm leading-relaxed text-ink-faint">
        We never ask for your FPL password, and we never will. Overtake only reads data
        that is already public on the FPL website.
      </p>
    </div>
  );
}
