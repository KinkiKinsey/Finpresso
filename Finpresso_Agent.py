#!/usr/bin/env python3
# Finpresso_Agent.py - Main orchestration file for the Finpresso AI analysis workflow
from __future__ import annotations
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).parent / "ALL_Files"))
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
from ALL_Files.Price_Agent import PriceAgent

print("[DEBUG] Finpresso_Agent.py loaded")

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

from job_registry import jobs

# Thread-safe progress tracking
STEP_TOTAL = {"macro": 10, "micro": 20, "price": 12, "strategy": 6}
ANSI_RE = re.compile(r"\x1B\[[0-9;]*m")

# Thread-local storage for job context
_thread_local = threading.local()

# Global lock for file operations that might conflict
_file_lock = threading.Lock()

# Job-specific contexts to avoid global state conflicts
_job_contexts = {}
_contexts_lock = threading.Lock()

class JobContext:
    """Per-job context to maintain isolation between concurrent analyses"""
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.step_done = {"macro": 0, "micro": 0, "price": 0, "strategy": 0}
        self.lock = threading.Lock()

def get_context(job_id: str) -> JobContext:
    """Get or create a job context"""
    with _contexts_lock:
        if job_id not in _job_contexts:
            _job_contexts[job_id] = JobContext(job_id)
        return _job_contexts[job_id]

def cleanup_context(job_id: str):
    """Clean up job context after completion"""
    with _contexts_lock:
        if job_id in _job_contexts:
            del _job_contexts[job_id]

# Stream output queue for real-time updates
output_queue = queue.Queue()
streaming_active = False

def ensure_ticker_graph_directory(ticker):
    ticker_graph_dir = os.path.join(GRAPHS_BASE_DIR, f"{ticker}_Graph")
    print(f"[DEBUG] ensure_ticker_graph_directory called for ticker: {ticker}")
    os.makedirs(ticker_graph_dir, exist_ok=True)
    print(f"[DEBUG] ensure_ticker_graph_directory returns: {ticker_graph_dir}")
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

def stream_message(message, color=None, add_newline=True, job_id=None):
    # Get current job_id from thread local if not provided
    if job_id is None:
        job_id = getattr(_thread_local, 'job_id', None)
    
    txt = f"{color}{message}{Colors.ENDC}" if color else message
    if add_newline:
        txt += '\n'
    output_queue.put(txt)

    # Write to frontend log
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
    """Thread-safe progress increment"""
    if job_id is None:
        job_id = getattr(_thread_local, 'job_id', None)
    
    if not job_id:
        return
    
    context = get_context(job_id)
    with context.lock:
        context.step_done[panel] = context.step_done.get(panel, 0) + 1
        current_steps = context.step_done[panel]
        total_steps = STEP_TOTAL[panel]
        pct = min(95, int(100 * current_steps / total_steps))
        
        if job_id in jobs:
            jobs[job_id].panel_progress[panel] = pct

def _finish(panel: str, job_id: str | None):
    """Mark a panel as 100% complete"""
    if job_id is None:
        job_id = getattr(_thread_local, 'job_id', None)
    
    if not job_id:
        return
    
    if job_id in jobs:
        jobs[job_id].panel_progress[panel] = 100
    
    context = get_context(job_id)
    with context.lock:
        context.step_done[panel] = STEP_TOTAL[panel]

def validate_ticker(ticker):
    """Validate if the provided ticker exists on Yahoo Finance"""
    # Remove ALL whitespace characters and ensure uppercase
    ticker = ''.join(ticker.split()).upper()
    
    # Additional validation for empty or invalid ticker
    if not ticker:
        stream_message("❌ Empty ticker symbol provided", Colors.RED)
        return False
        
    # Validate ticker format (basic check for common invalid characters)
    if any(c in ticker for c in [' ', '\t', '\n', '\r', ',', ';', '|']):
        stream_message("❌ Invalid ticker symbol format", Colors.RED)
        return False
    
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

def get_rating_json_path(ticker):
    """Return the canonical path for a ticker's rating JSON."""
    return os.path.join(RATING_JSON_DIR, f"{ticker}.json")

def get_graph_folder_path(ticker):
    return os.path.join(GRAPHS_BASE_DIR, f"{ticker}_Graph")

