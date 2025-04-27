#!/usr/bin/env python
# coding: utf-8

# Set non-interactive matplotlib backend to prevent threading issues
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend to avoid NSWindow thread issues

import yfinance as yf
import matplotlib.pyplot as plt
import pandas as pd

import numpy as np

from scipy.stats import norm
import scipy.stats as stats
import numpy as np

from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.statespace.sarimax import SARIMAX
import warnings

import itertools

from sklearn.preprocessing import MinMaxScaler

import matplotlib.dates as mdates
from matplotlib.dates import DateFormatter


from ta.trend import macd_diff

from io import BytesIO
import base64





def bayesian_weight_function(stock_ticker, N, alpha=1):
    """

    Bayesian Risk-Reward Stock Analysis Tool

    You could dynamically change the input parameters to see the performance of the strategy.

    A quantitative trading assistant that evaluates optimal long/short positions using:
    - Bayesian probability-weighted historical analysis
    - Volatility-adjusted risk/reward metrics
    - Interactive scenario testing

    Key Features:
    1. Dynamic Position Analysis:
    - Calculates risk/reward ratios for any stock/ETF
    - Compares long vs. short strategies
    - Supports custom entry/exit prices

    2. Intelligent Weighting:
    - Adjusts for market volatility using Normal-Gamma Bayesian models
    - Probability-weighted expected returns
    - Confidence scoring (0-100%)

    3. Visual Backtesting:
    - Generates annotated price charts with:
        * Entry/exit markers
        * Risk-reward zones
        * Bayesian confidence intervals

    Usage Example:
    >>> analysis, graphs = calculate_risk_reward("AAPL", position_type="long")
    >>> print(analysis)  # Detailed text report
    >>> display_image(graphs["main_plot"])  # Show chart

    Input Parameters:
    - stock_ticker (str): Valid ticker symbol (e.g. "TSLA")
    - position_type (str): "long"|"short"|"both"
    - N (int): Lookback period in days (default: 360)
    - buy_price (float): Optional manual entry price
    - hypothesis_stop_gain/loss (float): Test custom scenarios

    Outputs:
    Tuple[str, dict]:
    - Analysis report (markdown formatted)
    - Dictionary containing:
        * "main_plot": Base64 encoded chart (long/short)
        * "combined_plot": Comparison chart (when position_type="both")

    Integration Notes:
    1. For LangChain: Use @tool decorator with pydantic schema
    2. For Jupyter: display_image(base64.b64decode(graphs["main_plot"]))
    3. Error Handling: Returns clear messages for invalid inputs

    Typical Workflow:
    1. Fetch historical data
    2. Calculate Bayesian probabilities
    3. Generate risk/reward metrics
    4. Visualize optimal strategy

    """       
    np.random.seed(42)

    # Step 1: Download historical stock data
    data = yf.download(stock_ticker, period="10y")['Close'].dropna()[-N:]

    # Compute daily log returns
    returns = ((data - data.shift(1)) / data.shift(1)).dropna().to_numpy()

    # Step 2: Bayesian Predictive Mean & Variance (Normal-Gamma Model)
    prior_mean = np.mean(returns)
    prior_var = np.var(returns, ddof=1)
    alpha_prior = 2
    beta_prior = prior_var

    # Compute posterior mean & variance (Bayesian update)
    sample_mean = np.mean(returns)
    sample_var = np.var(returns, ddof=1)

    posterior_mean = (N * sample_mean + prior_mean) / (N + 1)
    posterior_variance = (beta_prior + np.sum((returns - sample_mean) ** 2) / 2) / (alpha_prior + N / 2)

    # Predictive Mean & Variance
    predictive_mean = posterior_mean
    predictive_variance = posterior_variance + (1 / N)
    sigma = np.sqrt(predictive_variance)

    loss_threshold = predictive_mean - sigma * alpha
    gain_threshold = predictive_mean + sigma * alpha

    expect_loss = abs(loss_threshold)
    expect_gain = abs(gain_threshold)

    return expect_loss, expect_gain

