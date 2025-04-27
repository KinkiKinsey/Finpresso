#!/usr/bin/env python
# coding: utf-8

import sys
import traceback
import os
import json
from datetime import datetime
from micro_tool import MicroTools, create_financial_analysis_agent

# Try to import the MicroAnalystAgent
try:
    # Add the parent directory to the path
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from Micro_Analyst_Agent import MicroAnalystAgent
    ANALYST_AGENT_AVAILABLE = True
except ImportError:
    print("Warning: MicroAnalystAgent is not available. Enhanced tests will be skipped.")
    ANALYST_AGENT_AVAILABLE = False

def test_tool(tool_name, tool_func, *args, **kwargs):
    """Test a specific tool function and report its success or failure"""
    print(f"\n{'='*80}")
    print(f"Testing tool: {tool_name} for ticker {args[0] if args else ''}")
    print(f"{'='*80}")
    
    try:
        result = tool_func(*args, **kwargs)
        if result is None:
            print(f"✓ {tool_name} executed without errors (returned None)")
        elif isinstance(result, dict) and result.get('status') == 'error':
            print(f"✗ {tool_name} returned error: {result.get('message', 'Unknown error')}")
        else:
            print(f"✓ {tool_name} executed successfully")
            # Print a small sample of the result if it's not too large
            if isinstance(result, dict):
                print(f"Result type: dict")
                print(f"Result keys: {list(result.keys())}")
                if len(str(result)) > 1000:
                    print(f"Result: {str(result)[:500]}...[truncated]...")
                else:
                    print(f"Result: {result}")
            elif hasattr(result, 'shape'):  # DataFrame
                print(f"Result is a DataFrame with {result.shape[0]} rows and {result.shape[1]} columns")
                print("\nSample data (first 3 rows):")
                if not result.empty and result.shape[0] > 0:
                    print(f"{result.head(3)}")
            elif isinstance(result, list):
                print(f"Result type: list")
                print(f"Result: {result[:5]}" + ("..." if len(result) > 5 else ""))
            else:
                print(f"Result type: {type(result).__name__}")
                print(f"Result: {result}")
        print("\n" + "="*80)
        return result, True
    except Exception as e:
        print(f"✗ {tool_name} failed with error: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        print("\n" + "="*80)
        return None, False

def run_all_tests(ticker="AAPL"):
    """Run tests for all the micro tools"""
    print(f"Testing all tools for ticker: {ticker}")
    
    # Keep track of successes and failures
    results = {
        "success": [],
        "failure": [],
        "data": {}
    }
    
    # 1. Test get_key_metrics
    tool_name = "get_key_metrics"
    result, success = test_tool(tool_name, MicroTools.get_key_metrics, ticker)
    results["success" if success else "failure"].append(tool_name)
    if success:
        results["data"][tool_name] = result
    
    # 2. Test get_beta
    tool_name = "get_beta"
    result, success = test_tool(tool_name, MicroTools.get_beta, ticker)
    results["success" if success else "failure"].append(tool_name)
    if success:
        results["data"][tool_name] = result
    
    # 3. Test get_dcf_valuation
    tool_name = "get_dcf_valuation"
    result, success = test_tool(tool_name, MicroTools.get_dcf_valuation, ticker)
    results["success" if success else "failure"].append(tool_name)
    if success:
        results["data"][tool_name] = result
    
    # 4. Test get_detailed_dcf
    tool_name = "get_detailed_dcf"
    result, success = test_tool(tool_name, MicroTools.get_detailed_dcf, ticker)
    results["success" if success else "failure"].append(tool_name)
    if success:
        results["data"][tool_name] = result
    
    # 5. Test get_company_profile
    tool_name = "get_company_profile"
    result, success = test_tool(tool_name, MicroTools.get_company_profile, ticker)
    results["success" if success else "failure"].append(tool_name)
    if success:
        results["data"][tool_name] = result
    
    # 6. Test get_peers
    tool_name = "get_peers"
    result, success = test_tool(tool_name, MicroTools.get_peers, ticker)
    results["success" if success else "failure"].append(tool_name)
    if success:
        results["data"][tool_name] = result
    
    # 7. Test get_peer_valuation_comparison
    tool_name = "get_peer_valuation_comparison"
    result, success = test_tool(tool_name, MicroTools.get_peer_valuation_comparison, ticker)
    results["success" if success else "failure"].append(tool_name)
    if success:
        results["data"][tool_name] = result
    
    # 8. Test get_peer_beta_comparison
    tool_name = "get_peer_beta_comparison"
    result, success = test_tool(tool_name, MicroTools.get_peer_beta_comparison, ticker)
    results["success" if success else "failure"].append(tool_name)
    if success:
        results["data"][tool_name] = result
    
    # 9. Test get_earnings_surprises
    tool_name = "get_earnings_surprises"
    result, success = test_tool(tool_name, MicroTools.get_earnings_surprises, ticker)
    results["success" if success else "failure"].append(tool_name)
    if success:
        results["data"][tool_name] = result
    
    # 10. Test analyze_earnings_vs_estimates
    tool_name = "analyze_earnings_vs_estimates"
    result, success = test_tool(tool_name, MicroTools.analyze_earnings_estimates_vs_actual, ticker)
    results["success" if success else "failure"].append(tool_name)
    if success:
        results["data"][tool_name] = result
    
    # Print summary of test results
    print("\n\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    print(f"Total tools tested: {len(results['success']) + len(results['failure'])}")
    print(f"Successful: {len(results['success'])} ({', '.join(results['success'])})")
    print(f"Failed: {len(results['failure'])} ({', '.join(results['failure'])})")
    
    # Save the test results to a JSON file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Tool_Tests")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Save JSON output
    json_path = os.path.join(output_dir, f"tool_test_{ticker}_{timestamp}.json")
    with open(json_path, "w") as f:
        json.dump({
            "ticker": ticker,
            "timestamp": timestamp,
            "successful_tests": results["success"],
            "failed_tests": results["failure"],
            "results": {k: str(v) for k, v in results["data"].items()}
        }, f, indent=2)
    
    # Save text output for easier reading
    text_path = os.path.join(output_dir, f"tool_test_{ticker}_{timestamp}.txt")
    with open(text_path, "w") as f:
        f.write(f"Testing all tools for ticker: {ticker}\n")
        f.write(f"Date/Time: {timestamp}\n\n")
        
        for tool_name in results["success"]:
            f.write(f"{tool_name}: SUCCESS\n")
            if tool_name in results["data"]:
                f.write(f"  Result: {str(results['data'][tool_name])[:200]}...\n\n")
                
        for tool_name in results["failure"]:
            f.write(f"{tool_name}: FAILED\n\n")
    
    print(f"\nResults saved to:")
    print(f"  - JSON: {json_path}")
    print(f"  - Text: {text_path}")
    
    # Return True if all tests passed
    return len(results["failure"]) == 0, results["data"]

def test_enhanced_features(ticker="MSFT", debug=True):
    """
    Test the enhanced cache and LLM features in MicroAnalystAgent
    
    Args:
        ticker (str): Stock ticker to analyze
        debug (bool): Whether to print debug information
    """
    if not ANALYST_AGENT_AVAILABLE:
        print("\n" + "="*50)
        print("ENHANCED FEATURES TEST SKIPPED: MicroAnalystAgent not available")
        print("="*50)
        return False
    
    print("\n" + "*" * 50)
    print(f"* TESTING ENHANCED CACHE AND LLM FEATURES FOR {ticker}")
    print(f"* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("*" * 50 + "\n")
    
    # Create a test rating JSON file
    rating_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Rating_Json")
    if not os.path.exists(rating_dir):
        os.makedirs(rating_dir)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    rating_path = os.path.join(rating_dir, f"test_rating_{timestamp}.json")
    
    # Create a simple rating JSON with the ticker
    rating_data = {
        "Ticker": ticker,
        "Macro": {
            "summary": "The economy is showing signs of growth with moderate inflation.",
            "key_indicators": {
                "GDP_growth_description": "Real GDP growth at 3% annually",
                "Interest_rate_description": "Fed Funds Rate at 4.5%"
            }
        },
        "Micro": {
            "Three_Key_Takeaway_News": "1. Strong earnings growth expected\n2. New product launch announced\n3. Expanding into new markets"
        }
    }
    
    # Save the rating JSON
    with open(rating_path, "w") as f:
        json.dump(rating_data, f, indent=2)
    
    print(f"Created test rating JSON at {rating_path}")
    
    try:
        # Initialize the agent
        print("\nInitializing MicroAnalystAgent...")
        agent = MicroAnalystAgent(use_langchain=False)
        
        # Test selected tools
        test_tools = ["get_stock_metrics", "get_stock_beta", "get_company_profile"]
        print(f"\nTesting selected tools: {', '.join(test_tools)}")
        
        # Manually construct a tool selection
        tool_selection = {
            "selected_tools": test_tools,
            "facts_to_verify": ["Fact 1", "Fact 2"],
            "expectations_to_test": ["Expectation 1", "Expectation 2"],
            "rationale": {tool: f"Testing {tool}" for tool in test_tools}
        }
        
        # Execute tools individually to test caching
        print("\nExecuting tools and testing cache functionality...")
        
        tool_results = {}
        for tool in test_tools:
            print(f"\nExecuting {tool}...")
            # Execute the tool
            single_result = agent.execute_micro_tools(ticker, [tool], verbose=debug)
            tool_results.update(single_result)
        
        # Check if tool results were cached
        print("\nChecking for cached tool results...")
        cache_dir = agent.cache_dir
        cache_files = [f for f in os.listdir(cache_dir) if f.startswith(f"cache_{ticker}_")]
        
        if cache_files:
            latest_cache = sorted(cache_files)[-1]
            cache_path = os.path.join(cache_dir, latest_cache)
            print(f"Found cache file: {cache_path}")
            
            # Load the cache file
            with open(cache_path, "r") as f:
                cache_data = json.load(f)
            
            # Print the tools cached
            print(f"Cached tools: {', '.join(cache_data.keys())}")
            success = True
        else:
            print("❌ No cache files found!")
            success = False
        
        # Test LLM processing
        print("\nTesting LLM processing of tool results...")
        llm_results = agent.process_tool_results_with_llm(ticker, tool_results, verbose=debug)
        
        if llm_results:
            print("\nLLM-processed results:")
            for tool_name, result_data in llm_results.items():
                print(f"\n  Tool: {tool_name}")
                if "name" in result_data:
                    print(f"  Name: {result_data['name']}")
                if "result" in result_data:
                    print(f"  Analysis: {result_data['result'][:200]}...")
            
            print("\nUpdating the rating JSON with LLM-processed results...")
            # Generate a simple analysis result
            analysis_results = {
                "reasoning": "Test reasoning for enhanced features",
                "tools_used": test_tools
            }
            
            # Update the rating JSON
            agent.update_rating_json(rating_path, analysis_results, tool_selection, tool_results, verbose=debug)
            
            # Verify the updated rating JSON
            with open(rating_path, "r") as f:
                updated_rating = json.load(f)
            
            if "Micro" in updated_rating and "tool_results" in updated_rating["Micro"]:
                print("\nVerified: Rating JSON updated with LLM-processed results")
                print("\nExample of LLM-processed content in Rating JSON:")
                sample_tool = test_tools[0]
                if sample_tool in updated_rating["Micro"]["tool_results"]:
                    sample_result = updated_rating["Micro"]["tool_results"][sample_tool]
                    print(f"  Tool: {sample_tool}")
                    print(f"  Result: {sample_result.get('result', 'N/A')[:200]}...")
                success = True
            else:
                print("❌ Failed to update Rating JSON with LLM-processed results")
                success = False
        else:
            print("❌ LLM processing failed")
            success = False
        
        print("\n" + "="*50)
        if success:
            print("✅ ENHANCED FEATURES TEST PASSED!")
        else:
            print("❌ ENHANCED FEATURES TEST FAILED!")
        print("="*50)
        
        return success
    
    except Exception as e:
        print(f"\n❌ Error testing enhanced features: {e}")
        traceback.print_exc()
        print("\n" + "="*50)
        print("❌ ENHANCED FEATURES TEST FAILED!")
        print("="*50)
        return False

def test_langchain_agent():
    """Test the LangChain agent integration with DeepSeek"""
    try:
        print("\n\n" + "="*50)
        print("TESTING LANGCHAIN AGENT WITH DEEPSEEK")
        print("="*50)
        
        # Create the financial analysis agent
        print("Creating financial analysis agent with DeepSeek...")
        agent = create_financial_analysis_agent(use_deepseek=True, verbose=True)
        
        # Test query
        test_query = "What is Apple's beta compared to its peers, and what does this tell us about its risk profile?"
        print(f"\nTesting with query: {test_query}")
        
        # Run the agent
        result = agent.run(test_query)
        
        print("\nAgent Response:")
        print(result)
        return True
    except ImportError as e:
        print(f"LangChain integration test skipped: {e}")
        return None
    except Exception as e:
        print(f"LangChain integration test failed: {e}")
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("Starting MicroTools validation test...")
    
    # Parse command line arguments
    ticker = "MSFT"  # Default ticker
    debug = True    # Default debug mode
    
    if len(sys.argv) > 1:
        ticker = sys.argv[1]
        
    if len(sys.argv) > 2 and sys.argv[2].lower() in ['false', '0', 'no', 'n', 'off']:
        debug = False
    
    print(f"Testing all tools for ticker: {ticker}")
    print(f"Debug mode: {'ON' if debug else 'OFF'}")
    
    # Run the standard tools test
    all_passed, tool_data = run_all_tests(ticker)
    
    # Run the enhanced features test
    if all_passed and ANALYST_AGENT_AVAILABLE:
        enhanced_passed = test_enhanced_features(ticker, debug)
        all_passed = all_passed and enhanced_passed
    
    # Test LangChain integration if requested
    test_langchain_input = input("\nDo you want to test the LangChain agent with DeepSeek? (y/n): ").strip().lower()
    if test_langchain_input == 'y':
        langchain_result = test_langchain_agent()
        if langchain_result is False:
            all_passed = False
    
    print("\nTest completed!")
    
    if all_passed:
        print("\nALL TESTS PASSED! The MicroTools are working correctly.")
        sys.exit(0)
    else:
        print("\nSome tests failed. Please check the errors above.")
        sys.exit(1)

# Get all financial analysis tools
financial_tools = MicroTools.get_langchain_tools()

# Create your LangChain agent
from langchain.agents import initialize_agent, AgentType
from langchain.llms import OpenAI  # or any other LLM you prefer

llm = OpenAI(temperature=0)
agent = initialize_agent(
    financial_tools,
    llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# Now your agent can use all the financial tools
response = agent.run("What are the key metrics and peers for Apple?") 