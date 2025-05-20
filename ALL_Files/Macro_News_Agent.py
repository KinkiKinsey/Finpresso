import requests
import json
import pandas as pd
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
import seaborn as sns

import feedparser
import requests
from bs4 import BeautifulSoup
import time
import asyncio
import aiohttp

from datetime import datetime
import pandas as pd

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import pandas as pd
import time
from openai import OpenAI
import re

from os import read
import os
import inspect
import sys
from datetime import timedelta


RSS_CONCURRENCY = 4
PAGE_CONCURRENCY = 8

def deepseek_api_call(prompt, base_url="https://api.deepseek.com", model="deepseek-chat"):

    client = OpenAI(api_key='sk-43e9043c7ab8480393d34367f2ae997e', base_url=base_url)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are an financial report analyst as API agent"},
            {"role": "user", "content": prompt},
        ],
        stream=False
    )

    return response.choices[0].message.content
    

async def extract_news_content_async(session: aiohttp.ClientSession, url: str, sem: asyncio.Semaphore) -> str:
    """异步抓取网页并在线程池里用 BeautifulSoup 解析正文。"""
    async with sem:
        try:
            async with session.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10) as resp:
                html = await resp.text()
            loop = asyncio.get_running_loop()
            # 在后台线程里解析 HTML，以免阻塞事件循环
            content = await loop.run_in_executor(
                None,
                lambda: "\n".join(
                    p.get_text() for p in BeautifulSoup(html, "lxml").find_all("p")
                )
            )
            return content.strip() or "⚠ Unable to extract article content."
        except Exception as e:
            return f"⚠ Extraction failed: {e}"

def extract_news_content(url: str) -> str:
    """
    同步接口包装。内部启动一次性事件循环来跑 extract_news_content_async。
    使用时直接调用这个同步函数即可。
    """
    sem = asyncio.Semaphore(PAGE_CONCURRENCY)
    async def runner():
        async with aiohttp.ClientSession() as session:
            return await extract_news_content_async(session, url, sem)
    return asyncio.run(runner())


async def fetch_rss(session, name, url):
    """异步拉取 RSS 并返回 (name, feedparser.FeedParserDict)"""
    async with session.get(url, timeout=10) as resp:
        text = await resp.text()
    # feedparser.parse 对文本解析，占用 CPU，可放到线程池
    loop = asyncio.get_running_loop()
    parsed = await loop.run_in_executor(None, feedparser.parse, text)
    return name, parsed

async def fetch_article(session, entry, sem):
    """异步抓正文 + 在线程池里做 BeautifulSoup 解析"""
    async with sem:  # 限制并发量
        async with session.get(entry.link, timeout=10) as resp:
            html = await resp.text()
        loop = asyncio.get_running_loop()
        content = await loop.run_in_executor(
            None,
            lambda: "\n".join(p.get_text() for p in BeautifulSoup(html, "lxml").find_all("p"))
        )
        if not content.strip():
            content = "⚠ Unable to extract article content."
        return {
            "title": entry.title,
            "link": entry.link,
            "published": getattr(entry, "published", ""),
            "content": content.strip()
        }

def fetch_news(download=True):
    """
    同步接口：调用底层的异步实现。
    download=True 则把结果写到 full_economic_news.txt，
    否则返回 news_cache dict。
    """
    return asyncio.run(fetch_news_async(download))

