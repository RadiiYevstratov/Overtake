"use client";

import { useRouter } from "next/navigation";
import { useId, useState } from "react";

import { Button } from "@/components/ui";
import { track } from "@/lib/api";
import { leagueIdError, parseLeagueId } from "@/lib/format";

/**
 * The single first action on the site. One input, zero friction, and it accepts
 * whatever the user actually has to hand — an id, or the URL they copied from
 * the FPL site.
 *
 * It is a real form with a real destination (`/l?league=…`, see app/l/page),
 * so a press before the page's JavaScript has loaded still goes somewhere:
 * without an action it submitted to the page it was on, which ignored it, and
 * the button appeared to do nothing.
 */
export function LeagueIdForm({
  autoFocus = false,
  initialValue = "",
  initialError = null,
}: {
  autoFocus?: boolean;
  initialValue?: string;
  initialError?: string | null;
}) {
  const router = useRouter();
  const inputId = useId();
  const errorId = useId();
  const [value, setValue] = useState(initialValue);
  const [error, setError] = useState<string | null>(initialError);
  const [pending, setPending] = useState(false);

  function submit(event: React.FormEvent) {
    event.preventDefault();
    const leagueId = parseLeagueId(value);
    if (leagueId === null) {
      // Nothing is requested for input that cannot be a league.
      setError(leagueIdError(value));
      return;
    }
    setError(null);
    setPending(true);
    track("league_id_pasted", { league_id: leagueId });
    router.push(`/l/${leagueId}`);
  }

  return (
    <form action="/l" method="get" onSubmit={submit} noValidate>
      <label htmlFor={inputId} className="sr-only">
        Your FPL league ID or league URL
      </label>
      <div className="flex flex-col gap-2 sm:flex-row">
        <input
          id={inputId}
          name="league"
          type="text"
          inputMode="text"
          autoComplete="off"
          autoFocus={autoFocus}
          value={value}
          onChange={(event) => {
            setValue(event.target.value);
            if (error) setError(null);
          }}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errorId : undefined}
          placeholder="Paste your league ID or URL"
          className="min-h-[52px] flex-1 rounded-[8px] border border-border-strong bg-surface px-4 py-3 text-[1rem] text-ink placeholder:text-ink-faint focus:border-you focus:outline-none"
        />
        <Button
          type="submit"
          disabled={pending}
          className="min-h-[52px] whitespace-nowrap px-6 text-[1rem]"
        >
          {pending ? "Reading your league…" : "See my odds →"}
        </Button>
      </div>
      {error ? (
        <p id={errorId} role="alert" className="mt-2 text-sm text-rival">
          {error}
        </p>
      ) : null}
    </form>
  );
}
