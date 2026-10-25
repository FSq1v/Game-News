import { readFileSync } from "node:fs";
import { sourceName } from "./sources";

export type Genre = "game" | "ai";
export type Region = "jp" | "global" | "official";

export type NewsItem = {
  id: string;
  title: string;
  title_original?: string;
  translated?: boolean;
  link: string;
  summary: string;
  source: string;
  region: Region;
  platforms: string[];
  image: string | null;
  published_at: string;
  first_seen: string;
  genre: Genre;
};

export type Deal = {
  id: string;
  store: "steam" | "epic" | "ps" | "eshop";
  title: string;
  link: string;
  image: string | null;
  price_original: number;
  price_sale: number;
  discount: number;
  is_free: boolean;
  upcoming: boolean;
  starts_at: string | null;
  ends_at: string | null;
};

export type SourceStatus = {
  id: string;
  ok: boolean;
  count: number;
  error: string | null;
  last_success: string | null;
  genre?: Genre;
};

export type NewsData = {
  updated_at: string | null;
  sources: SourceStatus[];
  news: NewsItem[];
  deals: Deal[];
};

const empty = (): NewsData & { error: boolean } => ({
  updated_at: null,
  sources: [],
  news: [],
  deals: [],
  error: true,
});

// ビルド時だけ動く。読めないときは例外を投げず、error: true の空データを返す
export function loadNews(path = "data/news.json"): NewsData & { error: boolean } {
  try {
    const raw = JSON.parse(readFileSync(path, "utf-8"));
    if (!raw || !Array.isArray(raw.news)) return empty();
    return {
      updated_at: raw.updated_at ?? null,
      sources: Array.isArray(raw.sources) ? raw.sources : [],
      news: raw.news,
      deals: Array.isArray(raw.deals) ? raw.deals : [],
      error: false,
    };
  } catch {
    return empty();
  }
}

// genre がない古い項目は game として扱う
export function byGenre(items: NewsItem[], genre: Genre): NewsItem[] {
  return items.filter((n) => (n.genre ?? "game") === genre);
}

/** 取得に失敗したソースの、画面に出す名前 */
export function failedSources(sources: SourceStatus[]): string[] {
  return sources.filter((s) => !s.ok).map((s) => sourceName(s.id));
}
