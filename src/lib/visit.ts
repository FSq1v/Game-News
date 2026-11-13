// 「前回見たあとに増えた記事」を決める処理。保存（localStorage / sessionStorage）は呼ぶ側でする。
// 基準には端末の時計ではなく、そのとき見ていたデータの updated_at を使う（端末の時計がずれていても正しく比べられる）。

const ms = (iso: string | null | undefined): number => {
  if (!iso) return Number.NaN;
  return new Date(iso).getTime();
};

/**
 * このタブで使う基準を決める。
 * session：このタブに覚えさせた基準（タブで最初のページなら null）。"none" は「初めて来た人」
 * last：前回までに見たデータの時刻（localStorage）
 */
export function pickBase(session: string | null, last: string | null): { base: string | null; session: string } {
  if (session !== null) return { base: session === "none" ? null : session, session };
  if (last && !Number.isNaN(ms(last))) return { base: last, session: last };
  return { base: null, session: "none" };
}

/** 次に覚えておく「見たデータの時刻」。新しいほうを残す（古い版のページを見ても戻さない） */
export function nextLastSeen(last: string | null, current: string): string | null {
  const a = ms(last);
  const b = ms(current);
  if (Number.isNaN(b)) return Number.isNaN(a) ? null : last;
  if (Number.isNaN(a) || b > a) return current;
  return last;
}

/** Signal が記事を初めて取ってきた時刻が、基準より後なら新しい */
export function isNewSince(firstSeen: string, base: string | null): boolean {
  const a = ms(firstSeen);
  const b = ms(base);
  if (Number.isNaN(a) || Number.isNaN(b)) return false;
  return a > b;
}