async def fetch_news_async(download=True):
    ECONOMY_RSS_FEEDS = {
        "Yahoo Finance - Economy": "https://www.yahoo.com/news/rss/economy",
        "Google News - Tariffs": "https://news.google.com/rss/search?q=tariffs+trade&hl=en-US&gl=US&ceid=US:en",
        "Google News - Federal Reserve": "https://news.google.com/rss/search?q=Federal+Reserve&hl=en-US&gl=US&ceid=US:en",
        "Google News - Inflation": "https://news.google.com/rss/search?q=inflation&hl=en-US&gl=US&ceid=US:en",
        "CNBC Economy": "https://www.cnbc.com/id/20910258/device/rss/rss.html",
        "WSJ Economy": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
        "Reuters - Business & Economy": "https://www.reutersagency.com/feed/?best-topics=business-economy&post_type=best"
    }
    OUTPUT_FILE = "full_economic_news.txt"
    news_cache = {}
    counter = 0

    # 如果要 download，则后面统一写文件
    results_for_file = []

    semaphore_rss = asyncio.Semaphore(RSS_CONCURRENCY)
    semaphore_page = asyncio.Semaphore(PAGE_CONCURRENCY)

    async with aiohttp.ClientSession(headers={'User-Agent': 'Mozilla/5.0'}) as session:
        # 1) 并发拉 RSS
        rss_tasks = [
            asyncio.create_task(fetch_rss(session, name, url))
            for name, url in ECONOMY_RSS_FEEDS.items()
        ]
        for rss_task in asyncio.as_completed(rss_tasks):
            source_name, feed = await rss_task
            entries = feed.entries[:5]
            articles = []

            # 2) 并发拉正文
            page_tasks = [
                asyncio.create_task(fetch_article(session, entry, semaphore_page))
                for entry in entries
            ]
            for idx, page_task in enumerate(asyncio.as_completed(page_tasks), start=1):
                article = await page_task
                counter += 1
                articles.append(article)
                if download:
                    results_for_file.append((source_name, idx, article))
                else:
                    # 存到 cache
                    news_cache.setdefault(source_name, []).append(article)

    # 3) 写文件（如果需要）
    if download:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("📊 Full Economic & Political News Articles 📊\n\n")
            for source_name in ECONOMY_RSS_FEEDS:
                f.write(f"🔹 {source_name} 🔹\n\n")
                for src, idx, art in filter(lambda x: x[0]==source_name, results_for_file):
                    f.write(f"{idx}. {art['title']}\n")
                    f.write(f"   Link: {art['link']}\n")
                    f.write(f"   Published: {art['published']}\n\n")
                    f.write(f"{art['content']}\n\n")
        print(f"✅ Full news articles saved to {OUTPUT_FILE}")
        return None

    return news_cache

def fetch_economic_calendar():
    """Fetch economic calendar data for the next month from FMP API"""
    API_KEY = "9dfbbfa29d93f4793f246e8fb5ca5e74"
    
    # Calculate date range (today to 30 days from now)
    today = datetime.now().strftime('%Y-%m-%d')
    end_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    
    # FMP Economic Calendar API endpoint
    url = f"https://financialmodelingprep.com/api/v3/economic_calendar?from={today}&to={end_date}&apikey={API_KEY}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            print(f"Error fetching economic calendar: {response.status_code}")
            return []
    except Exception as e:
        print(f"Exception when fetching economic calendar: {str(e)}")
        return []

def format_economic_calendar(calendar_data, top_n=10):
    """Format economic calendar data into a readable report, only including top N most important events"""
    if not calendar_data:
        return "⚠ No economic calendar data available for the next month."
    
    # Filter and prioritize events
    high_impact_events = []
    medium_impact_events = []
    low_impact_events = []
    
    for event in calendar_data:
        impact = event.get('impact', '').lower()
        if impact == 'high':
            high_impact_events.append(event)
        elif impact == 'medium':
            medium_impact_events.append(event)
        else:
            low_impact_events.append(event)
    
    # Sort each impact level by date
    for events_list in [high_impact_events, medium_impact_events, low_impact_events]:
        events_list.sort(key=lambda x: x.get('date', ''))
    
    # Combine events in priority order (high → medium → low)
    prioritized_events = high_impact_events + medium_impact_events + low_impact_events
    
    # Take only the top N events
    top_events = prioritized_events[:top_n]
    
    # Format the report
    report = f"📅 TOP {top_n} IMPORTANT ECONOMIC DATA RELEASES 📅\n\n"
    
    # Group events by date
    events_by_date = {}
    for event in top_events:
        # Fix the date extraction to handle various formats
        date_str = event.get('date', '')
        # Extract just the date part (handle both T separator and space separator)
        if 'T' in date_str:
            date = date_str.split('T')[0]
        elif ' ' in date_str:
            date = date_str.split(' ')[0]
        else:
            date = date_str  # Use as is if no separator found
            
        if date not in events_by_date:
            events_by_date[date] = []
        events_by_date[date].append(event)
    
    # Sort dates
    for date in sorted(events_by_date.keys()):
        try:
            formatted_date = datetime.strptime(date, "%Y-%m-%d").strftime("%B %d, %Y")
        except ValueError:
            # If date parsing fails, use the original date string
            formatted_date = date
            
        report += f"📆 {formatted_date}\n"
        
        # Sort events by time for this date
        day_events = events_by_date[date]
        
        for event in day_events:
            country = event.get('country', '')
            event_name = event.get('event', '')
            
            # Handle time extraction with better error handling
            date_str = event.get('date', '')
            time = ""
            if 'T' in date_str:
                time_part = date_str.split('T')[1]
                time = time_part.split('+')[0] if '+' in time_part else time_part
            elif ' ' in date_str and len(date_str.split(' ')) > 1:
                time = date_str.split(' ')[1]
                
            impact = '🔴 High Impact' if event.get('impact') == 'High' else '🟡 Medium Impact' if event.get('impact') == 'Medium' else '🟢 Low Impact'
            
            report += f"  • {time} | {country}: {event_name} ({impact})\n"
            
            # Add previous, estimate and actual if available
            prev = event.get('previous', None)
            estimate = event.get('estimate', None)
            actual = event.get('actual', None)
            
            if prev is not None or estimate is not None or actual is not None:
                report += f"    [Previous: {prev}, Estimate: {estimate}, Actual: {actual}]\n"
        
        report += "\n"
    
    return report


