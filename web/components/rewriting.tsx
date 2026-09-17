"use client";

import { createContext, useContext, useState, type ReactNode } from "react";

import { BriefCardSkeleton } from "@/components/brief-skeleton";

/**
 * Shared state between the Rewrite button and the brief it replaces.
 *
 * A rewrite takes several seconds — two model calls when the first draft fails
 * its checks. Until now the only sign was the button's own label, so the old
 * brief sat there looking current and nothing said where the new one would
 * appear. The page now shows the same placeholder it shows on the way in from
 * the dashboard, in the same place, so the wait reads as the brief arriving
 * rather than the page being stuck.
 */
const RewritingContext = createContext<{
  rewriting: boolean;
  setRewriting: (value: boolean) => void;
}>({ rewriting: false, setRewriting: () => {} });

export function useRewriting() {
  return useContext(RewritingContext);
}

export function RewritingProvider({ children }: { children: ReactNode }) {
  const [rewriting, setRewriting] = useState(false);
  return (
    <RewritingContext.Provider value={{ rewriting, setRewriting }}>
      {children}
    </RewritingContext.Provider>
  );
}

/** Swaps the brief for the placeholder while a rewrite is in flight. */
export function RewritingSwap({ children }: { children: ReactNode }) {
  const { rewriting } = useRewriting();
  if (rewriting) return <BriefCardSkeleton label="Writing a new brief…" />;
  return <>{children}</>;
}
