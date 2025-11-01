"""Fix all missing columns in shops table"""
import psycopg2

conn = psycopg2.connect('postgresql://saksaks:11!!!!.Magics4321@193.203.165.217:5432/sakrev_db?sslmode=disable')
cur = conn.cursor()

# Columns that should exist according to models_v2.py
required_columns = {
    'owner_id': 'INTEGER NOT NULL',
    'sakura_shop_id': 'VARCHAR(255) NOT NULL'
}

print("\n" + "="*60)
print("FIXING SHOPS TABLE SCHEMA")
print("="*60)

# Check and add missing columns
for col_name, col_def in required_columns.items():
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'shops' AND column_name = %s;
    """, (col_name,))
    
    if cur.fetchone():
        print(f"[OK] {col_name} already exists")
    else:
        print(f"[X] Adding {col_name}...")
        
        if col_name == 'owner_id':
            # Check if shop_owners table exists
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'shop_owners'
                );
            """)
            
            if not cur.fetchone()[0]:
                cur.execute("""
                    CREATE TABLE shop_owners (
                        id SERIAL PRIMARY KEY,
                        email VARCHAR(255) UNIQUE NOT NULL,
                        name VARCHAR(255),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                conn.commit()
                print("[OK] Created shop_owners table")
            
            # Add owner_id (nullable first)
            cur.execute("ALTER TABLE shops ADD COLUMN owner_id INTEGER;")
            conn.commit()
            
            # Set default owner for existing shops
            cur.execute("""
                INSERT INTO shop_owners (email, name) 
                VALUES ('default@shop.com', 'Default Owner')
                ON CONFLICT (email) DO NOTHING
                RETURNING id;
            """)
            default_owner = cur.fetchone()
            if default_owner:
                default_owner_id = default_owner[0]
                cur.execute("UPDATE shops SET owner_id = %s WHERE owner_id IS NULL;", (default_owner_id,))
                conn.commit()
            
            # Make NOT NULL and add FK
            cur.execute("""
                ALTER TABLE shops 
                ALTER COLUMN owner_id SET NOT NULL,
                ADD CONSTRAINT fk_shops_owner 
                FOREIGN KEY (owner_id) REFERENCES shop_owners(id);
            """)
            conn.commit()
            print(f"[OK] {col_name} added")
            
        elif col_name == 'sakura_shop_id':
            # Add sakura_shop_id (nullable first)
            cur.execute("ALTER TABLE shops ADD COLUMN sakura_shop_id VARCHAR(255);")
            conn.commit()
            
            # Generate sakura_shop_id for existing shops
            cur.execute("SELECT id, shop_domain FROM shops WHERE sakura_shop_id IS NULL;")
            shops = cur.fetchall()
            
            import base64
            for shop_id, shop_domain in shops:
                sakura_id = base64.b64encode(shop_domain.encode()).decode().replace('=', '').replace('/', '').replace('+', '')
                cur.execute("UPDATE shops SET sakura_shop_id = %s WHERE id = %s;", (sakura_id, shop_id))
            
            conn.commit()
            
            # Make NOT NULL and add unique constraint
            cur.execute("""
                ALTER TABLE shops 
                ALTER COLUMN sakura_shop_id SET NOT NULL,
                ADD CONSTRAINT shops_sakura_shop_id_unique UNIQUE (sakura_shop_id);
            """)
            
            # Create index
            cur.execute("CREATE INDEX IF NOT EXISTS idx_shops_sakura_shop_id ON shops(sakura_shop_id);")
            conn.commit()
            print(f"[OK] {col_name} added")

print("\n" + "="*60)
print("VERIFICATION")
print("="*60)

# Verify all columns exist
cur.execute("""
    SELECT column_name 
    FROM information_schema.columns
    WHERE table_name = 'shops'
    ORDER BY column_name;
""")

existing_columns = [row[0] for row in cur.fetchall()]

for col_name in required_columns.keys():
    if col_name in existing_columns:
        print(f"[OK] {col_name} verified")
    else:
        print(f"[X] {col_name} MISSING!")

cur.close()
conn.close()
print("\nDone!")

