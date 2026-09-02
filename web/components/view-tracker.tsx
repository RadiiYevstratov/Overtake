"use client";

import { useEffect } from "react";

import { track } from "@/lib/api";

/** Fires one analytics event when a page is viewed. Never blocks rendering. */
export function ViewTracker({
  event,
  props = {},
}: {
  event: string;
  props?: Record<string, unknown>;
}) {
  const serialised = JSON.stringify(props);
  useEffect(() => {
    track(event, JSON.parse(serialised) as Record<string, unknown>);
  }, [event, serialised]);
  return null;
}
