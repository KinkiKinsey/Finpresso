#!/usr/bin/env python3
"""
Quick LangChain Fix Script
--------------------------
This script installs the exact versions of LangChain packages needed for this project.
It's intended to be run directly when you encounter LangChain related errors.
"""

import subprocess
import sys
import os

def fix_langchain():
    print("🛠 LangChain Quick Fix Script")
    print("-----------------------------")
    print("This will uninstall existing LangChain packages and install the compatible versions.")
    
    # Packages to uninstall first
    to_uninstall = [
        "langchain",
        "langchain-core", 
        "langchain-community", 
        "langchain-openai"
    ]
    
    # Packages to install with exact versions
    to_install = [
        "langchain==0.0.235",  # Older version that's known to work
        "pydantic==1.10.8",    # Compatible with this langchain version
        "openai>=1.0.0"
    ]
    
    # Step 1: Uninstall existing packages
    print("\n1. Removing existing packages...")
    for package in to_uninstall:
        try:
            print(f"   Uninstalling {package}...")
            subprocess.run(
                [sys.executable, "-m", "pip", "uninstall", "-y", package],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
        except Exception as e:
            print(f"   Error uninstalling {package}: {e}")
    
    # Step 2: Install specific versions
    print("\n2. Installing compatible versions...")
    for package in to_install:
        try:
            print(f"   Installing {package}...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if result.returncode != 0:
                print(f"   Error installing {package}: {result.stderr}")
            else:
                print(f"   ✓ {package} installed")
        except Exception as e:
            print(f"   Error installing {package}: {e}")
    
    print("\n✅ LangChain fix completed")
    print("Now you can run your Micro_Analyst_Agent.py script")

if __name__ == "__main__":
    fix_langchain() 