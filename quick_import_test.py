#!/usr/bin/env python3
"""
Quick test to import reviews to a specific product
Run this to quickly test the import functionality
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from import_reviews_to_products import get_shopify_products, import_sample_reviews, get_shop_id_from_db, list_product_reviews

if __name__ == "__main__":
    print("=" * 60)
    print("QUICK IMPORT TEST")
    print("=" * 60)
    
    # Step 1: Get products
    print("\nStep 1: Fetching products from Shopify...")
    products = get_shopify_products()
    
    if not products:
        print("No products found. Exiting.")
        exit(1)
    
    # Step 2: Use first product for testing
    first_product = products[0]
    product_id = str(first_product['id'])
    
    print(f"\nStep 2: Importing sample reviews to product:")
    print(f"  Product: {first_product['title']}")
    print(f"  ID: {product_id}")
    
    # Step 3: Import reviews
    import_sample_reviews(product_id, count=3)
    
    # Step 4: List imported reviews
    print("\nStep 3: Verifying imported reviews...")
    list_product_reviews(product_id)
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Run 'python import_reviews_to_products.py' for interactive menu")
    print("2. Check database using psql: SELECT * FROM reviews WHERE shopify_product_id = '" + product_id + "';")
    print("3. Test widget: http://localhost:5000/widget/demo-shop/reviews/" + product_id)

