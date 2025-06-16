import os
import json
import time
import orjson
import asyncio
from datetime import datetime
import pandas as pd
import glob
import re
_TOOL_REGEX  = re.compile(
    r'(get_stock_metrics|get_stock_beta|get_stock_dcf_valuation|'
    r'get_stock_detailed_dcf|get_company_profile|get_stock_peers|'
    r'get_peer_valuation_comparison|get_peer_beta_comparison|'
    r'get_earnings_calendar|get_earnings_surprises|'
    r'analyze_earnings_vs_estimates)'
)
_JSON_OBJ_RE = re.compile(r"\{.*\}", re.DOTALL)
import sys
import numpy as np
import subprocess
import importlib.util
from tqdm import tqdm
from functools import wraps
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache

def tqdm_timer(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        with tqdm(total=1, desc=f"Running {func.__name__}") as pbar:
            start_time = time.time()
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            pbar.update(1)
            pbar.set_description_str(f"{func.__name__} completed")
            pbar.set_postfix_str(f"Time: {elapsed:.2f}s")
        return result
    return wrapper

# Custom JSON encoder to handle NumPy types
class NumpyJSONEncoder(json.JSONEncoder):
    @tqdm_timer
    def default(self, obj):
        if isinstance(obj, pd.DataFrame):
            return {"__dataframe__": True, "data": obj.to_dict(orient='records')}
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif pd.isna(obj):
            return None
        return super().default(obj)

@tqdm_timer
def check_and_install_packages():
    """Check if required packages are installed and install them if necessary"""
    required_packages = {
        "langchain": "langchain>=0.0.270",  # Base langchain package
        "langchain_openai": "langchain-openai>=0.0.1",
        "langchain_community": "langchain-community>=0.0.1",
        "langchain_core": "langchain-core>=0.1.0",
        "pydantic": "pydantic>=2.0.0",
        "yfinance": "yfinance>=0.2.0"
    }
    
    missing_packages = []
    
    for package_name, install_name in required_packages.items():
        if importlib.util.find_spec(package_name) is None:
            missing_packages.append(install_name)
    
    if missing_packages:
        print(f"Installing missing packages: {', '.join(missing_packages)}")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing_packages)
            print("All required packages installed successfully. Please restart the script.")
            sys.exit(0)
        except subprocess.CalledProcessError as e:
            print(f"Error installing packages: {e}")
            print("Please run: pip install langchain-openai langchain-community langchain-core pydantic yfinance")
    
    return True  # Return True even if some packages are missing to allow the script to try with what's available

# Check and install required packages
LANGCHAIN_AVAILABLE = check_and_install_packages()

# Import LangChain components if available
try:
    # Simpler imports that are definitely available in the newer versions
    from langchain_core.tools import BaseTool, Tool
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import MessagesPlaceholder
    
    # Set flag to indicate LangChain is available
    LANGCHAIN_AVAILABLE = True
    
    # Try to load memory (optional)
    try:
        from langchain_core.memory import ConversationBufferMemory
    except ImportError:
        from langchain.memory import ConversationBufferMemory
        
    # Try to load prompts (optional)
    try:
        from langchain_core.prompts.chat import SystemMessagePromptTemplate
    except ImportError:
        from langchain.prompts.chat import SystemMessagePromptTemplate
    
    # Only try these if they're actually needed by your code
    try:
        from langchain.agents import AgentType, initialize_agent
    except ImportError:
        pass  # We'll work without these
        
except ImportError as e:
    print(f"LangChain is not installed properly: {e}")
    print("Some functionality will be limited.")
    LANGCHAIN_AVAILABLE = False
    
    # Define placeholder classes
    class BaseTool:
        pass
    
    class Tool:
        pass

# Import LLM API function
try:
    from LLM_API_CALL import deepseek_api_call, Open_api_key, deepseek_api
except ImportError:
    @tqdm_timer
    def deepseek_api_call(prompt):
        print("Warning: Deepseek API function not available")
        return "LLM API not available"
    Open_api_key = None
    deepseek_api = None

async def deepseek_api_call_async(prompt: str) -> str:
    # 在后台线程调原来的同步接口
    return await asyncio.to_thread(deepseek_api_call, prompt)


@lru_cache(maxsize=256)
def _cached_deepseek_api_call(prompt: str) -> str:
    return deepseek_api_call(prompt)

# Import MicroTools
try:
    sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Tool'))
    from micro_tool import MicroTools
    MICRO_TOOLS_AVAILABLE = True
except ImportError:
    MICRO_TOOLS_AVAILABLE = False
    print("Warning: MicroTools module not available")

# Define paths
RATING_JSON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Rating_Json")

def get_rating_json_path(ticker):
    return os.path.join(RATING_JSON_DIR, f"{ticker}.json")

# Remove Debug directory references
# DEBUG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Debug")

# Remove debug directory creation
# if not os.path.exists(DEBUG_DIR):
#     os.makedirs(DEBUG_DIR)

