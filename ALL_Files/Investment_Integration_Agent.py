import os
import json
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from LLM_API_CALL import deepseek_api_call

RATING_JSON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Rating_Json")

def get_rating_json_path(ticker):
    return os.path.join(RATING_JSON_DIR, f"{ticker}.json")

class InvestmentIntegrationAgent:
    """
    This agent integrates Macro, Micro, and Price analyses to create a comprehensive 
    investment mindmap that provides a holistic view of the investment opportunity.
    """
    
    def __init__(self, rating_json_path: str = None):
        """Initialize the Investment Integration Agent with a rating JSON file path."""
        self.rating_data = None
        self.ticker = None
        self.rating_json_path = rating_json_path
        
        if rating_json_path:
            self.load_rating_data(rating_json_path)
    
    def load_rating_data(self, rating_json_path: str) -> None:
        """Load rating data from a JSON file."""
        try:
            with open(rating_json_path, 'r') as f:
                self.rating_data = json.load(f)
                
            # Extract ticker symbol
            self.ticker = self.rating_data.get("Ticker", "Unknown")
            print(f"Successfully loaded rating data for {self.ticker}")
            
        except Exception as e:
            print(f"Error loading rating data: {str(e)}")
            self.rating_data = None
    
    def extract_macro_insights(self) -> Dict[str, Any]:
        """Extract key insights from Macro analysis."""
        macro_data = self.rating_data.get("Macro", {})
        
        # Extract key macro elements - directly from top level Macro section
        macro_insights = {
            "summary": macro_data.get("summary", "No macro data available"),
            "sentiment": macro_data.get("sentiment", "NEUTRAL"),
            "trend": macro_data.get("trend", "STABLE"),
            "key_indicators": macro_data.get("key_indicators", {}),
            "favorable_sectors": macro_data.get("favorable_sectors", []),
            "non_favorable_sectors": macro_data.get("non_favorable_sectors", []),
            "macro_catalysts": macro_data.get("macro_catalysts", []),
            "macro_event_recap": macro_data.get("macro_event_recap", "No macro events recap available"),
            # Add more direct extractions from Macro section
            "economic_outlook": macro_data.get("economic_outlook", ""),
            "inflation": macro_data.get("inflation", ""),
            "interest_rates": macro_data.get("interest_rates", ""),
            "gdp_growth": macro_data.get("gdp_growth", ""),
            "next_inference_hint": macro_data.get("next_inference_hint", "")
        }
        
        return macro_insights
    
    def extract_micro_insights(self) -> Dict[str, Any]:
        """Extract key insights from Micro analysis."""
        micro_data = self.rating_data.get("Micro", {})
        
        # Extract tool results
        tool_results = {}
        if "tool_results" in micro_data:
            for tool_name, result in micro_data["tool_results"].items():
                # Extract the factual part and analysis from each tool result
                if "result" in result:
                    result_str = result["result"]
                    # Split result into factual report and analysis if possible
                    parts = result_str.split("**PART 2: ANALYSIS**")
                    if len(parts) > 1:
                        factual = parts[0].replace("**PART 1: FACTUAL REPORT**", "").strip()
                        analysis = parts[1].strip()
                        tool_results[tool_name] = {"factual": factual, "analysis": analysis}
                    else:
                        tool_results[tool_name] = {"full_result": result_str}
        
        # Extract all meaningful data from Micro section
        micro_insights = {
            "reasoning": micro_data.get("reasoning", "No micro reasoning available"),
            "tool_results": tool_results,
            "price_inference": micro_data.get("micro_to_price_next_inference", "No micro price inference available"),
            # Add direct extractions from other Micro fields
            "analysis_results": micro_data.get("analysis_results", {}),
            "key_findings": micro_data.get("analysis_results", {}).get("key_findings", []),
            "summary": micro_data.get("analysis_results", {}).get("summary", ""),
            "recommendation": micro_data.get("analysis_results", {}).get("recommendation", ""),
            "three_key_takeaway": micro_data.get("Three_Key_Takeaway_News", ""),
            "news_sentiment": micro_data.get("news_sentiment", ""),
            "stock_metrics": self._extract_stock_metrics(tool_results.get("get_stock_metrics", {}).get("full_result", ""))
        }
        
        return micro_insights
    
    def _extract_stock_metrics(self, metrics_str):
        """Extract key metrics from the get_stock_metrics tool result."""
        metrics = {}
        if not metrics_str:
            return metrics
            
        for line in metrics_str.split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                metrics[key.strip()] = value.strip()
                
        return metrics
    
    def extract_price_insights(self) -> Dict[str, Any]:
        """Extract key insights from Price analysis."""
        price_data = self.rating_data.get("Price", {})
        price_insights = {
            "risk_reward": price_data.get("risk_reward", {}).get("summary", "No risk/reward data available"),
            "sma_analysis": price_data.get("sma_crossovers", {}).get("summary", "No SMA analysis available"),
            "ema_analysis": price_data.get("ema_crossovers", {}).get("summary", "No EMA analysis available"),
            "macd_analysis": price_data.get("vw_macd", {}).get("summary", "No MACD analysis available"),
            "graph_paths": {
                "risk_reward": price_data.get("risk_reward", {}).get("graph_path"),
                "sma_crossovers": price_data.get("sma_crossovers", {}).get("graph_path"),
                "ema_crossovers": price_data.get("ema_crossovers", {}).get("graph_path"),
                "vw_macd": price_data.get("vw_macd", {}).get("graph_path"),
            }
        }
        return price_insights
    
    def extract_strategy_insights(self) -> Dict[str, Any]:
        """Extract key insights from Strategy analysis."""
        strategy_data = self.rating_data.get("Strategy", {})
        
        # Extract key strategy components
        strategy_insights = {
            "recommended_action": strategy_data.get("recommended_action", "No recommendation available"),
            "strategy_type": strategy_data.get("strategy_type", "Unknown"),
            "rationale": strategy_data.get("rationale", "No rationale available"),
            "risk_level": strategy_data.get("risk_level", "Unknown"),
            "time_horizon": strategy_data.get("time_horizon", "Unknown"),
            "expected_reward": strategy_data.get("expected_reward", "Unknown"),
            "exit_triggers": strategy_data.get("exit_triggers", []),
            "entry_signals": strategy_data.get("entry_signals", [])
        }
        
        return strategy_insights
    
    def generate_investment_mindmap(self) -> str:
        """
        Generate a comprehensive investment mindmap that integrates Macro, Micro, 
        and Price analyses into a cohesive investment thesis as a flowing paragraph.
        Every sentence must include explicit numerical or textual evidence and its JSON source.
        """
        if not self.rating_data:
            return "No rating data available to generate investment mindmap."
        
        macro_insights = self.extract_macro_insights()
        micro_insights = self.extract_micro_insights()
        price_insights = self.extract_price_insights()
        strategy_insights = self.extract_strategy_insights()
        paragraphs = []
        
        # INTRODUCTION
        intro = f"INVESTMENT THESIS FOR {self.ticker}: "
        if strategy_insights['recommended_action'] != "No recommendation available":
            action = strategy_insights['recommended_action']
            strategy_type = strategy_insights['strategy_type']
            intro += f"Our analysis indicates a {action} recommendation (Strategy.recommended_action) based on a {strategy_type} strategy (Strategy.strategy_type). "
        else:
            if "LONG" in price_insights['risk_reward']:
                intro += "Our analysis indicates a potential LONG opportunity (Price.risk_reward). "
            elif "SHORT" in price_insights['risk_reward']:
                intro += "Our analysis indicates a potential SHORT opportunity (Price.risk_reward). "
            else:
                intro += "Our analysis indicates a NEUTRAL stance on this security. "
        paragraphs.append(intro)
        
        # MACRO
        macro_para = "MACROECONOMIC ENVIRONMENT: "
        if macro_insights['gdp_growth']:
            macro_para += f"GDP growth was {macro_insights['gdp_growth']} (Macro.gdp_growth). "
        if macro_insights['interest_rates']:
            macro_para += f"Interest rates are {macro_insights['interest_rates']} (Macro.interest_rates). "
        if macro_insights['inflation']:
            macro_para += f"Inflation is {macro_insights['inflation']} (Macro.inflation). "
        if macro_insights['economic_outlook']:
            macro_para += f"Economic outlook: {macro_insights['economic_outlook']} (Macro.economic_outlook). "
        if macro_insights['favorable_sectors']:
            sectors = ', '.join(macro_insights['favorable_sectors'][:3])
            macro_para += f"Favored sectors: {sectors} (Macro.favorable_sectors). "
        if macro_insights['macro_catalysts']:
            macro_para += f"Key macro catalyst: {macro_insights['macro_catalysts'][0]} (Macro.macro_catalysts). "
        if macro_insights['next_inference_hint']:
            macro_para += f"Forward-looking: {macro_insights['next_inference_hint']} (Macro.next_inference_hint). "
        if not any([macro_insights['gdp_growth'], macro_insights['interest_rates'], macro_insights['inflation'], macro_insights['economic_outlook'], macro_insights['favorable_sectors'], macro_insights['macro_catalysts'], macro_insights['next_inference_hint']]):
            macro_para += "No macro data available. "
        paragraphs.append(macro_para)
        
        # MICRO
        company_para = f"COMPANY ANALYSIS ({self.ticker}): "
        if micro_insights['summary']:
            company_para += f"{micro_insights['summary']} (Micro.summary). "
        if micro_insights['three_key_takeaway']:
            company_para += f"Key insights: {micro_insights['three_key_takeaway']} (Micro.three_key_takeaway). "
        stock_metrics = micro_insights['stock_metrics']
        for metric, value in stock_metrics.items():
            company_para += f"{metric}: {value} (Micro.stock_metrics.{metric}). "
        if micro_insights['key_findings']:
            company_para += f"Key finding: {micro_insights['key_findings'][0]} (Micro.key_findings). "
        if micro_insights['price_inference'] != "No micro price inference available":
            company_para += f"Price inference: {micro_insights['price_inference']} (Micro.price_inference). "
        if micro_insights.get('recommendation'):
            company_para += f"Recommendation: {micro_insights['recommendation']} (Micro.recommendation). "
        if not any([micro_insights['summary'], micro_insights['three_key_takeaway'], stock_metrics, micro_insights['key_findings'], micro_insights['price_inference'], micro_insights.get('recommendation')]):
            company_para += "No micro/company data available. "
        paragraphs.append(company_para)
        
        # PRICE
        price_para = "PRICE ANALYSIS: "
        if price_insights['risk_reward'] != "No risk/reward data available":
            price_para += f"Risk/reward: {price_insights['risk_reward']} (Price.risk_reward). "
        if price_insights['sma_analysis'] != "No SMA analysis available":
            price_para += f"SMA: {price_insights['sma_analysis']} (Price.sma_analysis). "
        if price_insights['ema_analysis'] != "No EMA analysis available":
            price_para += f"EMA: {price_insights['ema_analysis']} (Price.ema_analysis). "
        if price_insights['macd_analysis'] != "No MACD analysis available":
            price_para += f"MACD: {price_insights['macd_analysis']} (Price.macd_analysis). "
        if not any([price_insights['risk_reward'], price_insights['sma_analysis'], price_insights['ema_analysis'], price_insights['macd_analysis']]):
            price_para += "No price/technical data available. "
        paragraphs.append(price_para)
        
        # STRATEGY
        strategy_para = "STRATEGY: "
        if strategy_insights['recommended_action'] != "No recommendation available":
            strategy_para += f"Recommended action: {strategy_insights['recommended_action']} (Strategy.recommended_action). "
        if strategy_insights['strategy_type']:
            strategy_para += f"Strategy type: {strategy_insights['strategy_type']} (Strategy.strategy_type). "
        if strategy_insights['entry_signals']:
            strategy_para += f"Entry signal: {strategy_insights['entry_signals'][0]} (Strategy.entry_signals). "
        if strategy_insights['exit_triggers']:
            strategy_para += f"Exit trigger: {strategy_insights['exit_triggers'][0]} (Strategy.exit_triggers). "
        if strategy_insights['expected_reward'] != "Unknown":
            strategy_para += f"Expected reward: {strategy_insights['expected_reward']} (Strategy.expected_reward). "
        if not any([strategy_insights['recommended_action'], strategy_insights['strategy_type'], strategy_insights['entry_signals'], strategy_insights['exit_triggers'], strategy_insights['expected_reward']]):
            strategy_para += "No strategy data available. "
        paragraphs.append(strategy_para)
        
        # CONCLUSION
        conclusion = "CONCLUSION: "
        if macro_insights['trend']:
            conclusion += f"Macro trend: {macro_insights['trend']} (Macro.trend). "
        if micro_insights.get('recommendation'):
            conclusion += f"Company recommendation: {micro_insights['recommendation']} (Micro.recommendation). "
        if 'LONG' in price_insights['risk_reward'] or 'BULLISH' in price_insights['macd_analysis']:
            conclusion += "Bullish technical indicators (Price.risk_reward/Price.macd_analysis). "
        elif 'SHORT' in price_insights['risk_reward'] or 'BEARISH' in price_insights['macd_analysis']:
            conclusion += "Bearish technical indicators (Price.risk_reward/Price.macd_analysis). "
        else:
            conclusion += "Mixed technical indicators (Price.risk_reward/Price.macd_analysis). "
        if strategy_insights['recommended_action'] != "No recommendation available":
            conclusion += f"Final recommendation: {strategy_insights['recommended_action']} (Strategy.recommended_action). "
        if macro_insights['macro_catalysts']:
            conclusion += f"Key catalyst: {macro_insights['macro_catalysts'][0]} (Macro.macro_catalysts). "
        paragraphs.append(conclusion)
        
        investment_mindmap = "\n\n".join(paragraphs)
        return investment_mindmap
    
    def update_rating_json(self) -> None:
        """Update the rating JSON with the investment mindmap."""
        if not self.rating_data or not self.rating_json_path:
            print("No rating data or path available.")
            return
        
        # Generate the investment mindmap
        investment_mindmap = self.generate_investment_mindmap()
        try:
        # 👈 NEW – produce the compact JSON graph
            mindmap_json = self.Preprocess_Investment_Mindmap(investment_mindmap)
        except Exception as e:
            print(f"❌ Pre-processing failed, keeping only the raw string: {e}")
            mindmap_json = None    

        
        # Print debug info
        print(f"\nUpdating rating JSON at: {self.rating_json_path}")
        print(f"Current Investment_Mindmap field exists: {'Investment_Mindmap' in self.rating_data}")
        print(f"Current Investment_Mindmap length: {len(str(self.rating_data.get('Investment_Mindmap', '')))}")
        
        # Update the rating data
        self.rating_data["Investment_Mindmap"] = investment_mindmap
        if mindmap_json is not None:
            self.rating_data["Investment_Mindmap_json"] = mindmap_json
        
        # Track success state
        update_success = False
        
        # Save the updated rating data
        try:
            # Save with pretty printing for readability
            with open(self.rating_json_path, 'w') as f:
                json.dump(self.rating_data, f, indent=2)
            
            # Verify the update was successful
            with open(self.rating_json_path, 'r') as f:
                verify_data = json.load(f)
                if "Investment_Mindmap" in verify_data and len(str(verify_data["Investment_Mindmap"])) > 0:
                    print(f"Success: Investment_Mindmap field updated with {len(str(verify_data['Investment_Mindmap']))} characters")
                    update_success = True
                else:
                    print("Warning: Investment_Mindmap field was not updated properly")
                    
            if update_success:
                print(f"Successfully updated rating JSON with investment mindmap for {self.ticker}")
            
        except Exception as e:
            print(f"Error updating rating JSON using standard method: {str(e)}")
        
        # If standard method failed, try the force update method
        if not update_success:
            print("Attempting direct file update method...")
            if self.force_update_investment_mindmap(investment_mindmap):
                print("Successfully updated using direct file method")
            else:
                print("All update attempts failed. Please check file permissions and format.")
    
    def run(self, rating_json_path: str = None) -> Optional[str]:
        """
        Run the integration agent, loading the rating JSON using the new {ticker}.json pattern if a ticker is provided.
        """
        if rating_json_path is None and self.ticker:
            rating_json_path = get_rating_json_path(self.ticker)
        if rating_json_path:
            self.load_rating_data(rating_json_path)
        else:
            print("No rating JSON path or ticker provided.")
            return None
        
        if not self.rating_data:
            print("No rating data available.")
            return None
        
        try:
            print(f"\nProcessing rating data for {self.ticker}...")
            
            # Check if all required sections exist
            required_sections = ["Macro", "Micro", "Price", "Strategy"]
            missing_sections = [section for section in required_sections if section not in self.rating_data]
            
            if missing_sections:
                print(f"Warning: The following sections are missing from the rating data: {', '.join(missing_sections)}")
            
            # Generate investment mindmap
            print("Generating investment mindmap...")
            investment_mindmap = self.generate_investment_mindmap()
            
            # Verify mindmap generation
            if not investment_mindmap or len(investment_mindmap) < 50:
                print(f"Warning: Generated investment mindmap seems too short: {len(investment_mindmap)} characters")
            else:
                print(f"Successfully generated investment mindmap: {len(investment_mindmap)} characters")
            
            # Update rating JSON
            print("Updating rating JSON file...")
            self.update_rating_json()
            
            
            return investment_mindmap
        
        except Exception as e:
            print(f"Error running Investment Integration Agent: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def create_backup_file(self, suffix='_backup'):
        """Create a backup of the original rating JSON file."""
        if not self.rating_json_path:
            return False
            
        try:
            backup_path = f"{self.rating_json_path}{suffix}"
            with open(self.rating_json_path, 'r') as src:
                content = src.read()
            
            with open(backup_path, 'w') as dest:
                dest.write(content)
                
            print(f"Created backup at: {backup_path}")
            return True
        except Exception as e:
            print(f"Error creating backup: {str(e)}")
            return False
    
    def force_update_investment_mindmap(self, mindmap):
        """Directly update the investment mindmap in the file using string operations."""
        if not self.rating_json_path or not mindmap:
            return False
            
        try:
            # Create backup first
            self.create_backup_file()
            
            # Read the file content
            with open(self.rating_json_path, 'r') as f:
                content = f.read()
            
            # Check if Investment_Mindmap field exists
            if '"Investment_Mindmap": {}' in content:
                # Replace empty object with string
                new_content = content.replace(
                    '"Investment_Mindmap": {}', 
                    f'"Investment_Mindmap": {json.dumps(mindmap)}'
                )
            elif '"Investment_Mindmap":' in content:
                # Find and replace existing content
                import re
                pattern = r'"Investment_Mindmap":\s*(\{[^}]*\}|\[[^]]*\]|"[^"]*"|[^,}\]]*)'
                match = re.search(pattern, content)
                if match:
                    old_value = match.group(1)
                    new_content = content.replace(
                        f'"Investment_Mindmap": {old_value}',
                        f'"Investment_Mindmap": {json.dumps(mindmap)}'
                    )
                else:
                    new_content = content
            else:
                # Add field before the closing brace
                if content.rstrip().endswith('}'):
                    new_content = content.rstrip()[:-1].rstrip()
                    if new_content.endswith(','):
                        new_content += f' "Investment_Mindmap": {json.dumps(mindmap)}\n}}'
                    else:
                        new_content += f', "Investment_Mindmap": {json.dumps(mindmap)}\n}}'
                else:
                    new_content = content
                    print("Couldn't find proper JSON structure to add Investment_Mindmap")
                    
            # Write updated content back to file
            with open(self.rating_json_path, 'w') as f:
                f.write(new_content)
                
            print(f"Directly updated Investment_Mindmap in file using string operations")
            
            # Verify update
            try:
                with open(self.rating_json_path, 'r') as f:
                    verify_data = json.load(f)
                if "Investment_Mindmap" in verify_data and len(str(verify_data["Investment_Mindmap"])) > 0:
                    print(f"Verification successful: Investment_Mindmap has {len(str(verify_data['Investment_Mindmap']))} characters")
                    return True
                else:
                    print("Verification failed: Investment_Mindmap is missing or empty")
                    return False
            except json.JSONDecodeError:
                print("Warning: File verification failed - JSON parsing error")
                return False
                
        except Exception as e:
            print(f"Error in force_update_investment_mindmap: {str(e)}")
            return False
        
    def Preprocess_Investment_Mindmap(self, narrative: str) -> dict:
        prompt = f"""
You are a mind-map **JSON extractor** specialized in capturing the full multi-headed analytical structure of an investment thesis, and your output will be consumed by a visualization that highlights causal and thematic branches.

VERY IMPORTANT: Every sentence in the input narrative must include explicit numerical or textual evidence and its JSON source (e.g., "GDP growth was 2.5% (Macro.gdp_growth)"). Do not summarize without evidence.

Transform the following investment-analysis text into a JSON object that matches
this TypeScript interface (do not output the interface itself):

interface MindmapData {{
  nodes: {{ id: string; label: string; parent?: string;
            group?: "Macro" | "Company" | "Price" | "Strategy" | "Catalyst" | "Conclusion";
            extra?: any; }}[];
  edges: {{ source: string; target: string;
            relation: "supports" | "contradicts" | "drives" | "monitors" | "hedges"; }}[];
}}

**Required Structure:**
- The root node (n1) must have exactly three direct children:
  1. Macro (group: "Macro")
  2. Micro (group: "Company")
  3. Price (group: "Price")
- All other nodes must be descendants of one of these three branches. Do not add any other direct children to the root.

**Evidence Node Requirements:**
- Every evidence node must include:
  1. The event or concept (e.g., "Company Valuation")
  2. The ground truth: a specific, unbiased fact (numerical or text), e.g., "TSLA DCF is $210, peers GM, F, HMC are $60, $45, $50"
- Use actual values from the JSON data (not just summaries or generic statements).
- Explanations must be logical, detailed, and unbiased.

**Output Example:**
- "Company Valuation" → "TSLA DCF is $210, peers GM, F, HMC are $60, $45, $50"
- "Macro: US GDP Growth" → "Q1 2024 GDP growth was 2.1% (source: Macro.summary)"

**Branch Organization:**
- Macro branch should include: economic outlook, interest rates, inflation, GDP growth, sector impacts, geopolitical factors
- Company branch should include: fundamentals, metrics, news sentiment, earnings, company-specific catalysts
- Price branch should include: technical analysis, risk/reward, moving averages, momentum indicators
- Strategy/Conclusion should synthesize insights from all three branches 

**Additional guidelines for edge classification:**
- **drives**: use for causal links where the source is presented as a driver or cause of the target (e.g. "rate cuts drive EV demand")
- **supports**: use when the source serves as evidence or justification reinforcing the target thesis (e.g. "high beta supports sensitivity to macro shifts")
- **monitors**: use for metrics, indicators or upcoming events to track ("monitor CPI inflation")
- **contradicts**: use when the source expresses a counterargument or headwind to the target ("persistent inflation contradicts consumer spending recovery")
- **hedges**: use for risk-management or offsetting factors ("gold hedges inflation risk")

Also:
- For the main tree, only create edges between a node and its direct children (no edges that skip levels; e.g., do not connect the root directly to grandchildren or deeper descendants).
- Do not create multiple edges from the root to both a branch and its subnodes—each node should have only one parent in the main tree.
- Only add cross-links (edges between nodes in different branches) if there is a strong, explicit relationship in the text (e.g., "hedges", "contradicts", etc.), and never for the main tree structure.
- Ensure **logical flow**: parents represent antecedent concepts; children are direct consequences, evidence or mitigants
- Assign concise unique `id` values in encounter order (`"n1"`, `"n2"`, …)
- Only create an edge when a clear logical relationship exists in the text

**Output rules obey exactly**
1. Return **one single-line JSON string** and nothing else
2. No Markdown, no back-ticks, no comments
3. The JSON must parse with `JSON.parse`
4. ≤ 80 nodes, ≤ 300 edges
5. If you cannot comply, reply only: `ERROR_PARSING_INPUT`

=== BEGIN TEXT ===
{narrative}
=== END TEXT ===
"""

        raw = deepseek_api_call(prompt).strip()
        if raw == "ERROR_PARSING_INPUT":
            raise ValueError("DeepSeek could not parse the investment narrative.")
        return json.loads(raw)

        



if __name__ == "__main__":
    # Check if a rating JSON file path is provided as a command-line argument
    if len(sys.argv) > 1:
        rating_json_path = sys.argv[1]
    else:
        # If no path is provided, look for the most recent rating JSON file
        rating_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Rating_Json")
        
        if not os.path.exists(rating_dir):
            print(f"Rating JSON directory not found: {rating_dir}")
            sys.exit(1)
            
        json_files = [f for f in os.listdir(rating_dir) 
                     if f.endswith(".json") and not f.startswith("Rating_Json")]
        
        if not json_files:
            print("No rating JSON files found.")
            sys.exit(1)
        
        # Sort files by modification time (newest first)
        json_files.sort(key=lambda x: os.path.getmtime(os.path.join(rating_dir, x)), reverse=True)
        rating_json_path = os.path.join(rating_dir, json_files[0])
        
        # Verify this is a valid rating JSON with ticker info
        try:
            with open(rating_json_path, 'r') as f:
                test_data = json.load(f)
                if "Ticker" not in test_data:
                    print(f"Warning: The most recent file {rating_json_path} does not contain ticker information.")
                else:
                    print(f"Using most recent rating JSON file for {test_data['Ticker']}: {rating_json_path}")
        except Exception as e:
            print(f"Error reading most recent rating JSON file: {str(e)}")
            sys.exit(1)
    
    # Initialize and run the Investment Integration Agent
    agent = InvestmentIntegrationAgent()
    mindmap = agent.run(rating_json_path)
    
    if mindmap:
        print("\n==== INVESTMENT MINDMAP ====")
        print(mindmap)
        print("\n==== SUCCESSFULLY UPDATED THE RATING JSON ====")
        print(f"File: {rating_json_path}")
    else:
        print("Failed to generate investment mindmap.")
