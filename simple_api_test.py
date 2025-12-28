#!/usr/bin/env python3
"""
Simple API Test Script for Sakura Reviews
Tests core endpoints without Unicode issues
"""

import requests
import json
import time
from datetime import datetime

# Configuration
API_BASE = "http://localhost:5000"
TEST_SESSION_ID = f"test_session_{int(time.time())}"

def test_api():
    print("=" * 50)
    print("SAKURA REVIEWS - API TEST")
    print("=" * 50)
    print(f"Testing API at: {API_BASE}")
    print(f"Session ID: {TEST_SESSION_ID}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test 1: Health Check
    print("\n1. HEALTH CHECK")
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"   SUCCESS - Version: {data.get('version')}, Status: {data.get('status')}")
        else:
            print(f"   FAILED - Status: {response.status_code}")
    except Exception as e:
        print(f"   ERROR - {e}")
    
    # Test 2: API Info
    print("\n2. API INFORMATION")
    try:
        response = requests.get(f"{API_BASE}/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"   SUCCESS - API Version: {data.get('version')}")
            print(f"   Platforms: {', '.join(data.get('platforms', []))}")
        else:
            print(f"   FAILED - Status: {response.status_code}")
    except Exception as e:
        print(f"   ERROR - {e}")
    
    # Test 3: Shopify Product Search
    print("\n3. SHOPIFY PRODUCT SEARCH")
    try:
        response = requests.get(
            f"{API_BASE}/shopify/products/search",
            params={'q': 'test'},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                products = data.get('products', [])
                print(f"   SUCCESS - Found {len(products)} products")
            else:
                print(f"   API ERROR - {data.get('error')}")
        else:
            print(f"   FAILED - Status: {response.status_code}")
            
    except Exception as e:
        print(f"   ERROR - {e}")
    
    # Test 4: Skip Review
    print("\n4. SKIP REVIEW")
    try:
        skip_payload = {
            "review_id": f"test_review_{int(time.time())}",
            "session_id": TEST_SESSION_ID
        }
        
        response = requests.post(
            f"{API_BASE}/admin/reviews/skip",
            json=skip_payload,
            headers={'Content-Type': 'application/json'},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"   SUCCESS - {data.get('message')}")
            else:
                print(f"   API ERROR - {data.get('error')}")
        else:
            print(f"   FAILED - Status: {response.status_code}")
            
    except Exception as e:
        print(f"   ERROR - {e}")
    
    # Test 5: Import Single Review
    print("\n5. IMPORT SINGLE REVIEW")
    try:
        import_payload = {
            "review": {
                "id": f"test_review_import_{int(time.time())}",
                "rating": 5,
                "text": "Great product! Test review.",
                "reviewer_name": "Test User",
                "date": datetime.now().strftime('%Y-%m-%d'),
                "quality_score": 8.5,
                "ai_recommended": True,
                "platform": "aliexpress"
            },
            "shopify_product_id": "123456789",
            "session_id": TEST_SESSION_ID
        }
        
        response = requests.post(
            f"{API_BASE}/admin/reviews/import/single",
            json=import_payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"   SUCCESS - {data.get('message')}")
            else:
                print(f"   API ERROR - {data.get('error')}")
        else:
            print(f"   FAILED - Status: {response.status_code}")
            
    except Exception as e:
        print(f"   ERROR - {e}")
    
    # Test 6: Bookmarklet
    print("\n6. BOOKMARKLET JAVASCRIPT")
    try:
        response = requests.get(f"{API_BASE}/js/bookmarklet.js", timeout=5)
        
        if response.status_code == 200:
            js_content = response.text
            
            # Check for key features
            has_search = "setupProductSearch" in js_content
            has_import = "importReview" in js_content
            has_skip = "skipReview" in js_content
            has_bulk = "importAllReviews" in js_content
            
            print(f"   SUCCESS - JavaScript loaded ({len(js_content):,} chars)")
            print(f"   Features: Search={has_search}, Import={has_import}, Skip={has_skip}, Bulk={has_bulk}")
            
        else:
            print(f"   FAILED - Status: {response.status_code}")
            
    except Exception as e:
        print(f"   ERROR - {e}")
    
    # Test 7: Review Scraping
    print("\n7. REVIEW SCRAPING (AliExpress)")
    try:
        params = {
            'productId': '1005004632823451',
            'platform': 'aliexpress',
            'page': 1,
            'per_page': 3,
            'id': TEST_SESSION_ID
        }
        
        response = requests.get(
            f"{API_BASE}/admin/reviews/import/url",
            params=params,
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                reviews = data.get('reviews', [])
                ai_count = sum(1 for r in reviews if r.get('ai_recommended'))
                print(f"   SUCCESS - Scraped {len(reviews)} reviews")
                print(f"   AI Recommended: {ai_count}/{len(reviews)}")
            else:
                print(f"   API ERROR - {data.get('error')}")
        else:
            print(f"   FAILED - Status: {response.status_code}")
            
    except Exception as e:
        print(f"   ERROR - {e}")
    
    print("\n" + "=" * 50)
    print("TEST COMPLETE")
    print("=" * 50)
    print("\nBookmarklet URL:")
    print(f"javascript:(function(){{var s=document.createElement('script');")
    print(f"s.src='{API_BASE}/js/bookmarklet.js';document.head.appendChild(s);}})();")
    print("\nNext: Test on AliExpress product page!")

if __name__ == "__main__":
    test_api()










