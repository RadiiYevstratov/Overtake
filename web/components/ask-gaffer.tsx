"use client";

import { useId, useRef, useState } from "react";

import { Button, Skeleton, cx } from "@/components/ui";
import { ApiError, clientFetch, track } from "@/lib/api";
import type { GafferAnswer, GafferConversation, GafferTurn } from "@/lib/types";

const MAX_LENGTH = 500;

/** Where to start, for someone who has never asked. Names come from the server's data. */
const STARTERS = [
  "Which rival is easiest to catch from here?",
  "What is my biggest risk this week?",
  "Is my captain the right call against my closest rival?",
];

/**
 * Ask-the-Gaffer: a follow-up question about this brief, answered from the
 * simulation and nothing else.
 *
 * It sits under the brief rather than on the front door, on purpose — the
 * simulation is the product, and a chat box as the first thing a visitor sees
 * would say "wrapper". A question the writer cannot answer from the numbers
 * comes back saying so, and costs nothing.
 */
export function AskGaffer({
  leagueId,
  initial,
}: {
  leagueId: number;
  initial: GafferConversation;
}) {
  const inputId = useId();
  const input = useRef<HTMLTextAreaElement>(null);
  const [turns, setTurns] = useState<(GafferTurn & { note?: string })[]>(initial.messages);
  const [remaining, setRemaining] = useState<number | null>(initial.remaining_today);
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const spent = remaining !== null && remaining <= 0;

  async function ask(question: string) {
    const message = question.trim();
    if (!message || pending || spent) return;

    setPending(true);
    setError(null);
    setDraft("");
    // Shown at once, so the wait reads as the answer being written.
    setTurns((current) => [...current, { role: "user", content: message }]);
    track("gaffer_message_sent", { league_id: leagueId });

    try {
      const reply = await clientFetch<GafferAnswer>(`/leagues/${leagueId}/ask`, {
        method: "POST",
        body: JSON.stringify({ message }),
      });
      setTurns((current) => [
        ...current,
        {
          role: "assistant",
          content: reply.answer,
          note: reply.is_fallback
            ? "Could not be answered from the numbers, so it did not use a question."
            : undefined,
        },
      ]);
      setRemaining(reply.remaining_today);
    } catch (err) {
      // Put the question back where it was typed, rather than make them retype it.
      setTurns((current) => current.slice(0, -1));
      setDraft(message);
      setError(
        err instanceof ApiError ? err.message : "The Gaffer could not answer just now.",
      );
    } finally {
      setPending(false);
      input.current?.focus();
    }
  }

  return (
    <section aria-labelledby={`${inputId}-heading`} className="mt-10">
      <div className="flex items-baseline justify-between gap-4">
        <h2 id={`${inputId}-heading`} className="text-xl font-semibold">
          Ask the Gaffer
        </h2>
        {remaining !== null ? (
          <p className="text-xs text-ink-faint">
            <span className="num">{remaining}</span> question{remaining === 1 ? "" : "s"} left
            today
          </p>
        ) : null}
      </div>
      <p className="mt-1 text-sm text-ink-dim">
        A follow-up about your league, answered from the same simulation as the brief. If
        the numbers cannot answer it, the Gaffer says so rather than guess.
      </p>

      <div aria-live="polite" className="mt-5 space-y-3">
        {turns.map((turn, index) => (
          <div
            key={index}
            className={cx(
              "rounded-[8px] px-4 py-3 text-sm leading-relaxed",
              turn.role === "user"
                ? "ml-auto max-w-[85%] bg-surface-2 text-ink"
                : "max-w-[92%] border border-border bg-surface text-ink-dim",
            )}
          >
            <span className="mb-1 block text-[11px] uppercase tracking-wide text-ink-faint">
              {turn.role === "user" ? "You" : "The Gaffer"}
            </span>
            {turn.content}
            {turn.note ? (
              <span className="mt-2 block text-xs text-ink-faint">{turn.note}</span>
            ) : null}
          </div>
        ))}
        {pending ? (
          <div
            role="status"
            className="max-w-[92%] rounded-[8px] border border-border bg-surface px-4 py-3"
          >
            <span className="sr-only">The Gaffer is answering…</span>
            <Skeleton className="h-3 w-3/4" />
            <Skeleton className="mt-2 h-3 w-1/2" />
          </div>
        ) : null}
      </div>

      {turns.length === 0 && !spent ? (
        <div className="mt-4 flex flex-wrap gap-2">
          {STARTERS.map((starter) => (
            <button
              key={starter}
              type="button"
              disabled={pending}
              onClick={() => void ask(starter)}
              className="min-h-[44px] rounded-[8px] border border-border-strong px-3 py-2 text-left text-sm text-ink-dim transition-colors hover:border-ink-faint hover:text-ink disabled:opacity-50"
            >
              {starter}
            </button>
          ))}
        </div>
      ) : null}

      <form
        className="mt-4"
        onSubmit={(event) => {
          event.preventDefault();
          void ask(draft);
        }}
      >
        <label htmlFor={inputId} className="sr-only">
          Your question for the Gaffer
        </label>
        <textarea
          id={inputId}
          ref={input}
          rows={2}
          maxLength={MAX_LENGTH}
          value={draft}
          disabled={spent}
          onChange={(event) => {
            setDraft(event.target.value);
            if (error) setError(null);
          }}
          onKeyDown={(event) => {
            // Enter asks; Shift+Enter is a new line, as in every chat box.
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void ask(draft);
            }
          }}
          placeholder={
            spent
              ? "That is today's questions used. More tomorrow."
              : "e.g. What would it take to catch the leader?"
          }
          className="w-full resize-none rounded-[8px] border border-border-strong bg-surface px-4 py-3 text-[1rem] text-ink placeholder:text-ink-faint focus:border-you focus:outline-none disabled:opacity-60"
        />
        <div className="mt-2 flex items-center justify-between gap-3">
          <span className="num text-[11px] text-ink-faint">
            {draft.length}/{MAX_LENGTH}
          </span>
          <Button type="submit" disabled={pending || spent || !draft.trim()}>
            {pending ? "Asking…" : "Ask"}
          </Button>
        </div>
        {error ? (
          <p role="alert" className="mt-2 text-sm text-rival">
            {error}
          </p>
        ) : null}
      </form>
    </section>
  );
}
