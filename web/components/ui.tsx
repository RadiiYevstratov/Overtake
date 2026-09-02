/** The small component set. Deliberately hand-written and small. */

import Link from "next/link";
import type { ComponentProps, ReactNode } from "react";

export function cx(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(" ");
}

/* ------------------------------------------------------------------ layout */

export function Card({
  children,
  className,
  as: Tag = "div",
}: {
  children: ReactNode;
  className?: string;
  as?: "div" | "section" | "article" | "li";
}) {
  return (
    <Tag
      className={cx(
        "rounded-[8px] border border-border bg-surface",
        className,
      )}
    >
      {children}
    </Tag>
  );
}

export function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <h2 className="mb-3 text-[11px] font-semibold uppercase tracking-[0.14em] text-ink-faint">
      {children}
    </h2>
  );
}

/** A labelled rule, matching the dossier's "── WHERE THE GAP IS ──" style. */
export function RuleHeading({ children }: { children: ReactNode }) {
  return (
    <div className="mb-4 flex items-center gap-3">
      <h2 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-ink-faint whitespace-nowrap">
        {children}
      </h2>
      <span className="h-px flex-1 bg-border" aria-hidden="true" />
    </div>
  );
}

/* ------------------------------------------------------------------ actions */

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

const BUTTON_STYLES: Record<ButtonVariant, string> = {
  primary:
    "bg-you text-[#06231a] hover:bg-[#4ae8a5] active:bg-[#35c586] font-semibold",
  secondary:
    "border border-border-strong bg-surface-2 text-ink hover:border-ink-faint hover:bg-[#1d2833]",
  ghost: "text-ink-dim hover:text-ink hover:bg-surface-2",
  danger:
    "border border-rival-dim bg-transparent text-rival hover:bg-[#2a1616] hover:border-rival",
};

const BUTTON_BASE =
  "inline-flex items-center justify-center gap-2 rounded-[8px] px-4 py-2.5 text-sm " +
  "transition-colors disabled:cursor-not-allowed disabled:opacity-50 " +
  "min-h-[44px]"; // A comfortable touch target: this is used on a phone before a deadline.

export function Button({
  variant = "primary",
  className,
  ...props
}: ComponentProps<"button"> & { variant?: ButtonVariant }) {
  return (
    <button
      {...props}
      className={cx(BUTTON_BASE, BUTTON_STYLES[variant], className)}
    />
  );
}

export function ButtonLink({
  variant = "primary",
  className,
  ...props
}: ComponentProps<typeof Link> & { variant?: ButtonVariant }) {
  return (
    <Link
      {...props}
      className={cx(BUTTON_BASE, BUTTON_STYLES[variant], className)}
    />
  );
}

/* -------------------------------------------------------------------- data */

/** A probability. The number lands first; everything else supports it. */
export function Probability({
  value,
  size = "md",
  label,
}: {
  value: number;
  size?: "sm" | "md" | "lg" | "xl";
  label?: string;
}) {
  const sizes = {
    sm: "text-base",
    md: "text-2xl",
    lg: "text-4xl",
    xl: "text-6xl",
  } as const;
  const tone =
    value >= 0.6 ? "text-you" : value <= 0.25 ? "text-rival" : "text-ink";
  return (
    <span className="inline-flex flex-col">
      <span className={cx("num font-semibold", sizes[size], tone)}>
        {Math.round(value * 100)}
        <span className="text-[0.6em] font-normal text-ink-faint">%</span>
      </span>
      {label ? (
        <span className="mt-1 text-xs leading-tight text-ink-faint">{label}</span>
      ) : null}
    </span>
  );
}

/** A signed delta. Carries an arrow as well as a colour, always. */
export function Delta({ value, unit = "pp" }: { value: number; unit?: string }) {
  const rounded = unit === "pp" ? value * 100 : value;
  if (Math.abs(rounded) < 0.05) {
    return <span className="num text-ink-faint">no change</span>;
  }
  const up = rounded > 0;
  return (
    <span className={cx("num font-medium", up ? "text-you" : "text-rival")}>
      <span aria-hidden="true">{up ? "▲" : "▼"}</span>{" "}
      <span className="sr-only">{up ? "up" : "down"} </span>
      {Math.abs(rounded).toFixed(1)}
      {unit}
    </span>
  );
}

