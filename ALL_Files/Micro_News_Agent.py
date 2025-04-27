import os
import json
import requests
import feedparser
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import re
import pytz
import tiktoken
from LLM_API_CALL import deepseek_api_call

# File paths
RATING_JSON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Rating_Json")
DEBUG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Debug")

# Create debug directory if it doesn't exist
if not os.path.exists(DEBUG_DIR):
    os.makedirs(DEBUG_DIR)

# Debug mode flag
DEBUG = False

# Maximum tokens for content (increased to allow more articles)
MAX_TOKENS = 15000

def num_tokens_from_string(string, encoding_name="cl100k_base"):
    """Calculate the number of tokens in a string."""
    encoding = tiktoken.get_encoding(encoding_name)
    return len(encoding.encode(string))

def extract_date(date_string):
    """Extract date from various date formats."""
    try:
        for fmt in ["%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S"]:
            try:
                return datetime.strptime(date_string, fmt)
            except ValueError:
                continue
        return None
    except Exception:
        return None

def scrape_news(url):
    """Check if an article is accessible."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return 1
        return 0
    except Exception:
        return 0

def extract_news_content(url):
    """Extracts full news content using BeautifulSoup."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "lxml")

        # Extract main article content (different websites have different structures)
        # Try different potential article containers
        article_body = soup.find("article") or soup.find("div", {"class": "content"}) or soup.find("div", {"class": "article-body"})
        
        if article_body:
            paragraphs = article_body.find_all("p")
            content = "\n".join([para.get_text() for para in paragraphs])
        else:
            # If no specific article container is found, extract all paragraphs
            paragraphs = soup.find_all('p')
            content = "\n".join([para.get_text() for para in paragraphs])

        return content.strip() if content else "⚠ Unable to extract article content."

    except Exception as e:
        return f"⚠ Extraction failed: {str(e)}"

def get_news_json(ticker, n_days=7, min_accessible_articles=15):
    """Retrieve news for a specific ticker."""
    print(f"Searching for {ticker} news from the past {n_days} days...")
    
    token_data = []
    accessible_articles_count = 0
    
    today = datetime.now(pytz.utc)
    threshold_date = today - timedelta(days=n_days)
    
    # Define specialized RSS feeds for company-specific news
    COMPANY_RSS_FEEDS = {
        f"Yahoo Finance - {ticker}": f"https://finance.yahoo.com/rss/headline?s={ticker}",
        f"Google News - {ticker} Stock": f"https://news.google.com/rss/search?q={ticker}+stock&hl=en-US&gl=US&ceid=US:en",
        f"Google News - {ticker} Earnings": f"https://news.google.com/rss/search?q={ticker}+earnings&hl=en-US&gl=US&ceid=US:en",
        f"Google News - {ticker} Analyst": f"https://news.google.com/rss/search?q={ticker}+analyst+ratings&hl=en-US&gl=US&ceid=US:en",
        f"Seeking Alpha - {ticker}": f"https://seekingalpha.com/api/sa/combined/{ticker}.xml",
        # Add more general financial sources that might have ticker news
        f"CNBC - {ticker}": f"https://www.cnbc.com/search/rss?q={ticker}"
    }

    new_counter = 0
    total_found = 0
    
    # Flag to break out of nested loops when we have enough articles
    enough_articles = False
    
    for source_name, rss_url in COMPANY_RSS_FEEDS.items():
        if enough_articles:
            break
            
        try:
            print(f"Fetching from {source_name}: {rss_url}")
            feed = feedparser.parse(rss_url)
            if not feed.entries:
                print(f"No entries found in {source_name}")
                continue
                
            print(f"Found {len(feed.entries)} articles from {source_name}")
            total_found += len(feed.entries)

            for entry in feed.entries:
                pub_date = entry.published if "published" in entry else "No Date"
                article_datetime = extract_date(pub_date)
                
                # Check if article is within time interval (we'll still track this but not filter by it)
                is_in_interval = True
                if not article_datetime or article_datetime < threshold_date:
                    is_in_interval = False

                article_url = entry.link
                try:
                    accessible = scrape_news(article_url)
                    if accessible == 1:
                        accessible_articles_count += 1
                    print(f"Article {article_url} accessible: {accessible}, Total accessible: {accessible_articles_count}")
                except Exception as e:
                    print(f"Error processing article: {str(e)}")
                    accessible = 0

                new_counter += 1
                print(f'Discovering articles about {ticker}... ({new_counter})')
                
                # Calculate token count
                article_tokens = num_tokens_from_string(entry.title)

                token_data.append({
                    "title": entry.title,
                    "url": article_url,
                    "tokens": article_tokens,
                    "date": pub_date.strip(),
                    "rank": None,
                    "out_of_interval": 0 if is_in_interval else 1,
                    "accessible": accessible,
                    "source": source_name
                })
                
                # Check if we have enough accessible articles (regardless of interval)
                if accessible_articles_count >= min_accessible_articles:
                    print(f"Found {min_accessible_articles} accessible articles. Stopping search.")
                    enough_articles = True
                    break
                
                # Sleep briefly to avoid being blocked
                time.sleep(0.5)
                
        except Exception as e:
            print(f"Error fetching from {rss_url}: {str(e)}")
    
    if not token_data:
        if total_found > 0:
            print(f"Found {total_found} articles about {ticker}, but none were accessible")
        else:
            print(f"No news articles found for {ticker}. Try a different ticker or increase the date range.")
        return None
    
    # Count accessible articles
    accessible_count = sum(1 for article in token_data if article["accessible"] == 1)
    
    print(f"Processing {len(token_data)} total articles ({accessible_count} accessible) for {ticker}")
    return token_data

