#!/usr/bin/env python3
"""
Simple Widget Endpoint for Product Reviews
Queries reviews directly from Easypanel PostgreSQL database
Can be integrated into backend/app.py or used standalone
"""
from flask import Flask, jsonify, render_template_string, request
import psycopg2
import json
from datetime import datetime

# Database connection details
DB_CONFIG = {
    'host': '193.203.165.217',
    'port': 5432,
    'database': 'sakrev_db',
    'user': 'saksaks',
    'password': '11!!!!.Magics4321'
}

def get_db_connection():
    """Get PostgreSQL database connection"""
    return psycopg2.connect(**DB_CONFIG)

def get_product_reviews_from_db(shopify_product_id: str, limit: int = 20):
    """
    Get reviews for a specific product from database
    
    Args:
        shopify_product_id: Shopify product ID (string)
        limit: Maximum number of reviews to return
    
    Returns:
        List of review dictionaries
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT 
                id, reviewer_name, rating, title, body,
                reviewer_country, verified_purchase, quality_score,
                ai_recommended, review_date, imported_at,
                images, shop_id
            FROM reviews 
            WHERE shopify_product_id = %s
            AND status = 'published'
            AND published = true
            ORDER BY imported_at DESC
            LIMIT %s;
        """, (shopify_product_id, limit))
        
        reviews = cursor.fetchall()
        
        result = []
        for review in reviews:
            (rev_id, name, rating, title, body, country, verified,
             quality, ai_rec, review_date, imported_at, images_json, shop_id) = review
            
            # Parse images JSON
            images = []
            if images_json:
                try:
                    images = json.loads(images_json) if isinstance(images_json, str) else images_json
                except:
                    images = []
            
            result.append({
                'id': rev_id,
                'reviewer_name': name or 'Anonymous',
                'rating': rating,
                'title': title or '',
                'body': body or '',
                'reviewer_country': country or '',
                'verified_purchase': verified or False,
                'quality_score': float(quality) if quality else 0.0,
                'ai_recommended': ai_rec or False,
                'review_date': review_date.isoformat() if review_date else None,
                'imported_at': imported_at.isoformat() if imported_at else None,
                'images': images,
                'shop_id': shop_id
            })
        
        return result
        
    except Exception as e:
        print(f"Error fetching reviews: {e}")
        return []
        
    finally:
        cursor.close()
        conn.close()

