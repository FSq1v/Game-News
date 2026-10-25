// @ts-check
import { defineConfig } from "astro/config";
import sitemap from "@astrojs/sitemap";
import { SITE_URL } from "./src/site.ts";

// build.format は初期値（directory）のまま。/digest/2026-10-14/index.html として出るので、
// Vercel 側で URL を書き換える設定（cleanUrls など）がなくても /digest/2026-10-14 が開ける。
export default defineConfig({
  site: SITE_URL,
  integrations: [sitemap()],
});
