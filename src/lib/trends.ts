import { readFileSync } from "node:fs";

// data/trends.json の形（fetcher/main.py の update_trends が書く）。history は画面では使わない

export type BuzzItem = {
  name: string;
  /** 直近 3 日に取り上げた記事の数 */
  recent: number;
  /** その前の 7 日の数 */
  prev: number;
  sources: string[];
  score: number;
  articles: { title: string; link: string; source: string }[];
};

export type TwitchItem = {
  name: string;
  /** 最新の日の平均視聴者数 */
  viewers: number;
  /** 前の 7 日の平均。記録がまだなければ null */
  prev_viewers: number | null;
  /** (viewers - prev) / prev。記録がまだなければ null */
  growth: number | null;
  box_art: string;
};

export type TrendsData = {
  updated_at: string | null;
  twitch_enabled: boolean;
  mention_days: number;
  twitch_days: number;
  buzz: BuzzItem[];
  twitch: TwitchItem[];
};

const empty = (): TrendsData => ({
  updated_at: null,
  twitch_enabled: false,
  mention_days: 0,
  twitch_days: 0,
  buzz: [],
  twitch: [],
});

// ビルド時だけ動く。読めないときは例外を投げず、空のデータを返す（ページは「まだデータがない」と出す）
export function loadTrends(path = "data/trends.json"): TrendsData {
  try {
    const raw = JSON.parse(readFileSync(path, "utf-8"));
    if (!raw || typeof raw !== "object") return empty();
    return {
      updated_at: raw.updated_at ?? null,
      twitch_enabled: raw.twitch_enabled === true,
      mention_days: Number(raw.mention_days) || 0,
      twitch_days: Number(raw.twitch_days) || 0,
      buzz: Array.isArray(raw.buzz) ? raw.buzz : [],
      twitch: Array.isArray(raw.twitch) ? raw.twitch : [],
    };
  } catch {
    return empty();
  }
}

/** 前の 7 日と比べられるだけの記録があるか（直近 3 日＋前の日が 1 日以上） */
export const buzzHasHistory = (d: TrendsData) => d.mention_days >= 4;
export const twitchHasHistory = (d: TrendsData) => d.twitch_days >= 2;

/** 伸び率を「+120%」のように出す。比べられないときは空文字 */
export function formatGrowth(growth: number | null): string {
  if (growth === null || !Number.isFinite(growth)) return "";
  const pct = Math.round(growth * 100);
  return `${pct >= 0 ? "+" : "−"}${Math.abs(pct)}%`;
}

/** 視聴者数を「1.2万」「8,400」のように出す */
export function formatViewers(n: number): string {
  if (n >= 10000) return `${(n / 10000).toFixed(n >= 100000 ? 0 : 1)}万`;
  return n.toLocaleString("ja-JP");
}
