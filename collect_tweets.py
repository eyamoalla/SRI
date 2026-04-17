import json
import hashlib
import time
from urllib.parse import quote

from playwright.sync_api import sync_playwright

queries = {
    "Q1": "Iran regime collapse",
    "Q2": "Hormuz strait closure",
    "Q3": "Revolutionary Guard attack",
    "Q4": "Iran supreme leader speech",
    "Q5": "US bases Iran missiles",
}

MAX_TWEETS_PER_QUERY = 100
SCROLL_PAUSE_MS = 1800
MAX_NO_NEW_ROUNDS = 4

all_docs = []
qrels = []

def make_docno(text: str, url: str) -> str:
    base = (url or text).encode("utf-8", errors="ignore")
    return hashlib.md5(base).hexdigest()[:16]

with sync_playwright() as p:
    # Persistent profile lets you stay logged in on X between runs.
    context = p.chromium.launch_persistent_context(
        channel="chrome",
        user_data_dir="pw-user-data",
        headless=False,
        viewport={"width": 1280, "height": 900},
    )
    page = context.new_page()

    print("If not logged in, log in manually in the opened browser window.")
    print("After login is complete, press Enter here to continue...")
    input()

    for qid, query in queries.items():
        print(f"Collecting for {qid}: {query}")
        search_url = f"https://x.com/search?q={quote(query)}&src=typed_query&f=live"
        page.goto(search_url, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        seen = set()
        no_new_rounds = 0
        rank = 0

        while len(seen) < MAX_TWEETS_PER_QUERY and no_new_rounds < MAX_NO_NEW_ROUNDS:
            cards = page.locator('article[data-testid="tweet"]')
            count = cards.count()
            before = len(seen)

            for i in range(count):
                if len(seen) >= MAX_TWEETS_PER_QUERY:
                    break

                card = cards.nth(i)

                text_loc = card.locator('div[data-testid="tweetText"]')
                if text_loc.count() == 0:
                    continue

                text = text_loc.first.inner_text().strip()
                if not text:
                    continue

                url = ""
                link_loc = card.locator('a[href*="/status/"]')
                if link_loc.count() > 0:
                    href = link_loc.first.get_attribute("href") or ""
                    if href.startswith("/"):
                        url = "https://x.com" + href
                    else:
                        url = href

                dedupe_key = (url or text).strip()
                if not dedupe_key or dedupe_key in seen:
                    continue
                seen.add(dedupe_key)

                rank += 1
                docno = make_docno(text, url)
                record = {
                    "docno": docno,
                    "text": text,
                    "qid": qid,
                    "rank": rank,
                    "source": "x.com",
                    "url": url,
                    "published_at": "",
                }
                all_docs.append(record)

                relevance = 1 if rank <= 30 else 0
                qrels.append(f"{qid} 0 {docno} {relevance}")

            # Scroll for more tweets
            page.mouse.wheel(0, 6000)
            page.wait_for_timeout(SCROLL_PAUSE_MS)

            if len(seen) == before:
                no_new_rounds += 1
            else:
                no_new_rounds = 0

        print(f"  -> {len(seen)} tweets collected")

    context.close()

with open("tweets.jsonl", "w", encoding="utf-8") as f:
    for t in all_docs:
        f.write(json.dumps(t, ensure_ascii=False) + "\n")

with open("qrels.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(qrels))

print(f"\nTotal documents collectés : {len(all_docs)}")
print("Fichiers générés : tweets.jsonl, qrels.txt")