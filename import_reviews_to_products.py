#!/usr/bin/env python3
"""
Import Reviews to Specific Products
Connects to Easypanel PostgreSQL and imports reviews linked to Shopify products
"""
import psycopg2
import requests
import json
from datetime import datetime
from typing import List, Dict, Optional

# Database connection details
DB_CONFIG = {
    'host': '193.203.165.217',
    'port': 5432,
    'database': 'sakrev_db',
    'user': 'saksaks',
    'password': '11!!!!.Magics4321'
}

# Shopify API configuration
SHOPIFY_CONFIG = {
    'shop_domain': 'sakura-rev-test-store.myshopify.com',
    'access_token': 'YOUR_ACCESS_TOKEN_HERE',  # Replace with your access token
    'api_version': '2025-10'
}

def get_db_connection():
    """Get PostgreSQL database connection"""
    return psycopg2.connect(**DB_CONFIG)

def get_shop_id_from_db():
    """Get shop ID from database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, shop_domain FROM shops LIMIT 1;")
    shop = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if shop:
        return shop[0]
    return None

def get_shopify_products():
    """Fetch products from Shopify store"""
    headers = {
        'X-Shopify-Access-Token': SHOPIFY_CONFIG['access_token'],
        'Content-Type': 'application/json'
    }
    
    url = f"https://{SHOPIFY_CONFIG['shop_domain']}/admin/api/{SHOPIFY_CONFIG['api_version']}/products.json"
    params = {'limit': 250}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        products = data.get('products', [])
        
        print(f"\nFound {len(products)} products in Shopify store:\n")
        for i, product in enumerate(products, 1):
            print(f"{i}. {product['title']}")
            print(f"   ID: {product['id']}")
            print(f"   Handle: {product.get('handle', 'N/A')}")
            print()
        
        return products
        
    except Exception as e:
        print(f"Error fetching products: {e}")
        return []

def import_review_to_product(shop_id: int, shopify_product_id: str, review_data: Dict):
    """
    Import a single review to a specific product in the database
    
    Args:
        shop_id: Shop ID from database
        shopify_product_id: Shopify product ID (string)
        review_data: Review data dictionary
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Prepare review data
        reviewer_name = review_data.get('reviewer_name', review_data.get('author', 'Anonymous'))
        rating = review_data.get('rating', 5)
        title = review_data.get('title', '')
        body = review_data.get('body', review_data.get('text', ''))
        source_platform = review_data.get('source_platform', 'aliexpress')
        source_product_id = review_data.get('source_product_id', '')
        source_review_id = review_data.get('source_review_id', review_data.get('id', ''))
        reviewer_country = review_data.get('reviewer_country', review_data.get('country', ''))
        verified_purchase = review_data.get('verified_purchase', review_data.get('verified', False))
        
        # Handle review date
        review_date = None
        if review_data.get('review_date'):
            review_date = review_data['review_date']
        elif review_data.get('date'):
            try:
                review_date = datetime.fromisoformat(review_data['date'].replace('Z', '+00:00'))
            except:
                pass
        
        # Handle images (convert to JSON)
        images_json = json.dumps(review_data.get('images', []))
        
        # Quality scores
        quality_score = review_data.get('quality_score', review_data.get('ai_score', 0))
        ai_recommended = review_data.get('ai_recommended', False)
        if quality_score and quality_score > 8:
            ai_recommended = True
        
        # Insert review into database
        insert_query = """
            INSERT INTO reviews (
                shop_id, shopify_product_id, source_platform, source_product_id,
                source_review_id, reviewer_name, rating, title, body,
                verified_purchase, reviewer_country, review_date,
                images, quality_score, ai_recommended, status, published,
                imported_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING id;
        """
        
        cursor.execute(insert_query, (
            shop_id,
            shopify_product_id,
            source_platform,
            source_product_id,
            source_review_id,
            reviewer_name,
            rating,
            title,
            body,
            verified_purchase,
            reviewer_country,
            review_date,
            images_json,
            quality_score,
            ai_recommended,
            'published',  # status
            True,  # published
            datetime.utcnow()  # imported_at
        ))
        
        review_id = cursor.fetchone()[0]
        
        # Update shop's review count
        cursor.execute(
            "UPDATE shops SET reviews_imported = reviews_imported + 1 WHERE id = %s;",
            (shop_id,)
        )
        
        conn.commit()
        
        print(f"  Imported review ID: {review_id}")
        return review_id
        
    except Exception as e:
        conn.rollback()
        print(f"  Error importing review: {e}")
        return None
        
    finally:
        cursor.close()
        conn.close()

