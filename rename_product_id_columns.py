"""Add aliexpress_product_id column to products and reviews tables"""
import psycopg2

conn = psycopg2.connect('postgresql://saksaks:11!!!!.Magics4321@193.203.165.217:5432/sakrev_db?sslmode=disable')
cur = conn.cursor()

print("\n" + "="*60)
print("ADDING aliexpress_product_id COLUMN")
print("="*60)

# Add to products table
print("\n1. PRODUCTS TABLE:")
cur.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'products' AND column_name = 'aliexpress_product_id';
""")

if cur.fetchone():
    print("   [OK] aliexpress_product_id already exists in products")
else:
    print("   [X] Adding aliexpress_product_id to products...")
    cur.execute("ALTER TABLE products ADD COLUMN aliexpress_product_id VARCHAR(255);")
    conn.commit()
    
    # Copy data from source_product_id where platform is aliexpress
    cur.execute("""
        UPDATE products 
        SET aliexpress_product_id = source_product_id 
        WHERE source_platform = 'aliexpress' AND source_product_id IS NOT NULL;
    """)
    conn.commit()
    
    # Create index
    cur.execute("CREATE INDEX IF NOT EXISTS idx_products_aliexpress_product_id ON products(aliexpress_product_id);")
    conn.commit()
    print("   [OK] aliexpress_product_id added to products")

# Add to reviews table
print("\n2. REVIEWS TABLE:")
cur.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'reviews' AND column_name = 'aliexpress_product_id';
""")

if cur.fetchone():
    print("   [OK] aliexpress_product_id already exists in reviews")
else:
    print("   [X] Adding aliexpress_product_id to reviews...")
    cur.execute("ALTER TABLE reviews ADD COLUMN aliexpress_product_id VARCHAR(255);")
    conn.commit()
    
    # Copy data from source_product_id where platform is aliexpress
    cur.execute("""
        UPDATE reviews 
        SET aliexpress_product_id = source_product_id 
        WHERE source_platform = 'aliexpress' AND source_product_id IS NOT NULL;
    """)
    conn.commit()
    
    # Create index
    cur.execute("CREATE INDEX IF NOT EXISTS idx_reviews_aliexpress_product_id ON reviews(aliexpress_product_id);")
    conn.commit()
    print("   [OK] aliexpress_product_id added to reviews")

print("\n" + "="*60)
print("VERIFICATION")
print("="*60)

# Verify products
cur.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'products' 
    AND column_name IN ('shopify_product_id', 'source_product_id', 'aliexpress_product_id')
    ORDER BY column_name;
""")
products_cols = cur.fetchall()
print("\nPRODUCTS table columns:")
for col in products_cols:
    print(f"   - {col[0]}")

# Verify reviews
cur.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'reviews' 
    AND column_name IN ('shopify_product_id', 'source_product_id', 'aliexpress_product_id')
    ORDER BY column_name;
""")
reviews_cols = cur.fetchall()
print("\nREVIEWS table columns:")
for col in reviews_cols:
    print(f"   - {col[0]}")

cur.close()
conn.close()
print("\nDone!")

