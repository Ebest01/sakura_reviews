"""Test inserting a review with the exact JSON provided"""
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from backend.models_v2 import db
from database_integration import DatabaseIntegration
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment
from dotenv import load_dotenv
load_dotenv('env_local.txt')

# Create Flask app and initialize database
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Test data - exact JSON from user
test_data = {
    "review": {
        "ai_recommended": False,
        "country": "US",
        "date": "2025-11-01",
        "helpful_count": 0,
        "id": 60093073062792024,
        "images": [],
        "platform": "aliexpress",
        "position": 33,
        "product_id": "1005006661162689",
        "quality_score": 6,
        "rating": 100,
        "reviewer_name": "U***r",
        "sentiment_score": 0.5,
        "text": "I've always wanted one but never got myself it until I seen the price of it and figured why not. There nice to have when you need something sealed back up, also double feature of cutting it too. Magnet was a plus! ",
        "translation": "I've always wanted one but never got myself it until i seen the price of it and figured why not. There nice to have when you need something sealed back up, also double feature of cutting it too. Magnet was a plus!",
        "verified": True
    },
    "shopify_product_id": "10045740187962",
    "session_id": "0rrve68rf"
}

def test_insert():
    print("\n" + "="*60)
    print("TESTING REVIEW INSERT")
    print("="*60)
    
    with app.app_context():
        # Initialize database integration
        db_integration = DatabaseIntegration(db)
        
        # Use demo shop domain
        shop_domain = "sakura-rev-test-store.myshopify.com"
        
        try:
            print(f"\n1. Getting/creating shop: {shop_domain}")
            shop = db_integration.get_or_create_shop(shop_domain)
            print(f"   Shop ID: {shop.id}")
            print(f"   Shop Domain: {shop.shop_domain}")
            
            print(f"\n2. Extracting review data...")
            review_data = test_data["review"]
            shopify_product_id = test_data["shopify_product_id"]
            
            print(f"   Shopify Product ID: {shopify_product_id}")
            print(f"   Review ID (source): {review_data['id']}")
            print(f"   Reviewer: {review_data['reviewer_name']}")
            print(f"   Rating: {review_data['rating']}")
            
            print(f"\n3. Calling import_single_review...")
            result = db_integration.import_single_review(
                shop_id=shop.id,
                shopify_product_id=shopify_product_id,
                review_data=review_data,
                source_platform=review_data.get('platform', 'aliexpress')
            )
            
            print(f"\n" + "="*60)
            print("SUCCESS!")
            print("="*60)
            print(f"Database Review ID: {result['review_id']}")
            print(f"Database Product ID: {result['product_id']}")
            print(f"Shopify Product ID: {result['shopify_product_id']}")
            print(f"\nReview successfully saved to database!")
            
            # Verify in database
            print(f"\n4. Verifying in database...")
            from backend.models_v2 import Review
            saved_review = Review.query.get(result['review_id'])
            if saved_review:
                print(f"   Found review in DB:")
                print(f"   - ID: {saved_review.id}")
                print(f"   - Reviewer: {saved_review.reviewer_name}")
                print(f"   - Rating: {saved_review.rating}")
                print(f"   - Body length: {len(saved_review.body) if saved_review.body else 0} chars")
                print(f"   - Shopify Product ID: {saved_review.shopify_product_id}")
                print(f"   - Source Review ID: {saved_review.source_review_id}")
            
        except Exception as e:
            print(f"\n" + "="*60)
            print("ERROR!")
            print("="*60)
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            import traceback
            print(f"\nFull traceback:")
            print(traceback.format_exc())
            return False
    
    return True

if __name__ == "__main__":
    success = test_insert()
    sys.exit(0 if success else 1)

