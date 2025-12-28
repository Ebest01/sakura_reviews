"""
Sakura Reviews - Loox-Style Widget System v2.0
==============================================

Proper implementation following Loox's strategy:
- Store reviews in OUR database (not Shopify)
- Use sakura_shop_id like Loox uses LOOX_FALLBACK_ID
- Hide reviews if payment stops
- Allow CSV export
"""
from flask import Flask, render_template, request, jsonify
import os
import hashlib
import hmac
import time
from datetime import datetime
import json

# Import our proper models
from backend.models_v2 import db, Shop, Product, Review, ReviewMedia, ShopOwner

app = Flask(__name__)

# Configuration
WIDGET_BASE_URL = "https://sakura-reviews-sak-rev-test-srv.utztjw.easypanel.host/widget"
SHOPIFY_APP_URL = "https://sakura-reviews-sak-rev-test-srv.utztjw.easypanel.host"

class SakuraWidgetSystem:
    """
    Loox-style widget system with proper schema
    """
    
    def __init__(self):
        self.widget_cache = {}
        self.analytics = {}
    
    def generate_widget_url(self, sakura_shop_id, shopify_product_id, theme="default", limit=20):
        """
        Generate widget URL like Loox does with LOOX_FALLBACK_ID
        sakura_shop_id = equivalent to Loox's LOOX_FALLBACK_ID
        """
        timestamp = int(time.time())
        version = "2.0.0"
        
        # Create secure hash for validation
        payload = f"{sakura_shop_id}:{shopify_product_id}:{timestamp}:{version}"
        signature = hmac.new(
            os.getenv('WIDGET_SECRET', 'sakura-secret-key').encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        widget_url = f"{WIDGET_BASE_URL}/{sakura_shop_id}/reviews/{shopify_product_id}"
        params = {
            'v': version,
            't': timestamp,
            's': signature,
            'theme': theme,
            'limit': limit,
            'platform': 'shopify'
        }
        
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"{widget_url}?{query_string}"
    
    def create_shopify_app_block(self, sakura_shop_id, shopify_product_id):
        """
        Create Shopify app block HTML
        """
        widget_url = self.generate_widget_url(sakura_shop_id, shopify_product_id)
        
        return f"""
        <!-- Sakura Reviews Widget - Superior to Loox -->
        <section id="sakura-reviews-section" class="sakura-reviews-widget">
            <div class="sakura-reviews-container">
                <iframe 
                    id="sakuraReviewsFrame"
                    src="{widget_url}"
                    width="100%"
                    height="auto"
                    frameborder="0"
                    scrolling="no"
                    style="border: none; overflow: hidden; min-height: 400px;"
                    title="Sakura Reviews Widget"
                    loading="lazy"
                >
                    <p>Loading reviews...</p>
                </iframe>
            </div>
        </section>
        
        <style>
        .sakura-reviews-widget {{
            margin: 20px 0;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }}
        
        .sakura-reviews-container {{
            position: relative;
            background: white;
        }}
        
        #sakuraReviewsFrame {{
            display: block;
            width: 100%;
            border: none;
        }}
        </style>
        
        <script>
        // Auto-resize iframe based on content
        window.addEventListener('message', function(event) {{
            if (event.origin !== '{WIDGET_BASE_URL}') return;
            
            if (event.data.type === 'resize') {{
                const iframe = document.getElementById('sakuraReviewsFrame');
                iframe.style.height = event.data.height + 'px';
            }}
        }});
        </script>
        """

# Widget Routes
@app.route('/widget/<sakura_shop_id>/reviews/<shopify_product_id>')
def widget_reviews(sakura_shop_id, shopify_product_id):
    """
    Main widget endpoint - Loox style with payment gating
    """
    # Validate request
    signature = request.args.get('s')
    timestamp = request.args.get('t')
    version = request.args.get('v')
    theme = request.args.get('theme', 'default')
    limit = int(request.args.get('limit', 20))
    
    # Get shop by sakura_shop_id (like Loox uses LOOX_FALLBACK_ID)
    shop = Shop.query.filter_by(sakura_shop_id=sakura_shop_id).first()
    
    if not shop:
        return render_template('widget_error.html', 
                             error='Shop not found')
    
    # Check payment status (Loox-style gating)
    if not shop.is_payment_active():
        return render_template('widget_payment_required.html', 
                             shop_id=sakura_shop_id,
                             shop_name=shop.shop_name,
                             upgrade_url=f"{SHOPIFY_APP_URL}/billing")
    
    # Get product-specific reviews from OUR database
    reviews = get_product_reviews(shop.id, shopify_product_id, limit)
    
    # Render widget
    return render_template('widget_v2.html', 
                         sakura_shop_id=sakura_shop_id,
                         shopify_product_id=shopify_product_id,
                         shop_name=shop.shop_name,
                         reviews=reviews,
                         theme=theme,
                         version=version)

@app.route('/widget/<sakura_shop_id>/reviews/<shopify_product_id>/api')
def widget_api(sakura_shop_id, shopify_product_id):
    """
    API endpoint for widget data
    """
    # Get shop by sakura_shop_id
    shop = Shop.query.filter_by(sakura_shop_id=sakura_shop_id).first()
    
    if not shop:
        return jsonify({'error': 'Shop not found'}), 404
    
    # Check payment status
    if not shop.is_payment_active():
        return jsonify({
            'error': 'Payment required',
            'upgrade_url': f"{SHOPIFY_APP_URL}/billing"
        }), 402
    
    reviews = get_product_reviews(shop.id, shopify_product_id)
    
    return jsonify({
        'success': True,
        'reviews': reviews,
        'total': len(reviews),
        'sakura_shop_id': sakura_shop_id,
        'shopify_product_id': shopify_product_id,
        'shop_name': shop.shop_name
    })

def get_product_reviews(shop_id, shopify_product_id, limit=20):
    """
    Get reviews for a specific product from OUR database (Loox style)
    """
    # Get product first
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
    
    # Convert to dict format with media
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

# Import Routes (for bookmarklet)
@app.route('/admin/reviews/import/single', methods=['POST'])
def import_single_review():
    """
    Import single review to OUR database (Loox style)
    """
    data = request.json
    
    # Get shop by sakura_shop_id
    shop = Shop.query.filter_by(sakura_shop_id=data['sakura_shop_id']).first()
    
    if not shop:
        return jsonify({'error': 'Shop not found'}), 404
    
    # Check if shop can import more reviews
    if not shop.can_import_reviews():
        return jsonify({'error': 'Review limit reached'}), 403
    
    # Get or create product
    product = Product.query.filter_by(
        shop_id=shop.id,
        shopify_product_id=data['shopify_product_id']
    ).first()
    
    if not product:
        product = Product(
            shop_id=shop.id,
            shopify_product_id=data['shopify_product_id'],
            shopify_product_title=data.get('product_title', ''),
            source_platform=data['platform'],
            source_product_id=data.get('source_product_id', ''),
            status='active'
        )
        db.session.add(product)
        db.session.flush()  # Get product.id
    
    # Create review
    review = Review(
        shop_id=shop.id,
        product_id=product.id,
        source_platform=data['platform'],
        source_product_id=data.get('source_product_id', ''),
        source_review_id=data['review']['source_review_id'],
        reviewer_name=data['review']['author'],
        rating=data['review']['rating'],
        title=data['review'].get('title', ''),
        body=data['review']['text'],
        verified_purchase=data['review'].get('verified', False),
        reviewer_country=data['review'].get('country', ''),
        review_date=datetime.fromisoformat(data['review']['date']) if data['review'].get('date') else None,
        quality_score=data['review'].get('ai_score', 0),
        ai_recommended=data['review'].get('ai_score', 0) > 8,
        status='published' if shop.settings.auto_publish else 'pending'
    )
    
    db.session.add(review)
    db.session.flush()  # Get review.id
    
    # Add media files
    for media_data in data['review'].get('images', []):
        media = ReviewMedia(
            review_id=review.id,
            media_type='image',
            media_url=media_data['url'],
            file_size=media_data.get('size'),
            width=media_data.get('width'),
            height=media_data.get('height'),
            status='active'
        )
        db.session.add(media)
    
    # Update shop's review count
    shop.reviews_imported += 1
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'review_id': review.id,
        'product_id': product.id,
        'reviews_remaining': shop.review_limit - shop.reviews_imported
    })

