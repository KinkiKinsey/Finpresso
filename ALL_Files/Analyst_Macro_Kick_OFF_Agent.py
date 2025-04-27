#!/usr/bin/env python3
# Analyst_Macro_Kick_OFF_Agent.py
# This agent reads macro_data_report.txt and creates a structured JSON file for analysis.

import os
import json
from datetime import datetime, timedelta
import sys
import re
import numpy as np
from typing import Dict, Any, List

# Import directly from the current environment
from LLM_API_CALL import deepseek_api_call, openai_api_call

# Custom JSON encoder to handle NumPy types
class NumpyJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

# Function to call the selected LLM API
def call_llm_api(prompt, model_name="deepseek"):
    """Call the specified LLM API with the given prompt and model name"""
    if model_name.lower() == "deepseek":
        return deepseek_api_call(prompt)
    elif model_name.lower() == "openai":
        return openai_api_call(prompt)
    else:
        print(f"Error: Unsupported model '{model_name}'. Using deepseek as default.")
        return deepseek_api_call(prompt)

def read_macro_data_report():
    """Read the macro data report from the Macro_Files directory inside Tool_Box"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    report_path = os.path.join(script_dir, 'Macro_Files', 'macro_data_report.txt')
    if not os.path.exists(report_path):
        print(f"Error: {report_path} not found")
        return None
    
    print(f"Reading macro data from: {report_path}")
    with open(report_path, 'r') as file:
        return file.read()

def read_macro_news_report():
    """Read the macro news report from the Macro_Files directory inside Tool_Box"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    report_path = os.path.join(script_dir, 'Macro_Files', 'macro_news_report.txt')
    if not os.path.exists(report_path):
        print(f"Error: {report_path} not found")
        return None
    
    print(f"Reading macro news from: {report_path}")
    with open(report_path, 'r') as file:
        return file.read()

def extract_key_influencers(news_text, model_name="deepseek"):
    """Extract key political/government influencers from the news report"""
    
    prompt = f"""
    You are a financial analyst focusing on identifying key macro influencers from news.
    
    Based on the following macro news report, identify the top 1-2 most important political or government figures 
    who are ACTIVELY influencing macroeconomic conditions and market sentiment.
    
    Focus only on people in political/government positions who have the most significant impact on macro trends.
    
    For each influencer, provide:
    1. Their full name and position
    2. A brief description of why they are influential (what policy they control, what they've recently done)
    
    Return your response in this format:
    ```json
    [
      "Full Name (Position) - Brief description of influence"
    ]
    ```
    
    Return ONLY the 1-2 most significant influencers in JSON format.
    
    Here is the news report:
    {news_text}
    """
    
    try:
        response = call_llm_api(prompt, model_name)
        # Try to parse the response as JSON
        try:
            # Extract JSON from the response
            if '```json' in response and '```' in response.split('```json', 1)[1]:
                json_str = response.split('```json', 1)[1].split('```', 1)[0].strip()
            elif '```' in response and '```' in response.split('```', 1)[1]:
                json_str = response.split('```', 1)[1].split('```', 1)[0].strip()
            else:
                json_str = response.strip()
            
            influencers = json.loads(json_str)
            return influencers
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response for influencers: {e}")
            print(f"Raw response: {response}")
            # Try to extract influencers using regex if JSON parsing fails
            influencer_pattern = r'"([^"]+)"'
            matches = re.findall(influencer_pattern, response)
            if matches:
                return matches[:2]  # Return at most 2 influencers
            return ["Federal Reserve (Monetary Authority)"]  # Default fallback
    except Exception as e:
        print(f"Error calling LLM API for influencers: {e}")
        return ["Federal Reserve (Monetary Authority)"]  # Default fallback

