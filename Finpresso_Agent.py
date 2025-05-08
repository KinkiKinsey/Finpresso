#!/usr/bin/env python3
# Finpresso_Agent.py - Main orchestration file for the Finpresso AI analysis workflow
from __future__ import annotations         # ★新增：放在所有 import 之前
import sys, pathlib                         # ★新增
sys.path.append(str(pathlib.Path(__file__).parent / "ALL_Files"))   # ★新增
import os
import sys
import json
import shutil
import time
from datetime import datetime
import yfinance as yf
import threading
import queue
import re
import numpy as np
import pandas as pd

# Custom JSON encoder to handle DataFrames and numpy types
class NumpyJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, pd.DataFrame):
            return {"__dataframe__": True, "data": obj.to_dict(orient='records')}
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif pd.isna(obj):
            return None
        return super().default(obj)

# Define paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ALL_FILES_DIR = os.path.join(CURRENT_DIR, "ALL_Files")
RATING_JSON_DIR = os.path.join(ALL_FILES_DIR, "Rating_Json")
MACRO_FILES_DIR = os.path.join(ALL_FILES_DIR, "Macro_Files")
GRAPHS_BASE_DIR = os.path.join(ALL_FILES_DIR, "Graph")

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

from job_registry import jobs               # ★新增：全局 dict
STEP_TOTAL = {"macro": 8, "micro": 17, "price": 8, "strategy": 4}
_step_done: dict[str, int] = {}
_current_job: str | None = None
ANSI_RE = re.compile(r"\x1B\[[0-9;]*m") 

# Stream output queue for real-time updates
output_queue = queue.Queue()
streaming_active = False

def ensure_ticker_graph_directory(ticker):
    """Create a ticker-specific graph directory if it doesn't exist"""
    # Create the base Graph directory if it doesn't exist
    os.makedirs(GRAPHS_BASE_DIR, exist_ok=True)
    
    # Create the ticker-specific graph directory
    ticker_graph_dir = os.path.join(GRAPHS_BASE_DIR, f"{ticker}_Graph")
    os.makedirs(ticker_graph_dir, exist_ok=True)
    
    return ticker_graph_dir

def stream_output():
    """Function to continuously stream output from the queue"""
    global streaming_active
    while streaming_active:
        try:
            message = output_queue.get(timeout=0.1)
            print(message, end='', flush=True)
            output_queue.task_done()
        except queue.Empty:
            pass

def start_streaming():
    """Start the streaming output thread"""
    global streaming_active
    streaming_active = True
    stream_thread = threading.Thread(target=stream_output)
    stream_thread.daemon = True
    stream_thread.start()
    return stream_thread

def stop_streaming():
    """Stop the streaming output thread"""
    global streaming_active
    streaming_active = False

def stream_message(message, color=None, add_newline=True, job_id = None):
    if job_id is None:
        job_id = _current_job   
    txt = f"{color}{message}{Colors.ENDC}" if color else message
    if add_newline:
        txt += '\n'
    output_queue.put(txt)

    # 写入前端日志
    if job_id and job_id in jobs:
        clean = ANSI_RE.sub("", message)
        jobs[job_id].log.append(clean)
        jobs[job_id].message = clean


def stream_progress(title, steps, current_step):
    """Display a progress bar with the current step highlighted"""
    progress = ["○"] * steps
    if 0 <= current_step < steps:
        progress[current_step] = "●"
    
    progress_str = " ".join(progress)
    stream_message(f"\r{Colors.CYAN}{title}: [{progress_str}]{Colors.ENDC}", add_newline=False)

def stream_thinking(message, duration=3, dots=3):
    """Display a thinking animation"""
    base_message = message
    for _ in range(duration):
        for i in range(dots + 1):
            stream_message(f"\r{Colors.CYAN}{base_message}{'.' * i}{' ' * (dots - i)}{Colors.ENDC}", add_newline=False)
            time.sleep(0.3)

def _incr(panel: str, job_id: str | None):
    if job_id and job_id in jobs:
        _step_done[panel] = _step_done.get(panel, 0) + 1
        pct = int(100 * _step_done[panel] / STEP_TOTAL[panel])
        jobs[job_id].panel_progress[panel] = pct

def _finish(panel: str, job_id: str | None):
    if job_id and job_id in jobs:
        jobs[job_id].panel_progress[panel] = 100

def validate_ticker(ticker):
    """Validate if the provided ticker exists on Yahoo Finance"""
    stream_message(f"Validating ticker: {ticker}", Colors.CYAN)
    stream_thinking("Checking ticker data", 2)
    
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        if info and 'regularMarketPrice' in info and info['regularMarketPrice'] is not None:
            stream_message(f"✅ Ticker {ticker} is valid. Current price: ${info['regularMarketPrice']:.2f}", Colors.GREEN)
            return True
        else:
            stream_message(f"❌ Ticker {ticker} does not appear to be valid.", Colors.RED)
            return False
    except Exception as e:
        stream_message(f"❌ Error validating ticker {ticker}: {str(e)}", Colors.RED)
        return False

