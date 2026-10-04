import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import json
import re
import os
from datetime import datetime, timezone, timedelta

# ==========================================
# 1. 取得元フィード & 設定
# ==========================================
FEEDS = [
    # --- 国内ニュース ---
    {"url": "https://www.famitsu.com/rss/famitsu.xml", "source": "ファミ通", "category": "jp"},
    {"url": "https://www.4gamer.net/rss/index.xml", "source": "4Gamer", "category": "jp"},
    {"url": "https://jp.ign.com/feed.xml", "source": "IGN Japan", "category": "jp"},
    {"url": "https://dengekionline.com/rss/dengeki.xml", "source": "電撃オンライン", "category": "jp"},
    {"url": "https://www.gamer.ne.jp/rss/news.xml", "source": "Gamer", "category": "jp"},
    {"url": "https://news.denfaminicogamer.jp/feed", "source": "電ファミニコゲーマー", "category": "jp"},
    {"url": "https://automaton-media.com/feed/", "source": "AUTOMATON", "category": "jp"},
    {"url": "https://gamebiz.jp/rss/all.xml", "source": "gamebiz", "category": "jp"},

    # --- ハード公式 / 専門誌 ---
    {"url": "https://topics.nintendo.co.jp/rss/index.xml", "source": "任天堂公式", "category": "jp", "default_platform": "Switch"},
    {"url": "https://blog.ja.playstation.com/feed/", "source": "PlayStation Blog", "category": "jp", "default_platform": "PS5"},
    {"url": "https://news.xbox.com/ja-jp/feed/", "source": "Xbox Wire Japan", "category": "jp", "default_platform": "Xbox"},
    {"url": "https://www.gamespark.jp/rss/index.xml", "source": "Game*Spark", "category": "jp"},

    # --- 海外ニュース (自動翻訳対象) ---
    {"url": "https://www.gematsu.com/feed", "source": "Gematsu", "category": "global"},
    {"url": "https://www.pcgamer.com/rss/", "source": "PC Gamer", "category": "global"},
    {"url": "https://kotaku.com/rss", "source": "Kotaku", "category": "global"},
    {"url": "https://www.eurogamer.net/feed", "source": "Eurogamer", "category": "global"}
]

PLATFORM_KEYWORDS = {
    "Switch": ["switch", "スイッチ", "任天堂", "nintendo"],
    "PS5": ["ps5", "playstation 5", "プレイステーション5"],
    "PS4": ["ps4", "playstation 4", "プレイステーション4"],
    "PC": ["pc", "steam", "epic", "rtx", "windows"],
    "Xbox": ["xbox", "game pass", "ゲームパス"]
}

# ==========================================
# 2. ユーティリティ関数
# ==========================================
def clean_html(raw_html):
    if not raw_html:
        return ""
    cleaner = re.compile('<.*?>')
    cleaned = re.sub(cleaner, '', raw_html)
    return cleaned.replace('\n', ' ').strip()

def translate_to_japanese(text):
    if not text:
        return text
    if re.search(r'[a-zA-Z]{5,}', text):
        try:
            url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=ja&dt=t&q={urllib.parse.quote(text)}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            res = urllib.request.urlopen(req, timeout=4).read().decode('utf-8')
            data = json.loads(res)
            return "".join([item[0] for item in data[0] if item[0]])
        except Exception:
            return text
    return text

def detect_platforms(text, default_platform=None):
    platforms = set()
    if default_platform:
        platforms.add(default_platform)
    text_lower = text.lower()
    for platform, keywords in PLATFORM_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            platforms.add(platform)
    return list(platforms) if platforms else ["ALL"]

