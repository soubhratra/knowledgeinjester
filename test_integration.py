#!/usr/bin/env python3
"""
Integration test for the new LLM crawler with the existing pipeline.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from apps.crawler.services import crawl_website_sync, CrawlerType


def test_integration():
    """Test the integration with the existing pipeline."""
    
    # Check if OpenAI API key is set
    if not os.getenv('OPENAI_API_KEY'):
        print("ERROR: OPENAI_API_KEY environment variable is required")
        print("Please set your OpenAI API key:")
        print("export OPENAI_API_KEY='your-api-key-here'")
        return
    
    print("=== Testing LLM Crawler Integration ===\n")
    
    # Test URL
    test_url = "https://example.com"
    max_pages = 3
    max_depth = 1
    tenant_id = "test_tenant"
    
    print(f"Testing URL: {test_url}")
    print(f"Max pages: {max_pages}, Max depth: {max_depth}")
    print(f"Tenant ID: {tenant_id}")
    
    try:
        # Test LLM crawler
        print("\n--- Testing LLM Crawler ---")
        pages = crawl_website_sync(
            root_url=test_url,
            max_pages=max_pages,
            tenant_id=tenant_id,
            crawler_type=CrawlerType.LLM,
            max_depth=max_depth
        )
        
        print(f"✓ LLM Crawler completed successfully")
        print(f"  - Pages crawled: {len(pages)}")
        
        for i, page in enumerate(pages, 1):
            print(f"  - Page {i}: {page.title}")
            print(f"    URL: {page.url}")
            print(f"    Word count: {page.metadata.get('word_count', 0)}")
            print(f"    Depth: {page.metadata.get('depth', 0)}")
            print(f"    Score: {page.metadata.get('score', 0):.2f}")
            
            # Check if LLM extracted content exists
            llm_content = page.metadata.get('llm_extracted_content', '')
            if llm_content:
                print(f"    LLM extracted content: {len(llm_content)} characters")
            else:
                print(f"    LLM extracted content: None")
        
        # Test comprehensive crawler for comparison
        print("\n--- Testing Comprehensive Crawler (for comparison) ---")
        comp_pages = crawl_website_sync(
            root_url=test_url,
            max_pages=max_pages,
            tenant_id=tenant_id,
            crawler_type=CrawlerType.COMPREHENSIVE,
            max_depth=max_depth
        )
        
        print(f"✓ Comprehensive Crawler completed successfully")
        print(f"  - Pages crawled: {len(comp_pages)}")
        
        # Compare results
        print(f"\n--- Comparison ---")
        print(f"LLM Crawler: {len(pages)} pages")
        print(f"Comprehensive Crawler: {len(comp_pages)} pages")
        
        if pages:
            avg_word_count_llm = sum(p.metadata.get('word_count', 0) for p in pages) / len(pages)
            print(f"Average word count (LLM): {avg_word_count_llm:.1f}")
        
        if comp_pages:
            avg_word_count_comp = sum(p.metadata.get('word_count', 0) for p in comp_pages) / len(comp_pages)
            print(f"Average word count (Comprehensive): {avg_word_count_comp:.1f}")
        
        print("\n✓ Integration test completed successfully!")
        
    except Exception as e:
        print(f"✗ Integration test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_integration()
