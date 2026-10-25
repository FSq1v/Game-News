// astro:content に依存しない部分。単体テストできるように分けてある。

/** 新しい順。同じ日は id の降順（2026-10-14-2 が 2026-10-14 より先） */
export function digestOrder(a: { id: string; data: { date: Date } }, b: { id: string; data: { date: Date } }): number {
  const diff = b.data.date.getTime() - a.data.date.getTime();
  if (diff !== 0) return diff;
  return a.id < b.id ? 1 : a.id > b.id ? -1 : 0;
}

export function h3Texts(headings: { depth: number; text: string }[]): string[] {
  return headings.filter((h) => h.depth === 3).map((h) => h.text);
}

/** 見出しを「、」でつなぎ、max 文字を超えるときは区切りで切って「…」を付ける（meta description と RSS 用） */
export function clampDescription(parts: string[], max = 120): string {
  const full = parts.join("、");
  if (full.length <= max) return full;
  let out = "";
  for (const p of parts) {
    const next = out ? `${out}、${p}` : p;
    if (next.length + 1 > max) break;
    out = next;
  }
  // 1 つ目の見出しだけで長すぎるときは文字数で切る
  if (!out) out = full.slice(0, max - 1);
  return `${out}…`;
}

/** 日付は日本時間で出す（ビルドは UTC で動くので、タイムゾーンを明示する） */
export function formatDigestDate(date: Date): string {
  return new Intl.DateTimeFormat("ja-JP", {
    timeZone: "Asia/Tokyo",
    year: "numeric",
    month: "long",
    day: "numeric",
  }).format(date);
}

/** datetime 属性用の YYYY-MM-DD（日本時間） */
export function digestDateIso(date: Date): string {
  return new Intl.DateTimeFormat("sv-SE", { timeZone: "Asia/Tokyo" }).format(date);
}