# ==========================================
# 3. ストアAPI取得処理 (Epic / Steam)
# ==========================================
def fetch_epic_store():
    epic_items = []
    try:
        # Epic Store GraphQL API (セール対象含め確実に取得するためのパラメータ設定)
        url = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions?locale=ja&country=JP&allowCountries=JP"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        res = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')
        data = json.loads(res)
        
        elements = data.get('data', {}).get('Catalog', {}).get('searchStore', {}).get('elements', [])
        now = datetime.now(timezone.utc)

        for el in elements:
            title = el.get('title')
            price_info = el.get('price', {}).get('totalPrice', {})
            promotions = el.get('promotions') or {}
            
            if not title or not price_info:
                continue

            discount_price = price_info.get('discountPrice', 0)
            original_price = price_info.get('originalPrice', 0)
            
            # 画像取得
            image_url = None
            for img in el.get('keyImages', []):
                if img.get('type') in ['OfferImageWide', 'DieselStoreFrontWide', 'VaultClosed', 'Thumbnail', 'OfferImageTall']:
                    image_url = img.get('url')
                    break
            if not image_url and el.get('keyImages'):
                image_url = el['keyImages'][0].get('url')

            # URL設定
            product_slug = el.get('productSlug')
            if not product_slug and el.get('offerMappings'):
                product_slug = el['offerMappings'][0].get('pageSlug')
            if not product_slug and el.get('catalogNs', {}).get('mappings'):
                product_slug = el['catalogNs']['mappings'][0].get('pageSlug')

            link = f"https://store.epicgames.com/ja/p/{product_slug}" if product_slug else "https://store.epicgames.com/ja/browse?sortBy=releaseDate&sortDir=DESC&priceTier=tierDiscounts"

            is_free = False
            end_date_str = ""

            # プロモーション（無料配布）判定
            promotional_offers = promotions.get('promotionalOffers', [])
            if promotional_offers:
                for group in promotional_offers:
                    for offer in group.get('promotionalOffers', []):
                        start = offer.get('startDate')
                        end = offer.get('endDate')
                        if start and end:
                            s_date = datetime.fromisoformat(start.replace('Z', '+00:00'))
                            e_date = datetime.fromisoformat(end.replace('Z', '+00:00'))
                            
                            if s_date <= now <= e_date:
                                jst_end = e_date.astimezone(timezone(timedelta(hours=9)))
                                end_date_str = jst_end.strftime("%m/%d %H:%Mまで")
                                
                                discount_setting = offer.get('discountSetting', {})
                                if discount_setting.get('discountPercentage') == 0 or discount_price == 0:
                                    is_free = True

            # 1. 無料配布中
            if is_free or (discount_price == 0 and original_price > 0):
                epic_items.append({
                    "id": f"epic_free_{hash(title)}",
                    "title": title,
                    "link": link,
                    "summary": f"【Epic Gamesストア 無料配布中】通常価格 ¥{original_price:,} ➔ 無料！",
                    "source": "Epic Games Store",
                    "category": "epic_free",
                    "category_name": "🎁 Epic無料配布",
                    "platforms": ["PC"],
                    "image": image_url,
                    "badge": "FREE",
                    "expire": end_date_str,
                    "pubDate": datetime.now().strftime("%m/%d %H:%M")
                })
            # 2. 通常セール・季節限定セール中
            elif original_price > 0 and discount_price < original_price:
                discount_rate = int((1 - discount_price / original_price) * 100)
                epic_items.append({
                    "id": f"epic_sale_{hash(title)}",
                    "title": title,
                    "link": link,
                    "summary": f"【セール中】¥{original_price:,} ➔ ¥{discount_price:,}",
                    "source": "Epic Games Store",
                    "category": "epic_sale",
                    "category_name": "🏷 Epicセール",
                    "platforms": ["PC"],
                    "image": image_url,
                    "badge": f"-{discount_rate}%",
                    "expire": end_date_str,
                    "pubDate": datetime.now().strftime("%m/%d %H:%M")
                })
    except Exception as e:
        print(f"Error fetching Epic Games Store: {e}")
        
    return epic_items


