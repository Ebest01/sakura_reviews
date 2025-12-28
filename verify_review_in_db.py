"""
Verify if review was saved to database for a Shopify product ID
"""
import psycopg2
import os

# Read DATABASE_URL from env_local.txt or environment
DB_URL = os.environ.get('DATABASE_URL')
if not DB_URL:
    # Try reading from env_local.txt
    try:
        with open('env_local.txt', 'r') as f:
            for line in f:
                if line.startswith('DATABASE_URL='):
                    DB_URL = line.split('=', 1)[1].strip()
                    break
    except:
        pass

if not DB_URL:
    DB_URL = 'postgresql://saksaks:11!!!!.Magics4321@193.203.165.217:5432/sakrev_db?sslmode=disable'

def verify_review(shopify_product_id):
    """Verify review exists in database"""
    try:
        # Parse DATABASE_URL
        # Format: postgresql://user:pass@host:port/dbname
        url_parts = DB_URL.replace('postgresql://', '').split('@')
        user_pass = url_parts[0].split(':')
        host_db = url_parts[1].split('/')
        host_port = host_db[0].split(':')
        
        conn = psycopg2.connect(
            host=host_port[0],
            port=int(host_port[1]) if len(host_port) > 1 else 5432,
            database=host_db[1].split('?')[0],
            user=user_pass[0],
            password=user_pass[1]
        )
        
        cursor = conn.cursor()
        
        # First, check if product exists
        print(f"\n[CHECK] Checking for product: {shopify_product_id}")
        cursor.execute("""
            SELECT id, shopify_product_id, shopify_product_title 
            FROM products 
            WHERE shopify_product_id = %s
        """, (shopify_product_id,))
        
        product = cursor.fetchone()
        if not product:
            print(f"[ERROR] Product NOT found in database!")
            print(f"   Shopify Product ID: {shopify_product_id}")
            return
        
        product_id = product[0]
        print(f"[OK] Product found!")
        print(f"   Product ID: {product_id}")
        print(f"   Shopify Product ID: {product[1]}")
        print(f"   Title: {product[2]}")
        
        # Now check reviews for this product
        print(f"\n[CHECK] Checking reviews for product_id: {product_id}")
        cursor.execute("""
            SELECT 
                r.id, 
                r.reviewer_name, 
                r.rating, 
                r.body, 
                r.created_at,
                r.shopify_product_id
            FROM reviews r
            WHERE r.product_id = %s
            ORDER BY r.created_at DESC
            LIMIT 10
        """, (product_id,))
        
        reviews = cursor.fetchall()
        
        if not reviews:
            print(f"[ERROR] NO reviews found for this product!")
            print(f"   Checked product_id: {product_id}")
        else:
            print(f"[OK] Found {len(reviews)} review(s):")
            for review in reviews:
                print(f"\n   Review ID: {review[0]}")
                print(f"   Author: {review[1]}")
                print(f"   Rating: {review[2]}/5")
                print(f"   Text: {review[3][:100]}..." if len(review[3]) > 100 else f"   Text: {review[3]}")
                print(f"   Created: {review[4]}")
                print(f"   Shopify Product ID (in review): {review[5]}")
        
        # Also check directly by shopify_product_id in reviews table (if it exists)
        print(f"\n[CHECK] Also checking reviews table directly for shopify_product_id: {shopify_product_id}")
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'reviews' 
            AND column_name = 'shopify_product_id'
        """)
        has_shopify_col = cursor.fetchone()
        
        if has_shopify_col:
            cursor.execute("""
                SELECT id, reviewer_name, rating, body, created_at
                FROM reviews
                WHERE shopify_product_id = %s
                ORDER BY created_at DESC
                LIMIT 10
            """, (shopify_product_id,))
            
            direct_reviews = cursor.fetchall()
            if direct_reviews:
                print(f"[OK] Found {len(direct_reviews)} review(s) directly:")
                for review in direct_reviews:
                    print(f"   Review ID: {review[0]}, Author: {review[1]}, Rating: {review[2]}/5")
            else:
                print(f"[ERROR] No reviews found with direct shopify_product_id query")
        else:
            print(f"   [WARN] reviews table doesn't have shopify_product_id column")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    import sys
    shopify_product_id = sys.argv[1] if len(sys.argv) > 1 else '10045740122426'
    print(f"\n{'='*60}")
    print(f"Verifying Review in Database")
    print(f"{'='*60}")
    verify_review(shopify_product_id)
    print(f"\n{'='*60}\n")

