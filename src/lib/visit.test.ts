import { expect, test } from "vitest";
import { isNewSince, nextLastSeen, pickBase } from "./visit";

test("pickBase：タブで最初のページは、前回見たデータの時刻を基準にして、タブに覚えさせる", () => {
  expect(pickBase(null, "2026-11-12T10:00:00+09:00")).toEqual({
    base: "2026-11-12T10:00:00+09:00",
    session: "2026-11-12T10:00:00+09:00",
  });
});

test("pickBase：同じタブで次のページに移っても、最初に決めた基準を使う（印が消えない）", () => {
  expect(pickBase("2026-11-12T10:00:00+09:00", "2026-11-13T09:00:00+09:00")).toEqual({
    base: "2026-11-12T10:00:00+09:00",
    session: "2026-11-12T10:00:00+09:00",
  });
});

test("pickBase：初めて来た人は基準なし（全部に印を付けない）。タブにも「なし」を覚えさせる", () => {
  expect(pickBase(null, null)).toEqual({ base: null, session: "none" });
  expect(pickBase("none", "2026-11-13T09:00:00+09:00")).toEqual({ base: null, session: "none" });
});

test("nextLastSeen：見たデータの時刻を覚える。古い版が出たときに戻さない", () => {
  expect(nextLastSeen(null, "2026-11-13T09:00:00+09:00")).toBe("2026-11-13T09:00:00+09:00");
  expect(nextLastSeen("2026-11-13T09:00:00+09:00", "2026-11-13T12:00:00+09:00")).toBe("2026-11-13T12:00:00+09:00");
  expect(nextLastSeen("2026-11-13T12:00:00+09:00", "2026-11-13T09:00:00+09:00")).toBe("2026-11-13T12:00:00+09:00");
  expect(nextLastSeen("broken", "2026-11-13T09:00:00+09:00")).toBe("2026-11-13T09:00:00+09:00");
  expect(nextLastSeen("2026-11-13T09:00:00+09:00", "broken")).toBe("2026-11-13T09:00:00+09:00");
});

test("isNewSince：基準より後に Signal が取ってきた記事だけ新しい", () => {
  const base = "2026-11-13T09:00:00+09:00";
  expect(isNewSince("2026-11-13T09:30:00+09:00", base)).toBe(true);
  expect(isNewSince("2026-11-13T09:00:00+09:00", base)).toBe(false);
  expect(isNewSince("2026-11-13T08:00:00+09:00", base)).toBe(false);
  // タイムゾーンの書き方が違っても同じ時刻として比べる
  expect(isNewSince("2026-11-13T00:30:00Z", base)).toBe(true);
  expect(isNewSince("2026-11-13T09:30:00+09:00", null)).toBe(false);
  expect(isNewSince("broken", base)).toBe(false);
});
