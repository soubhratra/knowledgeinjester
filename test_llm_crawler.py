#!/usr/bin/env python3
"""
Test script for the new LLM-based crawler.
"""
import asyncio
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from apps.crawler.services import crawl_website, CrawlerType

async def test_llm_crawler():
    """Test the LLM crawler functionality."""
    
    # Check if OpenAI API key is available
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ OPENAI_API_KEY environment variable is required")
        print("Please set your OpenAI API key:")
        print("export OPENAI_API_KEY='your-api-key-here'")
        return
    
    # Test URL - you can change this to any website
    test_url = "https://demo.spectrumsense.co"
    max_pages = 5
    max_depth = 5
    
    print(f"🚀 Testing LLM Crawler")
    print(f"URL: {test_url}")
    print(f"Max Pages: {max_pages}")
    print(f"Max Depth: {max_depth}")
    print("-" * 50)
    
    try:
        # Test LLM crawler
        print("🤖 Testing LLM-based crawler...")
        llm_pages = await crawl_website(
            root_url=test_url,
            max_pages=max_pages,
            crawler_type=CrawlerType.LLM,
            max_depth=max_depth
        )
        
        print(f"\n✅ LLM Crawler Results:")
        print(f"Pages crawled: {len(llm_pages)}")
        
        for i, page in enumerate(llm_pages, 1):
            print(f"\n--- Page {i} ---")
            print(f"Title: {page.title}")
            print(f"URL: {page.url}")
            print(f"Word Count: {page.metadata.get('word_count', 0)}")
            
            # Show LLM extracted content
            llm_content = page.metadata.get('llm_extracted_content', '')
            if llm_content:
                print(f"LLM Extracted Content:")
                print(llm_content[:300] + "..." if len(llm_content) > 300 else llm_content)
            else:
                print("No LLM extracted content")
        
        # Test comprehensive crawler for comparison
        print(f"\n🔍 Testing Comprehensive crawler for comparison...")
        comp_pages = await crawl_website(
            root_url=test_url,
            max_pages=max_pages,
            crawler_type=CrawlerType.COMPREHENSIVE
        )
        
        print(f"\n✅ Comprehensive Crawler Results:")
        print(f"Pages crawled: {len(comp_pages)}")
        
        for i, page in enumerate(comp_pages, 1):
            print(f"\n--- Page {i} ---")
            print(f"Title: {page.title}")
            print(f"URL: {page.url}")
            print(f"Word Count: {page.metadata.get('word_count', 0)}")
            
            # Show extraction stats
            stats = page.metadata.get('extraction_stats', {})
            print(f"Extraction Stats: {stats}")
        
        print(f"\n📊 Comparison Summary:")
        print(f"LLM Crawler: {len(llm_pages)} pages")
        print(f"Comprehensive Crawler: {len(comp_pages)} pages")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_llm_crawler())