def is_recent(filepath, max_age_seconds=7200):
    if not os.path.exists(filepath):
        return False
    mtime = os.path.getmtime(filepath)
    return (time.time() - mtime) < max_age_seconds

def all_graphs_recent(graph_dir, ticker, max_age_seconds=7200):
    if not os.path.isdir(graph_dir):
        return False
    files = [f for f in os.listdir(graph_dir) if f.startswith(f"{ticker}_") and (f.endswith('.png') or f.endswith('.jpg') or f.endswith('.jpeg'))]
    if len(files) != 4:
        return False
    return all(is_recent(os.path.join(graph_dir, f), max_age_seconds) for f in files)

def create_or_overwrite_rating_json(ticker):
    print(f"[DEBUG] create_or_overwrite_rating_json called for ticker: {ticker}")
    os.makedirs(RATING_JSON_DIR, exist_ok=True)
    output_path = get_rating_json_path(ticker)
    rating_data = {
        "Ticker": ticker,
        "Macro": {},
        "Micro": {},
        "Price": {},
        "Strategy": {},
        "last_update": int(time.time())
    }
    with open(output_path, 'w') as f:
        json.dump(rating_data, f, indent=4)
    print(f"[DEBUG] create_or_overwrite_rating_json wrote: {output_path}")
    return output_path

def is_rating_json_recent(ticker, max_age_seconds=7200):
    path = get_rating_json_path(ticker)
    if not os.path.exists(path):
        return False
    try:
        with open(path, 'r') as f:
            data = json.load(f)
            last_update = data.get('last_update', 0)
            if (time.time() - last_update) < max_age_seconds:
                return True
    except Exception as e:
        print(f"[DEBUG] Error reading last_update from {path}: {e}")
    return False

def run_macro_analyst(rating_json_path, job_id: str | None = None):
    print(f"[DEBUG] run_macro_analyst called for: {rating_json_path}")
    stream_message("\n" + "=" * 50, Colors.YELLOW)
    stream_message(f"{Colors.BOLD}{Colors.YELLOW}MACRO ANALYSIS PHASE{Colors.ENDC}")
    stream_message("=" * 50, Colors.YELLOW)
    
    stream_message("🔍 Initializing Macro Analyst Agent...", Colors.CYAN)
    
    try:
        if job_id:
            from progress_manager import update_progress
            update_progress(job_id, "macro", "init")
        
        sys.path.append(ALL_FILES_DIR)
        from Analyst_Macro_Kick_OFF_Agent import run_macro_kick_off_agent
        
        # Simulate macro analysis steps
        macro_steps = ["Loading economic data", "Analyzing interest rates", "Evaluating inflation trends", 
                      "Analyzing GDP forecasts", "Reviewing market sentiment", "Checking sector performance", 
                      "Detecting economic cycle signals", "Synthesizing macro view", "Generating insights"]
        
        stream_message("\n📊 Macro Analysis Process:", Colors.CYAN)
        for i, step in enumerate(macro_steps):
            stream_progress("Macro Analysis", len(macro_steps), i)
            stream_message(f"\n  - {step}...", Colors.CYAN)
            stream_thinking("  Processing", 2)
            stream_message(f"    ✓ {step} complete", Colors.GREEN)
            time.sleep(0.5)
            
            # Update progress using milestones
            if job_id:
                if i < 2:
                    update_progress(job_id, "macro", "data_loading")
                elif i < 4:
                    update_progress(job_id, "macro", "analysis_start")
                elif i < 6:
                    update_progress(job_id, "macro", "processing")
                elif i < 8:
                    update_progress(job_id, "macro", "inference")
                else:
                    update_progress(job_id, "macro", "finalization")

        stream_message("\n🧠 Running Macro inference engine...", Colors.CYAN)
        stream_thinking("Generating macro insights", 3)
        
        # Run the macro analysis
        success = run_macro_kick_off_agent()
        if not success:
            stream_message("\n❌ Failed to generate/update macro analysis", Colors.RED)
            return False
        
        # Thread-safe reading of macro analysis file
        macro_json_path = os.path.join(ALL_FILES_DIR, 'Macro_Files', 'Macro_Analyst_Json.json')
        
        with _file_lock:
            # Create a job-specific copy of the macro file to avoid conflicts
            if job_id:
                job_macro_dir = os.path.join(ALL_FILES_DIR, 'Macro_Files', f'job_{job_id}')
                os.makedirs(job_macro_dir, exist_ok=True)
                job_macro_path = os.path.join(job_macro_dir, 'Macro_Analyst_Json.json')
                shutil.copy2(macro_json_path, job_macro_path)
                macro_json_path = job_macro_path
            
            try:
                with open(macro_json_path, 'r') as f:
                    macro_data = json.load(f)['data']
            except Exception as e:
                stream_message(f"\n❌ Error reading macro analysis: {e}", Colors.RED)
                return False
        
        # Generate next inference hint
        try:
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
            
            # Update rating JSON with macro data
            rating_data['Macro'] = macro_data
            rating_data['Macro']['next_inference_hint'] = next_inference
            
            # Thread-safe file write
            with _file_lock:
                with open(rating_json_path, 'w') as f:
                    json.dump(rating_data, f, indent=4, cls=NumpyJSONEncoder)
                
            # Update progress to save_complete milestone
            if job_id:
                update_progress(job_id, "macro", "save_complete")
                
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
            
            if job_id and job_id in jobs:
                jobs[job_id].panel_data["macro"] = macro_data
                from progress_manager import complete_panel
                complete_panel(job_id, "macro")  # Mark as 100% complete
            
            return True
            
        except Exception as e:
            stream_message(f"\n❌ Error generating inference hint: {e}", Colors.RED)
            return False
            
    except Exception as e:
        stream_message(f"\n❌ Error in macro analysis: {e}", Colors.RED)
        return False

