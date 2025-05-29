# News_Verification.py  ─────────────────────────────────────────────────────────
# 依赖：pip install python-dotenv langchain openai youtube_transcript_api requests bs4
# 环境变量：DEEPSEEK_API_KEY  TAVILY_API_KEY  OPENAI_API_KEY

import asyncio, json, os, re, time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional
import logging

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
model = ChatOpenAI(model="gpt-4o", openai_api_key=OPENAI_API_KEY)
tavily_search_tool = TavilySearchResults(max_results=10, tavily_api_key=TAVILY_API_KEY)

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

async def tavily_search(q: str, k: int = 3, topic: str = "news"):
    """Fixed tavily search with better error handling and timeout"""
    try:
        tool = TavilySearch(max_results=k, topic=topic, tavily_api_key=TAVILY_API_KEY)
        # Add timeout to prevent hanging
        result = await asyncio.wait_for(
            asyncio.to_thread(tool.invoke, {"query": q}),
            timeout=30.0  # 30 second timeout per search
        )
        return result
    except asyncio.TimeoutError:
        logger.error(f"Tavily search timeout for query: {q}")
        return {"results": []}
    except Exception as e:
        logger.error(f"Tavily search error: {e}")
        return {"results": []}

async def fetch_yt_transcript(vid: str):
    return await asyncio.to_thread(YouTubeTranscriptApi.get_transcript, vid)

# ─── JSON 抽取 ─────────────────────────────────────────────────────
def extract_json_block(txt: str) -> dict:
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", txt)
    js = m.group(1) if m else txt
    return json.loads(js.strip())

# ─── Agent 1  Reason Agent ─────────────────────────────────────────
async def async_reason_agent(statement: str, sid: str):
    await notify_progress(sid, "Reason Agent", FilterStatus.PROCESSING, "Analyzing structure…")
    llm_prompt = f"""
Analyze the following statement and output a JSON with the data needed to verify its structural feasibility.

You are a news/fact-checking agent. Your analysis feeds investors' decision-making in stock/crypto markets.
Think about how the news or fact affects the market (noise vs real impact).

Classify analysis level:
- Macro (nation/global policy, central bank)
- Fundamental (company-specific, financials)
- Price (market microstructure, liquidity)

Identify 1-3 critical data objects (keep it concise). For each give:
- name
- time_interval
- purpose
- data_source (Macro / Fundamental / Price)

End with an "end_goal": one sentence of what the data will confirm.

Statement:
{statement}

Output JSON strictly:
{{
  "data_requirements": {{
    "Object1": {{
      "name": "...",
      "time_interval": "...",
      "purpose": "...",
      "data_source": "Macro|Fundamental|Price"
    }},
    "Baseline Object": {{
      "name": "Check internet mention or fact existence"
    }}
  }},
  "end_goal": "..."
}}
""".strip()
    try:
        resp   = await asyncio.wait_for(deepseek_llm(llm_prompt), timeout=120)
        result = extract_json_block(resp["content"])
        await notify_progress(sid, "Reason Agent", FilterStatus.PASSED, "Structure OK", result)
        return result
    except Exception as e:
        err = {"error": str(e)}
        await notify_progress(sid, "Reason Agent", FilterStatus.FAILED, str(e), err)
        return err

# ─── Agent 2  Online Data Agent (FIXED) ────────────────────────────────────
async def async_online_data_agent(reason_json: dict, sid: str):
    """Fixed Online Data Agent with concurrent searches and better error handling"""
    await notify_progress(sid, "Online Data Agent", FilterStatus.PROCESSING, "Gathering evidence…")
    
    output: Dict[str, Any] = {}
    reqs = reason_json.get("data_requirements", {})
    
    # Limit number of searches to prevent overload
    max_searches = min(len(reqs), 5)  # Max 5 concurrent searches
    
    # Create search tasks
    search_tasks = []
    search_keys = []
    
    for i, (key, obj) in enumerate(list(reqs.items())[:max_searches]):
        q = obj.get("name")
        if not q:
            continue
            
        purpose = obj.get("purpose", "")
        search_query = f"{q}. Purpose: {purpose}" if purpose else q
        
        # Create search task with its own timeout
        task = tavily_search(search_query, 2, "finance")
        search_tasks.append(task)
        search_keys.append(q)
    
    if not search_tasks:
        await notify_progress(sid, "Online Data Agent", FilterStatus.PASSED, "No searches needed", {})
        return {}
    
    try:
        # Run all searches concurrently with overall timeout
        search_results = await asyncio.wait_for(
            asyncio.gather(*search_tasks, return_exceptions=True),
            timeout=60.0  # 60 second overall timeout
        )
        
        # Process results
        for i, (key, result) in enumerate(zip(search_keys, search_results)):
            if isinstance(result, Exception):
                logger.error(f"Search error for '{key}': {result}")
                output[key] = []
            else:
                output[key] = [
                    {
                        "title": r.get("title", ""),
                        "summary": r.get("content", "")[:500],  # Limit summary length
                        "url": r.get("url", "")
                    }
                    for r in result.get("results", [])[:3]  # Limit to 3 results per search
                ]
            
            # Update progress
            await notify_progress(
                sid, "Online Data Agent", FilterStatus.PROCESSING,
                f"{i+1}/{len(search_keys)} searches completed"
            )
        
        await notify_progress(sid, "Online Data Agent", FilterStatus.PASSED, "Evidence collected", output)
        return output
        
    except asyncio.TimeoutError:
        logger.error("Online Data Agent timeout")
        await notify_progress(sid, "Online Data Agent", FilterStatus.FAILED, "Search timeout", {"error": "timeout"})
        return {"error": "Search timeout"}
    except Exception as e:
        logger.error(f"Online Data Agent error: {e}")
        await notify_progress(sid, "Online Data Agent", FilterStatus.FAILED, str(e), {"error": str(e)})
        return {"error": str(e)}

