"""Add shopify_product_id column to reviews table"""
import psycopg2

conn = psycopg2.connect('postgresql://saksaks:11!!!!.Magics4321@193.203.165.217:5432/sakrev_db?sslmode=disable')
cur = conn.cursor()

# Check if column exists
cur.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'reviews' 
    AND column_name = 'shopify_product_id'
""")

if cur.fetchone():
    print("Column shopify_product_id already exists in reviews table")
else:
    # Add column
    cur.execute("ALTER TABLE reviews ADD COLUMN shopify_product_id VARCHAR(255)")
    conn.commit()
    print("Added shopify_product_id column to reviews table")

# Create index if it doesn't exist
cur.execute("""
    SELECT indexname 
    FROM pg_indexes 
    WHERE tablename = 'reviews' 
    AND indexname = 'idx_reviews_shopify_product_id'
""")

if cur.fetchone():
    print("Index idx_reviews_shopify_product_id already exists")
else:
    cur.execute("CREATE INDEX idx_reviews_shopify_product_id ON reviews(shopify_product_id)")
    conn.commit()
    print("Created index on shopify_product_id")

conn.close()
print("Done!")

