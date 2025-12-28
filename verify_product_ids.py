"""Verify product IDs are correctly stored"""
import psycopg2

conn = psycopg2.connect('postgresql://saksaks:11!!!!.Magics4321@193.203.165.217:5432/sakrev_db?sslmode=disable')
cur = conn.cursor()

print("\n" + "="*60)
print("VERIFYING PRODUCT IDs")
print("="*60)

# Check products
print("\nPRODUCTS:")
cur.execute("""
    SELECT id, shopify_product_id, aliexpress_product_id, source_product_id, source_platform
    FROM products
    ORDER BY id DESC
    LIMIT 5;
""")
products = cur.fetchall()

if products:
    print(f"Found {len(products)} product(s):")
    for p in products:
        print(f"  Product ID: {p[0]}")
        print(f"    - shopify_product_id: {p[1]}")
        print(f"    - aliexpress_product_id: {p[2] or '(null)'}")
        print(f"    - source_product_id: {p[3] or '(null)'}")
        print(f"    - source_platform: {p[4] or '(null)'}")
        print()
else:
    print("  No products found")

# Check reviews
print("\nREVIEWS:")
cur.execute("""
    SELECT id, shopify_product_id, aliexpress_product_id, source_product_id, source_platform, reviewer_name
    FROM reviews
    ORDER BY id DESC
    LIMIT 5;
""")
reviews = cur.fetchall()

if reviews:
    print(f"Found {len(reviews)} review(s):")
    for r in reviews:
        print(f"  Review ID: {r[0]}")
        print(f"    - shopify_product_id: {r[1]}")
        print(f"    - aliexpress_product_id: {r[2] or '(null)'}")
        print(f"    - source_product_id: {r[3] or '(null)'}")
        print(f"    - source_platform: {r[4] or '(null)'}")
        print(f"    - reviewer: {r[5]}")
        print()
else:
    print("  No reviews found")

cur.close()
conn.close()
print("Done!")