# CSV Export (prevent data hostage claims)
@app.route('/admin/reviews/export/<sakura_shop_id>')
def export_reviews(sakura_shop_id):
    """
    Export all reviews to CSV (Loox style - prevents data hostage)
    """
    shop = Shop.query.filter_by(sakura_shop_id=sakura_shop_id).first()
    
    if not shop:
        return jsonify({'error': 'Shop not found'}), 404
    
    # Get all reviews for this shop
    reviews = Review.query.filter_by(shop_id=shop.id).all()
    
    # Create CSV data
    csv_data = []
    for review in reviews:
        product = Product.query.get(review.product_id)
        
        csv_data.append({
            'Review ID': review.id,
            'Product ID': review.shopify_product_id,
            'Product Title': product.shopify_product_title if product else '',
            'Reviewer Name': review.reviewer_name,
            'Rating': review.rating,
            'Review Title': review.title,
            'Review Text': review.body,
            'Source Platform': review.source_platform,
            'Verified Purchase': review.verified_purchase,
            'Reviewer Country': review.reviewer_country,
            'Review Date': review.review_date.strftime('%Y-%m-%d') if review.review_date else '',
            'AI Quality Score': review.quality_score,
            'AI Recommended': review.ai_recommended,
            'Import Date': review.imported_at.strftime('%Y-%m-%d'),
            'Status': review.status
        })
    
    return jsonify({
        'success': True,
        'total_reviews': len(csv_data),
        'download_url': f'/downloads/reviews_{shop.id}.csv',
        'csv_data': csv_data  # In production, save to file and return download URL
    })