def create_rating_json(ticker):
    """Create the initial Rating JSON file for the given ticker or reuse existing one"""
    # Ensure Rating_Json directory exists
    os.makedirs(RATING_JSON_DIR, exist_ok=True)
    
    stream_message("Initializing analysis template...", Colors.CYAN)
    
    # Check if a rating JSON for this ticker already exists
    existing_files = [f for f in os.listdir(RATING_JSON_DIR) 
                     if f.startswith(f"{ticker}_Rating_") and f.endswith(".json")]
    
    if existing_files:
        # Find the most recent file for this ticker
        most_recent = max(existing_files, key=lambda f: os.path.getmtime(os.path.join(RATING_JSON_DIR, f)))
        output_path = os.path.join(RATING_JSON_DIR, most_recent)
        
        # Read the existing file
        with open(output_path, 'r') as f:
            rating_data = json.load(f)
        
        stream_message(f"✅ Found existing Rating JSON file for {ticker}: {output_path}", Colors.GREEN)
        stream_message("Reusing this file and updating with new analysis...", Colors.CYAN)
        
        # Clear all analysis sections except Ticker
        rating_data = {
            "Ticker": ticker,
            "Macro": {},
            "Micro": {},
            "Price": {},
            "Strategy": {}
        }
        
        # Save the updated Rating JSON file
        with open(output_path, 'w') as f:
            json.dump(rating_data, f, indent=4)
    else:
        # Create timestamp for the filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(RATING_JSON_DIR, f"{ticker}_Rating_{timestamp}.json")
        
        # Create the initial Rating JSON structure
        rating_data = {
            "Ticker": ticker,
            "Macro": {},
            "Micro": {},
            "Price": {},
            "Strategy": {}
        }
        
        # Simulate processing with streaming output
        stream_thinking("Creating rating template", 2)
        
        # Save the Rating JSON file
        with open(output_path, 'w') as f:
            json.dump(rating_data, f, indent=4)
        
        stream_message(f"✅ Created new Rating JSON file: {output_path}", Colors.GREEN)
    
    return output_path

