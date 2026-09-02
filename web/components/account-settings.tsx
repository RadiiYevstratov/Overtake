"use client";

import { useRouter } from "next/navigation";
import { useId, useState } from "react";

import { Button, Card } from "@/components/ui";
import { ApiError, clientFetch } from "@/lib/api";
import { parseEntryId } from "@/lib/format";
import type { Me } from "@/lib/types";

export function AccountSettings({ me }: { me: Me }) {
  const router = useRouter();
  const nameId = useId();
  const entryId = useId();

  const [displayName, setDisplayName] = useState(me.user.display_name ?? "");
  const [fplEntry, setFplEntry] = useState(
    me.user.fpl_entry_id ? String(me.user.fpl_entry_id) : "",
  );
  const [marketing, setMarketing] = useState(me.user.marketing_opt_in);
  const [state, setState] = useState<"idle" | "saving" | "saved">("idle");
  const [error, setError] = useState<string | null>(null);

  const isAdult = me.user.age_band === "adult";

  async function save(event: React.FormEvent) {
    event.preventDefault();
    setState("saving");
    setError(null);
    const parsed = fplEntry ? parseEntryId(fplEntry) : null;
    if (fplEntry && parsed === null) {
      setState("idle");
      setError("That does not look like an FPL manager ID.");
      return;
    }
    try {
      await clientFetch("/me", {
        method: "PATCH",
        body: JSON.stringify({
          display_name: displayName || null,
          fpl_entry_id: parsed,
          marketing_opt_in: marketing,
        }),
      });
      setState("saved");
      router.refresh();
      window.setTimeout(() => setState("idle"), 2500);
    } catch (err) {
      setState("idle");
      setError(err instanceof ApiError ? err.message : "Could not save those changes.");
    }
  }

  return (
    <Card className="p-6">
      <form onSubmit={save}>
        <div className="grid gap-5 sm:grid-cols-2">
          <div>
            <label htmlFor={nameId} className="block text-sm font-medium">
              Display name
            </label>
            <input
              id={nameId}
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              maxLength={60}
              className="mt-2 min-h-[48px] w-full rounded-[8px] border border-border-strong bg-base px-3 py-2.5 text-base focus:border-you focus:outline-none"
              placeholder="Optional"
            />
          </div>
          <div>
            <label htmlFor={entryId} className="block text-sm font-medium">
              FPL manager ID
            </label>
            <input
              id={entryId}
              value={fplEntry}
              onChange={(event) => setFplEntry(event.target.value)}
              inputMode="numeric"
              className="mt-2 min-h-[48px] w-full rounded-[8px] border border-border-strong bg-base px-3 py-2.5 text-base focus:border-you focus:outline-none"
              placeholder="e.g. 1234567"
            />
            <p className="mt-1 text-xs text-ink-faint">
              The number in your FPL points URL. Paste the whole URL if it is easier.
            </p>
          </div>
        </div>

        <div className="mt-6 border-t border-border pt-5">
          <div className="text-sm font-medium">Email</div>
          <p className="mt-1 text-sm text-ink-dim">{me.user.email}</p>
          <p className="mt-1 text-xs text-ink-faint">
            Deadline Briefs and Monday recaps go here. They are part of the product,
            not marketing, so they are not affected by the setting below.
          </p>
        </div>

        <div className="mt-5">
          {isAdult ? (
            <label className="flex items-start gap-3 text-sm">
              <input
                type="checkbox"
                checked={marketing}
                onChange={(event) => setMarketing(event.target.checked)}
                className="mt-1 h-4 w-4 accent-[#3ddc97]"
              />
              <span>
                <span className="text-ink">Occasional product email</span>
                <span className="block text-ink-dim">
                  A few times a season at most: season reviews, and a reminder in July
                  when the next season is close. Never pre-ticked, and one click to
                  turn off.
                </span>
              </span>
            </label>
          ) : (
            <p className="text-sm text-ink-faint">
              We do not send marketing email to under-18s, so there is nothing to
              opt into here. You still get the product emails you have asked for.
            </p>
          )}
        </div>

        {error ? (
          <p role="alert" className="mt-4 text-sm text-rival">
            {error}
          </p>
        ) : null}

        <div className="mt-6 flex items-center gap-3">
          <Button type="submit" disabled={state === "saving"}>
            {state === "saving" ? "Saving…" : "Save changes"}
          </Button>
          {state === "saved" ? (
            <span role="status" className="text-sm text-you">
              Saved ✓
            </span>
          ) : null}
        </div>
      </form>
    </Card>
  );
}