def import_sample_reviews(shopify_product_id: str, count: int = 3):
    """
    Import sample reviews to a specific product
    
    Args:
        shopify_product_id: Shopify product ID to import reviews for
        count: Number of sample reviews to create
    """
    shop_id = get_shop_id_from_db()
    
    if not shop_id:
        print("Error: No shop found in database!")
        return
    
    print(f"\nImporting {count} sample reviews to product {shopify_product_id}...")
    print(f"Shop ID: {shop_id}\n")
    
    # Sample review data
    sample_reviews = [
        {
            'reviewer_name': 'Sarah Johnson',
            'rating': 5,
            'title': 'Excellent quality!',
            'body': 'This product exceeded my expectations. Very high quality and fast shipping.',
            'source_platform': 'aliexpress',
            'source_product_id': 'sample_product_1',
            'source_review_id': 'review_1',
            'reviewer_country': 'US',
            'verified_purchase': True,
            'images': ['https://via.placeholder.com/400x300?text=Review+Photo+1'],
            'quality_score': 9.5,
            'ai_recommended': True,
            'review_date': datetime.utcnow()
        },
        {
            'reviewer_name': 'Michael Chen',
            'rating': 4,
            'title': 'Good value for money',
            'body': 'Solid product, works as described. Minor issues with packaging but overall satisfied.',
            'source_platform': 'aliexpress',
            'source_product_id': 'sample_product_1',
            'source_review_id': 'review_2',
            'reviewer_country': 'CA',
            'verified_purchase': True,
            'images': [],
            'quality_score': 7.8,
            'ai_recommended': False,
            'review_date': datetime.utcnow()
        },
        {
            'reviewer_name': 'Emma Williams',
            'rating': 5,
            'title': 'Perfect! Highly recommend',
            'body': 'Absolutely love this product! Great quality and looks exactly like the photos. Will definitely order again!',
            'source_platform': 'aliexpress',
            'source_product_id': 'sample_product_1',
            'source_review_id': 'review_3',
            'reviewer_country': 'GB',
            'verified_purchase': True,
            'images': [
                'https://via.placeholder.com/400x300?text=Review+Photo+2',
                'https://via.placeholder.com/400x300?text=Review+Photo+3'
            ],
            'quality_score': 9.8,
            'ai_recommended': True,
            'review_date': datetime.utcnow()
        }
    ]
    
    imported_count = 0
    for i, review_data in enumerate(sample_reviews[:count], 1):
        print(f"Importing review {i}/{min(count, len(sample_reviews))}...")
        review_id = import_review_to_product(shop_id, shopify_product_id, review_data)
        if review_id:
            imported_count += 1
    
    print(f"\nSuccessfully imported {imported_count}/{count} reviews!")

def list_product_reviews(shopify_product_id: str):
    """List all reviews for a specific product"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, reviewer_name, rating, title, body, reviewer_country,
               verified_purchase, quality_score, imported_at
        FROM reviews
        WHERE shopify_product_id = %s
        ORDER BY imported_at DESC;
    """, (shopify_product_id,))
    
    reviews = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    print(f"\nReviews for product {shopify_product_id}:")
    print("=" * 60)
    
    if reviews:
        for review in reviews:
            review_id, name, rating, title, body, country, verified, quality, imported = review
            print(f"\nReview ID: {review_id}")
            print(f"Reviewer: {name} ({country})")
            print(f"Rating: {'*' * rating} ({rating}/5)")
            if title:
                print(f"Title: {title}")
            if body:
                print(f"Body: {body[:100]}...")
            print(f"Verified: {'Yes' if verified else 'No'}")
            if quality:
                print(f"Quality Score: {quality}/10")
            print(f"Imported: {imported}")
    else:
        print("No reviews found for this product.")
    
    print("=" * 60)

def main():
    """Main function with interactive menu"""
    print("=" * 60)
    print("PRODUCT-SPECIFIC REVIEW IMPORT SYSTEM")
    print("=" * 60)
    
    while True:
        print("\nOptions:")
        print("1. List Shopify products")
        print("2. Import sample reviews to a product")
        print("3. List reviews for a product")
        print("4. Check database stats")
        print("5. Exit")
        
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == '1':
            get_shopify_products()
            
        elif choice == '2':
            product_id = input("\nEnter Shopify Product ID: ").strip()
            count = input("Number of reviews to import (default 3): ").strip()
            count = int(count) if count.isdigit() else 3
            import_sample_reviews(product_id, count)
            
        elif choice == '3':
            product_id = input("\nEnter Shopify Product ID: ").strip()
            list_product_reviews(product_id)
            
        elif choice == '4':
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get shop info
            cursor.execute("SELECT id, shop_domain, reviews_imported, review_limit FROM shops LIMIT 1;")
            shop = cursor.fetchone()
            
            # Get review counts
            cursor.execute("SELECT COUNT(*) FROM reviews;")
            total_reviews = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT shopify_product_id) FROM reviews;")
            products_with_reviews = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            print("\nDatabase Statistics:")
            print("=" * 60)
            if shop:
                shop_id, domain, imported, limit = shop
                print(f"Shop: {domain}")
                print(f"Reviews Imported: {imported}/{limit}")
                print(f"Total Reviews in DB: {total_reviews}")
                print(f"Products with Reviews: {products_with_reviews}")
            print("=" * 60)
            
        elif choice == '5':
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()

