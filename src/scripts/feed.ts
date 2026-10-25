// フィードの画面操作。カードの HTML はビルドのときにできているので、ここでは
// data-* を読んで hidden を付け外しし、並べ替えのときは既存の要素を並べ直すだけにする。
import { formatShort, relativeTime } from "../lib/format";
import { matchesDeal, matchesNews, sortDeals, type DealState, type FeedState } from "../lib/filter";
import type { Deal, Region } from "../lib/news";

const FAV_KEY = "gamefeed_favs_v2";
const STALE_MINUTES = 180;

// ---------- お気に入り ----------
function loadFavs(): Set<string> {
  try {
    const raw: unknown = JSON.parse(localStorage.getItem(FAV_KEY) || "[]");
    return new Set(Array.isArray(raw) ? raw.filter((v): v is string => typeof v === "string") : []);
  } catch {
    return new Set();
  }
}

function saveFavs(favs: Set<string>): void {
  try {
    localStorage.setItem(FAV_KEY, JSON.stringify([...favs]));
  } catch {
    // プライベートモードなどで保存できなくても、このページを開いているあいだは使えるようにする
  }
}

const favs = loadFavs();
const refreshers: (() => void)[] = [];

function syncFavButton(button: HTMLButtonElement): void {
  const id = button.dataset.fav ?? "";
  const title = button.dataset.favTitle ?? "";
  const on = favs.has(id);
  button.setAttribute("aria-pressed", String(on));
  const label = button.querySelector(".visually-hidden");
  if (label) label.textContent = on ? `${title}をお気に入りから外す` : `${title}をお気に入りに追加`;
}

function initFavs(): void {
  const buttons = [...document.querySelectorAll<HTMLButtonElement>("button[data-fav]")];
  buttons.forEach(syncFavButton);
  document.addEventListener("click", (e) => {
    const button = (e.target as Element | null)?.closest<HTMLButtonElement>("button[data-fav]");
    if (!button) return;
    const id = button.dataset.fav ?? "";
    if (favs.has(id)) favs.delete(id);
    else favs.add(id);
    saveFavs(favs);
    buttons.filter((b) => b.dataset.fav === id).forEach(syncFavButton);
    // 「お気に入り」で絞り込んでいるフィードは、外した記事をすぐ消す
    refreshers.forEach((fn) => fn());
  });
}

// ---------- 時刻 ----------
function updateTimes(): void {
  const now = new Date();
  document.querySelectorAll<HTMLTimeElement>("time[data-rel]").forEach((el) => {
    const text = relativeTime(el.dateTime, now);
    if (!text) return;
    el.textContent = text;
    el.title = formatShort(el.dateTime);
  });
  document.querySelectorAll<HTMLElement>("[data-status]").forEach((status) => {
    const time = status.querySelector<HTMLTimeElement>("time");
    if (!time) return;
    const minutes = (now.getTime() - new Date(time.dateTime).getTime()) / 60000;
    const stale = minutes > STALE_MINUTES;
    status.classList.toggle("is-stale", stale);
    const note = status.querySelector<HTMLElement>("[data-stale]");
    if (note) note.hidden = !stale;
  });
}

// ---------- 画像 ----------
function initImages(): void {
  document.querySelectorAll<HTMLImageElement>(".thumb img").forEach((img) => {
    const miss = () => img.parentElement?.classList.add("is-missing");
    // スクリプトが動く前に読み込みに失敗していた画像も拾う
    if (img.complete && img.naturalWidth === 0 && img.currentSrc) miss();
    else img.addEventListener("error", miss, { once: true });
  });
}

