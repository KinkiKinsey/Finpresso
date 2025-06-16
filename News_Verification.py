# News_Verification.py  ─────────────────────────────────────────────────────────
# 依赖：pip install python-dotenv langchain openai youtube_transcript_api requests bs4
# 环境变量：DEEPSEEK_API_KEY  TAVILY_API_KEY  OPENAI_API_KEY

import asyncio, json, os, re, time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional
import logging
import datetime
import difflib

# ─── 第三方 ──────────────────────────────────────────────────────────
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from youtube_transcript_api import YouTubeTranscriptApi

# ─── LangChain / LangGraph ─────────────────────────────────────────
from langchain.tools import tool
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_deepseek import ChatDeepSeek
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch
from langgraph.prebuilt import create_react_agent

# ─── 环境变量 ───────────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# NOTE: Replace with your actual API keys or load from environment
DEEPSEEK_API_KEY = 'sk-43e9043c7ab8480393d34367f2ae997e'
TAVILY_API_KEY   = "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"
OPENAI_API_KEY   = "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"



# ─── 基础模型 & 搜索工具 ────────────────────────────────────────────
model = ChatDeepSeek(model="deepseek-chat", api_key=DEEPSEEK_API_KEY)
tavily_search_tool = TavilySearchResults(max_results=10, tavily_api_key=TAVILY_API_KEY, search_depth="advanced", topic="finance", time_range="month")


# ─── 结果结构体 ─────────────────────────────────────────────────────
class FilterStatus(Enum):
    PENDING     = "pending"
    PROCESSING  = "processing"
    PASSED      = "passed"
    FAILED      = "failed"
    SKIPPED     = "skipped"

@dataclass
class FilterResult:
    name    : str
    status  : FilterStatus
    result  : Dict[str, Any]
    details : str
    timestamp: float

@dataclass
class VerificationResult:
    statement       : str
    filters         : List[FilterResult]
    final_decision  : Optional[str]               = None
    final_reasoning : Optional[str]               = None
    reference_links : List[Dict[str, str]] | None = None

# ─── WebSocket 回调 ────────────────────────────────────────────────
verification_callbacks: Dict[str, Any] = {}
def register_callback(sid: str, cb): verification_callbacks[sid] = cb
def unregister_callback(sid: str):    verification_callbacks.pop(sid, None)


async def notify_progress(sid: str, fname: str, status: FilterStatus,
                          details: str = "", result: Dict|None = None):
    if sid in verification_callbacks:
        try:
            await verification_callbacks[sid](fname, status, details, result)
        except Exception as e:
            logger.error(f"Error in notify_progress: {e}")

# ─── 同步 → 线程池 包装 ────────────────────────────────────────────
def deepseek_llm_sync(prompt: str, hist: List[Dict]|None = None):
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    msgs = hist[:] if hist else []
    msgs.append({"role": "user", "content": prompt})
    out  = client.chat.completions.create(model="deepseek-chat", messages=msgs)
    content = out.choices[0].message.content
    return {"content": content, "history": msgs+[{"role":"assistant","content":content}]}

async def deepseek_llm(prompt: str, hist: List[Dict]|None = None):
    return await asyncio.to_thread(deepseek_llm_sync, prompt, hist)