def Get_Government_Political_Action(download=False, debug_mode = False ):
  ######## This is the main function of this tool ############
  ## Description: This function read all market expectation/dynamic/policy from the government / polotical side, and return and use LLM API to summarize all the action ############
  news_data = fetch_news(download=False)
  
  # Fetch economic calendar data first
  calendar_data = fetch_economic_calendar()
  economic_calendar_report = format_economic_calendar(calendar_data)
  
  prompt = f"""
    ## Prompt: You are an Economic Analyst reviewing the latest news articles. Base on the news Only Return me Below information:
    YOU Are analysting for the economic/federal reserve/president policy/ etc that impact the marcoeconomic
    read the text that report the economic/politcal/more national wise news, more marco news.
    YOu don read the part that about a stock/companies or micro terms in term of these. I want you be an maroeconomic reporter

    ###### Reports Informations be like  ######
    # Part1.  Keys takeaways of each economic/political news article.  (ex:who do what, what is annouced. For example: "Fed Reserve announced to increase interest rate by 0.25%")
    # Part2. What is the impact of the news on the economy? (ex: "The news is expected to increase the inflation rate")
    # Part3. What is the potential implication of the news on the stock market? (ex: "The stock market is expected to rise due to the news")
    ###### Reports Informations be like ######

    ############# Here is Format of the report ###########
    1. Events(Part1) +  Impact(Part2) + Impact on Stock(Part3)
    2. Events(Part1) +  Impact(Part2) + Impact on Stock(Part3)
    3. Events(Part1) +  Impact(Part2) + Impact on Stock(Part3)
    etc... add more if necessary

    # If currently, there is no much available news, you could always return No significant economic news currently as the response.

    here is the news:
    {news_data}"""

  financial_report = deepseek_api_call(prompt)
  cleaned_response_text = re.sub(r"```json\n|\n```", "", financial_report).strip()
  
  # Combine both reports
  combined_report = f"{cleaned_response_text}\n\n{'='*80}\n\n{economic_calendar_report}"
  
  if debug_mode:
    print(f"This is the expecation news:     {cleaned_response_text}")
    print(f"This is the economic calendar:    {economic_calendar_report}")
  if download:
    with open('Expectation(macro+political_new).txt', 'w') as file:
      file.write(combined_report)
  return combined_report

# === FILE HANDLING FUNCTIONS ===

def get_script_dir():
    """Get the directory where this script is located"""
    # Use the directory of this script file
    return os.path.dirname(os.path.abspath(__file__))

# Use the script directory instead of the current working directory
SCRIPT_DIR = get_script_dir()
CURRENT_DIR = SCRIPT_DIR  # Change this to use script dir
PARENT_DIR = os.path.dirname(CURRENT_DIR)

# Choose the macro files directory inside the Tool_Box folder
MACRO_FILES_DIR = os.path.join(SCRIPT_DIR, "Macro_Files")
# But different file names for the news agent
NEWS_REPORT_PATH = os.path.join(MACRO_FILES_DIR, "macro_news_report.txt")
NEWS_META_PATH = os.path.join(MACRO_FILES_DIR, "macro_news_report.meta")
MAX_AGE_HOURS = 24

def test_file_access(directory):
    """Test if we can create and access files in the given directory"""
    print(f"Testing file access in: {directory}")
    try:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            print(f"Created directory: {directory}")
        
        test_file_path = os.path.join(directory, "test_access.txt")
        with open(test_file_path, "w") as f:
            f.write("Test file access")
        print(f"Successfully wrote to test file: {test_file_path}")
        
        with open(test_file_path, "r") as f:
            content = f.read()
        print(f"Successfully read from test file: {test_file_path}, content: {content}")
        
        os.remove(test_file_path)
        print(f"Successfully deleted test file: {test_file_path}")
        
        return True
    except Exception as e:
        print(f"ERROR testing file access in {directory}: {str(e)}")
        return False

