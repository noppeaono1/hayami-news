import feedparser
import anthropic
import tweepy
import os
from dotenv import load_dotenv

load_dotenv()

# APIクライアント設定
anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

x_client = tweepy.Client(
    consumer_key=os.getenv("X_API_KEY"),
    consumer_secret=os.getenv("X_API_SECRET"),
    access_token=os.getenv("X_ACCESS_TOKEN"),
    access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET"),
    bearer_token=os.getenv("X_BEARER_TOKEN")
)

# RSSフィード一覧
RSS_FEEDS = [
    "https://www3.nhk.or.jp/rss/news/cat0.xml",
    "https://feeds.feedburner.com/nhkworld/news",
]

def fetch_news():
    articles = []
    for url in RSS_FEEDS:
        feed = feedparser.parse(url)
        for entry in feed.entries[:3]:
            articles.append({
                "title": entry.title,
                "summary": entry.get("summary", ""),
                "link": entry.link
            })
    return articles

def summarize_news(articles):
    headlines = "\n".join([f"・{a['title']}" for a in articles[:5]])
    message = anthropic_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": f"""以下のニュース見出しをもとに、X投稿文を1つ作成してください。
条件：
- 140文字以内
- 誰でもわかりやすい言葉で
- 最後に #速見ニュース #hayaminews をつける

ニュース見出し：
{headlines}"""
        }]
    )
    return message.content[0].text

def post_to_x(text):
    response = x_client.create_tweet(text=text)
    print(f"投稿完了: {response.data['id']}")
    return response

def main():
    print("ニュース取得中...")
    articles = fetch_news()
    print(f"{len(articles)}件取得しました")
    print("要約生成中...")
    post_text = summarize_news(articles)
    print(f"投稿文:\n{post_text}")
    confirm = input("\nこの内容でXに投稿しますか？(y/n): ")
    if confirm.lower() == "y":
        post_to_x(post_text)
    else:
        print("投稿をキャンセルしました")

if __name__ == "__main__":
    main()