def extract_macro_catalysts(news_text, model_name="deepseek"):
    """Extract upcoming economic data release dates and catalysts from the news report"""
    
    prompt = f"""
    You are a financial analyst focusing on identifying upcoming economic data releases and macro catalysts.
    
    Based on the following macro news report, identify the upcoming economic data releases, central bank meetings, 
    or other significant events that will likely impact the markets in the near future.
    
    For each catalyst, include:
    1. Event name 
    2. Expected date (if available)
    3. Brief description of potential market impact
    
    Return your response in this format:
    ```json
    [
      "Event name (Date if available) - Brief description of potential impact"
    ]
    ```
    
    Return ONLY the JSON array with catalysts.
    
    Here is the news report:
    {news_text}
    """
    
    try:
        response = call_llm_api(prompt, model_name)
        # Try to parse the response as JSON
        try:
            # Extract JSON from the response
            if '```json' in response and '```' in response.split('```json', 1)[1]:
                json_str = response.split('```json', 1)[1].split('```', 1)[0].strip()
            elif '```' in response and '```' in response.split('```', 1)[1]:
                json_str = response.split('```', 1)[1].split('```', 1)[0].strip()
            else:
                json_str = response.strip()
            
            catalysts = json.loads(json_str)
            return catalysts
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response for catalysts: {e}")
            print(f"Raw response: {response}")
            # Try to extract catalysts using regex if JSON parsing fails
            catalyst_pattern = r'"([^"]+)"'
            matches = re.findall(catalyst_pattern, response)
            if matches:
                return matches
            return ["Next Fed meeting - Potential interest rate decision"]  # Default fallback
    except Exception as e:
        print(f"Error calling LLM API for catalysts: {e}")
        return ["Next Fed meeting - Potential interest rate decision"]  # Default fallback

def extract_macro_event_recap(report_text, news_text, model_name="deepseek"):
    """Extract a recap of recent significant macro events in chronological order"""
    
    prompt = f"""
    You are a financial analyst creating a chronological recap of recent significant macroeconomic events.
    
    Based on the following macro data and news reports, create a structured recap of the 3-5 most significant 
    macroeconomic events that have occurred recently. Format them in chronological order (most recent first).
    
    For each event, include:
    1. The approximate date
    2. What happened
    3. Its impact on markets or the economy
    
    Return your response as a single string with events separated by paragraph breaks and numbered (1., 2., etc.).
    
    Macro data report:
    {report_text}
    
    Macro news report:
    {news_text}
    """
    
    try:
        response = call_llm_api(prompt, model_name)
        return response.strip()
    except Exception as e:
        print(f"Error calling LLM API for event recap: {e}")
        return "No recent significant macro events identified."

def generate_macro_analysis(report_text, news_text, model_name="deepseek"):
    """Generate macro analysis using the selected LLM API"""
    
    prompt = f"""
    You are a financial macro analyst. Based on the following macro data report, create a structured analysis 
    of the current macroeconomic situation. Fill in ONLY the "Macro" section of the JSON template below with 
    concise and insightful information. Do not include placeholder text or "Example:" prefixes.
    
    Here is the macro data report:
    
    {report_text}
    
    Additional news context:
    
    {news_text}
    
    Please fill in the following JSON structure (ONLY the Macro section):
    ```json
    {{"Macro": {{  
        "summary": "",
        "key_indicators": {{  
            "GDP_growth_description": "",
            "Inflation_rate_description": "",
            "Unemployment_rate_description": "",
            "Interest_rate_description": "",
            "VIX_level_description": ""
        }},
        "sentiment": "",
        "trend": "",
        "influencers": [],
        "favorable_sectors": [],
        "non_favorable_sectors": []
    }}}}
    ```
    
    Return ONLY the valid JSON for the Macro section without additional text or explanations.
    """
    
    try:
        response = call_llm_api(prompt, model_name)
        # Try to parse the response as JSON
        try:
            # First try to extract JSON if it's wrapped in markdown code blocks
            if '```json' in response and '```' in response.split('```json', 1)[1]:
                json_str = response.split('```json', 1)[1].split('```', 1)[0].strip()
            elif '```' in response and '```' in response.split('```', 1)[1]:
                json_str = response.split('```', 1)[1].split('```', 1)[0].strip()
            else:
                json_str = response.strip()
                
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            print(f"Raw response: {response}")
            return None
    except Exception as e:
        print(f"Error calling LLM API: {e}")
        return None

