import type { Metadata, Viewport } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

import { CookieConsent } from "@/components/cookie-consent";
import { SiteHeader } from "@/components/site-header";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000"),
  title: {
    default: "Overtake — beat the people in your FPL mini-league",
    template: "%s · Overtake",
  },
  description:
    "Overtake simulates the rest of the season against your rivals' actual squads and tells you exactly what it takes to finish above them.",
  applicationName: "Overtake",
  manifest: "/manifest.webmanifest",
  openGraph: {
    type: "website",
    siteName: "Overtake",
    title: "Stop trying to beat 13 million strangers.",
    description:
      "Overtake works out what it takes to finish above the specific people in your FPL mini-league.",
  },
  twitter: { card: "summary_large_image" },
  robots: { index: true, follow: true },
};

export const viewport: Viewport = {
  themeColor: "#0B0F14",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en-GB">
      <body className="flex min-h-dvh flex-col">
        <a className="skip-link" href="#main">
          Skip to content
        </a>
        <SiteHeader />
        <main id="main" className="flex-1">
          {children}
        </main>
        <SiteFooter />
        <CookieConsent />
      </body>
    </html>
  );
}

function SiteFooter() {
  return (
    <footer className="mt-16 border-t border-border">
      <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
        <div className="flex flex-col gap-8 sm:flex-row sm:justify-between">
          <div className="max-w-sm">
            <span className="text-sm font-bold tracking-tight">OVERTAKE</span>
            <p className="mt-2 text-sm leading-relaxed text-ink-dim">
              You&apos;ll know exactly what it takes to catch them.
            </p>
          </div>
          <nav aria-label="Footer" className="grid grid-cols-2 gap-x-10 gap-y-2 text-sm sm:grid-cols-3">
            <FooterLink href="/how-it-works">How it works</FooterLink>
            <FooterLink href="/pricing">Pricing</FooterLink>
            <FooterLink href="/faq">FAQ</FooterLink>
            <FooterLink href="/mini-league/how-to-win-your-fpl-mini-league">
              Mini-league guides
            </FooterLink>
            <FooterLink href="/privacy">Privacy</FooterLink>
            <FooterLink href="/terms">Terms</FooterLink>
            <FooterLink href="/cookies">Cookies</FooterLink>
            <FooterLink href="/how-to/find-your-fpl-league-id">
              Find your league ID
            </FooterLink>
          </nav>
        </div>
        <p className="mt-8 border-t border-border pt-6 text-xs leading-relaxed text-ink-faint">
          Overtake is not affiliated with, endorsed by, or associated with the Premier
          League or Fantasy Premier League. We only read data that is already public on
          the FPL website, and we never ask for your FPL password. Briefs are generated
          by AI from simulation output; projections are estimates, and nothing here is
          advice of any regulated kind. This is not a gambling product: no odds, no
          stakes, no bookmakers, ever.
        </p>
      </div>
    </footer>
  );
}

function FooterLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link href={href} className="text-ink-dim transition-colors hover:text-ink">
      {children}
    </Link>
  );
}
