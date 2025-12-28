#!/usr/bin/env python3
"""
Update Shopify Configuration Script
Run this after getting your access token from the test store
"""

import os
import sys

def update_config():
    print("=" * 60)
    print("SAKURA REVIEWS - SHOPIFY CONFIG UPDATE")
    print("=" * 60)
    
    print("\nYour test store details:")
    print("Store: sakura-rev-test-store.myshopify.com")
    print("App: Sakura Rev Legacy BTN")
    print("API Key: 58c77d7f3f0132f238e80a4ab4f2ec5e")
    
    print("\n" + "=" * 60)
    print("STEP 1: Get your access token")
    print("=" * 60)
    print("1. Go to your test store admin")
    print("2. Apps and sales channels > Develop apps")
    print("3. Click 'Sakura Rev Legacy BTN'")
    print("4. Click 'Configure Admin API scopes'")
    print("5. Enable: read_products, write_products")
    print("6. Click 'Save'")
    print("7. Click 'Install app'")
    print("8. Copy the 'Admin API access token'")
    
    print("\n" + "=" * 60)
    print("STEP 2: Enter your access token")
    print("=" * 60)
    
    access_token = input("Paste your access token here: ").strip()
    
    if not access_token:
        print("❌ No token provided. Exiting.")
        return
    
    if not access_token.startswith('shpat_'):
        print("⚠️ Warning: Token doesn't start with 'shpat_' - are you sure this is correct?")
        confirm = input("Continue anyway? (y/n): ").strip().lower()
        if confirm != 'y':
            return
    
    print("\n" + "=" * 60)
    print("STEP 3: Updating configuration")
    print("=" * 60)
    
    # Set environment variables for this session
    os.environ['SHOPIFY_ACCESS_TOKEN'] = access_token
    os.environ['SHOPIFY_SHOP_DOMAIN'] = 'sakura-rev-test-store.myshopify.com'
    
    # Create a config file
    config_content = f"""# Shopify Configuration for Sakura Reviews
# Add these to your environment or .env file

SHOPIFY_ACCESS_TOKEN={access_token}
SHOPIFY_SHOP_DOMAIN=sakura-rev-test-store.myshopify.com
SHOPIFY_API_KEY=58c77d7f3f0132f238e80a4ab4f2ec5e
SHOPIFY_API_SECRET=8c254b805fef674a9f7b390859a9d742
SHOPIFY_API_VERSION=2025-10
"""
    
    with open('shopify_live_config.txt', 'w') as f:
        f.write(config_content)
    
    print("✅ Configuration saved to 'shopify_live_config.txt'")
    print("✅ Environment variables set for this session")
    
    print("\n" + "=" * 60)
    print("STEP 4: Test the connection")
    print("=" * 60)
    
    try:
        import requests
        
        headers = {
            'X-Shopify-Access-Token': access_token,
            'Content-Type': 'application/json'
        }
        
        url = f"https://sakura-rev-test-store.myshopify.com/admin/api/2025-10/shop.json"
        
        print("Testing connection to Shopify...")
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            shop_data = response.json()['shop']
            print(f"✅ SUCCESS! Connected to: {shop_data['name']}")
            print(f"   Domain: {shop_data['domain']}")
            print(f"   Plan: {shop_data['plan_name']}")
            
            # Test product search
            print("\nTesting product search...")
            products_url = f"https://sakura-rev-test-store.myshopify.com/admin/api/2025-10/products.json?limit=5"
            products_response = requests.get(products_url, headers=headers, timeout=10)
            
            if products_response.status_code == 200:
                products = products_response.json()['products']
                print(f"✅ Found {len(products)} products in your store")
                for product in products[:3]:
                    print(f"   - {product['title']}")
            else:
                print(f"⚠️ Product search failed: {products_response.status_code}")
            
        else:
            print(f"❌ Connection failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    print("\n" + "=" * 60)
    print("NEXT STEPS")
    print("=" * 60)
    print("1. Restart your Sakura Reviews server:")
    print("   python app_enhanced.py")
    print("\n2. Test the API:")
    print("   python simple_api_test.py")
    print("\n3. Use the bookmarklet on AliExpress!")
    
    print(f"\n🌸 Your Shopify integration is ready!")

if __name__ == "__main__":
    update_config()










