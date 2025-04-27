import os
import json
import sys
import pandas as pd
import numpy as np
from io import BytesIO
import base64
import matplotlib.pyplot as plt
from datetime import datetime
import importlib.util
import yfinance as yf

# Import price level tools with the correct path
current_dir = os.path.dirname(os.path.abspath(__file__))
price_tools_path = os.path.join(current_dir, "Tool", "price_level_tools.py")
spec = importlib.util.spec_from_file_location("price_level_tools", price_tools_path)
price_level_tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(price_level_tools)

class PriceAgent:
    def __init__(self, rating_json_path=None, graph_dir=None):
        """Initialize the Price Agent with a rating JSON file path."""
        self.rating_data = None
        self.ticker = None
        self.inference_data = {
            "macro_inference": None,
            "micro_inference": None,
            "price_inference": None
        }
        self.price_analysis = {}
        self.strategy = {}
        self.investment_mindmap = {}
        self.rating_json_path = rating_json_path
        self.graph_dir = graph_dir
        
        if rating_json_path:
            self.load_rating_data(rating_json_path)
    
    def load_rating_data(self, rating_json_path):
        """Load the rating JSON data from the specified file."""
        try:
            with open(rating_json_path, 'r') as f:
                self.rating_data = json.load(f)
                self.ticker = self.rating_data.get("Ticker")
                
                # Extract inference data
                if "Macro" in self.rating_data:
                    self.inference_data["macro_inference"] = self.rating_data["Macro"].get("next_inference_hint")
                
                if "Micro" in self.rating_data:
                    self.inference_data["micro_inference"] = self.rating_data["Micro"].get("micro_to_price_next_inference")
                
                print(f"Loaded rating data for {self.ticker}")
        except Exception as e:
            print(f"Error loading rating data: {str(e)}")
    
    def analyze_price_levels(self):
        """Analyze price levels using various tools based on inferences."""
        if not self.rating_data or not self.ticker:
            print("No rating data or ticker available. Load rating data first.")
            return
        
        # Extract current price from tool results if available
        current_price = None
        if "Micro" in self.rating_data and "tool_results" in self.rating_data["Micro"]:
            if "get_stock_metrics" in self.rating_data["Micro"]["tool_results"]:
                metrics_result = self.rating_data["Micro"]["tool_results"]["get_stock_metrics"]["result"]
                if "Current_Price" in metrics_result:
                    # Extract price from the metrics string
                    for line in metrics_result.split('\n'):
                        if "Current_Price" in line:
                            try:
                                current_price = float(line.split('=')[1].strip().split()[0])
                                break
                            except:
                                pass
        
        if not current_price:
            print("Warning: Could not extract current price from tool results. Fetching current price from Yahoo Finance.")
            try:
                ticker_data = yf.Ticker(self.ticker)
                current_data = ticker_data.history(period="1d")
                if not current_data.empty:
                    current_price = current_data['Close'].iloc[-1]
                    print(f"Current price fetched from Yahoo Finance: {current_price}")
                else:
                    print("Error: Could not fetch current price from Yahoo Finance.")
                    return
            except Exception as e:
                print(f"Error fetching price from Yahoo Finance: {str(e)}")
                return
        
        # Run analysis tools based on inferences
        self.price_analysis = {}
        
        # Determine graph directory - use provided dir or default
        graphs_dir = self.graph_dir if self.graph_dir else "Price_Graphs"
        os.makedirs(graphs_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. Risk/Reward Analysis for both positions
        try:
            print(f"Running risk/reward analysis for {self.ticker}...")
            analysis_string, graph_data = price_level_tools.analyze_both_positions(
                stock_ticker=self.ticker,
                price=current_price,
                share=1,
                N=360, # 1 year lookback
                bayesian_weight=True
            )
            
            # Save graph to file instead of embedding in JSON
            graph_path = os.path.join(graphs_dir, f"{self.ticker}_risk_reward_{timestamp}.png")
            if 'combined_plot' in graph_data:
                with open(graph_path, "wb") as f:
                    f.write(base64.b64decode(graph_data['combined_plot']))
                
            self.price_analysis["risk_reward"] = {
                "summary": analysis_string,
                "graph_path": graph_path
            }
            print("Risk/reward analysis completed.")
        except Exception as e:
            print(f"Error in risk/reward analysis: {str(e)}")
        
        # 2. SMA Crossover Analysis
        try:
            print(f"Running SMA crossover analysis for {self.ticker}...")
            analysis_string, graph_data = price_level_tools.analyze_sma_crossovers(
                ticker=self.ticker,
                period="1y",
                lookforward=30
            )
            
            # Save graph to file
            graph_path = os.path.join(graphs_dir, f"{self.ticker}_sma_crossovers_{timestamp}.png")
            if 'sma_plot' in graph_data:
                with open(graph_path, "wb") as f:
                    f.write(base64.b64decode(graph_data['sma_plot']))
            
            self.price_analysis["sma_crossovers"] = {
                "summary": analysis_string,
                "graph_path": graph_path
            }
            print("SMA crossover analysis completed.")
        except Exception as e:
            print(f"Error in SMA crossover analysis: {str(e)}")
        
        # 3. EMA Crossover Analysis
        try:
            print(f"Running EMA crossover analysis for {self.ticker}...")
            analysis_string, graph_data = price_level_tools.analyze_ema_crossovers(
                ticker=self.ticker,
                period="1y",
                lookforward=30
            )
            
            # Save graph to file
            graph_path = os.path.join(graphs_dir, f"{self.ticker}_ema_crossovers_{timestamp}.png")
            if 'ema_plot' in graph_data:
                with open(graph_path, "wb") as f:
                    f.write(base64.b64decode(graph_data['ema_plot']))
            
            self.price_analysis["ema_crossovers"] = {
                "summary": analysis_string,
                "graph_path": graph_path
            }
            print("EMA crossover analysis completed.")
        except Exception as e:
            print(f"Error in EMA crossover analysis: {str(e)}")
        
        # 4. Volume-Weighted MACD Analysis
        try:
            print(f"Running volume-weighted MACD analysis for {self.ticker}...")
            analysis_string, graph_data = price_level_tools.analyze_vw_macd(
                ticker=self.ticker,
                period="1y"
            )
            
            # Save graph to file
            graph_path = os.path.join(graphs_dir, f"{self.ticker}_vw_macd_{timestamp}.png")
            if 'vw_macd_plot' in graph_data:
                with open(graph_path, "wb") as f:
                    f.write(base64.b64decode(graph_data['vw_macd_plot']))
            
            self.price_analysis["vw_macd"] = {
                "summary": analysis_string,
                "graph_path": graph_path
            }
            print("Volume-weighted MACD analysis completed.")
        except Exception as e:
            print(f"Error in volume-weighted MACD analysis: {str(e)}")
    
    def generate_strategy(self):
        """Generate a trading strategy based on price analysis and inferences."""
        if not self.price_analysis:
            print("No price analysis available. Run analyze_price_levels first.")
            return
        
        # Extract key signals from price analysis
        rr_signal = None
        if "risk_reward" in self.price_analysis:
            if "LONG" in self.price_analysis["risk_reward"]["summary"]:
                rr_signal = "LONG"
            elif "SHORT" in self.price_analysis["risk_reward"]["summary"]:
                rr_signal = "SHORT"
        
        ma_signal = None
        if "sma_crossovers" in self.price_analysis and "ema_crossovers" in self.price_analysis:
            sma_bullish = "BULLISH" in self.price_analysis["sma_crossovers"]["summary"]
            ema_bullish = "BULLISH" in self.price_analysis["ema_crossovers"]["summary"]
            
            if sma_bullish and ema_bullish:
                ma_signal = "STRONG BULLISH"
            elif sma_bullish or ema_bullish:
                ma_signal = "MODERATE BULLISH"
            elif not sma_bullish and not ema_bullish:
                ma_signal = "BEARISH"
        
        macd_signal = None
        macd_momentum = "WEAK"
        if "vw_macd" in self.price_analysis:
            if "BULLISH SIGNAL" in self.price_analysis["vw_macd"]["summary"]:
                macd_signal = "BULLISH"
            elif "BEARISH SIGNAL" in self.price_analysis["vw_macd"]["summary"]:
                macd_signal = "BEARISH"
            
            if "STRONG MOMENTUM" in self.price_analysis["vw_macd"]["summary"]:
                macd_momentum = "STRONG"
            elif "MODERATE MOMENTUM" in self.price_analysis["vw_macd"]["summary"]:
                macd_momentum = "MODERATE"
        
        # Parse the micro inference for price recommendation
        micro_bias = None
        if self.inference_data["micro_inference"]:
            if "SHORT" in self.inference_data["micro_inference"]:
                micro_bias = "SHORT"
            elif "LONG" in self.inference_data["micro_inference"]:
                micro_bias = "LONG"
        
        # Determine if we should catch momentum or wait for reversion
        is_momentum_strategy = False
        if macd_momentum in ["STRONG", "MODERATE"] and macd_signal:
            is_momentum_strategy = True
        
        # Extract upcoming catalysts from macro analysis
        catalysts = []
        if "Macro" in self.rating_data and "macro_catalysts" in self.rating_data["Macro"]:
            catalysts = self.rating_data["Macro"]["macro_catalysts"][:3]  # Get top 3 catalysts
        
        # Generate price-in determination
        price_in = self.determine_price_in()
        
        # Combine signals to determine overall strategy
        strategy_type = "MOMENTUM" if is_momentum_strategy else "REVERSION"
        
        if rr_signal and ma_signal and macd_signal:
            if (rr_signal == "LONG" and ma_signal.endswith("BULLISH") and macd_signal == "BULLISH") or \
               (micro_bias == "LONG" and (ma_signal.endswith("BULLISH") or macd_signal == "BULLISH")):
                action = "BUY"
                rationale = f"Strong bullish signals across risk/reward, moving averages, and MACD, supported by micro analysis. Using {strategy_type} strategy."
                risk_level = "MODERATE"
            elif (rr_signal == "SHORT" and ma_signal == "BEARISH" and macd_signal == "BEARISH") or \
                 (micro_bias == "SHORT" and (ma_signal == "BEARISH" or macd_signal == "BEARISH")):
                action = "SELL"
                rationale = f"Strong bearish signals across risk/reward, moving averages, and MACD, supported by micro analysis. Using {strategy_type} strategy."
                risk_level = "MODERATE"
            elif micro_bias and (
                (micro_bias == "LONG" and (rr_signal == "LONG" or ma_signal.endswith("BULLISH") or macd_signal == "BULLISH")) or
                (micro_bias == "SHORT" and (rr_signal == "SHORT" or ma_signal == "BEARISH" or macd_signal == "BEARISH"))
            ):
                action = "BUY" if micro_bias == "LONG" else "SELL"
                rationale = f"Mixed signals with {micro_bias} bias from micro analysis and partial technical confirmation. Using {strategy_type} strategy."
                risk_level = "HIGH"
            else:
                action = "WAIT"
                rationale = f"Conflicting signals between risk/reward, moving averages, and MACD. Wait for clearer {strategy_type} signals."
                risk_level = "LOW"
        else:
            action = "INSUFFICIENT DATA"
            rationale = "Unable to determine strategy due to missing analysis components."
            risk_level = "UNKNOWN"
            strategy_type = "UNDEFINED"
        
        # Define exit triggers and catalysts for momentum or reversion strategy
        exit_triggers = []
        if strategy_type == "MOMENTUM":
            exit_triggers = [
                "Trend reversal in MACD indicator",
                "Moving average crossover in opposite direction",
                "Price hitting resistance/support levels"
            ]
            if catalysts:
                exit_triggers.append(f"Post-event profit-taking after {catalysts[0]}")
        else:  # REVERSION
            exit_triggers = [
                "Price returning to mean level",
                "Oversold/overbought indicator normalization",
                "New support/resistance levels established"
            ]
            if catalysts:
                exit_triggers.append(f"Market reaction confirmation after {catalysts[0]}")
        
        entry_signals = []
        if strategy_type == "MOMENTUM":
            entry_signals = [
                "Breakout above resistance with increased volume",
                "Continuation of current trend with higher highs/lower lows",
                "Strong MACD momentum confirmation"
            ]
        else:  # REVERSION
            entry_signals = [
                "Price reaching extreme oversold/overbought levels",
                "Divergence between price and momentum indicators",
                "Price testing historical support/resistance levels"
            ]
        
        # Generate the strategy and investment mindmap
        self.strategy = {
            "recommended_action": action,
            "strategy_type": strategy_type,
            "rationale": self.generate_detailed_rationale(rr_signal, ma_signal, macd_signal, micro_bias, price_in, catalysts),
            "risk_level": risk_level,
            "time_horizon": "SHORT-TERM" if strategy_type == "MOMENTUM" else "MEDIUM-TERM",
            "expected_reward": self.estimate_reward_potential(),
            "exit_triggers": exit_triggers,
            "entry_signals": entry_signals
        }
        
        # Generate investment mindmap with comprehensive reasoning
        self.investment_mindmap = self.generate_investment_mindmap(
            rr_signal, ma_signal, macd_signal, micro_bias, 
            strategy_type, catalysts, price_in
        )
    
    def generate_investment_mindmap(self, rr_signal, ma_signal, macd_signal, micro_bias, 
                                   strategy_type, catalysts, price_in):
        """Generate a comprehensive investment mindmap with chain-of-thought reasoning."""
        # Extract deep insights from Macro analysis
        macro_outlook = self.extract_economic_outlook()
        sector_trends = self.extract_sector_trends()
        macro_summary = self.rating_data.get("Macro", {}).get("summary", "No macro data available")
        macro_hint = self.inference_data.get("macro_inference", "No macro inference available")
        
        # Extract deep insights from Micro analysis
        company_fundamentals = self.extract_company_fundamentals()
        news_sentiment = self.extract_news_sentiment()
        micro_news = self.rating_data.get("Micro", {}).get("Three_Key_Takeaway_News", "No micro news available")
        earnings_surprise = self.extract_earnings_surprise()
        
        # Extract key metrics if available
        key_metrics = {}
        if "Micro" in self.rating_data and "tool_results" in self.rating_data["Micro"]:
            if "get_stock_metrics" in self.rating_data["Micro"]["tool_results"]:
                metrics_str = self.rating_data["Micro"]["tool_results"]["get_stock_metrics"]["result"]
                for line in metrics_str.split('\n'):
                    if "=" in line:
                        parts = line.split('=')
                        if len(parts) >= 2:
                            key = parts[0].strip()
                            value = parts[1].strip()
                            key_metrics[key] = value
        
        # Price analysis synthesis
        price_synthesis = self.synthesize_price_analysis(rr_signal, ma_signal, macd_signal)
        
        # Analyze relationship between news and price action
        news_price_relationship = self.analyze_news_price_relationship(price_in, news_sentiment, micro_news)
        
        # Analyze if macro environment is overriding normal valuation metrics
        macro_override = self.analyze_macro_override(macro_outlook, sector_trends, company_fundamentals)
        
        # Determine if there's a disconnect between fundamentals and technicals
        fundamental_technical_disconnect = self.analyze_fundamental_technical_disconnect(
            company_fundamentals, rr_signal, ma_signal, macd_signal
        )
        
        # Analyze current market positioning relative to catalysts
        catalyst_positioning = self.analyze_catalyst_positioning(catalysts, price_in, strategy_type)
        
        # Generate comprehensive chain of thought reasoning
        reasoning_chain = self.generate_reasoning_chain(
            macro_outlook, sector_trends, macro_summary, macro_hint,
            company_fundamentals, news_sentiment, micro_news, earnings_surprise,
            rr_signal, ma_signal, macd_signal, price_synthesis,
            news_price_relationship, macro_override, fundamental_technical_disconnect,
            catalyst_positioning, strategy_type, price_in
        )
        
        # Construct the final mindmap
        mindmap = {
            "macro_considerations": {
                "economic_outlook": macro_outlook,
                "sector_trends": sector_trends,
                "catalysts": catalysts if catalysts else ["No significant catalysts identified"],
                "macro_summary": macro_summary[:200] + "..." if len(macro_summary) > 200 else macro_summary
            },
            "micro_factors": {
                "company_fundamentals": company_fundamentals,
                "news_sentiment": news_sentiment,
                "price_in_status": "PRICED IN" if price_in else "NOT PRICED IN" if price_in is not None else "UNKNOWN",
                "earnings_surprise": earnings_surprise,
                "key_metrics": key_metrics
            },
            "price_technicals": {
                "risk_reward": rr_signal if rr_signal else "NEUTRAL",
                "moving_averages": ma_signal if ma_signal else "NEUTRAL",
                "momentum": macd_signal if macd_signal else "NEUTRAL",
                "price_synthesis": price_synthesis
            },
            "relationship_analysis": {
                "news_price_relationship": news_price_relationship,
                "macro_override": macro_override,
                "fundamental_technical_disconnect": fundamental_technical_disconnect,
                "catalyst_positioning": catalyst_positioning
            },
            "strategy_integration": {
                "primary_approach": strategy_type,
                "dominant_factor": self.determine_dominant_factor(rr_signal, ma_signal, macd_signal, micro_bias),
                "conviction_level": self.calculate_conviction_level(rr_signal, ma_signal, macd_signal, micro_bias)
            },
            "reasoning_chain": reasoning_chain
        }
        
        return mindmap
    
    def extract_economic_outlook(self):
        """Extract economic outlook from macro data."""
        if "Macro" in self.rating_data and "summary" in self.rating_data["Macro"]:
            summary = self.rating_data["Macro"]["summary"]
            if "bullish" in summary.lower() or "positive" in summary.lower() or "growth" in summary.lower():
                return "POSITIVE"
            elif "bearish" in summary.lower() or "negative" in summary.lower() or "contraction" in summary.lower():
                return "NEGATIVE"
            else:
                return "NEUTRAL"
        return "UNKNOWN"
    
    def extract_sector_trends(self):
        """Extract sector trends from macro data."""
        if "Macro" in self.rating_data and "summary" in self.rating_data["Macro"]:
            summary = self.rating_data["Macro"]["summary"]
            if "sector" in summary.lower() and "outperform" in summary.lower():
                return "OUTPERFORMING"
            elif "sector" in summary.lower() and "underperform" in summary.lower():
                return "UNDERPERFORMING"
            else:
                return "AVERAGE"
        return "UNKNOWN"
    
    def extract_company_fundamentals(self):
        """Extract company fundamentals from micro data."""
        if "Micro" in self.rating_data and "tool_results" in self.rating_data["Micro"]:
            if "get_stock_metrics" in self.rating_data["Micro"]["tool_results"]:
                metrics = self.rating_data["Micro"]["tool_results"]["get_stock_metrics"]["result"]
                if "undervalued" in metrics.lower() or "strong buy" in metrics.lower():
                    return "STRONG"
                elif "overvalued" in metrics.lower() or "sell" in metrics.lower():
                    return "WEAK"
                else:
                    return "AVERAGE"
        return "UNKNOWN"
    
    def extract_news_sentiment(self):
        """Extract news sentiment from micro data."""
        if "Micro" in self.rating_data and "Three_Key_Takeaway_News" in self.rating_data["Micro"]:
            news = self.rating_data["Micro"]["Three_Key_Takeaway_News"]
            if "positive" in news.lower() or "beat" in news.lower() or "exceed" in news.lower():
                return "POSITIVE"
            elif "negative" in news.lower() or "miss" in news.lower() or "below" in news.lower():
                return "NEGATIVE"
            else:
                return "NEUTRAL"
        return "UNKNOWN"
    
    def extract_earnings_surprise(self):
        """Extract any earnings surprise information from the micro data."""
        if "Micro" in self.rating_data and "Three_Key_Takeaway_News" in self.rating_data["Micro"]:
            news = self.rating_data["Micro"]["Three_Key_Takeaway_News"].lower()
            
            if "beat" in news and "estimate" in news:
                return "POSITIVE"
            elif "miss" in news and "estimate" in news:
                return "NEGATIVE"
            elif "in-line" in news or "meet" in news:
                return "NEUTRAL"
        
        return "UNKNOWN"
    
    def synthesize_price_analysis(self, rr_signal, ma_signal, macd_signal):
        """Synthesize the various price analysis components into a coherent view."""
        signals = []
        if rr_signal:
            signals.append(f"{rr_signal} risk/reward")
        if ma_signal:
            signals.append(f"{ma_signal} moving averages")
        if macd_signal:
            signals.append(f"{macd_signal} momentum")
        
        if not signals:
            return "INSUFFICIENT TECHNICAL DATA"
        
        # Count bullish vs bearish signals
        bullish_count = sum(1 for s in signals if "LONG" in s or "BULLISH" in s)
        bearish_count = sum(1 for s in signals if "SHORT" in s or "BEARISH" in s)
        
        if bullish_count > bearish_count:
            strength = "STRONG" if bullish_count >= 2 * bearish_count else "MODERATE"
            return f"{strength} BULLISH BIAS"
        elif bearish_count > bullish_count:
            strength = "STRONG" if bearish_count >= 2 * bullish_count else "MODERATE"
            return f"{strength} BEARISH BIAS"
        else:
            return "NEUTRAL/MIXED SIGNALS"
    
    def analyze_news_price_relationship(self, price_in, news_sentiment, micro_news):
        """Analyze the relationship between news and price action."""
        if price_in is None or news_sentiment == "UNKNOWN":
            return "UNCLEAR RELATIONSHIP"
        
        if price_in and news_sentiment == "POSITIVE":
            return "POSITIVE NEWS ALREADY PRICED IN - Limited upside potential"
        elif price_in and news_sentiment == "NEGATIVE":
            return "NEGATIVE NEWS ALREADY PRICED IN - Limited downside risk"
        elif not price_in and news_sentiment == "POSITIVE":
            return "POSITIVE NEWS NOT FULLY PRICED IN - Potential upside opportunity"
        elif not price_in and news_sentiment == "NEGATIVE":
            return "NEGATIVE NEWS NOT FULLY PRICED IN - Potential downside risk"
        else:
            return "NEUTRAL NEWS WITH NO CLEAR PRICE IMPACT"
    
    def analyze_macro_override(self, macro_outlook, sector_trends, company_fundamentals):
        """Analyze if macro factors are overriding normal company valuation."""
        if macro_outlook == "UNKNOWN" or company_fundamentals == "UNKNOWN":
            return "INSUFFICIENT DATA"
        
        # Check for contradictions between macro and fundamentals
        if (macro_outlook == "POSITIVE" and company_fundamentals == "WEAK") or \
           (macro_outlook == "NEGATIVE" and company_fundamentals == "STRONG"):
            return "HIGH MACRO OVERRIDE - Macro factors likely dominating company fundamentals"
        
        # Check for sector-specific effects
        if sector_trends in ["OUTPERFORMING", "UNDERPERFORMING"]:
            return f"MODERATE MACRO OVERRIDE - {sector_trends} sector trends influencing stock beyond fundamentals"
        
        return "LOW MACRO OVERRIDE - Company fundamentals likely driving valuation"
    
    def analyze_fundamental_technical_disconnect(self, company_fundamentals, rr_signal, ma_signal, macd_signal):
        """Analyze any disconnect between fundamentals and technicals."""
        if company_fundamentals == "UNKNOWN" or (not rr_signal and not ma_signal and not macd_signal):
            return "INSUFFICIENT DATA"
        
        # Determine overall technical direction
        technical_bullish = 0
        technical_bearish = 0
        
        if rr_signal == "LONG":
            technical_bullish += 1
        elif rr_signal == "SHORT":
            technical_bearish += 1
        
        if ma_signal and "BULLISH" in ma_signal:
            technical_bullish += 1
        elif ma_signal == "BEARISH":
            technical_bearish += 1
        
        if macd_signal == "BULLISH":
            technical_bullish += 1
        elif macd_signal == "BEARISH":
            technical_bearish += 1
        
        technical_bias = "BULLISH" if technical_bullish > technical_bearish else \
                         "BEARISH" if technical_bearish > technical_bullish else "NEUTRAL"
        
        # Check for disconnect
        if (company_fundamentals == "STRONG" and technical_bias == "BEARISH") or \
           (company_fundamentals == "WEAK" and technical_bias == "BULLISH"):
            return f"HIGH DISCONNECT - {company_fundamentals} fundamentals vs {technical_bias} technicals"
        elif company_fundamentals == "AVERAGE" and technical_bias != "NEUTRAL":
            return f"MODERATE DISCONNECT - Average fundamentals vs {technical_bias} technicals"
        else:
            return "LOW DISCONNECT - Fundamentals and technicals aligned"
    
    def analyze_catalyst_positioning(self, catalysts, price_in, strategy_type):
        """Analyze current market positioning relative to upcoming catalysts."""
        if not catalysts or price_in is None:
            return "INSUFFICIENT DATA"
        
        catalyst_description = catalysts[0][:100] + "..." if len(catalysts[0]) > 100 else catalysts[0]
        
        if not price_in and "earnings" in catalyst_description.lower():
            return f"PRE-EARNINGS POSITIONING - Market anticipating catalyst: {catalyst_description}"
        elif price_in and "earnings" in catalyst_description.lower():
            return f"POST-EARNINGS ADJUSTMENT - Market digesting recent earnings"
        
        # Strategy-specific positioning
        if strategy_type == "MOMENTUM":
            return f"MOMENTUM-DRIVEN POSITIONING - Riding trend ahead of catalyst: {catalyst_description}"
        else:  # REVERSION
            return f"MEAN-REVERSION POSITIONING - Anticipating normalization around catalyst: {catalyst_description}"
    
    def determine_dominant_factor(self, rr_signal, ma_signal, macd_signal, micro_bias):
        """Determine which factor is most influential in the strategy."""
        # Count supporting signals for each direction
        bullish_signals = 0
        bearish_signals = 0
        
        if rr_signal == "LONG":
            bullish_signals += 1
        elif rr_signal == "SHORT":
            bearish_signals += 1
            
        if ma_signal and "BULLISH" in ma_signal:
            bullish_signals += 1
        elif ma_signal == "BEARISH":
            bearish_signals += 1
            
        if macd_signal == "BULLISH":
            bullish_signals += 1
        elif macd_signal == "BEARISH":
            bearish_signals += 1
            
        if isinstance(micro_bias, str):
            if micro_bias == "LONG":
                bullish_signals += 1.5  # Give extra weight to micro_bias
            elif micro_bias == "SHORT":
                bearish_signals += 1.5  # Give extra weight to micro_bias
        
        # Check which type of analysis is most influential
        macro_influence = "HIGH" if "Macro" in self.rating_data and self.rating_data["Macro"].get("next_inference_hint") else "LOW"
        micro_influence = "HIGH" if micro_bias else "LOW"
        price_influence = "HIGH" if (rr_signal and ma_signal and macd_signal) else "LOW"
        
        # Determine dominant factor
        influences = {
            "MACRO": macro_influence,
            "MICRO": micro_influence,
            "PRICE": price_influence
        }
        
        max_influence = max(influences, key=lambda k: "HIGH" if influences[k] == "HIGH" else "LOW")
        return max_influence
    
    def calculate_conviction_level(self, rr_signal, ma_signal, macd_signal, micro_bias):
        """Calculate the conviction level for the strategy."""
        signals = [rr_signal, ma_signal, macd_signal, micro_bias]
        signals = [s for s in signals if s]  # Remove None values
        
        if not signals:
            return "NONE"
        
        # Check for consensus
        long_signals = sum(1 for s in signals if "LONG" in str(s) or "BULLISH" in str(s))
        short_signals = sum(1 for s in signals if "SHORT" in str(s) or "BEARISH" in str(s))
        
        total_signals = len(signals)
        if long_signals == total_signals or short_signals == total_signals:
            return "HIGH"  # All signals agree
        elif long_signals > short_signals * 2 or short_signals > long_signals * 2:
            return "MEDIUM-HIGH"  # Strong majority
        elif long_signals > short_signals or short_signals > long_signals:
            return "MEDIUM"  # Simple majority
        else:
            return "LOW"  # Mixed signals
    
    def generate_reasoning_chain(self, macro_outlook, sector_trends, macro_summary, macro_hint,
                               company_fundamentals, news_sentiment, micro_news, earnings_surprise,
                               rr_signal, ma_signal, macd_signal, price_synthesis,
                               news_price_relationship, macro_override, fundamental_technical_disconnect,
                               catalyst_positioning, strategy_type, price_in):
        """Generate a comprehensive chain-of-thought investment reasoning with concrete evidence."""
        # Start with macro analysis
        reasoning = []
        
        # Extract concrete macro evidence
        macro_evidence = self.extract_concrete_macro_evidence()
        
        # Extract concrete micro evidence
        micro_evidence = self.extract_concrete_micro_evidence()
        
        # Extract concrete price evidence
        price_evidence = self.extract_concrete_price_evidence()
        
        # Macro reasoning with specific evidence
        reasoning.append(f"MACRO EVIDENCE AND ANALYSIS:")
        reasoning.append(f"Economic outlook is {macro_outlook.lower()} based on:")
        for evidence in macro_evidence[:3]:  # Top 3 pieces of evidence
            reasoning.append(f"- {evidence}")
        
        if macro_summary and len(macro_summary) > 10:
            reasoning.append(f"Specifically, the macro analysis indicates: \"{macro_summary[:200]}...\"")
        if macro_hint and len(macro_hint) > 5:
            reasoning.append(f"The forward-looking macro inference suggests: \"{macro_hint[:200]}...\"")
        
        # Micro reasoning with specific evidence
        reasoning.append(f"\nMICRO (COMPANY-SPECIFIC) EVIDENCE AND ANALYSIS:")
        reasoning.append(f"The company shows {company_fundamentals.lower()} fundamentals based on:")
        for evidence in micro_evidence[:3]:  # Top 3 pieces of evidence
            reasoning.append(f"- {evidence}")
        
        if micro_news and len(micro_news) > 10:
            reasoning.append(f"Key company news: \"{micro_news[:200]}...\"")
        if earnings_surprise != "UNKNOWN":
            reasoning.append(f"Recent earnings were a {earnings_surprise.lower()} surprise relative to market expectations.")
        
        # Price analysis with specific evidence
        reasoning.append(f"\nPRICE ANALYSIS AND TECHNICAL EVIDENCE:")
        reasoning.append(f"Technical price analysis reveals {price_synthesis} based on:")
        for evidence in price_evidence[:3]:  # Top 3 pieces of evidence
            reasoning.append(f"- {evidence}")
        
        if rr_signal:
            reasoning.append(f"Risk/reward analysis favors a {rr_signal} position.")
        if ma_signal:
            reasoning.append(f"Moving averages signal {ma_signal} trends.")
        if macd_signal:
            reasoning.append(f"MACD indicates {macd_signal} momentum.")
        
        # Relationship analysis
        reasoning.append(f"\nINTEGRATED RELATIONSHIP ANALYSIS:")
        reasoning.append(f"1. News vs. Price: {news_price_relationship}")
        reasoning.append(f"2. Macro Impact: {macro_override}")
        reasoning.append(f"3. Fundamental vs. Technical: {fundamental_technical_disconnect}")
        reasoning.append(f"4. Catalyst Positioning: {catalyst_positioning}")
        
        # Integration and strategy with evidence-based reasoning
        reasoning.append(f"\nINTEGRATED STRATEGY REASONING:")
        reasoning.append(f"Based on the above evidence, a {strategy_type} strategy is most appropriate because:")
        
        # Strategy-specific reasoning
        if strategy_type == "MOMENTUM":
            if price_in == False:
                reasoning.append("- Recent news is NOT fully priced in (evident from continued price movement post-news), suggesting momentum continuation")
            if macd_signal == "BULLISH":
                reasoning.append("- Strong momentum indicators (increasing MACD histogram) suggest trend continuation")
            if ma_signal and "BULLISH" in ma_signal:
                reasoning.append("- Moving averages show bullish alignment (faster MAs above slower MAs), confirming ongoing trend strength")
            
            # Add macro/micro catalyst support for momentum
            macro_catalysts = self.extract_momentum_catalysts_from_macro()
            if macro_catalysts:
                reasoning.append(f"- Macro catalyst supporting momentum: {macro_catalysts[0]}")
            
            micro_catalysts = self.extract_momentum_catalysts_from_micro()
            if micro_catalysts:
                reasoning.append(f"- Company-specific catalyst supporting momentum: {micro_catalysts[0]}")
        else:  # REVERSION
            if price_in == True:
                reasoning.append("- Recent news appears fully priced in (minimal price movement post-news), suggesting potential overreaction and reversion")
            if fundamental_technical_disconnect.startswith("HIGH"):
                reasoning.append("- Significant disconnect between fundamentals and technicals (price diverging from fundamental value) indicates reversion potential")
            if macro_override.startswith("HIGH"):
                reasoning.append("- Macro factors temporarily overriding fundamentals, creating mean-reversion opportunity when macro concerns subside")
            
            # Add macro/micro catalyst support for reversion
            reversion_catalysts = self.extract_reversion_catalysts()
            if reversion_catalysts:
                reasoning.append(f"- Potential catalyst for reversion: {reversion_catalysts[0]}")
        
        # Final conclusion
        dominant_factor = self.determine_dominant_factor(rr_signal, ma_signal, macd_signal, micro_news)
        conviction = self.calculate_conviction_level(rr_signal, ma_signal, macd_signal, micro_news)
        
        reasoning.append(f"\nCONCLUSION:")
        reasoning.append(f"The {dominant_factor} factors are currently most influential with {conviction} conviction level.")
        
        if "BUY" in self.strategy.get("recommended_action", ""):
            reasoning.append(f"Therefore, the recommended strategy is to BUY with {self.strategy.get('risk_level', 'MODERATE')} risk and {self.strategy.get('expected_reward', 'UNKNOWN')} potential reward.")
            
            # Add timing consideration
            if strategy_type == "MOMENTUM":
                reasoning.append(f"Timing: Enter position now to capture ongoing momentum, with the understanding that position should be exited if any of the following exit triggers are met:")
            else:
                reasoning.append(f"Timing: Enter position as the stock reaches reversion point, with the understanding that position should be exited if any of the following exit triggers are met:")
            
            # Add exit triggers
            for trigger in self.strategy.get("exit_triggers", [])[:2]:
                reasoning.append(f"- {trigger}")
            
        elif "SELL" in self.strategy.get("recommended_action", ""):
            reasoning.append(f"Therefore, the recommended strategy is to SELL with {self.strategy.get('risk_level', 'MODERATE')} risk and {self.strategy.get('expected_reward', 'UNKNOWN')} potential reward.")
            
            # Add timing consideration
            if strategy_type == "MOMENTUM":
                reasoning.append(f"Timing: Enter short position now to capture ongoing negative momentum, with the understanding that position should be closed if any of the following exit triggers are met:")
            else:
                reasoning.append(f"Timing: Enter short position as the stock reaches upper reversion point, with the understanding that position should be closed if any of the following exit triggers are met:")
            
            # Add exit triggers
            for trigger in self.strategy.get("exit_triggers", [])[:2]:
                reasoning.append(f"- {trigger}")
            
        else:
            reasoning.append(f"Therefore, the recommended action is to {self.strategy.get('recommended_action', 'WAIT')} until clearer signals emerge.")
            reasoning.append(f"Specifically, wait for the following entry signals before taking action:")
            
            # Add entry signals
            for signal in self.strategy.get("entry_signals", [])[:2]:
                reasoning.append(f"- {signal}")
        
        return reasoning
    
    def extract_concrete_macro_evidence(self):
        """Extract concrete evidence from macro data such as economic events, policy changes, etc."""
        evidence = []
        
        # Extract from macro summary
        if "Macro" in self.rating_data and "summary" in self.rating_data["Macro"]:
            macro_summary = self.rating_data["Macro"]["summary"]
            
            # Look for Fed/interest rate mentions
            if "fed" in macro_summary.lower() or "interest rate" in macro_summary.lower():
                for sentence in macro_summary.split('. '):
                    if "fed" in sentence.lower() or "interest rate" in sentence.lower() or "rates" in sentence.lower():
                        evidence.append(f"Monetary policy factor: {sentence.strip()}")
                        break
            
            # Look for inflation mentions
            if "inflation" in macro_summary.lower():
                for sentence in macro_summary.split('. '):
                    if "inflation" in sentence.lower():
                        evidence.append(f"Inflation factor: {sentence.strip()}")
                        break
            
            # Look for GDP/growth mentions
            if "gdp" in macro_summary.lower() or "growth" in macro_summary.lower() or "economy" in macro_summary.lower():
                for sentence in macro_summary.split('. '):
                    if "gdp" in sentence.lower() or "growth" in sentence.lower() or "economy" in sentence.lower():
                        evidence.append(f"Economic growth factor: {sentence.strip()}")
                        break
            
            # Look for market sentiment
            if "bull" in macro_summary.lower() or "bear" in macro_summary.lower() or "sentiment" in macro_summary.lower():
                for sentence in macro_summary.split('. '):
                    if "bull" in sentence.lower() or "bear" in sentence.lower() or "sentiment" in sentence.lower():
                        evidence.append(f"Market sentiment factor: {sentence.strip()}")
                        break
        
        # Extract from catalysts
        if "Macro" in self.rating_data and "macro_catalysts" in self.rating_data["Macro"]:
            catalysts = self.rating_data["Macro"]["macro_catalysts"]
            if catalysts and len(catalysts) > 0:
                evidence.append(f"Upcoming macro catalyst: {catalysts[0][:150]}..." if len(catalysts[0]) > 150 else catalysts[0])
        
        # If we don't have enough evidence, add some generic placeholders
        if len(evidence) < 2:
            if "Macro" in self.rating_data and "next_inference_hint" in self.rating_data["Macro"]:
                hint = self.rating_data["Macro"]["next_inference_hint"]
                evidence.append(f"Forward-looking inference: {hint[:150]}..." if len(hint) > 150 else hint)
        
        return evidence
    
    def extract_concrete_micro_evidence(self):
        """Extract concrete evidence from micro data such as earnings, company events, news, etc."""
        evidence = []
        
        # Extract from company news
        if "Micro" in self.rating_data and "Three_Key_Takeaway_News" in self.rating_data["Micro"]:
            news = self.rating_data["Micro"]["Three_Key_Takeaway_News"]
            
            # Break down news by sentences and find the most relevant ones
            sentences = news.split('. ')
            
            # Look for earnings-related news
            earnings_sentence = next((s for s in sentences if "earnings" in s.lower() or "revenue" in s.lower() or "profit" in s.lower()), None)
            if earnings_sentence:
                evidence.append(f"Earnings data: {earnings_sentence.strip()}")
            
            # Look for guidance/outlook
            guidance_sentence = next((s for s in sentences if "guidance" in s.lower() or "outlook" in s.lower() or "forecast" in s.lower()), None)
            if guidance_sentence:
                evidence.append(f"Forward guidance: {guidance_sentence.strip()}")
            
            # Look for product/service news
            product_sentence = next((s for s in sentences if "product" in s.lower() or "launch" in s.lower() or "service" in s.lower()), None)
            if product_sentence:
                evidence.append(f"Product/service news: {product_sentence.strip()}")
        
        # Extract from analyst ratings
        if "Micro" in self.rating_data and "tool_results" in self.rating_data["Micro"]:
            if "get_stock_metrics" in self.rating_data["Micro"]["tool_results"]:
                metrics_str = self.rating_data["Micro"]["tool_results"]["get_stock_metrics"]["result"]
                
                # Look for analyst ratings
                for line in metrics_str.split('\n'):
                    if "rating" in line.lower() or "recommendation" in line.lower():
                        evidence.append(f"Analyst view: {line.strip()}")
                        break
                
                # Look for valuation metrics
                for line in metrics_str.split('\n'):
                    if "p/e" in line.lower() or "price/earning" in line.lower() or "pe ratio" in line.lower():
                        evidence.append(f"Valuation metric: {line.strip()}")
                        break
        
        # Extract from micro inferences
        if "micro_to_price_next_inference" in self.rating_data.get("Micro", {}):
            inference = self.rating_data["Micro"]["micro_to_price_next_inference"]
            evidence.append(f"Company-specific inference: {inference[:150]}..." if len(inference) > 150 else inference)
        
        return evidence
    
    def extract_concrete_price_evidence(self):
        """Extract concrete evidence from price analysis such as specific levels, patterns, etc."""
        evidence = []
        
        # Extract from risk/reward analysis
        if "risk_reward" in self.price_analysis:
            rr_summary = self.price_analysis["risk_reward"]["summary"]
            lines = rr_summary.split('\n')
            
            # Extract risk/reward ratio
            rr_line = next((line for line in lines if "Risk/Reward Ratio" in line or "Reward per Unit Risk" in line), None)
            if rr_line:
                evidence.append(f"Risk/reward profile: {rr_line.strip()}")
            
            # Extract expected profit/loss
            profit_line = next((line for line in lines if "Expected Profit" in line), None)
            loss_line = next((line for line in lines if "Expected Loss" in line), None)
            if profit_line and loss_line:
                evidence.append(f"Profit/loss expectations: {profit_line.strip()} | {loss_line.strip()}")
        
        # Extract from moving average analysis
        if "sma_crossovers" in self.price_analysis:
            sma_summary = self.price_analysis["sma_crossovers"]["summary"]
            lines = sma_summary.split('\n')
            
            # Extract SMA crossover data
            crossover_line = next((line for line in lines if "Bullish Crosses" in line or "Bearish Crosses" in line), None)
            if crossover_line:
                evidence.append(f"Moving average trend: {crossover_line.strip()}")
            
            # Extract return data
            return_line = next((line for line in lines if "Return" in line), None)
            if return_line:
                evidence.append(f"Historical MA performance: {return_line.strip()}")
        
        # Extract from MACD analysis
        if "vw_macd" in self.price_analysis:
            macd_summary = self.price_analysis["vw_macd"]["summary"]
            lines = macd_summary.split('\n')
            
            # Extract MACD signal
            signal_line = next((line for line in lines if "BULLISH SIGNAL" in line or "BEARISH SIGNAL" in line), None)
            if signal_line:
                evidence.append(f"MACD signal: {signal_line.strip()}")
            
            # Extract momentum strength
            momentum_line = next((line for line in lines if "MOMENTUM" in line), None)
            if momentum_line:
                evidence.append(f"Momentum strength: {momentum_line.strip()}")
        
        return evidence
    
    def extract_momentum_catalysts_from_macro(self):
        """Extract catalysts from macro data that could support a momentum strategy."""
        catalysts = []
        
        if "Macro" in self.rating_data and "macro_catalysts" in self.rating_data["Macro"]:
            all_catalysts = self.rating_data["Macro"]["macro_catalysts"]
            
            for catalyst in all_catalysts:
                lower_catalyst = catalyst.lower()
                # Look for catalysts that typically support momentum
                if any(term in lower_catalyst for term in ["stimulus", "expansion", "recovery", "growth", "policy", "fed", "announcement"]):
                    catalysts.append(catalyst[:150] + "..." if len(catalyst) > 150 else catalyst)
        
        return catalysts
    
    def extract_momentum_catalysts_from_micro(self):
        """Extract catalysts from micro data that could support a momentum strategy."""
        catalysts = []
        
        # Check news for momentum-supporting events
        if "Micro" in self.rating_data and "Three_Key_Takeaway_News" in self.rating_data["Micro"]:
            news = self.rating_data["Micro"]["Three_Key_Takeaway_News"]
            
            # Break down by sentences
            sentences = news.split('. ')
            
            for sentence in sentences:
                lower_sentence = sentence.lower()
                # Look for momentum-supporting news
                if any(term in lower_sentence for term in ["beat", "exceed", "growth", "launch", "increase", "higher", "positive", "expansion"]):
                    catalysts.append(sentence.strip())
                    break
        
        return catalysts
    
    def extract_reversion_catalysts(self):
        """Extract catalysts that could support a mean reversion strategy."""
        catalysts = []
        
        # Check macro catalysts
        if "Macro" in self.rating_data and "macro_catalysts" in self.rating_data["Macro"]:
            all_catalysts = self.rating_data["Macro"]["macro_catalysts"]
            
            for catalyst in all_catalysts:
                lower_catalyst = catalyst.lower()
                # Look for catalysts that typically support reversion
                if any(term in lower_catalyst for term in ["correction", "overvalued", "overbought", "pullback", "recession", "contraction"]):
                    catalysts.append(catalyst[:150] + "..." if len(catalyst) > 150 else catalyst)
        
        # Check micro news
        if "Micro" in self.rating_data and "Three_Key_Takeaway_News" in self.rating_data["Micro"]:
            news = self.rating_data["Micro"]["Three_Key_Takeaway_News"]
            
            # Break down by sentences
            sentences = news.split('. ')
            
            for sentence in sentences:
                lower_sentence = sentence.lower()
                # Look for reversion-supporting news
                if any(term in lower_sentence for term in ["miss", "below", "decline", "lower", "negative", "overreaction", "temporary"]):
                    catalysts.append(sentence.strip())
                    break
        
        return catalysts
    
    def determine_price_in(self):
        """Determine if news is priced in based on recent price action and volume."""
        # This is a simplified determination
        if "Micro" in self.rating_data and "Three_Key_Takeaway_News" in self.rating_data["Micro"]:
            news = self.rating_data["Micro"]["Three_Key_Takeaway_News"]
            
            # Check if earnings news is followed by significant price reaction
            is_earnings_news = "earnings" in news.lower() or "revenue" in news.lower()
            
            if is_earnings_news and "vw_macd" in self.price_analysis:
                strong_momentum = "STRONG MOMENTUM" in self.price_analysis["vw_macd"]["summary"]
                
                if strong_momentum:
                    return False  # News not fully priced in if strong momentum exists
                else:
                    return True  # News likely priced in if no strong momentum after earnings
            
        return None  # Cannot determine
    
    def estimate_reward_potential(self):
        """Estimate the potential reward based on risk/reward analysis."""
        if "risk_reward" in self.price_analysis:
            summary = self.price_analysis["risk_reward"]["summary"]
            lines = summary.split('\n')
            
            for line in lines:
                if "Expected Profit" in line:
                    try:
                        profit = float(line.split("Expected Profit =")[1].split(',')[0].strip())
                        if profit > 0:
                            return f"{profit:.2f}% POTENTIAL UPSIDE"
                        else:
                            return "MINIMAL UPSIDE"
                    except:
                        pass
        
        return "UNKNOWN"
    
    def generate_detailed_rationale(self, rr_signal, ma_signal, macd_signal, micro_bias, price_in, catalysts):
        """Generate a detailed rationale for the strategy based on all analyses."""
        rationale = []
        
        # Macro perspective
        if "Macro" in self.rating_data and "summary" in self.rating_data["Macro"]:
            macro_summary = self.rating_data["Macro"]["summary"]
            rationale.append(f"From a macro perspective: {macro_summary[:100]}...")
        
        # Micro perspective
        if "Micro" in self.rating_data and "Three_Key_Takeaway_News" in self.rating_data["Micro"]:
            micro_news = self.rating_data["Micro"]["Three_Key_Takeaway_News"]
            rationale.append(f"Micro analysis shows: {micro_news[:100]}...")
        
        # Price analysis
        rationale.append(f"Price analysis indicates:")
        if rr_signal:
            rationale.append(f"- Risk/Reward favors {rr_signal} position")
        if ma_signal:
            rationale.append(f"- Moving Averages signal {ma_signal}")
        if macd_signal:
            rationale.append(f"- MACD shows {macd_signal} momentum")
        
        # Price-in determination
        if price_in is not None:
            rationale.append(f"Recent news appears to be {'priced in' if price_in else 'NOT fully priced in'}")
        
        # Catalysts
        if catalysts:
            rationale.append("Upcoming catalysts to watch:")
            for i, catalyst in enumerate(catalysts, 1):
                rationale.append(f"  {i}. {catalyst[:100]}...")
        
        # Recommendation basis
        if micro_bias:
            rationale.append(f"Micro analysis suggests a {micro_bias} bias for this stock")
        
        return "\n".join(rationale)
    
    def update_rating_json(self):
        """Update the original rating JSON with price analysis and strategy."""
        if not self.rating_data or not self.price_analysis:
            print("No rating data or price analysis available.")
            return
        
        # Update the Price section
        self.rating_data["Price"] = {
            "risk_reward_summary": self.price_analysis.get("risk_reward", {}).get("summary", ""),
            "sma_crossovers_summary": self.price_analysis.get("sma_crossovers", {}).get("summary", ""),
            "ema_crossovers_summary": self.price_analysis.get("ema_crossovers", {}).get("summary", ""),
            "vw_macd_summary": self.price_analysis.get("vw_macd", {}).get("summary", ""),
            "graph_paths": {
                "risk_reward": self.price_analysis.get("risk_reward", {}).get("graph_path", ""),
                "sma_crossovers": self.price_analysis.get("sma_crossovers", {}).get("graph_path", ""),
                "ema_crossovers": self.price_analysis.get("ema_crossovers", {}).get("graph_path", ""),
                "vw_macd": self.price_analysis.get("vw_macd", {}).get("graph_path", "")
            }
        }
        
        # Update the Strategy section
        self.rating_data["Strategy"] = self.strategy
        
        # Add Investment Mindmap section
        self.rating_data["Investment_Mindmap"] = self.investment_mindmap
        
        # Save the updated rating JSON to the original file
        with open(self.rating_json_path, 'w') as f:
            json.dump(self.rating_data, f, indent=2)
        print(f"Updated original rating JSON at {self.rating_json_path}")
        
        return self.rating_data

def find_latest_rating_json():
    """Find the latest rating JSON file in the Rating_Json directory."""
    json_dir = "Rating_Json"
    if not os.path.isdir(json_dir):
        print(f"Directory {json_dir} not found.")
        return None
    
    # Consider any JSON file in the directory
    json_files = [f for f in os.listdir(json_dir) 
                 if f.endswith('.json') and not f.startswith('.')]
    
    if not json_files:
        print(f"No rating JSON files found in {json_dir}.")
        return None
    
    latest_file = max(json_files, key=lambda x: os.path.getmtime(os.path.join(json_dir, x)))
    print(f"Found JSON file: {latest_file}")
    return os.path.join(json_dir, latest_file)

def main():
    # Find the latest rating JSON file
    latest_rating_json = find_latest_rating_json()
    if not latest_rating_json:
        print("No rating JSON file found. Exiting.")
        return
    
    print(f"Using rating JSON file: {latest_rating_json}")
    
    # Initialize the Price Agent
    agent = PriceAgent(latest_rating_json)
    
    # Analyze price levels
    agent.analyze_price_levels()
    
    # Generate strategy
    agent.generate_strategy()
    
    # Update the original rating JSON
    agent.update_rating_json()
    
    print(f"Price analysis complete. Results saved to the original file: {latest_rating_json}")

if __name__ == "__main__":
    main()