def is_report_recent(meta_path, max_age_hours=24):
    print(f"Checking if report is recent at path: {meta_path}")
    print(f"File exists: {os.path.exists(meta_path)}")
    
    if not os.path.exists(meta_path):
        print(f"Metadata file does not exist at: {meta_path}")
        return False
    
    with open(meta_path, "r") as f:
        try:
            content = f.read().strip()
            print(f"Meta file content: {content}")
            last_updated = float(content)
        except Exception as e:
            print(f"Failed to parse timestamp from metadata file: {str(e)}")
            return False
    
    last_time = datetime.fromtimestamp(last_updated)
    time_diff = datetime.now() - last_time
    print(f"Last report was generated {time_diff.total_seconds()/3600:.1f} hours ago")
    return time_diff < timedelta(hours=max_age_hours)

def save_report(report_text, report_path, meta_path):
    # Create the directory if it doesn't exist
    dir_path = os.path.dirname(report_path)
    print(f"Attempting to save to directory: {dir_path}")
    
    if not os.path.exists(dir_path):
        print(f"Creating directory: {dir_path}")
        os.makedirs(dir_path, exist_ok=True)
    
    print(f"Saving report to: {report_path}")
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_text)
        print(f"Successfully saved report file: {report_path}")
    except Exception as e:
        print(f"ERROR saving report: {str(e)}")
    
    print(f"Saving metadata to: {meta_path}")
    try:
        with open(meta_path, "w") as f:
            f.write(str(time.time()))
        print(f"Successfully saved metadata file: {meta_path}")
    except Exception as e:
        print(f"ERROR saving metadata: {str(e)}")
    
    # Verify files were created
    print(f"Report file exists after save: {os.path.exists(report_path)}")
    print(f"Meta file exists after save: {os.path.exists(meta_path)}")

def load_report(report_path):
    print(f"Loading report from: {report_path}")
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()
            print(f"Successfully loaded report, length: {len(content)} characters")
            return content
    except Exception as e:
        print(f"ERROR loading report: {str(e)}")
        return "Error loading report"

# === MAIN EXECUTION ===
if __name__ == "__main__":
    print(f"Python version: {sys.version}")
    print(f"Current working directory: {CURRENT_DIR}")
    print(f"Script directory: {SCRIPT_DIR}")
    print(f"Parent directory: {PARENT_DIR}")
    print(f"Selected macro files directory: {MACRO_FILES_DIR}")
    
    # Test file access in the directory we plan to use
    access_ok = test_file_access(MACRO_FILES_DIR)
    print(f"File access test result: {access_ok}")
    
    # Ensure the directory exists
    if not os.path.exists(MACRO_FILES_DIR):
        print(f"Creating Macro_Files directory at: {MACRO_FILES_DIR}")
        os.makedirs(MACRO_FILES_DIR, exist_ok=True)
    else:
        print(f"Macro_Files directory already exists at: {MACRO_FILES_DIR}")
    
    print(f"News report path: {NEWS_REPORT_PATH}")
    print(f"News metadata path: {NEWS_META_PATH}")
    print(f"News report file exists: {os.path.exists(NEWS_REPORT_PATH)}")
    print(f"News meta file exists: {os.path.exists(NEWS_META_PATH)}")
    
    if os.path.exists(NEWS_REPORT_PATH) and is_report_recent(NEWS_META_PATH, MAX_AGE_HOURS):
        print("📄 Recent news report found. Skipping regeneration.")
        macro_news_report = load_report(NEWS_REPORT_PATH)
    else:
        print("⏳ No recent news report found. Generating new one...")
        macro_news_report = Get_Government_Political_Action(download=False, debug_mode=False)
        print(f"Generation complete, news report length: {len(macro_news_report)} characters")
        save_report(macro_news_report, NEWS_REPORT_PATH, NEWS_META_PATH)
        
        # Double-check files were created
        print(f"FINAL CHECK - News report file exists: {os.path.exists(NEWS_REPORT_PATH)}")
        print(f"FINAL CHECK - News meta file exists: {os.path.exists(NEWS_META_PATH)}")

    print("✅ Loaded Macro News Report:\n")
    print(macro_news_report)