def calculate_risk_reward(stock_ticker, N=360, share=1, buy_price=None, hypothesis_stop_gain=None, hypothesis_stop_loss=None, bayesian_weight=True, position_type='long'):
    analysis_string = ""
    graph_data = {}

    # Validate position_type
    if position_type not in ['long', 'short']:
        raise ValueError("position_type must be either 'long' or 'short'")

    # Download historical stock data
    data = yf.download(stock_ticker, period="10y")
    prices = data['Close'].dropna()[-N:]


    if buy_price is None:
        buy_price = float(prices.values[-1].item())
    
    buy_price = float(buy_price) if isinstance(buy_price, (np.ndarray, pd.Series)) else float(buy_price)
    if prices.empty:
        analysis_string += "No data available for the given stock ticker.\n"
        return analysis_string, graph_data

    # Initialize variables
    long_expected_loss = 0
    long_expected_profit = 0
    short_expected_loss = 0
    short_expected_profit = 0

    # Calculate profit/loss
    long_profit_loss = prices - buy_price
    long_profit_loss = long_profit_loss.dropna()
    short_profit_loss = buy_price - prices
    short_profit_loss = short_profit_loss.dropna()

    # Calculate for long position
    if hypothesis_stop_loss is None:
        long_loss = long_profit_loss[long_profit_loss < 0]
        long_expected_loss = long_loss.mean() if not long_loss.empty else 0
    else:
        long_expected_loss = hypothesis_stop_loss - buy_price

    if hypothesis_stop_gain is None:
        long_profit = long_profit_loss[long_profit_loss > 0]
        long_expected_profit = long_profit.mean() if not long_profit.empty else 0
    else:
        long_expected_profit = hypothesis_stop_gain - buy_price

    # Calculate for short position
    if hypothesis_stop_loss is None:
        short_loss = short_profit_loss[short_profit_loss < 0]
        short_expected_loss = short_loss.mean() if not short_loss.empty else 0
    else:
        short_expected_loss = buy_price - hypothesis_stop_loss

    if hypothesis_stop_gain is None:
        short_profit = short_profit_loss[short_profit_loss > 0]
        short_expected_profit = short_profit.mean() if not short_profit.empty else 0
    else:
        short_expected_profit = buy_price - hypothesis_stop_gain

    # Ensure expected values are scalars
    if isinstance(long_expected_loss, (pd.Series, pd.DataFrame)):
        long_expected_loss = long_expected_loss.values[0] if not long_expected_loss.empty else 0
    if isinstance(long_expected_profit, (pd.Series, pd.DataFrame)):
        long_expected_profit = long_expected_profit.values[0] if not long_expected_profit.empty else 0
    if isinstance(short_expected_loss, (pd.Series, pd.DataFrame)):
        short_expected_loss = short_expected_loss.values[0] if not short_expected_loss.empty else 0
    if isinstance(short_expected_profit, (pd.Series, pd.DataFrame)):
        short_expected_profit = short_expected_profit.values[0] if not short_expected_profit.empty else 0

    # Make loss values negative
    long_expected_loss = -1 * abs(long_expected_loss)
    long_expected_profit = abs(long_expected_profit)
    short_expected_loss = -1 * abs(short_expected_loss)
    short_expected_profit = abs(short_expected_profit)

    # Apply Bayesian weighting
    if bayesian_weight:
        loss_weight, gain_weight = bayesian_weight_function(stock_ticker, N)
        if hypothesis_stop_gain is None:
            long_expected_profit = long_expected_profit * (1 + gain_weight)
            short_expected_profit = short_expected_profit * (1 + loss_weight)
        if hypothesis_stop_loss is None:
            long_expected_loss = long_expected_loss * (1 + loss_weight)
            short_expected_loss = short_expected_loss * (1 + gain_weight)

    # Select values based on position_type
    if position_type == 'long':
        expected_loss = long_expected_loss
        expected_profit = long_expected_profit
    else:
        expected_loss = short_expected_loss
        expected_profit = short_expected_profit

    # Check if there's no risk
    if expected_loss >= 0:
        analysis_string += f"No risk at all for {position_type} position!! ALL IN!!!!!\n"
        return analysis_string, graph_data

    # Total expected loss and gain
    total_expect_loss = share * expected_loss
    total_expect_gain = share * expected_profit

    # Percentage return calculations
    total_stop_loss_return = (abs(expected_loss) / buy_price) * 100 if buy_price != 0 else 0
    total_expect_gain_return = (expected_profit / buy_price) * 100 if buy_price != 0 else 0

    # Calculate risk/reward ratio
    risk_reward_ratio = abs(expected_loss) / expected_profit if expected_profit != 0 else float('inf')
    reverse_risk_reward_ratio = expected_profit / abs(expected_loss) if expected_loss != 0 else float('inf')

    # Generate analysis string
    analysis_string += f"{position_type.capitalize()} Position Analysis for {stock_ticker}:\n"
    analysis_string += "="*50 + "\n"
    analysis_string += f"Risk/Reward Ratio: {risk_reward_ratio:.2f}\n"
    analysis_string += f"Reward per Unit Risk: {reverse_risk_reward_ratio:.2f}\n"
    analysis_string += f"Expected Loss: {expected_loss:.2f} per share\n"
    analysis_string += f"Expected Profit: {expected_profit:.2f} per share\n"
    analysis_string += f"Expected Loss Return: {total_stop_loss_return:.2f}%\n"
    analysis_string += f"Expected Gain Return: {total_expect_gain_return:.2f}%\n"
    analysis_string += f"Total Expected Loss: {total_expect_loss:.2f}\n"
    analysis_string += f"Total Expected Gain: {total_expect_gain:.2f}\n\n"

    # Generate and save the plot
    plt.figure(figsize=(12, 8))
    plt.plot(prices.index, prices, label='Price Trend', color='blue')
    plt.axhline(y=buy_price, color='green', linestyle='--', label='Entry Price')

    if position_type == 'long' or position_type == 'both':
        plt.axhline(y=buy_price + long_expected_profit, color='orange', linestyle='--', 
                   label=f'Long Expected Profit Level: {buy_price + long_expected_profit:.2f}')
        plt.axhline(y=buy_price + long_expected_loss, color='red', linestyle='--', 
                   label=f'Long Expected Loss Level: {buy_price + long_expected_loss:.2f}')
    
    if position_type == 'short' or position_type == 'both':
        plt.axhline(y=buy_price - short_expected_profit, color='purple', linestyle=':', 
                   label=f'Short Expected Profit Level: {buy_price - short_expected_profit:.2f}')
        plt.axhline(y=buy_price - short_expected_loss, color='brown', linestyle=':', 
                   label=f'Short Expected Loss Level: {buy_price - short_expected_loss:.2f}')

    title_prefix = f'{stock_ticker} Risk/Reward for {position_type.capitalize()} Position'
    if bayesian_weight:
        plt.title(f'{title_prefix} with Bayesian Weight')
    else:
        plt.title(title_prefix)

    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.legend(loc='best')
    plt.grid(True)
    
    textstr = f'R/R Ratio: {risk_reward_ratio:.2f}\nReward per Unit Risk: {reverse_risk_reward_ratio:.2f}'
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
    plt.text(0.05, 0.95, textstr, transform=plt.gca().transAxes, fontsize=10,
             verticalalignment='top', bbox=props)
    
    plt.tight_layout()
    
    # Save plot to bytes
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    graph_data['main_plot'] = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()

    # Calculate both long and short for comparison
    if position_type != 'both':
        long_rr = abs(long_expected_loss) / long_expected_profit if long_expected_profit != 0 else float('inf')
        short_rr = abs(short_expected_loss) / short_expected_profit if short_expected_profit != 0 else float('inf')
        
        analysis_string += "Comparison of Long vs Short:\n"
        analysis_string += f"Long Position Risk/Reward: {long_rr:.2f}\n"
        analysis_string += f"Short Position Risk/Reward: {short_rr:.2f}\n"
        
        if long_rr < short_rr and long_rr < 1:
            analysis_string += "Recommendation: Long position has better risk/reward profile\n"
        elif short_rr < long_rr and short_rr < 1:
            analysis_string += "Recommendation: Short position has better risk/reward profile\n"
        else:
            analysis_string += "Recommendation: Both positions have similar or unfavorable risk/reward profiles\n"

    return analysis_string, graph_data

