import { expect, test } from "vitest";
import { formatEnd, formatShort, relativeTime, safeImageUrl, safeUrl, yen } from "./format";

test("safeUrl は http(s) だけ通す", () => {
  expect(safeUrl("https://a.jp/x")).toBe("https://a.jp/x");
  expect(safeUrl("javascript:alert(1)")).toBe("#");
  expect(safeUrl("data:text/html,x")).toBe("#");
  expect(safeUrl(null)).toBe("#");
  expect(safeUrl(undefined)).toBe("#");
  expect(safeUrl("not a url")).toBe("#");
});

test("relativeTime", () => {
  const now = new Date("2026-10-25T12:00:00+09:00");
  expect(relativeTime("2026-10-25T11:59:30+09:00", now)).toBe("たった今");
  expect(relativeTime("2026-10-25T11:15:00+09:00", now)).toBe("45分前");
  expect(relativeTime("2026-10-25T09:00:00+09:00", now)).toBe("3時間前");
  expect(relativeTime("2026-10-22T09:00:00+09:00", now)).toBe("10/22");
  expect(relativeTime("broken", now)).toBe("");
});

test("yen", () => expect(yen(12800)).toBe("¥12,800"));

test("formatEnd", () => {
  expect(formatEnd(null)).toBe("");
  // 表示はローカル時刻なので、ローカルで作った日時を使う
  const d = new Date(2026, 9, 5, 3, 7);
  expect(formatEnd(d.toISOString())).toBe("10/5 03:07まで");
});

test("timeZone を渡すとプロセスの TZ に関係なく JST で出る", () => {
  expect(formatEnd("2026-10-25T15:30:00Z", "Asia/Tokyo")).toBe("10/26 00:30まで");
  expect(formatShort("2026-10-25T15:30:00Z", "Asia/Tokyo")).toBe("10/26 00:30");
  expect(formatShort("broken", "Asia/Tokyo")).toBe("");
  expect(relativeTime("2026-10-21T16:00:00Z", new Date("2026-10-25T12:00:00+09:00"), "Asia/Tokyo")).toBe("10/22");
});

test("safeImageUrl は https だけ通し、http の画像はサムネイルなしにする", () => {
  expect(safeImageUrl("https://a.jp/x.png")).toBe("https://a.jp/x.png");
  expect(safeImageUrl("http://a.jp/x.png")).toBe("#");
  expect(safeImageUrl("javascript:alert(1)")).toBe("#");
  expect(safeImageUrl(null)).toBe("#");
});