def run_macro_analyst(rating_json_path, job_id: str | None = None):
    """Run the Macro Analyst Agent and update the Rating JSON with macro analysis"""
    stream_message("\n" + "=" * 50, Colors.YELLOW)
    stream_message(f"{Colors.BOLD}{Colors.YELLOW}MACRO ANALYSIS PHASE{Colors.ENDC}")
    stream_message("=" * 50, Colors.YELLOW)
    
    stream_message("🔍 Initializing Macro Analyst Agent...", Colors.CYAN)
    
    try:
        # Import and run the Macro Analyst Agent
        sys.path.append(ALL_FILES_DIR)
        from Analyst_Macro_Kick_OFF_Agent import run_macro_kick_off_agent
        
        # Simulate macro analysis steps with streaming output
        macro_steps = ["Loading economic data", "Analyzing interest rates", "Evaluating inflation trends", 
                      "Analyzing GDP forecasts", "Reviewing market sentiment", "Checking sector performance", 
                      "Detecting economic cycle signals", "Synthesizing macro view"]
        
        stream_message("\n📊 Macro Analysis Process:", Colors.CYAN)
        for i, step in enumerate(macro_steps):
            stream_progress("Macro Analysis", len(macro_steps), i)
            stream_message(f"\n  - {step}...", Colors.CYAN)
            stream_thinking("  Processing", 2)
            stream_message(f"    ✓ {step} complete", Colors.GREEN)
            time.sleep(0.5)
            _incr("macro", job_id)          

        stream_message("\n🧠 Running Macro inference engine...", Colors.CYAN)
        stream_thinking("Generating macro insights", 3)
        
        # Run the macro analysis to update or create Macro_Analyst_Json.json
        success = run_macro_kick_off_agent()
        if not success:
            stream_message("\n❌ Failed to generate/update macro analysis", Colors.RED)
            return False
            
        # Read the macro analysis from Macro_Files/Macro_Analyst_Json.json
        macro_json_path = os.path.join(ALL_FILES_DIR, 'Macro_Files', 'Macro_Analyst_Json.json')
        try:
            with open(macro_json_path, 'r') as f:
                macro_data = json.load(f)['data']
        except Exception as e:
            stream_message(f"\n❌ Error reading macro analysis: {e}", Colors.RED)
            return False
            
        # Generate next inference hint based on macro data and ticker
        try:
            # Get ticker from rating JSON
            with open(rating_json_path, 'r') as f:
                rating_data = json.load(f)
                ticker = rating_data.get('Ticker')
                
            if not ticker:
                stream_message("\n❌ No ticker found in rating JSON", Colors.RED)
                return False
                
            # Generate inference hint using LLM
            prompt = f"""
            You are a financial analyst creating a forward-looking inference about how macro conditions will affect {ticker}.
            
            Based on the following macro analysis:
            Summary: {macro_data.get('summary', '')}
            Market Sentiment: {macro_data.get('sentiment', '')}
            Market Trend: {macro_data.get('trend', '')}
            Key Indicators:
            - GDP Growth: {macro_data.get('key_indicators', {}).get('GDP_growth_description', '')}
            - Inflation: {macro_data.get('key_indicators', {}).get('Inflation_rate_description', '')}
            - Interest Rates: {macro_data.get('key_indicators', {}).get('Interest_rate_description', '')}
            
            Upcoming Catalysts:
            {', '.join(macro_data.get('macro_catalysts', [])[:3]) if macro_data.get('macro_catalysts') else 'No major catalysts identified'}
            
            Provide a concise, forward-looking inference about how these macro conditions will likely impact {ticker} in the next 1-3 months.
            Focus on:
            1. The most significant macro factor that will affect this stock
            2. Whether this creates a tailwind or headwind
            3. Any specific catalyst that could change this outlook
            
            Return ONLY a single paragraph, no more than 3-4 sentences.
            """
            
            from LLM_API_CALL import deepseek_api_call
            next_inference = deepseek_api_call(prompt).strip()
            
            # Update rating JSON with macro data and inference hint
            rating_data['Macro'] = macro_data
            rating_data['Macro']['next_inference_hint'] = next_inference
            
            with open(rating_json_path, 'w') as f:
                json.dump(rating_data, f, indent=4, cls=NumpyJSONEncoder)
                
            # Display key insights
            stream_message("\n📈 Key Macro Insights:", Colors.BLUE)
            if macro_data.get('summary'):
                stream_message(f"  • Summary: {macro_data['summary']}", Colors.BLUE)
            
            if macro_data.get('sentiment'):
                stream_message(f"  • Market Sentiment: {macro_data['sentiment']}", Colors.BLUE)
                
            if macro_data.get('trend'):
                stream_message(f"  • Market Trend: {macro_data['trend']}", Colors.BLUE)
                
            if macro_data.get('macro_catalysts'):
                stream_message("\n  • Key Catalysts:", Colors.BLUE)
                for catalyst in macro_data['macro_catalysts'][:2]:
                    stream_message(f"    - {catalyst}", Colors.BLUE)
                    
            stream_message("\n🔮 Next Inference Hint:", Colors.YELLOW)
            stream_message(f"  {next_inference}", Colors.YELLOW)
            
            stream_message("\n✅ Macro analysis complete!", Colors.GREEN)
            _finish("macro", job_id)
            return True
            
        except Exception as e:
            stream_message(f"\n❌ Error generating inference hint: {e}", Colors.RED)
            return False
            
    except Exception as e:
        stream_message(f"\n❌ Error in macro analysis: {e}", Colors.RED)
        return False