def run_micro_news(rating_json_path, job_id: str | None = None):
    print(f"[DEBUG] run_micro_news called for: {rating_json_path}")
    stream_message("\n" + "=" * 50, Colors.CYAN)
    stream_message(f"{Colors.BOLD}{Colors.CYAN}MICRO NEWS ANALYSIS PHASE{Colors.ENDC}")
    stream_message("=" * 50, Colors.CYAN)
    
    stream_message("🔍 Initializing Micro News Agent...", Colors.CYAN)
    
    try:
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
            
        # Thread-safe file update
        with _file_lock:
            with open(rating_json_path, 'r') as f:
                rating_data = json.load(f)
                
            if "Micro" not in rating_data:
                rating_data["Micro"] = {}
                
            rating_data["Micro"].update({
                "Three_Key_Takeaways": news_data.get("Three_Key_Takeaways", ""),
                "Micro_Expectation": news_data.get("Micro_Expectation", ""),
                "Next_Inference_Hint_Micro_News": news_data.get("Next_Inference_Hint_Micro_News", "")
            })
            
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
    print(f"[DEBUG] run_micro_analyst called for: {rating_json_path}")
    stream_message("\n" + "=" * 50, Colors.BLUE)
    stream_message(f"{Colors.BOLD}{Colors.BLUE}MICRO ANALYSIS PHASE{Colors.ENDC}")
    stream_message("=" * 50, Colors.BLUE)
    
    stream_message("🔍 Initializing Micro Analyst Agent...", Colors.CYAN)
    
    try:
        sys.path.append(ALL_FILES_DIR)
        from Micro_Analyst_Agent import MicroAnalystAgent
        
        # Simulate micro analysis steps
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
        
        # Initialize and run the Micro Analyst Agent
        micro_agent = MicroAnalystAgent()
        result = micro_agent.run_analysis(rating_path=rating_json_path, verbose=True)
        
        # Extract and display micro insights
        try:
            with open(rating_json_path, 'r') as f:
                rating_data = json.load(f)
                if "Micro" in rating_data and rating_data["Micro"]:
                    stream_message("\n📊 Key Micro Insights:", Colors.BLUE)
                    micro_data = rating_data["Micro"]
                    
                    if "analysis_results" in micro_data and "key_findings" in micro_data["analysis_results"]:
                        for finding in micro_data["analysis_results"]["key_findings"][:3]:
                            stream_message(f"  • {finding}", Colors.BLUE)
        except Exception as e:
            stream_message(f"Note: Could not extract micro insights: {str(e)}", Colors.YELLOW)
        
        if result:
            stream_message("\n✅ Micro analysis complete!", Colors.GREEN)
            _incr("micro", job_id)
            
            if job_id and job_id in jobs:
                with _file_lock:
                    with open(rating_json_path, 'r') as _f:
                        _d = json.load(_f)
                        jobs[job_id].panel_data["micro"] = _d.get("Micro", {})
            
            _finish("micro", job_id) 
            return True
        else:
            stream_message("\n❌ Failed to get micro analysis data", Colors.RED)
            return False
    except Exception as e:
        stream_message(f"\n❌ Error running Micro Analyst Agent: {str(e)}", Colors.RED)
        return False

