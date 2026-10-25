import { expect, test } from "vitest";
import { matchesDeal, matchesNews, sortDeals, type DealState, type FeedState } from "./filter";

const base: FeedState = { region: "all", query: "", favs: new Set<string>() };
const item = { id: "n1", title: "Claude の新モデル", title_original: "New Claude model", source: "The Verge AI", region: "global" as const };

test("地域の絞り込み", () => {
  expect(matchesNews(item, { ...base, region: "global" })).toBe(true);
  expect(matchesNews(item, { ...base, region: "jp" })).toBe(false);
});

test("お気に入り", () => {
  expect(matchesNews(item, { ...base, region: "fav" })).toBe(false);
  expect(matchesNews(item, { ...base, region: "fav", favs: new Set(["n1"]) })).toBe(true);
});

test("検索は原題と出典にも当たる。大文字小文字は区別しない", () => {
  expect(matchesNews(item, { ...base, query: "new claude" })).toBe(true);
  expect(matchesNews(item, { ...base, query: "verge" })).toBe(true);
  expect(matchesNews(item, { ...base, query: "unity" })).toBe(false);
});

const dealBase: DealState = { store: "all", query: "" };
const deal = { store: "ps" as const, title: "Elden Ring" };

test("matchesDeal のストア絞り込み", () => {
  expect(matchesDeal(deal, dealBase)).toBe(true);
  expect(matchesDeal(deal, { ...dealBase, store: "ps" })).toBe(true);
  expect(matchesDeal(deal, { ...dealBase, store: "steam" })).toBe(false);
});

test("matchesDeal の検索はタイトルとストア表示名に当たる", () => {
  expect(matchesDeal(deal, { ...dealBase, query: "elden" })).toBe(true);
  expect(matchesDeal(deal, { ...dealBase, query: "ps store" })).toBe(true);
  expect(matchesDeal(deal, { ...dealBase, query: "steam" })).toBe(false);
});

test("sortDeals の ending は終了日なしを最後にする", () => {
  const d = [{ discount: 10, price_sale: 100, ends_at: null }, { discount: 50, price_sale: 500, ends_at: "2026-10-26T00:00:00+09:00" }];
  expect(sortDeals(d, "ending")[0].discount).toBe(50);
  expect(sortDeals(d, "discount")[0].discount).toBe(50);
  expect(sortDeals(d, "price")[0].discount).toBe(10);
  expect(sortDeals(d, "default")).toEqual(d);
});