# Debug mode flag - set to False by default
DEBUG = False

class MicroAnalystAgent:
    """
    Agent that analyzes micro data in the context of macro news.
    
    This agent reads macro news and micro news from JSON files, differentiating
    between actual facts and market expectations to provide deeper financial analysis
    and investment recommendations.
    """
    @tqdm_timer
    def __init__(self, use_langchain=True):
        """
        Initialize the Micro Analyst Agent
        
        Args:
            use_langchain (bool): Whether to use LangChain for agent implementation
        """
        self.use_langchain = use_langchain and LANGCHAIN_AVAILABLE
        self.micro_tools_available = MICRO_TOOLS_AVAILABLE
        
        # Initialize cache directory
        self.cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Tool_Tests")
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        
        # Initialize LangChain agent if available
        if self.use_langchain:
            self._setup_langchain_agent()

    @tqdm_timer
    def _setup_langchain_agent(self):
        """Set up LangChain agent with appropriate tools"""
        if not LANGCHAIN_AVAILABLE:
            print("LangChain is not available. Cannot set up agent.")
            return
            
        if not MICRO_TOOLS_AVAILABLE:
            print("MicroTools is not available. Cannot set up agent tools.")
            return
            
        # Get MicroTools LangChain tools
        self.tools = MicroTools.get_langchain_tools()
        
        # Set up memory
        try:
            self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        except Exception as e:
            print(f"Error setting up memory: {e}")
            self.memory = None
        
        # Set up LLM - use the OpenAI API key from LLM_API_CALL
        try:
            self.llm = ChatOpenAI(temperature=0.2, openai_api_key=Open_api_key)
        except Exception as e:
            print(f"Error setting up LLM: {e}")
            self.llm = None
            return
        
        # System message for the agent
        system_message = """
        Micro Analyst Agent
        
        You are a professional micro investment analyst AI Agent. Your job is to carefully read and analyze
        news about a given **ticker** and separate fact from market expectations.
        
        You will:
        1. **Read Macro News Context**
           - Understand the broader economic context from macro news
           - Note key economic indicators, business cycle phase, and market sentiment
           - Identify which macro factors specifically impact the ticker being analyzed
        
        2. **Analyze Micro News**
           - Distinguish between factual information and market expectations/projections
           - Identify key company-specific developments, earnings data, and business changes
           - Look for discrepancies between facts and market narratives
        
        3. **Compare Key Takeaways**
           - Compare what's actually happening (facts) vs. what the market expects (expectations)
           - Identify areas where market expectations may be misaligned with reality
           - Look for signals that might indicate future price adjustments
        
        4. **Execute Micro Tools for Deeper Analysis**
           - Use data tools to verify claims made in news articles
           - Gather quantitative metrics to test qualitative market narratives
           - Find evidence that either supports or contradicts prevailing market expectations
           
        5. **Generate Actionable Insights**
           - Determine if the stock is being correctly valued based on factual information
           - Identify potential catalysts that could change current market perceptions
           - Provide a well-reasoned investment recommendation

        6. Future Events
        - In the reading, you will have some calender events that will happen in the future.
        - You need to analyze the news and determine if the event is already priced in or not.
        - If it is priced in, you need to use tools to check the price of the stock before and after the event.
        - If it is not priced in, you need to use tools to check the price of the stock before and after the event.

        7!! Important !!
        - You cant just simply think  news is good or bad, stock price is good or bad.
        - If sentiment is too positive, then any slight negative news will be driving the stock price down.
        - If sentiment is too negative, then any slight postive news will be driving the stock price up.
        - You need to use tools to verify the news and the stock price.
        - You need to use your knowledge to make a final recommendation.
        
        Your analysis should clearly separate objective facts from subjective expectations
        and highlight any significant gaps between them.
        """
        
        # Initialize the agent - try different methods based on what's available
        try:
            # Try to load the agent creator from langchain module
            from langchain.agents import initialize_agent, AgentType
            
            agent_kwargs = {}
            if hasattr(SystemMessagePromptTemplate, "from_template"):
                agent_kwargs["system_message"] = system_message
            
            self.agent_chain = initialize_agent(
                tools=self.tools,
                llm=self.llm,
                agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
                verbose=True,
                memory=self.memory,
                agent_kwargs=agent_kwargs
            )
            
            print("Successfully initialized LangChain agent using legacy method")
        except Exception as e:
            print(f"Error initializing agent: {e}")
            print("Agent functionality will be limited")
            self.agent_chain = None
    
    @tqdm_timer
    def get_latest_rating_json(self) -> Tuple[str, Dict]:
        """
        Get the latest rating JSON file for the ticker (now always {ticker}.json)
        """
        # Use the new naming convention
        ticker = getattr(self, 'ticker', None)
        if not ticker:
            raise ValueError("No ticker set in MicroAnalystAgent")
        path = get_rating_json_path(ticker)
        if not os.path.exists(path):
            raise FileNotFoundError(f"No JSON file found for {ticker} at {path}")
        with open(path, "r") as f:
            rating_data = json.load(f)
        return path, rating_data
    
    @tqdm_timer
    def load_rating_json(self, file_path: str) -> Dict:
        """
        Load a specific rating JSON file
        
        Args:
            file_path (str): Path to the rating JSON file
            
        Returns:
            Dict containing the parsed JSON content
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        with open(file_path, "r") as f:
            rating_data = json.load(f)
            
        return rating_data
    
    @tqdm_timer
    def extract_inference_hints(self, rating_data: Dict, verbose: bool = True) -> Dict:
        """
        Extract inference hints from the rating data
        
        Args:
            rating_data (Dict): Rating data containing macro and micro information
            verbose (bool): Whether to print detailed logs
            
        Returns:
            Dict containing extracted inference hints
        """
        ticker = rating_data.get("Ticker", "")
        macro_hint = rating_data.get("Macro", {}).get("next_inference_hint", "")
        micro_hint = rating_data.get("Micro", {}).get("Next_Inference_Hint_Micro_News", "")
        
        if verbose:
            print("\n💡 EXTRACTING INFERENCE HINTS")
            if macro_hint:
                print(f"  📈 Macro Inference Hint: {macro_hint[:150]}...")
            else:
                print(f"  ⚠️ No macro inference hint found in the data")
                
            if micro_hint:
                print(f"  📉 Micro Inference Hint: {micro_hint[:150]}...")
            else:
                print(f"  ⚠️ No micro inference hint found in the data")
        
        return {
            "ticker": ticker,
            "macro_hint": macro_hint,
            "micro_hint": micro_hint
        }
    
    async def determine_micro_tools(self, rating_data: Dict, verbose: bool = True) -> Dict:
        """
        异步版：根据 rating_data 选取 micro-tools
        """
        # —— 保留原校验
        ticker = rating_data.get("Ticker", "")
        if not ticker:
            raise ValueError("No ticker found in rating data")

        # —— 用 orjson 只序列化最少必要字段（避免 dump 整个大 dict）
        macro_summary = {
            "headlines": rating_data.get("Macro", {}).get("headlines", [])[:3],
            "key_indicators": rating_data.get("Macro", {}).get("key_indicators", {})
        }
        micro_summary = {
            "snippets": rating_data.get("Micro", {}).get("snippets", [])[:3],
            "next_hint": rating_data.get("Micro", {}).get("Next_Inference_Hint_Micro_News", "")
        }
        macro_str = orjson.dumps(macro_summary).decode()
        micro_str = orjson.dumps(micro_summary).decode()

        # —— 构建 prompt（可按需微调文案）
        prompt = f"""
