"use client";

import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui";
import { ApiError, clientFetch } from "@/lib/api";

export function UnsubscribeForm({ token }: { token: string | null }) {
  const [state, setState] = useState<"idle" | "working" | "done">("idle");
  const [error, setError] = useState<string | null>(null);

  async function unsubscribe() {
    setState("working");
    setError(null);
    try {
      await clientFetch("/me", {
        method: "PATCH",
        body: JSON.stringify({ marketing_opt_in: false }),
      });
      setState("done");
    } catch (err) {
      setState("idle");
      setError(
        err instanceof ApiError && err.isAuthRequired
          ? "Sign in first and we can turn them off from your account page."
          : "That did not work. Email hello@overtake.app and we will do it by hand.",
      );
    }
  }

  if (state === "done") {
    return (
      <div role="status">
        <h2 className="font-semibold text-you">Done</h2>
        <p className="mt-2 text-sm leading-relaxed text-ink-dim">
          You will not get product email from us again. Deadline Briefs still arrive if
          you have Pro, because those are the thing you are paying for — turn them off
          in your account settings if you would rather not have them.
        </p>
        <Link
          href="/app/account"
          className="mt-4 inline-flex text-sm text-you underline"
        >
          Go to account settings
        </Link>
      </div>
    );
  }

  return (
    <>
      {!token ? (
        <p className="mb-4 text-sm text-ink-faint">
          This link is missing its token. You can still turn emails off below if you are
          signed in.
        </p>
      ) : null}
      <Button onClick={unsubscribe} disabled={state === "working"} className="w-full">
        {state === "working" ? "Turning them off…" : "Turn off product email"}
      </Button>
      {error ? (
        <p role="alert" className="mt-3 text-sm text-rival">
          {error}
        </p>
      ) : null}
    </>
  );
}
