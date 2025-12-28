#!/usr/bin/env python3
"""
Import AliExpress Reviews to Specific Shopify Products
Scrapes reviews from AliExpress and saves them to Easypanel PostgreSQL database
"""
import sys
import os
import psycopg2
import json
import requests
from datetime import datetime
from typing import List, Dict, Optional

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from backend.scrapers import AliExpressScraper, ScraperFactory

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

def scrape_aliexpress_reviews(aliexpress_url: str, max_reviews: int = 20):
    """
    Scrape reviews from AliExpress product URL
    
    Args:
        aliexpress_url: AliExpress product URL (e.g., https://www.aliexpress.com/item/1234567890.html)
        max_reviews: Maximum number of reviews to scrape
    
    Returns:
        List of review dictionaries
    """
    print(f"\nScraping AliExpress reviews from: {aliexpress_url}")
    
    scraper = AliExpressScraper()
    
    # Extract product ID from URL
    product_id = scraper.extract_product_id(aliexpress_url)
    
    if not product_id:
        print(f"Error: Could not extract product ID from URL: {aliexpress_url}")
        return []
    
    print(f"Extracted Product ID: {product_id}")
    
    # Scrape reviews (multiple pages if needed)
    all_reviews = []
    page = 1
    page_size = 20  # AliExpress API limit per page
    
    while len(all_reviews) < max_reviews:
        print(f"Fetching page {page}...")
        result = scraper.get_reviews(product_id, page=page, page_size=page_size)
        
        if not result.get('success'):
            print(f"Error scraping page {page}: {result.get('error', 'Unknown error')}")
            break
        
        reviews = result.get('reviews', [])
        if not reviews:
            print(f"No more reviews found on page {page}")
            break
        
        all_reviews.extend(reviews)
        print(f"  Found {len(reviews)} reviews on page {page}")
        
        # Check if there are more pages
        if not result.get('has_next', False):
            break
        
        # Check if we have enough
        if len(all_reviews) >= max_reviews:
            break
        
        page += 1
    
    # Limit to max_reviews
    all_reviews = all_reviews[:max_reviews]
    
    print(f"\nTotal reviews scraped: {len(all_reviews)}")
    return all_reviews, product_id

def calculate_quality_score(review: Dict) -> float:
    """Calculate quality score for a review (simple version)"""
    score = 5.0  # Base score
    
    # Length bonus
    text = review.get('text', '')
    if len(text) > 100:
        score += 1.0
    if len(text) > 200:
        score += 1.0
    
    # Images bonus
    images = review.get('images', [])
    if images:
        score += 1.0
        if len(images) > 1:
            score += 0.5
    
    # Rating bonus
    rating = review.get('rating', 5)
    if rating == 5:
        score += 0.5
    
    # Verified bonus
    if review.get('verified', False):
        score += 0.5
    
    # Helpful count bonus
    helpful = review.get('helpful_count', 0)
    if helpful > 10:
        score += 0.5
    
    return min(10.0, max(0.0, score))

