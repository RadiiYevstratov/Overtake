import type { MetadataRoute } from "next";

/**
 * A PWA rather than a native app: the audience is at a desktop or in a mobile
 * browser before a deadline, and a native app in year one would be effort spent
 * where nobody asked for it.
 */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Overtake — beat your FPL mini-league",
    short_name: "Overtake",
    description:
      "Overtake tells you exactly what it takes to finish above the specific people in your FPL mini-league.",
    start_url: "/app",
    scope: "/",
    display: "standalone",
    background_color: "#0B0F14",
    theme_color: "#0B0F14",
    orientation: "portrait-primary",
    categories: ["sports", "utilities"],
    icons: [
      { src: "/icon.svg", sizes: "any", type: "image/svg+xml", purpose: "any" },
    ],
  };
}
