"""
Migration script to add unique constraint for duplicate prevention
Run this once to update your existing database schema
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://saksaks:11!!!!.Magics4321@193.203.165.217:5432/sakrev_db?sslmode=disable')

def add_unique_constraint():
    """Add unique constraint for duplicate prevention"""
    try:
        # Parse DATABASE_URL
        if DATABASE_URL.startswith('postgresql://'):
            # Remove postgresql:// prefix and parse
            url_parts = DATABASE_URL.replace('postgresql://', '').split('@')
            auth = url_parts[0].split(':')
            host_db = url_parts[1].split('/')
            host_port = host_db[0].split(':')
            
            conn = psycopg2.connect(
                host=host_port[0],
                port=int(host_port[1]) if len(host_port) > 1 else 5432,
                database=host_db[1].split('?')[0],
                user=auth[0],
                password=auth[1]
            )
        else:
            # Direct connection string
            conn = psycopg2.connect(DATABASE_URL)
        
        cursor = conn.cursor()
        
        print("Adding unique constraint for duplicate prevention...")
        
        # Drop constraint if it exists (for re-running migration)
        cursor.execute("""
            ALTER TABLE reviews 
            DROP CONSTRAINT IF EXISTS uq_shop_product_review;
        """)
        
        # Create unique constraint
        cursor.execute("""
            ALTER TABLE reviews 
            ADD CONSTRAINT uq_shop_product_review 
            UNIQUE (shop_id, shopify_product_id, source_review_id);
        """)
        
        # Create index for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_shop_product_review_unique 
            ON reviews (shop_id, shopify_product_id, source_review_id);
        """)
        
        conn.commit()
        print("SUCCESS: Unique constraint added successfully!")
        
        # Verify constraint exists
        cursor.execute("""
            SELECT constraint_name, constraint_type 
            FROM information_schema.table_constraints 
            WHERE table_name = 'reviews' 
            AND constraint_name = 'uq_shop_product_review';
        """)
        
        result = cursor.fetchone()
        if result:
            print(f"SUCCESS: Constraint verified: {result[0]} ({result[1]})")
        else:
            print("WARNING: Constraint not found after creation")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    add_unique_constraint()

