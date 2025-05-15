#!/usr/bin/env python
# coding: utf-8

import yfinance as yf
import pandas as pd
import requests
import os
import sys
import numpy as np
import importlib.util
import subprocess
from datetime import datetime, timedelta
import json
import inspect
from typing import List, Dict, Any, Optional
from tqdm import tqdm
import time
from functools import wraps
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import euclidean_distances


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
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

# Function to check and install required packages
@tqdm_timer
def check_and_install_packages():
    """Check if required packages are installed and install them if necessary"""
    required_packages = {
        "langchain_community": "langchain-community>=0.0.1",
        "langchain_core": "langchain-core>=0.1.0",
        "pydantic": "pydantic>=2.0.0"
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
    
    return len(missing_packages) == 0

# Check and install required packages
LANGCHAIN_AVAILABLE = check_and_install_packages()

# Global variables for API configuration
API_KEY = "9dfbbfa29d93f4793f246e8fb5ca5e74"  # Financial Modeling Prep API key
BASE_URL = "https://financialmodelingprep.com/api/v3"  # Financial Modeling Prep API base URL

# Try to import LLM API function
try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    sys.path.append(parent_dir)
    from LLM_API_CALL import deepseek_api_call
except ImportError:
    def deepseek_api_call(prompt):
        print("Warning: LLM API function not available")
        return ""

# Try to import LangChain components
if LANGCHAIN_AVAILABLE:
    try:
        # Core components
        from langchain_core.tools import BaseTool, Tool
        from pydantic import BaseModel, Field
    except ImportError as e:
        print(f"Error importing LangChain components: {e}")
        print("LangChain tools won't be available.")
        LANGCHAIN_AVAILABLE = False
else:
    print("Warning: LangChain is not installed. LangChain tools won't be available.")
    # Define placeholder classes for type hints
    class BaseTool:
        pass
    
    class BaseModel:
        pass
    
    class Field:
        pass
        
    class Tool:
        pass

class MicroTools:
    """Collection of micro financial analysis tools for stock analysis"""
    
    @staticmethod
    @tqdm_timer
    def get_key_metrics(ticker):
        """
        Calculate key financial metrics for a given stock ticker.
        
        Parameters:
            ticker (str): Stock ticker symbol
            
        Returns:
            dict: Dictionary containing the calculated metrics
        """
        print(f"Fetching key metrics for {ticker}...")
        
        try:
            # Get stock data
            stock = yf.Ticker(ticker)
            
            # Get financial statements
            income_stmt = stock.income_stmt
            balance_sheet = stock.balance_sheet
            cash_flow = stock.cashflow
            financials = stock.financials
            
            # Initialize result dictionary
            metrics = {
                "EPS": "Data unavailable",
                "ROIC": "Data unavailable",
                "Debt_to_Equity": "Data unavailable",
                "Revenue_Growth": "Data unavailable",
                "Free_Cash_Flow": "Data unavailable",
                "Beta": "Data unavailable",
                "Current_Price": "Data unavailable",
                "Market_Cap": "Data unavailable",
                "PE_Ratio": "Data unavailable",
                "PB_Ratio": "Data unavailable"
            }
            
            # Debug info
            print(f"Got data for {ticker}")
            print(f"Balance sheet rows: {len(balance_sheet.index) if isinstance(balance_sheet, pd.DataFrame) else 'Not a DataFrame'}")
            print(f"Income statement rows: {len(income_stmt.index) if isinstance(income_stmt, pd.DataFrame) else 'Not a DataFrame'}")
            
            # Current Price
            try:
                current_price = stock.info.get("currentPrice")
                if current_price is not None:
                    metrics["Current_Price"] = f"${current_price:.2f}"
            except Exception as e:
                print(f"Error getting current price: {e}")
            
            # Market Cap
            try:
                market_cap = stock.info.get("marketCap")
                if market_cap is not None:
                    metrics["Market_Cap"] = f"${market_cap / 1e9:.2f}B"
            except Exception as e:
                print(f"Error getting market cap: {e}")
            
            # P/E Ratio
            try:
                pe_ratio = stock.info.get("trailingPE")
                if pe_ratio is not None:
                    metrics["PE_Ratio"] = f"{pe_ratio:.2f}"
            except Exception as e:
                print(f"Error getting P/E ratio: {e}")
                
            # P/B Ratio
            try:
                pb_ratio = stock.info.get("priceToBook")
                if pb_ratio is not None:
                    metrics["PB_Ratio"] = f"{pb_ratio:.2f}"
            except Exception as e:
                print(f"Error getting P/B ratio: {e}")
                
            # EPS (Earnings Per Share)
            try:
                eps = stock.info.get("trailingEps")
                if eps is not None:
                    metrics["EPS"] = f"${eps:.2f}"
            except Exception as e:
                print(f"Error calculating EPS: {e}")
            
            # ROIC (Return on Invested Capital)
            try:
                # Try with financials first
                if isinstance(financials, pd.DataFrame) and "Net Income" in financials.index:
                    net_income = financials.loc["Net Income"].iloc[0]
                # Fallback to income_stmt
                elif isinstance(income_stmt, pd.DataFrame) and "Net Income" in income_stmt.index:
                    net_income = income_stmt.loc["Net Income"].iloc[0]
                else:
                    # Try alternative labels
                    possible_income_labels = [
                        "Net Income Common Stockholders",
                        "Net Income Including Noncontrolling Interests"
                    ]
                    found = False
                    for label in possible_income_labels:
                        if isinstance(income_stmt, pd.DataFrame) and label in income_stmt.index:
                            net_income = income_stmt.loc[label].iloc[0]
                            found = True
                            break
                    if not found:
                        raise ValueError("Net Income not found in income statement")
                        
                if isinstance(balance_sheet, pd.DataFrame) and "Total Assets" in balance_sheet.index:
                    total_assets = balance_sheet.loc["Total Assets"].iloc[0]
                else:
                    raise ValueError("Total Assets not found in balance sheet")
                    
                if isinstance(balance_sheet, pd.DataFrame) and "Total Current Liabilities" in balance_sheet.index:
                    current_liabilities = balance_sheet.loc["Total Current Liabilities"].iloc[0]
                else:
                    raise ValueError("Total Current Liabilities not found in balance sheet")

                # Invested Capital = Total Assets - Current Liabilities
                invested_capital = total_assets - current_liabilities

                # ROIC Calculation
                roic_value = (net_income / invested_capital) * 100
                metrics["ROIC"] = f"{roic_value:.2f}%"
            except Exception as e:
                print(f"Error calculating ROIC: {e}")
            
            # Debt to Equity Ratio
            try:
                if isinstance(balance_sheet, pd.DataFrame):
                    if "Total Debt" in balance_sheet.index:
                        total_debt = balance_sheet.loc["Total Debt"].iloc[0]
                    elif "Long Term Debt" in balance_sheet.index:
                        total_debt = balance_sheet.loc["Long Term Debt"].iloc[0]
                    else:
                        raise ValueError("Debt information not found in balance sheet")
                        
                    if "Total Stockholder Equity" in balance_sheet.index:
                        total_equity = balance_sheet.loc["Total Stockholder Equity"].iloc[0]
                    elif "Tangible Book Value" in balance_sheet.index:
                        total_equity = balance_sheet.loc["Tangible Book Value"].iloc[0]
                    else:
                        raise ValueError("Equity information not found in balance sheet")
                        
                    debt_to_equity = total_debt / total_equity
                    metrics["Debt_to_Equity"] = f"{debt_to_equity:.2f}"
                else:
                    print("Balance sheet is not a DataFrame")
            except Exception as e:
                print(f"Error calculating Debt to Equity: {e}")
            
            # Revenue Growth
            try:
                if isinstance(income_stmt, pd.DataFrame) and "Total Revenue" in income_stmt.index:
                    recent_revenue = income_stmt.loc["Total Revenue"].iloc[0]
                    previous_revenue = income_stmt.loc["Total Revenue"].iloc[1]
                    growth = ((recent_revenue - previous_revenue) / previous_revenue) * 100
                    metrics["Revenue_Growth"] = f"{growth:.2f}% YoY"
                else:
                    raise ValueError("Revenue information not found in income statement")
            except Exception as e:
                print(f"Error calculating Revenue Growth: {e}")
            
            # Free Cash Flow
            try:
                if isinstance(cash_flow, pd.DataFrame) and "Operating Cash Flow" in cash_flow.index and "Capital Expenditures" in cash_flow.index:
                    operating_cash = cash_flow.loc["Operating Cash Flow"].iloc[0]
                    capital_expenditures = abs(cash_flow.loc["Capital Expenditures"].iloc[0])
                    fcf = operating_cash - capital_expenditures
                    fcf_billions = fcf / 1e9
                    metrics["Free_Cash_Flow"] = f"${fcf_billions:.2f}B"
                else:
                    raise ValueError("Cash flow information not found")
            except Exception as e:
                print(f"Error calculating Free Cash Flow: {e}")
            
            # Beta
            try:
                beta = stock.info.get("beta")
                if beta is not None:
                    metrics["Beta"] = f"{beta:.2f}"
            except Exception as e:
                print(f"Error calculating Beta: {e}")
            
            # Check if we have any valid metrics
            valid_metrics = {k: v for k, v in metrics.items() if v != "Data unavailable"}
            if not valid_metrics:
                print(f"Warning: No valid metrics found for {ticker}")
                metrics = {
                    "error": f"No valid metrics could be retrieved for {ticker}. The data sources may be unavailable."
                }
            
            # Return the metrics in the required format
            result = {
                "key_metrics": metrics,
                "ticker": ticker,
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            print(f"Successfully fetched metrics for {ticker}")
            return result
            
        except Exception as e:
            print(f"Error in get_key_metrics for {ticker}: {e}")
            return {
                "error": f"Failed to retrieve metrics for {ticker}: {str(e)}",
                "ticker": ticker
            }
    
    @staticmethod
    @tqdm_timer
    def get_beta(ticker):
        """
        Get the beta value for a stock ticker.
        
        Parameters:
            ticker (str): Stock ticker symbol
            
        Returns:
            float: Beta value or None if not available
        """
        try:
            stock = yf.Ticker(ticker)
            beta = stock.info.get("beta")
            return beta
        except Exception as e:
            print(f"Error getting beta for {ticker}: {e}")
            return None
    
    @staticmethod
    @tqdm_timer
    def get_dcf_valuation(ticker):
        """
        Fetch the Discounted Cash Flow (DCF) valuation for a company.
        
        Parameters:
            ticker (str): Stock ticker symbol
            
        Returns:
            dict: DCF valuation data including stock price, DCF value, and price difference
        """
        url = f"{BASE_URL}/discounted-cash-flow/{ticker}?apikey={API_KEY}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            if data and len(data) > 0:
                return data[0]
            return {}
        except Exception as e:
            print(f"Error fetching DCF for {ticker}: {e}")
            return {}
    
    @staticmethod
    @tqdm_timer
    def get_detailed_dcf(ticker):
        """
        Calculate a detailed Discounted Cash Flow (DCF) valuation for a company.
        
        Parameters:
            ticker (str): Stock ticker symbol
            
        Returns:
            dict: Detailed DCF valuation results
        """
        try:
            # Get profile for current price and market cap
            profile = MicroTools.get_company_profile(ticker)
            if not profile or 'price' not in profile:
                return {'status': 'error', 'message': 'Could not retrieve company profile'}
            
            current_price = profile.get('price', 0)
            
            # Get stock data
            stock = yf.Ticker(ticker)
            
            # Get income statements and cash flow
            income_stmt = stock.income_stmt
            balance_sheet = stock.balance_sheet
            cash_flow = stock.cashflow
            
            if income_stmt.empty or cash_flow.empty:
                return {'status': 'error', 'message': 'Could not retrieve sufficient financial data'}
            
            # Get Free Cash Flow
            if "Free Cash Flow" in cash_flow.index:
                fcf_data = cash_flow.loc["Free Cash Flow"]
            elif "Operating Cash Flow" in cash_flow.index and "Capital Expenditures" in cash_flow.index:
                operating_cash = cash_flow.loc["Operating Cash Flow"]
                capital_expenditures = cash_flow.loc["Capital Expenditures"]
                fcf_data = operating_cash + capital_expenditures  # Capital expenditures are negative
            else:
                return {'status': 'error', 'message': 'Could not retrieve Free Cash Flow data'}
            
            # Calculate FCF growth rate
            fcf_values = fcf_data.values
            
            # Calculate year-over-year growth
            if len(fcf_values) >= 2:
                growth_rates = []
                for i in range(len(fcf_values) - 1):
                    if fcf_values[i+1] != 0:  # Avoid division by zero
                        growth_rate = (fcf_values[i] - fcf_values[i+1]) / abs(fcf_values[i+1])
                        growth_rates.append(growth_rate)
                
                avg_growth_rate = sum(growth_rates) / len(growth_rates) if growth_rates else 0.10
            else:
                avg_growth_rate = 0.10  # Default 10% growth if not enough data
            
            # If growth rate is negative or unreasonably high, use a moderate default
            if avg_growth_rate < 0 or avg_growth_rate > 0.5:
                avg_growth_rate = 0.10  # 10% growth as fallback
            
            # Get latest annual FCF
            latest_annual_fcf = fcf_values[0]
            
            # Project FCF for 5 years
            projected_fcf = []
            for year in range(1, 6):
                projected_fcf.append(latest_annual_fcf * ((1 + avg_growth_rate) ** year))
            
            # Calculate terminal value (using perpetuity growth method)
            perpetuity_growth_rate = 0.03  # 3% long-term growth
            discount_rate = 0.10  # 10% discount rate
            
            terminal_value = projected_fcf[-1] * (1 + perpetuity_growth_rate) / (discount_rate - perpetuity_growth_rate)
            
            # Discount all future cash flows
            discounted_fcf = [fcf / ((1 + discount_rate) ** (i + 1)) for i, fcf in enumerate(projected_fcf)]
            discounted_terminal_value = terminal_value / ((1 + discount_rate) ** 5)
            
            # Calculate the intrinsic value
            total_present_value = sum(discounted_fcf) + discounted_terminal_value
            
            # Get shares outstanding
            shares_outstanding = profile.get('mktCap', 0) / profile.get('price', 1)
            
            if shares_outstanding <= 0:
                # Fallback to income statement data
                shares_outstanding = stock.info.get('sharesOutstanding')
                if not shares_outstanding:
                    return {'status': 'error', 'message': 'Could not determine shares outstanding'}
            
            # Calculate intrinsic value per share
            intrinsic_value = total_present_value / shares_outstanding
            
            # Calculate margin of safety
            margin_of_safety = ((intrinsic_value - current_price) / current_price) * 100
            
            return {
                'status': 'success',
                'current_price': current_price,
                'intrinsic_value': intrinsic_value,
                'margin_of_safety_pct': margin_of_safety,
                'projected_fcf': projected_fcf,
                'terminal_value': terminal_value,
                'total_present_value': total_present_value,
                'shares_outstanding': shares_outstanding,
                'assumptions': {
                    'discount_rate': discount_rate,
                    'growth_rate': avg_growth_rate,
                    'terminal_growth_rate': perpetuity_growth_rate,
                    'projection_years': 5
                }
            }
        
        except Exception as e:
            return {'status': 'error', 'message': f'DCF calculation error: {str(e)}'}
    
    @staticmethod
    @tqdm_timer
    def get_company_profile(ticker):
        """
        Fetch company profile information including beta.
        
        Parameters:
            ticker (str): Stock ticker symbol
            
        Returns:
            dict: Company profile data
        """
        url = f"{BASE_URL}/profile/{ticker}?apikey={API_KEY}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            if data and len(data) > 0:
                return data[0]
            return {}
        except Exception as e:
            print(f"Error fetching company profile for {ticker}: {e}")
            return {}
    
    @staticmethod
    @tqdm_timer
    def get_peers(ticker, candidate_features=['beta', 'marketCap', 'volume'], top_n=15):
        df = pd.read_csv('us_equities_metadata.csv')
        if ticker not in df['symbol'].values:
            print(f"Ticker {ticker} not found.")
            return pd.DataFrame()

        target = df[df['symbol'] == ticker].iloc[0]
        peers = df[(df['industry'] == target['industry']) & (df['symbol'] != ticker)].copy()

        # Determine usable features (non-null for both target and peers)
        usable_features = []
        for feat in candidate_features:
            if pd.notnull(target.get(feat)) and peers[feat].notnull().sum() > 0:
                usable_features.append(feat)

        if not usable_features:
            print("No sufficient features available for similarity matching.")
            return pd.DataFrame()

        # Drop peers with missing values in usable features
        peers = peers.dropna(subset=usable_features)

        # Include target in matrix for standardization
        temp_df = pd.concat([peers, pd.DataFrame([target])], ignore_index=True)

        # Standardize and compute distances
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(temp_df[usable_features])
        distances = euclidean_distances([X_scaled[-1]], X_scaled[:-1])[0]

        peers['similarity_distance'] = distances
        closest_peers = peers.sort_values('similarity_distance').head(top_n)

        if len(closest_peers) < top_n:
            print(f"Warning: Could only find {len(closest_peers)} peers for {ticker}, which is less than the requested minimum of {top_n}")
        return list(closest_peers['symbol'])
    # def get_peers(ticker, min_peers=15):
    #     """
    #     Fetch the peer companies for a given ticker, ensuring at least min_peers results when possible.
        
    #     Parameters:
    #         ticker (str): Stock ticker symbol
    #         min_peers (int): Minimum number of peers to return (default is 15)
            
    #     Returns:
    #         list: List of peer company ticker symbols
    #     """
    #     all_peers = []
        
    #     # First strategy: Try to get peers from LLM (most relevant since it can understand business models)
    #     llm_peers = MicroTools._get_peers_from_llm(ticker)
    #     if llm_peers and len(llm_peers) > 0:
    #         all_peers.extend(llm_peers)
    #         print(f"Found {len(llm_peers)} peers from LLM")
        
    #     # Second strategy: Try the Financial Modeling Prep API endpoints
    #     if len(all_peers) < min_peers:
    #         api_peers = MicroTools._get_api_peers(ticker)
            
    #         # Add new peers to our list
    #         for peer in api_peers:
    #             if peer not in all_peers and peer != ticker:
    #                 all_peers.append(peer)
            
    #         if api_peers:
    #             print(f"Found {len(api_peers)} peers from API")
        
    #     # Third strategy: Use sector-based discovery (most reliable for finding peers in same industry)
    #     if len(all_peers) < min_peers:
    #         sector_peers = MicroTools._get_sector_peers(ticker, min_peers - len(all_peers))
    #         for peer in sector_peers:
    #             if peer not in all_peers and peer != ticker:
    #                 all_peers.append(peer)
            
    #         if sector_peers:
    #             print(f"Found {len(sector_peers)} peers from sector analysis")
        
    #     # Last resort: Use index component scanning to find at least some peers
    #     if len(all_peers) < min_peers:
    #         # Try to find additional peers using a more intensive sector scan
    #         index_peers = MicroTools._scan_indices_for_peers(ticker, min_peers - len(all_peers))
    #         for peer in index_peers:
    #             if peer not in all_peers and peer != ticker:
    #                 all_peers.append(peer)
            
    #         if index_peers:
    #             print(f"Found {len(index_peers)} peers from index scan")
                    
    #     # Remove duplicates
    #     all_peers = list(dict.fromkeys(all_peers))
        
    #     # If still not enough peers, we'll warn but return what we have
    #     if len(all_peers) < min_peers:
    #         print(f"Warning: Could only find {len(all_peers)} peers for {ticker}, which is less than the requested minimum of {min_peers}")
            
    #     return all_peers
    
    @staticmethod
    @tqdm_timer
    def _get_api_peers(ticker):
        """
        Get peer companies for a ticker using the Financial Modeling Prep API.
        
        Parameters:
            ticker (str): Stock ticker symbol
            
        Returns:
            list: List of peer company ticker symbols
        """
        api_peers = []
        
        # Try multiple endpoint formats to ensure compatibility
        endpoints = [
            f"{BASE_URL}/stock_peer?symbol={ticker}&apikey={API_KEY}",
            f"{BASE_URL}/stock/peers?symbol={ticker}&apikey={API_KEY}",
            f"{BASE_URL}/stock-peers?symbol={ticker}&apikey={API_KEY}"
        ]
        
        for url in endpoints:
            try:
                response = requests.get(url)
                response.raise_for_status()
                data = response.json()
                
                # Handle different response formats
                if isinstance(data, list) and len(data) > 0:
                    if 'peersList' in data[0]:
                        new_peers = data[0]['peersList'].split(',')
                    else:
                        new_peers = data
                        
                elif isinstance(data, dict) and 'peersList' in data:
                    new_peers = data['peersList'].split(',')
                else:
                    continue
                
                # Add valid peers to our list
                for peer in new_peers:
                    peer = peer.strip()
                    if peer and peer != ticker and peer not in api_peers:
                        api_peers.append(peer)
                        
                if api_peers:
                    break  # If we found peers, no need to try other endpoints
                    
            except Exception as e:
                continue
                
        return api_peers
    
    @staticmethod
    @tqdm_timer
    def _get_sector_peers(ticker, count=15):
        """
        Get peer companies for a given ticker based on their sector and industry.
        Uses a targeted sector-based approach to find same-sector companies.
        
        Parameters:
            ticker (str): Stock ticker symbol
            count (int): Number of peers to try to find
            
        Returns:
            list: List of peer company ticker symbols in the same sector
        """
        try:
            stock = yf.Ticker(ticker)
            target_sector = stock.info.get('sector')
            target_industry = stock.info.get('industry')
            
            if not target_sector and not target_industry:
                return []
            
            # Get a list of tickers in the same sector from predefined lists
            same_sector_tickers = []
            
            # Get the sector peers by checking stock info
            # Start with popular indices to find companies in the same sector
            indices = ['^GSPC', '^NDX', '^DJI']  # S&P 500, NASDAQ 100, Dow Jones
            
            for index_ticker in indices:
                try:
                    # For each index, we'll get components and check their sector
                    index = yf.Ticker(index_ticker)
                    if hasattr(index, 'constituents'):
                        constituents = index.constituents
                    else:
                        # Some alternative method to get index components if available
                        continue
                    
                    # Check each constituent's sector
                    for constituent in constituents[:50]:  # Limit to first 50 to avoid API limits
                        if len(same_sector_tickers) >= count:
                            break
                            
                        try:
                            constituent_ticker = yf.Ticker(constituent)
                            constituent_sector = constituent_ticker.info.get('sector')
                            constituent_industry = constituent_ticker.info.get('industry')
                            
                            # Check for sector and industry match
                            sector_match = target_sector and constituent_sector == target_sector
                            industry_match = target_industry and constituent_industry == target_industry
                            
                            if industry_match or sector_match:
                                if constituent != ticker and constituent not in same_sector_tickers:
                                    same_sector_tickers.append(constituent)
                        except:
                            continue
                except:
                    continue
            
            # If we couldn't get enough peers from indices, try a direct sector search
            if len(same_sector_tickers) < count:
                # Alternative approach: try to get tickers from ETFs in the sector
                try:
                    # Map sectors to sector ETFs
                    sector_etfs = {
                        'Technology': ['XLK', 'VGT', 'QQQ'],
                        'Financial': ['XLF', 'VFH', 'KBWB'],
                        'Healthcare': ['XLV', 'VHT', 'IHI'],
                        'Consumer Discretionary': ['XLY', 'VCR', 'RTH'],
                        'Consumer Staples': ['XLP', 'VDC', 'KXI'],
                        'Energy': ['XLE', 'VDE', 'XOP'],
                        'Utilities': ['XLU', 'VPU', 'IDU'],
                        'Materials': ['XLB', 'VAW', 'IYM'],
                        'Industrial': ['XLI', 'VIS', 'IYJ'],
                        'Communication Services': ['XLC', 'VOX', 'IYZ'],
                        'Real Estate': ['XLRE', 'VNQ', 'IYR']
                    }
                    
                    # Find ETFs for the stock's sector
                    matching_etfs = []
                    for sector, etfs in sector_etfs.items():
                        if target_sector and sector.lower() in target_sector.lower():
                            matching_etfs.extend(etfs)
                    
                    # Get holdings from the sector ETFs
                    for etf in matching_etfs[:2]:  # Limit to first 2 ETFs
                        try:
                            etf_ticker = yf.Ticker(etf)
                            if hasattr(etf_ticker, 'holdings'):
                                for holding in etf_ticker.holdings.index[:30]:
                                    if holding != ticker and holding not in same_sector_tickers:
                                        same_sector_tickers.append(holding)
                                        if len(same_sector_tickers) >= count:
                                            break
                        except:
                            continue
                except:
                    pass
            
            return same_sector_tickers[:count]
            
        except Exception as e:
            print(f"Error finding sector peers for {ticker}: {e}")
            return []
    
    @staticmethod
    @tqdm_timer
    def _scan_indices_for_peers(ticker, count=15):
        """
        Scan major indices to find peers with similar characteristics.
        This is a last resort approach to find additional peers.
        
        Parameters:
            ticker (str): Stock ticker symbol
            count (int): Number of peers to find
            
        Returns:
            list: List of peer company ticker symbols
        """
        try:
            # Get the target stock information
            stock = yf.Ticker(ticker)
            stock_info = stock.info
            
            # Get key characteristics to match
            target_sector = stock_info.get('sector', '')
            target_industry = stock_info.get('industry', '')
            target_market_cap = stock_info.get('marketCap', 0)
            
            # Indices to check
            indices = ['^GSPC', '^NDX', '^DJI', '^RUT']  # S&P 500, NASDAQ 100, Dow Jones, Russell 2000
            
            results = []
            
            # Check index ETFs as well (more reliable for getting components)
            etfs = ['SPY', 'QQQ', 'DIA', 'IWM']
            
            # Main target indices to scan
            all_scan_targets = indices + etfs
            
            for index_symbol in all_scan_targets:
                if len(results) >= count:
                    break
                    
                try:
                    # Get index components/holdings if possible
                    index = yf.Ticker(index_symbol)
                    
                    # Try different ways to get components depending on what's available
                    components = []
                    if hasattr(index, 'holdings'):
                        components = index.holdings.index.tolist()[:50]
                    elif hasattr(index, 'constituents'):
                        components = index.constituents[:50]
                    
                    # If we got components, check them
                    for component in components:
                        if component == ticker or component in results:
                            continue
                            
                        if len(results) >= count:
                            break
                        
                        try:
                            # Check if this component is in the same sector
                            comp_stock = yf.Ticker(component)
                            comp_info = comp_stock.info
                            
                            comp_sector = comp_info.get('sector', '')
                            comp_industry = comp_info.get('industry', '')
                            comp_market_cap = comp_info.get('marketCap', 0)
                            
                            # Score this potential peer based on similarity
                            score = 0
                            
                            # Exact sector match is highest priority
                            if target_sector and comp_sector and target_sector == comp_sector:
                                score += 5
                            
                            # Exact industry match is even better
                            if target_industry and comp_industry and target_industry == comp_industry:
                                score += 10
                            
                            # Similar market cap (within 50% larger or smaller)
                            if target_market_cap and comp_market_cap:
                                if 0.5 * target_market_cap <= comp_market_cap <= 1.5 * target_market_cap:
                                    score += 3
                            
                            # If it's a decent match, add it
                            if score >= 5:  # Threshold for being considered a peer
                                results.append(component)
                        except:
                            continue
                except Exception as e:
                    print(f"Error scanning index {index_symbol}: {e}")
                    continue
            
            return results[:count]
            
        except Exception as e:
            print(f"Error in index scan for peers of {ticker}: {e}")
            return []
    
    @staticmethod
    @tqdm_timer
    def _get_peers_from_llm(ticker):
        """
        Get peer companies for a given ticker using the LLM API.
        This method asks the LLM to identify companies in the same sector with similar business models.
        
        Parameters:
            ticker (str): Stock ticker symbol
            
        Returns:
            list: List of peer company ticker symbols
        """
        try:
            # Get ticker information to identify sector
            stock = yf.Ticker(ticker)
            sector = stock.info.get('sector', '')
            industry = stock.info.get('industry', '')
            business_summary = stock.info.get('longBusinessSummary', '')
            market_cap = stock.info.get('marketCap', '')
            if market_cap:
                market_cap = f"Market Cap: ${market_cap/1e9:.2f} billion"
            
            # Prepare a detailed context for the LLM
            company_context = f"""
            Company: {ticker}
            Sector: {sector}
            Industry: {industry}
            {market_cap}
            Business Summary: {business_summary[:500]}...
            """
            
            # Create a targeted prompt for the LLM
            prompt = f"""
            As a financial expert, I need you to identify peer companies for {ticker} based on the following information:
            
            {company_context}
            
            Please provide at least 15 similar publicly traded companies that are true peers to {ticker} with similar:
            1. Business model and operations
            2. Sector and industry
            3. Market positioning
            4. Competitive landscape
            
            Return ONLY the ticker symbols as a comma-separated list.
            Only include valid ticker symbols of publicly traded companies.
            Include companies of similar size and scale when possible.
            Do not include {ticker} itself in the list.
            
            Example format: AAPL, MSFT, GOOGL, FB, AMZN
            """
            
            # Call the LLM API
            response = deepseek_api_call(prompt)
            
            # Clean and parse the response
            response = response.strip()
            
            # Handle different possible formats in the response
            if ',' in response:
                # Split by comma
                peers = [p.strip() for p in response.split(',')]
            elif '\n' in response:
                # Split by newline
                peers = [p.strip() for p in response.split('\n')]
            else:
                # Assume space-separated
                peers = [p.strip() for p in response.split()]
            
            # Filter out any non-ticker text and the input ticker itself
            peers = [p for p in peers if p.isupper() and len(p) <= 5 and p != ticker]
            
            # Remove duplicates and limit to 20 peers max
            peers = list(dict.fromkeys(peers))[:20]
            
            return peers
        except Exception as e:
            print(f"Error getting peers from LLM for {ticker}: {e}")
            return []
    
    @staticmethod
    @tqdm_timer
    def get_peer_valuation_comparison(ticker):
        """
        Compare key valuation metrics of a company with its peers from the same sector.
        
        Parameters:
            ticker (str): Stock ticker symbol
            
        Returns:
            pd.DataFrame: Valuation comparison of the company and its sector peers
        """
        # Get sector-specific peers
        peers = MicroTools.get_peers(ticker)
        all_tickers = [ticker] + peers  # Include the original ticker first
        
        # Get data for each ticker using yfinance
        valuation_data = []
        for peer_ticker in all_tickers:
            try:
                stock = yf.Ticker(peer_ticker)
                info = stock.info
                
                # Check if we have the necessary data
                if info and 'currentPrice' in info:
                    valuation_data.append({
                        'ticker': peer_ticker,
                        'price': info.get('currentPrice', None),
                        'market_cap': info.get('marketCap', None),
                        'forward_pe': info.get('forwardPE', None),
                        'price_to_book': info.get('priceToBook', None),
                        'ev_to_ebitda': info.get('enterpriseToEbitda', None),
                        'profit_margins': info.get('profitMargins', None),
                        'sector': info.get('sector', None),
                        'industry': info.get('industry', None)
                    })
            except Exception as e:
                print(f"Error fetching data for {peer_ticker}: {e}")
        
        # Create DataFrame and sort by forward PE
        if valuation_data:
            df = pd.DataFrame(valuation_data)
            
            # Convert market cap to billions for readability
            if 'market_cap' in df.columns:
                df['market_cap_B'] = df['market_cap'] / 1e9
            
            # Calculate percentile ranks for key metrics
            metrics_to_rank = ['forward_pe', 'price_to_book', 'ev_to_ebitda']
            for metric in metrics_to_rank:
                if metric in df.columns:
                    df[f'{metric}_rank'] = df[metric].rank(pct=True)
            
            # Sort by market cap by default
            return df.sort_values('market_cap', ascending=False).reset_index(drop=True)
        else:
            print("No valuation data available for any ticker")
            return pd.DataFrame()
    
    @staticmethod
    @tqdm_timer
    def get_peer_beta_comparison(ticker):
        """
        Compare the beta and volatility metrics of a company with its peers.
        
        Parameters:
            ticker (str): Stock ticker symbol
            
        Returns:
            pd.DataFrame: Beta comparison of the company and its sector peers
        """
        # Get sector-specific peers
        peers = MicroTools.get_peers(ticker)
        all_tickers = [ticker] + peers  # Include the original ticker first
        
        # Get beta and other risk metrics for each ticker
        beta_data = []
        for peer_ticker in all_tickers:
            try:
                stock = yf.Ticker(peer_ticker)
                info = stock.info
                
                if info and 'beta' in info:
                    beta_data.append({
                        'ticker': peer_ticker,
                        'beta': info.get('beta', None),
                        'price': info.get('currentPrice', None),
                        'market_cap': info.get('marketCap', None),
                        'sector': info.get('sector', None),
                        'industry': info.get('industry', None),
                        '52w_high': info.get('fiftyTwoWeekHigh', None),
                        '52w_low': info.get('fiftyTwoWeekLow', None)
                    })
            except Exception as e:
                print(f"Error fetching data for {peer_ticker}: {e}")
        
        # Create DataFrame and sort by beta
        if beta_data:
            df = pd.DataFrame(beta_data)
            
            # Calculate 52-week volatility
            if all(col in df.columns for col in ['52w_high', '52w_low', 'price']):
                df['52w_volatility'] = (df['52w_high'] - df['52w_low']) / df['price']
            
            # Convert market cap to billions for readability
            if 'market_cap' in df.columns:
                df['market_cap_B'] = df['market_cap'] / 1e9
                
            return df.sort_values('beta', ascending=True).reset_index(drop=True)
        else:
            print("No beta data available for any ticker")
            return pd.DataFrame()
    
    @staticmethod
    @tqdm_timer
    def get_companies_earnings_calendar(months=6):
        """
        Gets the earnings calendar for companies for the specified period.
        
        Parameters:
            months (int): Number of months to look ahead (default is 6 months)
            
        Returns:
            pd.DataFrame: Earnings calendar data
        """
        # Calculate date range for the next N months
        today = datetime.now()
        future_date = today + timedelta(days=30 * months)
        
        # Format dates for the API
        from_date = today.strftime('%Y-%m-%d')
        to_date = future_date.strftime('%Y-%m-%d')
        
        # Use Financial Modeling Prep API to get earnings calendar
        url = f"{BASE_URL}/earning-calendar?from={from_date}&to={to_date}&apikey={API_KEY}"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            if data:
                # Convert to DataFrame for easier manipulation
                df = pd.DataFrame(data)
                
                # Clean up and format the data
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                    df = df.sort_values('date')
                
                # Add market cap if we have the symbol
                if 'symbol' in df.columns:
                    df['market_cap'] = df['symbol'].apply(MicroTools._get_market_cap)
                    
                    # Convert market cap to billions for readability
                    df['market_cap_B'] = df['market_cap'] / 1e9
                    
                    # Sort by market cap (descending) and then by date
                    df = df.sort_values(['date', 'market_cap'], ascending=[True, False])
                
                # Group by month for easier analysis
                if 'date' in df.columns:
                    df['month'] = df['date'].dt.strftime('%Y-%m')
                
                return df
            else:
                print("No earnings calendar data available")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"Error fetching earnings calendar: {e}")
            return pd.DataFrame()
            
    # Keep the old function name for backward compatibility
    @staticmethod
    @tqdm_timer
    def get_companies_one_month_calendar():
        """
        Gets the earnings calendar for the next month (legacy function)
        
        Returns:
            pd.DataFrame: Earnings calendar data for next month
        """
        return MicroTools.get_companies_earnings_calendar(months=1)
    
    @staticmethod
    @tqdm_timer
    def _get_market_cap(ticker):
        """Helper method to get market cap for a ticker"""
        try:
            stock = yf.Ticker(ticker)
            return stock.info.get('marketCap', 0)
        except:
            return 0
    
    @staticmethod
    @tqdm_timer
    def get_earnings_surprises(ticker, limit=4):
        """
        Fetch the earnings surprises (actual vs. estimate) for a company.
        
        Parameters:
            ticker (str): Stock ticker symbol
            limit (int): Number of past quarters to retrieve
            
        Returns:
            pd.DataFrame: Earnings surprises data
        """
        url = f"{BASE_URL}/earnings-surprises/{ticker}?limit={limit}&apikey={API_KEY}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            if data:
                return pd.DataFrame(data)
            return pd.DataFrame()
        except Exception as e:
            print(f"Error fetching earnings surprises for {ticker}: {e}")
            return pd.DataFrame()
    
    @staticmethod
    @tqdm_timer
    def analyze_earnings_estimates_vs_actual(ticker, limit=4):
        """
        Analyze the gap between earnings estimates and actual results.
        
        Parameters:
            ticker (str): Stock ticker symbol
            limit (int): Number of quarters to analyze
            
        Returns:
            dict: Analysis of earnings estimate vs. actual
        """
        surprises_df = MicroTools.get_earnings_surprises(ticker, limit)
        
        if surprises_df.empty:
            return {'status': 'error', 'message': 'No earnings data available'}
        
        # Calculate metrics
        surprises_df['surprise_pct'] = (surprises_df['actualEarningResult'] - surprises_df['estimatedEarning']) / abs(surprises_df['estimatedEarning']) * 100
        
        # Calculate consistency metrics
        beats = (surprises_df['surprise_pct'] > 0).sum()
        misses = (surprises_df['surprise_pct'] < 0).sum()
        
        # Average surprise percentage
        avg_surprise = surprises_df['surprise_pct'].mean()
        
        # Trend in surprise percentage
        if len(surprises_df) >= 2:
            surprise_trend = surprises_df['surprise_pct'].iloc[0] - surprises_df['surprise_pct'].iloc[-1]
        else:
            surprise_trend = 0
        
        return {
            'data': surprises_df.to_dict('records'),
            'summary': {
                'total_quarters': len(surprises_df),
                'beats': beats,
                'misses': misses,
                'beat_rate': beats / len(surprises_df) if len(surprises_df) > 0 else 0,
                'average_surprise_pct': avg_surprise,
                'surprise_trend': surprise_trend
            }
        }

    # Add LangChain compatibility
    @staticmethod
    @tqdm_timer
    def get_langchain_tools() -> List[Any]:
        """
        Return a list of LangChain-compatible tools based on the MicroTools class methods.
        
        Returns:
            List[Tool]: List of LangChain tools
        """
        if not LANGCHAIN_AVAILABLE:
            print("LangChain is not installed. Please install it to use this functionality.")
            return []
        
        tools = []
        
        # Helper function to convert DataFrames to JSON for LangChain tools
        def convert_df_to_json(result):
            if isinstance(result, pd.DataFrame):
                return result.to_json(orient='records')
            elif isinstance(result, dict):
                for key, value in result.items():
                    if isinstance(value, pd.DataFrame):
                        result[key] = value.to_json(orient='records')
            return result
        
        # Get Key Metrics tool
        tools.append(
            Tool(
                name="get_stock_metrics",
                func=lambda ticker: json.dumps(MicroTools.get_key_metrics(ticker), cls=NumpyJSONEncoder),
                description="Retrieves key financial metrics for a stock. Input should be a stock ticker symbol like 'AAPL'."
            )
        )
        
        # Get Beta tool
        tools.append(
            Tool(
                name="get_stock_beta",
                func=lambda ticker: MicroTools.get_beta(ticker),
                description="Get the beta value for a stock. Input should be a stock ticker symbol."
            )
        )
        
        # Get DCF Valuation tool
        tools.append(
            Tool(
                name="get_stock_dcf_valuation",
                func=lambda ticker: json.dumps(MicroTools.get_dcf_valuation(ticker), cls=NumpyJSONEncoder),
                description="Get the DCF valuation for a stock. Input should be a stock ticker symbol."
            )
        )
        
        # Get Detailed DCF tool
        tools.append(
            Tool(
                name="get_stock_detailed_dcf",
                func=lambda ticker: json.dumps(MicroTools.get_detailed_dcf(ticker), cls=NumpyJSONEncoder),
                description="Get a detailed DCF valuation for a stock. Input should be a stock ticker symbol."
            )
        )
        
        # Get Company Profile tool
        tools.append(
            Tool(
                name="get_company_profile",
                func=lambda ticker: json.dumps(MicroTools.get_company_profile(ticker), cls=NumpyJSONEncoder),
                description="Get profile information for a company. Input should be a stock ticker symbol."
            )
        )
        
        # Get Peers tool
        tools.append(
            Tool(
                name="get_stock_peers",
                func=lambda ticker: json.dumps(MicroTools.get_peers(ticker), cls=NumpyJSONEncoder),
                description="Get a list of peer companies for a stock. Input should be a stock ticker symbol."
            )
        )
        
        # Get Peer Valuation Comparison tool
        tools.append(
            Tool(
                name="get_peer_valuation_comparison",
                func=lambda ticker: convert_df_to_json(MicroTools.get_peer_valuation_comparison(ticker)),
                description="Compare valuation metrics with peer companies. Input should be a stock ticker symbol."
            )
        )
        
        # Get Peer Beta Comparison tool
        tools.append(
            Tool(
                name="get_peer_beta_comparison",
                func=lambda ticker: convert_df_to_json(MicroTools.get_peer_beta_comparison(ticker)),
                description="Compare beta and volatility metrics with peer companies. Input should be a stock ticker symbol."
            )
        )
        
        # Get Earnings Calendar tool
        tools.append(
            Tool(
                name="get_earnings_calendar",
                func=lambda months=6: convert_df_to_json(MicroTools.get_companies_earnings_calendar(int(months))),
                description="Get the earnings calendar for the next N months. Input should be number of months (default is 6)."
            )
        )
        
        # Get Earnings Surprises tool
        tools.append(
            Tool(
                name="get_earnings_surprises",
                func=lambda ticker: convert_df_to_json(MicroTools.get_earnings_surprises(ticker)),
                description="Get historical earnings surprises for a stock. Input should be a stock ticker symbol."
            )
        )
        
        # Analyze Earnings vs Actual tool
        tools.append(
            Tool(
                name="analyze_earnings_vs_estimates",
                func=lambda ticker: json.dumps(MicroTools.analyze_earnings_estimates_vs_actual(ticker), cls=NumpyJSONEncoder),
                description="Analyze the difference between earnings estimates and actual results. Input should be a stock ticker symbol."
            )
        )
        
        return tools

# Example of how to use with LangChain
if __name__ == "__main__" and LANGCHAIN_AVAILABLE:
    try:
        from langchain_community.agents import initialize_agent, AgentType
        from langchain_core.prompts import PromptTemplate
        from langchain_community.agents import create_react_agent
        
        # Try to import DeepSeek integration for LangChain
        try:
            from langchain_community.llms import DeepSeekLLM
            HAS_DEEPSEEK = True
        except ImportError:
            from langchain_community.llms.openai import OpenAI
            HAS_DEEPSEEK = False
            print("DeepSeek LangChain integration not found. Falling back to OpenAI.")
        
        # Get tools
        tools = MicroTools.get_langchain_tools()
        
        # Initialize LLM - try to use DeepSeek if available, otherwise fallback to OpenAI
        if HAS_DEEPSEEK:
            try:
                # Using DeepSeekLLM integration if available
                llm = DeepSeekLLM(
                    api_key=os.environ.get("DEEPSEEK_API_KEY"),
                    model_name="deepseek-chat",
                    temperature=0.1
                )
                print("Using DeepSeek LLM")
            except Exception as e:
                print(f"Error initializing DeepSeek: {e}")
                print("Falling back to default LLM")
                llm = OpenAI(temperature=0)
        else:
            # Fallback to OpenAI
            llm = OpenAI(temperature=0)
        
        # Option 1: Basic agent
        print("Creating basic zero-shot agent...")
        basic_agent = initialize_agent(
            tools, 
            llm, 
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True
        )
        
        # Option 2: Advanced ReAct agent with custom prompt for better reasoning
        # Create a more sophisticated ReAct agent for better financial analysis
        react_template = """You are a sophisticated financial analysis AI assistant with access to various tools.
        Your goal is to provide in-depth financial analysis and insights based on the available data.
        When analyzing stocks, consider multiple factors such as:
        - Fundamental metrics (EPS, P/E ratio, etc.)
        - Peer comparisons
        - Valuation methods (DCF)
        - Market trends and volatility (Beta)
        
        Use the following format:
        
        Question: The input question you must answer
        Thought: You should always think about what to do
        Action: The action to take, should be one of [{tool_names}]
        Action Input: The input to the action
        Observation: The result of the action
        ... (this Thought/Action/Action Input/Observation can repeat N times)
        Thought: I now know the final answer
        Final Answer: The final answer to the original input question
        
        Begin!
        
        Question: {input}
        Thought: """
        
        # Create the prompt
        react_prompt = PromptTemplate.from_template(template=react_template)
        
        # Create the ReAct agent
        print("Creating advanced ReAct reasoning agent...")
        react_agent = create_react_agent(
            llm=llm,
            tools=tools,
            prompt=react_prompt
        )
        
        # Example query
        test_query = "What are the key financial metrics for Apple and how do they compare to its peers?"
        
        print("\nTesting with query: " + test_query)
        
        # Choose which agent to run
        use_react = True  # Set to False to use the basic agent instead
        
        if use_react:
            from langchain_community.agents import AgentExecutor
            agent_executor = AgentExecutor.from_agent_and_tools(
                agent=react_agent,
                tools=tools,
                verbose=True
            )
            result = agent_executor.run(test_query)
        else:
            result = basic_agent.run(test_query)
            
        print("\nFinal Result:")
        print(result)
        
    except ImportError as e:
        print(f"Additional LangChain components not installed: {e}")
        
    except Exception as e:
        print(f"Error running agent: {e}")

# Add a demonstration function for creating a financial analysis agent
def create_financial_analysis_agent(use_deepseek=True, verbose=True):
    """
    Create a financial analysis agent using the MicroTools functions.
    
    Parameters:
        use_deepseek (bool): Whether to try using DeepSeek instead of OpenAI
        verbose (bool): Whether to show verbose output
        
    Returns:
        agent: A LangChain agent configured for financial analysis
    """
    if not LANGCHAIN_AVAILABLE:
        raise ImportError("LangChain is not installed. Please install it to use this functionality.")
        
    try:
        from langchain_community.agents import create_react_agent, AgentExecutor
        from langchain_core.prompts import PromptTemplate
        
        # Get tools
        tools = MicroTools.get_langchain_tools()
        
        # Try to use DeepSeek if requested
        if use_deepseek:
            try:
                from langchain_community.llms import DeepSeekLLM
                llm = DeepSeekLLM(
                    api_key=os.environ.get("DEEPSEEK_API_KEY"),
                    model_name="deepseek-chat",
                    temperature=0.1
                )
                print("Using DeepSeek LLM")
            except ImportError:
                from langchain_community.llms.openai import OpenAI
                llm = OpenAI(temperature=0)
                print("DeepSeek not available. Using OpenAI.")
        else:
            from langchain_community.llms.openai import OpenAI
            llm = OpenAI(temperature=0)
        
        # Create a custom prompt for better financial analysis
        template = """You are an expert financial analyst AI with access to various financial data tools.
        Analyze stocks thoroughly and provide detailed insights based on fundamental and technical indicators.
        Consider valuation metrics, peer comparisons, historical performance, and risk factors (like beta).
        
        Use the following format:
        
        Question: The input question you must answer
        Thought: You should always think about what to do
        Action: The action to take, should be one of [{tool_names}]
        Action Input: The input to the action
        Observation: The result of the action
        ... (this Thought/Action/Action Input/Observation can repeat N times)
        Thought: I now know the final answer
        Final Answer: The final answer to the original input question
        
        Begin!
        
        Question: {input}
        Thought: """
        
        # Create the prompt
        prompt = PromptTemplate.from_template(template=template)
        
        # Create the ReAct agent
        react_agent = create_react_agent(
            llm=llm,
            tools=tools,
            prompt=prompt
        )
        
        # Create the agent executor
        agent_executor = AgentExecutor.from_agent_and_tools(
            agent=react_agent,
            tools=tools,
            verbose=verbose
        )
        
        return agent_executor
        
    except Exception as e:
        print(f"Error creating financial analysis agent: {e}")
        raise 