def analyze_both_positions(stock_ticker, price, share, N, hypothesis_stop_gain=None, hypothesis_stop_loss=None, bayesian_weight=True):
    analysis_string = ""
    graph_data = {}

    # Download historical stock data
    data = yf.download(stock_ticker, period="10y")
    prices = data['Close'].dropna()[-N:]
    
    if prices.empty:
        analysis_string += "No data available for the given stock ticker.\n"
        return analysis_string, graph_data
    
    # Calculate for both positions
    long_results = {}
    short_results = {}
    
    # For long positions
    long_profit_loss = prices - price
    long_loss = long_profit_loss[long_profit_loss < 0]
    long_profit = long_profit_loss[long_profit_loss > 0]
    
    long_results['expected_loss'] = long_loss.mean() if not long_loss.empty else 0
    long_results['expected_profit'] = long_profit.mean() if not long_profit.empty else 0
    
    # For short positions
    short_profit_loss = price - prices
    short_loss = short_profit_loss[short_profit_loss < 0]
    short_profit = short_profit_loss[short_profit_loss > 0]
    
    short_results['expected_loss'] = short_loss.mean() if not short_loss.empty else 0
    short_results['expected_profit'] = short_profit.mean() if not short_profit.empty else 0
    
    # Process and normalize values
    for results in [long_results, short_results]:
        if isinstance(results['expected_loss'], (pd.Series, pd.DataFrame)):
            results['expected_loss'] = results['expected_loss'].values[0] if not pd.isna(results['expected_loss']).all() else 0
        if isinstance(results['expected_profit'], (pd.Series, pd.DataFrame)):
            results['expected_profit'] = results['expected_profit'].values[0] if not pd.isna(results['expected_profit']).all() else 0
        
        results['expected_loss'] = -1 * abs(results['expected_loss'])
        results['expected_profit'] = abs(results['expected_profit'])
    
    # Apply Bayesian weighting
    if bayesian_weight:
        loss_weight, gain_weight = bayesian_weight_function(stock_ticker, N)
        
        long_results['expected_profit'] *= (1 + gain_weight)
        long_results['expected_loss'] *= (1 + loss_weight)
        
        short_results['expected_profit'] *= (1 + loss_weight)
        short_results['expected_loss'] *= (1 + gain_weight)
    
    # Calculate risk/reward ratios
    long_results['risk_reward'] = abs(long_results['expected_loss']) / long_results['expected_profit'] if long_results['expected_profit'] != 0 else float('inf')
    short_results['risk_reward'] = abs(short_results['expected_loss']) / short_results['expected_profit'] if short_results['expected_profit'] != 0 else float('inf')
    
    # Generate analysis string
    analysis_string += f"Combined Risk/Reward Analysis for {stock_ticker}:\n"
    analysis_string += "="*50 + "\n"
    analysis_string += f"Long Position: R/R = {long_results['risk_reward']:.2f}, Expected Profit = {long_results['expected_profit']:.2f}, Expected Loss = {long_results['expected_loss']:.2f}\n"
    analysis_string += f"Short Position: R/R = {short_results['risk_reward']:.2f}, Expected Profit = {short_results['expected_profit']:.2f}, Expected Loss = {short_results['expected_loss']:.2f}\n\n"
    
    # Generate recommendation
    if long_results['risk_reward'] < short_results['risk_reward'] and long_results['risk_reward'] < 1:
        recommendation = "Recommended Position: LONG"
    elif short_results['risk_reward'] < long_results['risk_reward'] and short_results['risk_reward'] < 1:
        recommendation = "Recommended Position: SHORT"
    else:
        recommendation = "Recommendation: Consider alternatives (R/R > 1)"
    
    analysis_string += recommendation + "\n"
    
    # Create combined visualization
    plt.figure(figsize=(14, 10))
    
    # Main price plot
    plt.subplot(2, 1, 1)
    plt.plot(prices.index, prices, label='Price Trend', color='blue')
    plt.axhline(y=price, color='green', linestyle='--', label='Entry Price')
    
    # Long position lines
    plt.axhline(y=price + long_results['expected_profit'], color='orange', linestyle='-', 
               label=f'Long Profit Level: {price + long_results["expected_profit"]:.2f}')
    plt.axhline(y=price + long_results['expected_loss'], color='red', linestyle='-', 
               label=f'Long Loss Level: {price + long_results["expected_loss"]:.2f}')
    
    # Short position lines
    plt.axhline(y=price - short_results['expected_profit'], color='purple', linestyle=':', 
               label=f'Short Profit Level: {price - short_results["expected_profit"]:.2f}')
    plt.axhline(y=price - short_results['expected_loss'], color='brown', linestyle=':', 
               label=f'Short Loss Level: {price - short_results["expected_loss"]:.2f}')
    
    plt.title(f'{stock_ticker} Combined Long and Short Risk/Reward Analysis')
    plt.ylabel('Price')
    plt.legend(loc='best')
    plt.grid(True)
    
    # Risk/Reward comparison subplot
    plt.subplot(2, 1, 2)
    positions = ['Long', 'Short']
    rr_values = [long_results['risk_reward'], short_results['risk_reward']]
    profit_values = [long_results['expected_profit'], short_results['expected_profit']]
    loss_values = [abs(long_results['expected_loss']), abs(short_results['expected_loss'])]
    
    x = np.arange(len(positions))
    width = 0.25
    
    plt.bar(x - width, rr_values, width, label='Risk/Reward Ratio')
    plt.bar(x, profit_values, width, label='Expected Profit')
    plt.bar(x + width, loss_values, width, label='Expected Loss')
    
    plt.axhline(y=1, color='red', linestyle='--', label='R/R Threshold')
    plt.xticks(x, positions)
    plt.ylabel('Value')
    plt.title('Risk/Reward Comparison')
    plt.legend(loc='best')
    plt.grid(True, axis='y')
    
    # Add text annotations for R/R values
    for i, rr in enumerate(rr_values):
        plt.text(x[i] - width, rr + 0.1, f'{rr:.2f}', ha='center')
    
    plt.figtext(0.5, 0.01, recommendation, ha='center', fontsize=12, bbox=dict(facecolor='yellow', alpha=0.5))
    
    plt.tight_layout()
    
    # Save plot to bytes
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    graph_data['combined_plot'] = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    
    return analysis_string, graph_data


