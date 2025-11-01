#!/usr/bin/env python3
"""
Verify Reviews in Database
Quick script to check if reviews are properly saved in Easypanel PostgreSQL
"""
import psycopg2
import json

# Database connection details
DB_CONFIG = {
    'host': '193.203.165.217',
    'port': 5432,
    'database': 'sakrev_db',
    'user': 'saksaks',
    'password': '11!!!!.Magics4321'
}

def get_db_connection():
    """Get PostgreSQL database connection"""
    return psycopg2.connect(**DB_CONFIG)

def verify_product_reviews(shopify_product_id: str):
    """Verify all reviews for a specific product"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("=" * 70)
    print(f"VERIFYING REVIEWS FOR PRODUCT: {shopify_product_id}")
    print("=" * 70)
    
    try:
        # Count total reviews
        cursor.execute("""
            SELECT COUNT(*) FROM reviews 
            WHERE shopify_product_id = %s;
        """, (shopify_product_id,))
        total = cursor.fetchone()[0]
        
        print(f"\nTotal Reviews: {total}")
        
        if total == 0:
            print("\nNo reviews found for this product!")
            return
        
        # Get detailed review list
        cursor.execute("""
            SELECT 
                id,
                reviewer_name,
                rating,
                title,
                LEFT(body, 100) as body_preview,
                reviewer_country,
                verified_purchase,
                quality_score,
                ai_recommended,
                imported_at,
                CASE 
                    WHEN images IS NULL OR images::text = '[]' THEN false 
                    ELSE true 
                END as has_images,
                images
            FROM reviews 
            WHERE shopify_product_id = %s
            ORDER BY imported_at DESC;
        """, (shopify_product_id,))
        
        reviews = cursor.fetchall()
        
        print(f"\nDetailed Review List ({len(reviews)} reviews):")
        print("-" * 70)
        
        for i, review in enumerate(reviews, 1):
            (rev_id, name, rating, title, body, country, verified, 
             quality, ai_rec, imported, has_images, images_json) = review
            
            print(f"\nReview #{i} (ID: {rev_id})")
            print(f"  Reviewer: {name} ({country})")
            print(f"  Rating: {'*' * rating} ({rating}/5)")
            if title:
                print(f"  Title: {title}")
            if body:
                print(f"  Body: {body}...")
            print(f"  Verified: {'Yes' if verified else 'No'}")
            print(f"  Quality Score: {quality:.1f}/10" if quality else "  Quality Score: N/A")
            print(f"  AI Recommended: {'Yes' if ai_rec else 'No'}")
            print(f"  Has Images: {'Yes' if has_images else 'No'}")
            if has_images and images_json:
                try:
                    images = json.loads(images_json)
                    print(f"  Image Count: {len(images)}")
                except:
                    pass
            print(f"  Imported: {imported}")
        
        # Get statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                AVG(rating) as avg_rating,
                COUNT(CASE WHEN verified_purchase THEN 1 END) as verified_count,
                COUNT(CASE WHEN images IS NOT NULL AND images::text != '[]' THEN 1 END) as with_images,
                AVG(quality_score) as avg_quality
            FROM reviews 
            WHERE shopify_product_id = %s;
        """, (shopify_product_id,))
        
        stats = cursor.fetchone()
        total_rev, avg_rating, verified, with_images, avg_quality = stats
        
        print("\n" + "=" * 70)
        print("STATISTICS")
        print("=" * 70)
        print(f"  Total Reviews: {total_rev}")
        print(f"  Average Rating: {avg_rating:.2f}/5" if avg_rating else "  Average Rating: N/A")
        print(f"  Verified Purchases: {verified}")
        print(f"  Reviews with Images: {with_images}")
        print(f"  Average Quality Score: {avg_quality:.2f}/10" if avg_quality else "  Average Quality Score: N/A")
        
        # Get shop info
        cursor.execute("""
            SELECT s.id, s.shop_domain, s.reviews_imported, s.review_limit
            FROM shops s
            JOIN reviews r ON s.id = r.shop_id
            WHERE r.shopify_product_id = %s
            LIMIT 1;
        """, (shopify_product_id,))
        
        shop_info = cursor.fetchone()
        if shop_info:
            shop_id, domain, imported, limit = shop_info
            print(f"\n  Shop: {domain}")
            print(f"  Total Reviews Imported (all products): {imported}/{limit}")
        
        print("=" * 70)
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        cursor.close()
        conn.close()

def list_all_products_with_reviews():
    """List all products that have reviews"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("=" * 70)
    print("ALL PRODUCTS WITH REVIEWS")
    print("=" * 70)
    
    try:
        cursor.execute("""
            SELECT 
                shopify_product_id,
                COUNT(*) as review_count,
                AVG(rating) as avg_rating,
                MAX(imported_at) as last_imported
            FROM reviews
            GROUP BY shopify_product_id
            ORDER BY review_count DESC;
        """)
        
        products = cursor.fetchall()
        
        if products:
            print(f"\nFound {len(products)} product(s) with reviews:\n")
            for product_id, count, avg_rating, last_imported in products:
                print(f"  Product ID: {product_id}")
                print(f"    Reviews: {count}")
                print(f"    Avg Rating: {avg_rating:.2f}/5" if avg_rating else "    Avg Rating: N/A")
                print(f"    Last Imported: {last_imported}")
                print()
        else:
            print("\nNo products with reviews found.")
        
    except Exception as e:
        print(f"ERROR: {e}")
        
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Verify specific product
        product_id = sys.argv[1]
        verify_product_reviews(product_id)
    else:
        # List all products
        list_all_products_with_reviews()
        print("\nUsage: python verify_reviews_in_db.py [PRODUCT_ID]")
        print("Example: python verify_reviews_in_db.py 10045740417338")