def run_micro_news(rating_json_path, job_id: str | None = None):
    """Run the Micro News Agent to analyze company news and generate inference hints"""
    stream_message("\n" + "=" * 50, Colors.CYAN)
    stream_message(f"{Colors.BOLD}{Colors.CYAN}MICRO NEWS ANALYSIS PHASE{Colors.ENDC}")
    stream_message("=" * 50, Colors.CYAN)
    
    stream_message("🔍 Initializing Micro News Agent...", Colors.CYAN)
    
    try:
        # Import and run the Micro News Agent
        sys.path.append(ALL_FILES_DIR)
        from Micro_News_Agent import process_ticker
        
        # Get ticker from rating JSON
        with open(rating_json_path, 'r') as f:
            rating_data = json.load(f)
            ticker = rating_data.get("Ticker")
            
        if not ticker:
            stream_message("❌ No ticker found in rating JSON", Colors.RED)
            return False
            
        # Simulate news analysis steps
        news_steps = ["Fetching recent news", "Filtering relevant articles", 
                     "Analyzing news sentiment", "Extracting key takeaways",
                     "Identifying market expectations", "Generating news inference",
                     "Validating news impact", "Synthesizing news view"]
                     
        stream_message("\n📰 News Analysis Process:", Colors.CYAN)
        for i, step in enumerate(news_steps):
            stream_progress("News Analysis", len(news_steps), i)
            stream_message(f"\n  - {step}...", Colors.CYAN)
            stream_thinking("  Processing", 2)
            stream_message(f"    ✓ {step} complete", Colors.GREEN)
            time.sleep(0.5)
            _incr("micro", job_id)
            
        stream_message("\n🧠 Running News inference engine...", Colors.CYAN)
        stream_thinking("Analyzing company news", 3)
        
        # Process the ticker's news
        news_data = process_ticker(ticker)
        if not isinstance(news_data, dict):
            stream_message("\n❌ News data is not a dictionary", Colors.RED)
            return False
            
        # Read current rating JSON
        with open(rating_json_path, 'r') as f:
            rating_data = json.load(f)
            
        # Update Micro section with news data
        if "Micro" not in rating_data:
            rating_data["Micro"] = {}
            
        rating_data["Micro"].update({
            "Three_Key_Takeaways": news_data.get("Three_Key_Takeaways", ""),
            "Micro_Expectation": news_data.get("Micro_Expectation", ""),
            "Next_Inference_Hint_Micro_News": news_data.get("Next_Inference_Hint_Micro_News", "")
        })
        
        # Save updated rating JSON
        with open(rating_json_path, 'w') as f:
            json.dump(rating_data, f, indent=4, cls=NumpyJSONEncoder)
            
        # Display key insights
        stream_message("\n📊 Key News Insights:", Colors.BLUE)
        
        if news_data.get("Three_Key_Takeaways"):
            stream_message("\n  • Key Takeaways:", Colors.BLUE)
            for takeaway in news_data["Three_Key_Takeaways"][:3]:
                stream_message(f"    - {takeaway}", Colors.BLUE)
                
        if news_data.get("Micro_Expectation"):
            stream_message("\n  • Market Expectations:", Colors.BLUE)
            stream_message(f"    {news_data['Micro_Expectation']}", Colors.BLUE)
            
        if news_data.get("Next_Inference_Hint_Micro_News"):
            stream_message("\n🔮 Next Inference Hint:", Colors.YELLOW)
            stream_message(f"  {news_data['Next_Inference_Hint_Micro_News']}", Colors.YELLOW)
            
        stream_message("\n✅ News analysis complete!", Colors.GREEN)
        return True
        
    except Exception as e:
        stream_message(f"\n❌ Error in news analysis: {e}", Colors.RED)
        return False

def run_micro_analyst(rating_json_path, job_id: str | None = None):
    """Run the Micro Analyst Agent and update the Rating JSON with micro analysis"""
    stream_message("\n" + "=" * 50, Colors.BLUE)
    stream_message(f"{Colors.BOLD}{Colors.BLUE}MICRO ANALYSIS PHASE{Colors.ENDC}")
    stream_message("=" * 50, Colors.BLUE)
    
    stream_message("🔍 Initializing Micro Analyst Agent...", Colors.CYAN)
    
    try:
        # Import and run the Micro Analyst Agent
        sys.path.append(ALL_FILES_DIR)
        from Micro_Analyst_Agent import MicroAnalystAgent
        
        # Simulate micro analysis steps with streaming output
        micro_steps = ["Gathering company fundamentals", "Analyzing financial statements", 
                      "Reviewing earnings reports", "Checking analyst ratings", 
                      "Analyzing news sentiment", "Evaluating competitive position",
                      "Checking industry trends", "Synthesizing micro view"]
        
        stream_message("\n🔬 Micro Analysis Process:", Colors.CYAN)
        for i, step in enumerate(micro_steps):
            stream_progress("Micro Analysis", len(micro_steps), i)
            stream_message(f"\n  - {step}...", Colors.CYAN)
            stream_thinking("  Processing", 2)
            stream_message(f"    ✓ {step} complete", Colors.GREEN)
            time.sleep(0.5)
            _incr("micro", job_id)
        
        stream_message("\n🧠 Running Micro inference engine...", Colors.CYAN)
        stream_thinking("Generating company insights", 3)
        
        # Initialize the Micro Analyst Agent
        micro_agent = MicroAnalystAgent()
        
        # Run the micro analysis
        result = micro_agent.run_analysis(rating_path=rating_json_path, verbose=True)
        
        # Extract and display micro insights
        try:
            with open(rating_json_path, 'r') as f:
                rating_data = json.load(f)
                if "Micro" in rating_data and rating_data["Micro"]:
                    stream_message("\n📊 Key Micro Insights:", Colors.BLUE)
                    micro_data = rating_data["Micro"]
                    
                    if "analysis_results" in micro_data and "key_findings" in micro_data["analysis_results"]:
                        for finding in micro_data["analysis_results"]["key_findings"][:3]:  # Show top 3 findings
                            stream_message(f"  • {finding}", Colors.BLUE)
        except Exception as e:
            stream_message(f"Note: Could not extract micro insights: {str(e)}", Colors.YELLOW)
        
        if result:
            stream_message("\n✅ Micro analysis complete!", Colors.GREEN)
            _incr("micro", job_id)
            _finish("micro", job_id) 
            return True
        else:
            stream_message("\n❌ Failed to get micro analysis data", Colors.RED)
            return False
    except Exception as e:
        stream_message(f"\n❌ Error running Micro Analyst Agent: {str(e)}", Colors.RED)
        return False

