# Finpresso

## AI-Powered Financial Analysis Platform

Finpresso is an advanced AI-powered financial analysis platform that provides comprehensive stock and market analysis through multiple specialized agents.

### Features

- **Macro Analysis**: Economic trends, interest rates, inflation, GDP forecasts, and sector performance
- **Micro Analysis**: Company fundamentals, financial statements, earnings reports, and analyst ratings
- **Price Analysis**: Technical indicators, price patterns, support/resistance levels, and volatility analysis
- **Investment Strategy**: Integrates all analyses to generate actionable investment strategies with conviction levels

### Components

- **Finpresso_Agent.py**: Main orchestration file for the Finpresso AI analysis workflow
- **Analyst_Macro_Kick_OFF_Agent.py**: Analyzes macroeconomic conditions and trends
- **Micro_Analyst_Agent.py**: Analyzes company-specific financial data and news
- **Price_Agent.py**: Performs technical analysis of stock price patterns
- **Investment_Integration_Agent.py**: Integrates all analyses into a unified investment mindmap

### Usage

Run the main Finpresso agent:

```bash
python Finpresso_Agent.py
```

Then enter a stock ticker when prompted to generate a complete analysis.

### Requirements

- Python 3.7+
- Dependencies listed in `requirements.txt`

To install required dependencies:

```bash
pip install -r requirements.txt
```

### Output

The analysis results are saved in JSON format in the `ALL_Files/Rating_Json` directory, with visualizations stored in the `ALL_Files/Graph` directory.

### License

Copyright © 2024
