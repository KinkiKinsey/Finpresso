#!/usr/bin/env python3
# Analyst_Macro_Kick_OFF_Agent.py
# This agent reads macro_data_report.txt and creates a structured JSON file for analysis.

import os
import json
import subprocess
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

def call_llm_api(prompt, model_name="deepseek"):
    """Call the specified LLM API with the given prompt and model name"""
    if model_name.lower() == "deepseek":
        return deepseek_api_call(prompt)
    elif model_name.lower() == "openai":
        return openai_api_call(prompt)
    else:
        print(f"Error: Unsupported model '{model_name}'. Using deepseek as default.")
        return deepseek_api_call(prompt)

def check_macro_file_freshness() -> bool:
    """Check if Macro_Analyst_Json.json is less than 24 hours old"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    macro_json_path = os.path.join(script_dir, 'Macro_Files', 'Macro_Analyst_Json.json')
    
    if not os.path.exists(macro_json_path):
        return False
        
    try:
        with open(macro_json_path, 'r') as f:
            data = json.load(f)
            timestamp = datetime.fromisoformat(data.get('timestamp', '2000-01-01T00:00:00'))
            age = datetime.now() - timestamp
            return age < timedelta(hours=24)
    except:
        return False

def run_data_and_news_agents():
    """Run Macro_Data_Agent.py and Macro_News_Agent.py in parallel"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Run Macro_Data_Agent.py
    data_agent_path = os.path.join(script_dir, 'Macro_Data_Agent.py')
    try:
        subprocess.run(['python', data_agent_path], check=True)
        print("Successfully ran Macro_Data_Agent.py")
    except Exception as e:
        print(f"Error running Macro_Data_Agent.py: {e}")
        return False

    # Run Macro_News_Agent.py
    news_agent_path = os.path.join(script_dir, 'Macro_News_Agent.py')
    try:
        subprocess.run(['python', news_agent_path], check=True)
        print("Successfully ran Macro_News_Agent.py")
    except Exception as e:
        print(f"Error running Macro_News_Agent.py: {e}")
        return False
        
    return True

def read_macro_data_report():
    """Read the macro data report from Macro_Files directory"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    report_path = os.path.join(script_dir, 'Macro_Files', 'macro_data_report.txt')
    
    try:
        with open(report_path, 'r') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading macro data report: {e}")
        return None

def read_macro_news_report():
    """Read the macro news report from Macro_Files directory"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    report_path = os.path.join(script_dir, 'Macro_Files', 'macro_news_report.txt')
    
    try:
        with open(report_path, 'r') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading macro news report: {e}")
        return None

def generate_macro_analysis(report_text: str, news_text: str) -> Dict:
    """Generate complete macro analysis using LLM"""
    prompt = f"""
    You are a financial macro analyst. Based on the following macro data and news reports, create a structured analysis 
    of the current macroeconomic situation. Fill in the JSON template with concise and insightful information.
    
    Macro Data Report:
    {report_text}
    
    Macro News Report:
    {news_text}
    
    Return the following JSON structure:
    ```json
    {{
        "summary": "Brief overview of current macro environment",
        "key_indicators": {{
            "GDP_growth_description": "",
            "Inflation_rate_description": "",
            "Unemployment_rate_description": "",
            "Interest_rate_description": "",
            "VIX_level_description": ""
        }},
        "sentiment": "BULLISH/NEUTRAL/BEARISH",
        "trend": "UPWARD/STABLE/DOWNWARD",
        "influencers": ["Key political/economic figures and their impact"],
        "favorable_sectors": ["Sectors benefiting from current conditions"],
        "non_favorable_sectors": ["Sectors facing headwinds"],
        "macro_catalysts": ["Upcoming events that could impact markets"],
        "macro_event_recap": "Chronological recap of recent significant events"
    }}
    ```
    """
    
    try:
        response = call_llm_api(prompt)
        if '```json' in response:
            json_str = response.split('```json')[1].split('```')[0]
        else:
            json_str = response
        return json.loads(json_str)
    except Exception as e:
        print(f"Error generating macro analysis: {e}")
        return None

def save_macro_json(macro_data: Dict):
    """Save macro analysis to Macro_Files/Macro_Analyst_Json.json"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    macro_dir = os.path.join(script_dir, 'Macro_Files')
    os.makedirs(macro_dir, exist_ok=True)
    
    output_path = os.path.join(macro_dir, 'Macro_Analyst_Json.json')
    try:
        with open(output_path, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'data': macro_data
            }, f, indent=4, cls=NumpyJSONEncoder)
        print(f"Saved macro analysis to {output_path}")
        return True
    except Exception as e:
        print(f"Error saving macro analysis: {e}")
        return False

def run_macro_kick_off_agent() -> bool:
    """Main function to run the Macro Analyst Agent"""
    # Check if we need to update macro analysis
    if check_macro_file_freshness():
        print("Existing macro analysis is fresh (< 24 hours old). No update needed.")
        return True
        
    print("Generating new macro analysis...")
    
    # Run data and news agents
    if not run_data_and_news_agents():
        print("Failed to run data and news agents")
        return False
        
    # Read reports
    report_text = read_macro_data_report()
    news_text = read_macro_news_report()
    
    if not report_text or not news_text:
        print("Failed to read required reports")
        return False
        
    # Generate macro analysis
    macro_data = generate_macro_analysis(report_text, news_text)
    if not macro_data:
        print("Failed to generate macro analysis")
        return False
        
    # Save macro analysis
    return save_macro_json(macro_data)

if __name__ == "__main__":
    success = run_macro_kick_off_agent()
    sys.exit(0 if success else 1) 