"use strict";

const FAV_KEY = "gamefeed_favs_v2";
const STALE_MINUTES = 180;
const STORE_NAMES = { steam: "Steam", epic: "Epic", ps: "PS Store", eshop: "Switch" };

const state = {
  data: null,
  newsFilter: "all",
  store: "all",
  sort: "default",
  query: "",
  favs: loadFavs(),
};

const $ = (id) => document.getElementById(id);

function loadFavs() {
  try {
    return new Set(JSON.parse(localStorage.getItem(FAV_KEY) || "[]"));
  } catch {
    return new Set();
  }
}

function saveFavs() {
  try {
    localStorage.setItem(FAV_KEY, JSON.stringify([...state.favs]));
  } catch {
    /* プライベートモードなどで保存できなくても表示は続ける */
  }
}

// 外部データの URL は http(s) だけ通す（javascript: などを防ぐ）
function safeUrl(value) {
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:" ? url.href : "#";
  } catch {
    return "#";
  }
}

function relativeTime(iso, now = new Date()) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  const minutes = Math.floor((now - date) / 60000);
  if (minutes < 1) return "たった今";
  if (minutes < 60) return `${minutes}分前`;
  if (minutes < 60 * 24) return `${Math.floor(minutes / 60)}時間前`;
  return `${date.getMonth() + 1}/${date.getDate()}`;
}