# Widget HTML template
WIDGET_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Product Reviews - {{ product_id }}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }
        .widget-container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .widget-header {
            border-bottom: 2px solid #f0f0f0;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        .widget-header h2 {
            color: #333;
            font-size: 28px;
            margin-bottom: 10px;
        }
        .review-count {
            color: #666;
            font-size: 14px;
        }
        .reviews-list {
            display: grid;
            gap: 20px;
        }
        .review-item {
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 20px;
            background: #fafafa;
        }
        .review-header {
            display: flex;
            justify-content: space-between;
            align-items: start;
            margin-bottom: 15px;
        }
        .reviewer-info {
            flex: 1;
        }
        .reviewer-name {
            font-weight: 600;
            color: #333;
            margin-bottom: 5px;
        }
        .review-meta {
            font-size: 12px;
            color: #999;
        }
        .rating {
            color: #ffa500;
            font-size: 20px;
        }
        .review-title {
            font-weight: 600;
            color: #333;
            margin-bottom: 10px;
            font-size: 16px;
        }
        .review-body {
            color: #666;
            line-height: 1.6;
            margin-bottom: 15px;
        }
        .review-images {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
            gap: 10px;
            margin-top: 15px;
        }
        .review-image {
            width: 100%;
            height: 100px;
            object-fit: cover;
            border-radius: 4px;
            cursor: pointer;
        }
        .badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            margin-left: 5px;
        }
        .badge-verified {
            background: #4caf50;
            color: white;
        }
        .badge-ai {
            background: #ff69b4;
            color: white;
        }
        .no-reviews {
            text-align: center;
            padding: 40px;
            color: #999;
        }
        .stats {
            display: flex;
            gap: 20px;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
        }
        .stat-item {
            text-align: center;
        }
        .stat-value {
            font-size: 24px;
            font-weight: 600;
            color: #333;
        }
        .stat-label {
            font-size: 12px;
            color: #999;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="widget-container">
        <div class="widget-header">
            <h2>Product Reviews</h2>
            <div class="review-count">{{ review_count }} Review(s)</div>
        </div>
        
        {% if reviews %}
            <div class="reviews-list">
                {% for review in reviews %}
                <div class="review-item">
                    <div class="review-header">
                        <div class="reviewer-info">
                            <div class="reviewer-name">
                                {{ review.reviewer_name }}
                                {% if review.verified_purchase %}
                                <span class="badge badge-verified">Verified</span>
                                {% endif %}
                                {% if review.ai_recommended %}
                                <span class="badge badge-ai">AI Recommended</span>
                                {% endif %}
                            </div>
                            <div class="review-meta">
                                {% if review.reviewer_country %}{{ review.reviewer_country }} • {% endif %}
                                {{ review.review_date[:10] if review.review_date else review.imported_at[:10] }}
                                {% if review.quality_score %}• Quality: {{ "%.1f"|format(review.quality_score) }}/10{% endif %}
                            </div>
                        </div>
                        <div class="rating">{{ "★" * review.rating }}{{ "☆" * (5 - review.rating) }}</div>
                    </div>
                    {% if review.title %}
                    <div class="review-title">{{ review.title }}</div>
                    {% endif %}
                    <div class="review-body">{{ review.body }}</div>
                    {% if review.images %}
                    <div class="review-images">
                        {% for image in review.images %}
                        <img src="{{ image }}" alt="Review photo" class="review-image" onclick="window.open('{{ image }}', '_blank')">
                        {% endfor %}
                    </div>
                    {% endif %}
                </div>
                {% endfor %}
            </div>
            
            {% if stats %}
            <div class="stats">
                <div class="stat-item">
                    <div class="stat-value">{{ stats.avg_rating }}</div>
                    <div class="stat-label">Average Rating</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{{ stats.verified_count }}</div>
                    <div class="stat-label">Verified</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{{ stats.with_images }}</div>
                    <div class="stat-label">With Photos</div>
                </div>
            </div>
            {% endif %}
        {% else %}
            <div class="no-reviews">
                <p>No reviews yet for this product.</p>
            </div>
        {% endif %}
    </div>
</body>
</html>
"""

def create_widget_endpoint(app):
    """
    Add widget endpoint to Flask app
    
    Usage:
        from widget_endpoint_simple import create_widget_endpoint
        create_widget_endpoint(app)
    """
    
    @app.route('/widget/demo-shop/reviews/<shopify_product_id>')
    def widget_reviews(shopify_product_id):
        """
        Widget endpoint to display reviews for a product
        URL format: /widget/demo-shop/reviews/{shopify_product_id}
        """
        limit = int(request.args.get('limit', 20))
        
        # Get reviews from database
        reviews = get_product_reviews_from_db(shopify_product_id, limit)
        
        # Calculate statistics
        stats = None
        if reviews:
            avg_rating = sum(r['rating'] for r in reviews) / len(reviews)
            verified_count = sum(1 for r in reviews if r['verified_purchase'])
            with_images = sum(1 for r in reviews if r.get('images'))
            
            stats = {
                'avg_rating': f"{avg_rating:.1f}",
                'verified_count': verified_count,
                'with_images': with_images
            }
        
        # Render widget
        return render_template_string(
            WIDGET_TEMPLATE,
            product_id=shopify_product_id,
            reviews=reviews,
            review_count=len(reviews),
            stats=stats
        )
    
    @app.route('/widget/demo-shop/reviews/<shopify_product_id>/api')
    def widget_api(shopify_product_id):
        """
        Widget API endpoint (JSON)
        URL format: /widget/demo-shop/reviews/{shopify_product_id}/api
        """
        limit = int(request.args.get('limit', 20))
        
        reviews = get_product_reviews_from_db(shopify_product_id, limit)
        
        return jsonify({
            'success': True,
            'product_id': shopify_product_id,
            'reviews': reviews,
            'total': len(reviews)
        })
    
    print("Widget endpoints registered:")
    print("  - GET /widget/demo-shop/reviews/<product_id> (HTML)")
    print("  - GET /widget/demo-shop/reviews/<product_id>/api (JSON)")

if __name__ == "__main__":
    # Standalone test server
    from flask import Flask, request
    
    app = Flask(__name__)
    create_widget_endpoint(app)
    
    print("Starting test widget server...")
    print("Access widget at: http://localhost:5000/widget/demo-shop/reviews/PRODUCT_ID")
    app.run(host='0.0.0.0', port=5000, debug=True)

