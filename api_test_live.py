#!/usr/bin/env python3
"""
Live API Test Script for Sakura Reviews
Tests all endpoints with your actual Shopify configuration
"""

import requests
import json
import time
from datetime import datetime

# Configuration
API_BASE = "http://localhost:5000"
TEST_SESSION_ID = f"test_session_{int(time.time())}"

def print_section(title):
    print(f"\n{'='*60}")
    print(f"🧪 {title}")
    print('='*60)

def print_test(test_name, status, details=""):
    status_emoji = "✅" if status else "❌"
    print(f"{status_emoji} {test_name}")
    if details:
        print(f"   {details}")

def test_health_check():
    """Test basic health check"""
    print_section("HEALTH CHECK")
    
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_test("Health Check", True, f"Version: {data.get('version')}, Status: {data.get('status')}")
            return True
        else:
            print_test("Health Check", False, f"Status code: {response.status_code}")
            return False
    except Exception as e:
        print_test("Health Check", False, f"Error: {e}")
        return False

def test_api_info():
    """Test API info endpoint"""
    print_section("API INFORMATION")
    
    try:
        response = requests.get(f"{API_BASE}/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_test("API Info", True, f"API Version: {data.get('version')}")
            print(f"   Platforms: {', '.join(data.get('platforms', []))}")
            print(f"   Endpoints: {len(data.get('endpoints', {}))}")
            return True
        else:
            print_test("API Info", False, f"Status code: {response.status_code}")
            return False
    except Exception as e:
        print_test("API Info", False, f"Error: {e}")
        return False

def test_shopify_product_search():
    """Test Shopify product search"""
    print_section("SHOPIFY PRODUCT SEARCH")
    
    # Test with different queries
    test_queries = [
        "test",
        "shirt", 
        "product",
        "https://example.myshopify.com/products/test-product"
    ]
    
    for query in test_queries:
        try:
            response = requests.get(
                f"{API_BASE}/shopify/products/search",
                params={'q': query},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    products = data.get('products', [])
                    print_test(f"Search '{query}'", True, f"Found {len(products)} products")
                    if products:
                        print(f"      First product: {products[0].get('title', 'N/A')}")
                else:
                    print_test(f"Search '{query}'", False, f"API Error: {data.get('error')}")
            else:
                print_test(f"Search '{query}'", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            print_test(f"Search '{query}'", False, f"Error: {e}")
    
    return True

def test_review_operations():
    """Test review skip and import operations"""
    print_section("REVIEW OPERATIONS")
    
    # Test skip review
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
            print_test("Skip Review", data.get('success'), data.get('message', ''))
        else:
            print_test("Skip Review", False, f"HTTP {response.status_code}")
            
    except Exception as e:
        print_test("Skip Review", False, f"Error: {e}")
    
    # Test single review import
    try:
        import_payload = {
            "review": {
                "id": f"test_review_import_{int(time.time())}",
                "rating": 5,
                "text": "Great product! Highly recommended.",
                "reviewer_name": "Test User",
                "date": datetime.now().strftime('%Y-%m-%d'),
                "country": "US",
                "verified": True,
                "images": ["https://example.com/image1.jpg"],
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
            print_test("Single Import", data.get('success'), data.get('message', ''))
        else:
            print_test("Single Import", False, f"HTTP {response.status_code}")
            
    except Exception as e:
        print_test("Single Import", False, f"Error: {e}")

def test_bulk_import():
    """Test bulk review import"""
    print_section("BULK IMPORT")
    
    try:
        bulk_payload = {
            "reviews": [
                {
                    "id": f"bulk_review_1_{int(time.time())}",
                    "rating": 5,
                    "text": "Excellent quality!",
                    "reviewer_name": "User 1",
                    "quality_score": 9.0,
                    "ai_recommended": True
                },
                {
                    "id": f"bulk_review_2_{int(time.time())}", 
                    "rating": 4,
                    "text": "Good product, fast shipping",
                    "reviewer_name": "User 2",
                    "quality_score": 7.5,
                    "ai_recommended": False
                }
            ],
            "shopify_product_id": "123456789",
            "session_id": TEST_SESSION_ID,
            "filters": {"min_quality_score": 7}
        }
        
        response = requests.post(
            f"{API_BASE}/admin/reviews/import/bulk",
            json=bulk_payload,
            headers={'Content-Type': 'application/json'},
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print_test("Bulk Import", True, 
                          f"Imported: {data.get('imported_count')}, "
                          f"Failed: {data.get('failed_count')}, "
                          f"Skipped: {data.get('skipped_count')}")
            else:
                print_test("Bulk Import", False, data.get('error'))
        else:
            print_test("Bulk Import", False, f"HTTP {response.status_code}")
            
    except Exception as e:
        print_test("Bulk Import", False, f"Error: {e}")

def test_bookmarklet():
    """Test bookmarklet JavaScript"""
    print_section("BOOKMARKLET")
    
    try:
        response = requests.get(f"{API_BASE}/js/bookmarklet.js", timeout=5)
        
        if response.status_code == 200:
            js_content = response.text
            
            # Check for key features
            features = {
                "Product Search": "setupProductSearch" in js_content,
                "Select Product": "selectProduct" in js_content,
                "Import Review": "importReview" in js_content,
                "Skip Review": "skipReview" in js_content,
                "Import All": "importAllReviews" in js_content,
                "Sakura Branding": "Sakura Reviews" in js_content
            }
            
            for feature, present in features.items():
                print_test(f"Bookmarklet - {feature}", present)
                
            print(f"   JavaScript size: {len(js_content):,} characters")
            
        else:
            print_test("Bookmarklet", False, f"HTTP {response.status_code}")
            
    except Exception as e:
        print_test("Bookmarklet", False, f"Error: {e}")

def test_review_scraping():
    """Test review scraping functionality"""
    print_section("REVIEW SCRAPING")
    
    try:
        # Test AliExpress scraping
        params = {
            'productId': '1005004632823451',  # Sample AliExpress product ID
            'platform': 'aliexpress',
            'page': 1,
            'per_page': 5,
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
                print_test("AliExpress Scraping", True, 
                          f"Scraped {len(reviews)} reviews")
                if reviews:
                    print(f"   First review quality: {reviews[0].get('quality_score', 'N/A')}/10")
                    print(f"   AI recommended: {sum(1 for r in reviews if r.get('ai_recommended'))}/{len(reviews)}")
            else:
                print_test("AliExpress Scraping", False, data.get('error'))
        else:
            print_test("AliExpress Scraping", False, f"HTTP {response.status_code}")
            
    except Exception as e:
        print_test("AliExpress Scraping", False, f"Error: {e}")

def main():
    """Run all tests"""
    print("🌸" * 30)
    print("   SAKURA REVIEWS - LIVE API TEST")
    print("🌸" * 30)
    
    print(f"\n🎯 Testing API at: {API_BASE}")
    print(f"🆔 Session ID: {TEST_SESSION_ID}")
    print(f"⏰ Test started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run all tests
    tests = [
        test_health_check,
        test_api_info,
        test_shopify_product_search,
        test_review_operations,
        test_bulk_import,
        test_bookmarklet,
        test_review_scraping
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test_func.__name__} failed: {e}")
            results.append(False)
    
    # Summary
    print_section("TEST SUMMARY")
    passed = sum(1 for r in results if r)
    total = len(results)
    
    print(f"✅ Tests Passed: {passed}/{total}")
    print(f"❌ Tests Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Your Sakura Reviews API is working perfectly!")
        print("\n🚀 Ready for production use:")
        print("   ✅ Shopify integration configured")
        print("   ✅ Product search working")
        print("   ✅ Review import/skip functionality")
        print("   ✅ Bulk import capabilities")
        print("   ✅ Bookmarklet with Part 1 features")
    else:
        print(f"\n⚠️ Some tests failed. Check the details above.")
    
    print(f"\n📖 Bookmarklet URL:")
    print(f"javascript:(function(){{var s=document.createElement('script');s.src='{API_BASE}/js/bookmarklet.js';document.head.appendChild(s);}})();")

if __name__ == "__main__":
    main()