def fetch_steam_sales():
    steam_items = []
    try:
        # Steam Store API (セール中タイトルを網羅的に検索取得)
        url = "https://store.steampowered.com/api/storesearch/?term=&campaign=specials&cc=jp&l=japanese&count=50"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        res = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')
        data = json.loads(res)
        
        items = data.get('items', [])
        
        for item in items:
            title = item.get('name')
            app_id = item.get('id')
            price_info = item.get('price', {})
            
            if not title or not app_id or not price_info:
                continue
                
            orig_price = price_info.get('initial', 0) // 100
            final_price = price_info.get('final', 0) // 100
            discount_percent = price_info.get('discount_percent', 0)
            
            if discount_percent > 0 and final_price < orig_price:
                link = f"https://store.steampowered.com/app/{app_id}/"
                image_url = item.get('tiny_image', '').replace("capsule_sm_120.jpg", "header.jpg")
                
                steam_items.append({
                    "id": f"steam_{app_id}",
                    "title": title,
                    "link": link,
                    "summary": f"【Steamセール中】¥{orig_price:,} ➔ ¥{final_price:,}",
                    "source": "Steam Store",
                    "category": "steam_sale",
                    "category_name": "🎮 Steamセール",
                    "platforms": ["PC"],
                    "image": image_url,
                    "badge": f"-{discount_percent}%",
                    "expire": "セール期間中",
                    "pubDate": datetime.now().strftime("%m/%d %H:%M")
                })
    except Exception as e:
        print(f"Error fetching Steam Store: {e}")
        
    return steam_items


# ==========================================
# 4. メディアRSS取得処理
# ==========================================
def fetch_rss_feeds():
    rss_items = []
    for feed in FEEDS:
        try:
            req = urllib.request.Request(feed['url'], headers={'User-Agent': 'Mozilla/5.0'})
            xml_data = urllib.request.urlopen(req, timeout=10).read()
            root = ET.fromstring(xml_data)

            items = root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')

            for item in items[:10]:
                title_elem = item.find('title') or item.find('{http://www.w3.org/2005/Atom}title')
                link_elem = item.find('link') or item.find('{http://www.w3.org/2005/Atom}link')
                summary_elem = item.find('description') or item.find('{http://www.w3.org/2005/Atom}summary')

                if title_elem is None:
                    continue

                raw_title = title_elem.text or ""
                link = link_elem.text if link_elem is not None and link_elem.text else ""
                if not link and link_elem is not None:
                    link = link_elem.attrib.get('href', '')

                summary = clean_html(summary_elem.text if summary_elem is not None else "")[:120]
                translated_title = translate_to_japanese(raw_title) if feed['category'] == 'global' else raw_title
                
                cat_type = feed['category']
                cat_name = "📰 国内速報" if cat_type == "jp" else "🌐 海外ニュース"
                badge = None

                if any(kw in translated_title.lower() for kw in ['セール', '割引', '無料', 'sale', 'discount']):
                    cat_type = "sale"
                    cat_name = "🔥 セール速報"
                    badge = "SALE"

                platforms = detect_platforms(translated_title + " " + summary, feed.get('default_platform'))

                rss_items.append({
                    "id": f"rss_{hash(translated_title)}",
                    "title": translated_title,
                    "link": link,
                    "summary": summary,
                    "source": feed['source'],
                    "category": cat_type,
                    "category_name": cat_name,
                    "platforms": platforms,
                    "badge": badge,
                    "pubDate": datetime.now().strftime("%m/%d %H:%M")
                })
        except Exception as e:
            print(f"Error fetching RSS {feed['source']}: {e}")
            continue
            
    return rss_items


# ==========================================
# 5. メイン実行処理
# ==========================================
def main():
    print("Starting news fetch pipeline...")
    all_articles = []

    all_articles.extend(fetch_epic_store())
    all_articles.extend(fetch_steam_sales())
    all_articles.extend(fetch_rss_feeds())

    unique_articles = []
    seen_titles = set()
    for art in all_articles:
        if art['title'] not in seen_titles:
            seen_titles.add(art['title'])
            unique_articles.append(art)

    jst_now = datetime.now(timezone(timedelta(hours=9)))
    output_data = {
        "updated_at": jst_now.strftime("%Y/%m/%d %H:%M"),
        "articles": unique_articles
    }

    # カレントディレクトリ（プロジェクトルート）に news.json を出力
    output_path = os.path.join(os.getcwd(), "news.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"Successfully output {len(unique_articles)} articles to {output_path}")

if __name__ == "__main__":
    main()
