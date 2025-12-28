"""
ReviewKing Enhanced - WITH DATABASE INTEGRATION
===============================================

This version includes PostgreSQL database integration for product-specific reviews.
"""
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import os
import logging
from datetime import datetime
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app, supports_credentials=True, origins=["*"])

# Database configuration - Use Easypanel PostgreSQL
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://saksaks:11!!!!.Magics4321@193.203.165.217:5432/sakrev_db?sslmode=disable')
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)

# Import our database models
from backend.models_v2 import ShopOwner, Shop, Product, Review, ReviewMedia, Import, ShopSettings

# Import existing classes from app_enhanced.py
# (We'll copy the working parts and add database integration)

class DatabaseIntegration:
    """Database integration for ReviewKing"""
    
    def get_or_create_shop(self, shop_domain, access_token=None):
        """Get or create shop record"""
        shop = Shop.query.filter_by(shop_domain=shop_domain).first()
        
        if not shop:
            # Create new shop owner
            owner_email = f"owner@{shop_domain}"
            owner = ShopOwner.query.filter_by(email=owner_email).first()
            
            if not owner:
                owner = ShopOwner(email=owner_email, name=f"Owner of {shop_domain}")
                db.session.add(owner)
                db.session.flush()
            
            # Generate sakura_shop_id
            import base64
            sakura_shop_id = base64.b64encode(shop_domain.encode()).decode().replace('=', '').replace('/', '').replace('+', '')
            
            shop = Shop(
                owner_id=owner.id,
                shop_domain=shop_domain,
                access_token=access_token or "demo-token",
                sakura_shop_id=sakura_shop_id,
                shop_name=shop_domain.replace('.myshopify.com', ''),
                plan='free',
                review_limit=50
            )
            db.session.add(shop)
            db.session.commit()
            
            logger.info(f"Created new shop: {shop_domain} with sakura_shop_id: {sakura_shop_id}")
        
        return shop
    
    def get_or_create_product(self, shop_id, shopify_product_id, product_data=None):
        """Get or create product record"""
        product = Product.query.filter_by(
            shop_id=shop_id,
            shopify_product_id=shopify_product_id
        ).first()
        
        if not product:
            product = Product(
                shop_id=shop_id,
                shopify_product_id=shopify_product_id,
                shopify_product_title=product_data.get('title', '') if product_data else '',
                shopify_product_handle=product_data.get('handle', '') if product_data else '',
                shopify_product_url=product_data.get('url', '') if product_data else '',
                status='active'
            )
            db.session.add(product)
            db.session.flush()
            logger.info(f"Created new product: {shopify_product_id} for shop {shop_id}")
        
        return product
    
    def import_single_review(self, shop_id, shopify_product_id, review_data, source_platform='aliexpress'):
        """Import a single review to database"""
        # Get or create product
        product = self.get_or_create_product(shop_id, shopify_product_id)
        
        # Create review
        review = Review(
            shop_id=shop_id,
            product_id=product.id,
            source_platform=source_platform,
            source_product_id=review_data.get('source_product_id', ''),
            source_review_id=review_data.get('id', ''),
            reviewer_name=review_data.get('author', 'Anonymous'),
            rating=review_data.get('rating', 5),
            title=review_data.get('title', ''),
            body=review_data.get('text', ''),
            verified_purchase=review_data.get('verified', False),
            reviewer_country=review_data.get('country', ''),
            review_date=datetime.fromisoformat(review_data['date'].replace('Z', '+00:00')) if review_data.get('date') else None,
            quality_score=review_data.get('quality_score', 0),
            ai_recommended=review_data.get('ai_score', 0) > 8,
            status='published'
        )
        
        db.session.add(review)
        db.session.flush()
        
        # Add media files
        for image_data in review_data.get('images', []):
            media = ReviewMedia(
                review_id=review.id,
                media_type='image',
                media_url=image_data.get('url', ''),
                file_size=image_data.get('size'),
                width=image_data.get('width'),
                height=image_data.get('height'),
                status='active'
            )
            db.session.add(media)
        
        # Update shop's review count
        shop = Shop.query.get(shop_id)
        if shop:
            shop.reviews_imported += 1
        
        db.session.commit()
        
        logger.info(f"Imported review {review.id} for product {shopify_product_id}")
        
        return {
            'success': True,
            'review_id': review.id,
            'product_id': product.id,
            'shopify_product_id': shopify_product_id
        }
    
    def get_product_reviews(self, shop_id, shopify_product_id, limit=20):
        """Get reviews for a specific product"""
        # Get product
        product = Product.query.filter_by(
            shop_id=shop_id,
            shopify_product_id=shopify_product_id
        ).first()
        
        if not product:
            return []
        
        # Get reviews for this product
        reviews = Review.query.filter_by(
            shop_id=shop_id,
            product_id=product.id,
            status='published'
        ).order_by(Review.imported_at.desc()).limit(limit).all()
        
        # Convert to dict format
        result = []
        for review in reviews:
            review_data = review.to_dict()
            
            # Add media files
            media_files = ReviewMedia.query.filter_by(
                review_id=review.id,
                status='active'
            ).all()
            
            review_data['media'] = [media.to_dict() for media in media_files]
            result.append(review_data)
        
        return result