// ---------- 押しっぱなしのボタンの組（チップ） ----------
function bindPressed(group: Element, attr: string, onSelect: (value: string) => void): void {
  const buttons = [...group.querySelectorAll<HTMLButtonElement>(`button[data-${attr}]`)];
  group.addEventListener("click", (e) => {
    const button = (e.target as Element | null)?.closest<HTMLButtonElement>("button");
    if (!button || !buttons.includes(button)) return;
    buttons.forEach((b) => b.setAttribute("aria-pressed", String(b === button)));
    onSelect(button.getAttribute(`data-${attr}`) ?? "");
  });
  // スマホではチップの列が横にスクロールするので、Tab で来たチップが端で切れないように寄せる
  group.addEventListener("focusin", (e) => {
    (e.target as Element | null)?.scrollIntoView?.({ block: "nearest", inline: "nearest" });
  });
}

// ---------- ニュース ----------
const REGIONS = ["all", "jp", "global", "official", "fav"] as const;

function initFeed(root: HTMLElement): void {
  const cards = [...root.querySelectorAll<HTMLElement>("li[data-id]")];
  const count = root.querySelector<HTMLElement>("[data-count]");
  const empty = root.querySelector<HTMLElement>("[data-empty]");
  const input = root.querySelector<HTMLInputElement>("input[data-search-input]");
  const chips = root.querySelector('[role="group"]');
  const state: FeedState = { region: "all", query: "", favs };

  const apply = () => {
    let shown = 0;
    for (const card of cards) {
      const ok = matchesNews(
        {
          id: card.dataset.id ?? "",
          // data-search にタイトル・原題・出典を小文字でまとめてある
          title: card.dataset.search ?? "",
          source: "",
          region: (card.dataset.region ?? "") as Region,
        },
        state,
      );
      card.hidden = !ok;
      if (ok) shown += 1;
    }
    if (count) count.textContent = `${shown} 件`;
    if (empty) {
      empty.hidden = shown > 0;
      if (shown === 0) {
        empty.textContent = state.region === "fav"
          ? "☆ を押した記事がここに並びます。"
          : "条件に合う記事はありません。絞り込みや検索を変えてみてください。";
      }
    }
  };

  if (chips) {
    bindPressed(chips, "region", (value) => {
      state.region = (REGIONS as readonly string[]).includes(value) ? (value as FeedState["region"]) : "all";
      apply();
    });
  }
  if (input) {
    const read = () => {
      state.query = input.value.trim().toLowerCase();
      apply();
    };
    input.addEventListener("input", read);
    // 戻るボタンなどで入力欄に文字が残っていたときも、その文字で絞り込む
    if (input.value) read();
  }
  refreshers.push(() => {
    if (state.region === "fav") apply();
  });
}

// ---------- セール ----------
const STORES = ["all", "steam", "epic", "ps", "eshop"] as const;
const SORTS = ["default", "discount", "ending", "price"] as const;
type Sort = (typeof SORTS)[number];

