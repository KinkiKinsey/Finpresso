#!/bin/bash

echo "Installing LangChain and required dependencies..."

# Install core LangChain packages
pip install langchain>=0.0.267 \
          langchain-openai>=0.0.1 \
          langchain-community>=0.0.1 \
          langchain-core>=0.1.0 \
          openai>=1.0.0 \
          pydantic>=2.0.0 \
          tiktoken>=0.3.0 \
          pandas>=1.3.0 \
          yfinance>=0.2.0

echo "LangChain installation completed!"
echo "You may need to restart your Python environment for changes to take effect." 