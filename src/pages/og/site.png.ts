import type { APIRoute } from "astro";
import { renderOg } from "../../lib/og";
import { SITE_NAME, SITE_DESCRIPTION } from "../../site";

export const GET: APIRoute = async () => {
  const png = await renderOg({ title: SITE_NAME, subtitle: SITE_DESCRIPTION });
  return new Response(new Uint8Array(png), { headers: { "Content-Type": "image/png" } });
};