function initDeals(root: HTMLElement): void {
  const list = root.querySelector<HTMLElement>("[data-deal-list]");
  const free = [...root.querySelectorAll<HTMLElement>("[data-free-list] > li")];
  const count = root.querySelector<HTMLElement>("[data-count]");
  const empty = root.querySelector<HTMLElement>("[data-empty]");
  const select = root.querySelector<HTMLSelectElement>("select[data-sort]");
  const input = root.querySelector<HTMLInputElement>("input[data-search-input]");
  const chips = root.querySelector('[role="group"]');
  const state: DealState = { store: "all", query: "" };

  // 並べ替えに使う値。最初の並び（おすすめ順）はこの配列の順番として残る
  const paid = [...(list?.querySelectorAll<HTMLElement>(":scope > li") ?? [])].map((el) => {
    const ends = el.dataset.ends ? Number(el.dataset.ends) : NaN;
    return {
      el,
      discount: Number(el.dataset.discount) || 0,
      price_sale: Number(el.dataset.price) || 0,
      ends_at: Number.isNaN(ends) ? null : new Date(ends).toISOString(),
    };
  });

  const matches = (el: HTMLElement) =>
    matchesDeal(
      { store: (el.dataset.store ?? "") as Deal["store"], title: el.dataset.search ?? "" },
      state,
    );

  let sort: Sort = "default";

  const apply = () => {
    let shown = 0;
    for (const el of free) {
      el.hidden = !matches(el);
      if (!el.hidden) shown += 1;
    }
    for (const { el } of paid) {
      el.hidden = !matches(el);
      if (!el.hidden) shown += 1;
    }
    if (count) count.textContent = `${shown} 件`;
    if (empty) {
      empty.hidden = shown > 0;
      if (shown === 0) empty.textContent = "条件に合うセールはありません。ストアや検索を変えてみてください。";
    }
  };

  const reorder = () => {
    if (!list) return;
    // 要素は作り直さず、今ある li を順番どおりに付け直す
    list.append(...sortDeals(paid, sort).map((d) => d.el));
  };

  if (chips) {
    bindPressed(chips, "store", (value) => {
      state.store = (STORES as readonly string[]).includes(value) ? (value as DealState["store"]) : "all";
      apply();
    });
  }
  if (input) {
    const readQuery = () => {
      state.query = input.value.trim().toLowerCase();
      apply();
    };
    input.addEventListener("input", readQuery);
    // 戻るボタンなどで入力欄に文字が残っていたときも、その文字で絞り込む
    if (input.value) readQuery();
  }
  if (select) {
    const read = () => {
      sort = (SORTS as readonly string[]).includes(select.value) ? (select.value as Sort) : "default";
      reorder();
    };
    select.addEventListener("change", read);
    if (select.value !== "default") read();
  }
}

// ---------- タブ（/game の 899px 以下） ----------
function initTabs(root: HTMLElement): void {
  const tabs = [...root.querySelectorAll<HTMLButtonElement>('[role="tab"]')];
  const panels = tabs.map((t) => document.getElementById(t.getAttribute("aria-controls") ?? ""));
  if (tabs.length === 0 || panels.some((p) => !p)) return;
  const narrow = window.matchMedia("(max-width: 899px)");

  const select = (index: number, focus: boolean) => {
    tabs.forEach((tab, i) => {
      const on = i === index;
      tab.setAttribute("aria-selected", String(on));
      tab.tabIndex = on ? 0 : -1;
      panels[i]!.classList.toggle("is-active", on);
    });
    if (focus) tabs[index]!.focus();
  };

  // 2 カラムのときはタブを見せないので、パネルも普通のセクションに戻す
  const syncRoles = () => {
    panels.forEach((panel, i) => {
      if (narrow.matches) {
        panel!.setAttribute("role", "tabpanel");
        panel!.setAttribute("aria-labelledby", tabs[i]!.id);
      } else {
        panel!.removeAttribute("role");
        panel!.removeAttribute("aria-labelledby");
      }
    });
  };

  tabs.forEach((tab, i) => {
    tab.addEventListener("click", () => select(i, false));
    tab.addEventListener("keydown", (e) => {
      const last = tabs.length - 1;
      const next =
        e.key === "ArrowRight" ? (i === last ? 0 : i + 1)
        : e.key === "ArrowLeft" ? (i === 0 ? last : i - 1)
        : e.key === "Home" ? 0
        : e.key === "End" ? last
        : -1;
      if (next < 0) return;
      e.preventDefault();
      select(next, true);
    });
  });

  const initial = Math.max(0, tabs.findIndex((t) => t.getAttribute("aria-selected") === "true"));
  select(initial, false);
  syncRoles();
  narrow.addEventListener("change", syncRoles);
  root.classList.add("is-tabbed");
}

// ---------- 起動 ----------
initImages();
initFavs();
document.querySelectorAll<HTMLElement>("[data-feed]").forEach(initFeed);
document.querySelectorAll<HTMLElement>("[data-deals]").forEach(initDeals);
document.querySelectorAll<HTMLElement>("[data-tabs]").forEach(initTabs);
updateTimes();
// 開きっぱなしでも「◯分前」がずれないように、1 分ごとに書き直す
setInterval(updateTimes, 60_000);
