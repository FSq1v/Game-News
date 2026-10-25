import { describe, expect, it } from "vitest";
import { digestDateIso, digestOrder, formatDigestDate, h3Texts } from "./digest-utils";

const e = (id: string, iso: string) => ({ id, data: { date: new Date(iso) } });

describe("digestOrder", () => {
  it("新しい日が先、同じ日は id の降順", () => {
    const list = [e("2026-10-14", "2026-10-14"), e("2026-10-15", "2026-10-15"), e("2026-10-14-2", "2026-10-14")];
    expect(list.sort(digestOrder).map((x) => x.id)).toEqual(["2026-10-15", "2026-10-14-2", "2026-10-14"]);
  });
});

describe("h3Texts", () => {
  it("depth 3 だけ取る", () => {
    expect(h3Texts([{ depth: 2, text: "AI" }, { depth: 3, text: "a" }, { depth: 3, text: "b" }])).toEqual(["a", "b"]);
  });
});

describe("日付は日本時間", () => {
  it("UTC の 0 時でも 10/14 のまま", () => {
    const d = new Date("2026-10-14");
    expect(formatDigestDate(d)).toBe("2026年10月14日");
    expect(digestDateIso(d)).toBe("2026-10-14");
  });
});