### Test case ### 

# analysis, graphs = calculate_risk_reward(
#     stock_ticker="AAPL",
#     N=360,  # Use 1 year of historical data
#     share=10,  # Analyzing 10 shares
#     position_type='long'  # Analyzing long position
# )

# # Print the analysis text
# print(analysis)

# # To display the graph (in a Jupyter notebook or web app)
# from IPython.display import Image
# import base64

# Image(base64.b64decode(graphs['main_plot']))





def analyze_sma_crossovers(ticker="AAPL", period="5y", lookforward=90):
    """
SMA/EMA Crossover Analysis Toolkit

You could dynamically change the lookforward period to see the performance of the strategy.

A technical analysis package that evaluates moving average crossover strategies with:
- Performance metrics for golden/death crosses
- Visual backtesting of signals
- Forward-looking return analysis

Contains 3 main functions:

1. analyze_sma_crossovers()
   - Tracks 50/200 SMA crossovers (golden/death crosses)
   - Measures subsequent price performance
   - Optimal for long-term trend following

2. analyze_ema_crossovers() 
   - Monitors 9/21 EMA crossovers
   - Captures short-term momentum shifts
   - Ideal for swing trading strategies

3. print_performance()
   - Helper to display formatted results

Key Features:
- Quantifies max returns after crossovers
- Identifies optimal holding periods
- Generates annotated visualizations
- Supports custom lookback/forward windows

Usage Example:
>>> sma_report, sma_graph = analyze_sma_crossovers("AAPL", period="10y")
>>> ema_report, ema_graph = analyze_ema_crossovers("TSLA", lookforward=14)
>>> print_performance("50/200 SMA", bull_returns, bear_returns)

Input Parameters (for both functions):
- ticker (str): Stock symbol (e.g. "NVDA")
- period (str): Data timeframe (e.g. "5y", "10y")
- lookforward (int): Days to analyze after crossover (default: 90/30)

Outputs:
Tuple[str, dict] containing:
   - Analysis report (markdown formatted)
   - Dictionary with base64-encoded plot:
     * sma_plot for 50/200 SMA
     * ema_plot for 9/21 EMA

Metrics Calculated:
1. For Bullish Crosses:
   - Frequency of occurrences
   - Average/max/median returns
   - Best-case performance

2. For Bearish Crosses:  
   - Same metrics for short opportunities
   - Measures downside protection

Visualization Includes:
- Price + moving averages
- Crossover markers (colored by type)
- Extreme points (peaks/troughs)
- Performance annotations

Integration Notes:
- Returns base64 images for web/chat display
- Use print_performance() for console output
- Handles missing data gracefully

Typical Workflow:
1. Identify crossover events
2. Measure subsequent price movement
3. Compare bull/bear performance
4. Visualize optimal holding periods
    """
    analysis_string = ""
    graph_data = {}
    
    df = yf.download(ticker, period=period)
    if df.empty:
        analysis_string += f"No data found for {ticker}\n"
        return analysis_string, graph_data
    
    dates = df.index.values
    close = df['Close'].values.flatten()
    
    # Calculate SMAs
    sma_50 = pd.Series(close).rolling(window=50).mean().values
    sma_200 = pd.Series(close).rolling(window=200).mean().values
    
    # Find crossovers and signals
    cross = np.where(sma_50 > sma_200, 1, 0)
    signals = np.diff(cross, prepend=0)
    
    # Find extremes
    extremes = []
    cross_indices = np.where(signals != 0)[0]
    
    for i in cross_indices:
        if i + lookforward >= len(close):
            continue
            
        window = close[i:i+lookforward]
        signal = signals[i]
        
        if signal > 0:  # Bullish cross
            peak_idx = np.argmax(window) + i
            max_return = (window.max() - close[i]) / close[i] * 100
            extremes.append((dates[peak_idx], 'peak', max_return))
        else:  # Bearish cross
            trough_idx = np.argmin(window) + i
            max_return = (close[i] - window.min()) / close[i] * 100
            extremes.append((dates[trough_idx], 'trough', max_return))
    
    # Create plot
    plt.figure(figsize=(16, 7))
    plt.plot(dates, close, label="Price", color="black", linewidth=1.5)
    plt.plot(dates, sma_50, label="50-SMA", linestyle="--", color="orange")
    plt.plot(dates, sma_200, label="200-SMA", linestyle="--", color="red")
    
    # Mark crossovers and extremes
    for i, date in enumerate(dates[np.where(signals != 0)]):
        signal = signals[np.where(signals != 0)][i]
        color = 'green' if signal > 0 else 'red'
        plt.axvline(x=date, color=color, alpha=0.3, linestyle=':')
        plt.text(date, close.min()*0.95, f"{'Golden' if color=='green' else 'Death'} Cross", 
                rotation=90, color=color, alpha=0.7)
    
    for date, typ, ret in extremes:
        marker = '^' if typ == 'peak' else 'v'
        plt.scatter(date, close[np.where(dates == date)][0], 
                   color='red', marker=marker, s=100)
    
    plt.title(f"{ticker} 50/200 SMA Crossover Analysis ({period})")
    plt.legend(loc="upper left")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    # Save plot to bytes
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    graph_data['sma_plot'] = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    
    # Calculate performance metrics
    bull_returns = [ret for (_, typ, ret) in extremes if typ == 'peak']
    bear_returns = [ret for (_, typ, ret) in extremes if typ == 'trough']
    
    # Generate analysis string
    analysis_string += f"\n=== {ticker} 50/200 SMA Crossover Analysis ===\n"
    analysis_string += f"Analysis Period: {period}\n"
    analysis_string += f"Lookforward Window: {lookforward} days\n"
    
    if bull_returns:
        analysis_string += f"\nBullish Crosses: {len(bull_returns)}\n"
        analysis_string += f"Average Max Return: {np.mean(bull_returns):.1f}%\n"
        analysis_string += f"Best Return: {max(bull_returns):.1f}%\n"
        analysis_string += f"Median Return: {np.median(bull_returns):.1f}%\n"
    else:
        analysis_string += "\nNo bullish crosses found in this period\n"
    
    if bear_returns:
        analysis_string += f"\nBearish Crosses: {len(bear_returns)}\n"
        analysis_string += f"Average Max Return: {np.mean(bear_returns):.1f}%\n"
        analysis_string += f"Best Return: {max(bear_returns):.1f}%\n"
        analysis_string += f"Median Return: {np.median(bear_returns):.1f}%\n"
    else:
        analysis_string += "\nNo bearish crosses found in this period\n"
    
    return analysis_string, graph_data

