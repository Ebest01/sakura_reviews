"""Get shop_id and sakura_shop_id for widget URL"""
import psycopg2

conn = psycopg2.connect('postgresql://saksaks:11!!!!.Magics4321@193.203.165.217:5432/sakrev_db?sslmode=disable')
cur = conn.cursor()

print("\n" + "="*60)
print("GETTING SHOP IDS FOR WIDGET")
print("="*60)

cur.execute("""
    SELECT id, shop_domain, sakura_shop_id
    FROM shops
    WHERE shop_domain = 'sakura-rev-test-store.myshopify.com';
""")

shop = cur.fetchone()

if shop:
    print(f"\nShop ID: {shop[0]}")
    print(f"Shop Domain: {shop[1]}")
    print(f"Sakura Shop ID: {shop[2]}")
    print(f"\nWidget URL format:")
    print(f"  /widget/{shop[0]}/reviews/10045740024122")
    print(f"  OR")
    print(f"  /widget/{shop[2]}/reviews/10045740024122")
else:
    print("\n[X] Shop not found!")

cur.close()
conn.close()