function formatEnd(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getMonth() + 1}/${d.getDate()} ${pad(d.getHours())}:${pad(d.getMinutes())}まで`;
}

const yen = (n) => `¥${Number(n).toLocaleString("ja-JP")}`;

function setImage(container, src, label) {
  container.dataset.label = label;
  const img = container.querySelector("img");
  const url = src ? safeUrl(src) : "#";
  if (url === "#") {
    container.classList.add("is-missing");
    return;
  }
  img.addEventListener("error", () => container.classList.add("is-missing"), { once: true });
  img.src = url;
}

function favButton(button, id, title) {
  const on = state.favs.has(id);
  button.setAttribute("aria-pressed", String(on));
  button.querySelector(".visually-hidden").textContent = on ? `${title} をお気に入りから外す` : `${title} をお気に入りに追加`;
  button.addEventListener("click", () => {
    if (state.favs.has(id)) state.favs.delete(id);
    else state.favs.add(id);
    saveFavs();
    render();
  });
}

function matches(item) {
  if (!state.query) return true;
  const q = state.query;
  return [item.title, item.title_original, item.source, STORE_NAMES[item.store]]
    .some((v) => v && v.toLowerCase().includes(q));
}

// ---------- ニュース ----------
function renderNews() {
  const list = $("news-list");
  const tpl = $("news-item");
  const now = new Date();
  const inFilter = (n) => state.newsFilter === "fav" ? state.favs.has(n.id)
    : state.newsFilter === "all" || n.region === state.newsFilter;
  const items = state.data.news.filter((n) => inFilter(n) && matches(n));

  list.replaceChildren(...items.map((n) => {
    const li = tpl.content.firstElementChild.cloneNode(true);
    const link = li.querySelector(".news-item__link");
    link.href = safeUrl(n.link);
    setImage(li.querySelector(".thumb"), n.image, n.source);
    const title = li.querySelector(".news-item__title");
    title.textContent = n.title;
    if (n.translated && n.title_original) title.title = `原題：${n.title_original}`;
    li.querySelector(".news-item__source").textContent = n.source;
    const time = li.querySelector("time");
    time.dateTime = n.published_at;
    time.textContent = relativeTime(n.published_at, now);
    li.querySelector(".badge").hidden = !n.translated;
    favButton(li.querySelector(".fav"), n.id, n.title);
    return li;
  }));

  const empty = $("news-empty");
  empty.hidden = items.length > 0;
  empty.textContent = state.newsFilter === "fav"
    ? "☆ を押した記事がここに並びます。"
    : "条件に合う記事はありません。絞り込みや検索を変えてみてください。";
}

// ---------- セール ----------
function sortDeals(deals) {
  const sorted = [...deals];
  const end = (d) => (d.ends_at ? new Date(d.ends_at).getTime() : Infinity);
  if (state.sort === "discount") sorted.sort((a, b) => b.discount - a.discount);
  if (state.sort === "ending") sorted.sort((a, b) => end(a) - end(b));
  if (state.sort === "price") sorted.sort((a, b) => a.price_sale - b.price_sale);
  return sorted;
}

function renderFree(freeDeals) {
  const tpl = $("free-item");
  $("free").replaceChildren(...freeDeals.map((d) => {
    const card = tpl.content.firstElementChild.cloneNode(true);
    card.href = safeUrl(d.link);
    card.classList.toggle("is-upcoming", d.upcoming);
    const img = card.querySelector("img");
    if (d.image && safeUrl(d.image) !== "#") img.src = safeUrl(d.image);
    card.querySelector(".free-card__label").textContent = d.upcoming ? "来週の無料" : "いま無料";
    card.querySelector(".free-card__title").textContent = d.title;
    card.querySelector(".free-card__when").textContent = d.upcoming
      ? `${formatEnd(d.starts_at).replace("まで", "から")} 配布予定`
      : `${formatEnd(d.ends_at)}（通常 ${yen(d.price_original)}）`;
    return card;
  }));
}

function renderDeals() {
  const deals = state.data.deals.filter((d) =>
    (state.store === "all" || d.store === state.store) && matches(d));
  const free = deals.filter((d) => d.is_free).sort((a, b) => a.upcoming - b.upcoming);
  const paid = sortDeals(deals.filter((d) => !d.is_free));
  renderFree(free);

  const tpl = $("deal-item");
  $("deal-list").replaceChildren(...paid.map((d) => {
    const li = tpl.content.firstElementChild.cloneNode(true);
    li.querySelector(".deal__link").href = safeUrl(d.link);
    setImage(li.querySelector(".thumb"), d.image, STORE_NAMES[d.store] || "");
    li.querySelector(".deal__title").textContent = d.title;
    li.querySelector(".deal__title").title = d.title;
    const mark = li.querySelector(".store-mark");
    mark.dataset.store = d.store;
    mark.textContent = STORE_NAMES[d.store] || d.store;
    li.querySelector(".deal__ends").textContent = formatEnd(d.ends_at);
    li.querySelector(".tag__off").textContent = `-${d.discount}%`;
    li.querySelector(".tag__price").textContent = yen(d.price_sale);
    li.querySelector(".tag__was").textContent = yen(d.price_original);
    return li;
  }));

  const empty = $("deals-empty");
  empty.hidden = free.length + paid.length > 0;
  empty.textContent = "条件に合うセールはありません。ストアや検索を変えてみてください。";
}

// ---------- ヘッダーの更新状況 ----------
function renderStatus() {
  const status = $("status");
  const { updated_at: updatedAt, sources = [] } = state.data;
  const minutes = (Date.now() - new Date(updatedAt).getTime()) / 60000;
  status.classList.toggle("is-stale", minutes >= STALE_MINUTES);
  status.replaceChildren(`最終更新 ${relativeTime(updatedAt)}`);
  const failed = sources.filter((s) => !s.ok).map((s) => s.id.replace(/^rss:/, ""));
  if (failed.length) {
    const note = document.createElement("span");
    note.className = "status__failed";
    note.textContent = `一部の取得に失敗：${failed.join("、")}`;
    status.append(note);
  }
}

function render() {
  if (!state.data) return;
  renderStatus();
  renderNews();
  renderDeals();
}

// ---------- 操作 ----------
function bindPressedGroup(groupId, attr, onSelect) {
  const group = $(groupId);
  group.addEventListener("click", (e) => {
    const button = e.target.closest("button");
    if (!button || !group.contains(button)) return;
    group.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b === button)));
    onSelect(button.dataset[attr]);
  });
}

function bindEvents() {
  bindPressedGroup("news-filters", "filter", (v) => { state.newsFilter = v; renderNews(); });
  bindPressedGroup("store-filters", "store", (v) => { state.store = v; renderDeals(); });
  $("deal-sort").addEventListener("change", (e) => { state.sort = e.target.value; renderDeals(); });
  $("search").addEventListener("input", (e) => {
    state.query = e.target.value.trim().toLowerCase();
    renderNews();
    renderDeals();
  });
  document.querySelector(".view-tabs").addEventListener("click", (e) => {
    const tab = e.target.closest(".view-tab");
    if (!tab) return;
    document.querySelectorAll(".view-tab").forEach((t) => t.setAttribute("aria-pressed", String(t === tab)));
    document.querySelector(".layout").dataset.view = tab.dataset.view;
    window.scrollTo({ top: 0 });
  });
}

async function load() {
  try {
    const res = await fetch(`news.json?t=${Date.now()}`, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    state.data = await res.json();
    state.data.news ||= [];
    state.data.deals ||= [];
    render();
  } catch {
    $("status").textContent = "データを読み込めませんでした。少し待ってから再読み込みしてください。";
    $("status").classList.add("is-stale");
  }
}

bindEvents();
load();
// 開きっぱなしでも「◯分前」がずれないように1分ごとに表示を更新する
setInterval(() => { if (state.data) renderStatus(); }, 60000);
