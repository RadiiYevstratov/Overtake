"use client";

import { useId, useState } from "react";

import { Button } from "@/components/ui";
import { ApiError, clientFetch, track } from "@/lib/api";

const CURRENT_YEAR = new Date().getFullYear();

/**
 * Signup asks for a neutral year of birth, not "are you over 18?" — which
 * invites a lie. Only the derived band is ever sent or stored; the date itself
 * is never retained (11-legal-security-risk.md §1.1).
 */
function ageBandFor(year: number | null): string {
  if (year === null) return "unknown";
  const age = CURRENT_YEAR - year;
  if (age < 13) return "under13";
  if (age < 16) return "13_15";
  if (age < 18) return "16_17";
  return "adult";
}

export function SignInForm({ next }: { next: string | null }) {
  const emailId = useId();
  const yearId = useId();
  const [email, setEmail] = useState("");
  const [year, setYear] = useState("");
  const [state, setState] = useState<"idle" | "sending" | "sent">("idle");
  const [error, setError] = useState<string | null>(null);

  const band = ageBandFor(year ? Number.parseInt(year, 10) : null);
  const tooYoung = band === "under13";

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (tooYoung) return;
    setState("sending");
    setError(null);
    track("signup_started", {});
    try {
      await clientFetch("/auth/magic-link", {
        method: "POST",
        body: JSON.stringify({
          email,
          age_band: band,
          marketing_opt_in: false,
          next_path: next,
        }),
      });
      setState("sent");
    } catch (err) {
      setState("idle");
      setError(
        err instanceof ApiError
          ? err.message
          : "We could not send that link. Try again in a moment.",
      );
    }
  }

  if (state === "sent") {
    return (
      <div role="status">
        <h2 className="text-lg font-semibold text-you">Check your email</h2>
        <p className="mt-2 leading-relaxed text-ink-dim">
          We sent a sign-in link to <span className="text-ink">{email}</span>. It works
          once and expires in 15 minutes.
        </p>
        <p className="mt-4 text-sm text-ink-faint">
          Nothing arrived? Check spam, then{" "}
          <button
            type="button"
            onClick={() => setState("idle")}
            className="underline hover:text-ink-dim"
          >
            try again
          </button>
          .
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={submit} noValidate>
      <label htmlFor={emailId} className="block text-sm font-medium">
        Email address
      </label>
      <input
        id={emailId}
        type="email"
        name="email"
        required
        autoComplete="email"
        value={email}
        onChange={(event) => setEmail(event.target.value)}
        className="mt-2 min-h-[48px] w-full rounded-[8px] border border-border-strong bg-base px-3 py-2.5 text-base focus:border-you focus:outline-none"
        placeholder="you@example.com"
      />

      <label htmlFor={yearId} className="mt-5 block text-sm font-medium">
        Year of birth
      </label>
      <p className="mt-1 text-xs text-ink-faint">
        We store only an age band, never the date. It decides what we are allowed to
        send you.
      </p>
      <input
        id={yearId}
        type="number"
        name="birth_year"
        inputMode="numeric"
        min={1900}
        max={CURRENT_YEAR}
        value={year}
        onChange={(event) => setYear(event.target.value)}
        className="mt-2 min-h-[48px] w-full rounded-[8px] border border-border-strong bg-base px-3 py-2.5 text-base focus:border-you focus:outline-none"
        placeholder="e.g. 2001"
      />

      {tooYoung ? (
        <p role="alert" className="mt-3 text-sm text-warn">
          You need to be at least 13 to create an account. You can still use every
          public league page without one.
        </p>
      ) : null}

      {error ? (
        <p role="alert" className="mt-3 text-sm text-rival">
          {error}
        </p>
      ) : null}

      <Button
        type="submit"
        disabled={state === "sending" || tooYoung || !email}
        className="mt-6 w-full"
      >
        {state === "sending" ? "Sending…" : "Email me a sign-in link"}
      </Button>
    </form>
  );
}
