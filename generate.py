import feedparser
import anthropic
import os
import json
import urllib.request
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

RSS_FEEDS = {
    "ニュース": ["https://feeds.bbci.co.uk/japanese/rss.xml"],
    "テクノロジー": ["https://techcrunch.com/feed/"],
    "スポーツ": ["https://sportsnavi.ht.kyodo-d.jp/sports/rss/all.xml"],
    "エンタメ": ["https://natalie.mu/music/feed/news"],
    "ゲーム": ["https://automaton-media.com/feed/"],
    "アニメ": ["https://animeanime.jp/rss/index.rdf"],
    "経済": ["https://feeds.bbci.co.uk/japanese/business/rss.xml"],
    "国際": ["https://feeds.bbci.co.uk/japanese/world/rss.xml"],
}

AREAS = {
    "北海道・東北": {
        "北海道": "016000", "青森": "020000", "岩手": "030000",
        "宮城": "040000", "秋田": "050000", "山形": "060000", "福島": "070000"
    },
    "関東": {
        "茨城": "080000", "栃木": "090000", "群馬": "100000",
        "埼玉": "110000", "千葉": "120000", "東京": "130000",
        "神奈川": "140000"
    },
    "中部": {
        "新潟": "150000", "富山": "160000", "石川": "170000",
        "福井": "180000", "山梨": "190000", "長野": "200000",
        "岐阜": "210000", "静岡": "220000", "愛知": "230000"
    },
    "近畿": {
        "三重": "240000", "滋賀": "250000", "京都": "260000",
        "大阪": "270000", "兵庫": "280000", "奈良": "290000", "和歌山": "300000"
    },
    "中国・四国": {
        "鳥取": "310000", "島根": "320000", "岡山": "330000",
        "広島": "340000", "山口": "350000", "徳島": "360000",
        "香川": "370000", "愛媛": "380000", "高知": "390000"
    },
    "九州・沖縄": {
        "福岡": "400000", "佐賀": "410000", "長崎": "420000",
        "熊本": "430000", "大分": "440000", "宮崎": "450000",
        "鹿児島": "460100", "沖縄": "471000"
    }
}

WEATHER_ICONS = {
    "晴": "☀️", "晴れ": "☀️", "快晴": "☀️",
    "曇": "⛅", "曇り": "⛅", "くもり": "⛅",
    "雨": "🌧️", "小雨": "🌦️", "大雨": "⛈️",
    "雪": "❄️", "みぞれ": "🌨️",
    "雷": "⚡", "暴風": "🌀",
}

def get_weather_icon(text):
    for key, icon in WEATHER_ICONS.items():
        if key in text:
            return icon
    return "🌤️"

def fetch_weather(area_code="130000"):
    try:
        url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as res:
            data = json.loads(res.read().decode("utf-8"))

        today = data[0]
        area = today["timeSeries"][0]["areas"][0]
        area_name = area["area"]["name"]
        weathers = area["weathers"]
        today_weather = weathers[0] if weathers else "情報なし"
        tomorrow_weather = weathers[1] if len(weathers) > 1 else "情報なし"

        max_temp = "--"
        min_temp = "--"
        try:
            temp_areas = data[1]["timeSeries"][1]["areas"]
            for a in temp_areas:
                temps_max = a.get("tempsMax", [])
                temps_min = a.get("tempsMin", [])
                if temps_max:
                    max_temp = next((t for t in temps_max if t), "--")
                if temps_min:
                    min_temp = next((t for t in temps_min if t), "--")
                break
        except:
            pass

        hourly = []
        try:
            time_series = today["timeSeries"][0]
            times = time_series["timeDefines"]
            areas = time_series["areas"][0]
            weathers_list = areas.get("weathers", [])
            for i, t in enumerate(times[:6]):
                dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
                hour = (dt.hour + 9) % 24
                w = weathers_list[i] if i < len(weathers_list) else ""
                icon = get_weather_icon(w)
                hourly.append({"time": f"{hour}時", "weather": w, "icon": icon})
        except:
            pass

        return {
            "area": area_name,
            "today": today_weather,
            "today_icon": get_weather_icon(today_weather),
            "tomorrow": tomorrow_weather,
            "tomorrow_icon": get_weather_icon(tomorrow_weather),
            "max_temp": max_temp,
            "min_temp": min_temp,
            "hourly": hourly
        }
    except Exception as e:
        print(f"天気取得エラー: {e}")
        return None

