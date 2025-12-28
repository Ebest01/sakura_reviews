"""Check if reviews for product 10045740450106 are in database"""
import psycopg2

# Connect to database
conn = psycopg2.connect('postgresql://saksaks:11!!!!.Magics4321@193.203.165.217:5432/sakrev_db?sslmode=disable')
cur = conn.cursor()

# Check reviews for this product
product_id = '10045740450106'

print(f"\n{'='*60}")
print(f"Checking reviews for Shopify Product ID: {product_id}")
print(f"{'='*60}\n")

# Query reviews table
cur.execute("""
    SELECT 
        id, 
        shopify_product_id, 
        reviewer_name, 
        rating, 
        title, 
        source_review_id,
        review_date,
        imported_at,
        status
    FROM reviews 
    WHERE shopify_product_id = %s
    ORDER BY imported_at DESC;
""", (product_id,))

reviews = cur.fetchall()

if reviews:
    print(f"[OK] Found {len(reviews)} review(s) for product {product_id}:\n")
    for i, review in enumerate(reviews, 1):
        print(f"Review #{i}:")
        print(f"  Database ID: {review[0]}")
        print(f"  Shopify Product ID: {review[1]}")
        print(f"  Reviewer: {review[2]}")
        print(f"  Rating: {review[3]} stars")
        print(f"  Title: {review[4][:50] if review[4] else 'N/A'}...")
        print(f"  Source Review ID: {review[5]}")
        print(f"  Review Date: {review[6]}")
        print(f"  Imported At: {review[7]}")
        print(f"  Status: {review[8]}")
        print()
else:
        print(f"[X] No reviews found for product {product_id}")
        print("\nChecking if product exists in products table...")
        
        # Check if product exists
        cur.execute("""
            SELECT id, shopify_product_id, shopify_product_title, created_at
            FROM products 
            WHERE shopify_product_id = %s;
        """, (product_id,))
        
        product = cur.fetchone()
        if product:
            print(f"[OK] Product exists in database:")
            print(f"  DB ID: {product[0]}")
            print(f"  Shopify Product ID: {product[1]}")
            print(f"  Title: {product[2]}")
            print(f"  Created: {product[3]}")
        else:
            print(f"[X] Product {product_id} not found in products table")

# Also check recent imports
print(f"\n{'='*60}")
print("Recent import attempts (from logs):")
print(f"{'='*60}\n")
print("Review IDs from logs:")
print("  - 50191330739068040")
print("  - 60090837072745090")
print()

# Check if these specific review IDs exist
review_ids = ['50191330739068040', '60090837072745090']
for review_id in review_ids:
    cur.execute("""
        SELECT id, shopify_product_id, source_review_id, reviewer_name, rating
        FROM reviews 
        WHERE source_review_id = %s;
    """, (review_id,))
    
    found = cur.fetchone()
    if found:
        print(f"[OK] Review {review_id} FOUND in database:")
        print(f"   DB ID: {found[0]}")
        print(f"   Shopify Product ID: {found[1]}")
        print(f"   Source Review ID: {found[2]}")
        print(f"   Reviewer: {found[3]}")
        print(f"   Rating: {found[4]}")
    else:
        print(f"[X] Review {review_id} NOT FOUND in database")
    print()

cur.close()
conn.close()

print(f"{'='*60}")
print("Query complete!")
print(f"{'='*60}")

