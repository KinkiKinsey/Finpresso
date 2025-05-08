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


### Work FLow & Restriction: 
2. Pipeline of Agents


Finpresso_Agent first create a rating json, then it run the Analyst Macro Kick OFF Agent, the  Analyst Macro Kick OFF Agent will run the Macro_News_Agent + Macro_Data_Agent at the same time, and it will generate all columns as I indicate (but this result, the Macro Json part will static/constant store in Macro_File, where it update 24 hours, and when everytime we enter a ticker to go through the pipeline, Finpress_Agent will directly copy and past the whole Macro Json Part to the current ticker’s rating json, then starting from here we do the next part). After we copy and past the Macro Information and the next inference hint in the ticker’s rating json. We then run the Micro_News_Agent where it read all news from companies and generate correspond information and micro news next inference hint in the ticker’s rating json. Then we run the Micro_Analyst_Agent to read both macro hint and micro new hint part from the ticker’s rating json to decide what direction and tools should the micro agent use. After It did it, it will generate the result and an micro to price hint. Then Price_Agent will read the hint to use next level of price tools. Then the Investment_Integration Agent will base on the Macro analyst result (find the rating_json) , micro analyst result and price result in the rating json to generate the integrate investment mindmap   

Througtout the process. The Finpresso_Agent will call the agent in the previous mention order, and store their process in the ticker’ rating json and call back any information from this ticker’ rating json 




3. Agent Files function, input and output 


Files Input and Output (Strictly Follow this format and Pipeline)

When we run Finpresso_Agent.py 

	1). First, Finpresso_Agent.py input is a ticker,  will create an empty json that have columns as follow  ticker(ex:TSLA).json as follow: Macro {} . Micro {}. Price{}. Strategy {}), this rating json  ticker(ex:TSLA).json is real-timely store in the Rating_Json Folder, for latter use.

2). The Macro_Analyst_Agent.py will run and follow the code workflow to Output is an Macro_Analyst_Json.json in the Macro_Files Folder. If this is update within the assign time (as we define the code already in Macro_Analyst_Agent.py) then it wont run everything again.

3). Finpresso_Agent.py will directly copy and paste everything from Macro_Analyst_Json.json to the Macro {} column at ticker(ex:TSLA).json. 

4). Finpress_Agent.py will read the recap part and the given ticker to generate last column in Macro {} Section call Macro_Inference_Hint{} (where this sub column will provide hint for what we should look for in Micro Part next given the Macro situation with this ticker, ex: If Macro is bad for high tech sector, and ticker is high tech, then Micro part might focus on the relatively beta/dcf with same sector peers, etc…) 

5). Then Finpress_Agent.py will run the Micro_News_Agent.py 

6). Micro_News_Agent.py input is a ticker, and outputs is the “Three Key takeaways”, “Micro Expectation”, and “Next_Inference_Hint_Micro_News”  three sub columns in (the The Micro_News input is a ticker, and it follows the design code to read all news and write the result as  Three Key takeaways{}, Micro Expectation{}, Next_Inference_Hint_Micro_News{} as subcolumn in the ticker json under Micro Column)  ticker(ex:TSLA).json

7). Then, Micro_News_Agent.py will also read and generate an inference hint for the next agent, where it tries to guide the following micro analyst agent to call its tools. 

8).Then Finpresso_Agent.py will run the Micro_Analyst_Agent.py 
 Micro_Analyst_Agent.py  will input the both Macro_Inference_Hint{} and Micro_News_Inferece_Hint{} to and use langchain to call the micro_tool.py from Tool Folder and decide and use the tools in inside to analyst the ticker. Then tools will output an string readable format of analyst result with an addition LLM layer. Then output of   Micro_Analyst_Agent.py will write the Reasoning{} , Tools_use{}, Tools_result{}, and Micro_to_Price_Next_Inference{} as subcolumn into the ticker(ex:TSLA).json under Micro Column.

9). Then Finpresso_Agent.py will run the Price_Agent.py， the Price_Agent.py will input the previous Micro_to_Price_Next_Inference{} to call the tools from price_level_tools.py from Tool Folder. Then the Price_Agent.py will output the Price_Reasoning_Column{}  Tools_Use{}, Tool_Result{}  sub column and write to the ticker(ex:TSLA).json under Price Column, and the analyst graph that generate by the price tools into the folder called Graph (Graph Folder) with an folder call by its ticker (ex: TSLA_Graph). Every time for same ticker if it has some graph in it, then delete all graph, and input all news graph.

10). The Finpresso_Agent.py will run the Investment_integration_agent.py to write the last few subcolumns in strategy column



Functionality Restriction :
Finpresso_Agent.py will only serve three functions: 1). create the ticker json 2). Run sequentially as pipeline for each agent only. 3). Stream the output (the text information) for each subcolumn in the Rating Json  in each big column as long as where it get fill immediately  (this will real-time show in the user interface in future, where it shows each step as work workflow) 

The other agent.py will only serve on function 1. Input as assign, and write on the ticker’s rating.json

The Filling order of Rating Json Files is fix, where we fill in Macro, Micro News, Micro Analyst, Price Analyst, and the Invesmtent Strategy


The roots :  1). Finpresso_Agent.py  2).ALL_Files
 (where the ALL_Files contain all agent, all tools, all code we need) . the Finpresso_Agent is at the same level as ALL_Files. 


(all variable name, folder name, functionality workflow, data and restrcition has writen in the explainantion, refer it)
