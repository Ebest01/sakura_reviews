"""Add owner_id column to shops table if it doesn't exist"""
import psycopg2

conn = psycopg2.connect('postgresql://saksaks:11!!!!.Magics4321@193.203.165.217:5432/sakrev_db?sslmode=disable')
cur = conn.cursor()

# Check if owner_id exists
cur.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'shops' AND column_name = 'owner_id';
""")

if cur.fetchone():
    print("[OK] owner_id column already exists")
else:
    print("[X] Adding owner_id column...")
    
    # First check if shop_owners table exists
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'shop_owners'
        );
    """)
    
    shop_owners_exists = cur.fetchone()[0]
    
    if not shop_owners_exists:
        print("[X] shop_owners table doesn't exist - creating it first...")
        cur.execute("""
            CREATE TABLE shop_owners (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                name VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        print("[OK] shop_owners table created")
    
    # Add owner_id column (nullable for now, we'll set default later)
    cur.execute("""
        ALTER TABLE shops 
        ADD COLUMN owner_id INTEGER;
    """)
    
    conn.commit()
    print("[OK] owner_id column added to shops table")
    
    # Set a default owner_id for existing shops (create a default owner)
    cur.execute("""
        INSERT INTO shop_owners (email, name) 
        VALUES ('default@shop.com', 'Default Owner')
        ON CONFLICT (email) DO NOTHING
        RETURNING id;
    """)
    
    default_owner = cur.fetchone()
    if default_owner:
        default_owner_id = default_owner[0]
        cur.execute("""
            UPDATE shops 
            SET owner_id = %s 
            WHERE owner_id IS NULL;
        """, (default_owner_id,))
        conn.commit()
        print(f"[OK] Set default owner_id ({default_owner_id}) for existing shops")
    
    # Now make it NOT NULL and add foreign key
    cur.execute("""
        ALTER TABLE shops 
        ALTER COLUMN owner_id SET NOT NULL,
        ADD CONSTRAINT fk_shops_owner 
        FOREIGN KEY (owner_id) REFERENCES shop_owners(id);
    """)
    
    conn.commit()
    print("[OK] owner_id set as NOT NULL with foreign key constraint")

cur.close()
conn.close()
print("\nDone! shops table should now have owner_id column.")

