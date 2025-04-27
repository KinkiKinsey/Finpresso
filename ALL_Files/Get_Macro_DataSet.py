import requests
import json
import pandas as pd
import time
from datetime import datetime
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
import seaborn as sns

import feedparser
import requests
from bs4 import BeautifulSoup
import time

from datetime import datetime
import pandas as pd

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import pandas as pd
import time
from openai import OpenAI
import re

from os import read




def expand_quarterly_to_monthly(data_dict):

  ## This Code Help to Convert Some Quarter from Macro DataSet to Montly
    expanded_data = {}
    for year, quarters in data_dict.items():
        for quarter, value in quarters.items():
            if 'Q1' in quarter:
                expanded_data[f"{year}-01"] = value
                expanded_data[f"{year}-02"] = value
                expanded_data[f"{year}-03"] = value
            elif 'Q2' in quarter:
                expanded_data[f"{year}-04"] = value
                expanded_data[f"{year}-05"] = value
                expanded_data[f"{year}-06"] = value
            elif 'Q3' in quarter:
                expanded_data[f"{year}-07"] = value
                expanded_data[f"{year}-08"] = value
                expanded_data[f"{year}-09"] = value
            elif 'Q4' in quarter:
                expanded_data[f"{year}-10"] = value
                expanded_data[f"{year}-11"] = value
                expanded_data[f"{year}-12"] = value
    return expanded_data


def process_monthly_data(data_dict):
  ## This Code Help to Some Month Data Convert Correctly
    processed_data = {}
    for year, months in data_dict.items():
        for month_key, value in months.items():
            month_num = month_key.replace("Mo", "")
            processed_data[f"{year}-{month_num.zfill(2)}"] = value
    return processed_data