def generate_next_inference_hint(ticker, macro_data, model_name="deepseek"):
    """Generate a next inference hint for the Micro Agent based on macro info and ticker"""
    
    favorable_sectors = macro_data.get('favorable_sectors', [])
    non_favorable_sectors = macro_data.get('non_favorable_sectors', [])
    sentiment = macro_data.get('sentiment', '')
    trend = macro_data.get('trend', '')
    
    prompt = f"""
    You are a financial analyst bridging macro and micro analysis for {ticker}.
    
    Based on the following macro information:
    - Macro sentiment: {sentiment}
    - Macro trend: {trend}
    - Favorable sectors: {', '.join(favorable_sectors) if favorable_sectors else 'None identified'}
    - Non-favorable sectors: {', '.join(non_favorable_sectors) if non_favorable_sectors else 'None identified'}
    
    Generate a concise 3-4 sentence "Next Inference Hint" that:
    1. Summarizes the current macro environment
    2. Provides specific guidance for what the micro analysis should focus on for {ticker}
    3. If sectors are favorable, suggests checking fundamentals and valuation
    4. If sectors are not favorable, suggests examining resilience, potential for outperformance, or positioning for when the business cycle changes
    5. Consider the timeline of the macro events and how they will impact the stock price (see if the event is already priced in or not)
    
    Make your hint VERY directional and actionable, focusing on what specifically to look for in the micro analysis.
    
    Return ONLY the hint text without additional formatting or explanations.
    """
    
    try:
        response = call_llm_api(prompt, model_name)
        return response.strip()
    except Exception as e:
        print(f"Error generating next inference hint: {e}")
        return "Examine how company fundamentals align with current macro environment. Check for sector resilience and competitive positioning."

