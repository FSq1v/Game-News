import rss from "@astrojs/rss";
import type { APIContext } from "astro";
import { getDigests } from "../lib/digest";
import { SITE_DESCRIPTION, SITE_NAME } from "../site";

export async function GET(context: APIContext) {
  const digests = await getDigests();
  return rss({
    title: SITE_NAME,
    description: SITE_DESCRIPTION,
    site: context.site!,
    customData: "<language>ja</language>",
    items: digests.map(({ entry, headings }) => ({
      title: entry.data.title,
      pubDate: entry.data.date,
      link: `/digest/${entry.id}`,
      description: headings.join("、"),
    })),
  });
}