def rank_articles(articles, ticker):
    """Rank articles by relevance."""
    print('Ranking news articles by relevance...')
    
    if not articles:
        print(f"No news articles were found for {ticker}.")
        return None
    
    # Filter out articles that are out of interval or not accessible
    filtered_articles = [
        article for article in articles
        if article["out_of_interval"] == 0 and article["accessible"] == 1
    ]
    
    total_articles = len(articles)
    accessible_articles = sum(1 for article in articles if article["accessible"] == 1)
    in_interval_articles = sum(1 for article in articles if article["out_of_interval"] == 0)
    filtered_count = len(filtered_articles)
    
    print(f"Found {total_articles} articles, {accessible_articles} accessible, {in_interval_articles} within time range, {filtered_count} valid")
    
    if not filtered_articles:
        if total_articles > 0 and accessible_articles == 0:
            print(f"Found {total_articles} articles for {ticker}, but none were accessible (possibly behind paywalls)")
        elif in_interval_articles == 0:
            print(f"Found {total_articles} articles for {ticker}, but none were within the specified time range")
        else:
            print(f"No relevant articles found for {ticker}. Try a more popular ticker or increase the date range.")
        return None

    # Prepare a list of relevant articles for ranking
    relevant_articles = [
        {"title": article["title"], "url": article["url"]}
        for article in filtered_articles
    ]

    print(f"Sending {len(relevant_articles)} articles to DeepSeek for ranking")
    prompt = f"""
    You are an AI assistant that ranks news articles based on their importance and relevance. 
    The articles are related to the stock ticker {ticker}. 
    Rank the following articles in order of priority (1 being the most important).
    
    Articles:
    {json.dumps(relevant_articles, indent=2)}
    
    Please return the ranking in a JSON format like:
    {{"rankings": [{{"title": "Article Title", "url": "Article URL", "rank": 1}}, 
                    {{"title": "Another Title", "url": "Another URL", "rank": 2}}, ...]}}
    """

    response_text = deepseek_api_call(prompt)
    print("Received response from DeepSeek")
    
    # Standard JSON extraction process
    cleaned_response_text = re.sub(r"```json\n|\n```", "", response_text).strip()

    try:
        ranking_result = json.loads(cleaned_response_text)
            
        rankings = ranking_result.get("rankings", [])
        print(f"Parsed rankings: {len(rankings)} articles ranked")
        
        # Update the original articles with ranks
        url_to_rank = {item["url"]: item["rank"] for item in rankings}
        for article in filtered_articles:
            article["rank"] = url_to_rank.get(article["url"])
        
        # Sort by rank
        ranked_articles = sorted([a for a in filtered_articles if a["rank"] is not None], key=lambda x: x["rank"])
        print(f"Successfully ranked {len(ranked_articles)} articles")
        
        return ranked_articles
        
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error parsing ranking result: {str(e)}")
        print(f"Raw response: {response_text}")
        return None

