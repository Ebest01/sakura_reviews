"""Fix ALL missing columns in products table to match models_v2.py"""
import psycopg2

conn = psycopg2.connect('postgresql://saksaks:11!!!!.Magics4321@193.203.165.217:5432/sakrev_db?sslmode=disable')
cur = conn.cursor()

print("\n" + "="*60)
print("FIXING PRODUCTS TABLE - Adding ALL Missing Columns")
print("="*60)

# All columns that should exist according to models_v2.py Product model
required_columns = {
    'shopify_product_url': 'TEXT',
    'source_platform': 'VARCHAR(50)',
    'source_product_id': 'VARCHAR(255)',
    'source_product_url': 'TEXT',
    'price': 'DOUBLE PRECISION',
    'currency': 'VARCHAR(10)',
    'image_url': 'TEXT',
    'status': 'VARCHAR(50) DEFAULT \'active\'',
    'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
    'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
}

# Check current columns
cur.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'products'
    ORDER BY column_name;
""")
existing_columns = [row[0] for row in cur.fetchall()]

print(f"\nCurrent columns: {', '.join(existing_columns)}")

# Add missing columns
for col_name, col_def in required_columns.items():
    if col_name in existing_columns:
        print(f"[OK] {col_name} already exists")
    else:
        print(f"[X] Adding {col_name}...")
        try:
            cur.execute(f"ALTER TABLE products ADD COLUMN {col_name} {col_def};")
            conn.commit()
            print(f"[OK] {col_name} added successfully")
        except Exception as e:
            print(f"[ERROR] Failed to add {col_name}: {e}")
            conn.rollback()

# Verify all columns exist now
print("\n" + "="*60)
print("VERIFICATION")
print("="*60)

cur.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'products'
    ORDER BY column_name;
""")
final_columns = [row[0] for row in cur.fetchall()]

all_present = True
for col_name in required_columns.keys():
    if col_name in final_columns:
        print(f"[OK] {col_name} verified")
    else:
        print(f"[X] {col_name} MISSING!")
        all_present = False

cur.close()
conn.close()

if all_present:
    print("\n✅ All columns are present! Products table is ready.")
else:
    print("\n❌ Some columns are still missing. Check errors above.")

print("\nDone!")