def analyze_ema_crossovers(ticker="AAPL", period="5y", lookforward=30):
    """Analyze 9/21 EMA crossovers with performance metrics"""
    analysis_string = ""
    graph_data = {}
    
    df = yf.download(ticker, period=period)
    if df.empty:
        analysis_string += f"No data found for {ticker}\n"
        return analysis_string, graph_data
    
    dates = df.index.values
    close = df['Close'].values.flatten()
    
    # Calculate EMAs
    ema_9 = pd.Series(close).ewm(span=9, adjust=False).mean().values
    ema_21 = pd.Series(close).ewm(span=21, adjust=False).mean().values
    
    # Find crossovers and signals
    cross = np.where(ema_9 > ema_21, 1, 0)
    signals = np.diff(cross, prepend=0)
    
    # Find extremes
    extremes = []
    cross_indices = np.where(signals != 0)[0]
    
    for i in cross_indices:
        if i + lookforward >= len(close):
            continue
            
        window = close[i:i+lookforward]
        signal = signals[i]
        
        if signal > 0:  # Bullish cross
            peak_idx = np.argmax(window) + i
            max_return = (window.max() - close[i]) / close[i] * 100
            extremes.append((dates[peak_idx], 'peak', max_return))
        else:  # Bearish cross
            trough_idx = np.argmin(window) + i
            max_return = (close[i] - window.min()) / close[i] * 100
            extremes.append((dates[trough_idx], 'trough', max_return))
    
    # Create plot
    plt.figure(figsize=(16, 7))
    plt.plot(dates, close, label="Price", color="black", linewidth=1.5)
    plt.plot(dates, ema_9, label="9-EMA", linestyle="-.", color="blue")
    plt.plot(dates, ema_21, label="21-EMA", linestyle="-.", color="purple")
    
    # Mark crossovers and extremes
    for i, date in enumerate(dates[np.where(signals != 0)]):
        signal = signals[np.where(signals != 0)][i]
        color = 'green' if signal > 0 else 'red'
        plt.axvline(x=date, color=color, alpha=0.3, linestyle=':')
        plt.text(date, close.min()*0.95, "EMA Cross", rotation=90, color=color, alpha=0.7)
    
    for date, typ, ret in extremes:
        marker = '^' if typ == 'peak' else 'v'
        plt.scatter(date, close[np.where(dates == date)][0], 
                   color='red', marker=marker, s=100)
    
    plt.title(f"{ticker} 9/21 EMA Crossover Analysis ({period})")
    plt.legend(loc="upper left")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    # Save plot to bytes
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    graph_data['ema_plot'] = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    
    # Calculate performance metrics
    bull_returns = [ret for (_, typ, ret) in extremes if typ == 'peak']
    bear_returns = [ret for (_, typ, ret) in extremes if typ == 'trough']
    
    # Generate analysis string
    analysis_string += f"\n=== {ticker} 9/21 EMA Crossover Analysis ===\n"
    analysis_string += f"Analysis Period: {period}\n"
    analysis_string += f"Lookforward Window: {lookforward} days\n"
    
    if bull_returns:
        analysis_string += f"\nBullish Crosses: {len(bull_returns)}\n"
        analysis_string += f"Average Max Return: {np.mean(bull_returns):.1f}%\n"
        analysis_string += f"Best Return: {max(bull_returns):.1f}%\n"
        analysis_string += f"Median Return: {np.median(bull_returns):.1f}%\n"
    else:
        analysis_string += "\nNo bullish crosses found in this period\n"
    
    if bear_returns:
        analysis_string += f"\nBearish Crosses: {len(bear_returns)}\n"
        analysis_string += f"Average Max Return: {np.mean(bear_returns):.1f}%\n"
        analysis_string += f"Best Return: {max(bear_returns):.1f}%\n"
        analysis_string += f"Median Return: {np.median(bear_returns):.1f}%\n"
    else:
        analysis_string += "\nNo bearish crosses found in this period\n"
    
    return analysis_string, graph_data