async def tavily_search(q: str, k: int = 3, topic: str = "finance", time_range: str = "month", include_domains: List[str] = []):
    """Fixed tavily search with better error handling and timeout, now supports time_range"""
    try:
        print("[DEBUG] tavily_search: Starting search with query:", q)
        tool = TavilySearch(max_results=k, topic=topic, tavily_api_key=TAVILY_API_KEY, time_range=time_range, include_domains=include_domains)
        print("[DEBUG] tavily_search: Created TavilySearch tool")
        
        # Try the tool first
        raw_result = await asyncio.wait_for(
            asyncio.to_thread(tool.invoke, {"query": q}),
            timeout=30.0  # 30 second timeout per search
        )
        print("[DEBUG] tavily_search: Raw result type:", type(raw_result))
        print("[DEBUG] tavily_search: Raw result:", repr(raw_result)[:500])
        
        # If the tool returned a string (error message), try using the API wrapper directly
        if isinstance(raw_result, str):
            print("[DEBUG] tavily_search: Tool returned string, trying API wrapper directly")
            if hasattr(tool, 'api_wrapper'):
                raw_result = tool.api_wrapper.raw_results(q)
                print("[DEBUG] tavily_search: API wrapper response type:", type(raw_result))
                print("[DEBUG] tavily_search: API wrapper response:", repr(raw_result)[:500])
            else:
                print("[DEBUG] tavily_search: No API wrapper available, returning empty results")
                return {"results": []}
        
        # If result is a tuple (from TavilySearchResults), take the first element
        if isinstance(raw_result, tuple):
            print("[DEBUG] tavily_search: Converting tuple result to first element")
            raw_result = raw_result[0]
            
        # Ensure result is a dictionary with a "results" key
        if not isinstance(raw_result, dict):
            print("[DEBUG] tavily_search: Result is not a dictionary, returning empty results")
            return {"results": []}
            
        if "results" not in raw_result:
            print("[DEBUG] tavily_search: Result missing 'results' key, returning empty results")
            return {"results": []}
            
        return raw_result
    except asyncio.TimeoutError:
        logger.error(f"Tavily search timeout for query: {q}")
        return {"results": []}
    except Exception as e:
        logger.error(f"Tavily search error: {e}")
        print("[DEBUG] tavily_search: Error details:", str(e))
        return {"results": []}

async def fetch_yt_transcript(vid: str, sid: str = None):
    try:
        # Add timeout to transcript fetch
        trans = await asyncio.wait_for(
            asyncio.to_thread(YouTubeTranscriptApi.get_transcript, vid),
            timeout=30.0  # 30 second timeout for transcript
        )
        if sid:
            await notify_progress(sid, "Filter 2: Live Stream or Video Check", FilterStatus.PROCESSING, "Transcript fetched successfully")
        return trans
    except asyncio.TimeoutError:
        logger.error("YouTube transcript fetch timeout")
        if sid:
            await notify_progress(sid, "Filter 2: Live Stream or Video Check", FilterStatus.FAILED, "Transcript fetch timeout")
        raise
    except Exception as e:
        logger.error(f"YouTube transcript fetch error: {e}")
        if sid:
            await notify_progress(sid, "Filter 2: Live Stream or Video Check", FilterStatus.FAILED, f"Transcript error: {str(e)}")
        raise

# ─── JSON 抽取 ─────────────────────────────────────────────────────
def extract_json_block(txt: str) -> dict:
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", txt)
    js = m.group(1) if m else txt
    return json.loads(js.strip())

# ─── Agent 1  Reason Agent ─────────────────────────────────────────
async def async_reason_agent(statement: str, sid: str):
    await notify_progress(sid, "Filter 3.a: Inference Point", FilterStatus.PROCESSING, "Analyzing structure…")
    # DEBUG: Print the LLM prompt and response
    print("[DEBUG] async_reason_agent: statement:", statement)
    llm_prompt = f"""
Analyze the following statement and create a hierarchical tree structure for market impact analysis.

You are a news/fact-checking agent. Your analysis feeds investors' decision-making in stock/crypto markets.
Think about how the news or fact affects the market (noise vs real impact).

Create a tree structure with the following hierarchy:
1. Strategy/Theme (main market impact)
2. Analysis Levels (branches):
   - Macro (nation/global policy, central bank)
   - Fundamental (company-specific, financials)
   - Price (market microstructure, liquidity)
3. For each level, identify specific data points needed for verification

Output JSON strictly:
{{
  "strategy": {{
    "name": "Main market impact theme",
    "description": "Brief explanation of the strategy/theme"
  }},
  "analysis_levels": {{
    "macro": {{
      "name": "Macro-level impact",
      "data_points": [
        {{
          "name": "Specific macro data point",
          "time_interval": "Required time range",
          "purpose": "Why this data point matters",
          "data_source": "Source type"
        }}
      ]
    }},
    "fundamental": {{
      "name": "Fundamental-level impact",
      "data_points": [
        {{
          "name": "Specific fundamental data point",
          "time_interval": "Required time range",
          "purpose": "Why this data point matters",
          "data_source": "Source type"
        }}
      ]
    }},
    "price": {{
      "name": "Price-level impact",
      "data_points": [
        {{
          "name": "Specific price data point",
          "time_interval": "Required time range",
          "purpose": "Why this data point matters",
          "data_source": "Source type"
        }}
      ]
    }}
  }},
  "end_goal": "One sentence summarizing what the data will confirm"
}}

Statement:
{statement}

Your output MUST be valid JSON and nothing else. Do not include any explanation or markdown, just the JSON object.
You are a API call, you answer will directly be used by the next agent, hence you do not need to include any explanation or markdown, just the JSON object.
""".strip()
    try:
        resp   = await asyncio.wait_for(deepseek_llm(llm_prompt), timeout=120)
        print("[DEBUG] async_reason_agent: LLM response:", resp)
        result = extract_json_block(resp["content"])
        print("[DEBUG] async_reason_agent: Parsed reason JSON:", result)
        await notify_progress(sid, "Filter 3.a: Inference Point", FilterStatus.PASSED, "Structure OK", result)
        return result
    except Exception as e:
        err = {"error": str(e)}
        await notify_progress(sid, "Filter 3.a: Inference Point", FilterStatus.FAILED, str(e), err)
        return err