def get_ogp_image(entry):
    if hasattr(entry, 'media_content') and entry.media_content:
        url = entry.media_content[0].get('url', '')
        if url:
            return url
    if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
        url = entry.media_thumbnail[0].get('url', '')
        if url:
            return url
    if hasattr(entry, 'enclosures') and entry.enclosures:
        for enc in entry.enclosures:
            if enc.get('type', '').startswith('image'):
                return enc.get('href', '')
    if hasattr(entry, 'links'):
        for link in entry.links:
            if link.get('type', '').startswith('image'):
                return link.get('href', '')
    summary = entry.get('summary', '')
    if '<img' in summary:
        import re
        m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', summary)
        if m:
            return m.group(1)
    return ''

def fetch_news(category, urls):
    articles = []
    for url in urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                articles.append({
                    "title": entry.title,
                    "summary": entry.get("summary", ""),
                    "link": entry.link,
                    "category": category,
                    "image": get_ogp_image(entry),
                })
        except:
            pass
    return articles

def summarize_article(article):
    message = anthropic_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        messages=[{
            "role": "user",
            "content": f"""以下のニュースを小学生でもわかる言葉で2〜3文で要約してください。
「# 要約」「# 簡単な説明」などの見出しは絶対につけず、いきなり本文から始めてください。

タイトル：{article['title']}
内容：{article['summary']}"""
        }]
    )
    return message.content[0].text

def generate_area_selector():
    html = ""
    for region, prefs in AREAS.items():
        pref_buttons = ""
        for pref, code in prefs.items():
            pref_buttons += f'<button class="pref-btn" onclick="changeArea(\'{code}\',\'{pref}\')">{pref}</button>'
        html += f'<div class="region-group"><div class="region-name">{region}</div><div class="pref-list">{pref_buttons}</div></div>'
    return html

def generate_weather_html(weather):
    if not weather:
        return '<div class="weather-error">天気情報を取得できませんでした</div>'

    hourly_html = ""
    for h in weather["hourly"]:
        hourly_html += f"""<div class="hourly-item"><div class="hourly-time">{h['time']}</div><div class="hourly-icon">{h['icon']}</div></div>"""

    return f"""
    <div class="weather-card" id="weatherCard">
        <div class="weather-area-selector">
            <button class="area-toggle-btn" onclick="toggleAreaSelector()">🗾 地域を変更 ▼</button>
            <div class="area-selector" id="areaSelector">
                {generate_area_selector()}
            </div>
        </div>
        <div id="weatherContent">
            <div class="weather-top">
                <div class="weather-main">
                    <div class="weather-icon-big">{weather['today_icon']}</div>
                    <div class="weather-info">
                        <div class="weather-area">{weather['area']}の天気</div>
                        <div class="weather-today">{weather['today']}</div>
                        <div class="weather-temp">🌡️ 最高 <span class="temp-max">{weather['max_temp']}℃</span> / 最低 <span class="temp-min">{weather['min_temp']}℃</span></div>
                    </div>
                </div>
                <div class="weather-tomorrow">
                    <div class="tomorrow-label">明日</div>
                    <div class="tomorrow-icon">{weather['tomorrow_icon']}</div>
                    <div class="tomorrow-text">{weather['tomorrow'][:8]}</div>
                </div>
            </div>
            <div class="weather-toggle" onclick="toggleHourly()">時間帯別を見る ▼</div>
            <div class="hourly-wrap" id="hourlyWrap">
                <div class="hourly-list">{hourly_html}</div>
            </div>
        </div>
    </div>"""

