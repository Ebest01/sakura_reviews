"""Check shops table schema"""
import psycopg2

conn = psycopg2.connect('postgresql://saksaks:11!!!!.Magics4321@193.203.165.217:5432/sakrev_db?sslmode=disable')
cur = conn.cursor()

# Get table schema
cur.execute("""
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'shops'
    ORDER BY ordinal_position;
""")

columns = cur.fetchall()

print("\n" + "="*60)
print("SHOPS TABLE SCHEMA:")
print("="*60)
for col in columns:
    print(f"  {col[0]:30} {col[1]:20} nullable={col[2]}")

# Check if owner_id exists
cur.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'shops' AND column_name = 'owner_id';
""")
if cur.fetchone():
    print("\n[OK] owner_id column EXISTS")
else:
    print("\n[X] owner_id column DOES NOT EXIST - NEEDS TO BE ADDED")

cur.close()
conn.close()