# ─── Agent 2  Online Data Agent (FIXED) ────────────────────────────────────
async def async_online_data_agent(reason_json: dict, sid: str):
    await notify_progress(sid, "Filter 3.b: Inference Evidence", FilterStatus.PROCESSING, "Gathering evidence…")
    print("[DEBUG] async_online_data_agent: reason_json:", reason_json)
    
    # Initialize search_tasks list
    search_tasks = []
    
    # Extract data points from analysis levels
    data_points = []
    for level in reason_json.get("analysis_levels", {}).values():
        if isinstance(level, dict) and "data_points" in level:
            data_points.extend(level["data_points"])
    
    # Create search tasks for each data point
    for data_point in data_points[:5]:  # Limit to 5 searches
        if not isinstance(data_point, dict):
            continue
        q = data_point.get("name")
        if not q:
            continue
        purpose = data_point.get("purpose", "")
        time_interval = data_point.get("time_interval", "")
        
        # Create search query
        search_query = f"{q}. Purpose: {purpose}. Time: {time_interval}" if purpose else f"{q}. Time: {time_interval}"
        task = tavily_search(search_query, 2, "finance", time_range="month")
        search_tasks.append(task)
    
    print("[DEBUG] async_online_data_agent: search_tasks:", search_tasks)
    
    if not search_tasks:
        await notify_progress(sid, "Filter 3.b: Inference Evidence", FilterStatus.PASSED, "No searches needed", {})
        return {}
    try:
        search_results = await asyncio.wait_for(
            asyncio.gather(*search_tasks, return_exceptions=True),
            timeout=60.0
        )
        # Ensure every result is a dict to prevent 'str' object has no attribute 'get'
        search_results = [ensure_dict(r) for r in search_results]
        output: Dict[str, Any] = {}
        for i, (data_point, result) in enumerate(zip(data_points, search_results)):
            # Use the data point's name as the key, or fallback to index
            key = data_point.get('name') if isinstance(data_point, dict) and 'name' in data_point else f'data_point_{i}'
            if isinstance(result, Exception):
                output[key] = []
            else:
                safe_results = []
                for r in result.get("results", []) if isinstance(result, dict) else []:
                    if isinstance(r, dict):
                        safe_results.append({
                            "title": r.get("title", ""),
                            "summary": r.get("content", "")[:500],
                            "url": r.get("url", "")
                        })
                    else:
                        print(f"[WARNING] Source Searching: result is not a dict: {r}")
                        safe_results.append({
                            "title": "Non-dict result",
                            "summary": str(r)[:500],
                            "url": ""
                        })
                output[key] = safe_results
            await notify_progress(
                sid, "Filter 3.b: Inference Evidence", FilterStatus.PROCESSING,
                f"{i+1}/{len(data_points)} searches completed"
            )
        await notify_progress(sid, "Filter 3.b: Inference Evidence", FilterStatus.PASSED, "Evidence collected", output)
        return output
    except asyncio.TimeoutError:
        await notify_progress(sid, "Filter 3.b: Inference Evidence", FilterStatus.FAILED, "Search timeout", {"error": "timeout"})
        return {"error": "Search timeout"}
    except Exception as e:
        await notify_progress(sid, "Filter 3.b: Inference Evidence", FilterStatus.FAILED, str(e), {"error": str(e)})
        return {"error": str(e)}