def save_macro_analyst_json(macro_data):
    """Save the macro analysis to Macro_Files/Macro_Analyst_Json.json"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    macro_dir = os.path.join(script_dir, 'Macro_Files')
    
    try:
        os.makedirs(macro_dir, exist_ok=True)
        print(f"Macro_Files directory path: {macro_dir}")
    except Exception as e:
        print(f"Error creating directory: {e}")
    
    filepath = os.path.join(macro_dir, 'Macro_Analyst_Json.json')
    
    try:
        with open(filepath, 'w') as file:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'data': macro_data
            }, file, indent=2, cls=NumpyJSONEncoder)
        print(f"Successfully wrote macro analysis to {filepath}")
    except Exception as e:
        print(f"Error writing JSON file: {e}")
    
    return filepath

def update_rating_json_with_macro(ticker, macro_data):
    """Update the Rating_Json file's Macro section with new macro data"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    rating_dir = os.path.join(script_dir, 'Rating_Json')
    
    # Find the most recent rating file for the ticker
    rating_files = []
    if os.path.exists(rating_dir):
        for filename in os.listdir(rating_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(rating_dir, filename)
                try:
                    with open(filepath, 'r') as file:
                        data = json.load(file)
                        if data.get('Ticker') == ticker:
                            file_time = os.path.getmtime(filepath)
                            rating_files.append((filepath, file_time))
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
    
    if not rating_files:
        print(f"No existing rating files found for {ticker}")
        return None
    
    # Sort by modification time (newest first)
    rating_files.sort(key=lambda x: x[1], reverse=True)
    most_recent_file = rating_files[0][0]
    
    # Update the file
    try:
        with open(most_recent_file, 'r') as file:
            rating_data = json.load(file)
        
        # Update the Macro section
        rating_data['Macro'] = macro_data
        
        with open(most_recent_file, 'w') as file:
            json.dump(rating_data, file, indent=2, cls=NumpyJSONEncoder)
        
        print(f"Successfully updated Macro section in {most_recent_file}")
        return most_recent_file
    except Exception as e:
        print(f"Error updating rating file: {e}")
        return None

def check_macro_analyst_file_freshness():
    """Check if the Macro_Analyst_Json.json file is less than 24 hours old"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(script_dir, 'Macro_Files', 'Macro_Analyst_Json.json')
    
    if not os.path.exists(filepath):
        print("Macro_Analyst_Json.json does not exist, need to run analysis")
        return False, None
    
    try:
        with open(filepath, 'r') as file:
            data = json.load(file)
        
        # Parse the timestamp
        file_timestamp = datetime.fromisoformat(data.get('timestamp', '2000-01-01T00:00:00'))
        current_time = datetime.now()
        
        # Check if the file is less than 24 hours old
        time_diff = current_time - file_timestamp
        is_fresh = time_diff < timedelta(hours=24)
        
        if is_fresh:
            print(f"Macro analysis is fresh ({time_diff.total_seconds()/3600:.1f} hours old)")
            return True, data.get('data')
        else:
            print(f"Macro analysis is stale ({time_diff.total_seconds()/3600:.1f} hours old)")
            return False, None
    except Exception as e:
        print(f"Error checking file freshness: {e}")
        return False, None

def run_macro_kick_off_agent(model_name="deepseek"):
    """Main function to run the Macro Kick Off Agent"""
    print(f"Starting Macro Kick Off Agent using {model_name} model...")
    
    # Check if we have a fresh macro analysis
    is_fresh, existing_macro_data = check_macro_analyst_file_freshness()
    
    if is_fresh and existing_macro_data:
        print("Using existing macro analysis (less than 24 hours old)")
        return existing_macro_data
    
    # If not fresh or no existing data, run the full analysis
    print("Running full macro analysis...")
    
    # First, run the Macro_Data_Agent.py to update the macro data
    print("Running Macro_Data_Agent.py to update macro data...")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_agent_path = os.path.join(script_dir, 'Macro_Data_Agent.py')
    try:
        import subprocess
        subprocess.run(['python', data_agent_path], check=True)
        print("Macro data update completed successfully")
    except Exception as e:
        print(f"Warning: Failed to run Macro_Data_Agent.py: {e}")
        print("Continuing with existing data files...")
    
    # Next, run the Macro_News_Agent.py to update the macro news
    print("Running Macro_News_Agent.py to update macro news...")
    news_agent_path = os.path.join(script_dir, 'Macro_News_Agent.py')
    try:
        subprocess.run(['python', news_agent_path], check=True)
        print("Macro news update completed successfully")
    except Exception as e:
        print(f"Warning: Failed to run Macro_News_Agent.py: {e}")
        print("Continuing with existing news files...")
    
    # Read the macro data report
    report_text = read_macro_data_report()
    if not report_text:
        print("Error: Failed to read macro data report")
        return None
    else:
        print(f"Successfully read macro data report ({len(report_text)} chars)")
    
    # Read the macro news report for influencer extraction
    news_text = read_macro_news_report()
    if not news_text:
        print("Warning: Macro news report not found, will proceed without news context")
        news_text = ""
    else:
        print(f"Successfully read macro news report ({len(news_text)} chars)")
    
    print("Extracting key influencers from news...")
    # Extract key influencers from news
    key_influencers = extract_key_influencers(news_text, model_name)
    print(f"Extracted influencers: {key_influencers}")
    
    print("Extracting macro catalysts...")
    # Extract macro catalysts from news
    macro_catalysts = extract_macro_catalysts(news_text, model_name)
    print(f"Extracted catalysts: {macro_catalysts}")
    
    print("Creating macro event recap...")
    # Extract a recap of macro events
    macro_event_recap = extract_macro_event_recap(report_text, news_text, model_name)
    print(f"Created event recap of {len(macro_event_recap)} chars")
    
    print("Generating macro analysis...")
    # Generate the macro analysis
    macro_analysis = generate_macro_analysis(report_text, news_text, model_name)
    if not macro_analysis:
        print("Error: Failed to generate macro analysis")
        return None
    
    # Prepare the macro data
    if isinstance(macro_analysis, dict) and 'Macro' in macro_analysis:
        macro_data = macro_analysis['Macro']
        print("Using 'Macro' section from analysis result")
    else:
        macro_data = macro_analysis
        print("Using full analysis result for 'Macro' section")
    
    # Override the influencers with the extracted key influencers
    macro_data['influencers'] = key_influencers
    
    # Add the macro catalysts and event recap
    macro_data['macro_catalysts'] = macro_catalysts
    macro_data['macro_event_recap'] = macro_event_recap
    
    # Save the macro analysis to Macro_Files/Macro_Analyst_Json.json
    macro_filepath = save_macro_analyst_json(macro_data)
    print(f"Macro analysis saved to: {macro_filepath}")
    
    print(f"Macro Kick Off Agent completed successfully!")
    return macro_data

# Run the agent
if __name__ == "__main__":
    # Allow command-line argument for model selection, default to deepseek
    model_name = sys.argv[1] if len(sys.argv) > 1 else "deepseek"
    macro_data = run_macro_kick_off_agent(model_name)
    if macro_data:
        print("Macro analysis completed successfully") 