Based on the following macro and micro summary for {ticker},
1) pick 3-5 appropriate analysis tools (from the list below) and explain each;
2) format as JSON with keys: selected_tools, facts_to_verify, expectations_to_test, rationale, reasoning_process.

MACRO SUMMARY:
{macro_str}

MICRO SUMMARY:
{micro_str}

Available tools:
- get_stock_metrics: verify performance
- get_stock_beta: check sensitivity
- get_stock_dcf_valuation: test valuation
- get_stock_detailed_dcf: full DCF scenarios
- get_company_profile: examine business model
- get_stock_peers: identify industry peers
- get_peer_valuation_comparison: valuation vs peers
- get_peer_beta_comparison: volatility vs peers
- get_earnings_calendar: upcoming events
- get_earnings_surprises: historical surprises
- analyze_earnings_vs_estimates: expectations vs actual
"""

        # —— 异步调用缓存的 API：避免在事件循环里直接做网络阻塞
        raw = await asyncio.to_thread(_cached_deepseek_api_call, prompt)

        # —— 尝试提取 JSON
        match = _JSON_OBJ_RE.search(raw or "")
        if match:
            try:
                return orjson.loads(match.group(0))
            except orjson.JSONDecodeError:
                # 如果 JSON 不合法，继续走 fallback
                pass

        # —— fallback：用预编译正则抽工具名
        tools = _TOOL_REGEX.findall(raw or "")
        if not tools:
            # 再次 fallback 回默认
            return {
                "selected_tools": ["get_stock_metrics","get_company_profile","get_earnings_surprises"],
                "facts_to_verify": [],
                "expectations_to_test": [],
                "rationale": {},
                "reasoning_process": "Fallback: no tools extracted."
            }

        # —— 最终返回
        return {
            "selected_tools": tools,
            "facts_to_verify": ["Extracted via regex fallback"],
            "expectations_to_test": ["Extracted via regex fallback"],
            "rationale": {t: "Auto-selected" for t in tools},
            "reasoning_process": "Regex-based fallback."
        }
    @tqdm_timer
    def execute_micro_tools(self, ticker: str, selected_tools: List[str], verbose: bool = True) -> Dict:
        """
        Execute the selected micro tools for a given ticker
        
        Args:
            ticker (str): Stock ticker to analyze
            selected_tools (List[str]): List of micro tool names to execute
            verbose (bool): Whether to print detailed logs
            
        Returns:
            Dict containing results from each tool
        """
        if not MICRO_TOOLS_AVAILABLE:
            if verbose:
                print("⚠️ MicroTools not available, cannot execute tools")
            return {"error": "MicroTools not available"}
            
        results = {}
        
        # Map tool names to MicroTools methods
        tool_map = {
            "get_stock_metrics": MicroTools.get_key_metrics,
            "get_stock_beta": MicroTools.get_beta,
            "get_stock_dcf_valuation": MicroTools.get_dcf_valuation,
            "get_stock_detailed_dcf": MicroTools.get_detailed_dcf,
            "get_company_profile": MicroTools.get_company_profile,
            "get_stock_peers": MicroTools.get_peers,
            "get_peer_valuation_comparison": MicroTools.get_peer_valuation_comparison,
            "get_peer_beta_comparison": MicroTools.get_peer_beta_comparison,
            "get_earnings_calendar": MicroTools.get_companies_earnings_calendar,
            "get_earnings_surprises": MicroTools.get_earnings_surprises,
            "analyze_earnings_vs_estimates": MicroTools.analyze_earnings_estimates_vs_actual
        }
        
        # Tool descriptions for better explaining the thought process
        tool_descriptions = {
            "get_stock_metrics": "analyzing key financial metrics like EPS, ROIC, debt, and cash flow",
            "get_stock_beta": "assessing volatility and correlation with the market",
            "get_stock_dcf_valuation": "calculating discounted cash flow valuation",
            "get_stock_detailed_dcf": "performing detailed DCF valuation with multiple scenarios",
            "get_company_profile": "understanding the company's business model and operations",
            "get_stock_peers": "identifying comparable companies for benchmarking",
            "get_peer_valuation_comparison": "comparing valuation multiples against industry peers",
            "get_peer_beta_comparison": "comparing volatility metrics against peers",
            "get_earnings_calendar": "checking upcoming earnings announcements",
            "get_earnings_surprises": "analyzing historical earnings surprises",
            "analyze_earnings_vs_estimates": "examining analysts' estimate accuracy"
        }
        
        # Create a cache for the raw results
        results: Dict[str, Any] = {}
        raw_results: Dict[str, Any] = {}
        def run_tool(tool_name: str) -> Tuple[str, Any]:
            if verbose:
                print(f"\n⚙️ [Thread] EXECUTING TOOL: {tool_name}")
                print(f"  Purpose: {tool_descriptions.get(tool_name, 'No description available')}")
                print(f"  Input: Ticker = {ticker}")
            try:
                if tool_name == "get_earnings_calendar":
                    result = tool_map
                else:
                    result = tool_map[tool_name](ticker)
                if verbose:
                    print(f"  ✓ [Thread] {tool_name} completed")
                return tool_name, result
            except Exception as e:
                error_msg = str(e)
                if verbose:
                    print(f"  ❌ [Thread] Error executing {tool_name}: {error_msg}")
                return tool_name, {"error": error_msg}
        # Execute each selected tool
        with ThreadPoolExecutor(max_workers=min(len(selected_tools), 8)) as executor:
            future_to_tool = {
                executor.submit(run_tool, name): name
                for name in selected_tools
            }
            for future in as_completed(future_to_tool):
                name, result = future.result()
                raw_results[name] = result
                results[name] = result
        
        # Save the raw results to a cache file
        self.save_tool_results_cache(ticker, raw_results)
                
        return results
    
    @tqdm_timer
    def save_tool_results_cache(self, ticker: str, tool_results: Dict) -> str:
        """
        Save the raw tool results to a cache file
        
        Args:
            ticker (str): Stock ticker
            tool_results (Dict): Raw results from executing micro tools
            
        Returns:
            str: Path to the cache file
        """
        # Create a timestamp for the filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        cache_file = os.path.join(self.cache_dir, f"cache_{ticker}_{timestamp}.json")
        
        # Save the raw results to a JSON file
        try:
            with open(cache_file, "w") as f:
                json.dump(tool_results, f, indent=2, cls=NumpyJSONEncoder)
            return cache_file
        except Exception as e:
            print(f"Error saving tool results cache: {e}")
            return ""
    
    @tqdm_timer
    async def process_tool_results_with_llm_async(
        self,
        ticker: str,
        tool_results: Dict[str, Any],
        verbose: bool = True,
        max_concurrency: int = 16
    ) -> Dict[str, Any]:
        """
        Async version: process tool results with LLM in parallel coroutines.
        """
        if verbose:
            print("\n🧠 Processing tool results with LLM asynchronously...")

        sem = asyncio.Semaphore(min(len(tool_results), max_concurrency))

        async def _proc(tool_name: str, result: Any) -> Tuple[str, Dict[str, str]]:
            async with sem:
                if verbose:
                    print(f"  Processing {tool_name}…")
                result_str = str(result)
                if len(result_str) > 8000:
                    result_str = result_str[:8000] + "... [truncated]"

                is_peer_tool = any(
                    x in tool_name.lower()
                    for x in ["peer", "comparison", "competitors", "compare"]
                )
                if is_peer_tool:
                    prompt = f"""