def import_review_to_database(shop_id: int, shopify_product_id: str, review_data: Dict, source_product_id: str):
    """
    Import a single review to database
    
    Args:
        shop_id: Shop ID from database
        shopify_product_id: Shopify product ID (string)
        review_data: Review data from scraper
        source_product_id: AliExpress product ID
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Calculate quality score
        quality_score = calculate_quality_score(review_data)
        ai_recommended = quality_score >= 8.0
        
        # Parse review data
        reviewer_name = review_data.get('reviewer_name', review_data.get('buyerName', 'Anonymous'))
        rating = review_data.get('rating', 5)
        title = review_data.get('title', '')
        body = review_data.get('text', review_data.get('buyerFeedback', ''))
        source_review_id = review_data.get('id', '')
        reviewer_country = review_data.get('country', review_data.get('buyerCountry', ''))
        verified_purchase = review_data.get('verified', True)
        
        # Handle review date
        review_date = None
        date_str = review_data.get('date', review_data.get('evalTime', ''))
        if date_str:
            try:
                # Try parsing different date formats
                if isinstance(date_str, str):
                    # Try simple ISO format first
                    try:
                        review_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    except:
                        # Try parsing common date strings
                        # AliExpress often uses: "2024-12-15" or timestamp
                        try:
                            # If it's a number, treat as timestamp
                            if date_str.isdigit():
                                review_date = datetime.fromtimestamp(int(date_str) / 1000)
                            else:
                                # Try common date formats
                                for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%d-%m-%Y']:
                                    try:
                                        review_date = datetime.strptime(date_str, fmt)
                                        break
                                    except:
                                        continue
                        except:
                            review_date = datetime.utcnow()
                else:
                    review_date = datetime.fromisoformat(str(date_str))
            except:
                # If parsing fails, use current date
                review_date = datetime.utcnow()
        
        if not review_date:
            review_date = datetime.utcnow()
        
        # Handle images (convert to JSON)
        images = review_data.get('images', [])
        images_json = json.dumps(images) if images else '[]'
        
        # Check if review already exists (prevent duplicates)
        cursor.execute("""
            SELECT id FROM reviews 
            WHERE shop_id = %s 
            AND shopify_product_id = %s 
            AND source_review_id = %s
            LIMIT 1;
        """, (shop_id, shopify_product_id, source_review_id))
        
        existing = cursor.fetchone()
        if existing:
            print(f"  Review {source_review_id} already exists, skipping...")
            return existing[0]
        
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
            'aliexpress',
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
        
        return review_id
        
    except Exception as e:
        conn.rollback()
        raise e
        
    finally:
        cursor.close()
        conn.close()

def verify_reviews_in_database(shopify_product_id: str):
    """
    Verify reviews are properly saved in database
    
    Returns:
        Dictionary with verification results
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Count reviews for product
        cursor.execute("""
            SELECT COUNT(*) FROM reviews 
            WHERE shopify_product_id = %s;
        """, (shopify_product_id,))
        total_count = cursor.fetchone()[0]
        
        # Get detailed review info
        cursor.execute("""
            SELECT id, reviewer_name, rating, title, 
                   CASE WHEN body IS NULL THEN '' ELSE LEFT(body, 50) END as body_preview,
                   reviewer_country, verified_purchase, quality_score, 
                   imported_at,
                   CASE WHEN images IS NULL OR images::text = '[]' THEN false ELSE true END as has_images
            FROM reviews 
            WHERE shopify_product_id = %s
            ORDER BY imported_at DESC
            LIMIT 10;
        """, (shopify_product_id,))
        
        reviews = cursor.fetchall()
        
        # Get shop stats
        cursor.execute("""
            SELECT shop_id, COUNT(*) as review_count 
            FROM reviews 
            WHERE shopify_product_id = %s
            GROUP BY shop_id;
        """, (shopify_product_id,))
        shop_stats = cursor.fetchone()
        
        return {
            'success': True,
            'total_reviews': total_count,
            'reviews': reviews,
            'shop_stats': shop_stats
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
        
    finally:
        cursor.close()
        conn.close()

def import_aliexpress_to_shopify_product(aliexpress_url: str, shopify_product_id: str, max_reviews: int = 20):
    """
    Complete workflow: Scrape AliExpress reviews and import to Shopify product
    
    Args:
        aliexpress_url: AliExpress product URL
        shopify_product_id: Shopify product ID to link reviews to
        max_reviews: Maximum number of reviews to import
    """
    print("=" * 70)
    print("ALIEXPRESS REVIEW IMPORT WORKFLOW")
    print("=" * 70)
    
    # Step 1: Get shop ID
    shop_id = get_shop_id_from_db()
    if not shop_id:
        print("ERROR: No shop found in database!")
        print("Please run setup_database.py first to create demo shop.")
        return False
    
    print(f"\nStep 1: Shop ID from database: {shop_id}")
    
    # Step 2: Scrape reviews from AliExpress
    print(f"\nStep 2: Scraping reviews from AliExpress...")
    try:
        reviews, source_product_id = scrape_aliexpress_reviews(aliexpress_url, max_reviews)
    except Exception as e:
        print(f"ERROR scraping reviews: {e}")
        return False
    
    if not reviews:
        print("No reviews found to import!")
        return False
    
    print(f"Found {len(reviews)} reviews to import")
    
    # Step 3: Import each review to database
    print(f"\nStep 3: Importing reviews to database...")
    print(f"  Shopify Product ID: {shopify_product_id}")
    print(f"  Source Product ID: {source_product_id}")
    
    imported_count = 0
    skipped_count = 0
    error_count = 0
    
    for i, review in enumerate(reviews, 1):
        print(f"\n  [{i}/{len(reviews)}] Importing review...")
        print(f"    Reviewer: {review.get('reviewer_name', 'Unknown')}")
        print(f"    Rating: {review.get('rating', 'N/A')} stars")
        print(f"    Images: {len(review.get('images', []))}")
        
        try:
            review_id = import_review_to_database(
                shop_id, 
                shopify_product_id, 
                review, 
                source_product_id
            )
            print(f"    SUCCESS: Review ID {review_id}")
            imported_count += 1
        except Exception as e:
            if "already exists" in str(e):
                skipped_count += 1
                print(f"    SKIPPED: Duplicate review")
            else:
                error_count += 1
                print(f"    ERROR: {e}")
    
    # Step 4: Verify import
    print(f"\nStep 4: Verifying reviews in database...")
    verification = verify_reviews_in_database(shopify_product_id)
    
    if verification['success']:
        print(f"  Total reviews in database: {verification['total_reviews']}")
        print(f"\n  Sample reviews:")
        for rev in verification['reviews'][:5]:
            rev_id, name, rating, title, body, country, verified, quality, imported, has_images = rev
            print(f"    - {name} ({rating}★) - {country}")
            print(f"      Quality: {quality:.1f}/10, Images: {'Yes' if has_images else 'No'}")
            if title:
                print(f"      Title: {title[:50]}")
    else:
        print(f"  Verification error: {verification.get('error')}")
    
    # Summary
    print(f"\n" + "=" * 70)
    print("IMPORT SUMMARY")
    print("=" * 70)
    print(f"  Total scraped: {len(reviews)}")
    print(f"  Imported: {imported_count}")
    print(f"  Skipped (duplicates): {skipped_count}")
    print(f"  Errors: {error_count}")
    print(f"  Total in database: {verification.get('total_reviews', 0) if verification['success'] else 'N/A'}")
    print("=" * 70)
    
    return imported_count > 0

def main():
    """Interactive main function"""
    print("=" * 70)
    print("ALIEXPRESS REVIEW IMPORT TOOL")
    print("=" * 70)
    
    print("\nThis tool will:")
    print("1. Scrape reviews from an AliExpress product")
    print("2. Import them to Easypanel PostgreSQL database")
    print("3. Link them to a specific Shopify product")
    print("4. Verify they are saved correctly")
    
    print("\n" + "-" * 70)
    aliexpress_url = input("\nEnter AliExpress Product URL: ").strip()
    if not aliexpress_url:
        print("Error: URL required")
        return
    
    shopify_product_id = input("Enter Shopify Product ID: ").strip()
    if not shopify_product_id:
        print("Error: Shopify Product ID required")
        return
    
    max_reviews = input("Max reviews to import (default 20): ").strip()
    max_reviews = int(max_reviews) if max_reviews.isdigit() else 20
    
    print("\nStarting import process...")
    success = import_aliexpress_to_shopify_product(aliexpress_url, shopify_product_id, max_reviews)
    
    if success:
        print("\n" + "=" * 70)
        print("SUCCESS! Reviews imported to database.")
        print("=" * 70)
        print("\nNext steps:")
        print(f"1. Verify in database: SELECT * FROM reviews WHERE shopify_product_id = '{shopify_product_id}';")
        print(f"2. Test widget: http://localhost:5000/widget/demo-shop/reviews/{shopify_product_id}")
        print("3. Or use psql to verify the data")
    else:
        print("\nImport failed. Check errors above.")

if __name__ == "__main__":
    main()