# JavaScript injection (ScriptTag)
@app.route('/js/sakura-reviews.js')
def sakura_reviews_js():
    """
    JavaScript file for ScriptTag injection (Loox style)
    """
    js_content = f"""
(function() {{
    // Prevent multiple injections
    if (window.sakuraReviewsLoaded) return;
    window.sakuraReviewsLoaded = true;
    
    console.log('🌸 Sakura Reviews: Loading widget system...');
    
    // Get current page info
    const shopDomain = window.Shopify?.shop || window.location.hostname;
    const productId = window.Shopify?.product?.id || 
                     new URLSearchParams(window.location.search).get('id') ||
                     document.querySelector('[data-product-id]')?.dataset.productId;
    
    if (!productId) {{
        console.log('🌸 Sakura Reviews: No product ID found, skipping');
        return;
    }}
    
    // Generate sakura_shop_id (equivalent to Loox's LOOX_FALLBACK_ID)
    const sakuraShopId = btoa(shopDomain).replace(/[^a-zA-Z0-9]/g, '');
    
    // Create widget iframe
    const widgetUrl = `{WIDGET_BASE_URL}/${{sakuraShopId}}/reviews/${{productId}}?theme=default&limit=20&v=2.0.0&t=${{Date.now()}}`;
    
    const widgetHTML = `
        <div id="sakura-reviews-widget" style="margin: 20px 0; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
            <iframe 
                id="sakuraReviewsFrame"
                src="${{widgetUrl}}"
                width="100%"
                height="400"
                frameborder="0"
                scrolling="no"
                style="border: none; overflow: hidden;"
                title="Sakura Reviews Widget"
                loading="lazy"
            >
                <p>Loading reviews...</p>
            </iframe>
        </div>
    `;
    
    // Find insertion point
    const insertionPoints = [
        document.querySelector('.product-form'),
        document.querySelector('.product-single'),
        document.querySelector('#MainContent'),
        document.querySelector('.product'),
        document.querySelector('main')
    ];
    
    let insertionPoint = null;
    for (const point of insertionPoints) {{
        if (point) {{
            insertionPoint = point;
            break;
        }}
    }}
    
    if (insertionPoint) {{
        // Insert after the element
        insertionPoint.insertAdjacentHTML('afterend', widgetHTML);
        console.log('🌸 Sakura Reviews: Widget injected successfully via ScriptTag');
    }} else {{
        console.log('🌸 Sakura Reviews: No suitable insertion point found');
    }}
    
    // Auto-resize iframe
    window.addEventListener('message', function(event) {{
        if (event.origin !== '{WIDGET_BASE_URL}') return;
        
        if (event.data.type === 'resize') {{
            const iframe = document.getElementById('sakuraReviewsFrame');
            if (iframe) {{
                iframe.style.height = event.data.height + 'px';
            }}
        }}
    }});
}})();
"""
    
    return js_content, 200, {'Content-Type': 'application/javascript'}

if __name__ == '__main__':
    app.run(debug=True, port=5001)
