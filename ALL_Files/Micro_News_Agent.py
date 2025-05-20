import os
import json
import requests
from datetime import datetime
from LLM_API_CALL import deepseek_api_call
import tempfile
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed

RATING_JSON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Rating_Json")

def fetch_fmp_news(ticker, limit=10):
    """
    Fetch the most recent news articles for a ticker using the FMP API.
    """
    api_key = "…"
    urls = [
        f"https://financialmodelingprep.com/stable/news/stock?symbols={ticker}&limit={limit}&apikey={api_key}",
        f"https://financialmodelingprep.com/stable/news/crypto?symbols={ticker}&limit={limit}&apikey={api_key}"
    ]

    # 用线程池同时发出两个请求，哪个先返回有效就用哪个
    with ThreadPoolExecutor(max_workers=2) as ex:
        future_to_url = {ex.submit(requests.get, url): url for url in urls}
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            resp = future.result()
            if resp.status_code == 200:
                try:
                    articles = resp.json()
                    if articles:
                        print(f"[DEBUG] Got articles from {url}")
                        return articles[:limit]
                except:
                    pass
    return []


def summarize_news_with_llm(ticker, articles):
    """
    Use LLM to generate key takeaways, expectations, and next inference hint from news articles.
    """
    if not articles:
        return {
            "Three_Key_Takeaways": "No recent news articles found.",
            "Micro_Expectation": "No expectations can be formed due to lack of news.",
            "Next_Inference_Hint_Micro_News": "No news context available for next step."
        }
    # Concatenate news snippets for LLM context
    news_context = ""
    for i, article in enumerate(articles):
        title = article.get("title", "")
        text = article.get("text", article.get("content", ""))
        date = article.get("publishedDate", article.get("date", ""))
        print(f"[DEBUG] Article {i+1}: title={title}, date={date}, text_snippet={text[:100]}")
        news_context += f"{i+1}. {title} ({date})\n{text}\n\n"
    
    prompt = f"""
You are a professional financial news analyst. Given the following recent news for {ticker}, do the following:
1. Extract and summarize the three most important key takeaways (facts, events, or themes).
2. Summarize the current market expectations or sentiment for the company/crypto.
3. Generate a forward-looking inference hint for the next analyst step (what should be investigated next, or what is the most important open question?).

Return your answer as a JSON object with these keys:
- Three_Key_Takeaways: string (bulleted or numbered)
- Micro_Expectation: string
- Next_Inference_Hint_Micro_News: string

Recent news:
{news_context}
    """
    print(f"[DEBUG] LLM prompt:\n{prompt[:1000]}")  # Print first 1000 chars of prompt
    try:
        llm_response = deepseek_api_call(prompt)
        print(f"[DEBUG] LLM response: {llm_response}")
        # Try to extract JSON from LLM response
        import re
        import ast
        match = re.search(r"\{[\s\S]*\}", llm_response)
        if match:
            json_str = match.group(0)
            try:
                result = json.loads(json_str)
            except Exception:
                # Sometimes LLM returns single quotes, use ast.literal_eval as fallback
                result = ast.literal_eval(json_str)
            return result
        else:
            # Fallback: return the whole response as key takeaways
            return {
                "Three_Key_Takeaways": llm_response.strip(),
                "Micro_Expectation": "",
                "Next_Inference_Hint_Micro_News": ""
            }
    except Exception as e:
        print(f"[ERROR] Exception in LLM summarization: {e}")
        return {
            "Three_Key_Takeaways": f"Error generating summary: {e}",
            "Micro_Expectation": "",
            "Next_Inference_Hint_Micro_News": ""
        }

def process_ticker(ticker, limit=10):
    """
    Main entry: fetch news, summarize, and update the rating JSON for the ticker.
    """
    # Find the latest rating JSON for the ticker
    rating_files = [
        f for f in os.listdir(RATING_JSON_DIR)
        if f.startswith(f"{ticker}_Rating_") and f.endswith(".json")
    ]
    if not rating_files:
        print(f"No rating JSON found for {ticker}")
        return {
            "Three_Key_Takeaways": "",
            "Micro_Expectation": "",
            "Next_Inference_Hint_Micro_News": ""
        }
    latest_file = max(rating_files, key=lambda f: os.path.getmtime(os.path.join(RATING_JSON_DIR, f)))
    rating_json_path = os.path.join(RATING_JSON_DIR, latest_file)

    # Fetch news
    articles = fetch_fmp_news(ticker, limit=limit)
    # Summarize with LLM
    summary = summarize_news_with_llm(ticker, articles)
    print(f"[DEBUG] Summary to write: {summary}")

    # Update only the three subcolumns in Micro
    with open(rating_json_path, "r") as f:
        rating_data = json.load(f)

    if "Micro" not in rating_data or not isinstance(rating_data["Micro"], dict):
        rating_data["Micro"] = {}

    rating_data["Micro"]["Three_Key_Takeaways"] = str(summary.get("Three_Key_Takeaways", ""))
    rating_data["Micro"]["Micro_Expectation"] = str(summary.get("Micro_Expectation", ""))
    rating_data["Micro"]["Next_Inference_Hint_Micro_News"] = str(summary.get("Next_Inference_Hint_Micro_News", ""))

    with open(rating_json_path, "w") as f:
        json.dump(rating_data, f, indent=4)

    with open(rating_json_path, "r") as f:
        print("[DEBUG] File content after write:", f.read())

    print(f"Successfully updated {rating_json_path} with micro news analysis")
    return summary

# For direct CLI use
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python Micro_News_Agent.py <TICKER>")
        sys.exit(1)
    ticker = sys.argv[1].upper()
    process_ticker(ticker)