def run_price_analyst(rating_json_path, job_id: str | None = None):
    """Run the Price Analyst Agent and update the Rating JSON with price analysis and strategy"""
    stream_message("\n" + "=" * 50, Colors.GREEN)
    stream_message(f"{Colors.BOLD}{Colors.GREEN}PRICE ANALYSIS PHASE{Colors.ENDC}")
    stream_message("=" * 50, Colors.GREEN)
    
    stream_message("🔍 Initializing Price Analyst Agent...", Colors.CYAN)
    
    try:
        # Import and run the Price Analyst Agent
        sys.path.append(ALL_FILES_DIR)
        from Price_Agent import PriceAgent
        
        # Get the ticker from rating JSON
        ticker = None
        try:
            with open(rating_json_path, 'r') as f:
                rating_data = json.load(f)
                ticker = rating_data.get("Ticker")
        except Exception as e:
            stream_message(f"Error getting ticker from rating JSON: {str(e)}", Colors.RED)
        
        # Create ticker-specific graph directory
        if ticker:
            ticker_graph_dir = ensure_ticker_graph_directory(ticker)
            stream_message(f"Created graph directory for {ticker}: {ticker_graph_dir}", Colors.CYAN)
        
        # Simulate price analysis steps with streaming output
        price_steps = ["Loading price history", "Analyzing price patterns", 
                      "Calculating technical indicators", "Identifying support/resistance levels", 
                      "Evaluating risk/reward", "Analyzing price volatility",
                      "Identifying entry/exit points", "Formulating investment strategy"]
        
        stream_message("\n📈 Price Analysis Process:", Colors.CYAN)
        for i, step in enumerate(price_steps):
            stream_progress("Price Analysis", len(price_steps), i)
            stream_message(f"\n  - {step}...", Colors.CYAN)
            stream_thinking("  Processing", 2)
            stream_message(f"    ✓ {step} complete", Colors.GREEN)
            _incr("price", job_id)


        
        stream_message("\n🧠 Running Price inference engine...", Colors.CYAN)
        stream_thinking("Generating price strategy", 3)
        
        # Initialize the Price Agent with error handling
        try:
            # Create ticker-specific graph directory and pass it to the Price Agent
            ticker_graph_dir = ensure_ticker_graph_directory(ticker) if ticker else None
            if ticker_graph_dir:
                stream_message(f"Using graph directory: {ticker_graph_dir}", Colors.CYAN)
            
            price_agent = PriceAgent(rating_json_path=rating_json_path, graph_dir=ticker_graph_dir)
            
            # Run the price analysis with error handling
            try:
                price_agent.analyze_price_levels()
            except Exception as e:
                stream_message(f"\n⚠️ Warning: Error during price level analysis: {str(e)}", Colors.YELLOW)
                stream_message("Continuing with limited price analysis...", Colors.YELLOW)
            
            # Generate strategy with error handling
            try:
                price_agent.generate_strategy()
            except Exception as e:
                stream_message(f"\n⚠️ Warning: Error generating strategy: {str(e)}", Colors.YELLOW)
                stream_message("Using simplified strategy generation...", Colors.YELLOW)
            
            # Update the Rating JSON with error handling
            try:
                price_agent.update_rating_json()
            except Exception as e:
                stream_message(f"\n⚠️ Warning: Error updating Rating JSON: {str(e)}", Colors.YELLOW)
                # Manual fallback - write basic price analysis to Rating JSON
                try:
                    with open(rating_json_path, 'r') as f:
                        rating_data = json.load(f)
                    
                    # Add basic Price and Strategy data if missing
                    if "Price" not in rating_data:
                        rating_data["Price"] = {
                            "analysis": {"summary": "Price analysis unavailable due to technical issues"},
                            "technical_indicators": {"status": "unavailable"}
                        }
                    
                    if "Strategy" not in rating_data:
                        rating_data["Strategy"] = {
                            "strategy_type": "NEUTRAL",
                            "conviction_level": "LOW",
                            "dominant_factor": "MICRO",
                            "rationale": "Limited strategy due to price analysis issues. Consider fundamental analysis only."
                        }
                    
                    # Save the updated Rating JSON
                    with open(rating_json_path, 'w') as f:
                        json.dump(rating_data, f, indent=4)
                    
                    stream_message("Created fallback strategy data in Rating JSON", Colors.YELLOW)
                except Exception as fallback_error:
                    stream_message(f"\n❌ Fatal error in fallback strategy creation: {str(fallback_error)}", Colors.RED)
                    return False
            
            # Extract and display strategy insights
            try:
                with open(rating_json_path, 'r') as f:
                    rating_data = json.load(f)
                    if "Strategy" in rating_data and rating_data["Strategy"]:
                        stream_message("\n💡 Investment Strategy:", Colors.BLUE)
                        strategy = rating_data["Strategy"]
                        
                        if "strategy_type" in strategy:
                            stream_message(f"  • Type: {strategy['strategy_type']}", Colors.BLUE)
                        if "conviction_level" in strategy:
                            stream_message(f"  • Conviction: {strategy['conviction_level']}", Colors.BLUE)
                        if "dominant_factor" in strategy:
                            stream_message(f"  • Key Factor: {strategy['dominant_factor']}", Colors.BLUE)
            except Exception as e:
                stream_message(f"Note: Could not extract strategy insights: {str(e)}", Colors.YELLOW)
            
            stream_message("\n✅ Price analysis and strategy complete!", Colors.GREEN)
            _finish("price", job_id)
            return True
            
        except Exception as agent_error:
            stream_message(f"\n⚠️ Error initializing Price Agent: {str(agent_error)}", Colors.YELLOW)
            stream_message("Creating basic fallback strategy...", Colors.YELLOW)
            
            # Create a basic fallback strategy directly
            try:
                with open(rating_json_path, 'r') as f:
                    rating_data = json.load(f)
                
                # Add basic Price and Strategy data
                rating_data["Price"] = {
                    "analysis": {"summary": "Price analysis unavailable due to technical issues"},
                    "technical_indicators": {"status": "unavailable"}
                }
                
                rating_data["Strategy"] = {
                    "strategy_type": "NEUTRAL",
                    "conviction_level": "LOW",
                    "dominant_factor": "MICRO",
                    "rationale": "Fallback strategy due to price agent initialization failure. Review macro and micro data for insights."
                }
                
                # Save the updated Rating JSON
                with open(rating_json_path, 'w') as f:
                    json.dump(rating_data, f, indent=4)
                
                stream_message("Created fallback strategy data in Rating JSON", Colors.YELLOW)
                _finish("price", job_id)
                return True
            except Exception as fallback_error:
                stream_message(f"\n❌ Fatal error in fallback strategy creation: {str(fallback_error)}", Colors.RED)
                return False
    
    except Exception as e:
        stream_message(f"\n❌ Error running Price Analyst Agent: {str(e)}", Colors.RED)
        stream_message("Attempting emergency fallback...", Colors.YELLOW)
        
        # Emergency fallback - try to create a minimal strategy
        try:
            with open(rating_json_path, 'r') as f:
                rating_data = json.load(f)
            
            # Add minimal Strategy data
            rating_data["Strategy"] = {
                "strategy_type": "EMERGENCY_FALLBACK",
                "rationale": "No price analysis available. Please rely on macro and micro data only."
            }
            
            # Save the updated Rating JSON
            with open(rating_json_path, 'w') as f:
                json.dump(rating_data, f, indent=4)
            
            stream_message("Created emergency fallback entry in Rating JSON", Colors.YELLOW)
            return False
        except Exception as emergency_error:
            stream_message(f"\n❌ Critical failure in emergency fallback: {str(emergency_error)}", Colors.RED)
            return False

