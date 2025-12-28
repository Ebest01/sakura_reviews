"""
Check what product IDs are actually being imported
"""
import psycopg2

conn = psycopg2.connect('postgresql://saksaks:11!!!!.Magics4321@193.203.165.217:5432/sakrev_db?sslmode=disable')
cur = conn.cursor()

# Check all products in database
print("All products in database:")
cur.execute("SELECT id, shopify_product_id, shopify_product_title, created_at FROM products ORDER BY created_at DESC LIMIT 10")
products = cur.fetchall()
if products:
    for p in products:
        print(f"  ID: {p[0]}, Shopify Product ID: {p[1]}, Title: {p[2]}, Created: {p[3]}")
else:
    print("  No products found")

# Check all reviews
print("\nAll reviews in database:")
cur.execute("SELECT id, product_id, reviewer_name, rating, body, created_at FROM reviews ORDER BY created_at DESC LIMIT 10")
reviews = cur.fetchall()
if reviews:
    for r in reviews:
        print(f"  Review ID: {r[0]}, Product ID: {r[1]}, Author: {r[2]}, Rating: {r[3]}, Created: {r[5]}")
else:
    print("  No reviews found")

# Get product ID for reviews
if reviews:
    print("\nReviews with product details:")
    for r in reviews:
        cur.execute("SELECT shopify_product_id, shopify_product_title FROM products WHERE id = %s", (r[1],))
        product = cur.fetchone()
        if product:
            print(f"  Review {r[0]}: Shopify Product ID: {product[0]}, Product: {product[1]}")

conn.close()