# ─── Agent 3  Decision Agent ───────────────────────────────────────
async def async_decision_agent(statement: str, evidence: dict, sid: str):
    await notify_progress(sid, "Filter 3.c: Feasibility Check", FilterStatus.PROCESSING, "Making decision…")
    
    # Handle case where evidence might contain error
    if isinstance(evidence, dict) and "error" in evidence:
        await notify_progress(sid, "Filter 3.c: Feasibility Check", FilterStatus.FAILED, "No evidence available")
        return {
            "decision": "Noise for Investment",
            "reasoning": "Unable to gather sufficient evidence due to search errors."
        }
    
    # If evidence contains verifier output, extract its reason for the prompt
    verifier_info = ""
    if isinstance(evidence, dict) and "verifier" in evidence:
        v = evidence["verifier"]
        if isinstance(v, dict):
            if v.get("reason"):
                verifier_info = f"Verifier Agent reason: {v['reason']}"
            elif v.get("error"):
                verifier_info = f"Verifier Agent error: {v['error']}"
            elif v.get("content"):
                verifier_info = f"Verifier Agent content: {v['content']}"
    
    ev_text = "\n\n".join(
        f"Title: {r['title']}\nURL: {r['url']}\nSummary: {r['summary']}"
        for lst in evidence.get("evidence", {}).values() if isinstance(lst, list)
        for r in lst
    )[:12000]

    prompt = f"""
You are **Decision Agent** advising investors on factual reliability.

================================================================
STATEMENT
================================================================
{statement}

================================================================
EVIDENCE  (from previous filters)
================================================================
{ev_text if ev_text else "No evidence available"}

{verifier_info}

================================================================
✦✦ HARD RULES — apply BEFORE any reasoning ✦✦
================================================================
If the Verifier Agent failed, use the provided reason or error message to explain why the claim could not be verified. Be specific and informative. If the Evidence section is empty, says "No evidence available", or consists only of error / timeout messages →  return Json with only the following two keys:

{{
  "decision": "Noise for Investment",
  "reasoning": "Unable to gather sufficient evidence."
}}

================================================================
If NONE of the hard-rule conditions fire, proceed:

• Evaluate the quality & consistency of the evidence.  
• ≤ 150-word concise reasoning.  
• Return JSON with only the following two keys:

{{
  "decision": "Not Noise for Investment" | "Noise for Investment",
  "reasoning": "<your explanation ≤150 words>"
}}
Your output MUST be valid JSON and nothing else. Do not include any explanation or markdown, just the JSON object.
You are a API call, you answer will directly be used by the next agent, hence you do not need to include any explanation or markdown, just the JSON object.
""".strip()

    try:
        resp   = await asyncio.wait_for(deepseek_llm(prompt), timeout=150)
        result = extract_json_block(resp["content"])
        status = (FilterStatus.PASSED if result.get("decision", "").strip().lower() == "not noise for investment"
                  else FilterStatus.FAILED)
        await notify_progress(sid, "Filter 3.c: Feasibility Check", status, result.get("reasoning", ""), result)
        return result
    except Exception as e:
        err = {"error": str(e)}
        await notify_progress(sid, "Filter 3.c: Feasibility Check", FilterStatus.FAILED, str(e), err)
        return err

# ─── Agent 0  Verifier Agent ───────────────────────────────────────


credit_list = [
    # Major News Agencies
    "bbc.com/news",
    "reuters.com",
    "apnews.com",
    "aljazeera.com",
    "afp.com",
    
    # Financial News Sources
    "bloomberg.com",
    "wsj.com",
    "ft.com",
    "cnbc.com",
    "finance.yahoo.com",
    "forbes.com",
    "investopedia.com",
    "marketwatch.com",
    "barrons.com",
    "morningstar.com",
    "seekingalpha.com",
    "businessinsider.com",
    "fortune.com",
    
    # General News with Business Sections
    "economist.com",
    "nytimes.com",
    "washingtonpost.com",
    "npr.org",
    "npr.org/sections/business",
    "pbs.org/newshour",
    "politico.com",
    
    # Fact-Checking Sources
    "snopes.com",
    "politifact.com",
    "factcheck.org",
    "mediabiasfactcheck.com",
    "leadstories.com",
    "factcheck.afp.com",
    "reuters.com/fact-check"
]

