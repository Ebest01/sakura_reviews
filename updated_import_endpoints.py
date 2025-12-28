"""
Updated Import Endpoints for app_enhanced.py
============================================

Replace the simulation in app_enhanced.py with actual database storage.
"""

from flask import request, jsonify
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def create_updated_import_endpoints(app, db):
    """
    Create updated import endpoints that use database storage
    """
    
    # Initialize database integration
    from database_integration import DatabaseIntegration
    db_integration = DatabaseIntegration(db)
    
    @app.route('/admin/reviews/import/single', methods=['POST'])
    def import_single_review():
        """
        Updated: Import single review to database
        """
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
            
            # For now, use demo shop (in production, get from session/auth)
            shop_domain = "sakura-rev-test-store.myshopify.com"  # Your test store
            shop = db_integration.get_or_create_shop(shop_domain)
            
            # Check if shop can import more reviews
            if not db_integration.check_payment_status(shop.id):
                return jsonify({
                    'success': False,
                    'error': 'Review limit reached. Please upgrade your plan.'
                }), 403
            
            # Import review to database
            result = db_integration.import_single_review(
                shop_id=shop.id,
                shopify_product_id=shopify_product_id,
                review_data=review,
                source_platform=data.get('platform', 'aliexpress')
            )
            
            if result['success']:
                # Track analytics
                if session_id:
                    # Track successful import
                    logger.info(f"Review imported successfully: {result['review_id']}")
                
                return jsonify({
                    'success': True,
                    'review_id': result['review_id'],
                    'product_id': result['product_id'],
                    'shopify_product_id': shopify_product_id,
                    'imported_at': datetime.now().isoformat(),
                    'status': 'imported',
                    'quality_score': review.get('quality_score', 0),
                    'platform': review.get('platform', 'unknown'),
                    'reviews_remaining': shop.review_limit - shop.reviews_imported
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

    @app.route('/admin/reviews/import/bulk', methods=['POST'])
    def import_bulk_reviews():
        """
        Updated: Bulk import reviews to database
        """
        try:
            data = request.json
            reviews = data.get('reviews', [])
            shopify_product_id = data.get('shopify_product_id')
            session_id = data.get('session_id')
            filters = data.get('filters', {})
            
            if not reviews:
                return jsonify({
                    'success': False,
                    'error': 'No reviews provided'
                }), 400
            
            if not shopify_product_id:
                return jsonify({
                    'success': False,
                    'error': 'Shopify product ID required'
                }), 400
            
            # For now, use demo shop (in production, get from session/auth)
            shop_domain = "sakura-rev-test-store.myshopify.com"
            shop = db_integration.get_or_create_shop(shop_domain)
            
            # Check if shop can import more reviews
            if not db_integration.check_payment_status(shop.id):
                return jsonify({
                    'success': False,
                    'error': 'Review limit reached. Please upgrade your plan.'
                }), 403
            
            # Filter reviews based on criteria
            filtered_reviews = reviews
            if filters.get('min_quality_score'):
                min_score = filters['min_quality_score']
                filtered_reviews = [r for r in reviews if r.get('quality_score', 0) >= min_score]
            
            if filters.get('with_photos_only'):
                filtered_reviews = [r for r in filtered_reviews if r.get('images')]
            
            # Limit to available review slots
            available_slots = shop.review_limit - shop.reviews_imported
            reviews_to_import = filtered_reviews[:available_slots]
            
            if not reviews_to_import:
                return jsonify({
                    'success': False,
                    'error': 'No reviews meet the criteria or review limit reached'
                }), 400
            
            # Import reviews to database
            imported = []
            failed = []
            
            for review in reviews_to_import:
                try:
                    result = db_integration.import_single_review(
                        shop_id=shop.id,
                        shopify_product_id=shopify_product_id,
                        review_data=review,
                        source_platform=data.get('platform', 'aliexpress')
                    )
                    
                    if result['success']:
                        imported.append({
                            'id': review.get('id'),
                            'review_id': result['review_id'],
                            'imported_at': datetime.now().isoformat(),
                            'quality_score': review.get('quality_score'),
                            'shopify_product_id': shopify_product_id
                        })
                    else:
                        failed.append({
                            'id': review.get('id'),
                            'error': 'Database import failed'
                        })
                        
                except Exception as e:
                    logger.error(f"Failed to import review {review.get('id')}: {str(e)}")
                    failed.append({
                        'id': review.get('id'),
                        'error': str(e)
                    })
            
            # Track analytics
            if session_id and imported:
                logger.info(f"Bulk import completed: {len(imported)} imported, {len(failed)} failed")
            
            return jsonify({
                'success': True,
                'imported_count': len(imported),
                'failed_count': len(failed),
                'total_reviews': len(reviews),
                'filtered_reviews': len(filtered_reviews),
                'imported': imported,
                'failed': failed,
                'shopify_product_id': shopify_product_id,
                'reviews_remaining': shop.review_limit - shop.reviews_imported
            })
            
        except Exception as e:
            logger.error(f"Bulk import error: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Bulk import failed'
            }), 500

    @app.route('/widget/<shop_id>/reviews/<shopify_product_id>')
    def widget_reviews(shop_id, shopify_product_id):
        """
        Widget endpoint that shows product-specific reviews
        """
        try:
            # For now, use demo shop (in production, get shop by sakura_shop_id)
            shop_domain = "sakura-rev-test-store.myshopify.com"
            shop = db_integration.get_or_create_shop(shop_domain)
            
            # Check payment status (Loox-style gating)
            if not db_integration.check_payment_status(shop.id):
                return jsonify({
                    'error': 'Payment required',
                    'upgrade_url': 'https://sakura-reviews-sak-rev-test-srv.utztjw.easypanel.host/billing'
                }), 402
            
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

    @app.route('/admin/reviews/export')
    def export_reviews():
        """
        Export reviews to CSV (prevents data hostage claims)
        """
        try:
            # For now, use demo shop (in production, get from session/auth)
            shop_domain = "sakura-rev-test-store.myshopify.com"
            shop = db_integration.get_or_create_shop(shop_domain)
            
            # Get CSV data
            csv_data = db_integration.export_reviews_csv(shop.id)
            
            return jsonify({
                'success': True,
                'total_reviews': len(csv_data),
                'download_url': f'/downloads/reviews_{shop.id}.csv',
                'csv_data': csv_data  # In production, save to file and return download URL
            })
            
        except Exception as e:
            logger.error(f"Export error: {str(e)}")
            return jsonify({
                'error': 'Export failed'
            }), 500

    return {
        'import_single_review': import_single_review,
        'import_bulk_reviews': import_bulk_reviews,
        'widget_reviews': widget_reviews,
        'export_reviews': export_reviews
    }