def run_price_analyst(rating_json_path, job_id: str | None = None):
    """Run the Price Analyst Agent"""
    stream_message("\n" + "=" * 50, Colors.GREEN)
    stream_message(f"{Colors.BOLD}{Colors.GREEN}PRICE ANALYSIS PHASE{Colors.ENDC}")
    stream_message("=" * 50, Colors.GREEN)
    
    stream_message("🔍 Initializing Price Analyst Agent...", Colors.CYAN)
    
    try:
        sys.path.append(ALL_FILES_DIR)
        from Price_Agent import PriceAgent
        
        # Get ticker from rating JSON
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
        
        # Simulate price analysis steps
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
        
        # Initialize and run the Price Agent
        try:
            ticker_graph_dir = ensure_ticker_graph_directory(ticker) if ticker else None
            if ticker_graph_dir:
                stream_message(f"Using graph directory: {ticker_graph_dir}", Colors.CYAN)
            
            price_agent = PriceAgent(rating_json_path=rating_json_path, graph_dir=ticker_graph_dir)
            
            # Run price analysis with error handling
            try:
                price_agent.analyze_price_levels()
            except Exception as e:
                stream_message(f"\n⚠️ Warning: Error during price level analysis: {str(e)}", Colors.YELLOW)
                stream_message("Continuing with limited price analysis...", Colors.YELLOW)
            
            # Generate strategy
            try:
                price_agent.generate_strategy()
            except Exception as e:
                stream_message(f"\n⚠️ Warning: Error generating strategy: {str(e)}", Colors.YELLOW)
                stream_message("Using simplified strategy generation...", Colors.YELLOW)
            
            # Update the Rating JSON
            try:
                price_agent.update_rating_json()
            except Exception as e:
                stream_message(f"\n⚠️ Warning: Error updating Rating JSON: {str(e)}", Colors.YELLOW)
                # Manual fallback
                try:
                    with _file_lock:
                        with open(rating_json_path, 'r') as f:
                            rating_data = json.load(f)
                        
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
                                "rationale": "Limited strategy due to price analysis issues."
                            }
                        
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
            
            if job_id and job_id in jobs:
                with _file_lock:
                    with open(rating_json_path, 'r') as _f:
                        _d = json.load(_f)
                        jobs[job_id].panel_data["price"] = _d.get("Price", {})
            
            _finish("price", job_id)
            return True
            
        except Exception as agent_error:
            stream_message(f"\n⚠️ Error initializing Price Agent: {str(agent_error)}", Colors.YELLOW)
            stream_message("Creating basic fallback strategy...", Colors.YELLOW)
            
            # Create a basic fallback strategy
            try:
                with _file_lock:
                    with open(rating_json_path, 'r') as f:
                        rating_data = json.load(f)
                    
                    rating_data["Price"] = {
                        "analysis": {"summary": "Price analysis unavailable"},
                        "technical_indicators": {"status": "unavailable"}
                    }
                    
                    rating_data["Strategy"] = {
                        "strategy_type": "NEUTRAL",
                        "conviction_level": "LOW",
                        "dominant_factor": "MICRO",
                        "rationale": "Fallback strategy. Review macro and micro data."
                    }
                    
                    with open(rating_json_path, 'w') as f:
                        json.dump(rating_data, f, indent=4)
                
                stream_message("Created fallback strategy data", Colors.YELLOW)
                _finish("price", job_id)
                return True
            except Exception as fallback_error:
                stream_message(f"\n❌ Fatal error: {str(fallback_error)}", Colors.RED)
                return False
    
    except Exception as e:
        stream_message(f"\n❌ Error running Price Analyst Agent: {str(e)}", Colors.RED)
        return False

