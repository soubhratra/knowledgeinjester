#!/usr/bin/env python3
"""
Test script for the new LLM crawler implementation.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from apps.crawler.llm_crawler import test_llm_crawler


async def main():
    """Test the new LLM crawler implementation."""
    
    # Check if OpenAI API key is set
    if not os.getenv('OPENAI_API_KEY'):
        print("ERROR: OPENAI_API_KEY environment variable is required")
        print("Please set your OpenAI API key:")
        print("export OPENAI_API_KEY='your-api-key-here'")
        return
    
    # Test URLs
    test_urls = [
        "https://example.com",
        "https://httpbin.org",
        "https://jsonplaceholder.typicode.com"
    ]
    
    print("=== Testing New LLM Crawler Implementation ===\n")
    
    for url in test_urls:
        print(f"\n{'='*60}")
        print(f"Testing URL: {url}")
        print(f"{'='*60}")
        
        try:
            # Test with BFS strategy
            print("\n--- Testing BFS Strategy ---")
            await test_llm_crawler(url, max_pages=3, max_depth=1, strategy="bfs")
            
            # Test with BestFirst strategy
            print("\n--- Testing BestFirst Strategy ---")
            await test_llm_crawler(url, max_pages=3, max_depth=1, strategy="best_first")
            
        except Exception as e:
            print(f"Error testing {url}: {e}")
        
        print(f"\n{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
