import os
import json
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional, Union

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
        
        # Extract key price analysis components
        price_insights = {
            "risk_reward": price_data.get("risk_reward_summary", "No risk/reward data available"),
            "sma_analysis": price_data.get("sma_crossovers_summary", "No SMA analysis available"),
            "ema_analysis": price_data.get("ema_crossovers_summary", "No EMA analysis available"),
            "macd_analysis": price_data.get("vw_macd_summary", "No MACD analysis available"),
            "graph_paths": price_data.get("graph_paths", {})
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
        
        Returns:
            str: The investment mindmap as a detailed paragraph.
        """
        if not self.rating_data:
            return "No rating data available to generate investment mindmap."
        
        # Extract insights from each analysis component
        macro_insights = self.extract_macro_insights()
        micro_insights = self.extract_micro_insights()
        price_insights = self.extract_price_insights()
        strategy_insights = self.extract_strategy_insights()
        
        # Start building the comprehensive investment narrative
        paragraphs = []
        
        # INTRODUCTION - Short summary of overall thesis
        intro = f"INVESTMENT THESIS FOR {self.ticker}: "
        
        # Add strategy type and direction from strategy insights if available
        if strategy_insights['recommended_action'] != "No recommendation available":
            action = strategy_insights['recommended_action']
            strategy_type = strategy_insights['strategy_type']
            intro += f"Our analysis indicates a {action} recommendation based on a {strategy_type} strategy. "
        else:
            # Fallback to price insights
            if "LONG" in price_insights['risk_reward']:
                intro += "Our analysis indicates a potential LONG opportunity. "
            elif "SHORT" in price_insights['risk_reward']:
                intro += "Our analysis indicates a potential SHORT opportunity. "
            else:
                intro += "Our analysis indicates a NEUTRAL stance on this security. "
        
        paragraphs.append(intro)
        
        # MACRO ENVIRONMENT - Detailed paragraph about macro backdrop
        macro_para = "MACROECONOMIC ENVIRONMENT: "
        
        # Add economic outlook if available
        if macro_insights['economic_outlook']:
            macro_para += f"{macro_insights['economic_outlook']} "
        elif macro_insights['summary'] != "No macro data available":
            macro_para += f"{macro_insights['summary']} "
        else:
            macro_para += "The current economic environment presents a mixed picture. "
        
        # Add interest rates, inflation, GDP growth insights if available
        if macro_insights['interest_rates']:
            macro_para += f"Interest rates: {macro_insights['interest_rates']} "
        
        if macro_insights['inflation']:
            macro_para += f"Inflation: {macro_insights['inflation']} "
        
        if macro_insights['gdp_growth']:
            macro_para += f"GDP growth: {macro_insights['gdp_growth']} "
        
        # Add sector impacts
        if macro_insights['favorable_sectors']:
            sectors = ", ".join(macro_insights['favorable_sectors'][:3])
            macro_para += f"This environment particularly favors the {sectors} sectors. "
        
        # Add macro catalysts if available
        if macro_insights['macro_catalysts']:
            catalysts = macro_insights['macro_catalysts'][0]
            macro_para += f"A key upcoming catalyst to monitor is {catalysts}. "
        
        # Add inference hint if available for forward-looking perspective
        if macro_insights['next_inference_hint']:
            macro_para += f"Looking forward, {macro_insights['next_inference_hint']} "
        
        paragraphs.append(macro_para)
        
        # COMPANY ANALYSIS - Detailed paragraph about the company
        company_para = f"COMPANY ANALYSIS ({self.ticker}): "
        
        # Add company summary from micro analysis
        if micro_insights['summary']:
            company_para += f"{micro_insights['summary']} "
        elif micro_insights['three_key_takeaway']:
            company_para += f"Key insights: {micro_insights['three_key_takeaway']} "
        
        # Add key financial metrics if available
        stock_metrics = micro_insights['stock_metrics']
        metrics_to_include = ['PE_Ratio', 'Revenue_Growth', 'Profit_Margin', 'Current_Price']
        metrics_included = []
        
        for metric in metrics_to_include:
            if metric in stock_metrics:
                metrics_included.append(f"{metric}: {stock_metrics[metric]}")
        
        if metrics_included:
            company_para += f"Key metrics include {', '.join(metrics_included)}. "
        
        # Add key findings from analysis
        if micro_insights['key_findings']:
            findings = micro_insights['key_findings'][0]
            company_para += f"Our analysis highlights that {findings} "
        
        # Add micro to price inference
        if micro_insights['price_inference'] != "No micro price inference available":
            company_para += f"Based on these fundamentals, {micro_insights['price_inference']} "
        
        paragraphs.append(company_para)
        
        # PRICE ANALYSIS - Detailed paragraph about price action and technicals
        price_para = "PRICE ANALYSIS: "
        
        # Add risk/reward analysis
        if price_insights['risk_reward'] != "No risk/reward data available":
            price_para += f"{price_insights['risk_reward'].split('.')[0] if '.' in price_insights['risk_reward'] else price_insights['risk_reward']}. "
        
        # Add moving average insights
        ma_insights = []
        
        if price_insights['sma_analysis'] != "No SMA analysis available":
            ma_insights.append(f"SMA analysis: {price_insights['sma_analysis'].split('.')[0] if '.' in price_insights['sma_analysis'] else price_insights['sma_analysis']}")
        
        if price_insights['ema_analysis'] != "No EMA analysis available":
            ma_insights.append(f"EMA analysis: {price_insights['ema_analysis'].split('.')[0] if '.' in price_insights['ema_analysis'] else price_insights['ema_analysis']}")
        
        if ma_insights:
            price_para += f"Moving averages analysis indicates {' and '.join(ma_insights)}. "
        
        # Add MACD analysis
        if price_insights['macd_analysis'] != "No MACD analysis available":
            price_para += f"MACD analysis shows {price_insights['macd_analysis'].split('.')[0] if '.' in price_insights['macd_analysis'] else price_insights['macd_analysis']}. "
        
        paragraphs.append(price_para)
        
        # INTEGRATED STRATEGY - Detailed paragraph combining all insights into cohesive strategy
        strategy_para = "INTEGRATED INVESTMENT STRATEGY: "
        
        # Start with the recommendation
        if strategy_insights['recommended_action'] != "No recommendation available":
            strategy_para += f"We recommend a {strategy_insights['recommended_action']} strategy "
            
            # Add risk level and time horizon if available
            if strategy_insights['risk_level'] != "Unknown":
                strategy_para += f"with {strategy_insights['risk_level'].lower()} risk "
            
            if strategy_insights['time_horizon'] != "Unknown":
                strategy_para += f"over a {strategy_insights['time_horizon'].lower()} time horizon. "
            else:
                strategy_para += ". "
        else:
            # Fallback to synthesized recommendation
            price_signal = "BULLISH" if "LONG" in price_insights['risk_reward'] or "BULLISH" in price_insights['macd_analysis'] else "BEARISH" if "SHORT" in price_insights['risk_reward'] or "BEARISH" in price_insights['macd_analysis'] else "NEUTRAL"
            strategy_para += f"Based on our analysis, we suggest a {price_signal} approach. "
        
        # Add rationale if available
        if strategy_insights['rationale'] != "No rationale available":
            strategy_para += f"The rationale is: {strategy_insights['rationale']} "
        
        # Add entry signals
        if strategy_insights['entry_signals']:
            entry = strategy_insights['entry_signals'][0]
            strategy_para += f"For optimal entry, look for {entry}. "
        
        # Add exit triggers
        if strategy_insights['exit_triggers']:
            exit_trigger = strategy_insights['exit_triggers'][0]
            strategy_para += f"Consider exiting when {exit_trigger}. "
        
        # Add expected reward
        if strategy_insights['expected_reward'] != "Unknown":
            strategy_para += f"This strategy targets {strategy_insights['expected_reward']} "
        
        paragraphs.append(strategy_para)
        
        # CONCLUSION - Summarize the key points
        conclusion = "CONCLUSION: "
        
        # Add an integrative summary that connects macro → micro → price
        conclusion += f"In the current {macro_insights['trend'].lower() if macro_insights['trend'] != 'STABLE' else 'economic'} environment, "
        conclusion += f"{self.ticker}'s {micro_insights.get('recommendation', 'positioning')} and "
        
        # Add technical stance
        if "LONG" in price_insights['risk_reward'] or "BULLISH" in price_insights['macd_analysis']:
            conclusion += "bullish technical indicators "
        elif "SHORT" in price_insights['risk_reward'] or "BEARISH" in price_insights['macd_analysis']:
            conclusion += "bearish technical indicators "
        else:
            conclusion += "mixed technical indicators "
        
        # Final recommendation
        if strategy_insights['recommended_action'] != "No recommendation available":
            conclusion += f"support our {strategy_insights['recommended_action']} recommendation. "
        else:
            conclusion += "suggest cautious positioning. "
        
        # Add key catalyst to watch
        if macro_insights['macro_catalysts']:
            catalyst = macro_insights['macro_catalysts'][0]
            conclusion += f"Key catalyst to monitor: {catalyst}."
        
        paragraphs.append(conclusion)
        
        # Join all paragraphs with line breaks to create a flowing narrative
        investment_mindmap = "\n\n".join(paragraphs)
        
        return investment_mindmap
    
    def update_rating_json(self) -> None:
        """Update the rating JSON with the investment mindmap."""
        if not self.rating_data or not self.rating_json_path:
            print("No rating data or path available.")
            return
        
        # Generate the investment mindmap
        investment_mindmap = self.generate_investment_mindmap()
        
        # Print debug info
        print(f"\nUpdating rating JSON at: {self.rating_json_path}")
        print(f"Current Investment_Mindmap field exists: {'Investment_Mindmap' in self.rating_data}")
        print(f"Current Investment_Mindmap length: {len(str(self.rating_data.get('Investment_Mindmap', '')))}")
        
        # Update the rating data
        self.rating_data["Investment_Mindmap"] = investment_mindmap
        
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
        Run the Investment Integration Agent on a rating JSON file.
        
        Args:
            rating_json_path (str, optional): Path to rating JSON file. If None, uses the path from initialization.
        
        Returns:
            Optional[str]: The generated investment mindmap, or None if an error occurred.
        """
        if rating_json_path:
            self.load_rating_data(rating_json_path)
            self.rating_json_path = rating_json_path  # Ensure path is set
        
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