def run_investment_integration_agent(rating_json_path, job_id: str | None = None):
    """Run the Investment Integration Agent and get the final investment mindmap"""
    stream_message("\n" + "=" * 50, Colors.BLUE)
    stream_message(f"{Colors.BOLD}{Colors.BLUE}INTEGRATION PHASE{Colors.ENDC}")
    stream_message("=" * 50, Colors.BLUE)
    
    stream_message("🔍 Initializing Investment Integration Agent...", Colors.CYAN)
    
    try:
        # Import and run the Investment Integration Agent
        sys.path.append(ALL_FILES_DIR)
        from Investment_Integration_Agent import InvestmentIntegrationAgent
        
        stream_message("\n🧠 Running Investment Integration Agent...", Colors.CYAN)
        stream_thinking("Integrating all analyses", 3)
        _incr("strategy", job_id) 
        
        # Create Graph directory if it doesn't exist (needed for Price_Agent)
        ticker = None
        try:
            with open(rating_json_path, 'r') as f:
                rating_data = json.load(f)
                ticker = rating_data.get("Ticker")
                if ticker:
                    # Create ticker-specific graph directory
                    ensure_ticker_graph_directory(ticker)
                _incr("strategy", job_id) 
        except Exception as e:
            stream_message(f"Warning: Error ensuring Graph directory: {str(e)}", Colors.YELLOW)
        
        # Initialize the Investment Integration Agent
        try:
            investment_agent = InvestmentIntegrationAgent(rating_json_path=rating_json_path)
            
            # Generate the integrated mindmap
            try:
                investment_mindmap = investment_agent.generate_investment_mindmap()
                stream_message("\n✅ Investment mindmap generation complete!", Colors.GREEN)
                
                # Save the mindmap to the Rating JSON
                investment_agent.update_rating_json()
                _incr("strategy", job_id)
                
                # Display the investment mindmap sections with formatting
                if investment_mindmap:
                    stream_message("\n" + "*" * 60, Colors.BLUE)
                    stream_message(f"{Colors.BOLD}📊 FINPRESSO INTEGRATED INVESTMENT MINDMAP{Colors.ENDC}", Colors.BLUE)
                    stream_message("*" * 60, Colors.BLUE)
                    
                    # Split the mindmap into paragraphs and display each with proper formatting
                    sections = investment_mindmap.split("\n\n")
                    for section in sections:
                        # Extract the section title and content
                        if ":" in section:
                            title, content = section.split(":", 1)
                            stream_message(f"\n{Colors.BOLD}{title}:{Colors.ENDC}", Colors.BLUE)
                            stream_message(content.strip(), Colors.CYAN)
                        else:
                            stream_message(section, Colors.CYAN)
                    
                    stream_message("\n" + "*" * 60, Colors.BLUE)
                _incr("strategy", job_id)
                _finish("strategy", job_id) 
                return True
            except Exception as e:
                stream_message(f"\n⚠️ Warning: Error generating investment mindmap: {str(e)}", Colors.YELLOW)
                stream_message("Continuing without investment mindmap...", Colors.YELLOW)
        except Exception as e:
            stream_message(f"\n⚠️ Warning: Error initializing Investment Integration Agent: {str(e)}", Colors.YELLOW)
        
        return False
    except Exception as e:
        stream_message(f"\n❌ Error running Investment Integration Agent: {str(e)}", Colors.RED)
        return False

