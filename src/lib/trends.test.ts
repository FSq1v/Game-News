import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { expect, test } from "vitest";
import { buzzHasHistory, formatGrowth, formatViewers, loadTrends, twitchHasHistory } from "./trends";

const tmpFile = () => join(mkdtempSync(join(tmpdir(), "trends-")), "trends.json");

test("ファイルがない・壊れているときは空", () => {
  expect(loadTrends("does/not/exist.json")).toMatchObject({ buzz: [], twitch: [], twitch_enabled: false });
  const p = tmpFile();
  writeFileSync(p, "{");
  expect(loadTrends(p).buzz).toEqual([]);
});

test("読み込み：配列でない値は空にする", () => {
  const p = tmpFile();
  writeFileSync(p, JSON.stringify({ buzz: "x", twitch: [{ name: "A" }], twitch_enabled: true, mention_days: 5 }));
  const d = loadTrends(p);
  expect(d.buzz).toEqual([]);
  expect(d.twitch).toHaveLength(1);
  expect(buzzHasHistory(d)).toBe(true);
  expect(twitchHasHistory(d)).toBe(false);
});

test("formatGrowth", () => {
  expect(formatGrowth(1.2)).toBe("+120%");
  expect(formatGrowth(0)).toBe("+0%");
  expect(formatGrowth(-0.25)).toBe("−25%");
  expect(formatGrowth(null)).toBe("");
});

test("formatViewers", () => {
  expect(formatViewers(8400)).toBe("8,400");
  expect(formatViewers(12345)).toBe("1.2万");
  expect(formatViewers(250000)).toBe("25万");
});