export function Stat({
  value,
  label,
  tone = "default",
}: {
  value: ReactNode;
  label: string;
  tone?: "default" | "you" | "rival";
}) {
  const toneClass =
    tone === "you" ? "text-you" : tone === "rival" ? "text-rival" : "text-ink";
  return (
    <div className="min-w-0">
      <div className={cx("num text-2xl font-semibold sm:text-3xl", toneClass)}>
        {value}
      </div>
      <div className="mt-1 text-xs leading-snug text-ink-faint">{label}</div>
    </div>
  );
}

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "you" | "rival" | "warn";
}) {
  const tones = {
    neutral: "border-border-strong text-ink-dim",
    you: "border-you-dim text-you",
    rival: "border-rival-dim text-rival",
    warn: "border-[#5a4a15] text-warn",
  } as const;
  return (
    <span
      className={cx(
        "inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-medium",
        tones[tone],
      )}
    >
      {children}
    </span>
  );
}

/* ------------------------------------------------------------------ states */

export function EmptyState({
  title,
  children,
  action,
}: {
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <Card className="p-8 text-center">
      <h3 className="text-lg font-semibold text-ink">{title}</h3>
      {children ? (
        <div className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-ink-dim">
          {children}
        </div>
      ) : null}
      {action ? <div className="mt-5">{action}</div> : null}
    </Card>
  );
}

export function ErrorState({
  title = "That did not work",
  message,
  errorId,
  action,
}: {
  title?: string;
  message: string;
  errorId?: string;
  action?: ReactNode;
}) {
  return (
    <Card className="border-rival-dim p-6">
      <h3 className="text-base font-semibold text-rival">{title}</h3>
      <p className="mt-2 text-sm leading-relaxed text-ink-dim">{message}</p>
      {errorId ? (
        <p className="mt-3 text-xs text-ink-faint">
          Reference <span className="num">{errorId}</span> — quote it to{" "}
          <a className="underline hover:text-ink" href="mailto:hello@overtake.app">
            hello@overtake.app
          </a>{" "}
          and we can find exactly what happened.
        </p>
      ) : null}
      {action ? <div className="mt-4">{action}</div> : null}
    </Card>
  );
}

/** Amber, specific, and never silent — stale data is always labelled. */
export function StaleBanner({ since }: { since: string }) {
  return (
    <div
      role="status"
      className="flex flex-wrap items-center gap-x-2 gap-y-1 rounded-[8px] border border-[#5a4a15] bg-[#1e1a0c] px-4 py-3 text-sm text-warn"
    >
      <span aria-hidden="true">⚠</span>
      <span>
        These numbers are from <span className="num">{since}</span>. The FPL API is
        not responding — we will refresh automatically.
      </span>
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cx("skeleton rounded-[8px]", className)}
      aria-hidden="true"
    />
  );
}

/**
 * The wait is the credibility: a real progress narrative, not a spinner.
 */
export function SimulatingState({ squads }: { squads?: number }) {
  return (
    <Card className="p-8">
      <div className="mx-auto max-w-sm text-center">
        <div className="num text-sm text-you">Simulating</div>
        <ul className="mt-4 space-y-2 text-sm text-ink-dim">
          <li>Reading {squads ?? "every"} squad{squads === 1 ? "" : "s"}…</li>
          <li>Projecting the remaining gameweeks…</li>
          <li>Simulating 20,000 seasons…</li>
        </ul>
        <div className="mt-6 h-1 overflow-hidden rounded-full bg-surface-2">
          <div className="skeleton h-full w-full" />
        </div>
      </div>
    </Card>
  );
}

/* -------------------------------------------------------------- provenance */

/**
 * Every number is auditable. This footer is not decoration — it is the reason
 * a numerate audience believes the number above it.
 */
export function ProvenanceFooter({
  nSims,
  seed,
  computedAt,
  mae,
  maeGameweeks,
}: {
  nSims: number;
  seed: number;
  computedAt: string;
  mae: number | null;
  maeGameweeks: number;
}) {
  return (
    <p className="num flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-ink-faint">
      <span>simulated {nSims.toLocaleString("en-GB")} seasons</span>
      <span aria-hidden="true">·</span>
      <span>data as of {computedAt}</span>
      <span aria-hidden="true">·</span>
      <span>
        {mae === null
          ? "projection error not yet measured"
          : `projection MAE ${mae.toFixed(1)} over ${maeGameweeks} GW`}
      </span>
      <span aria-hidden="true">·</span>
      <span>seed {seed}</span>
    </p>
  );
}