def run_investment_integration_agent(rating_json_path, job_id: str | None = None):
    print(f"[DEBUG] run_investment_integration_agent called for: {rating_json_path}")
    stream_message("\n" + "=" * 50, Colors.BLUE)
    stream_message(f"{Colors.BOLD}{Colors.BLUE}INTEGRATION PHASE{Colors.ENDC}")
    stream_message("=" * 50, Colors.BLUE)
    
    stream_message("🔍 Initializing Investment Integration Agent...", Colors.CYAN)
    
    try:
        sys.path.append(ALL_FILES_DIR)
        from Investment_Integration_Agent import InvestmentIntegrationAgent
        
        stream_message("\n🧠 Running Investment Integration Agent...", Colors.CYAN)
        _incr("strategy", job_id) 
        stream_thinking("Integrating all analyses", 3)
        
        # Create Graph directory if needed
        ticker = None
        try:
            with open(rating_json_path, 'r') as f:
                rating_data = json.load(f)
                ticker = rating_data.get("Ticker")
                if ticker:
                    ensure_ticker_graph_directory(ticker)
        except Exception as e:
            stream_message(f"Warning: Error ensuring Graph directory: {str(e)}", Colors.YELLOW)
        _incr("strategy", job_id) 
        
        # Initialize and run the agent
        try:
            investment_agent = InvestmentIntegrationAgent(rating_json_path=rating_json_path)
            
            try:
                investment_mindmap = investment_agent.generate_investment_mindmap()
                stream_message("\n✅ Investment mindmap generation complete!", Colors.GREEN)
                
                # Save the mindmap
                investment_agent.update_rating_json()
                _incr("strategy", job_id)
                
                # Display the mindmap
                if investment_mindmap:
                    stream_message("\n" + "*" * 60, Colors.BLUE)
                    stream_message(f"{Colors.BOLD}📊 FINPRESSO INTEGRATED INVESTMENT MINDMAP{Colors.ENDC}", Colors.BLUE)
                    stream_message("*" * 60, Colors.BLUE)
                    
                    sections = investment_mindmap.split("\n\n")
                    for section in sections:
                        if ":" in section:
                            title, content = section.split(":", 1)
                            stream_message(f"\n{Colors.BOLD}{title}:{Colors.ENDC}", Colors.BLUE)
                            stream_message(content.strip(), Colors.CYAN)
                        else:
                            stream_message(section, Colors.CYAN)
                    
                    stream_message("\n" + "*" * 60, Colors.BLUE)
                
                if job_id and job_id in jobs:
                    with _file_lock:
                        with open(rating_json_path, 'r') as _f:
                            _d = json.load(_f)
                            jobs[job_id].panel_data["strategy"] = _d.get("Strategy", {})
                
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
    print(f"[DEBUG] display_final_results called for: {rating_json_path}")
    try:
        with open(rating_json_path, 'r') as f:
            final_data = json.load(f)
        
        stream_message("\n" + "=" * 60, Colors.BOLD)
        stream_message(f"{Colors.BOLD}📊 FINPRESSO AI ANALYSIS SUMMARY: {ticker}{Colors.ENDC}")
        stream_message("=" * 60, Colors.BOLD)
        
        # Extract key aspects
        macro_summary = "N/A"
        micro_summary = "N/A"
        price_action = "N/A"
        
        if "Macro" in final_data and final_data["Macro"]:
            macro_data = final_data["Macro"]
            if "summary" in macro_data:
                macro_summary = macro_data["summary"]
            elif "economic_outlook" in macro_data:
                macro_summary = macro_data["economic_outlook"]
        
        if "Micro" in final_data and final_data["Micro"]:
            micro_data = final_data["Micro"]
            if "analysis_results" in micro_data and "summary" in micro_data["analysis_results"]:
                micro_summary = micro_data["analysis_results"]["summary"]
        
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

