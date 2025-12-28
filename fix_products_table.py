"""Fix missing source_product_url column in products table"""
import psycopg2

conn = psycopg2.connect('postgresql://saksaks:11!!!!.Magics4321@193.203.165.217:5432/sakrev_db?sslmode=disable')
cur = conn.cursor()

print("\n" + "="*60)
print("FIXING PRODUCTS TABLE - Adding source_product_url")
print("="*60)

# Check if column exists
cur.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'products' AND column_name = 'source_product_url';
""")

if cur.fetchone():
    print("[OK] source_product_url already exists")
else:
    print("[X] Adding source_product_url column...")
    cur.execute("ALTER TABLE products ADD COLUMN source_product_url TEXT;")
    conn.commit()
    print("[OK] source_product_url column added")

cur.close()
conn.close()
print("\nDone!")

