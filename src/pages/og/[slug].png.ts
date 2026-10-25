import type { APIRoute, GetStaticPaths } from "astro";
import { getDigests } from "../../lib/digest";
import { digestDateIso } from "../../lib/digest-utils";
import { renderOg } from "../../lib/og";

export const getStaticPaths = (async () => {
  const digests = await getDigests();
  return digests.map(({ entry }) => ({
    params: { slug: entry.id },
    props: { title: entry.data.title, date: entry.data.date, period: entry.data.period },
  }));
}) satisfies GetStaticPaths;

export const GET: APIRoute = async ({ props }) => {
  const { title, date, period } = props as { title: string; date: Date; period?: string };
  const subtitle = period ? `まとめ・対象期間 ${period}` : `まとめ・${digestDateIso(date)}`;
  const png = await renderOg({ title, subtitle });
  return new Response(new Uint8Array(png), { headers: { "Content-Type": "image/png" } });
};
