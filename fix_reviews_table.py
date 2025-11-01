"""Fix missing product_id column in reviews table"""
import psycopg2

conn = psycopg2.connect('postgresql://saksaks:11!!!!.Magics4321@193.203.165.217:5432/sakrev_db?sslmode=disable')
cur = conn.cursor()

print("\n" + "="*60)
print("FIXING REVIEWS TABLE - Adding product_id column")
print("="*60)

# Check if column exists
cur.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'reviews' AND column_name = 'product_id';
""")

if cur.fetchone():
    print("[OK] product_id already exists")
else:
    print("[X] Adding product_id column...")
    
    # Check if products table exists first
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'products'
        );
    """)
    
    if not cur.fetchone()[0]:
        print("[ERROR] products table does not exist! Cannot add foreign key.")
        cur.close()
        conn.close()
        exit(1)
    
    # Add product_id column (nullable first)
    cur.execute("ALTER TABLE reviews ADD COLUMN product_id INTEGER;")
    conn.commit()
    
    # Set default product_id for existing reviews (if any)
    # Link to first product for each shop's reviews
    cur.execute("""
        UPDATE reviews r
        SET product_id = (
            SELECT MIN(p.id)
            FROM products p
            WHERE p.shop_id = r.shop_id
        )
        WHERE r.product_id IS NULL
        AND EXISTS (SELECT 1 FROM products WHERE shop_id = r.shop_id);
    """)
    conn.commit()
    
    # Add foreign key constraint
    try:
        cur.execute("""
            ALTER TABLE reviews 
            ADD CONSTRAINT fk_reviews_product 
            FOREIGN KEY (product_id) REFERENCES products(id);
        """)
        conn.commit()
        print("[OK] Foreign key constraint added")
    except Exception as e:
        print(f"[WARNING] Could not add foreign key (may already exist or data issue): {e}")
        conn.rollback()
    
    # Create index
    try:
        cur.execute("CREATE INDEX IF NOT EXISTS idx_reviews_product_id ON reviews(product_id);")
        conn.commit()
        print("[OK] Index created")
    except Exception as e:
        print(f"[WARNING] Could not create index: {e}")
        conn.rollback()
    
    print("[OK] product_id column added successfully")

# Verify
cur.execute("""
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'reviews' 
    AND column_name IN ('product_id', 'shopify_product_id', 'shop_id')
    ORDER BY column_name;
""")

columns = cur.fetchall()
print("\nVerification:")
for col in columns:
    nullable = "NULL" if col[2] == 'YES' else "NOT NULL"
    print(f"  {col[0]:<25} {col[1]:<20} {nullable}")

cur.close()
conn.close()
print("\nDone!")

