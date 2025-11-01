"""
Database Inspector for ReviewKing
================================

Inspect the SQLite database to see product-specific reviews.
"""
import sqlite3
import os

def inspect_database():
    """Inspect the database and show product-specific reviews"""
    db_path = 'instance/reviewking_test.db'
    
    if not os.path.exists(db_path):
        print(f"Database file {db_path} not found!")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("=== DATABASE INSPECTION ===")
    
    # Show tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"\nTables: {[table[0] for table in tables]}")
    
    # Show shops
    cursor.execute("SELECT id, shop_domain, sakura_shop_id, shop_name FROM shop;")
    shops = cursor.fetchall()
    print(f"\nShops ({len(shops)}):")
    for shop in shops:
        print(f"  ID: {shop[0]}, Domain: {shop[1]}, Sakura ID: {shop[2]}, Name: {shop[3]}")
    
    # Show products
    cursor.execute("SELECT id, shop_id, shopify_product_id, shopify_product_title FROM product;")
    products = cursor.fetchall()
    print(f"\nProducts ({len(products)}):")
    for product in products:
        print(f"  ID: {product[0]}, Shop: {product[1]}, Shopify ID: {product[2]}, Title: {product[3]}")
    
    # Show reviews with product info
    cursor.execute("""
        SELECT p.shopify_product_id, p.shopify_product_title, r.reviewer_name, r.rating, r.body
        FROM product p 
        JOIN review r ON p.id = r.product_id 
        ORDER BY p.shopify_product_id, r.id;
    """)
    reviews = cursor.fetchall()
    
    print(f"\nReviews ({len(reviews)}):")
    current_product = None
    for review in reviews:
        product_id, product_title, reviewer, rating, body = review
        
        if product_id != current_product:
            print(f"\n--- Product: {product_title} (ID: {product_id}) ---")
            current_product = product_id
        
        print(f"  {reviewer}: {rating} stars - {body}")
    
    # Verify product-specific separation
    cursor.execute("""
        SELECT p.shopify_product_id, COUNT(r.id) as review_count
        FROM product p 
        LEFT JOIN review r ON p.id = r.product_id 
        GROUP BY p.shopify_product_id;
    """)
    counts = cursor.fetchall()
    
    print(f"\n=== PRODUCT-SPECIFIC REVIEW COUNTS ===")
    for product_id, count in counts:
        print(f"Product {product_id}: {count} reviews")
    
    conn.close()

if __name__ == "__main__":
    inspect_database()
