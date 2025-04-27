#!/usr/bin/env python3
import subprocess
import sys
import os
import importlib.util
import platform

def get_environment_info():
    """Get information about the current Python environment"""
    env_info = {
        "python_executable": sys.executable,
        "python_version": sys.version,
        "platform": platform.platform(),
        "environment": "Unknown"
    }
    
    # Detect environment type
    if os.environ.get("CONDA_DEFAULT_ENV"):
        env_info["environment"] = f"Conda ({os.environ.get('CONDA_DEFAULT_ENV')})"
    elif os.environ.get("VIRTUAL_ENV"):
        env_info["environment"] = f"Virtual Environment ({os.environ.get('VIRTUAL_ENV')})"
    else:
        env_info["environment"] = "System Python"
    
    return env_info

def install_packages():
    """Install required packages"""
    required_packages = [
        "langchain>=0.0.270",
        "langchain-openai>=0.0.1",
        "langchain-community>=0.0.1",
        "langchain-core>=0.1.0",
        "pydantic>=2.0.0",
        "yfinance>=0.2.0",
        "openai>=1.0.0",
        "tiktoken>=0.3.0",
        "pandas>=1.3.0"
    ]
    
    print("Installing required packages...")
    env_info = get_environment_info()
    print(f"Using Python: {env_info['python_executable']}")
    print(f"Environment: {env_info['environment']}")
    print(f"Python version: {env_info['python_version'].split()[0]}")
    print(f"Platform: {env_info['platform']}")
    
    # First uninstall any existing packages to avoid conflicts
    print("\nRemoving any existing packages to avoid conflicts...")
    for package in [pkg.split(">=")[0] for pkg in required_packages]:
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "uninstall", "-y", package],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        except:
            pass
    
    # Install all packages
    print("\nInstalling packages:")
    for package in required_packages:
        package_name = package.split(">=")[0]
        print(f"Installing {package}...", end=" ")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if result.returncode == 0:
                print("✓ SUCCESS")
            else:
                print("✗ FAILED")
                print(f"Error: {result.stderr}")
        except Exception as e:
            print("✗ FAILED")
            print(f"Error: {str(e)}")
    
    # Verify installations
    print("\nVerifying installations:")
    all_success = True
    for package in [pkg.split(">=")[0] for pkg in required_packages]:
        if package == "langchain-openai":
            package_import = "langchain_openai"
        elif package == "langchain-community":
            package_import = "langchain_community"
        elif package == "langchain-core":
            package_import = "langchain_core"
        else:
            package_import = package
            
        spec = importlib.util.find_spec(package_import)
        if spec is not None:
            print(f"{package}: ✓ Installed successfully")
        else:
            print(f"{package}: ✗ Not found")
            all_success = False
    
    if all_success:
        print("\n✅ All packages installed successfully!")
        print("\nYou can now run your LangChain applications.")
    else:
        print("\n⚠️ Some packages could not be verified.")
        print("You may need to install them manually or check your Python environment.")

if __name__ == "__main__":
    install_packages() 