def display_final_results(rating_json_path, ticker):
    """Display the final analysis results in a nicely formatted way"""
    try:
        with open(rating_json_path, 'r') as f:
            final_data = json.load(f)
        
        stream_message("\n" + "=" * 60, Colors.BOLD)
        stream_message(f"{Colors.BOLD}📊 FINPRESSO AI ANALYSIS SUMMARY: {ticker}{Colors.ENDC}")
        stream_message("=" * 60, Colors.BOLD)
        
        # Extract key aspects from the analysis
        macro_summary = "N/A"
        micro_summary = "N/A"
        price_action = "N/A"
        
        # Extract macro outlook
        if "Macro" in final_data and final_data["Macro"]:
            macro_data = final_data["Macro"]
            if "summary" in macro_data:
                macro_summary = macro_data["summary"]
            elif "economic_outlook" in macro_data:
                macro_summary = macro_data["economic_outlook"]
        
        # Extract micro outlook
        if "Micro" in final_data and final_data["Micro"]:
            micro_data = final_data["Micro"]
            if "analysis_results" in micro_data and "summary" in micro_data["analysis_results"]:
                micro_summary = micro_data["analysis_results"]["summary"]
        
        # Extract price action
        if "Price" in final_data and final_data["Price"]:
            price_data = final_data["Price"]
            if "analysis" in price_data and "summary" in price_data["analysis"]:
                price_action = price_data["analysis"]["summary"]
        
        # Display summary sections
        stream_message(f"\n{Colors.YELLOW}MACRO OUTLOOK:{Colors.ENDC}")
        stream_message(f"{macro_summary[:200]}..." if len(macro_summary) > 200 else macro_summary)
        
        stream_message(f"\n{Colors.BLUE}COMPANY ANALYSIS:{Colors.ENDC}")
        stream_message(f"{micro_summary[:200]}..." if len(micro_summary) > 200 else micro_summary)
        
        stream_message(f"\n{Colors.CYAN}PRICE ACTION:{Colors.ENDC}")
        stream_message(f"{price_action[:200]}..." if len(price_action) > 200 else price_action)
        
        # Display investment strategy
        if "Strategy" in final_data and final_data["Strategy"]:
            strategy = final_data["Strategy"]
            
            stream_message(f"\n{Colors.GREEN}INVESTMENT STRATEGY:{Colors.ENDC}")
            
            if "strategy_type" in strategy:
                stream_message(f"{Colors.BOLD}Strategy Type:{Colors.ENDC} {strategy.get('strategy_type', 'N/A')}")
            
            if "conviction_level" in strategy:
                conviction = strategy.get('conviction_level', 'N/A')
                conviction_color = Colors.GREEN if "high" in conviction.lower() else (Colors.YELLOW if "medium" in conviction.lower() else Colors.RED)
                stream_message(f"{Colors.BOLD}Conviction Level:{Colors.ENDC} {conviction_color}{conviction}{Colors.ENDC}")
            
            if "dominant_factor" in strategy:
                stream_message(f"{Colors.BOLD}Key Driver:{Colors.ENDC} {strategy.get('dominant_factor', 'N/A')}")
            
            if "rationale" in strategy:
                rationale = strategy.get("rationale", "No rationale provided.")
                stream_message(f"\n{Colors.BOLD}Investment Thesis:{Colors.ENDC}")
                stream_message(f"{rationale[:300]}..." if len(rationale) > 300 else rationale)
            
            if "key_catalyst" in strategy:
                stream_message(f"\n{Colors.BOLD}Key Catalyst:{Colors.ENDC} {strategy.get('key_catalyst', 'N/A')}")
        else:
            stream_message(f"\n{Colors.RED}No investment strategy was generated.{Colors.ENDC}")
        
        stream_message(f"\n{Colors.CYAN}Detailed analysis saved to:{Colors.ENDC} {rating_json_path}")
        stream_message("=" * 60, Colors.BOLD)
    except Exception as e:
        stream_message(f"Error displaying final results: {str(e)}", Colors.RED)

