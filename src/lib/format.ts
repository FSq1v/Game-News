export const STORE_NAMES = { steam: "Steam", epic: "Epic", ps: "PS Store", eshop: "Switch" } as const;

// 外部データの URL は http(s) だけ通す（javascript: などを防ぐ）
export function safeUrl(value: string | null | undefined): string {
  try {
    const url = new URL(value as string);
    return url.protocol === "http:" || url.protocol === "https:" ? url.href : "#";
  } catch {
    return "#";
  }
}

export function relativeTime(iso: string, now: Date): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  const minutes = Math.floor((now.getTime() - date.getTime()) / 60000);
  if (minutes < 1) return "たった今";
  if (minutes < 60) return `${minutes}分前`;
  if (minutes < 60 * 24) return `${Math.floor(minutes / 60)}時間前`;
  return `${date.getMonth() + 1}/${date.getDate()}`;
}

export function formatEnd(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getMonth() + 1}/${d.getDate()} ${pad(d.getHours())}:${pad(d.getMinutes())}まで`;
}

export const yen = (n: number): string => `¥${Number(n).toLocaleString("ja-JP")}`;
