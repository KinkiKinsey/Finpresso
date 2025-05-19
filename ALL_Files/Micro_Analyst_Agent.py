#!/usr/bin/env python
# coding: utf-8

import os
import json
import time
from datetime import datetime
import pandas as pd
import glob
import re, orjson
import sys
import numpy as np
import subprocess
import importlib.util
from tqdm import tqdm
from functools import wraps, lru_cache
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

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
        Get the latest rating JSON file from the Rating_Json directory
        
        Returns:
            Tuple containing the file path and parsed JSON content
        """
        # Get all JSON files in the Rating_Json directory
        json_files = glob.glob(os.path.join(RATING_JSON_DIR, "*.json"))
        
        if not json_files:
            raise FileNotFoundError(f"No JSON files found in {RATING_JSON_DIR}")
        
        # Sort by modification time (newest first)
        latest_file = max(json_files, key=os.path.getmtime)
        
        # Read the JSON file
        with open(latest_file, "r") as f:
            rating_data = json.load(f)
        
        return latest_file, rating_data
    
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
    
    @tqdm_timer
    def determine_micro_tools(self, rating_data: Dict, verbose: bool = True) -> Dict:
        """
        Determine which micro tools to use based on the rating data
        
        Args:
            rating_data (Dict): Rating data containing macro and micro information
            verbose (bool): Whether to print detailed logs
            
        Returns:
            Dict containing selected tools and rationale
        """
        # Precompile regex
        TOOL_REGEX = re.compile(r'(get_stock_metrics|get_stock_beta|get_stock_dcf_valuation|'
                                r'get_stock_detailed_dcf|get_company_profile|get_stock_peers|'
                                r'get_peer_valuation_comparison|get_peer_beta_comparison|'
                                r'get_earnings_calendar|get_earnings_surprises|'
                                r'analyze_earnings_vs_estimates)')

        # Cached version of your LLM API call
        @lru_cache(maxsize=128)
        def cached_deepseek_api_call(prompt: str) -> str:
            return deepseek_api_call(prompt)

        # Utility to extract JSON from raw LLM response
        def extract_json_string(raw: str) -> str:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            return match.group(0).strip() if match else raw.strip()
        
        ticker = rating_data.get("Ticker", "")
        macro_data = rating_data.get("Macro", {})
        micro_data = rating_data.get("Micro", {})
        
        if not ticker:
            raise ValueError("No ticker found in rating data")
        
        if verbose:
            print(f"\n🤔 THINKING PROCESS: Analyzing news to separate fact from expectations")
            print(f"  - Reading macro news context for {ticker}")
            print(f"  - Identifying key facts in micro news")
            print(f"  - Comparing market expectations to actual developments")
            print(f"  - Determining tools needed to verify claims and expectations")
        
        # Use orjson for faster serialization
        macro_str = orjson.dumps(macro_data).decode()[:1000]
        micro_str = orjson.dumps(micro_data).decode()[:1000]
        # Build a prompt for the LLM to determine which tools to use
        prompt = f"""
        Based on the following macro and micro news for {ticker}, determine which micro analysis tools would be most useful to separate facts from market expectations and identify potential investment opportunities.

        MACRO DATA:
        {macro_str}
        
        MICRO DATA:
        {micro_str}
        
        Available micro tools and their purposes:
        - get_stock_metrics: verify company performance
        - get_stock_beta: check market sensitivity
        - get_stock_dcf_valuation: test valuation assumptions
        - get_stock_detailed_dcf: full DCF to verify views
        - get_company_profile: understand actual business model
        - get_stock_peers: find true industry peers
        - get_peer_valuation_comparison: compare valuation to peers
        - get_peer_beta_comparison: compare volatility with peers
        - get_earnings_calendar: confirm upcoming events
        - get_earnings_surprises: check if firm beats/misses estimates
        - analyze_earnings_vs_estimates: compare actual vs analyst estimates

        TASK:
        1. Identify which facts in the news need verification 
        2. Determine which market expectations need to be tested against data
        3. Select 3-5 most relevant tools that would help separate fact from fiction for {ticker}
        4. Explain why each tool would help uncover investment truths
        
        Format your response as a JSON object with these keys:
        - "selected_tools": array of tool names
        - "facts_to_verify": array of factual claims from the news that need verification
        - "expectations_to_test": array of market expectations that should be tested with data
        - "rationale": object with tool names as keys and rationales as values
        - "reasoning_process": string explaining your step-by-step thought process
        """
        
        if verbose:
            print(f"\n📝 PROMPT: Sending prompt to LLM to determine appropriate tools")
        
        try:
            llm_response = cached_deepseek_api_call(prompt)

            if verbose:
                print(f"\n🔄 RESPONSE: Received tool selection from LLM")
                print(f"RAW LLM RESPONSE:\n{llm_response[:1000]}...")  # Limit length in logs

            json_str = extract_json_string(llm_response)

            tool_selection = orjson.loads(json_str)

            if verbose and "reasoning_process" in tool_selection:
                print(f"\n🧠 REASONING PROCESS:")
                for line in tool_selection["reasoning_process"].split("\n"):
                    print(f"  {line}")

            return tool_selection

        except Exception as e:
            if verbose:
                print(f"\n⚠️ WARNING: Failed to parse LLM response as JSON: {str(e)}")
                print(f"Falling back to regex extraction of tool names")

            tools = TOOL_REGEX.findall(llm_response or "")
            if not tools:
                if verbose:
                    print(f"\n⚠️ No tools found in LLM response, using default fallback")

                return {
                    "selected_tools": ["get_stock_metrics", "get_company_profile", "get_earnings_surprises"],
                    "facts_to_verify": ["Company performance claims", "Business model descriptions", "Historical earnings performance"],
                    "expectations_to_test": ["Growth projections", "Market's earnings expectations", "Valuation assumptions"],
                    "rationale": {
                        "get_stock_metrics": "Verify factual claims about financial performance",
                        "get_company_profile": "Understand actual business model beyond market narrative",
                        "get_earnings_surprises": "Test market's earnings expectations against reality"
                    },
                    "reasoning_process": "Default reasoning process based on standard fact vs. expectations framework."
                }

            return {
                "selected_tools": tools,
                "facts_to_verify": ["Extracted from news context but not explicitly identified"],
                "expectations_to_test": ["Extracted from news context but not explicitly identified"],
                "rationale": {tool: "Automatically selected based on context" for tool in tools},
                "reasoning_process": "Tools were automatically extracted from the LLM response, which couldn't be parsed as JSON."
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
            "get_stock_peers": MicroTools.get_peers, #how to share results across?
            "get_peer_valuation_comparison": MicroTools.get_peer_valuation_comparison,
            "get_peer_beta_comparison": MicroTools.get_peer_beta_comparison,
            "get_earnings_calendar": MicroTools.get_companies_earnings_calendar,
            "get_earnings_surprises": MicroTools.get_earnings_surprises, #how to share results across?
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
    def process_tool_results_with_llm(self, ticker: str, tool_results: Dict[str, Any], verbose: bool = True) -> Dict[str, Any]:
        """
        Process tool results with LLM to convert them to readable comments (multithreaded version)
        
        Args:
            ticker (str): Stock ticker
            tool_results (Dict): Raw results from executing micro tools
            verbose (bool): Whether to print detailed logs
            
        Returns:
            Dict: Processed results with LLM-generated comments
        """
        if verbose:
            print("\n🧠 Processing tool results with LLM...")

        llm_processed_results: Dict[str, Any] = {}

        def _process_tool(tool_name: str, result: Any) -> Tuple[str, Dict[str, str]]:
            if verbose:
                print(f"  Processing {tool_name}...")
            
            # Convert result to string representation for LLM input
            result_str = str(result)
            if len(result_str) > 8000:  # Limit input size for LLM
                result_str = result_str[:8000] + "... [truncated]"

            # Check if this is a peer comparison tool
            is_peer_tool = any(x in tool_name.lower() for x in ["peer", "comparison", "competitors", "compare"])

            # Create a more structured prompt for LLM based on the tool type
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
                    
                    Remember to STRICTLY separate the factual report (PART 1) from your analysis (PART 2) and ensure you report BOTH {ticker} AND its peers' data.
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

            try:
                # Call the LLM API
                llm_response = deepseek_api_call(prompt).strip()
                
                if verbose:
                    print(f"  ✓ Generated factual report and analysis for {tool_name}")
                
                return tool_name, {"name": tool_name, "result": llm_response}
            except Exception as e:
                error_msg = str(e)
                if verbose:
                    print(f"  ❌ Error processing {tool_name} with LLM: {error_msg}")
                return tool_name, {"name": tool_name, "result": f"Error processing with LLM: {error_msg}"}

        # Use a thread pool to process all tools in parallel
        with ThreadPoolExecutor(max_workers=min(len(tool_results), 8)) as executor:
            futures = {
                executor.submit(_process_tool, tool_name, result): tool_name
                for tool_name, result in tool_results.items()
            }
            for future in as_completed(futures):
                tool_name, processed = future.result()
                llm_processed_results[tool_name] = processed

        return llm_processed_results

    
    @tqdm_timer
    def analyze_results(self, ticker: str, macro_data: Dict, micro_data: Dict, tool_results: Dict, verbose: bool = True) -> Dict:
        """
        Analyze tool results to discover facts and separate them from market expectations
        
        Args:
            ticker (str): Stock ticker being analyzed
            macro_data (Dict): Macro data from rating JSON
            micro_data (Dict): Micro data from rating JSON
            tool_results (Dict): Results from executing micro tools
            verbose (bool): Whether to print detailed logs
            
        Returns:
            Dict containing verified facts, unverified claims, and market expectation analysis
        """
        if verbose:
            print("\n🧠 FACT DISCOVERY PROCESS:")
            print(f"  1. Separating factual information from market expectations/narratives")
            print(f"  2. Verifying factual claims in the news against data from micro tools")
            print(f"  3. Testing market expectations against actual company metrics")
            print(f"  4. Identifying misalignments between facts and market perception")
            print(f"  5. Highlighting overlooked facts in current market narratives")
        
        # Convert tool results to readable string format
        readable_results = {}
        for tool_name, result in tool_results.items():
            if isinstance(result, pd.DataFrame):
                # For DataFrames, include a sample of the actual data
                if not result.empty:
                    sample_data = result.head(3).to_dict(orient='records')
                    cols = ", ".join(result.columns)
                    readable_results[tool_name] = {
                        "summary": f"DataFrame with {result.shape[0]} rows and {result.shape[1]} columns. Columns: {cols}",
                        "sample": sample_data
                    }
                else:
                    readable_results[tool_name] = {"summary": "Empty DataFrame", "sample": []}
            elif isinstance(result, dict):
                if "error" in result:
                    readable_results[tool_name] = {"summary": f"Error: {result['error']}", "details": {}}
                elif "key_metrics" in result:
                    # This is likely from get_stock_metrics
                    readable_results[tool_name] = {
                        "summary": "Key financial metrics retrieved",
                        "details": result["key_metrics"]
                    }
                else:
                    # For other dictionaries, provide detailed contents
                    summary_items = []
                    details = {}
                    
                    for k, v in result.items():
                        if isinstance(v, pd.DataFrame):
                            summary_items.append(f"{k}: DataFrame with {v.shape[0]} rows")
                            if not v.empty:
                                details[k] = v.head(3).to_dict(orient='records')
                        elif isinstance(v, (str, int, float, bool)):
                            summary_items.append(f"{k}: {v}")
                            details[k] = v
                        elif isinstance(v, dict):
                            summary_items.append(f"{k}: Dictionary with {len(v)} items")
                            details[k] = v
                    
                    readable_results[tool_name] = {
                        "summary": ", ".join(summary_items[:5]) + (f" and {len(summary_items) - 5} more..." if len(summary_items) > 5 else ""),
                        "details": details
                    }
            elif isinstance(result, (str, int, float)):
                readable_results[tool_name] = {"summary": str(result), "details": {}}
            else:
                readable_results[tool_name] = {"summary": f"Result of type {type(result).__name__}", "details": {}}
        
        # Generate reasoning text based on macro and micro data
        reasoning = f"""
        Analysis of {ticker} based on macro and micro news:
        
        Based on macro indicators like {macro_data.get('key_indicators', {}).get('GDP_growth_description', 'economic growth')} and 
        {macro_data.get('key_indicators', {}).get('Interest_rate_description', 'interest rates')}, combined with 
        company-specific news like earnings reports and market movements, I have selected these tools to verify facts and test
        market expectations for {ticker}.
        
        The overall macro sentiment is: {macro_data.get('sentiment', 'Not available')}
        The current market trend is: {macro_data.get('trend', 'Not available')}
        
        These tools will help verify factual claims about {ticker}'s performance metrics, recent earnings results,
        valuation compared to peers, and company fundamentals.
        """
        
        # Return a simplified analysis result with only the three requested elements
        analysis_results = {
            "reasoning": reasoning.strip(),
            "tools_used": list(tool_results.keys()),
            "tool_results": readable_results
        }
        
        return analysis_results
    
    @tqdm_timer
    def generate_price_inference(self, ticker: str, inference_hints: Dict, tool_results: Dict, analysis_results: Dict, verbose: bool = True) -> Dict:
        """
        Generate price inference based on micro analysis and inference hints
        
        Args:
            ticker (str): Stock ticker being analyzed
            inference_hints (Dict): Inference hints from macro and micro data
            tool_results (Dict): Results from executing micro tools
            analysis_results (Dict): Analysis results from micro analysis
            verbose (bool): Whether to print detailed logs
            
        Returns:
            Dict containing price inference results
        """
        if verbose:
            print("\n💰 GENERATING PRICE INFERENCE:")
            print(f"  1. Applying inference hints from macro and micro data")
            print(f"  2. Analyzing fundamental factors based on micro analysis")
            print(f"  3. Evaluating trading opportunities (reversal, momentum, etc.)")
            print(f"  4. Formulating direct price action recommendations")
        
        # Convert tool results to a single string for LLM consumption
        tool_results_str = json.dumps(analysis_results.get("tool_results", {}), indent=2, cls=NumpyJSONEncoder)
        if len(tool_results_str) > 4000:  # Limit size for LLM input
            tool_results_str = tool_results_str[:4000] + "... [truncated]"
        
        macro_hint = inference_hints.get("macro_hint", "")
        micro_hint = inference_hints.get("micro_hint", "")
        
        # Build a simpler prompt for price inference
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
            print(f"\n📝 Sending simplified price inference prompt to LLM")
        
        # Call the LLM API
        try:
            llm_response = deepseek_api_call(prompt).strip()
            
            if verbose:
                print(f"\n✅ Successfully generated price inference")
                print(f"  Response: {llm_response[:150]}...")
            
            # Extract trade direction and type using regex
            trade_direction_match = re.search(r'\b(LONG|SHORT|NEUTRAL|WAIT)\b', llm_response, re.IGNORECASE)
            trade_type_match = re.search(r'\b(MOMENTUM|REVERSAL)\b', llm_response, re.IGNORECASE)
            
            trade_direction = trade_direction_match.group(0) if trade_direction_match else "UNDEFINED"
            trade_type = trade_type_match.group(0) if trade_type_match else "UNDEFINED"
            
            # Construct a simple dictionary with the inference
            return {
                "inference": llm_response,
                "trade_direction": trade_direction.upper(),
                "trade_type": trade_type.upper()
            }
            
        except Exception as e:
            error_msg = str(e)
            if verbose:
                print(f"\n❌ Error generating price inference: {error_msg}")
            
            return {
                "inference": f"Error generating price inference: {error_msg}",
                "trade_direction": "ERROR",
                "trade_type": "ERROR"
            }
    
    @tqdm_timer
    def update_rating_json(self, rating_path: str, analysis_results: Dict, tool_selection: Dict, tool_results: Dict, price_inference: Dict = None, verbose: bool = True) -> None:
        """
        Update the rating JSON file with micro analysis results only
        
        Args:
            rating_path (str): Path to the rating JSON file
            analysis_results (Dict): Analysis results to add to the rating JSON
            tool_selection (Dict): Information about which tools were selected and why
            tool_results (Dict): Results from executing each micro tool
            price_inference (Dict, optional): Price inference results
            verbose (bool): Whether to print detailed logs
        """
        # Load the current rating JSON
        with open(rating_path, "r") as f:
            rating_data = json.load(f)
        
        # Get the ticker from the rating data
        ticker = rating_data.get("Ticker", "")
        
        # Process tool results with LLM
        llm_processed_results = self.process_tool_results_with_llm(ticker, tool_results, verbose)
        
        # Preserve existing Micro data
        existing_micro_data = rating_data.get("Micro", {})
        
        # Initialize Micro section if needed
        if "Micro" not in rating_data:
            rating_data["Micro"] = {}
        
        # Preserve important existing Micro fields
        preserve_fields = [
            "Three_Key_Takeaways",
            "Micro_Expectation",
            "Next_Inference_Hint_Micro_News"
        ]
        
        for field in preserve_fields:
            if field in existing_micro_data:
                rating_data["Micro"][field] = existing_micro_data[field]
        
        # Update with the enhanced format
        rating_data["Micro"].update({
            "reasoning": analysis_results.get("reasoning", "No reasoning provided"),
            "tools_used": analysis_results.get("tools_used", []),
            "tool_results": llm_processed_results,  # Use LLM-processed results
            "rationale": tool_selection.get("rationale", {})
        })
        
        # Add price inference if available
        if price_inference:
            rating_data["Micro"]["micro_to_price_next_inference"] = price_inference.get("inference", "")
            
            if verbose:
                print(f"\n💰 Added price inference to Micro section")
                print(f"  Trade direction: {price_inference.get('trade_direction', 'N/A')}")
                print(f"  Trade type: {price_inference.get('trade_type', 'N/A')}")
        
        # Save the updated rating JSON
        with open(rating_path, "w") as f:
            json.dump(rating_data, f, indent=2, cls=NumpyJSONEncoder)
            
        if verbose:
            print(f"\n✅ Updated the Micro section in rating JSON with enhanced format")
            print(f"📊 Tools used: {', '.join(analysis_results.get('tools_used', []))}")
            print(f"💾 File saved: {rating_path}")
        
        # Optionally, clean up legacy keys
        for legacy_key in ["Three_Key_Takeaway_News", "Micro_Expectations"]:
            if legacy_key in rating_data["Micro"]:
                del rating_data["Micro"][legacy_key]
    
    @tqdm_timer
    def run_analysis(self, rating_path: str = None, verbose: bool = True) -> Dict:
        """
        Run the fact discovery process based on macro and micro news
        
        Args:
            rating_path (str, optional): Path to a specific rating JSON file.
                                         If None, the latest rating JSON will be used.
            verbose (bool): Whether to print detailed analysis steps
            
        Returns:
            Dict containing discovered facts and analysis
        """
        # Load the rating JSON
        rating_data = self.load_rating_json(rating_path)
        ticker = rating_data.get("Ticker", "")

        # --- Read both hints ---
        macro_hint = rating_data["Macro"].get("next_inference_hint", "") if "Macro" in rating_data else ""
        micro_news_hint = rating_data["Micro"].get("Next_Inference_Hint_Micro_News", "") if "Micro" in rating_data else ""
        print(f"[DEBUG] Macro Inference Hint: {macro_hint}")
        print(f"[DEBUG] Micro News Inference Hint: {micro_news_hint}")

        # Tool selection
        print("[DEBUG] Calling tool selection...")
        try:
            tool_selection = self.determine_micro_tools(rating_data, verbose=verbose)
            print(f"[DEBUG] Tool selection result: {tool_selection}")
        except Exception as e:
            print(f"[ERROR] Tool selection crashed: {e}")
            tool_selection = {
                "selected_tools": ["get_stock_metrics", "get_company_profile"],
                "facts_to_verify": [],
                "expectations_to_test": [],
                "rationale": {},
                "reasoning_process": "Fallback to default tools due to error."
            }

        if not tool_selection or not tool_selection.get("selected_tools"):
            print("[ERROR] Tool selection failed or returned no tools.")
            return None

        # Tool execution
        print("[DEBUG] Executing selected tools...")
        try:
            tool_results = self.execute_micro_tools(ticker, tool_selection["selected_tools"], verbose=verbose)
            print(f"[DEBUG] Tool execution results: {tool_results}")
        except Exception as e:
            print(f"[ERROR] Tool execution crashed: {e}")
            tool_results = {}

        if not tool_results:
            print("[ERROR] Tool execution failed or returned no results.")
            return None

        # Analysis results
        print("[DEBUG] Analyzing results...")
        try:
            analysis_results = self.analyze_results(
                ticker,
                rating_data.get("Macro", {}),
                rating_data.get("Micro", {}),
                tool_results,
                verbose=verbose
            )
            print(f"[DEBUG] Analysis results: {analysis_results}")
        except Exception as e:
            print(f"[ERROR] Analysis crashed: {e}")
            analysis_results = {}

        if not analysis_results:
            print("[ERROR] Analysis failed or returned no results.")
            return None

        # Price inference (optional)
        print("[DEBUG] Generating price inference...")
        try:
            price_inference = self.generate_price_inference(
                ticker, {}, tool_results, analysis_results, verbose=verbose
            )
            print(f"[DEBUG] Price inference: {price_inference}")
        except Exception as e:
            print(f"[ERROR] Price inference crashed: {e}")
            price_inference = {}

        # Update rating JSON
        print("[DEBUG] Updating rating JSON...")
        try:
            self.update_rating_json(
                rating_path, analysis_results, tool_selection, tool_results, price_inference, verbose=verbose
            )
            print("[DEBUG] Rating JSON updated successfully.")
        except Exception as e:
            print(f"[ERROR] Failed to update rating JSON: {e}")

        # Return results
        return {
            "ticker": ticker,
            "analysis_results": analysis_results,
            "tool_selection": tool_selection,
            "tool_results": tool_results,
            "price_inference": price_inference
        }

# Example usage
if __name__ == "__main__":
    try:
        print("🚀 Starting Micro Analyst Agent")
        print("===============================")
        
        # Initialize the agent
        print("\n🔧 Initializing agent components...")
        agent = MicroAnalystAgent(use_langchain=LANGCHAIN_AVAILABLE)
        
        # Run directly without redirecting output to a log file
        print("\n🔄 Starting analysis process...")
        print("==================================")
        
        # Run the analysis
        results = agent.run_analysis(verbose=True)
        
        print("\n✅ Analysis completed!")
        print("==========================")
        
        # Summary section for quick reference
        print("\n📊 ANALYSIS SUMMARY")
        print(f"Ticker: {results['ticker']}")
        print(f"Tools used: {', '.join(results['analysis_results'].get('tools_used', []))}")
        
        # Show price inference summary
        if 'price_inference' in results:
            print("\n💰 PRICE INFERENCE SUMMARY")
            inference = results['price_inference']
            print(f"Inference: {inference.get('inference', 'N/A')}")
            print(f"Trade Direction: {inference.get('trade_direction', 'N/A')}")
            print(f"Trade Type: {inference.get('trade_type', 'N/A')}")
        
    except Exception as e:
        print(f"Error running Micro Analyst Agent: {e}")
        import traceback
        traceback.print_exc()