You are a financial data reporter. Analyze the following peer comparison data from the {tool_name} tool for ticker {ticker}.

DATA:
{result_str}

Your response MUST be structured in exactly two parts:

PART 1: FACTUAL REPORT
First, extract and list the key metrics for {ticker} AND its peers in simple format:
1. List {ticker}'s metrics first (at least 3-5 key values)
2. EXPLICITLY list the top 3-5 peers by name with their corresponding metrics
3. Use a "metric = value" format for all data points

PART 2: ANALYSIS
Only after listing the factual values, provide a brief interpretation (2-3 sentences) comparing {ticker} to its peers.

Remember to STRICTLY separate the factual report (PART 1) from your analysis (PART 2).
"""
                else:
                    prompt = f"""
You are a financial data reporter. Analyze the following data from the {tool_name} tool for ticker {ticker}.

DATA:
{result_str}

Your response MUST be structured in exactly two parts:

PART 1: FACTUAL REPORT
First, extract and list the key metrics and values directly from the data in simple "metric = value" format.
Report just the raw values without interpretation. List at least 3-5 key metrics with their exact values.

PART 2: ANALYSIS
Only after listing the factual values, provide a brief interpretation (2-3 sentences) explaining what these values suggest about the company.

Remember to STRICTLY separate the factual report (PART 1) from your analysis (PART 2).
"""

                try:
                    # 使用异步调用封装的 deepseek_api_call_async
                    resp = await deepseek_api_call_async(prompt)
                    return tool_name, {"name": tool_name, "result": resp.strip()}
                except Exception as e:
                    err = str(e)
                    if verbose:
                        print(f"  ❌ Error processing {tool_name}: {err}")
                    return tool_name, {"name": tool_name, "result": f"Error: {err}"}

        tasks = [_proc(name, res) for name, res in tool_results.items()]
        completed = await asyncio.gather(*tasks)
        return {name: processed for name, processed in completed}

    def process_tool_results_with_llm(self, ticker: str, tool_results: Dict[str, Any], verbose: bool = True) -> Dict[str, Any]:
        
        if verbose:
            print("\n🧠 Processing tool results with LLM (batch mode)…")

        # 1) Prepare each tool's raw data as text
        entries = []
        for tool_name, result in tool_results.items():
            result_str = str(result)
            if len(result_str) > 8000:
                result_str = result_str[:8000] + "... [truncated]"
            entries.append(f"### TOOL: {tool_name}\nDATA:\n{result_str}")

        batch_data = "\n\n".join(entries)

        # 2) Original per-tool prompt templates
        peer_template = f"""
    You are a financial data reporter. Analyze the following peer comparison data from the {{tool_name}} tool for ticker {ticker}.

    DATA:
    {{result_str}}

    Your response MUST be structured in exactly two parts:

    PART 1: FACTUAL REPORT
    First, extract and list the key metrics for {ticker} AND its peers in simple format:
    1. List {ticker}'s metrics first (at least 3-5 key values)
    2. EXPLICITLY list the top 3-5 peers by name with their corresponding metrics
    3. Use a "metric = value" format for all data points

    For example:
    {ticker} METRICS:
    - {ticker} EPS = $X.XX
    - {ticker} Revenue Growth = X.X%
    - {ticker} Beta = X.XX

    PEER METRICS:
    - Peer1 EPS = $X.XX, Beta = X.XX
    - Peer2 EPS = $X.XX, Beta = X.XX
    ...and so on for other peers

    PART 2: ANALYSIS
    Only after listing the factual values, provide a brief interpretation (2-3 sentences) comparing {ticker} to its peers.

    Remember to STRICTLY separate the factual report (PART 1) from your analysis (PART 2).
    """

        non_peer_template = f"""
    You are a financial data reporter. Analyze the following data from the {{tool_name}} tool for ticker {ticker}.

    DATA:
    {{result_str}}

    Your response MUST be structured in exactly two parts:

    PART 1: FACTUAL REPORT
    First, extract and list the key metrics and values directly from the data in simple "metric = value" format.
    Report just the raw values without interpretation. List at least 3-5 key metrics with their exact values.
    Example format:
    - EPS = $X.XX
    - Revenue Growth = X.X%
    - Beta = X.XX
    - Current Price = $XXX.XX

    PART 2: ANALYSIS
    Only after listing the factual values, provide a brief interpretation (2-3 sentences) explaining what these values 
    suggest about the company.

    Remember to STRICTLY separate the factual report (PART 1) from your analysis (PART 2).
    """

        # 3) Build the batch prompt
        prompt = f"""
    I will provide you multiple tool datasets for ticker {ticker}.  For each tool, apply these exact instructions:

    - If the tool name contains any of ["peer","comparison","competitors","compare"], use this template:

    {peer_template}

    - Otherwise, use this template:

    {non_peer_template}

    Here are all the tool datasets:

    {batch_data}

    Finally, return **only** a single JSON object that maps each tool name to its combined reply string (including both PART 1 and PART 2).  
    Example output format:

    {{
    "get_stock_metrics": "PART 1: ...\\nPART 2: ...",
    "get_peer_valuation_comparison": "PART 1: ...\\nPART 2: ..."
    }}
    """

        if verbose:
            print("📝 Sending batch prompt to LLM…")

        # 4) Single LLM call
        raw = deepseek_api_call(prompt).strip()
        if verbose:
            print("✅ Received batch LLM response")

        # 5) Extract JSON from LLM output
        try:
            batch_result = json.loads(raw)
        except Exception:
            m = re.search(r"\{[\s\S]*\}", raw)
            if m:
                batch_result = json.loads(m.group(0))
            else:
                # 全部失败时，返回空结构
                batch_result = {}

        # 6) Repackage to original interface
        processed: Dict[str, Any] = {}
        for tool_name in tool_results:
            text = batch_result.get(tool_name, "")
            processed[tool_name] = {"name": tool_name, "result": text}

        return processed
    
    def _format_single_result(self, tool_name: str, result: Any) -> Dict[str, Any]:
        """
        Helper to format one tool's raw result into a summary/details dict.
        """
        # DataFrame
        if isinstance(result, pd.DataFrame):
            if result.empty:
                return {"summary": "Empty DataFrame", "sample": []}
            sample = result.head(3).to_dict(orient="records")
            cols = ", ".join(result.columns)
            return {"summary": f"DataFrame with {len(result)} rows, columns: {cols}", "sample": sample}

        # Dict
        if isinstance(result, dict):
            if "error" in result:
                return {"summary": f"Error: {result['error']}", "details": {}}
            if "key_metrics" in result:
                return {"summary": "Key financial metrics retrieved", "details": result["key_metrics"]}

            summary_parts, details = [], {}
            for k, v in result.items():
                if isinstance(v, pd.DataFrame):
                    summary_parts.append(f"{k}: DataFrame({len(v)} rows)")
                    if not v.empty:
                        details[k] = v.head(3).to_dict(orient="records")
                elif isinstance(v, (str, int, float, bool)):
                    summary_parts.append(f"{k}: {v}")
                    details[k] = v
                elif isinstance(v, dict):
                    summary_parts.append(f"{k}: Dict({len(v)} items)")
                    details[k] = v

            summary = ", ".join(summary_parts[:5])
            if len(summary_parts) > 5:
                summary += f" and {len(summary_parts)-5} more..."
            return {"summary": summary, "details": details}

        # Scalar or other
        return {"summary": str(result), "details": {}}

    @tqdm_timer
    def analyze_results(self, ticker: str, macro_data: Dict, micro_data: Dict, tool_results: Dict, verbose: bool = True) -> Dict:
        if verbose:
            print("\n🧠 FACT DISCOVERY PROCESS:")

        async def _async_runner():
            sem = asyncio.Semaphore(min(len(tool_results), 8))
            async def _fmt(name, result):
                async with sem:
                    return name, await asyncio.to_thread(self._format_single_result, name, result)
            coros = [_fmt(n, r) for n, r in tool_results.items()]
            completed = await asyncio.gather(*coros)
            return {n: res for n, res in completed}

        readable_results = asyncio.run(_async_runner())

        # 后面同方案 A 的 reasoning 逻辑…
        ki = macro_data.get("key_indicators", {})
        gdp_desc  = ki.get("GDP_growth_description", "economic growth")
        ir_desc   = ki.get("Interest_rate_description", "interest rates")
        sentiment = macro_data.get("sentiment", "Not available")
        trend     = macro_data.get("trend", "Not available")

        reasoning = (
            f"Analysis of {ticker} based on macro and micro news:\n"
            f"- GDP growth: {gdp_desc}; interest rates: {ir_desc}\n"
            f"- Macro sentiment: {sentiment}; market trend: {trend}"
        )

        return {
            "reasoning": reasoning,
            "tools_used": list(tool_results.keys()),
            "tool_results": readable_results
        }

    
    @tqdm_timer
    async def generate_price_inference_async(
        self,
        ticker: str,
        inference_hints: Dict[str, str],
        tool_results: Dict[str, Any],
        analysis_results: Dict[str, Any],
        verbose: bool = True
    ) -> Dict[str, str]:
        """
        Async version: generate price inference in one coroutine.
        """
        if verbose:
            print("\n💰 GENERATING PRICE INFERENCE (async)…")
        # 1) 准备 hints
        macro_hint = inference_hints.get("macro_hint", "")
        micro_hint = inference_hints.get("micro_hint", "")

        # 2) 高速序列化 tool_results_str
        def orjson_default(obj):
            if isinstance(obj, (np.integer, np.floating)):
                return obj.item()
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if pd.isna(obj):
                return None
            raise TypeError

        data_bytes = await asyncio.to_thread(
            orjson.dumps,
            analysis_results.get("tool_results", {}),
            default=orjson_default
        )
        tool_results_str = data_bytes.decode()
        if len(tool_results_str) > 4000:
            tool_results_str = tool_results_str[:4000] + "... [truncated]"

        # 3) 组织 Prompt（保持原样）
        prompt = f"""
        You are a financial analyst translating fundamental micro analysis into clear price action recommendations.

        Analyze the following data for {ticker} and provide a DIRECT CONCISE price action inference.

        MACRO INFERENCE HINT:
        {macro_hint}

        MICRO INFERENCE HINT:
        {micro_hint}

        MICRO ANALYSIS RESULTS:
        {tool_results_str}

        ---

        STRICT INSTRUCTIONS:
        1. Write ONLY 3-4 concise sentences total that:
           - Summarize the key micro insights (1-2 sentences)
           - Clearly state whether to LONG, SHORT, or NEUTRAL/WAIT on {ticker} (1 sentence)
           - Indicate if this is a MOMENTUM trade (following trend) or REVERSAL trade (against trend) (1 sentence)

        2. FOCUS ONLY on:
           - Whether the micro fundamentals support going LONG, SHORT, or staying NEUTRAL
           - Whether current price movement should continue (MOMENTUM) or reverse (REVERSAL)
           - Short 1-sentence rationale why

        3. DO NOT:
           - Include price targets or stop losses
           - Use JSON formatting or any code blocks
           - Include confidence levels or timeframes in your response
           - Write any introduction or additional explanations

        EXAMPLE GOOD RESPONSE:
        "{ticker} shows declining revenue growth (-2.3%) and margins (-150bps) alongside high valuation (P/E 45x) compared to peers (avg 22x). SHORT is recommended given the deteriorating fundamentals. This is a MOMENTUM trade as recent price weakness likely continues with earnings revisions downward."

        REMEMBER: Your entire response must be ONLY 3-4 concise sentences total with NO additional text.
        """

        if verbose:
            print("📝 Sending price inference prompt to LLM…")

        # 4) 调用 LLM
        llm_response = (await deepseek_api_call_async(prompt)).strip()
        if verbose:
            print(f"✅ Price inference: {llm_response[:150]}…")

        # 5) 正则提取方向 & 交易类型
        dir_m = re.search(r'\b(LONG|SHORT|NEUTRAL|WAIT)\b', llm_response, re.IGNORECASE)
        type_m = re.search(r'\b(MOMENTUM|REVERSAL)\b', llm_response, re.IGNORECASE)
        trade_direction = dir_m.group(0).upper() if dir_m else "UNDEFINED"
        trade_type      = type_m.group(0).upper() if type_m else "UNDEFINED"

        return {
            "inference":       llm_response,
            "trade_direction": trade_direction,
            "trade_type":      trade_type
        }

    def generate_price_inference(
        self,
        ticker: str,
        inference_hints: Dict[str, str],
        tool_results: Dict[str, Any],
        analysis_results: Dict[str, Any],
        verbose: bool = True
    ) -> Dict[str, str]:
        """
        同步接口，内部跑 async 版。
        """
        return asyncio.run(
            self.generate_price_inference_async(
                ticker, inference_hints, tool_results, analysis_results, verbose
            )
        )
    
    @tqdm_timer
    def update_rating_json(self,
                           rating_path: str,
                           analysis_results: Dict,
                           tool_selection: Dict,
                           tool_results: Dict,
                           price_inference: Dict = None,
                           verbose: bool = True, llm_processed_results: Optional[Dict[str, Any]] = None) -> None:
        """
        Update the rating JSON file with micro analysis results only, using
        the async version of process_tool_results_with_llm under the hood.
        
        Args:
            rating_path (str): Path to the rating JSON file
            analysis_results (Dict): Analysis results to add to the rating JSON
            tool_selection (Dict): Information about which tools were selected and why
            tool_results (Dict): Results from executing each micro tool
            price_inference (Dict, optional): Price inference results
            verbose (bool): Whether to print detailed logs
        """
        # 1. Load the current rating JSON
        with open(rating_path, "r", encoding="utf-8") as f:
            rating_data = json.load(f)
        
        # 2. Extract ticker
        ticker = rating_data.get("Ticker", "")
        
        # 3. Process tool results asynchronously
        if llm_processed_results is None:    
          if verbose:
                print("\n🧠 Running async LLM processing of tool results...")
                llm_processed_results = asyncio.run(
                self.process_tool_results_with_llm_async(ticker, tool_results, verbose)
            )
        
        # 4. Preserve existing Micro data
        existing_micro = rating_data.get("Micro", {})
        rating_data.setdefault("Micro", {})
        
        # 5. Carry over important fields
        for field in ("Three_Key_Takeaways", "Micro_Expectation", "Next_Inference_Hint_Micro_News"):
            if field in existing_micro:
                rating_data["Micro"][field] = existing_micro[field]
        
        # 6. Update with new analysis
        rating_data["Micro"].update({
            "reasoning":    analysis_results.get("reasoning",       "No reasoning provided"),
            "tools_used":   analysis_results.get("tools_used",     []),
            "tool_results": llm_processed_results,
            "rationale":    tool_selection.get("rationale",        {})
        })

        # Patch: Always fill Three_Key_Takeaways and Micro_Expectation with fallbacks if missing or empty
        micro = rating_data["Micro"]
        if not micro.get("Three_Key_Takeaways"):
            micro["Three_Key_Takeaways"] = [micro.get("reasoning", "No key takeaways available.")]
        if not micro.get("Micro_Expectation"):
            micro["Micro_Expectation"] = micro.get("micro_to_price_next_inference", micro.get("reasoning", "No expectation available."))
        rating_data["Micro"] = micro
        
        # 7. Add price inference if present
        if price_inference:
            rating_data["Micro"]["micro_to_price_next_inference"] = price_inference.get("inference", "")
            if verbose:
                print(f"\n💰 Added price inference to Micro section")
                print(f"  Trade direction: {price_inference.get('trade_direction', 'N/A')}")
                print(f"  Trade type:      {price_inference.get('trade_type',      'N/A')}")
        
        # 8. Write back to disk
        with open(rating_path, "w", encoding="utf-8") as f:
            json.dump(rating_data, f, indent=2, cls=NumpyJSONEncoder)
        
        if verbose:
            print(f"\n✅ Updated the Micro section in rating JSON with enhanced format")
            print(f"📊 Tools used: {', '.join(analysis_results.get('tools_used', []))}")
            print(f"💾 File saved: {rating_path}")
        
        # 9. Clean up legacy keys if they exist
        for legacy in ("Three_Key_Takeaway_News", "Micro_Expectations"):
            if legacy in rating_data["Micro"]:
                del rating_data["Micro"][legacy]
    
    async def run_analysis_async(self, rating_path: str = None, verbose: bool = True) -> Dict:
        # 1. Load JSON (同步很快)
        rating_data = self.load_rating_json(rating_path)
        ticker = rating_data.get("Ticker", "")

        # 2. Extract hints
        macro_hint = rating_data.get("Macro", {}).get("next_inference_hint", "")
        micro_hint = rating_data.get("Micro", {}).get("Next_Inference_Hint_Micro_News", "")
        if verbose:
            print(f"[DEBUG] Macro Hint: {macro_hint}")
            print(f"[DEBUG] Micro Hint: {micro_hint}")

        # 3. Tool selection (异步)
        if verbose: print("[DEBUG] Selecting tools…")
        tool_selection = await self.determine_micro_tools(rating_data, verbose=verbose)
        if not tool_selection.get("selected_tools"):
            raise RuntimeError("Tool selection failed")

        # 4. Tool execution (同步多线程已并发)
        if verbose: print("[DEBUG] Executing tools…")
        tool_results = await asyncio.to_thread(
            self.execute_micro_tools, ticker, tool_selection["selected_tools"], verbose
        )

        # 5. Analysis (同步小量计算)
        if verbose: print("[DEBUG] Analyzing results…")
        analysis_results = await asyncio.to_thread(
            self.analyze_results, ticker, rating_data.get("Macro", {}), rating_data.get("Micro", {}), tool_results, verbose
        )

        # 6. LLM post‐processing (异步并发)
        if verbose:
            print("[DEBUG] Post‐processing with LLM (batch mode)…")
        # 将同步批处理接口放到后台线程，避免冻结事件循环
        llm_processed = await asyncio.to_thread(
        self.process_tool_results_with_llm,
        ticker,
        tool_results,
        verbose
        )

        # 7. Price inference (异步版本，参照前面示例)
        if verbose: print("[DEBUG] Generating price inference…")
        price_inf = await self.generate_price_inference_async(
            ticker, {"macro_hint":macro_hint, "micro_hint":micro_hint}, tool_results, analysis_results, verbose
        )

        # 8. JSON 更新（把 orjson/线程写盘包装成异步）
        if verbose: print("[DEBUG] Updating rating JSON…")
        await asyncio.to_thread(
            self.update_rating_json, rating_path, analysis_results, tool_selection, tool_results, price_inf, verbose, llm_processed_results=llm_processed
        )

        return {
            "ticker": ticker,
            "analysis_results": analysis_results,
            "tool_selection": tool_selection,
            "tool_results": tool_results,
            "price_inference": price_inf
        }


    @tqdm_timer
    def run_analysis(self, *args, **kwargs):
        return asyncio.run(self.run_analysis_async(*args, **kwargs))

# Example usage
if __name__ == "__main__":
    try:
        print("🚀 Starting Micro Analyst Agent")
        agent = MicroAnalystAgent(use_langchain=LANGCHAIN_AVAILABLE)
        print("🔄 Running full analysis…")
        results = agent.run_analysis(verbose=True)
        # …打印 summary…
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback; traceback.print_exc()