def Get_Current_Post_Macro_Data(download=False): 

    ###### This Main Function #######
    ############## Description: This function will get most recent 1 to 3 years Macro_Data in turn of DF format #################


    ######### Here is the Data API #########

    print("Agent Downloading Macro Dataset")
    # BLU API key
    BLU_API_KEY = 'B46497CB-8778-47B7-A988-6D10B64C5C87'

    # BLU Url
    BLU_base_url = "https://apps.bea.gov/api/data/"


    # BLS API key
    BLS_API_key = "8011ce47c9d24985a95465dc712450dc"

    # BLS API URL
    BLS_url = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

    # FREQ API API
    FRED_API_Key = '2f76a862282c1968a33ea5faf143f78e'

    # FREQ API URL
    FRED_API_url = "https://api.stlouisfed.org/fred/series/observations"


    ####################################### GDP #######################################
    print("Agent Downloading GDP Dataset")


    current_year = datetime.now().year
    years = [str(current_year - i) for i in range(11)]

    gdp_quarterly_growth= {}

    for year in years:
        params = {
            "UserID": BLU_API_KEY,
            "METHOD": "GetData",
            "DATASETNAME": "NIPA",
            "TABLENAME": "T10101",
            "FREQUENCY": "Q",
            "YEAR": year,
            "RESULTFORMAT": "JSON"
        }

        response = requests.get(BLU_base_url, params=params)

        if response.status_code == 200:
            try:
                data = response.json()
                gdp_data = data["BEAAPI"]["Results"]["Data"]

                gdp_quarterly_growth[year] = {
                    item["TimePeriod"]: item["DataValue"]
                    for item in gdp_data if item["LineDescription"] == "Gross domestic product, current dollars"
                }
            except (KeyError, TypeError):
                print(f"Skipping {year} due to missing data structure.")
        else:
            print(f"Error retrieving data for {year}: {response.status_code}")


    ####################################### PCE #######################################
    print("Agent Downloading PCE Dataset")


    pce_quarterly = {}


    for year in years:
        params = {
            "UserID": BLU_API_KEY,
            "METHOD": "GetData",
            "DATASETNAME": "NIPA",
            "TABLENAME": "T10101",
            "FREQUENCY": "Q",
            "YEAR": year,
            "RESULTFORMAT": "JSON"
        }

        response = requests.get(BLU_base_url, params=params)

        if response.status_code == 200:
            try:
                data = response.json()
                pce_data = data["BEAAPI"]["Results"]["Data"]

                pce_quarterly[year] = {
                    item["TimePeriod"]: item["DataValue"]
                    for item in pce_data if item["LineDescription"] == "Personal consumption expenditures"
                }
            except (KeyError, TypeError):
                print(f"Skipping {year} due to missing data structure.")
        else:
            print(f"Error retrieving data for {year}: {response.status_code}")

    ####################################### CPI #######################################

    print("Agent Downloading CPI Dataset")

    # CPI-U (Consumer Price Index for All Urban Consumers)
    series_id = "CUUR0000SA0"

    # Get the current year
    current_year = datetime.now().year

    # API Request Payload
    payload = {
        "seriesid": [series_id],
        "startyear": f"{current_year - 10}",
        "endyear": f"{current_year}",
        "registrationkey": BLS_API_key
    }

    # Make API Request
    response = requests.post(BLS_url, json=payload)

    # Parse Response
    if response.status_code == 200:
        data = response.json()
        if data["status"] == "REQUEST_SUCCEEDED":
            cpi_data = data["Results"]["series"][0]["data"][:40]

            # Extract CPI values and their dates
            cpi_values = [float(entry["value"]) for entry in reversed(cpi_data)]
            cpi_dates = [(entry["year"], entry["period"]) for entry in reversed(cpi_data)]

            # Calculate percentage change and format the output
            percentage_changes = [
                {
                    "year": cpi_dates[i][0],
                    "month": f"Mo{int(cpi_dates[i][1][1:])}",  # Convert "M01" to "the 1 Month"
                    "change": f"{cpi_values[i]}"
                }
                for i in range(1, len(cpi_values))
            ]

            # Store results in JSON format with the correct order
            cpi_json = {}
            for entry in percentage_changes:
                year = entry["year"]
                month = entry["month"]
                if year not in cpi_json:
                    cpi_json[year] = {}
                cpi_json[year][month] = entry["change"]

            # **Reverse the year order to display most recent years first**
            cpi_json = dict(sorted(cpi_json.items(), key=lambda x: x[0], reverse=True))

            # Save to JSON file
            #with open("cpi_percentage_changes.json", "w") as json_file:
                #json.dump(cpi_json, json_file, indent=4)

            # Print formatted JSON result
            #print(json.dumps(cpi_json, indent=4))

        else:
            print("Error:", data["message"])
    else:
        print("Failed to retrieve data. Status code:", response.status_code)



    ################### Unemployment Rate #####################


    print("Agent Downloading Unemployment Rate Dataset")




    # **Unemployment Rate Series ID (U-3, seasonally adjusted)**
    series_id = "LNS14000000"  # This tracks the national unemployment rate (seasonally adjusted)

    # Get the current year
    current_year = datetime.now().year

    # API Request Payload
    payload = {
        "seriesid": [series_id],
        "startyear": f"{current_year - 10}",
        "endyear": f"{current_year}",
        "registrationkey": BLS_API_key
    }

    # Make API Request
    response = requests.post(BLS_url, json=payload)

    # Parse Response
    if response.status_code == 200:
        data = response.json()
        if data["status"] == "REQUEST_SUCCEEDED":
            unemployment_data = data["Results"]["series"][0]["data"][:40]  # Get last 40 months of data

            # Extract unemployment values and their dates
            unemployment_values = [float(entry["value"]) for entry in reversed(unemployment_data)]
            unemployment_dates = [(entry["year"], entry["period"]) for entry in reversed(unemployment_data)]

            # Calculate percentage change and format the output
            percentage_changes = [
                {
                    "year": unemployment_dates[i][0],
                    "month": f"Mo{int(unemployment_dates[i][1][1:])}",  # Convert "M01" to "Mo1"
                    "change": f"{unemployment_values[i]}"
                }
                for i in range(1, len(unemployment_values))
            ]

            # Store results in JSON format with the correct order
            unemployment_json = {}
            for entry in percentage_changes:
                year = entry["year"]
                month = entry["month"]
                if year not in unemployment_json:
                    unemployment_json[year] = {}
                unemployment_json[year][month] = entry["change"]

            # **Reverse the year order to display most recent years first**
            unemployment_json = dict(sorted(unemployment_json.items(), key=lambda x: x[0], reverse=True))

            # Save to JSON file
            #with open("unemployment_percentage_changes.json", "w") as json_file:
                #json.dump(unemployment_json, json_file, indent=4)

            # Print formatted JSON result
            #print(json.dumps(unemployment_growth_json, indent=4))

        else:
            print("Error:", data["message"])
    else:
        print("Failed to retrieve data. Status code:", response.status_code)

    ######################## PPI ###############################

    print("Agent Downloading PPI Dataset")


    series_id = "WPSFD4"


    current_year = datetime.now().year

    # API Request Payload
    payload = {
        "seriesid": [series_id],
        "startyear": f"{current_year - 10}",
        "endyear": f"{current_year}",
        "registrationkey": BLS_API_key
    }

    # Make API Request
    response = requests.post(BLS_url, json=payload)

    # Parse Response
    if response.status_code == 200:
        data = response.json()
        if data["status"] == "REQUEST_SUCCEEDED":
            ppi_data = data["Results"]["series"][0]["data"][:40]  # Get last 40 months of data

            # Extract PPI values and their dates
            ppi_values = [float(entry["value"]) for entry in reversed(ppi_data)]
            ppi_dates = [(entry["year"], entry["period"]) for entry in reversed(ppi_data)]

            # Calculate percentage change and format the output
            percentage_changes = [
                {
                    "year": ppi_dates[i][0],
                    "month": f"Mo{int(ppi_dates[i][1][1:])}",  # Convert "M01" to "Mo1"
                    "change": f"{round((ppi_values[i] - ppi_values[i-1]) / ppi_values[i-1] * 100, 2)}%"
                }
                for i in range(1, len(ppi_values))
            ]

            # Store results in JSON format with the correct order
            ppi_growth_json = {}
            for entry in percentage_changes:
                year = entry["year"]
                month = entry["month"]
                if year not in ppi_growth_json:
                    ppi_growth_json[year] = {}
                ppi_growth_json[year][month] = entry["change"]

            # **Reverse the year order to display most recent years first**
            ppi_growth_json = dict(sorted(ppi_growth_json.items(), key=lambda x: x[0], reverse=True))

            # Save to JSON file
            #with open("ppi_percentage_changes.json", "w") as json_file:
                #json.dump(ppi_growth_json, json_file, indent=4)

            # Print formatted JSON result
            #print(json.dumps(ppi_growth_json, indent=4))

        else:
            print("Error:", data["message"])
    else:
        print("Failed to retrieve data. Status code:", response.status_code)



    ############################# Export & Import ######################################

    print("Agent Downloading Export & Import Dataset")



    # **Producer Price Index (PPI) Series ID**
    series_id = "WPSFD4"  # This tracks the **Final Demand PPI** (seasonally adjusted)

    # Get the current year
    current_year = datetime.now().year

    # API Request Payload
    payload = {
        "seriesid": [series_id],
        "startyear": f"{current_year - 10}",
        "endyear": f"{current_year}",
        "registrationkey": BLS_API_key
    }

    # Make API Request
    response = requests.post(BLS_url, json=payload)

    # Parse Response
    if response.status_code == 200:
        data = response.json()
        if data["status"] == "REQUEST_SUCCEEDED":
            ppi_data = data["Results"]["series"][0]["data"][:40]  # Get last 40 months of data

            # Extract PPI values and their dates
            ppi_values = [float(entry["value"]) for entry in reversed(ppi_data)]
            ppi_dates = [(entry["year"], entry["period"]) for entry in reversed(ppi_data)]

            # Calculate percentage change and format the output
            percentage_changes = [
                {
                    "year": ppi_dates[i][0],
                    "month": f"Mo{int(ppi_dates[i][1][1:])}",  # Convert "M01" to "Mo1"
                    "change": f"{ppi_values[i]}"
                }
                for i in range(1, len(ppi_values))
            ]

            # Store results in JSON format with the correct order
            ppi_growth_json = {}
            for entry in percentage_changes:
                year = entry["year"]
                month = entry["month"]
                if year not in ppi_growth_json:
                    ppi_growth_json[year] = {}
                ppi_growth_json[year][month] = entry["change"]

            # **Reverse the year order to display most recent years first**
            ppi_growth_json = dict(sorted(ppi_growth_json.items(), key=lambda x: x[0], reverse=True))

            # Save to JSON file
            #with open("ppi_percentage_changes.json", "w") as json_file:
                #json.dump(ppi_growth_json, json_file, indent=4)

            # Print formatted JSON result
            #print(json.dumps(ppi_growth_json, indent=4))

        else:
            print("Error:", data["message"])
    else:
        print("Failed to retrieve data. Status code:", response.status_code)


    ######################## Export & Import ###############################
    print("Agent Downloading Export & Import Dataset")




    current_year = datetime.now().year


    # **Export Price Index Series ID**
    export_series_id = "EIUIR"
    # **Import Price Index Series ID**
    import_series_id = "EIUIQ"

    # Get the current year
    current_year = datetime.now().year

    # ----------------------- EXPORT PRICE INDEX -----------------------
    payload_export = {
        "seriesid": [export_series_id],
        "startyear": f"{current_year - 2}",
        "endyear": f"{current_year}",
        "registrationkey": BLS_API_key
    }

    response_export = requests.post(BLS_url, json=payload_export)

    if response_export.status_code == 200:
        data_export = response_export.json()
        if data_export["status"] == "REQUEST_SUCCEEDED":
            export_data = data_export["Results"]["series"][0]["data"][:40]  # Get last 40 months

            # Extract values and dates
            export_values = [float(entry["value"]) for entry in reversed(export_data)]
            export_dates = [(entry["year"], entry["period"]) for entry in reversed(export_data)]

            # Calculate percentage change
            export_percentage_changes = [
                {
                    "year": export_dates[i][0],
                    "month": f"Mo{int(export_dates[i][1][1:])}",
                    "change": f"{export_values[i]}"
                }
                for i in range(1, len(export_values))
            ]

            # Store results in JSON format
            export_growth_json = {}
            for entry in export_percentage_changes:
                year = entry["year"]
                month = entry["month"]
                if year not in export_growth_json:
                    export_growth_json[year] = {}
                export_growth_json[year][month] = entry["change"]

            # Reverse the year order to display most recent years first
            export_growth_json = dict(sorted(export_growth_json.items(), key=lambda x: x[0], reverse=True))

            # Save to JSON file
            #with open("export_price_index_percentage_changes.json", "w") as json_file:
                #json.dump(export_growth_json, json_file, indent=4)

            # Print formatted JSON result
            #print("Export Price Index Data Saved.")
            #print(json.dumps(export_growth_json, indent=4))

        else:
            print("Error fetching Export Price Index:", data_export["message"])
    else:
        print("Failed to retrieve Export Price Index data. Status code:", response_export.status_code)

    # ----------------------- IMPORT PRICE INDEX -----------------------
    payload_import = {
        "seriesid": [import_series_id],
        "startyear": f"{current_year - 10}",
        "endyear": f"{current_year}",
        "registrationkey": BLS_API_key
    }

    response_import = requests.post(BLS_url, json=payload_import)

    if response_import.status_code == 200:
        data_import = response_import.json()
        if data_import["status"] == "REQUEST_SUCCEEDED":
            import_data = data_import["Results"]["series"][0]["data"][:40]  # Get last 40 months

            # Extract values and dates
            import_values = [float(entry["value"]) for entry in reversed(import_data)]
            import_dates = [(entry["year"], entry["period"]) for entry in reversed(import_data)]

            # Calculate percentage change
            import_percentage_changes = [
                {
                    "year": import_dates[i][0],
                    "month": f"Mo{int(import_dates[i][1][1:])}",
                    "change": f"{import_values[i]}"
                }
                for i in range(1, len(import_values))
            ]

            # Store results in JSON format
            import_growth_json = {}
            for entry in import_percentage_changes:
                year = entry["year"]
                month = entry["month"]
                if year not in import_growth_json:
                    import_growth_json[year] = {}
                import_growth_json[year][month] = entry["change"]

            # Reverse the year order to display most recent years first
            import_growth_json = dict(sorted(import_growth_json.items(), key=lambda x: x[0], reverse=True))

            # Save to JSON file
            #with open("import_price_index_percentage_changes.json", "w") as json_file:
                #json.dump(import_growth_json, json_file, indent=4)

            # Print formatted JSON result
            #print("Import Price Index Data Saved.")
            #print(json.dumps(import_growth_json, indent=4))

        else:
            print("Error fetching Import Price Index:", data_import["message"])
    else:
        print("Failed to retrieve Import Price Index data. Status code:", response_import.status_code)



    ######################## Interest Rate  ###########################

    print("Agent Downloading Interest Rate Dataset")

    # Fed Funds Rate Series ID
    FEDFUNDS_series_id = "FEDFUNDS"

    # Request parameters
    params = {
        "series_id": FEDFUNDS_series_id,  # Federal Funds Rate
        "api_key": FRED_API_Key,
        "file_type": "json",
        "frequency": "m",
        "observation_start": f"{current_year - 10}-01-01",
        "observation_end": f"{current_year}-12-31"
    }

    # Fetch data
    response = requests.get(FRED_API_url, params=params)

    # Check response
    if response.status_code == 200:
        data = response.json()

        # Convert to DataFrame
        df = pd.DataFrame(data["observations"])

        # Rename columns for clarity
        df.rename(columns={"date": "Date", "value": "Fed_Funds_Rate"}, inplace=True)

        # Convert to datetime format
        df["Date"] = pd.to_datetime(df["Date"])
        df["Year"] = df["Date"].dt.year
        df["Month"] = df["Date"].dt.month

        # Reformat data to match your JSON structure
        fed_rate_json = {}
        for _, row in df.iterrows():
            year = str(row["Year"])
            month = f"Mo{row['Month']}"
            value = row["Fed_Funds_Rate"]

            if year not in fed_rate_json:
                fed_rate_json[year] = {}
            fed_rate_json[year][month] = value

        # Reverse year order to display most recent years first
        fed_rate_json = dict(sorted(fed_rate_json.items(), key=lambda x: x[0], reverse=True))

        # Save to JSON file
        #with open("fed_funds_rate.json", "w") as json_file:
            #json.dump(fed_rate_json, json_file, indent=4)

        #print("Fed Funds Rate data saved to fed_funds_rate.json")

    else:
        print(f"Error: {response.status_code}, {response.text}")




    ########################### 2 Year Treasury Yield #############################

    print("Agent Downloading 2 Year Treasury Yield Dataset")

    GS2_series_id = "GS2"


    params = {
        "series_id": GS2_series_id,
        "api_key": FRED_API_Key,
        "file_type": "json",
        "frequency": "m",
        "observation_start": f"{current_year - 10}-01-01",
        "observation_end": f"{current_year}-12-31"
    }

    # Fetch data
    response = requests.get(FRED_API_url, params=params)

    # Check response
    if response.status_code == 200:
        data = response.json()

        # Convert to DataFrame
        df = pd.DataFrame(data["observations"])

        # Rename columns for clarity
        df.rename(columns={"date": "Date", "value": "2Y_Treasury_Yield"}, inplace=True)

        # Convert to datetime format
        df["Date"] = pd.to_datetime(df["Date"])
        df["Year"] = df["Date"].dt.year
        df["Month"] = df["Date"].dt.month

        # Reformat data to match your JSON structure
        gs2_json = {}
        for _, row in df.iterrows():
            year = str(row["Year"])
            month = f"Mo{row['Month']}"
            value = row["2Y_Treasury_Yield"]

            if year not in gs2_json:
                gs2_json[year] = {}
            gs2_json[year][month] = value

        # Reverse year order to display most recent years first
        gs2_json = dict(sorted(gs2_json.items(), key=lambda x: x[0], reverse=True))

        # Save to JSON file
        #with open("2y_treasury_yield.json", "w") as json_file:
            #json.dump(gs2_json, json_file, indent=4)

        #print("2-Year Treasury Yield data saved to 2y_treasury_yield.json")

    else:
        print(f"Error: {response.status_code}, {response.text}")


    ########################### 10 Year Treasury Yield #############################

    print("Agent Downloading 10 Year Treasury Yield Dataset")

    GS10_series_id = "GS10"

    # Request parameters
    params = {
        "series_id": GS10_series_id,
        "api_key": FRED_API_Key,
        "file_type": "json",
        "frequency": "m",  # Monthly data
        "observation_start": f"{current_year - 10}-01-01",
        "observation_end": f"{current_year}-12-31"
    }

    # Fetch data
    response = requests.get(FRED_API_url, params=params)

    # Check response
    if response.status_code == 200:
        data = response.json()

        # Convert to DataFrame
        df = pd.DataFrame(data["observations"])

        # Rename columns for clarity
        df.rename(columns={"date": "Date", "value": "10Y_Treasury_Yield"}, inplace=True)

        # Convert to datetime format
        df["Date"] = pd.to_datetime(df["Date"])
        df["Year"] = df["Date"].dt.year
        df["Month"] = df["Date"].dt.month

        # Reformat data to match your JSON structure
        gs10_json = {}
        for _, row in df.iterrows():
            year = str(row["Year"])
            month = f"Mo{row['Month']}"
            value = row["10Y_Treasury_Yield"]

            if year not in gs10_json:
                gs10_json[year] = {}
            gs10_json[year][month] = value

        # Reverse year order to display most recent years first
        gs10_json = dict(sorted(gs10_json.items(), key=lambda x: x[0], reverse=True))

        # Save to JSON file
        #with open("10y_treasury_yield.json", "w") as json_file:
            #json.dump(gs10_json, json_file, indent=4)

        #print("10-Year Treasury Yield data saved to 10y_treasury_yield.json")

    else:
        print(f"Error: {response.status_code}, {response.text}")



    ########################### 30 Year Treasury Yield #############################

    print("Agent Downloading 30 Year Treasury Yield Dataset")

    GS30_series_id = "GS30"

    # Request parameters
    params = {
        "series_id": GS30_series_id,
        "api_key": FRED_API_Key,
        "file_type": "json",
        "frequency": "m",
        "observation_start": f"{current_year - 10}-01-01",
        "observation_end": f"{current_year}-12-31"
    }

    # Fetch data
    response = requests.get(FRED_API_url, params=params)

    # Check response
    if response.status_code == 200:
        data = response.json()

        # Convert to DataFrame
        df = pd.DataFrame(data["observations"])

        # Rename columns for clarity
        df.rename(columns={"date": "Date", "value": "30Y_Treasury_Yield"}, inplace=True)

        # Convert to datetime format
        df["Date"] = pd.to_datetime(df["Date"])
        df["Year"] = df["Date"].dt.year
        df["Month"] = df["Date"].dt.month

        # Reformat data to match your JSON structure
        gs30_json = {}
        for _, row in df.iterrows():
            year = str(row["Year"])
            month = f"Mo{row['Month']}"
            value = row["30Y_Treasury_Yield"]

            if year not in gs30_json:
                gs30_json[year] = {}
            gs30_json[year][month] = value

        # Reverse year order to display most recent years first
        gs30_json = dict(sorted(gs30_json.items(), key=lambda x: x[0], reverse=True))


    else:
        print(f"Error: {response.status_code}, {response.text}")

    ####################### 10Y - 2Y spread (basis points)###############################

    print("Agent Downloading 10Y - 2Y spread (basis points) Dataset")

    spread_json = {}

    for year in gs10_json.keys():  # Iterate through years (sorted from most recent)
        if year in gs2_json:  # Ensure both datasets contain the same year
            spread_json[year] = {}
            for month in gs10_json[year].keys():  # Iterate through months
                if month in gs2_json[year]:  # Ensure both datasets contain the same month
                    gs10_value = float(gs10_json[year][month])  # Convert to float
                    gs2_value = float(gs2_json[year][month])    # Convert to float

                    # Compute the basis point spread (10Y - 2Y) * 100
                    spread_json[year][month] = round((gs10_value - gs2_value) * 100, 2)

    # Save to JSON file
    #with open("10y_2y_basis_spread.json", "w") as json_file:
        #json.dump(spread_json, json_file, indent=4)



    ################################# House Price #####################################
    # Series IDs for Housing Data
    housing_series = {
        "FHFA_House_Price_Index": "USSTHPI",  # FHFA House Price Index
        "Median_Home_Sales_Price": "MSPUS",   # Median Sales Price of Homes
        "New_Home_Sales": "HSN1F"             # New Home Sales
    }

    # Function to fetch and format data
    def fetch_housing_data(series_id):
        params = {
            "series_id": series_id,
            "api_key": FRED_API_Key,
            "file_type": "json",
            "frequency": "q",
            "observation_start": f"{current_year - 10}-01-01",
            "observation_end": f"{current_year}-12-31"
        }

        response = requests.get(FRED_API_url, params=params)

        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame(data["observations"])

            # Rename columns for clarity
            df.rename(columns={"date": "Date", "value": "Value"}, inplace=True)

            # Convert to datetime format
            df["Date"] = pd.to_datetime(df["Date"])
            df["Year"] = df["Date"].dt.year
            df["Quarter"] = df["Date"].dt.quarter

            # Reformat data into JSON structure
            formatted_json = {}
            for _, row in df.iterrows():
                year = str(row["Year"])
                month = f"Q{row['Quarter']}"
                value = row["Value"]

                if year not in formatted_json:
                    formatted_json[year] = {}
                formatted_json[year][month] = value

            # Reverse year order to display most recent years first
            formatted_json = dict(sorted(formatted_json.items(), key=lambda x: x[0], reverse=True))

            return formatted_json

        else:
            print(f"Error fetching {series_id}: {response.status_code}, {response.text}")
            return {}

    # Fetch data for each indicator
    FHFA_House_Price_json = fetch_housing_data(housing_series["FHFA_House_Price_Index"])
    Median_Home_Sales_Price_json = fetch_housing_data(housing_series["Median_Home_Sales_Price"])
    New_Home_Sales_json = fetch_housing_data(housing_series["New_Home_Sales"])

    # Save each dataset as a separate JSON file
    #with open("fhfa_house_price_index.json", "w") as file:
        #json.dump(fhfa_json, file, indent=4)

    #with open("median_home_sales_price.json", "w") as file:
        #json.dump(msp_json, file, indent=4)

    #with open("new_home_sales.json", "w") as file:
        #json.dump(nhs_json, file, indent=4)

    #print("Housing data saved to JSON files.")

    ############################### Hourly Earning #########################

    print("Agent Downloading Hourly Earnings Dataset")


    # BLS Series ID for Average Hourly Earnings (Total Private)
    AHE_series_id = "CES0500000003"

    # Request payload
    payload = {
        "seriesid": [AHE_series_id],
        "startyear": str(current_year - 10),
        "endyear": str(current_year),
        "registrationkey": BLS_API_key
    }

    # Fetch data
    response = requests.post(BLS_url, json=payload)

    # Check response
    if response.status_code == 200:
        data = response.json()

        if data["status"] == "REQUEST_SUCCEEDED":
            earnings_data = data["Results"]["series"][0]["data"]

            # Extract values and dates
            earnings_values = [float(entry["value"]) for entry in reversed(earnings_data)]
            earnings_dates = [(entry["year"], entry["period"]) for entry in reversed(earnings_data)]

            # Reformat data into JSON structure
            ahe_json = {}
            for i in range(len(earnings_values)):
                year = earnings_dates[i][0]
                month = f"Mo{int(earnings_dates[i][1][1:])}"  # Convert "M01" -> "Mo1"
                value = earnings_values[i]

                if year not in ahe_json:
                    ahe_json[year] = {}
                ahe_json[year][month] = value

            # Reverse the year order to display most recent years first
            ahe_json = dict(sorted(ahe_json.items(), key=lambda x: x[0], reverse=True))

            # Save to JSON file
            #with open("average_hourly_earnings.json", "w") as json_file:
                #json.dump(ahe_json, json_file, indent=4)

            #print("Average Hourly Earnings data saved to average_hourly_earnings.json")

        else:
            print("Error fetching AHE data:", data["message"])

    else:
        print("Failed to retrieve AHE data. Status code:", response.status_code)

    ########################### Personal Saving Rate ###################################

    print("Agent Downloading Personal Saving Rate Dataset")



    Personal_Savings_series_id = "PSAVERT"

    # Request parameters
    params = {
        "series_id": Personal_Savings_series_id,  # Personal Savings Rate
        "api_key": FRED_API_Key,
        "file_type": "json",
        "frequency": "m",  # Monthly data
        "observation_start": f"{current_year - 10}-01-01",
        "observation_end": f"{current_year}-12-31"
    }

    # Fetch data
    response = requests.get(FRED_API_url, params=params)

    # Check response
    if response.status_code == 200:
        data = response.json()
        df = pd.DataFrame(data["observations"])

        # Rename columns for clarity
        df.rename(columns={"date": "Date", "value": "Personal_Savings_Rate"}, inplace=True)

        # Convert to datetime format
        df["Date"] = pd.to_datetime(df["Date"])
        df["Year"] = df["Date"].dt.year
        df["Month"] = df["Date"].dt.month

        # Reformat data to match your JSON structure
        savings_json = {}
        for _, row in df.iterrows():
            year = str(row["Year"])
            month = f"Mo{row['Month']}"
            value = row["Personal_Savings_Rate"]

            if year not in savings_json:
                savings_json[year] = {}
            savings_json[year][month] = value

        # Reverse year order to display most recent years first
        savings_json = dict(sorted(savings_json.items(), key=lambda x: x[0], reverse=True))

        # Save to JSON file
        #with open("personal_savings_rate.json", "w") as json_file:
            #json.dump(savings_json, json_file, indent=4)

        #print("Personal Savings Rate data saved to personal_savings_rate.json")

    else:
        print(f"Error: {response.status_code}, {response.text}")




    #################################### Gold Price ######################################

    print("Agent Downloading Gold Price Dataset")



    gold = yf.Ticker("GC=F")
    gold_data = gold.history(period="3y")

    # Resample data to get monthly closing prices
    gold_monthly = gold_data["Close"].resample("ME").last()

    # Convert to JSON structure
    gold_json = {}
    for date, price in gold_monthly.items():
        year = str(date.year)
        month = f"Mo{date.month}"

        if year not in gold_json:
            gold_json[year] = {}
        gold_json[year][month] = f"{round(price, 2)} USD"

    # Reverse order to show most recent years first
    gold_json = dict(sorted(gold_json.items(), key=lambda x: x[0], reverse=True))

    data_sources = {
    "Real GDP Growth (Quarter)": expand_quarterly_to_monthly(gdp_quarterly_growth),
    "PCE (Quarter)": expand_quarterly_to_monthly(pce_quarterly),
    "CPI (Month)": process_monthly_data(cpi_json),
    "Unemployment Rate (Month)": process_monthly_data(unemployment_json),
    "PPI (Month)": process_monthly_data(ppi_growth_json),
    "Export Price Index Growth (Month)": process_monthly_data(export_growth_json),
    "Import Price Index Growth (Month)": process_monthly_data(import_growth_json),
    "Fed Funds Rate (Month)": process_monthly_data(fed_rate_json),
    "2Y Treasury Yield (Month)": process_monthly_data(gs2_json),
    "10Y Treasury Yield (Month)": process_monthly_data(gs10_json),
    "30Y Treasury Yield (Month)": process_monthly_data(gs30_json),
    "10Y-2Y Spread (Month)": process_monthly_data(spread_json),
    "FHFA House Price Index (Quarter)": expand_quarterly_to_monthly(FHFA_House_Price_json),
    "Median Home Sales Price (Quarter)": expand_quarterly_to_monthly(Median_Home_Sales_Price_json),
    "New Home Sales (Quarter)": expand_quarterly_to_monthly(New_Home_Sales_json),
    "Average Hourly Earnings (Month)": process_monthly_data(ahe_json),
    "Personal Savings Rate (Month)": process_monthly_data(savings_json),
    "Gold Price (Month)": process_monthly_data(gold_json)}

    df = pd.DataFrame.from_dict(data_sources, orient='index').transpose()
    df['Gold Price (Month)'] = df['Gold Price (Month)'].str.replace('USD', '', regex=True).str.strip()
    df['Gold Price (Month)'] = pd.to_numeric(df['Gold Price (Month)'], errors='coerce')


    # Fill missing values with blanks

    df = df.apply(pd.to_numeric, errors='coerce')

    # Ensure the DataFrame index is in proper chronological order
    df.index = pd.to_datetime(df.index, format='%Y-%m')
    df = df.sort_index()

    # Convert index back to YYYY-MM format for display
    df.index = df.index.strftime('%Y-%m')


    ###  Final Output #######
    if download:
      csv_filename = "economic_data.csv"
      df.to_csv(csv_filename, index=True)
      return df


    return df