import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import json
import re
from datetime import datetime

# 全15メディアの超豪華ソースリスト
FEEDS = [
    # 🎮 公式プラットフォーム速報
    {"url": "https://blog.ja.playstation.com/feed/", "source": "PS Blog", "category": "hardware", "category_name": "🎮 PS公式"},
    {"url": "https://news.xbox.com/ja-jp/feed/", "source": "Xbox Wire", "category": "hardware", "category_name": "🎮 Xbox公式"},

    # 🇯🇵 国内大手・総合ニュース
    {"url": "https://www.famitsu.com/rss/famitsu-all.xml", "source": "ファミ通", "category": "jp", "category_name": "🇯🇵 国内速報"},
    {"url": "https://jp.ign.com/feed/news", "source": "IGN Japan", "category": "jp", "category_name": "🇯🇵 国内速報"},
    {"url": "https://www.4gamer.net/rss/index.xml", "source": "4Gamer", "category": "jp", "category_name": "🇯🇵 国内速報"},
    {"url": "https://dengekionline.com/rss/index.xml", "source": "電撃オンライン", "category": "jp", "category_name": "🇯🇵 国内速報"},
    {"url": "https://www.gamer.ne.jp/rss/news/", "source": "Gamer", "category": "jp", "category_name": "🇯🇵 国内速報"},
    
    # 🇯🇵 カルチャー・インディー・業界
    {"url": "https://news.denfaminicogamer.jp/feed", "source": "電ファミ", "category": "jp", "category_name": "🇯🇵 電ファミ・話題"},
    {"url": "https://automaton-media.com/feed/", "source": "AUTOMATON", "category": "jp", "category_name": "🇯🇵 インディー・話題"},
    {"url": "https://gamebiz.jp/rss/all.xml", "source": "gamebiz", "category": "jp", "category_name": "📱 スマホ・業界"},
    
    # 💻 ハードウェア & Core PC
    {"url": "https://www.gamespark.jp/rss/index.rdf", "source": "Game*Spark", "category": "hardware", "category_name": "💻 CorePC・ハード"},

    # 🌐 海外トレンド & 速報（自動日本語翻訳）
    {"url": "https://www.gematsu.com/feed", "source": "Gematsu", "category": "global", "category_name": "🌐 海外速報"},
    {"url": "https://www.pcgamer.com/rss/", "source": "PC Gamer", "category": "global", "category_name": "🌐 海外トレンド"},
    {"url": "https://kotaku.com/rss", "source": "Kotaku", "category": "global", "category_name": "🌐 海外トレンド"},
    {"url": "https://www.eurogamer.net/feed", "source": "Eurogamer", "category": "global", "category_name": "🌐 海外トレンド"},
]

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
        res = urllib.request.urlopen(req, timeout=6).read().decode('utf-8')
        result = json.loads(res)
        translated = "".join([sentence[0] for sentence[0] in result[0] if sentence[0]])
        return translated if translated else text
    except Exception:
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
            
            # 各メディア最新3〜4件を取得して均等に表示
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
                
                # 海外ソース（Gematsu, PC Gamer, Kotaku, Eurogamer）は自動日本語翻訳
                if feed["category"] == "global" or re.search(r'[a-zA-Z]{5,}', title):
                    title = translate_to_japanese(title)
                    if summary:
                        summary = translate_to_japanese(summary)

                cat = feed["category"]
                cat_name = feed["category_name"]
                title_lower = title.lower()
                
                # セールやハード関連のキーワードがあれば動的にタグ変更
                if any(k in title_lower for k in ["セール", "無料", "割引", "discount", "sale", "epic", "steam", "100%", "bundle", "game pass"]):
                    cat = "sale"
                    cat_name = "🔥 セール・お得"
                elif any(k in title_lower for k in ["ps5", "switch", "steam deck", "gpu", "rtx", "グラボ", "モニター", "コントローラー", "xbox", "ハード", "新型"]):
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
            
    # タイトル重複チェック
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
