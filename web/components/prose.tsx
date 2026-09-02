import type { ReactNode } from "react";

/**
 * Long-form legal and guide pages. Written to be read, including by a
 * fifteen-year-old — which the Children's Code requires and which happens to be
 * good writing advice anyway.
 */
export function Prose({
  title,
  updated,
  lead,
  children,
}: {
  title: string;
  updated?: string;
  lead?: ReactNode;
  children: ReactNode;
}) {
  return (
    <article className="mx-auto max-w-2xl px-4 py-14 sm:px-6">
      <h1 className="text-4xl font-bold tracking-tight">{title}</h1>
      {updated ? (
        <p className="num mt-2 text-sm text-ink-faint">Last updated {updated}</p>
      ) : null}
      {lead ? (
        <div className="mt-5 text-lg leading-relaxed text-ink-dim">{lead}</div>
      ) : null}
      <div className="prose-overtake mt-10 space-y-6">{children}</div>
    </article>
  );
}

export function H2({ children }: { children: ReactNode }) {
  return (
    <h2 className="pt-4 text-xl font-semibold tracking-tight text-ink">{children}</h2>
  );
}

export function P({ children }: { children: ReactNode }) {
  return <p className="leading-relaxed text-ink-dim">{children}</p>;
}

export function UL({ children }: { children: ReactNode }) {
  return (
    <ul className="list-disc space-y-2 pl-5 leading-relaxed text-ink-dim marker:text-ink-faint">
      {children}
    </ul>
  );
}

export function Callout({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-[8px] border border-border bg-surface p-5 leading-relaxed text-ink">
      {children}
    </div>
  );
}
