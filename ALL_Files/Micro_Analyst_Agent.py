#!/usr/bin/env python
# coding: utf-8

import os
import json
import time
from datetime import datetime
import pandas as pd
import glob
import re
import sys
import numpy as np
import subprocess
import importlib.util
from typing import List, Dict, Any, Optional, Tuple

# Custom JSON encoder to handle NumPy types
class NumpyJSONEncoder(json.JSONEncoder):
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
    
    def determine_micro_tools(self, rating_data: Dict, verbose: bool = True) -> Dict:
        """
        Determine which micro tools to use based on the rating data
        
        Args:
            rating_data (Dict): Rating data containing macro and micro information
            verbose (bool): Whether to print detailed logs
            
        Returns:
            Dict containing selected tools and rationale
        """
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
            
        # Build a prompt for the LLM to determine which tools to use
        prompt = f"""
        Based on the following macro and micro news for {ticker}, determine which micro analysis tools would be most useful to separate facts from market expectations and identify potential investment opportunities.

        MACRO DATA:
        {json.dumps(macro_data, indent=2, cls=NumpyJSONEncoder)[:1000]}
        
        MICRO DATA:
        {json.dumps(micro_data, indent=2, cls=NumpyJSONEncoder)[:1000]}
        
        Available micro tools and their purposes:
        1. get_stock_metrics - Get key financial metrics to verify claims about company performance
        2. get_stock_beta - Check actual market correlation against claimed market sensitivity
        3. get_stock_dcf_valuation - Compare actual valuation metrics against market expectations
        4. get_stock_detailed_dcf - Perform detailed valuation analysis to test optimistic/pessimistic views
        5. get_company_profile - Understand the company's actual business model beyond market narratives
        6. get_stock_peers - Identify true industry peers to compare performance claims
        7. get_peer_valuation_comparison - Compare actual valuation to peers to test "undervalued/overvalued" claims
        8. get_peer_beta_comparison - Compare volatility with peers to test risk narratives
        9. get_earnings_calendar - Verify upcoming event dates mentioned in news
        10. get_earnings_surprises - Check if company consistently meets/misses expectations
        11. analyze_earnings_vs_estimates - Compare analyst expectations with actual performance
        
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
        
        # Use LLM to determine tools
        llm_response = deepseek_api_call(prompt)
        
        if verbose:
            print(f"\n🔄 RESPONSE: Received tool selection from LLM")
        
        # Try to parse the response as JSON
        try:
            tool_selection = json.loads(llm_response)
            
            if verbose and "reasoning_process" in tool_selection:
                print(f"\n🧠 REASONING PROCESS:")
                reasoning = tool_selection["reasoning_process"]
                # Print reasoning in chunks
                for line in reasoning.split("\n"):
                    print(f"  {line}")
                    
            return tool_selection
        except Exception as e:
            if verbose:
                print(f"\n⚠️ WARNING: Failed to parse LLM response as JSON: {str(e)}")
                print(f"Falling back to regex extraction of tool names")
            
            # If JSON parsing fails, extract tool names using regex
            tool_regex = r'(get_stock_metrics|get_stock_beta|get_stock_dcf_valuation|get_stock_detailed_dcf|get_company_profile|get_stock_peers|get_peer_valuation_comparison|get_peer_beta_comparison|get_earnings_calendar|get_earnings_surprises|analyze_earnings_vs_estimates)'
            tools = re.findall(tool_regex, llm_response)
            
            # If no tools found, return a default set
            if not tools:
                if verbose:
                    print(f"\n⚠️ WARNING: No tools found in LLM response, using default tools")
                    
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
        raw_results = {}
        
        # Execute each selected tool
        for tool_name in selected_tools:
            if tool_name in tool_map:
                if verbose:
                    print(f"\n⚙️ EXECUTING TOOL: {tool_name}")
                    print(f"  Purpose: {tool_descriptions.get(tool_name, 'No description available')}")
                    print(f"  Input: Ticker = {ticker}")
                
                try:
                    # Special case for get_earnings_calendar which takes a months parameter
                    if tool_name == "get_earnings_calendar":
                        if verbose:
                            print(f"  Special parameter: months = 6")
                        tool_result = tool_map[tool_name](6)  # Default to 6 months
                    else:
                        tool_result = tool_map[tool_name](ticker)
                    
                    # Save the raw result in the cache
                    raw_results[tool_name] = tool_result
                    
                    # Process the result for the regular output
                    results[tool_name] = tool_result
                        
                    if verbose:
                        print(f"  Result: Successfully executed {tool_name}")
                        
                        # Print summary of results if available
                        if isinstance(results[tool_name], dict):
                            keys = list(results[tool_name].keys())
                            if keys:
                                print(f"  Data returned: {', '.join(keys[:5])}")
                                if len(keys) > 5:
                                    print(f"    ... and {len(keys) - 5} more fields")
                        elif isinstance(results[tool_name], (float, int, str)):
                            print(f"  Value: {results[tool_name]}")
                            
                except Exception as e:
                    error_msg = str(e)
                    results[tool_name] = {"error": error_msg}
                    raw_results[tool_name] = {"error": error_msg}
                    if verbose:
                        print(f"  ❌ Error executing {tool_name}: {error_msg}")
            else:
                if verbose:
                    print(f"\n⚠️ UNKNOWN TOOL: {tool_name}")
                results[tool_name] = {"error": "Tool not found"}
                raw_results[tool_name] = {"error": "Tool not found"}
        
        # Save the raw results to a cache file
        self.save_tool_results_cache(ticker, raw_results)
                
        return results
    
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
    
    def process_tool_results_with_llm(self, ticker: str, tool_results: Dict, verbose: bool = True) -> Dict:
        """
        Process tool results with LLM to convert them to readable comments
        
        Args:
            ticker (str): Stock ticker
            tool_results (Dict): Raw results from executing micro tools
            verbose (bool): Whether to print detailed logs
            
        Returns:
            Dict: Processed results with LLM-generated comments
        """
        if verbose:
            print("\n🧠 Processing tool results with LLM...")
        
        llm_processed_results = {}
        
        for tool_name, result in tool_results.items():
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
                llm_response = deepseek_api_call(prompt)
                
                # Clean up the response
                llm_response = llm_response.strip()
                
                llm_processed_results[tool_name] = {
                    "name": tool_name,
                    "result": llm_response
                }
                
                if verbose:
                    print(f"  ✓ Generated factual report and analysis for {tool_name}")
            except Exception as e:
                error_msg = str(e)
                llm_processed_results[tool_name] = {
                    "name": tool_name,
                    "result": f"Error processing with LLM: {error_msg}"
                }
                if verbose:
                    print(f"  ❌ Error processing {tool_name} with LLM: {error_msg}")
        
        return llm_processed_results
    
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
            "Three_Key_Takeaway_News", 
            "Micro_Expectations", 
            "news",
            "key_news",
            "news_summary",
            "Next_Inference_Hint_Micro_News"  # Also preserve the hint for reference
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
        # Get the rating JSON file
        if rating_path is None:
            if verbose:
                print("🔍 STEP 1: Loading the latest rating JSON file")
            rating_path, rating_data = self.get_latest_rating_json()
        else:
            if verbose:
                print(f"🔍 STEP 1: Loading rating JSON from {rating_path}")
            rating_data = self.load_rating_json(rating_path)
        
        ticker = rating_data.get("Ticker", "")
        macro_data = rating_data.get("Macro", {})
        micro_data = rating_data.get("Micro", {})
        
        if not ticker:
            raise ValueError("No ticker found in rating data")
        
        if verbose:
            print(f"\n📊 Analyzing {ticker}...")
            print(f"\n🌎 Macro Context: {macro_data.get('summary', 'N/A')[:200]}...")
            
            # Print key news points if available
            if "key_news" in macro_data:
                print("\n📰 Key Macro News Points:")
                for i, news in enumerate(macro_data.get("key_news", [])[:3], 1):
                    print(f"  {i}. {news[:150]}...")
            
            # Print key micro news if available
            if "Three_Key_Takeaway_News" in micro_data:
                print("\n📰 Key Micro News:")
                print(f"  {micro_data.get('Three_Key_Takeaway_News', '')[:200]}...")
        
        # Determine which micro tools to use for fact-checking
        if verbose:
            print("\n🔍 STEP 2: Identifying fact claims and expectations to verify")
        tool_selection = self.determine_micro_tools(rating_data, verbose)
        selected_tools = tool_selection.get("selected_tools", [])
        
        if verbose:
            print(f"\n🔧 Selected Tools: {', '.join(selected_tools)}")
            
            # Print facts to verify
            facts_to_verify = tool_selection.get("facts_to_verify", [])
            if facts_to_verify:
                print("\n🔍 Facts to Verify:")
                for i, fact in enumerate(facts_to_verify[:5], 1):
                    print(f"  {i}. {fact}")
                
            # Print expectations to test
            expectations_to_test = tool_selection.get("expectations_to_test", [])
            if expectations_to_test:
                print("\n🔮 Market Expectations to Test:")
                for i, expectation in enumerate(expectations_to_test[:5], 1):
                    print(f"  {i}. {expectation}")
            
            print("\n📝 Tool Selection Rationale:")
            for tool, rationale in tool_selection.get("rationale", {}).items():
                print(f"  - {tool}: {rationale}")
        
        # Execute the selected micro tools to gather data for fact-checking
        if verbose:
            print("\n🔍 STEP 3: Gathering data to verify facts and test expectations")
        
        tool_results = {}
        for tool in selected_tools:
            if verbose:
                print(f"  ⚙️ Running {tool}...")
            
            # Execute each tool individually to track progress
            single_result = self.execute_micro_tools(ticker, [tool], verbose)
            tool_results.update(single_result)
            
            if verbose:
                # Print a brief summary of the result
                if tool in single_result:
                    result = single_result[tool]
                    if isinstance(result, dict) and "error" in result:
                        print(f"     ❌ Error: {result['error']}")
                    else:
                        print(f"     ✓ Completed successfully")
        
        # Analyze the results, separating fact from fiction
        if verbose:
            print("\n🔍 STEP 4: Analyzing data to provide reasoning, tools used, and results")
        analysis_results = self.analyze_results(ticker, macro_data, micro_data, tool_results, verbose)
        
        # Generate price inference
        if verbose:
            print("\n🔍 STEP 5: Generating price inference based on micro analysis")
        price_inference = self.generate_price_inference(ticker, self.extract_inference_hints(rating_data, verbose), tool_results, analysis_results, verbose)
        
        # Update the rating JSON with the enhanced output format including LLM-processed insights
        if verbose:
            print("\n🔍 STEP 6: Updating Micro section in rating JSON with enhanced format")
        self.update_rating_json(rating_path, analysis_results, tool_selection, tool_results, price_inference, verbose)
        
        if verbose:
            print(f"\n✅ Analysis for {ticker} completed and saved to {rating_path}")
        
        return {
            "ticker": ticker,
            "tool_selection": tool_selection,
            "tool_results": tool_results,
            "analysis_results": analysis_results,
            "price_inference": price_inference
        }
    
    def run_langchain_agent(self, rating_path: str = None, verbose: bool = True) -> str:
        """
        Run fact discovery using LangChain agent
        
        Args:
            rating_path (str, optional): Path to a specific rating JSON file.
                                         If None, the latest rating JSON will be used.
            verbose (bool): Whether to print detailed logs
            
        Returns:
            String containing agent's response
        """
        if not self.use_langchain:
            return "LangChain agent not available"
        
        # Get the rating JSON file
        if rating_path is None:
            if verbose:
                print("🔍 STEP 1: Loading the latest rating JSON file")
            rating_path, rating_data = self.get_latest_rating_json()
        else:
            if verbose:
                print(f"🔍 STEP 1: Loading rating JSON from {rating_path}")
            rating_data = self.load_rating_json(rating_path)
        
        ticker = rating_data.get("Ticker", "")
        macro_data = rating_data.get("Macro", {})
        micro_data = rating_data.get("Micro", {})
        
        if not ticker:
            return "No ticker found in rating data"
        
        if verbose:
            print(f"\n📊 Discovering facts about {ticker} using LangChain agent...")
            print(f"\n🌎 Macro Context: {macro_data.get('summary', 'N/A')[:200]}...")
        
        # Extract inference hints
        inference_hints = self.extract_inference_hints(rating_data, verbose)
        
        # Prepare the query
        query = f"""
        Discover facts about {ticker} by comparing news data against verified information. Focus ONLY on identifying facts and misalignments with market expectations - do NOT generate investment recommendations.
        
        MACRO CONTEXT:
        {macro_data.get('summary', 'No macro summary available')}
        
        MACRO KEY NEWS:
        {json.dumps(macro_data.get('key_news', []), indent=2, cls=NumpyJSONEncoder)[:500]}
        
        MICRO NEWS:
        {json.dumps(micro_data.get('news', []), indent=2, cls=NumpyJSONEncoder)[:500]}
        
        Your task:
        1. Identify factual claims in the news that need verification
        2. Determine which market expectations should be tested
        3. Use appropriate micro tools to gather data for verification
        4. Compare facts against market expectations
        5. Identify overlooked facts and misalignments
        
        Format your response as follows:
        1. Fact Claims Identified: factual statements from news requiring verification
        2. Market Expectations: current market narratives that should be tested
        3. Tools Used: list of tools you decided to use for verification
        4. Verified Facts: factual claims confirmed by data
        5. Unverified Claims: claims not supported by data
        6. Expectation vs. Reality Gaps: where market expectations differ from verified facts
        7. Overlooked Facts: important facts missing from current market narratives
        """
        
        if verbose:
            print("\n🔍 STEP 2: Running agent to discover facts")
        
        # Run the agent
        response = self.agent_chain.run(query)
        
        if verbose:
            print("\n🔍 STEP 3: Processing agent's fact discovery")
        
        # Extract tool usage from memory if available
        tool_selection = {"selected_tools": [], "rationale": {}, "facts_to_verify": [], "expectations_to_test": []}
        tool_results = {}
        
        # LangChain memory contains information about which tools were used
        if hasattr(self, 'memory') and hasattr(self.memory, 'chat_memory'):
            # Parse memory to find tool usage
            tools_used = []
            for msg in self.memory.chat_memory.messages:
                if hasattr(msg, 'content') and isinstance(msg.content, str):
                    # Look for tool names in the content
                    tool_patterns = [
                        "get_stock_metrics", "get_stock_beta", "get_stock_dcf_valuation", 
                        "get_detailed_dcf", "get_company_profile", "get_stock_peers",
                        "get_peer_valuation_comparison", "get_peer_beta_comparison",
                        "get_earnings_calendar", "get_earnings_surprises", "analyze_earnings_vs_estimates"
                    ]
                    
                    for tool in tool_patterns:
                        if tool in msg.content and tool not in tools_used:
                            tools_used.append(tool)
            
            tool_selection["selected_tools"] = tools_used
            tool_selection["rationale"] = {tool: "Selected by LangChain agent" for tool in tools_used}
            
            # Try to extract facts and expectations from memory
            fact_pattern = r"Facts? to verify:(.+?)(?=Expectations|Market expectations|Tools used|$)"
            expectation_pattern = r"(?:Expectations|Market expectations) to test:(.+?)(?=Tools used|Facts verified|$)"
            
            for msg in self.memory.chat_memory.messages:
                if hasattr(msg, 'content') and isinstance(msg.content, str):
                    # Extract facts to verify
                    fact_matches = re.search(fact_pattern, msg.content, re.DOTALL | re.IGNORECASE)
                    if fact_matches:
                        facts_text = fact_matches.group(1).strip()
                        facts = [f.strip() for f in re.split(r'\n-|\n\d+\.|\n•', facts_text) if f.strip()]
                        tool_selection["facts_to_verify"] = facts
                    
                    # Extract expectations to test
                    expectation_matches = re.search(expectation_pattern, msg.content, re.DOTALL | re.IGNORECASE)
                    if expectation_matches:
                        expectations_text = expectation_matches.group(1).strip()
                        expectations = [e.strip() for e in re.split(r'\n-|\n\d+\.|\n•', expectations_text) if e.strip()]
                        tool_selection["expectations_to_test"] = expectations
            
            # Try to extract results from memory, but this might be limited
            tool_results = {tool: {"result": "Used by LangChain agent (detailed results not captured)"} for tool in tools_used}
        
        # Parse the response to extract structured information
        analysis_results = {
            "verified_facts": [],
            "unverified_claims": [],
            "market_expectations": [],
            "expectation_reality_gaps": [],
            "overlooked_facts": []
        }
        
        # Best-effort extraction of analysis parts
        sections = {
            "verified_facts": r"(?:Verified Facts|VERIFIED FACTS):(.*?)(?=\n\n|\n\d+\.|\n[A-Z]|$)",
            "unverified_claims": r"(?:Unverified Claims|UNVERIFIED CLAIMS):(.*?)(?=\n\n|\n\d+\.|\n[A-Z]|$)",
            "market_expectations": r"(?:Market Expectations|MARKET EXPECTATIONS):(.*?)(?=\n\n|\n\d+\.|\n[A-Z]|$)",
            "expectation_reality_gaps": r"(?:Expectation vs\. Reality Gaps|EXPECTATION VS\. REALITY GAPS):(.*?)(?=\n\n|\n\d+\.|\n[A-Z]|$)",
            "overlooked_facts": r"(?:Overlooked Facts|OVERLOOKED FACTS):(.*?)(?=\n\n|\n\d+\.|\n[A-Z]|$)"
        }
        
        for key, pattern in sections.items():
            matches = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            if matches:
                content = matches.group(1).strip()
                items = [item.strip() for item in re.split(r'\n-|\n\d+\.|\n•', content) if item.strip()]
                analysis_results[key] = items
        
        # Generate price inference based on analysis results
        if verbose:
            print("\n🔍 STEP 4: Generating price inference based on micro analysis")
        price_inference = self.generate_price_inference(ticker, inference_hints, tool_results, analysis_results, verbose)
        
        # Update the rating JSON with ONLY micro facts (not strategy)
        if verbose:
            print("\n🔍 STEP 5: Updating Micro section in rating JSON with enhanced format")
        self.update_rating_json(rating_path, analysis_results, tool_selection, tool_results, price_inference, verbose)
        
        if verbose:
            print(f"\n✅ Fact discovery for {ticker} completed and saved to {rating_path}")
        
        return response

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