def print_performance(name, bull_returns, bear_returns):
    """Helper function to print performance metrics"""
    print(f"\n=== {name} Crossover Performance ===")
    if bull_returns:
        print(f"Bullish Crosses: {len(bull_returns)}")
        print(f"Average Max Return: {np.mean(bull_returns):.1f}%")
        print(f"Best Return: {max(bull_returns):.1f}%")
    if bear_returns:
        print(f"\nBearish Crosses: {len(bear_returns)}")
        print(f"Average Max Return: {np.mean(bear_returns):.1f}%")
        print(f"Best Return: {max(bear_returns):.1f}%")


# ### Example Usage ###
# # Analyze SMA crossovers
# sma_analysis, sma_graphs = analyze_sma_crossovers(ticker="AAPL", period="10y")

# # Print the analysis
# print(sma_analysis)

# # Display the graph (in Jupyter notebook)
# from IPython.display import Image
# import base64

# Image(base64.b64decode(sma_graphs['sma_plot']))






def volume_weighted_macd(close, volume, fast=12, slow=26, signal=9):

    """
Volume-Weighted MACD Analysis Toolkit

A sophisticated technical analysis tool that enhances traditional MACD with volume weighting,
providing clearer signals by combining price momentum with trading volume activity.

Core Components:
1. volume_weighted_macd(): Calculates the volume-adjusted MACD values
2. generate_analysis_report(): Generates a human-readable interpretation of signals
3. analyze_vw_macd(): Complete analysis pipeline with visualization

Key Features:
- Volume-Weighted Signals: Amplifies moves with high volume confirmation
- Triple-Panel Visualization: Price action, volume, and MACD in one view
- Smart Signal Detection: Identifies bullish/bearish crosses with confidence scoring
- Momentum Scoring: Quantifies strength of current trend
- Historical Context: Shows recent performance statistics

Usage Example:
>>> analysis, graphs = analyze_vw_macd("AAPL", "6mo")
>>> print(analysis)  # Textual analysis report
>>> display_image(graphs["vw_macd_plot"])  # Show the chart

Input Parameters:
- ticker (str): Stock symbol (e.g. "TSLA")
- period (str): Analysis timeframe (e.g. "1y", "6mo")
- fast/slow/signal (int): MACD parameters (default 12/26/9)

Outputs:
Tuple containing:
1. Analysis report (str) with:
   - Current signal status
   - Momentum assessment
   - Historical performance
   - Trading recommendations
2. Dictionary with base64-encoded chart

Technical Details:
- Volume Normalization: Scales volume to 0-1 range for consistent weighting
- Signal Calculation: 9-period EMA of VW-MACD
- Trend Confirmation: Requires price trend alignment for strong signals

Visualization Includes:
1. Price Panel:
   - Closing prices with trend-colored fills
   - Green/red shading for up/down days
2. Volume Panel:
   - Volume bars colored by daily direction
3. MACD Panel:
   - VW-MACD and signal line
   - Bullish/bearish shaded areas
   - Zero line reference

Signal Interpretation Guide:
🟢 Strong Bullish: MACD > Signal AND > 0 line
🔴 Strong Bearish: MACD < Signal AND < 0 line
🟡 Weak Signal: Small MACD/Signal divergence

Integration Notes:
- Returns base64 images for web/chat display
- Handles missing data gracefully
- Compatible with pandas/numpy arrays
- Includes error handling for API failures

Typical Workflow:
1. Download price/volume data
2. Calculate volume-weighted MACD
3. Generate trading signals
4. Assess momentum strength
5. Visualize results
"""

    """Calculate Volume-Weighted MACD"""
    close = np.asarray(close).flatten()
    volume = np.asarray(volume).flatten()
    
    if close.size == 0 or volume.size == 0:
        return np.array([]), np.array([])
    
    # Normalize volume
    volume_safe = np.where(volume > 0, volume, 1e-10)
    norm_volume = (volume_safe - volume_safe.min()) / (volume_safe.max() - volume_safe.min() + 1e-10)
    
    # Calculate EMAs
    ema_fast = pd.Series(close).ewm(span=fast, adjust=False).mean().values
    ema_slow = pd.Series(close).ewm(span=slow, adjust=False).mean().values
    
    vw_macd = (ema_fast - ema_slow) * norm_volume
    signal_line = pd.Series(vw_macd).ewm(span=signal, adjust=False).mean().values
    
    return vw_macd, signal_line