verifier_agent = create_react_agent(
    model,
    tools=[tavily_search_tool],
    name="verifier_agent",
    prompt="""
# Verifier Agent

Stage 1: Find original credible source for the claim. If none → UNVERIFIABLE  
Stage 2: Compare with claim, output one of FAITHFUL / MISLEADING / UNVERIFIABLE.



Output:
Return a valid JSON object with the following keys:
{
  "source": {"url": "...", "credibility": "...", "date": "..."},
  "analysis": "...",
  "verdict": "FAITHFUL" | "MISLEADING" | "UNVERIFIABLE",
  "reason": "..."
}
If the claim is unverifiable or the agent fails, set 'verdict' to 'UNVERIFIABLE' and provide a clear explanation in the 'reason' field (e.g., 'No credible source found', 'Claim is too vague', 'Contradictory evidence', etc.).

#### Important !!!
There is a direct/strictly reason for the The Claim is unverifiable: Statement is not explicitly/ close meaning is explicitly not mention in the source.
hence if the statement is not explicitly/ close meaning is explicitly not mention in the source, you need!!! to not pass, else you could pass.
######
Your output MUST be valid JSON and nothing else. Do not include any explanation or markdown, just the JSON object.
You are a API call, you answer will directly be used by the next agent, hence you do not need to include any explanation or markdown, just the JSON object.
"""
)

async def async_verifier_agent(statement: str, sid: str):
    await notify_progress(sid, "Filter 1: Source Check", FilterStatus.PROCESSING, "Verifying text source…")
    try:
        print("[DEBUG] Filter 1: Starting tavily search...")
        search_result = await tavily_search(
            statement,
            k=10,
            topic="finance",
            time_range="month",
            include_domains=credit_list
        )
        # Ensure the result is a dictionary
        search_result = ensure_dict(search_result)
        print("[DEBUG] Filter 1: Search result type:", type(search_result))
        print("[DEBUG] Filter 1: Search result keys:", search_result.keys() if isinstance(search_result, dict) else "Not a dict")
        
        # Check if there are any results
        results = search_result.get("results", [])
        print("[DEBUG] Filter 1: Results type:", type(results))
        print("[DEBUG] Filter 1: Results length:", len(results))
        
        for idx, r in enumerate(results):
            print(f"[DEBUG] Filter 1: Result[{idx}] type: {type(r)}")
            print(f"[DEBUG] Filter 1: Result[{idx}] value: {repr(r)[:200]}")
            if isinstance(r, dict):
                print(f"[DEBUG] Filter 1: Result[{idx}] keys: {r.keys()}")
            else:
                print(f"[DEBUG] Filter 1: Result[{idx}] is not a dict!")
        
        # Only pass if at least one result is from a credit domain
        def is_credit_source(url):
            return any(domain in url for domain in credit_list)
        
        credit_results = []
        for r in results:
            if not isinstance(r, dict):
                print(f"[DEBUG] Filter 1: Skipping non-dict result: {type(r)}")
                continue
            url = r.get("url", "")
            if is_credit_source(url):
                credit_results.append(r)
                print(f"[DEBUG] Filter 1: Found credit source: {url}")
        
        if not credit_results:
            err = {"content": f"No credible news result found for '{statement}'.", "passed": False}
            await notify_progress(sid, "Filter 1: Source Check", FilterStatus.FAILED, err["content"], err)
            return err
            
        content = json.dumps({"results": credit_results})
        await notify_progress(sid, "Filter 1: Source Check", FilterStatus.PASSED, "Credible source found", {"content": content, "passed": True})
        return {"content": content, "passed": True}
    except asyncio.TimeoutError:
        err = {"error": "Verification timeout"}
        await notify_progress(sid, "Filter 1: Source Check", FilterStatus.FAILED, "Timeout", err)
        return err
    except Exception as e:
        err = {"error": str(e)}
        await notify_progress(sid, "Filter 1: Source Check", FilterStatus.FAILED, str(e), err)
        return err

