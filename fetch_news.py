import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import json
import re
from datetime import datetime, timezone, timedelta

FEEDS = [
    {"url": "https://topics.nintendo.co.jp/feed/rss/index.xml", "source": "任天堂", "category": "hardware", "category_name": "🎮 任天堂公式"},
    {"url": "https://blog.ja.playstation.com/feed/", "source": "PS Blog", "category": "hardware", "category_name": "🎮 PS公式"},
    {"url": "https://news.xbox.com/ja-jp/feed/", "source": "Xbox Wire", "category": "hardware", "category_name": "🎮 Xbox公式"},
    {"url": "https://www.famitsu.com/rss/famitsu-all.xml", "source": "ファミ通", "category": "jp", "category_name": "🇯🇵 国内速報"},
    {"url": "https://jp.ign.com/feed/news", "source": "IGN Japan", "category": "jp", "category_name": "🇯🇵 国内速報"},
    {"url": "https://www.4gamer.net/rss/index.xml", "source": "4Gamer", "category": "jp", "category_name": "🇯🇵 国内速報"},
    {"url": "https://dengekionline.com/rss/index.xml", "source": "電撃オンライン", "category": "jp", "category_name": "🇯🇵 国内速報"},
    {"url": "https://www.gamer.ne.jp/rss/news/", "source": "Gamer", "category": "jp", "category_name": "🇯🇵 国内速報"},
    {"url": "https://news.denfaminicogamer.jp/feed", "source": "電ファミ", "category": "jp", "category_name": "🇯🇵 電ファミ・話題"},
    {"url": "https://automaton-media.com/feed/", "source": "AUTOMATON", "category": "jp", "category_name": "🇯🇵 インディー・話題"},
    {"url": "https://gamebiz.jp/rss/all.xml", "source": "gamebiz", "category": "jp", "category_name": "📱 スマホ・業界"},
    {"url": "https://www.gamespark.jp/rss/index.rdf", "source": "Game*Spark", "category": "hardware", "category_name": "💻 CorePC・ハード"},
    {"url": "https://www.gematsu.com/feed", "source": "Gematsu", "category": "global", "category_name": "🌐 海外速報"},
    {"url": "https://www.pcgamer.com/rss/", "source": "PC Gamer", "category": "global", "category_name": "🌐 海外トレンド"},
    {"url": "https://kotaku.com/rss", "source": "Kotaku", "category": "global", "category_name": "🌐 海外トレンド"},
    {"url": "https://www.eurogamer.net/feed", "source": "Eurogamer", "category": "global", "category_name": "🌐 海外トレンド"},
]

PLATFORM_KEYWORDS = {
    "Switch": ["switch", "スイッチ", "nintendo switch", "任天堂"],
    "PS5": ["ps5", "playstation 5", "プレイステーション5"],
    "PS4": ["ps4", "playstation 4"],
    "PC": ["pc", "steam", "epic games", "rtx", "gpu", "ゲーミングpc", "pc gamer"],
    "Xbox": ["xbox", "series x", "series s", "game pass"]
}

def detect_platforms(text, default_platform=None):
    text_lower = text.lower()
    detected = set()
    
    if default_platform:
        detected.add(default_platform)
        
    for platform, keywords in PLATFORM_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            detected.add(platform)
            
    return list(detected) if detected else ["ALL"]

def clean_html(text):
    if not text: return ""
    clean = re.sub('<.*?>', '', text)
    return clean.strip()[:140] + "..."

def translate_to_japanese(text):
    if not text or len(text.strip()) == 0:
        return text
    try:
        url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=ja&dt=t&q=" + urllib.parse.quote(text)
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        res = urllib.request.urlopen(req, timeout=4).read().decode('utf-8')
        result = json.loads(res)
        translated = "".join([sentence[0] for sentence[0] in result[0] if sentence[0]])
        return translated if translated else text
    except Exception:
        return text