def scrape_articles_directly(articles, ticker, target_count=15):
    """Scrape content from articles without ranking them first."""
    print(f"Scraping {len(articles)} articles for {ticker}")
    
    if not articles:
        print("No articles provided")
        return "No article content available"
    
    cache_content = []
    scrape_counter = 0
    success_counter = 0
    failure_counter = 0
    total_tokens = 0
    
    # Detailed failure tracking
    failure_reasons = {
        "extraction_failed": 0,
        "content_too_short": 0,
        "token_limit": 0,
        "exception": 0
    }
    
    # Create a copy of the articles list to modify if needed
    articles_to_process = list(articles)
    
    print(f"Attempting to scrape {len(articles_to_process)} articles to get {target_count} successful ones")
    
    # Process articles until we have enough or run out
    while articles_to_process and success_counter < target_count and total_tokens < MAX_TOKENS:
        if scrape_counter >= len(articles_to_process):
            print(f"Processed all {scrape_counter} articles but only got {success_counter} successful extractions")
            break
            
        article = articles_to_process[scrape_counter]
        title = article["title"]
        url = article["url"]
        scrape_counter += 1
        print(f"Scraping article {scrape_counter}/{len(articles_to_process)}: {url}")

        try:
            # Try to extract the content - this is the real test of accessibility
            content = extract_news_content(url)
            
            # If content is too short or contains extraction error message, skip it
            if content.startswith("⚠"):
                print(f"Article extraction failed: {content[:100]}")
                failure_counter += 1
                failure_reasons["extraction_failed"] += 1
                continue
                
            if len(content) < 150:  # Minimum content length to be useful
                print(f"Article content too short ({len(content)} chars): {content[:100]}")
                failure_counter += 1
                failure_reasons["content_too_short"] += 1
                continue
                
            # Track token count
            article_tokens = num_tokens_from_string(content)
            
            # Check if adding this article would exceed token limit
            if total_tokens + article_tokens > MAX_TOKENS:
                print(f"Token limit would be exceeded. Current: {total_tokens}, Article: {article_tokens}, Max: {MAX_TOKENS}")
                failure_counter += 1
                failure_reasons["token_limit"] += 1
                break
            
            total_tokens += article_tokens
            success_counter += 1
            
            article_content = f"🔹 {title}\n🔗 {url}\n\n{content}\n{'-'*80}\n"
            cache_content.append(article_content)
            print(f"Article {scrape_counter} successfully added. Count: {success_counter}/{target_count}. Tokens: {total_tokens}/{MAX_TOKENS}")

        except Exception as e:
            print(f"Error scraping {url}: {str(e)}")
            failure_counter += 1
            failure_reasons["exception"] += 1
            continue

    if not cache_content:
        print("Failed to extract content from any of the articles")
        return "No article content could be extracted"
    
    print(f"FINAL RESULTS: Successfully scraped {success_counter} out of {scrape_counter} articles. Failed: {failure_counter}. Total tokens: {total_tokens}")
    print(f"Failure reasons: {failure_reasons}")
    
    # In debug mode, save the success rate information
    if DEBUG:
        success_rate_info = (
            f"Articles processed: {scrape_counter}\n"
            f"Successful extractions: {success_counter}\n"
            f"Failed extractions: {failure_counter}\n"
            f"Success rate: {success_counter/scrape_counter*100:.2f}%\n"
            f"Total tokens: {total_tokens}\n\n"
            f"Failure reasons:\n"
            f"- Extraction failed: {failure_reasons['extraction_failed']}\n"
            f"- Content too short: {failure_reasons['content_too_short']}\n"
            f"- Token limit reached: {failure_reasons['token_limit']}\n"
            f"- Exception thrown: {failure_reasons['exception']}\n\n"
            f"Note: If you need more articles, consider:\n"
            f"1. Increasing the MAX_TOKENS limit (currently {MAX_TOKENS})\n"
            f"2. Increasing the min_target_articles in process_ticker (to fetch more articles initially)\n"
            f"3. Improving the extract_news_content function to handle more website structures"
        )
        debug_stats_path = os.path.join(DEBUG_DIR, f"{ticker}_scraping_stats.txt")
        with open(debug_stats_path, 'w', encoding='utf-8') as f:
            f.write(success_rate_info)
        print(f"DEBUG: Saved detailed scraping stats to {debug_stats_path}")
    
    full_content = "\n".join(cache_content)
    return full_content

