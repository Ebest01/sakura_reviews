#!/usr/bin/env python3
"""
Test Shopify Products - Check what's in the store
"""

import os
import requests

# Test store details - Use environment variables for security
ACCESS_TOKEN = os.getenv('SHOPIFY_ACCESS_TOKEN', 'your-access-token-here')
SHOP_DOMAIN = os.getenv('SHOPIFY_SHOP_DOMAIN', 'your-shop.myshopify.com')
API_VERSION = '2025-10'

def test_direct_shopify():
    """Test direct Shopify API"""
    print("=" * 50)
    print("TESTING DIRECT SHOPIFY API")
    print("=" * 50)
    
    headers = {
        'X-Shopify-Access-Token': ACCESS_TOKEN,
        'Content-Type': 'application/json'
    }
    
    # Get all products
    url = f"https://{SHOP_DOMAIN}/admin/api/{API_VERSION}/products.json?limit=10"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            products = data.get('products', [])
            print(f"Products found: {len(products)}")
            
            for i, product in enumerate(products[:5], 1):
                print(f"  {i}. {product['title']}")
                print(f"     ID: {product['id']}")
                print(f"     Handle: {product['handle']}")
                print()
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

def test_sakura_api():
    """Test our Sakura Reviews API"""
    print("=" * 50)
    print("TESTING SAKURA REVIEWS API")
    print("=" * 50)
    
    # Test different search terms
    search_terms = ['collection', 'snowboard', 'liquid', 'multi', 'the']
    
    for term in search_terms:
        try:
            response = requests.get(f'http://localhost:5000/shopify/products/search?q={term}', timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    products = data.get('products', [])
                    print(f"Search '{term}': {len(products)} products found")
                    for product in products[:2]:
                        print(f"  - {product['title']}")
                else:
                    print(f"Search '{term}': Error - {data.get('error')}")
            else:
                print(f"Search '{term}': HTTP {response.status_code}")
                
        except Exception as e:
            print(f"Search '{term}': Error - {e}")

if __name__ == "__main__":
    test_direct_shopify()
    print()
    test_sakura_api()