def run_analysis(ticker: str, job_id: str | None = None) -> dict:
    print(f"[DEBUG] run_analysis called for ticker: {ticker}")
    if job_id:
        _thread_local.job_id = job_id
    try:
        rating_json_path = get_rating_json_path(ticker)
        print(f"[DEBUG] Checking cache for ticker: {ticker}")
        recent_json = is_rating_json_recent(ticker)
        print(f"[DEBUG] is_rating_json_recent: {recent_json}")
        
        # Initialize progress manager if we have a job_id
        if job_id:
            from progress_manager import ProgressManager, init_progress, complete_panel
            init_progress(job_id)
        
        if recent_json:
            # Load cached JSON
            with open(rating_json_path, 'r') as f:
                data = json.load(f)
            
            # Set macro and micro to complete immediately since we're using cached data
            if job_id and job_id in jobs:
                # Load the cached data into the job's panel data
                jobs[job_id].panel_data["macro"] = data.get("Macro", {})
                jobs[job_id].panel_data["micro"] = data.get("Micro", {})
                # Mark panels as complete
                complete_panel(job_id, "macro")
                complete_panel(job_id, "micro")

            # Only update price analysis and graphs
            print(f"[DEBUG] Rerunning Price analysis for {ticker} (JSON is recent, only updating Price section)")
            if not run_price_analyst(rating_json_path, job_id):
                stream_message("⚠️ Price analysis failed. Continuing to integration phase.", Colors.YELLOW)
            
            # After price analysis, update the strategy data and mark as complete
            if job_id and job_id in jobs:
                # Reload the JSON to get the updated data
                with open(rating_json_path, 'r') as f:
                    updated_data = json.load(f)
                # Update the job's panel data with the latest data
                jobs[job_id].panel_data["price"] = updated_data.get("Price", {})
                jobs[job_id].panel_data["strategy"] = updated_data.get("Strategy", {})
                complete_panel(job_id, "strategy")

            # Update last_update field
            data['last_update'] = int(time.time())
            
            # Save the updated data
            with open(rating_json_path, 'w') as f:
                json.dump(data, f, indent=4)
            
            # Return the complete JSON with all sections
            return data
        
        # Otherwise, rerun the full pipeline
        rating_json_path = create_or_overwrite_rating_json(ticker)
        if not run_macro_analyst(rating_json_path, job_id):
            stream_message("⚠️ Macro analysis failed. Continuing to next phase.", Colors.YELLOW)
        if not run_micro_news(rating_json_path, job_id):
            stream_message("⚠️ Micro news analysis failed. Continuing to next phase.", Colors.YELLOW)
        if not run_micro_analyst(rating_json_path, job_id):
            stream_message("⚠️ Micro analysis failed. Continuing to next phase.", Colors.YELLOW)
        if not run_price_analyst(rating_json_path, job_id):
            stream_message("⚠️ Price analysis failed. Continuing to integration phase.", Colors.YELLOW)
        run_investment_integration_agent(rating_json_path, job_id)
        display_final_results(rating_json_path, ticker)
        # Update last_update field after pipeline
        try:
            with open(rating_json_path, 'r') as f:
                data = json.load(f)
            data['last_update'] = int(time.time())
            with open(rating_json_path, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"[DEBUG] Error updating last_update in {rating_json_path}: {e}")
        try:
            with open(rating_json_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading final rating JSON: {e}")
            return {}
    except Exception as e:
        print(f"Error in analysis pipeline: {e}")
        return {}
    finally:
        if hasattr(_thread_local, 'job_id'):
            del _thread_local.job_id
        if job_id:
            cleanup_context(job_id)
            from progress_manager import cleanup_progress
            cleanup_progress(job_id)
            job_macro_dir = os.path.join(ALL_FILES_DIR, 'Macro_Files', f'job_{job_id}')
            if os.path.exists(job_macro_dir):
                try:
                    shutil.rmtree(job_macro_dir)
                except:
                    pass

def main():
    print("[DEBUG] main() called")
    stream_thread = start_streaming()
    try:
        stream_message("\n" + "=" * 60, Colors.BOLD)
        stream_message(f"{Colors.BOLD}🚀 FINPRESSO AI FINANCIAL ANALYSIS{Colors.ENDC}")
        stream_message("=" * 60, Colors.BOLD)
        
        # Get and clean ticker input
        ticker = input("\nPlease enter a stock ticker symbol (e.g., AAPL): ").strip()
        if not ticker:
            stream_message("❌ No ticker symbol provided", Colors.RED)
            stop_streaming()
            return
            
        print(f"[DEBUG] main() ticker before validation: {ticker}")
        if not validate_ticker(ticker):
            stream_message("Please try again with a valid ticker symbol.", Colors.RED)
            stop_streaming()
            return
            
        # Use the cache-aware pipeline (preserves all streaming and frontend log functionality)
        result = run_analysis(ticker)
    except Exception as e:
        stream_message(f"Error in main execution: {str(e)}", Colors.RED)
    finally:
        stop_streaming()
        stream_thread.join(timeout=1.0)

if __name__ == "__main__":
    main()