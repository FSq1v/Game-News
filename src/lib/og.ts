import { readFileSync } from "node:fs";
import { join } from "node:path";
import satori from "satori";
import { Resvg } from "@resvg/resvg-js";
import { SITE_NAME } from "../site";

// satori は CSS 変数を読めないので、色だけここに 16 進で置く。
// 値は src/styles/tokens.css のライトテーマ（--bg / --text / --text-muted / --accent / --border）と同じ。
// 色をトークン以外で書いてよいのは、この OGP 画像と theme-color のメタだけ。
const COLOR = {
  bg: "#f5f5f7",
  text: "#1d1d1f",
  muted: "#636366",
  accent: "#0066cc",
  border: "#d2d2d7",
} as const;

const WIDTH = 1200;
const HEIGHT = 630;

// Astro はエンドポイントを dist/ のチャンクにまとめるので、import.meta.url ではなくプロジェクトの根から探す
let fontData: Buffer | undefined;
function loadFont(): Buffer {
  fontData ??= readFileSync(join(process.cwd(), "src/assets/fonts/NotoSansJP-Bold.otf"));
  return fontData;
}

type Node = { type: string; props: { style?: Record<string, string | number>; children?: unknown } };
const el = (type: string, style: Record<string, string | number>, children?: unknown): Node => ({
  type,
  props: { style, children },
});

export async function renderOg(opts: { title: string; subtitle: string }): Promise<Buffer> {
  const tree = el(
    "div",
    {
      display: "flex",
      flexDirection: "column",
      boxSizing: "border-box",
      width: WIDTH,
      height: HEIGHT,
      padding: "56px 80px 64px",
      backgroundColor: COLOR.bg,
      borderTop: `12px solid ${COLOR.accent}`,
      color: COLOR.text,
      fontFamily: "Noto Sans JP",
      fontWeight: 700,
    },
    [
      el("div", { display: "flex", alignItems: "center" }, [
        el("div", { width: 28, height: 28, borderRadius: 999, backgroundColor: COLOR.accent, marginRight: 16 }),
        el("div", { fontSize: 36, letterSpacing: "-0.02em" }, SITE_NAME),
      ]),
      // タイトルは残りの高さの中央に置き、3 行を超えたら末尾を … にする
      el("div", { display: "flex", flexGrow: 1, alignItems: "center", paddingBlock: 24 }, [
        el("div", { fontSize: 68, lineHeight: 1.3, letterSpacing: "-0.03em", lineClamp: 3 }, opts.title),
      ]),
      el(
        "div",
        { fontSize: 30, lineHeight: 1.5, color: COLOR.muted, paddingTop: 24, borderTop: `2px solid ${COLOR.border}`, lineClamp: 2 },
        opts.subtitle,
      ),
    ],
  );

  // satori の型は React 要素を想定しているので、プレーンなオブジェクトはここで型を合わせる
  const svg = await satori(tree as unknown as Parameters<typeof satori>[0], {
    width: WIDTH,
    height: HEIGHT,
    fonts: [{ name: "Noto Sans JP", data: loadFont(), weight: 700, style: "normal" }],
  });
  return Buffer.from(new Resvg(svg, { fitTo: { mode: "width", value: WIDTH } }).render().asPng());
}