# ─── Agent 3  Decision Agent ───────────────────────────────────────
async def async_decision_agent(statement: str, evidence: dict, sid: str):
    await notify_progress(sid, "Decision Agent", FilterStatus.PROCESSING, "Making decision…")
    
    # Handle case where evidence might contain error
    if isinstance(evidence, dict) and "error" in evidence:
        await notify_progress(sid, "Decision Agent", FilterStatus.FAILED, "No evidence available")
        return {
            "decision": "Not Likely to Happen",
            "reasoning": "Unable to gather sufficient evidence due to search errors."
        }
    
    ev_text = "\n\n".join(
        f"Title: {r['title']}\nURL: {r['url']}\nSummary: {r['summary']}"
        for lst in evidence.values() if isinstance(lst, list)
        for r in lst
    )[:12000]

    prompt = prompt = f"""
You are **Decision Agent** advising investors on factual reliability.

================================================================
STATEMENT
================================================================
{statement}

================================================================
EVIDENCE  (from previous filters)
================================================================
{ev_text if ev_text else "No evidence available"}

================================================================
✦✦ HARD RULES — apply BEFORE any reasoning ✦✦
================================================================
If the Evidence section is empty, says “No evidence available”,   
   or consists only of error / timeout messages →  
   return Json with only the following two keys:

{{
  "decision": "Not Likely to Happen",
  "reasoning": "Unable to gather sufficient evidence.",
}}

================================================================
If NONE of the hard-rule conditions fire, proceed:

• Evaluate the quality & consistency of the evidence.  
• ≤ 150-word concise reasoning.  
• Return JSON with only the following two keys:

{{
  "decision": "Likely to Happen" | "Not Likely to Happen",
  "reasoning": "<your explanation ≤150 words>"
}}
""".strip()

    try:
        resp   = await asyncio.wait_for(deepseek_llm(prompt), timeout=150)
        result = extract_json_block(resp["content"])
        status = (FilterStatus.PASSED if "Likely to Happen" in result.get("decision", "")
                  else FilterStatus.FAILED)
        await notify_progress(sid, "Decision Agent", status, result.get("reasoning", ""), result)
        return result
    except Exception as e:
        err = {"error": str(e)}
        await notify_progress(sid, "Decision Agent", FilterStatus.FAILED, str(e), err)
        return err

# ─── Agent 0  Verifier Agent ───────────────────────────────────────
verifier_agent = create_react_agent(
    model,
    tools=[tavily_search_tool],
    name="verifier_agent",
    prompt="""
# Verifier Agent

Stage 1: Find original credible source for the claim. If none → ❌ UNVERIFIABLE  
Stage 2: Compare with claim, output ✅ FAITHFUL / ❌ MISLEADING.

Output:
**SOURCE**: url | credibility | date

**ANALYSIS**:
Original: ...
Claim   : ...
Differences: ...

**VERDICT**: ✅/❌ reason
"""
)

async def async_verifier_agent(statement: str, sid: str):
    await notify_progress(sid, "Verifier Agent", FilterStatus.PROCESSING, "Verifying text source…")
    try:
        resp = await asyncio.wait_for(
            asyncio.to_thread(verifier_agent.invoke,
                            {"messages": [{"role": "user", "content": statement}]}),
            timeout=90.0
        )
        content = resp["messages"][-1].content
        ok = "✅" in content
        await notify_progress(sid, "Verifier Agent",
                              FilterStatus.PASSED if ok else FilterStatus.FAILED,
                              content, {"content": content})
        return {"content": content, "passed": ok}
    except asyncio.TimeoutError:
        err = {"error": "Verification timeout"}
        await notify_progress(sid, "Verifier Agent", FilterStatus.FAILED, "Timeout", err)
        return err
    except Exception as e:
        err = {"error": str(e)}
        await notify_progress(sid, "Verifier Agent", FilterStatus.FAILED, str(e), err)
        return err

# ─── Video Verifier (可选) ─────────────────────────────────────────
video_verifier_agent = create_react_agent(
    model, tools=[], name="video_verifier_agent",
    prompt="""
Locate the claim in YouTube transcript, show context and analysis.

Output:
**Time location**
**Context**
**Analysis**:
"""
)

def extract_yid(url: str) -> Optional[str]:
    m = re.search(r"(?:youtu\\.be/|v=|embed/|shorts/)([A-Za-z0-9_-]{11})", url)
    return m.group(1) if m else None

