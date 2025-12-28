"""Check reviews table schema"""
import psycopg2

conn = psycopg2.connect('postgresql://saksaks:11!!!!.Magics4321@193.203.165.217:5432/sakrev_db?sslmode=disable')
cur = conn.cursor()

cur.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'reviews' 
    ORDER BY ordinal_position
""")

print("Reviews table columns:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

# Check if any reviews exist
cur.execute("SELECT COUNT(*) FROM reviews")
count = cur.fetchone()[0]
print(f"\nTotal reviews in database: {count}")

if count > 0:
    cur.execute("SELECT id, shopify_product_id, reviewer_name, rating, created_at FROM reviews ORDER BY created_at DESC LIMIT 5")
    print("\nRecent reviews:")
    for r in cur.fetchall():
        print(f"  Review {r[0]}: shopify_product_id={r[1]}, author={r[2]}, rating={r[3]}, created={r[4]}")

conn.close()

