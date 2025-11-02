"""
Script to remove duplicate reviews before adding unique constraint
Keeps the oldest review for each (shop_id, shopify_product_id, source_review_id) combination
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://saksaks:11!!!!.Magics4321@193.203.165.217:5432/sakrev_db?sslmode=disable')

def remove_duplicates():
    """Remove duplicate reviews, keeping the oldest one"""
    try:
        # Parse DATABASE_URL
        if DATABASE_URL.startswith('postgresql://'):
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
            conn = psycopg2.connect(DATABASE_URL)
        
        cursor = conn.cursor()
        
        print("Finding duplicate reviews...")
        
        # Find duplicates
        cursor.execute("""
            SELECT shop_id, shopify_product_id, source_review_id, COUNT(*) as cnt, 
                   MIN(imported_at) as oldest
            FROM reviews
            GROUP BY shop_id, shopify_product_id, source_review_id
            HAVING COUNT(*) > 1
            ORDER BY cnt DESC;
        """)
        
        duplicates = cursor.fetchall()
        print(f"Found {len(duplicates)} duplicate groups")
        
        total_deleted = 0
        
        for shop_id, shopify_product_id, source_review_id, count, oldest in duplicates:
            print(f"\nProcessing: shop_id={shop_id}, product={shopify_product_id}, review_id={source_review_id}")
            print(f"  Total duplicates: {count}, Keeping oldest: {oldest}")
            
            # Delete all except the oldest one
            cursor.execute("""
                DELETE FROM reviews
                WHERE shop_id = %s
                  AND shopify_product_id = %s
                  AND source_review_id = %s
                  AND id NOT IN (
                      SELECT id FROM reviews
                      WHERE shop_id = %s
                        AND shopify_product_id = %s
                        AND source_review_id = %s
                      ORDER BY imported_at ASC
                      LIMIT 1
                  )
            """, (shop_id, shopify_product_id, source_review_id,
                  shop_id, shopify_product_id, source_review_id))
            
            deleted = cursor.rowcount
            total_deleted += deleted
            print(f"  Deleted {deleted} duplicate(s)")
        
        conn.commit()
        print(f"\nTotal duplicates removed: {total_deleted}")
        
        # Verify no duplicates remain
        cursor.execute("""
            SELECT shop_id, shopify_product_id, source_review_id, COUNT(*) as cnt
            FROM reviews
            GROUP BY shop_id, shopify_product_id, source_review_id
            HAVING COUNT(*) > 1;
        """)
        
        remaining = cursor.fetchall()
        if remaining:
            print(f"\nWARNING: {len(remaining)} duplicate groups still exist!")
            for row in remaining:
                print(f"  {row}")
        else:
            print("\nSUCCESS: No duplicates remaining. Ready for unique constraint.")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    remove_duplicates()

