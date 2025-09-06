#!/usr/bin/env python3
"""
Integration test for the crawl API endpoint.
This is a standalone test script that can be run against a running server.
"""

import requests
import json

def test_crawl_endpoint():
    """Test the crawl API endpoint with a simple website."""
    
    # API endpoint URL (adjust if your server runs on different host/port)
    url = "http://localhost:8000/api/v1/crawl"
    
    # Test payload
    payload = {
        "url": "https://spectrumsense.netlify.app/",
        "max_pages": 5
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        print("Testing crawl API endpoint...")
        print(f"URL: {url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(url, json=payload, headers=headers)
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Response Body: {json.dumps(result, indent=2)}")
            print("\n✅ API endpoint test successful!")
        else:
            print(f"❌ API endpoint test failed with status {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the server. Make sure Django is running on localhost:8000")
    except Exception as e:
        print(f"❌ Error testing API: {e}")

if __name__ == "__main__":
    test_crawl_endpoint()
