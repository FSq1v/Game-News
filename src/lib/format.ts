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

// 月日時分を取り出す。timeZone を渡すとプロセスの TZ に左右されない
function parts(date: Date, timeZone?: string) {
  if (!timeZone) {
    return { month: date.getMonth() + 1, day: date.getDate(), hour: date.getHours(), minute: date.getMinutes() };
  }
  const p = Object.fromEntries(
    new Intl.DateTimeFormat("ja-JP", {
      timeZone, month: "numeric", day: "numeric", hour: "numeric", minute: "numeric", hourCycle: "h23",
    }).formatToParts(date).map((x) => [x.type, Number(x.value)]),
  );
  return { month: p.month, day: p.day, hour: p.hour, minute: p.minute };
}

const pad = (n: number) => String(n).padStart(2, "0");

export function relativeTime(iso: string, now: Date, timeZone?: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  const minutes = Math.floor((now.getTime() - date.getTime()) / 60000);
  if (minutes < 1) return "たった今";
  if (minutes < 60) return `${minutes}分前`;
  if (minutes < 60 * 24) return `${Math.floor(minutes / 60)}時間前`;
  const { month, day } = parts(date, timeZone);
  return `${month}/${day}`;
}

export function formatShort(iso: string, timeZone?: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const { month, day, hour, minute } = parts(d, timeZone);
  return `${month}/${day} ${pad(hour)}:${pad(minute)}`;
}

export function formatEnd(iso: string | null, timeZone?: string): string {
  if (!iso) return "";
  const s = formatShort(iso, timeZone);
  return s ? `${s}まで` : "";
}

export const yen = (n: number): string => `¥${Number(n).toLocaleString("ja-JP")}`;