def analyze_ticker_news(ticker, cached_data):
    """Generate key takeaways and micro expectations from ticker news."""
    print(f"Analyzing news content for {ticker}...")
    
    prompt = f"""
    ## Prompt: You are a professional financial analyst focused exclusively on company-specific news and developments. 
    Analyze the following news articles about {ticker} and provide:

    1. THREE KEY TAKEAWAYS: Extract the three most important insights about this company from the news articles.
       Each takeaway should be concise, specific, and focused ONLY on company-specific news (NOT macro trends).
       Format each takeaway as a brief headline followed by 1-2 sentences explaining its significance.
       
    2. MICRO EXPECTATIONS: Based solely on these news articles, provide a clear summary of what analysts and 
       financial institutions expect for this company in the near future. Include specific metrics, targets, 
       growth estimates, or guidance mentioned if available. Be quantitative whenever possible.
       
    3. NEXT INFERENCE HINT: Provide 3-4 concise sentences that:
       - Summarize the current sentiment in the news (is it overly greedy or fearful?)
       - Indicate if the company is outperforming or underperforming peers
       - Suggest if the stock appears favorable based on news
       - Recommend specific areas to investigate next (e.g., "investigate Q2 earnings breakdown")
       Your hint should be actionable and provide clear direction for further analysis.

    IMPORTANT INSTRUCTIONS:
    - Focus ONLY on company/ticker-specific information
    - Do NOT include macro trends or general market conditions
    - Be specific and data-driven whenever possible (include numbers, percentages, dates)
    - Extract information directly from the articles, don't make assumptions
    - Be concise but comprehensive
    
    Here are the articles to analyze:
    {cached_data}

    Format your response exactly as follows:
    
    THREE_KEY_TAKEAWAYS:
    1. [First key takeaway headline]: [1-2 sentence explanation with specific details]
    2. [Second key takeaway headline]: [1-2 sentence explanation with specific details]
    3. [Third key takeaway headline]: [1-2 sentence explanation with specific details]
    
    MICRO_EXPECTATIONS:
    [A clear, data-driven paragraph summarizing analyst and financial institution expectations for this company's future performance, including specific metrics when available]
    
    NEXT_INFERENCE_HINT:
    [3-4 concise, actionable sentences that summarize sentiment, performance vs peers, favorability, and specific areas to investigate next]
    """
    
    # Save prompt to file if in debug mode
    if DEBUG:
        debug_prompt_path = os.path.join(DEBUG_DIR, f"{ticker}_prompt.txt")
        with open(debug_prompt_path, 'w', encoding='utf-8') as f:
            f.write(prompt)
        print(f"DEBUG: Saved prompt to {debug_prompt_path}")
    
    response = deepseek_api_call(prompt)
    print("Received analysis from DeepSeek")
    
    # Save response to file if in debug mode
    if DEBUG:
        debug_response_path = os.path.join(DEBUG_DIR, f"{ticker}_response.txt")
        with open(debug_response_path, 'w', encoding='utf-8') as f:
            f.write(response)
        print(f"DEBUG: Saved response to {debug_response_path}")
    
    # Parse the response to extract the three sections
    takeaways_match = re.search(r"THREE_KEY_TAKEAWAYS:(.*?)MICRO_EXPECTATIONS:", response, re.DOTALL)
    expectations_match = re.search(r"MICRO_EXPECTATIONS:(.*?)NEXT_INFERENCE_HINT:", response, re.DOTALL)
    inference_hint_match = re.search(r"NEXT_INFERENCE_HINT:(.*?)$", response, re.DOTALL)
    
    takeaways = takeaways_match.group(1).strip() if takeaways_match else "Unable to extract key takeaways."
    expectations = expectations_match.group(1).strip() if expectations_match else "Unable to extract micro expectations."
    inference_hint = inference_hint_match.group(1).strip() if inference_hint_match else "Unable to extract next inference hint."
    
    return {
        "Three_Key_Takeaway_News": takeaways,
        "Micro_Expectations": expectations,
        "Next_Inference_Hint_Micro_News": inference_hint
    }

