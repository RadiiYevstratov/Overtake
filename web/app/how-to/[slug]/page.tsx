import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { GuidePage } from "@/components/guide-page";
import { GUIDES, findGuide, guidesFor } from "@/lib/guides";

type Params = Promise<{ slug: string }>;

export function generateStaticParams() {
  return guidesFor("how-to").map((guide) => ({ slug: guide.slug }));
}

export async function generateMetadata({ params }: { params: Params }): Promise<Metadata> {
  const { slug } = await params;
  const guide = findGuide("how-to", slug);
  if (!guide) return { title: "Not found" };
  return {
    title: guide.metaTitle,
    description: guide.description,
    alternates: { canonical: guide.href },
    openGraph: { title: guide.metaTitle, description: guide.description, url: guide.href },
  };
}

export default async function HowToGuide({ params }: { params: Params }) {
  const { slug } = await params;
  const guide = findGuide("how-to", slug);
  if (!guide) notFound();
  const related = GUIDES.filter((item) => item.href !== guide.href).slice(0, 3);
  return <GuidePage guide={guide} related={related} />;
}