def generate_analysis_report(vw_macd, signal_line, close_prices, ticker, period):
    """Generate trading analysis report"""
    report = []
    
    # Header
    report.append(f"📊 {ticker} VOLUME-WEIGHTED MACD ANALYSIS ({period})")
    report.append("="*50)
    
    # Current values
    current_macd = vw_macd[-1]
    current_signal = signal_line[-1]
    price_trend = close_prices[-1] - close_prices[-5] if len(close_prices) >= 5 else 0
    
    report.append(f"\n🔹 Current VW-MACD: {current_macd:.4f}")
    report.append(f"🔹 Current Signal: {current_signal:.4f}")
    report.append(f"🔹 5-Day Price Trend: {'↑' if price_trend > 0 else '↓'} {abs(price_trend):.2f}")
    
    # Signal analysis
    if current_macd > current_signal:
        report.append("\n🟢 BULLISH SIGNAL: VW-MACD above Signal line")
        if vw_macd[-1] > 0 and vw_macd[-2] <= 0:
            report.append("🟢 STRONG BULLISH: Crossed above zero line")
    else:
        report.append("\n🔴 BEARISH SIGNAL: VW-MACD below Signal line")
        if vw_macd[-1] < 0 and vw_macd[-2] >= 0:
            report.append("🔴 STRONG BEARISH: Crossed below zero line")
    
    # Momentum strength
    macd_diff = abs(current_macd - current_signal)
    avg_diff = np.mean(np.abs(np.diff(vw_macd[-10:]))) if len(vw_macd) >= 10 else 0
    
    report.append("\n💪 MOMENTUM ANALYSIS:")
    if macd_diff > avg_diff * 1.5:
        report.append("🔥 STRONG MOMENTUM: Current divergence > 1.5x average")
    elif macd_diff > avg_diff:
        report.append("🔸 MODERATE MOMENTUM: Current divergence > average")
    else:
        report.append("🟡 WEAK MOMENTUM: Current divergence ≤ average")
    
    # Historical performance
    if len(vw_macd) > 20:
        above_signal = np.sum(vw_macd[-20:] > signal_line[-20:])
        report.append(f"\n📈 RECENT PERFORMANCE: {above_signal}/20 days above signal line")
    
    return "\n".join(report)