def update_rating_json(analysis_results, ticker):
    """Update the Rating_Json files with the analysis results."""
    print(f"Updating Rating_Json for {ticker} with micro news analysis...")
    
    # Find the most recent rating JSON file for the ticker
    rating_files = [f for f in os.listdir(RATING_JSON_DIR) if f.endswith('.json')]
    
    if not rating_files:
        print(f"No Rating_Json files found in {RATING_JSON_DIR}")
        return False
    
    # Sort by creation time (most recent first)
    rating_files.sort(key=lambda f: os.path.getctime(os.path.join(RATING_JSON_DIR, f)), reverse=True)
    
    # Check each file until we find one with the matching ticker
    target_file = None
    for file in rating_files:
        file_path = os.path.join(RATING_JSON_DIR, file)
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                if data.get("Ticker") == ticker:
                    target_file = file_path
                    break
        except Exception as e:
            print(f"Error reading {file}: {str(e)}")
    
    if not target_file:
        print(f"No Rating_Json file found for ticker {ticker}")
        return False
    
    # Update the JSON file
    try:
        with open(target_file, 'r') as f:
            data = json.load(f)
        
        # Update the Micro field
        data["Micro"] = analysis_results
        
        with open(target_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Successfully updated {target_file} with micro news analysis")
        return True
    except Exception as e:
        print(f"Error updating {target_file}: {str(e)}")
        return False

def process_ticker(ticker, initial_days=3, max_days=14, min_accessible_articles=15):
    """Process news for a specific ticker and update Rating_Json files."""
    print(f"Starting news processing for {ticker}")
    
    articles = None
    current_days = initial_days
    accessible_articles_count = 0
    min_target_articles = min_accessible_articles * 3  # Target three times as many to account for extraction failures
    
    # Incrementally increase days until we have at least min_target_articles accessible articles or reach max_days
    while current_days <= max_days:
        print(f"Searching for news with timeframe of {current_days} days...")
        articles = get_news_json(ticker, current_days, min_target_articles)
        
        if not articles:
            print(f"No articles found with {current_days} days")
            current_days += 1
            continue
            
        # Count accessible articles (regardless of interval)
        accessible_articles_count = sum(1 for article in articles if article["accessible"] == 1)
        
        print(f"Found {accessible_articles_count} accessible articles with {current_days} days timeframe")
        
        # If we have enough articles or reached max days, break out of the loop
        if accessible_articles_count >= min_target_articles or current_days >= max_days:
            print(f"Stopping search: {'Found enough accessible articles' if accessible_articles_count >= min_target_articles else 'Reached maximum timeframe'}")
            break
            
        # Otherwise increase timeframe and try again
        current_days += 1
        print(f"Not enough accessible articles found. Increasing timeframe to {current_days} days.")
    
    if not articles:
        print(f"No news articles found for {ticker} after trying up to {max_days} days")
        return False
    
    print(f"Final result: {len(articles)} total articles ({accessible_articles_count} accessible) for {ticker}")
    
    # Skip the ranking step and directly process accessible articles
    accessible_articles = [article for article in articles if article["accessible"] == 1]
    print(f"Processing {len(accessible_articles)} accessible articles directly")
    
    # Get all accessible articles initially - scrape_articles_directly will handle the limiting
    cached_data = scrape_articles_directly(accessible_articles, ticker, min_accessible_articles)
    if not cached_data or cached_data == "No article content available":
        print(f"No article content could be extracted for {ticker}")
        return False
    
    # Save articles to file if in debug mode
    if DEBUG:
        debug_file_path = os.path.join(DEBUG_DIR, f"{ticker}_articles.txt")
        with open(debug_file_path, 'w', encoding='utf-8') as f:
            f.write(cached_data)
        print(f"DEBUG: Saved articles to {debug_file_path}")
    
    # Analyze the ticker news
    analysis_results = analyze_ticker_news(ticker, cached_data)
    
    # Update the Rating_Json files
    result = update_rating_json(analysis_results, ticker)
    
    return result

def process_all_rating_jsons(initial_days=3, max_days=14):
    """Process all tickers from Rating_Json files."""
    print("Processing all tickers from Rating_Json files...")
    
    # Get all rating JSON files
    rating_files = [f for f in os.listdir(RATING_JSON_DIR) if f.endswith('.json')]
    
    if not rating_files:
        print(f"No Rating_Json files found in {RATING_JSON_DIR}")
        return
    
    processed_tickers = set()
    success_count = 0
    
    for file in rating_files:
        file_path = os.path.join(RATING_JSON_DIR, file)
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                ticker = data.get("Ticker")
                
                if not ticker or ticker in processed_tickers:
                    continue
                
                print(f"\nProcessing ticker {ticker} from {file}")
                if process_ticker(ticker, initial_days, max_days):
                    success_count += 1
                
                processed_tickers.add(ticker)
                
        except Exception as e:
            print(f"Error processing {file}: {str(e)}")
    
    print(f"\nCompleted processing {len(processed_tickers)} tickers. Successfully updated {success_count} Rating_Json files.")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Process a specific ticker
        ticker = sys.argv[1].upper()
        initial_days = 3  # Default initial days
        max_days = 14     # Default maximum days
        
        if len(sys.argv) > 2:
            try:
                initial_days = int(sys.argv[2])
            except ValueError:
                print(f"Invalid initial days value: {sys.argv[2]}. Using default (3 days).")
                
        if len(sys.argv) > 3:
            try:
                max_days = int(sys.argv[3])
            except ValueError:
                print(f"Invalid max days value: {sys.argv[3]}. Using default (14 days).")
        
        print(f"Processing ticker {ticker} (initial timeframe: {initial_days} days, max: {max_days} days)")
        process_ticker(ticker, initial_days, max_days)
    else:
        # Process all tickers from Rating_Json files
        print("Processing all tickers from Rating_Json files")
        process_all_rating_jsons()
