import json
import hashlib
import requests

# ===== Clé API NewsAPI (gratuite : https://newsapi.org/register) =====
API_KEY = "d086dd8d0b694ed1a60a74aa57c03b9b"

queries = {
    "Q1": "Iran regime collapse",
    "Q2": "Hormuz strait closure",
    "Q3": "Revolutionary Guard attack",
    "Q4": "Iran supreme leader speech",
    "Q5": "US bases Iran missiles",
}

all_docs = []
qrels = []

for qid, query in queries.items():
    print(f"Collecting for {qid}: {query}")

    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "language": "en",
        "pageSize": 100,
        "sortBy": "relevancy",
        "apiKey": API_KEY,
    }

    resp = requests.get(url, params=params)
    data = resp.json()

    articles = data.get("articles", [])
    print(f"  -> {len(articles)} articles trouvés")

    for rank, article in enumerate(articles, start=1):
        # Générer un docno stable à partir de l'URL
        docno = hashlib.md5(article["url"].encode()).hexdigest()[:16]

        text = (article.get("title") or "") + ". " + (article.get("description") or "")

        record = {
            "docno": docno,
            "text": text,
            "qid": qid,
            "rank": rank,
            "source": article.get("source", {}).get("name", ""),
            "url": article.get("url", ""),
            "published_at": article.get("publishedAt", ""),
        }
        all_docs.append(record)

        # Top 30 = pertinents (1), le reste = non pertinents (0)
        relevance = 1 if rank <= 30 else 0
        qrels.append(f"{qid} 0 {docno} {relevance}")

# Save documents
with open("tweets.jsonl", "w", encoding="utf-8") as f:
    for t in all_docs:
        f.write(json.dumps(t, ensure_ascii=False) + "\n")

# Save qrels (format TREC)
with open("qrels.txt", "w") as f:
    f.write("\n".join(qrels))

print(f"\nTotal documents collectés : {len(all_docs)}")
print("Fichiers générés : tweets.jsonl, qrels.txt")