import json
import urllib.request
import datetime

# 1. ニュース記事の取得（既存処理）
def fetch_articles():
    # 既存のニュース取得ロジック
    return [
        {
            "id": "1",
            "title": "最新ゲームニュースタイトル",
            "link": "https://example.com",
            "source": "ファミ通",
            "category": "jp",
            "category_name": "🇯🇵 国内速報",
            "pubDate": "2026-09-29 12:00"
        }
    ]

# 2. 注目・期待の新作ゲームデータの自動生成／取得
def fetch_upcoming_games():
    # ※API経由での取得や、更新頻度に応じた動的なデータ管理
    # ここではSteam/IGDB等のAPIデータ構造に合わせた例を返します
    return [
        {
            "id": "gta6",
            "title": "Grand Theft Auto VI",
            "targetDate": "2026-11-15",
            "dateText": "2026年11月予定",
            "platforms": ["PS5", "Xbox Series"],
            "color": "from-fuchsia-500/20 to-pink-500/10",
            "youtubeId": "QdBZY2fkU-0",
            "links": [{"name": "公式サイト", "url": "https://www.rockstargames.com/VI"}]
        },
        {
            "id": "metroid_prime4",
            "title": "メトロイドプライム4 ビヨンド",
            "targetDate": "2027-01-28",
            "dateText": "2027年1月28日",
            "platforms": ["Switch 2", "Switch"],
            "color": "from-rose-500/20 to-red-500/10",
            "youtubeId": "71RNwDklYjk",
            "links": [{"name": "任天堂公式", "url": "https://www.nintendo.co.jp/"}]
        },
        {
            "id": "pokemon_za",
            "title": "Pokémon LEGENDS Z-A",
            "targetDate": "2027-11-18",
            "dateText": "2027年秋予定",
            "platforms": ["Switch 2", "Switch"],
            "color": "from-emerald-500/20 to-teal-500/10",
            "youtubeId": "5sBJq0WlixM",
            "links": [{"name": "ポケモン公式", "url": "https://www.pokemon.co.jp/ex/pokemon_legends_z-a/"}]
        }
    ]

def main():
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    data = {
        "updated_at": now_str,
        "upcoming_games": fetch_upcoming_games(),
        "articles": fetch_articles()
    }
    
    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[{now_str}] news.json successfully updated.")

if __name__ == "__main__":
    main()