# Initialize database integration
db_integration = DatabaseIntegration()

# Copy the working parts from app_enhanced.py
# (Shopify product search, review scraping, etc.)

# Import existing Shopify helper and scraper classes
# We'll need to copy these from app_enhanced.py

# UPDATED IMPORT ENDPOINTS WITH DATABASE

@app.route('/admin/reviews/import/single', methods=['POST'])
def import_single_review():
    """Updated: Import single review to database"""
    try:
        data = request.json
        
        if not data or 'review' not in data:
            return jsonify({
                'success': False,
                'error': 'Review data required'
            }), 400
        
        review = data['review']
        shopify_product_id = data.get('shopify_product_id')
        session_id = data.get('session_id')
        
        if not shopify_product_id:
            return jsonify({
                'success': False,
                'error': 'Shopify product ID required'
            }), 400
        
        # Use demo shop for testing
        shop_domain = "sakura-rev-test-store.myshopify.com"
        shop = db_integration.get_or_create_shop(shop_domain)
        
        # Import review to database
        result = db_integration.import_single_review(
            shop_id=shop.id,
            shopify_product_id=shopify_product_id,
            review_data=review,
            source_platform=data.get('platform', 'aliexpress')
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'review_id': result['review_id'],
                'product_id': result['product_id'],
                'shopify_product_id': shopify_product_id,
                'imported_at': datetime.now().isoformat(),
                'status': 'imported',
                'quality_score': review.get('quality_score', 0),
                'platform': review.get('platform', 'unknown')
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to import review to database'
            }), 500
            
    except Exception as e:
        logger.error(f"Import single review error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Import failed'
        }), 500

@app.route('/widget/<shop_id>/reviews/<shopify_product_id>')
def widget_reviews(shop_id, shopify_product_id):
    """Widget endpoint that shows product-specific reviews"""
    try:
        # Use demo shop for testing
        shop_domain = "sakura-rev-test-store.myshopify.com"
        shop = db_integration.get_or_create_shop(shop_domain)
        
        # Get product-specific reviews
        reviews = db_integration.get_product_reviews(shop.id, shopify_product_id)
        
        return jsonify({
            'success': True,
            'reviews': reviews,
            'total': len(reviews),
            'shop_id': shop_id,
            'shopify_product_id': shopify_product_id,
            'shop_name': shop.shop_name
        })
        
    except Exception as e:
        logger.error(f"Widget error: {str(e)}")
        return jsonify({
            'error': 'Widget failed to load'
        }), 500

# Copy other working endpoints from app_enhanced.py
# (We'll add them here as needed)

@app.route('/')
def index():
    """API status"""
    return jsonify({
        'app': 'ReviewKing Enhanced with Database',
        'version': '2.0.0',
        'status': 'operational',
        'database': 'PostgreSQL',
        'features': [
            'Product-specific reviews',
            'PostgreSQL database storage',
            'Loox-style widget system',
            'Multi-platform support'
        ]
    })

@app.route('/health')
def health():
    """Health check with database"""
    try:
        # Test database connection
        shops = Shop.query.limit(1).all()
        db_status = 'healthy'
    except Exception as e:
        db_status = f'unhealthy: {str(e)}'
    
    return jsonify({
        'status': 'healthy' if db_status == 'healthy' else 'degraded',
        'database': db_status,
        'timestamp': datetime.utcnow().isoformat()
    })

if __name__ == '__main__':
    print("🚀 Starting ReviewKing Enhanced with this Database...")
    print(f"Database: {DATABASE_URL}")
    
    # Create tables if they don't exist
    with app.app_context():
        try:
            db.create_all()
            print("✅ Database tables ready")
        except Exception as e:
            print(f"❌ Database error: {e}")
            print("Please run: python setup_database.py")
    
    port = int(os.environ.get('PORT', 5001))  # Use 5001 to avoid cache issues
    
    print("\n" + "=" * 70)
    print(f"🌸 SAKURA REVIEWS - Running on port {port}")
    print("=" * 70)
    print("\n📌 BOOKMARKLET URL:")
    print(f"javascript:(function(){{var s=document.createElement('script');s.src='http://localhost:{port}/js/bookmarklet.js?v='+Date.now();document.head.appendChild(s);}})();")
    print("\n" + "=" * 70)
    print()
    
    app.run(debug=True, host='0.0.0.0', port=port)

