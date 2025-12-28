"""
Test the Sakura Widget System
"""
import requests
import json

def test_widget_system():
    base_url = "http://localhost:5000"
    
    print("Testing Sakura Widget System")
    print("=" * 50)
    
    # Test 1: Widget URL generation
    print("\n1. Testing Widget URL Generation")
    try:
        response = requests.get(f"{base_url}/app-blocks", timeout=5)
        if response.status_code == 200:
            print("SUCCESS: App blocks endpoint working")
            data = response.json()
            print(f"   Available blocks: {len(data.get('blocks', []))}")
        else:
            print(f"FAILED: App blocks failed: {response.status_code}")
    except Exception as e:
        print(f"ERROR: App blocks error: {e}")
    
    # Test 2: Widget API
    print("\n2. Testing Widget API")
    try:
        response = requests.get(f"{base_url}/widget/test-shop/reviews/test-product/api", timeout=5)
        if response.status_code == 200:
            print("SUCCESS: Widget API working")
            data = response.json()
            print(f"   Reviews found: {data.get('total', 0)}")
        else:
            print(f"FAILED: Widget API failed: {response.status_code}")
    except Exception as e:
        print(f"ERROR: Widget API error: {e}")
    
    # Test 3: Widget HTML
    print("\n3. Testing Widget HTML")
    try:
        response = requests.get(f"{base_url}/widget/test-shop/reviews/test-product", timeout=5)
        if response.status_code == 200:
            print("SUCCESS: Widget HTML working")
            content = response.text
            if "Sakura Reviews" in content:
                print("   SUCCESS: Widget content found")
            else:
                print("   FAILED: Widget content missing")
        else:
            print(f"FAILED: Widget HTML failed: {response.status_code}")
    except Exception as e:
        print(f"ERROR: Widget HTML error: {e}")
    
    # Test 4: App Block HTML
    print("\n4. Testing App Block HTML")
    try:
        response = requests.get(f"{base_url}/app-blocks/sakura_reviews?shop_id=test-shop&product_id=test-product", timeout=5)
        if response.status_code == 200:
            print("SUCCESS: App block HTML working")
            content = response.text
            if "sakura-reviews-widget" in content:
                print("   SUCCESS: App block content found")
            else:
                print("   FAILED: App block content missing")
        else:
            print(f"FAILED: App block HTML failed: {response.status_code}")
    except Exception as e:
        print(f"ERROR: App block HTML error: {e}")
    
    print("\n" + "=" * 50)
    print("Widget System Test Complete!")

if __name__ == "__main__":
    test_widget_system()
