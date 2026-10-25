import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";

// scripts/sync_digests.py が書き出したまとめ記事。id（slug）はファイル名（2026-10-14、2026-10-14-2）
const digest = defineCollection({
  loader: glob({ pattern: "*.md", base: "./src/content/digest" }),
  schema: z.object({
    title: z.string(),
    date: z.coerce.date(),
    period: z.string().optional(),
    tags: z.array(z.string()).default([]),
  }),
});

export const collections = { digest };