async def search_youtube(statement: str):
    sr = await tavily_search(f"youtube video about {statement}", 1, "news")
    for r in sr.get("results", []):
        vid = extract_yid(r.get("url", ""))
        if vid:
            return vid, r.get("title", ""), r.get("content", ""), r.get("url", "")
    return None, "", "", ""

async def async_video_verifier(statement: str, sid: str):
    await notify_progress(sid, "Video Verifier", FilterStatus.PROCESSING, "Searching YouTube…")
    vid, title, content, url = await search_youtube(statement)
    if not vid:
        await notify_progress(sid, "Video Verifier", FilterStatus.FAILED, "No video found")
        return {"error": "No video", "passed": False}
    try:
        trans = await fetch_yt_transcript(vid)
        txt   = "\n".join(f"[{round(t['start'],2)}] {t['text']}" for t in trans[:100])  # Limit transcript length
        resp  = await asyncio.wait_for(
            asyncio.to_thread(video_verifier_agent.invoke,
                            {"messages":[{"role":"user",
                                        "content":f"statement:{statement}\\ntranscript:\\n{txt}"}]}),
            timeout=90.0
        )
        res = resp["messages"][-1].content
        await notify_progress(sid, "Video Verifier", FilterStatus.PASSED,
                              f"Video analyzed: {title}",
                              {"content": res, "video_url": url, "video_title": title})
        return {"content": res, "video_url": url, "video_title": title, "passed": True}
    except Exception as e:
        err = {"error": str(e)}
        await notify_progress(sid, "Video Verifier", FilterStatus.FAILED, str(e), err)
        return err

# ─── 主 pipeline ──────────────────────────────────────────────────
async def verify_statement(statement: str, sid: str, use_video: bool = False) -> VerificationResult:
    filters: List[FilterResult] = []
    
    logger.info(f"Starting verification for statement: {statement[:50]}... (use_video={use_video})")

    # Verifier Agent
    ver = await async_verifier_agent(statement, sid)
    filters.append(FilterResult("Verifier Agent",
                                FilterStatus.PASSED if ver.get("passed") else FilterStatus.FAILED,
                                ver, ver.get("content", ""), time.time()))

    # Video Verifier - Only run if explicitly requested
    if use_video is True:
        logger.info("Running Video Verifier (use_video=True)")
        vid = await async_video_verifier(statement, sid)
        filters.append(FilterResult("Video Verifier",
                                    FilterStatus.PASSED if vid.get("passed") else FilterStatus.FAILED,
                                    vid, vid.get("content", vid.get("error","")), time.time()))
    else:
        logger.info("Skipping Video Verifier (use_video=False)")
        # Add skipped status for Video Verifier
        await notify_progress(sid, "Video Verifier", FilterStatus.SKIPPED, "Video analysis not requested")
        filters.append(FilterResult("Video Verifier", 
                                    FilterStatus.SKIPPED, 
                                    {"skipped": True}, 
                                    "Video analysis not requested", 
                                    time.time()))

    # Reason Agent
    reason = await async_reason_agent(statement, sid)
    filters.append(FilterResult("Reason Agent",
                                FilterStatus.PASSED if "error" not in reason else FilterStatus.FAILED,
                                reason, reason.get("end_goal", reason.get("error","")), time.time()))
    if "error" in reason:
        return VerificationResult(statement, filters, "Analysis Failed", "Reason agent failed")

    # Online Data
    evidence = await async_online_data_agent(reason, sid)
    filters.append(FilterResult("Online Data Agent", 
                                FilterStatus.PASSED if "error" not in evidence else FilterStatus.FAILED,
                                evidence, f"{len(evidence)} keys" if "error" not in evidence else evidence.get("error", ""),
                                time.time()))
    # 在 verify_statement()，Online Data Agent 之后立即判断
    if not ver.get("passed") or "error" in evidence:
        fail_reason = ("Verifier Agent failed" if not ver.get("passed")
                    else "Online Data Agent failed")
        
        # —— 给前端发一个 Decision Agent 失败的实时消息 ——
        await notify_progress(
            sid, "Decision Agent",
            FilterStatus.FAILED,
            fail_reason,
            {"decision": "Not Likely to Happen", "reasoning": fail_reason}
        )
        
        # —— 把 Decision Agent 失败结果加入 filters 数组 ——
        filters.append(FilterResult(
            "Decision Agent",
            FilterStatus.FAILED,
            {"decision": "Not Likely to Happen", "reasoning": fail_reason},
            fail_reason,
            time.time()
        ))
        
        # —— 直接返回最终结果 ——
        return VerificationResult(
            statement        = statement,
            filters          = filters,
            final_decision   = "Not Likely to Happen",
            final_reasoning  = fail_reason,
            reference_links  = []
        )


    # Decision Agent
    decision = await async_decision_agent(statement, evidence, sid)
    filters.append(FilterResult("Decision Agent",
                                FilterStatus.PASSED if "Likely" in decision.get("decision","")
                                else FilterStatus.FAILED,
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