def analyze_vw_macd(ticker='TSLA', period='1y'):
    """Analyze volume-weighted MACD and return results"""
    analysis_string = ""
    graph_data = {}
    
    try:
        # Get data
        data = yf.download(ticker, period=period, progress=False)
        if data.empty:
            analysis_string = f"No data available for {ticker}"
            return analysis_string, graph_data
        
        close = data['Close'].values.flatten()
        volume = data['Volume'].values.flatten()
        dates = data.index
        
        # Calculate indicators
        vw_macd, signal_line = volume_weighted_macd(close, volume)
        
        if vw_macd.size == 0 or signal_line.size == 0:
            analysis_string = "Indicator calculation failed"
            return analysis_string, graph_data
        
        # Create figure
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 10), 
                                           gridspec_kw={'height_ratios': [3, 1, 1]})
        
        # Price plot with trend coloring
        ax1.plot(dates, close, 'k-', label='Price')
        ax1.fill_between(dates, close, close.min(), 
                        where=(close > np.roll(close,1)), 
                        facecolor='green', alpha=0.1)
        ax1.fill_between(dates, close, close.min(), 
                        where=(close <= np.roll(close,1)), 
                        facecolor='red', alpha=0.1)
        ax1.set_title(f'{ticker} Volume-Weighted MACD ({period})')
        ax1.grid(True, alpha=0.3)
        
        # Volume plot with simple green/red
        colors = ['green' if close[i] > close[i-1] else 'red' 
                for i in range(1, len(close))]
        ax2.bar(dates[1:], volume[1:], color=colors, alpha=0.3)
        ax2.grid(True, alpha=0.1)
        
        # MACD plot with colored fills
        ax3.plot(dates, vw_macd, 'b-', label='VW-MACD')
        ax3.plot(dates, signal_line, 'r--', label='Signal')
        ax3.fill_between(dates, vw_macd, signal_line, 
                        where=(vw_macd > signal_line), 
                        facecolor='green', alpha=0.2)
        ax3.fill_between(dates, vw_macd, signal_line,
                        where=(vw_macd <= signal_line),
                        facecolor='red', alpha=0.2)
        ax3.axhline(0, color='gray', ls='--')
        ax3.legend()
        ax3.grid(True, alpha=0.2)
        
        # Formatting
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Save plot to bytes
        buf = BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        graph_data['vw_macd_plot'] = base64.b64encode(buf.read()).decode('utf-8')
        plt.close()
        
        # Generate analysis report
        analysis_string = generate_analysis_report(vw_macd, signal_line, close, ticker, period)
        
        return analysis_string, graph_data
        
    except Exception as e:
        analysis_string = f"Error occurred: {str(e)}"
        return analysis_string, graph_data



### Example Usage ### 

# analysis, graphs = analyze_vw_macd('TSLA', '1y')
# print(analysis)  # This shows only the text analysis

# # To show the graph:
# from IPython.display import Image
# import base64
# Image(base64.b64decode(graphs['vw_macd_plot']))  # Add this line