# ─── Video Verifier (可选) ─────────────────────────────────────────
video_verifier_agent = create_react_agent(
    model, tools=[], name="video_verifier_agent",
    prompt="""
Locate the claim in YouTube transcript, show context and analysis.

Output:
Return a valid JSON object with the following keys:
{
  "time_location": "...",
  "context": "...",
  "analysis": "..."
}
Your output MUST be valid JSON and nothing else. Do not include any explanation or markdown, just the JSON object.
You are a API call, you answer will directly be used by the next agent, hence you do not need to include any explanation or markdown, just the JSON object.
"""
)

def extract_yid(url: str) -> Optional[str]:
    m = re.search(r"(?:youtu\\.be/|v=|embed/|shorts/)([A-Za-z0-9_-]{11})", url)
    return m.group(1) if m else None

async def search_youtube(statement: str):
    try:
        # Add timeout to YouTube search
        sr = await asyncio.wait_for(
            tavily_search(f"youtube video about {statement}", 1, "news", time_range="month"),
            timeout=30.0  # 30 second timeout for search
        )
        for r in sr.get("results", []):
            vid = extract_yid(r.get("url", ""))
            if vid:
                return vid, r.get("title", ""), r.get("content", ""), r.get("url", "")
        return None, "", "", ""
    except asyncio.TimeoutError:
        logger.error("YouTube search timeout")
        return None, "", "", ""
    except Exception as e:
        logger.error(f"YouTube search error: {e}")
        return None, "", "", ""

async def async_video_verifier(statement: str, sid: str):
    await notify_progress(sid, "Filter 2: Live Stream or Video Check", FilterStatus.PROCESSING, "Searching YouTube…")
    
    try:
        # Search for video with timeout
        vid, title, content, url = await search_youtube(statement)
        if not vid:
            await notify_progress(sid, "Filter 2: Live Stream or Video Check", FilterStatus.FAILED, "No relevant video found")
            return {"error": "No video", "passed": False}
            
        await notify_progress(sid, "Filter 2: Live Stream or Video Check", FilterStatus.PROCESSING, f"Found video: {title}")
        
        # Fetch transcript with timeout and progress updates
        try:
            trans = await fetch_yt_transcript(vid, sid)
        except Exception as e:
            await notify_progress(sid, "Filter 2: Live Stream or Video Check", FilterStatus.FAILED, f"Failed to get transcript: {str(e)}")
            return {"error": f"Transcript error: {str(e)}", "passed": False}
            
        # Process transcript in chunks to avoid memory issues
        chunk_size = 50  # Process 50 segments at a time
        txt_chunks = []
        for i in range(0, min(len(trans), 200), chunk_size):  # Limit to first 200 segments
            chunk = trans[i:i + chunk_size]
            txt_chunks.append("\n".join(f"[{round(t['start'],2)}] {t['text']}" for t in chunk))
            await notify_progress(sid, "Filter 2: Live Stream or Video Check", FilterStatus.PROCESSING, 
                                f"Processing transcript: {i+len(chunk)}/{min(len(trans), 200)} segments")
        
        txt = "\n".join(txt_chunks)
        
        # Run video agent with timeout
        try:
            await notify_progress(sid, "Filter 2: Live Stream or Video Check", FilterStatus.PROCESSING, "Analyzing video content...")
            resp = await asyncio.wait_for(
                asyncio.to_thread(video_verifier_agent.invoke,
                                {"messages":[{"role":"user",
                                            "content":f"statement:{statement}\\ntranscript:\\n{txt}"}]}),
                timeout=60.0  # Reduced timeout to 60 seconds
            )
            res = resp["messages"][-1].content
            await notify_progress(sid, "Filter 2: Live Stream or Video Check", FilterStatus.PASSED,
                                f"Video analyzed: {title}",
                                {"content": res, "video_url": url, "video_title": title})
            return {"content": res, "video_url": url, "video_title": title, "passed": True}
            
        except asyncio.TimeoutError:
            err = {"error": "Video analysis timeout"}
            await notify_progress(sid, "Filter 2: Live Stream or Video Check", FilterStatus.FAILED, "Analysis timeout", err)
            return err
            
    except Exception as e:
        err = {"error": str(e)}
        await notify_progress(sid, "Filter 2: Live Stream or Video Check", FilterStatus.FAILED, str(e), err)
        return err

