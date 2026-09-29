import urllib.request
import xml.etree.ElementTree as ET
import json
import re
from datetime import datetime

# 大幅強化：国内外の有名ゲームメディア＆トレンド情報源
FEEDS = [
    # --- 🇯🇵 国内大手・速報メディア ---
    {"url": "https://www.famitsu.com/rss/famitsu-all.xml", "source": "ファミ通", "category": "jp", "category_name": "🇯🇵 国内速報"},
    {"url": "https://jp.ign.com/feed/news", "source": "IGN Japan", "category": "jp", "category_name": "🇯🇵 国内速報"},
    {"url": "https://automaton-media.com/feed/", "source": "AUTOMATON", "category": "jp", "category_name": "🇯🇵 国内・インディー"},
    {"url": "https://www.4gamer.net/rss/index.xml", "source": "4Gamer", "category": "jp", "category_name": "🇯🇵 国内速報"},
    {"url": "https://dengekionline.com/rss/index.xml", "source": "電撃オンライン", "category": "jp", "category_name": "🇯🇵 国内速報"},
    {"url": "https://gamebiz.jp/rss/all.xml", "source": "gamebiz", "category": "jp", "category_name": "📱 スマホ・業界"},

    # --- 💻 ハードウェア & Core PC ---
    {"url": "https://www.gamespark.jp/rss/index.rdf", "source": "Game*Spark", "category": "hardware", "category_name": "💻 CorePC・ハード"},

    # --- 🔥 海外トレンド & Steam / Epic / セール ---
    {"url": "https://www.pcgamer.com/rss/", "source": "PC Gamer (海外)", "category": "global", "category_name": "🌐 Steam・PC"},
    {"url": "https://www.eurogamer.net/feed", "source": "Eurogamer (海外)", "category": "global", "category_name": "🌐 海外トレンド"},
    {"url": "https://kotaku.com/rss", "source": "Kotaku (海外)", "category": "global", "category_name": "🌐 海外トレンド"},
]

def clean_html(text):
    if not text: return ""
    clean = re.sub('<.*?>', '', text)
    return clean.strip()[:140] + "..."

def fetch_rss():
    articles = []
    
    for feed in FEEDS:
        try:
            # 拒否されないようUser-Agentを設定
            req = urllib.request.Request(
                feed["url"], 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            xml_data = urllib.request.urlopen(req, timeout=12).read()
            root = ET.fromstring(xml_data)
            
            # RSS 2.0, Atom, RDF 形式に対応
            items = (
                root.findall('.//item') or 
                root.findall('.//{http://www.w3.org/2005/Atom}entry') or
                root.findall('.//{http://purl.org/rss/1.0/}item')
            )
            
            for item in items[:5]: # 各メディア最新5件を取得
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
                
                # 自動カテゴリ判定（タイトル内のキーワードから動的に「セール」「ハード」に振り分け）
                cat = feed["category"]
                cat_name = feed["category_name"]
                
                title_lower = title.lower()
                # セール・無料配布判定
                if any(k in title_lower for k in ["セール", "無料配布", "割引", "discount", "sale", "epic games", "steam", "100% off", "bundle"]):
                    cat = "sale"
                    cat_name = "🔥 セール・お得"
                # ハードウェア・ガジェット判定
                elif any(k in title_lower for k in ["ps5", "switch", "steam deck", "gpu", "rtx", "グラボ", "モニター", "コントローラー", "xbox", "ハード"]):
                    cat = "hardware"
                    cat_name = "💻 ハード・機器"

                articles.append({
                    "title": title.strip(),
                    "link": link.strip(),
                    "summary": clean_html(desc),
                    "source": feed["source"],
                    "category": cat,
                    "category_name": cat_name,
                    "pubDate": datetime.now().strftime("%m/%d %H:%M")
                })
        except Exception as e:
            print(f"Error fetching {feed['source']}: {e}")
            
    # 重複記事の排除（タイトルが同じものをカット）
    unique_articles = []
    seen_titles = set()
    for art in articles:
        if art["title"] not in seen_titles:
            seen_titles.add(art["title"])
            unique_articles.append(art)

    # 保存データ作成
    data = {
        "updated_at": datetime.now().strftime("%Y/%m/%d %H:%M"),
        "articles": unique_articles
    }
    
    with open('news.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    fetch_rss()