def generate_html(all_articles, weather=None):
    now = datetime.now().strftime("%Y年%m月%d日 %H:%M")

    nav_html = '<a href="#天気">🌤️ 天気</a>'
    sections_html = f"""
    <section id="天気">
        <div class="section-title">今日の天気</div>
        {generate_weather_html(weather)}
    </section>"""

    for category, articles in all_articles.items():
        nav_html += f'<a href="#{category}">{category}</a>'
        cards_html = ""
        for i, article in enumerate(articles):
            card_id = f"card_{category}_{i}"
            img_html = ""
            if article.get('image'):
                img_html = f'<div class="card-img"><img src="{article["image"]}" alt="" loading="lazy" onerror="this.parentElement.style.display=\'none\'"></div>'
            cards_html += f"""
            <div class="card" id="{card_id}">
                {img_html}
                <h3>{article['title']}</h3>
                <div class="card-summary-wrap">
                    <p class="card-summary">{article['summary_text']}</p>
                    <a href="{article['link']}" target="_blank" rel="noopener" class="read-more">元記事を読む →</a>
                </div>
                <div class="card-footer">
                    <span class="tag">{article['category']}</span>
                    <button class="expand-btn" onclick="toggleSummary('{card_id}')">要約を見る ▼</button>
                </div>
            </div>"""
        sections_html += f"""
        <section id="{category}">
            <div class="section-title">{category}</div>
            <div class="grid">{cards_html}</div>
        </section>"""

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>速見ニュース | HAYAMI NEWS</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Helvetica Neue', Arial, sans-serif; background: #111; color: #222; }}
        header {{ background: #0d0d0d; padding: 16px 20px; }}
        .header-inner {{ max-width: 1000px; margin: 0 auto; display: flex; align-items: center; justify-content: space-between; }}
        .logo {{ color: #fff; font-size: 1.6rem; font-weight: 900; letter-spacing: 4px; }}
        .logo span {{ color: #ff3b5c; }}
        .logo-sub {{ color: #555; font-size: 0.7rem; margin-top: 3px; letter-spacing: 2px; }}
        .update-time {{ color: #555; font-size: 0.72rem; }}
        nav {{ background: #1a1a1a; position: sticky; top: 0; z-index: 100; border-bottom: 1px solid #2a2a2a; }}
        .nav-inner {{ max-width: 1000px; margin: 0 auto; display: flex; overflow-x: auto; -webkit-overflow-scrolling: touch; }}
        .nav-inner::-webkit-scrollbar {{ display: none; }}
        nav a {{ color: #888; font-size: 0.82rem; padding: 12px 18px; white-space: nowrap; text-decoration: none; border-bottom: 2px solid transparent; }}
        nav a:hover {{ color: #ff3b5c; border-bottom-color: #ff3b5c; }}
        main {{ max-width: 1000px; margin: 0 auto; padding: 20px 16px; }}
        section {{ margin-bottom: 32px; }}
        .section-title {{ font-size: 1rem; font-weight: bold; color: #ddd; margin-bottom: 14px; display: flex; align-items: center; gap: 8px; }}
        .section-title::before {{ content: ''; display: block; width: 4px; height: 20px; background: #ff3b5c; border-radius: 2px; }}
        .grid {{ display: grid; grid-template-columns: 1fr; gap: 10px; }}
        @media(min-width: 640px) {{ .grid {{ grid-template-columns: repeat(2, 1fr); }} }}
        @media(min-width: 900px) {{ .grid {{ grid-template-columns: repeat(3, 1fr); }} }}
        .card {{ background: #1e1e1e; border-radius: 10px; overflow: hidden; border: 1px solid #444; border-top: 2px solid #ff3b5c; transition: transform 0.15s; display: flex; flex-direction: column; }}
        .card:hover {{ transform: translateY(-2px); box-shadow: 0 6px 16px rgba(0,0,0,0.4); }}
        .card-img {{ width: 100%; aspect-ratio: 16/9; overflow: hidden; background: #2a2a2a; }}
        .card-img img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
        .card h3 {{ font-size: 0.92rem; color: #f0f0f0; margin: 12px 16px 8px; line-height: 1.55; }}
        .card-summary-wrap {{ max-height: 0; overflow: hidden; transition: max-height 0.3s ease, padding 0.3s ease; padding: 0 16px; }}
        .card-summary-wrap.open {{ max-height: 300px; padding: 0 16px 10px; }}
        .card-summary {{ font-size: 0.82rem; color: #bbb; line-height: 1.8; margin-bottom: 8px; }}
        .read-more {{ display: inline-block; color: #ff3b5c; font-size: 0.75rem; text-decoration: none; }}
        .read-more:hover {{ text-decoration: underline; }}
        .card-footer {{ display: flex; align-items: center; justify-content: space-between; padding: 10px 16px 14px; margin-top: auto; }}
        .tag {{ display: inline-block; background: #ff3b5c22; color: #ff3b5c; font-size: 0.68rem; padding: 3px 9px; border-radius: 4px; border: 1px solid #ff3b5c44; }}
        .expand-btn {{ background: none; border: none; color: #888; font-size: 0.72rem; cursor: pointer; padding: 0; }}
        .expand-btn:hover {{ color: #ff3b5c; }}
        .weather-card {{ background: #1e1e1e; border-radius: 12px; padding: 20px; border: 1px solid #444; border-top: 2px solid #4fc3f7; }}
        .area-toggle-btn {{ background: #2a2a2a; color: #4fc3f7; border: 1px solid #4fc3f744; padding: 6px 14px; border-radius: 6px; font-size: 0.78rem; cursor: pointer; margin-bottom: 12px; }}
        .area-selector {{ display: none; background: #2a2a2a; border-radius: 10px; padding: 14px; margin-bottom: 14px; }}
        .area-selector.open {{ display: block; }}
        .region-group {{ margin-bottom: 10px; }}
        .region-name {{ color: #888; font-size: 0.72rem; margin-bottom: 6px; }}
        .pref-list {{ display: flex; flex-wrap: wrap; gap: 6px; }}
        .pref-btn {{ background: #333; color: #ccc; border: 1px solid #444; padding: 4px 10px; border-radius: 4px; font-size: 0.75rem; cursor: pointer; }}
        .pref-btn:hover {{ background: #4fc3f7; color: #111; border-color: #4fc3f7; }}
        .weather-top {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }}
        .weather-main {{ display: flex; align-items: center; gap: 16px; flex: 1; }}
        .weather-icon-big {{ font-size: 3.5rem; line-height: 1; }}
        .weather-area {{ color: #888; font-size: 0.75rem; margin-bottom: 4px; }}
        .weather-today {{ color: #f0f0f0; font-size: 0.95rem; font-weight: bold; margin-bottom: 6px; }}
        .weather-temp {{ color: #bbb; font-size: 0.82rem; }}
        .temp-max {{ color: #ff6b6b; font-weight: bold; }}
        .temp-min {{ color: #4fc3f7; font-weight: bold; }}
        .weather-tomorrow {{ text-align: center; background: #2a2a2a; border-radius: 8px; padding: 10px 14px; }}
        .tomorrow-label {{ color: #888; font-size: 0.7rem; margin-bottom: 4px; }}
        .tomorrow-icon {{ font-size: 1.8rem; margin-bottom: 4px; }}
        .tomorrow-text {{ color: #ccc; font-size: 0.72rem; }}
        .weather-toggle {{ color: #4fc3f7; font-size: 0.78rem; cursor: pointer; margin-top: 14px; padding-top: 14px; border-top: 1px solid #2a2a2a; }}
        .hourly-wrap {{ max-height: 0; overflow: hidden; transition: max-height 0.3s ease; }}
        .hourly-wrap.open {{ max-height: 100px; }}
        .hourly-list {{ display: flex; gap: 8px; padding-top: 12px; overflow-x: auto; }}
        .hourly-item {{ text-align: center; background: #2a2a2a; border-radius: 8px; padding: 8px 12px; min-width: 56px; }}
        .hourly-time {{ color: #888; font-size: 0.68rem; margin-bottom: 4px; }}
        .hourly-icon {{ font-size: 1.4rem; }}
        .loading {{ color: #888; font-size: 0.82rem; text-align: center; padding: 20px; }}
        footer {{ background: #0d0d0d; color: #444; text-align: center; padding: 24px 20px; font-size: 0.8rem; margin-top: 20px; }}
        footer span {{ color: #ff3b5c; }}
    </style>
</head>
<body>
    <header>
        <div class="header-inner">
            <div>
                <div class="logo">HAYAMI<span> NEWS</span></div>
                <div class="logo-sub">速見ニュース — 今日を5分で知る</div>
            </div>
            <div class="update-time">更新 {now}</div>
        </div>
    </header>
    <nav><div class="nav-inner">{nav_html}</div></nav>
    <main>{sections_html}</main>
    <footer>
        © 2024 <span>速見ニュース</span> | HAYAMI NEWS<br>
        <span style="font-size:0.72rem;color:#333;margin-top:6px;display:block;">ニュースの内容はAIが要約しています</span>
    </footer>
    <script>
    function toggleSummary(cardId) {{
        const card = document.getElementById(cardId);
        const wrap = card.querySelector('.card-summary-wrap');
        const btn = card.querySelector('.expand-btn');
        const isOpen = wrap.classList.toggle('open');
        btn.textContent = isOpen ? '閉じる ▲' : '要約を見る ▼';
    }}
    const WEATHER_ICONS = {{"晴":"☀️","快晴":"☀️","曇":"⛅","くもり":"⛅","雨":"🌧️","小雨":"🌦️","雪":"❄️","雷":"⚡"}};
    function getIcon(text) {{
        for(const [k,v] of Object.entries(WEATHER_ICONS)) {{ if(text.includes(k)) return v; }}
        return "🌤️";
    }}
    function toggleAreaSelector() {{
        document.getElementById('areaSelector').classList.toggle('open');
    }}
    function toggleHourly() {{
        const wrap = document.getElementById('hourlyWrap');
        const btn = document.querySelector('.weather-toggle');
        wrap.classList.toggle('open');
        btn.textContent = wrap.classList.contains('open') ? '時間帯別を閉じる ▲' : '時間帯別を見る ▼';
    }}
    async function changeArea(code, name) {{
        document.getElementById('areaSelector').classList.remove('open');
        document.getElementById('weatherContent').innerHTML = '<div class="loading">天気情報を取得中...</div>';
        try {{
            const res = await fetch(`https://www.jma.go.jp/bosai/forecast/data/forecast/${{code}}.json`);
            const data = await res.json();
            const area = data[0].timeSeries[0].areas[0];
            const weathers = area.weathers || [];
            const todayW = weathers[0] || "情報なし";
            const tomorrowW = weathers[1] || "情報なし";
            let maxTemp = "--", minTemp = "--";
            try {{
                const tempAreas = data[1].timeSeries[1].areas;
                for(const a of tempAreas) {{
                    const mx = (a.tempsMax||[]).find(t=>t);
                    const mn = (a.tempsMin||[]).find(t=>t);
                    if(mx) maxTemp = mx;
                    if(mn) minTemp = mn;
                    break;
                }}
            }} catch(e) {{}}
            let hourlyHtml = "";
            try {{
                const ts = data[0].timeSeries[0];
                ts.timeDefines.slice(0,6).forEach((t,i) => {{
                    const h = (new Date(t).getHours() + 9) % 24;
                    const w = (ts.areas[0].weathers||[])[i] || "";
                    hourlyHtml += `<div class="hourly-item"><div class="hourly-time">${{h}}時</div><div class="hourly-icon">${{getIcon(w)}}</div></div>`;
                }});
            }} catch(e) {{}}
            document.getElementById('weatherContent').innerHTML = `
                <div class="weather-top">
                    <div class="weather-main">
                        <div class="weather-icon-big">${{getIcon(todayW)}}</div>
                        <div class="weather-info">
                            <div class="weather-area">${{name}}の天気</div>
                            <div class="weather-today">${{todayW}}</div>
                            <div class="weather-temp">🌡️ 最高 <span class="temp-max">${{maxTemp}}℃</span> / 最低 <span class="temp-min">${{minTemp}}℃</span></div>
                        </div>
                    </div>
                    <div class="weather-tomorrow">
                        <div class="tomorrow-label">明日</div>
                        <div class="tomorrow-icon">${{getIcon(tomorrowW)}}</div>
                        <div class="tomorrow-text">${{tomorrowW.slice(0,8)}}</div>
                    </div>
                </div>
                <div class="weather-toggle" onclick="toggleHourly()">時間帯別を見る ▼</div>
                <div class="hourly-wrap" id="hourlyWrap">
                    <div class="hourly-list">${{hourlyHtml}}</div>
                </div>`;
        }} catch(e) {{
            document.getElementById('weatherContent').innerHTML = '<div class="loading">取得に失敗しました</div>';
        }}
    }}
    </script>
</body>
</html>"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("index.html を生成しました")

def main():
    print("天気情報を取得中...")
    weather = fetch_weather("130000")
    if weather:
        print(f"天気: {weather['area']} {weather['today_icon']} 最高{weather['max_temp']}℃ 最低{weather['min_temp']}℃")

    all_articles = {}
    for category, urls in RSS_FEEDS.items():
        print(f"{category}のニュースを取得中...")
        articles = fetch_news(category, urls)
        for article in articles[:3]:
            print(f"  要約中: {article['title'][:30]}...")
            article['summary_text'] = summarize_article(article)
        all_articles[category] = articles[:3]

    print("HTMLを生成中...")
    generate_html(all_articles, weather)
    print("完了！")

if __name__ == "__main__":
    main()
