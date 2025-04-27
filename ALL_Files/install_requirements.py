#!/usr/bin/env python3
import subprocess
import sys

def install_langchain():
    """Install LangChain and required dependencies"""
    print("Installing LangChain and required dependencies...")
    
    # List of packages to install
    packages = [
        "langchain>=0.0.267",  # Core LangChain package
        "langchain-openai>=0.0.1",  # OpenAI integration
        "langchain-community>=0.0.1",  # Community integrations
        "langchain-core>=0.1.0",  # Core components
        "openai>=1.0.0",  # OpenAI API
        "pydantic>=2.0.0",  # Used by LangChain
        "tiktoken>=0.3.0",  # For token counting
        "pandas>=1.3.0",  # For data manipulation
        "yfinance>=0.2.0",  # For Yahoo Finance data
    ]
    
    # Install each package
    for package in packages:
        print(f"Installing {package}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"Successfully installed {package}")
        except subprocess.CalledProcessError as e:
            print(f"Error installing {package}: {e}")
    
    print("\nLangChain installation completed!")
    print("You may need to restart your Python environment for changes to take effect.")

if __name__ == "__main__":
    install_langchain() 