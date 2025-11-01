"""Create review_media table if it doesn't exist"""
import psycopg2

conn = psycopg2.connect('postgresql://saksaks:11!!!!.Magics4321@193.203.165.217:5432/sakrev_db?sslmode=disable')
cur = conn.cursor()

print("\n" + "="*60)
print("CREATING review_media TABLE")
print("="*60)

# Check if table exists
cur.execute("""
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_name = 'review_media'
    );
""")

table_exists = cur.fetchone()[0]

if table_exists:
    print("[OK] review_media table already exists")
else:
    print("[X] Creating review_media table...")
    
    cur.execute("""
        CREATE TABLE review_media (
            id SERIAL PRIMARY KEY,
            review_id INTEGER NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
            media_type VARCHAR(50) NOT NULL DEFAULT 'image',
            media_url TEXT NOT NULL,
            media_thumbnail TEXT,
            file_size INTEGER,
            width INTEGER,
            height INTEGER,
            duration INTEGER,
            status VARCHAR(50) DEFAULT 'active',
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # Create indexes
    cur.execute("CREATE INDEX idx_review_media_review_id ON review_media(review_id);")
    cur.execute("CREATE INDEX idx_review_media_status ON review_media(status);")
    
    conn.commit()
    print("[OK] review_media table created with indexes")

# Verify table structure
print("\nVerifying table structure:")
cur.execute("""
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'review_media'
    ORDER BY ordinal_position;
""")
columns = cur.fetchall()
for col in columns:
    nullable = "NULL" if col[2] == 'YES' else "NOT NULL"
    print(f"  {col[0]:<20} {col[1]:<20} {nullable}")

cur.close()
conn.close()
print("\nDone!")

