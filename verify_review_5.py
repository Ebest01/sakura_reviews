"""Verify review ID 5 was saved correctly"""
import psycopg2

conn = psycopg2.connect('postgresql://saksaks:11!!!!.Magics4321@193.203.165.217:5432/sakrev_db?sslmode=disable')
cur = conn.cursor()

print("\n" + "="*60)
print("VERIFYING REVIEW ID 5")
print("="*60)

# Get review details
cur.execute("""
    SELECT 
        id, shop_id, product_id, shopify_product_id, 
        aliexpress_product_id, source_product_id,
        source_platform, source_review_id,
        reviewer_name, rating, title, body,
        verified_purchase, reviewer_country, review_date,
        quality_score, ai_recommended, status,
        imported_at
    FROM reviews
    WHERE id = 5;
""")

review = cur.fetchone()

if review:
    print("\n[OK] REVIEW FOUND!")
    print(f"\nDatabase Details:")
    print(f"  - Review ID (DB): {review[0]}")
    print(f"  - Shop ID: {review[1]}")
    print(f"  - Product ID (DB): {review[2]}")
    print(f"  - Shopify Product ID: {review[3]}")
    print(f"  - AliExpress Product ID: {review[4]}")
    print(f"  - Source Product ID: {review[5]}")
    print(f"  - Source Platform: {review[6]}")
    print(f"  - Source Review ID: {review[7]}")
    print(f"\nReview Content:")
    print(f"  - Reviewer: {review[8]}")
    print(f"  - Rating: {review[9]} stars")
    print(f"  - Title: {review[10] or '(no title)'}")
    print(f"  - Body: {review[11][:100] + '...' if review[11] and len(review[11]) > 100 else review[11] or '(no body)'}")
    print(f"  - Verified Purchase: {review[12]}")
    print(f"  - Country: {review[13] or 'N/A'}")
    print(f"  - Review Date: {review[14] or 'N/A'}")
    print(f"\nAI Scoring:")
    print(f"  - Quality Score: {review[15] or 'N/A'}")
    print(f"  - AI Recommended: {review[16]}")
    print(f"\nStatus:")
    print(f"  - Status: {review[17]}")
    print(f"  - Imported At: {review[18]}")
    
    # Get media count
    cur.execute("""
        SELECT COUNT(*) FROM review_media WHERE review_id = 5;
    """)
    media_count = cur.fetchone()[0]
    print(f"\nMedia:")
    print(f"  - Images Count: {media_count}")
    
    if media_count > 0:
        cur.execute("""
            SELECT media_url FROM review_media WHERE review_id = 5;
        """)
        images = cur.fetchall()
        print(f"  - Image URLs:")
        for idx, img in enumerate(images, 1):
            print(f"    {idx}. {img[0]}")
    
    # Get product details
    cur.execute("""
        SELECT 
            id, shopify_product_id, aliexpress_product_id, 
            source_product_id, source_platform
        FROM products
        WHERE id = %s;
    """, (review[2],))
    
    product = cur.fetchone()
    if product:
        print(f"\nProduct Details:")
        print(f"  - Product ID (DB): {product[0]}")
        print(f"  - Shopify Product ID: {product[1]}")
        print(f"  - AliExpress Product ID: {product[2]}")
        print(f"  - Source Product ID: {product[3]}")
        print(f"  - Source Platform: {product[4]}")
    
else:
    print("\n[X] REVIEW NOT FOUND!")

# Also check by shopify_product_id
print("\n" + "="*60)
print("VERIFYING BY SHOPIFY PRODUCT ID")
print("="*60)

cur.execute("""
    SELECT COUNT(*) 
    FROM reviews 
    WHERE shopify_product_id = '10045740024122';
""")
count = cur.fetchone()[0]
print(f"\nTotal reviews for Shopify Product ID '10045740024122': {count}")

if count > 0:
    cur.execute("""
        SELECT id, reviewer_name, rating, imported_at, aliexpress_product_id
        FROM reviews 
        WHERE shopify_product_id = '10045740024122'
        ORDER BY id DESC;
    """)
    reviews = cur.fetchall()
    print("\nAll reviews for this product:")
    for r in reviews:
        print(f"  - Review ID: {r[0]}, Reviewer: {r[1]}, Rating: {r[2]}, AliExpress Product: {r[4]}, Imported: {r[3]}")

cur.close()
conn.close()
print("\nDone!")

