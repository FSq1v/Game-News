import { getCollection, render, type CollectionEntry } from "astro:content";
import { digestOrder, h3Texts } from "./digest-utils";

export type Digest = { entry: CollectionEntry<"digest">; headings: string[] };

/** まとめ記事を新しい順に返す。headings は記事の見出し（h3）の文字列 */
export async function getDigests(): Promise<Digest[]> {
  const entries = (await getCollection("digest")).sort(digestOrder);
  return Promise.all(
    entries.map(async (entry) => {
      const { headings } = await render(entry);
      return { entry, headings: h3Texts(headings) };
    }),
  );
}