def main():
    """Main function to run the entire Finpresso Agent workflow"""
    # Start the streaming output thread
    stream_thread = start_streaming()
    
    try:
        # Display welcome header
        stream_message("\n" + "=" * 60, Colors.BOLD)
        stream_message(f"{Colors.BOLD}🚀 FINPRESSO AI FINANCIAL ANALYSIS{Colors.ENDC}")
        stream_message("=" * 60, Colors.BOLD)
        
        # Get ticker from user input
        ticker = input("\nPlease enter a stock ticker symbol (e.g., AAPL): ").strip().upper()
        
        # Validate the ticker
        if not validate_ticker(ticker):
            stream_message("Please try again with a valid ticker symbol.", Colors.RED)
            stop_streaming()
            return
        
        # Create the initial Rating JSON file
        rating_json_path = create_rating_json(ticker)
        
        # Run the Macro Analyst Agent
        if not run_macro_analyst(rating_json_path):
            stream_message("Failed to complete Macro analysis. Continuing with the workflow...", Colors.YELLOW)
        
        # Run the Micro News Agent
        if not run_micro_news(rating_json_path):
            stream_message("Failed to complete Micro News analysis. Continuing with the workflow...", Colors.YELLOW)
        
        # Run the Micro Analyst Agent
        if not run_micro_analyst(rating_json_path):
            stream_message("Failed to complete Micro analysis. Continuing with the workflow...", Colors.YELLOW)
        
        # Run the Price Analyst Agent
        if not run_price_analyst(rating_json_path):
            stream_message("Failed to complete Price analysis.", Colors.RED)
        
        # Run the Investment Integration Agent
        if not run_investment_integration_agent(rating_json_path):
            stream_message("Failed to complete Investment Integration.", Colors.YELLOW)
        
        # Display final results
        display_final_results(rating_json_path, ticker)
        
    except Exception as e:
        stream_message(f"Error in main execution: {str(e)}", Colors.RED)
    finally:
        # Stop the streaming thread
        stop_streaming()
        stream_thread.join(timeout=1.0)    

def run_analysis(ticker: str, job_id: str | None = None) -> dict:
    global _current_job
    _current_job = job_id
    for k in STEP_TOTAL:
        _step_done[k] = 0
    """Run the complete analysis pipeline for a given ticker"""
    try:
        # Create rating JSON
        rating_json_path = create_rating_json(ticker)
        if not rating_json_path:
            return None
            
        # Run macro analysis
        if not run_macro_analyst(rating_json_path, job_id):
            return None
            
        # Run micro news analysis
        if not run_micro_news(rating_json_path, job_id):
            return None
            
        # Run micro analysis
        if not run_micro_analyst(rating_json_path, job_id):
            return None
            
        # Run price analysis
        if not run_price_analyst(rating_json_path, job_id):
            return None
            
        # Run investment integration
        if not run_investment_integration_agent(rating_json_path, job_id):
            return None
            
        # Display final results
        display_final_results(rating_json_path, ticker)
        
        # Return the final rating data
        try:
            with open(rating_json_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading final rating JSON: {e}")
            return None
            
    except Exception as e:
        print(f"Error in analysis pipeline: {e}")
        return None

if __name__ == "__main__":
    main() 