def fetch_epic_store():
    epic_items = []
    try:
        url = "https://store-site-backend-static-ipv4.akamaized.net/store/ffi/offers/v1/japan?locale=ja&country=JP&allowCountries=JP"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        res = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')
        data = json.loads(res)
        elements = data.get('data', {}).get('Catalog', {}).get('searchStore', {}).get('elements', [])

        now = datetime.now(timezone.utc)

        for el in elements:
            title = el.get('title')
            promotions = el.get('promotions')
            price_info = el.get('price', {}).get('totalPrice', {})
            
            image_url = None
            for img in el.get('keyImages', []):
                if img.get('type') in ['OfferImageWide', 'DieselStoreFrontWide', 'Thumbnail']:
                    image_url = img.get('url')
                    break
            if not image_url and el.get('keyImages'):
                image_url = el['keyImages'][0].get('url')

            product_slug = el.get('productSlug') or (el.get('catalogNs', {}).get('mappings', [{}])[0].get('pageSlug') if el.get('catalogNs') else None)
            link = f"https://store.epicgames.com/ja/p/{product_slug}" if product_slug else "https://store.epicgames.com/ja/"

            is_free = False
            discount_price = price_info.get('discountPrice', 0)
            original_price = price_info.get('originalPrice', 0)
            end_date_str = ""

            if promotions and promotions.get('promotionalOffers'):
                for group in promotions['promotionalOffers']:
                    for offer in group.get('promotionalOffers', []):
                        start = offer.get('startDate')
                        end = offer.get('endDate')
                        if start and end:
                            s_date = datetime.fromisoformat(start.replace('Z', '+00:00'))
                            e_date = datetime.fromisoformat(end.replace('Z', '+00:00'))
                            if s_date <= now <= e_date:
                                jst_end = e_date.astimezone(timezone(timedelta(hours=9)))
                                end_date_str = jst_end.strftime("%m/%d %H:%Mまで")
                                if offer.get('discountSetting', {}).get('discountPercentage') == 0 or discount_price == 0:
                                    is_free = True

            if is_free:
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
            elif original_price > 0 and discount_price < original_price:
                discount_rate = int((1 - discount_price / original_price) * 100)
                epic_items.append({
                    "id": f"epic_sale_{hash(title)}",
                    "title": title,
                    "link": link,
                    "summary": f"【セール中】¥{original_price:,} ➔ ¥{discount_price:,}",
                    "source": "Epic Games Store",
                    "category": "epic_sale",
                    "category_name": "🏷️ Epicセール",
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
        url = "https://store.steampowered.com/api/featuredcategories/?cc=jp&l=japanese"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        res = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')
        data = json.loads(res)
        
        specials = data.get('specials', {}).get('items', [])
        
        for item in specials:
            if not item.get('discount_expiration'):
                continue
            
            exp_time = item.get('discount_expiration')
            now_ts = int(datetime.now().timestamp())
            
            if exp_time > now_ts:
                title = item.get('name')
                app_id = item.get('id')
                link = f"https://store.steampowered.com/app/{app_id}/"
                image_url = item.get('header_image') or item.get('large_capsule_image')
                
                discount_percent = item.get('discount_percent', 0)
                orig_price = item.get('original_price', 0) // 100
                final_price = item.get('final_price', 0) // 100
                
                exp_dt = datetime.fromtimestamp(exp_time, tz=timezone(timedelta(hours=9)))
                expire_str = exp_dt.strftime("%m/%d %H:%Mまで")

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
                    "expire": expire_str,
                    "pubDate": datetime.now().strftime("%m/%d %H:%M")
                })
    except Exception as e:
        print(f"Error fetching Steam Store: {e}")
        
    return steam_items

def fetch_rss():
    news_articles = []
    sale_articles = []
    
    sale_articles.extend(fetch_epic_store())
    sale_articles.extend(fetch_steam_sales())
    
    for feed in FEEDS:
        try:
            req = urllib.request.Request(
                feed["url"], 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            xml_data = urllib.request.urlopen(req, timeout=10).read()
            
            try:
                root = ET.fromstring(xml_data)
            except ET.ParseError:
                continue
            
            items = (
                root.findall('.//item') or 
                root.findall('.//{http://www.w3.org/2005/Atom}entry') or
                root.findall('.//{http://purl.org/rss/1.0/}item')
            )
            
            # ソースごとの固定プラットフォーム（公式ブログ等）
            default_platform = None
            if feed["source"] == "任天堂": default_platform = "Switch"
            elif feed["source"] == "PS Blog": default_platform = "PS5"
            elif feed["source"] == "Xbox Wire": default_platform = "Xbox"

            for item in items[:4]:
                title = (
                    item.findtext('title') or 
                    item.findtext('{http://www.w3.org/2005/Atom}title')
                )
                link = (
                    item.findtext('link') or 
                    item.findtext('{http://www.w3.org/2005/Atom}href')
                )
                desc = (
                    item.findtext('description') or 
                    item.findtext('{http://www.w3.org/2005/Atom}summary') or ""
                )
                
                if not title or not link: continue
                
                title = title.strip()
                summary = clean_html(desc)
                
                if feed["category"] == "global" or re.search(r'[a-zA-Z]{5,}', title):
                    title = translate_to_japanese(title)
                    if summary:
                        summary = translate_to_japanese(summary)

                cat = feed["category"]
                cat_name = feed["category_name"]
                title_lower = title.lower()
                
                is_sale_article = False
                badge = ""
                if any(k in title_lower for k in ["セール", "無料", "割引", "discount", "sale", "epic", "steam", "100%", "bundle", "game pass"]):
                    cat = "sale"
                    cat_name = "🔥 セール速報"
                    is_sale_article = True
                    badge = "SALE"
                elif any(k in title_lower for k in ["ps5", "switch", "steam deck", "gpu", "rtx", "グラボ", "モニター", "コントローラー", "xbox", "ハード", "新型"]):
                    cat = "hardware"
                    cat_name = "💻 ハード・機器"

                # プラットフォーム判定
                platforms = detect_platforms(f"{title} {summary}", default_platform)

                article = {
                    "id": f"rss_{hash(title)}",
                    "title": title,
                    "link": link.strip(),
                    "summary": summary,
                    "source": feed["source"],
                    "category": cat,
                    "category_name": cat_name,
                    "platforms": platforms,
                    "badge": badge,
                    "expire": "",
                    "pubDate": datetime.now().strftime("%m/%d %H:%M")
                }

                if is_sale_article:
                    sale_articles.append(article)
                else:
                    news_articles.append(article)
        except Exception as e:
            print(f"Error fetching {feed['source']}: {e}")
            
    unique_articles = []
    seen_titles = set()
    
    all_combined = news_articles + sale_articles
    
    for art in all_combined:
        if art["title"] not in seen_titles:
            seen_titles.add(art["title"])
            unique_articles.append(art)

    data = {
        "updated_at": datetime.now(timezone(timedelta(hours=9))).strftime("%Y/%m/%d %H:%M"),
        "articles": unique_articles
    }
    
    with open('news.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    fetch_rss()
