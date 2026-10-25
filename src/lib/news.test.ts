import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { expect, test } from "vitest";
import { byGenre, failedSources, loadNews, type NewsItem, type SourceStatus } from "./news";

const tmpFile = () => join(mkdtempSync(join(tmpdir(), "news-")), "news.json");

test("ファイルがないときは error: true で空", () => {
  const d = loadNews("does/not/exist.json");
  expect(d).toMatchObject({ error: true, news: [], deals: [], sources: [] });
});

test("壊れた JSON でも例外を投げない", () => {
  const p = tmpFile();
  writeFileSync(p, "{");
  expect(loadNews(p)).toMatchObject({ error: true, news: [] });
});

test("news が配列でなければ error", () => {
  const p = tmpFile();
  writeFileSync(p, JSON.stringify({ news: "x" }));
  expect(loadNews(p).error).toBe(true);
});

test("正しいファイルは error: false で読める", () => {
  const p = tmpFile();
  writeFileSync(p, JSON.stringify({ updated_at: "2026-10-25T00:00:00+09:00", sources: [], news: [{ id: "a" }] }));
  const d = loadNews(p);
  expect(d.error).toBe(false);
  expect(d.news).toHaveLength(1);
  expect(d.deals).toEqual([]);
});

test("既定の data/news.json を読める", () => {
  expect(loadNews().error).toBe(false);
});

test("byGenre は genre がない項目を game にする", () => {
  const items = [{ id: "a", genre: "ai" }, { id: "b" }, { id: "c", genre: "game" }] as NewsItem[];
  expect(byGenre(items, "game").map((n) => n.id)).toEqual(["b", "c"]);
  expect(byGenre(items, "ai").map((n) => n.id)).toEqual(["a"]);
});

test("failedSources", () => {
  expect(failedSources([{ id: "rss:Kotaku", ok: false }, { id: "steam", ok: false }, { id: "epic", ok: true }] as SourceStatus[]))
    .toEqual(["Kotaku", "Steam"]);
});
