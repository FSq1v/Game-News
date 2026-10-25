import type { Genre, SourceStatus } from "./news";

// RSS 以外の取得元（ストア）の id と、画面に出す名前
const STORE_NAMES: Record<string, string> = {
  steam: "Steam",
  epic: "Epic Games Store",
  ps: "PlayStation Store",
  eshop: "ニンテンドーeショップ",
};

/** 取得元の id を、画面に出す名前にする */
export function sourceName(id: string): string {
  if (id.startsWith("rss:")) return id.slice(4);
  return STORE_NAMES[id] ?? id;
}

/** 取得元を genre ごとに分けて、名前の一覧にする。genre がない古い項目は game として扱う */
export function sourcesByGenre(sources: SourceStatus[]): Record<Genre, string[]> {
  const out: Record<Genre, string[]> = { game: [], ai: [] };
  for (const s of sources) {
    const list = out[s.genre ?? "game"];
    const name = sourceName(s.id);
    if (!list.includes(name)) list.push(name);
  }
  return out;
}
