"use client";

import { useRouter } from "next/navigation";
import { useId, useState } from "react";

import { Button } from "@/components/ui";
import { track } from "@/lib/api";
import { parseLeagueId } from "@/lib/format";

/**
 * The single first action on the site. One input, zero friction, and it accepts
 * whatever the user actually has to hand — an id, or the URL they copied from
 * the FPL site.
 */
export function LeagueIdForm({ autoFocus = false }: { autoFocus?: boolean }) {
  const router = useRouter();
  const inputId = useId();
  const errorId = useId();
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  function submit(event: React.FormEvent) {
    event.preventDefault();
    const leagueId = parseLeagueId(value);
    if (leagueId === null) {
      setError(
        "That does not look like a league ID. Paste the number, or the whole URL from the FPL site.",
      );
      return;
    }
    setError(null);
    setPending(true);
    track("league_id_pasted", { league_id: leagueId });
    router.push(`/l/${leagueId}`);
  }

  return (
    <form onSubmit={submit} noValidate>
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
          className="min-h-[52px] flex-1 rounded-[8px] border border-border-strong bg-surface px-4 py-3 text-base text-ink placeholder:text-ink-faint focus:border-you focus:outline-none"
        />
        <Button
          type="submit"
          disabled={pending}
          className="min-h-[52px] whitespace-nowrap px-6 text-base"
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