# ─── 主 pipeline ──────────────────────────────────────────────────
async def verify_statement(statement: str, sid: str, use_video: bool = False) -> VerificationResult:
    filters: List[FilterResult] = []
    
    logger.info(f"Starting verification for statement: {statement[:50]}... (use_video={use_video})")

    # Verifier Agent
    ver = await async_verifier_agent(statement, sid)
    filters.append(FilterResult("Filter 1: Source Check",
                                FilterStatus.PASSED if ver.get("passed") else FilterStatus.FAILED,
                                ver, ver.get("content", ""), time.time()))

    # Video Verifier - Only run if explicitly requested
    if use_video is True:
        logger.info("Running Video Verifier (use_video=True)")
        vid = await async_video_verifier(statement, sid)
        filters.append(FilterResult("Filter 2: Live Stream or Video Check",
                                    FilterStatus.PASSED if vid.get("passed") else FilterStatus.FAILED,
                                    vid, vid.get("content", vid.get("error","")), time.time()))
    else:
        logger.info("Skipping Video Verifier (use_video=False)")
        # Add skipped status for Video Verifier
        await notify_progress(sid, "Filter 2: Live Stream or Video Check", FilterStatus.SKIPPED, "Video analysis not requested")
        filters.append(FilterResult("Filter 2: Live Stream or Video Check", 
                                    FilterStatus.SKIPPED, 
                                    {"skipped": True}, 
                                    "Video analysis not requested", 
                                    time.time()))

    # Inference Points (was Reason Agent)
    reason = await async_reason_agent(statement, sid)
    filters.append(FilterResult("Filter 3.a: Inference Point",
                                FilterStatus.PASSED if reason.get("end_goal", "").strip().lower() == "likely to happen"
                                else FilterStatus.FAILED,
                                reason, reason.get("end_goal", reason.get("error","")), time.time()))
    if "error" in reason:
        return VerificationResult(statement, filters, "Analysis Failed", "Reason agent failed")

    # Source Searching (was Online Data Agent)
    evidence = await async_online_data_agent(reason, sid)
    filters.append(FilterResult("Filter 3.b: Inference Evidence", 
                                FilterStatus.PASSED if "error" not in evidence else FilterStatus.FAILED,
                                evidence, f"{len(evidence)} keys" if "error" not in evidence else evidence.get("error", ""),
                                time.time()))

    # Always call Decision Agent, even if Verifier Agent failed or evidence has error
    decision_input = {
        "verifier": ver,
        "evidence": evidence
    }
    decision = await async_decision_agent(statement, decision_input, sid)
    filters.append(FilterResult("Filter 3.c: Feasibility Check",
                                FilterStatus.PASSED if decision.get("decision", "").strip().lower() == "likely to happen" else FilterStatus.FAILED,
                                decision, decision.get("reasoning", decision.get("error","")), time.time()))

    # Extract reference links from evidence
    reference_links = []
    if isinstance(evidence, dict) and "error" not in evidence:
        for key, results in evidence.items():
            if isinstance(results, list):
                for r in results[:2]:  # Take top 2 results per key
                    if r.get("url"):
                        reference_links.append({
                            "reason": f"{key}: {r.get('title', '')}",
                            "url": r.get("url", "")
                        })

    return VerificationResult(
        statement       = statement,
        filters         = filters,
        final_decision  = decision.get("decision"),
        final_reasoning = decision.get("reasoning"),
        reference_links = reference_links
    )

def get_current_week_range():
    today = datetime.date.today()
    start = today - datetime.timedelta(days=today.weekday())  # Monday
    end = start + datetime.timedelta(days=6)  # Sunday
    return start, end

async def run_verifier():
    statement = "Donald Trump said he loves Xi Jinping."
    sid = "test-session-001"  # Any string, used for progress callbacks
    result = await async_verifier_agent(statement, sid)
    print(result)

def ensure_dict(obj):
    if isinstance(obj, dict):
        return obj
    if isinstance(obj, str):
        try:
            return json.loads(obj)
        except Exception:
            return {"error": "Output was not valid JSON", "raw": obj}
    return {"error": "Output was not a dict or JSON string", "raw": str(obj)}

if __name__ == "__main__":
    asyncio.run(run_verifier())