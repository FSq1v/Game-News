import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import json
import re
from datetime import datetime

# 安定して取得できる主要メディア一覧
FEEDS = [
    # 🇯🇵 国内ゲームメディア
    {"url": "https://www.famitsu.com/rss/famitsu-all.xml", "source": "ファミ通", "category": "jp", "category_name": "🇯🇵 国内速報"},
    {"url": "https://jp.ign.com/feed/news", "source": "IGN Japan", "category": "jp", "category_name": "🇯🇵 国内速報"},
    {"url": "https://automaton-media.com/feed/", "source": "AUTOMATON", "category": "jp", "category_name": "🇯🇵 国内・インディー"},
    {"url": "https://www.4gamer.net/rss/index.xml", "source": "4Gamer", "category": "jp", "category_name": "🇯🇵 国内速報"},
    {"url": "https://www.gamespark.jp/rss/index.rdf", "source": "Game*Spark", "category": "hardware", "category_name": "💻 CorePC・ハード"},

    # 🌐 海外人気トレンドメディア（自動で日本語翻訳します）
    {"url": "https://www.pcgamer.com/rss/", "source": "PC Gamer (海外)", "category": "global", "category_name": "🌐 海外トレンド"},
    {"url": "https://kotaku.com/rss", "source": "Kotaku (海外)", "category": "global", "category_name": "🌐 海外トレンド"},
]

def clean_html(text):
    if not text: return ""
    clean = re.sub('<.*?>', '', text)
    return clean.strip()[:140] + "..."

# 簡易的な自動日本語翻訳（Google翻訳API）
def translate_to_japanese(text):
    if not text or len(text.strip()) == 0: return text
    try:
        url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=ja&dt=t&q=" + urllib.parse.quote(text)
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        res = urllib.request.urlopen(req, timeout=5).read().decode('utf-8')
        result = json.loads(res)
        translated = "".join([sentence[0] for sentence[0] in result[0] if sentence[0]])
        return translated
    except Exception as e:
        return text

def fetch_rss():
    articles = []
    
    for feed in FEEDS:
        try:
            req = urllib.request.Request(
                feed["url"], 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            xml_data = urllib.request.urlopen(req, timeout=12).read()
            root = ET.fromstring(xml_data)
            
            items = (
                root.findall('.//item') or 
                root.findall('.//{http://www.w3.org/2005/Atom}entry') or
                root.findall('.//{http://purl.org/rss/1.0/}item')
            )
            
            for item in items[:5]:
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
                
                # 海外ソースの場合、タイトルと概要を自動で日本語化
                if feed["category"] == "global":
                    title = translate_to_japanese(title)
                    summary = translate_to_japanese(summary)

                # カテゴリの自動判定
                cat = feed["category"]
                cat_name = feed["category_name"]
                title_lower = title.lower()
                
                if any(k in title_lower for k in ["セール", "無料", "割引", "discount", "sale", "epic", "steam", "100%", "bundle"]):
                    cat = "sale"
                    cat_name = "🔥 セール・お得"
                elif any(k in title_lower for k in ["ps5", "switch", "steam deck", "gpu", "rtx", "グラボ", "モニター", "コントローラー", "xbox", "ハード"]):
                    cat = "hardware"
                    cat_name = "💻 ハード・機器"

                articles.append({
                    "title": title,
                    "link": link.strip(),
                    "summary": summary,
                    "source": feed["source"],
                    "category": cat,
                    "category_name": cat_name,
                    "pubDate": datetime.now().strftime("%m/%d %H:%M")
                })
        except Exception as e:
            print(f"Error fetching {feed['source']}: {e}")
            
    # 重複記事の排除
    unique_articles = []
    seen_titles = set()
    for art in articles:
        if art["title"] not in seen_titles:
            seen_titles.add(art["title"])
            unique_articles.append(art)

    data = {
        "updated_at": datetime.now().strftime("%Y/%m/%d %H:%M"),
        "articles": unique_articles
    }
    
    with open('news.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    fetch_rss()
