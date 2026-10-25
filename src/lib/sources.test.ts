import { expect, test } from "vitest";
import type { SourceStatus } from "./news";
import { sourceName, sourcesByGenre } from "./sources";

const src = (id: string, genre?: "game" | "ai"): SourceStatus => ({
  id,
  ok: true,
  count: 1,
  error: null,
  last_success: null,
  ...(genre ? { genre } : {}),
});

test("rss: を取った名前にする", () => {
  expect(sourceName("rss:4Gamer")).toBe("4Gamer");
  expect(sourceName("rss:The Verge AI")).toBe("The Verge AI");
});

test("ストアの id は読める名前にする", () => {
  expect(sourceName("steam")).toBe("Steam");
  expect(sourceName("epic")).toBe("Epic Games Store");
  expect(sourceName("ps")).toBe("PlayStation Store");
  expect(sourceName("eshop")).toBe("ニンテンドーeショップ");
});

test("知らない id はそのまま出す", () => {
  expect(sourceName("other")).toBe("other");
});

test("genre ごとに分ける。genre がないものは game", () => {
  const grouped = sourcesByGenre([src("rss:A", "game"), src("rss:B", "ai"), src("steam")]);
  expect(grouped).toEqual({ game: ["A", "Steam"], ai: ["B"] });
});

test("同じ名前は 1 回だけ出す", () => {
  expect(sourcesByGenre([src("rss:A"), src("rss:A")]).game).toEqual(["A"]);
});
