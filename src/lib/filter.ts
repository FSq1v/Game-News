import { STORE_NAMES } from "./format";
import type { Deal, NewsItem } from "./news";

export { STORE_NAMES };

export type FeedState = {
  region: "all" | "jp" | "global" | "official" | "fav";
  query: string; // 呼ぶ側で trim().toLowerCase() 済み
  favs: Set<string>;
};

export type DealState = {
  store: "all" | "steam" | "epic" | "ps" | "eshop";
  query: string; // 呼ぶ側で trim().toLowerCase() 済み
};

const hit = (values: (string | undefined)[], q: string) =>
  values.some((v) => v && v.toLowerCase().includes(q));

export function matchesNews(
  item: Pick<NewsItem, "id" | "title" | "title_original" | "source" | "region">,
  state: FeedState,
): boolean {
  const inRegion = state.region === "fav"
    ? state.favs.has(item.id)
    : state.region === "all" || item.region === state.region;
  if (!inRegion) return false;
  if (!state.query) return true;
  return hit([item.title, item.title_original, item.source], state.query);
}

export function matchesDeal(item: Pick<Deal, "store" | "title">, state: DealState): boolean {
  if (state.store !== "all" && item.store !== state.store) return false;
  if (!state.query) return true;
  return hit([item.title, STORE_NAMES[item.store]], state.query);
}

export function sortDeals<T extends Pick<Deal, "discount" | "price_sale" | "ends_at">>(
  deals: T[],
  sort: "default" | "discount" | "ending" | "price",
): T[] {
  const sorted = [...deals];
  const end = (d: T) => (d.ends_at ? new Date(d.ends_at).getTime() : Infinity);
  if (sort === "discount") sorted.sort((a, b) => b.discount - a.discount);
  if (sort === "ending") sorted.sort((a, b) => end(a) - end(b));
  if (sort === "price") sorted.sort((a, b) => a.price_sale - b.price_sale);
  return sorted;
}
