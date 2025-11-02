"""
Database Integration for app_enhanced.py
========================================

This module provides database functions to replace the simulation
in app_enhanced.py with actual database storage.
"""
from datetime import datetime
import json
import logging
from sqlalchemy.dialects.postgresql import insert

logger = logging.getLogger(__name__)

class DatabaseIntegration:
    """
    Database integration for ReviewKing
    """
    
    def __init__(self, db):
        self.db = db
    
    def get_or_create_shop(self, shop_domain, access_token=None):
        """
        Get or create shop record
        """
        from backend.models_v2 import Shop, ShopOwner
        
        # Try to find existing shop
        shop = Shop.query.filter_by(shop_domain=shop_domain).first()
        
        if not shop:
            # Create new shop owner (for now, use email as identifier)
            owner_email = f"owner@{shop_domain}"
            owner = ShopOwner.query.filter_by(email=owner_email).first()
            
            if not owner:
                owner = ShopOwner(
                    email=owner_email,
                    name=f"Owner of {shop_domain}"
                )
                self.db.session.add(owner)
                self.db.session.flush()
            
            # Generate sakura_shop_id (like Loox's LOOX_FALLBACK_ID)
            import base64
            sakura_shop_id = base64.b64encode(shop_domain.encode()).decode().replace('=', '').replace('/', '').replace('+', '')
            
            # Create new shop
            shop = Shop(
                owner_id=owner.id,
                shop_domain=shop_domain,
                access_token=access_token or "demo-token",
                sakura_shop_id=sakura_shop_id,
                shop_name=shop_domain.replace('.myshopify.com', ''),
                plan='free',  # Default to free plan
                review_limit=50
            )
            self.db.session.add(shop)
            self.db.session.commit()
            
            logger.info(f"Created new shop: {shop_domain} with sakura_shop_id: {sakura_shop_id}")
        
        return shop
    
    def get_or_create_product(self, shop_id, shopify_product_id, product_data=None):
        """
        Get or create product record
        """
        from backend.models_v2 import Product
        
        # Try to find existing product
        product = Product.query.filter_by(
            shop_id=shop_id,
            shopify_product_id=shopify_product_id
        ).first()
        
        if not product:
            # Create new product
            product = Product(
                shop_id=shop_id,
                shopify_product_id=shopify_product_id,
                shopify_product_title=product_data.get('title', '') if product_data else '',
                shopify_product_handle=product_data.get('handle', '') if product_data else '',
                shopify_product_url=product_data.get('url', '') if product_data else '',
                status='active'
            )
            self.db.session.add(product)
            self.db.session.flush()  # Get product.id
            logger.info(f"Created new product: {shopify_product_id} for shop {shop_id}")
        
        return product
    
    def import_reviews_bulk(self, shop_id, shopify_product_id, reviews_data, source_platform='aliexpress'):
        """
        Bulk import reviews using PostgreSQL ON CONFLICT DO NOTHING
        This is MUCH faster than checking each review individually (1 query vs N queries)
        """
        from backend.models_v2 import Review, ReviewMedia, Product
        import logging
        db_logger = logging.getLogger(__name__)
        
        if not reviews_data:
            return {
                'success': True,
                'imported': 0,
                'duplicates': 0,
                'failed': 0
            }
        
        # Get or create product
        product = self.get_or_create_product(shop_id, shopify_product_id)
        db_logger.info(f"[DB BULK] Product found/created: id={product.id}, shopify_id={shopify_product_id}")
        
        # Extract AliExpress product ID if needed
        aliexpress_product_id = None
        if source_platform == 'aliexpress' and reviews_data:
            aliexpress_product_id = reviews_data[0].get('product_id', reviews_data[0].get('source_product_id', ''))
            if aliexpress_product_id and not product.aliexpress_product_id:
                product.aliexpress_product_id = aliexpress_product_id
                product.source_platform = 'aliexpress'
                product.source_product_id = aliexpress_product_id
        
        # Prepare reviews for bulk insert
        reviews_to_insert = []
        media_data_by_source_id = {}  # Store media data keyed by source_review_id
        
        for review_data in reviews_data:
            # Normalize rating
            raw_rating = review_data.get('rating', 5)
            if isinstance(raw_rating, (int, float)):
                if raw_rating > 5:
                    rating = max(1, min(5, int((raw_rating / 100) * 5)))
                else:
                    rating = max(1, min(5, int(raw_rating)))
            else:
                rating = 5
            
            # Parse date
            review_date = None
            if review_data.get('date'):
                try:
                    date_str = review_data['date']
                    if isinstance(date_str, str):
                        try:
                            review_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        except:
                            for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%d-%m-%Y']:
                                try:
                                    review_date = datetime.strptime(date_str, fmt)
                                    break
                                except:
                                    continue
                            if not review_date:
                                review_date = datetime.utcnow()
                    else:
                        review_date = datetime.utcnow()
                except:
                    review_date = datetime.utcnow()
            
            if not review_date:
                review_date = datetime.utcnow()
            
            source_review_id = str(review_data.get('id', ''))
            if not source_review_id:
                continue  # Skip reviews without ID
            
            # Store review data for bulk insert
            review_dict = {
                'shop_id': shop_id,
                'product_id': product.id,
                'shopify_product_id': shopify_product_id,
                'source_platform': source_platform,
                'source_product_id': review_data.get('product_id', review_data.get('source_product_id', '')),
                'aliexpress_product_id': aliexpress_product_id,
                'source_review_id': source_review_id,
                'reviewer_name': review_data.get('author', review_data.get('reviewer_name', 'Anonymous')),
                'rating': rating,
                'title': review_data.get('title', ''),
                'body': review_data.get('text', review_data.get('body', '')),
                'verified_purchase': review_data.get('verified', False),
                'reviewer_country': review_data.get('country', ''),
                'review_date': review_date,
                'quality_score': review_data.get('quality_score', 0),
                'ai_recommended': review_data.get('ai_recommended', review_data.get('ai_score', 0) > 8),
                'status': 'published',
                'imported_at': datetime.utcnow()
            }
            
            reviews_to_insert.append(review_dict)
            
            # Store media data for later insertion (after we know which reviews were actually inserted)
            images = review_data.get('images', [])
            if images:
                media_list = []
                for img in images:
                    if isinstance(img, str):
                        media_list.append({
                            'url': img,
                            'size': None,
                            'width': None,
                            'height': None
                        })
                    elif isinstance(img, dict):
                        media_list.append({
                            'url': img.get('url', ''),
                            'size': img.get('size'),
                            'width': img.get('width'),
                            'height': img.get('height')
                        })
                media_data_by_source_id[source_review_id] = media_list
        
        if not reviews_to_insert:
            return {
                'success': True,
                'imported': 0,
                'duplicates': 0,
                'failed': len(reviews_data)
            }
        
        try:
            # Bulk insert with ON CONFLICT DO NOTHING
            # Uses the unique constraint: uq_shop_product_review (shop_id, shopify_product_id, source_review_id)
            stmt = insert(Review).values(reviews_to_insert)
            stmt = stmt.on_conflict_do_nothing(
                constraint='uq_shop_product_review'
            )
            
            result = self.db.session.execute(stmt)
            self.db.session.commit()
            
            attempted = len(reviews_to_insert)
            imported_count = result.rowcount  # Number of rows actually inserted
            duplicates_count = attempted - imported_count
            
            db_logger.info(f"[DB BULK] Attempted: {attempted}, Imported: {imported_count}, Duplicates: {duplicates_count}")
            
            # Now handle media files for newly imported reviews
            # We need to get the review IDs that were actually inserted
            if imported_count > 0 and media_data_by_source_id:
                # Fetch the newly inserted reviews to get their IDs
                source_review_ids = list(media_data_by_source_id.keys())
                new_reviews = Review.query.filter(
                    Review.shop_id == shop_id,
                    Review.shopify_product_id == shopify_product_id,
                    Review.source_review_id.in_(source_review_ids)
                ).all()
                
                # Create mapping of source_review_id to database review_id
                review_id_map = {r.source_review_id: r.id for r in new_reviews}
                
                # Insert media files for reviews that were actually inserted
                media_inserts = []
                for source_id, media_list in media_data_by_source_id.items():
                    review_db_id = review_id_map.get(source_id)
                    if review_db_id:  # Only insert media for reviews that were actually inserted (not duplicates)
                        for media_data in media_list:
                            media_inserts.append({
                                'review_id': review_db_id,
                                'media_type': 'image',
                                'media_url': media_data.get('url', ''),
                                'file_size': media_data.get('size'),
                                'width': media_data.get('width'),
                                'height': media_data.get('height'),
                                'status': 'active',
                                'created_at': datetime.utcnow()
                            })
                
                if media_inserts:
                    self.db.session.bulk_insert_mappings(ReviewMedia, media_inserts)
                    self.db.session.commit()
                    db_logger.info(f"[DB BULK] Inserted {len(media_inserts)} media files")
            
            # Update shop review count (only for newly imported reviews)
            shop = self.db.session.query(self.get_shop_model()).get(shop_id)
            if shop:
                shop.reviews_imported += imported_count
                self.db.session.commit()
                db_logger.info(f"[DB BULK] Updated shop review count to {shop.reviews_imported}")
            
            return {
                'success': True,
                'imported': imported_count,
                'duplicates': duplicates_count,
                'failed': 0
            }
            
        except Exception as e:
            self.db.session.rollback()
            db_logger.error(f"[DB BULK] Error: {str(e)}")
            import traceback
            db_logger.error(traceback.format_exc())
            return {
                'success': False,
                'imported': 0,
                'duplicates': 0,
                'failed': len(reviews_data),
                'error': str(e)
            }
    
    def import_single_review(self, shop_id, shopify_product_id, review_data, source_platform='aliexpress'):
        """
        Import a single review to database
        """
        from backend.models_v2 import Review, ReviewMedia
        import logging
        db_logger = logging.getLogger(__name__)
        
        # DEBUG: Log incoming data
        db_logger.info(f"[DB] Starting import for shop_id={shop_id}, product_id={shopify_product_id}")
        db_logger.info(f"[DB] Review data keys: {list(review_data.keys())}")
        
        # Extract AliExpress product ID from review data
        aliexpress_product_id = None
        if source_platform == 'aliexpress':
            aliexpress_product_id = review_data.get('product_id', review_data.get('source_product_id', ''))
        
        # Get or create product
        product = self.get_or_create_product(shop_id, shopify_product_id)
        db_logger.info(f"[DB] Product found/created: id={product.id}, shopify_id={shopify_product_id}")
        
        # Update product with AliExpress product ID if not set
        if aliexpress_product_id and source_platform == 'aliexpress':
            if not product.aliexpress_product_id:
                product.aliexpress_product_id = aliexpress_product_id
                product.source_platform = 'aliexpress'
                product.source_product_id = aliexpress_product_id
                db_logger.info(f"[DB] Updated product with aliexpress_product_id: {aliexpress_product_id}")
        
        # Normalize rating (AliExpress uses 0-100, convert to 1-5)
        raw_rating = review_data.get('rating', 5)
        if isinstance(raw_rating, (int, float)):
            if raw_rating > 5:
                # Convert percentage (0-100) to 1-5 scale
                rating = max(1, min(5, int((raw_rating / 100) * 5)))
            else:
                rating = max(1, min(5, int(raw_rating)))
        else:
            rating = 5
        
        db_logger.info(f"[DB] Rating: {raw_rating} -> normalized to {rating}")
        
        # Parse date
        review_date = None
        if review_data.get('date'):
            try:
                date_str = review_data['date']
                if isinstance(date_str, str):
                    # Try ISO format first
                    try:
                        review_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    except:
                        # Try other formats
                        for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%d-%m-%Y']:
                            try:
                                review_date = datetime.strptime(date_str, fmt)
                                break
                            except:
                                continue
                        if not review_date:
                            review_date = datetime.utcnow()
                else:
                    review_date = datetime.utcnow()
            except Exception as e:
                db_logger.warning(f"[DB] Date parsing failed: {e}, using current time")
                review_date = datetime.utcnow()
        
        if not review_date:
            review_date = datetime.utcnow()
        
        # Handle images (can be URLs or objects)
        images_to_process = []
        if review_data.get('images'):
            for img in review_data['images']:
                if isinstance(img, str):
                    images_to_process.append({'url': img})
                elif isinstance(img, dict):
                    images_to_process.append(img)
        
        db_logger.info(f"[DB] Processing {len(images_to_process)} images")
        
        # Use INSERT ... ON CONFLICT DO NOTHING (consistent with bulk import)
        source_review_id = str(review_data.get('id', ''))
        if not source_review_id:
            return {
                'success': False,
                'error': 'Review ID is required',
                'duplicate': False
            }
        
        # Prepare review data for insert
        review_dict = {
            'shop_id': shop_id,
            'product_id': product.id,
            'shopify_product_id': shopify_product_id,
            'source_platform': source_platform,
            'source_product_id': review_data.get('product_id', review_data.get('source_product_id', '')),
            'aliexpress_product_id': aliexpress_product_id,
            'source_review_id': source_review_id,
            'reviewer_name': review_data.get('author', review_data.get('reviewer_name', 'Anonymous')),
            'rating': rating,
            'title': review_data.get('title', ''),
            'body': review_data.get('text', review_data.get('body', '')),
            'verified_purchase': review_data.get('verified', False),
            'reviewer_country': review_data.get('country', ''),
            'review_date': review_date,
            'quality_score': review_data.get('quality_score', 0),
            'ai_recommended': review_data.get('ai_recommended', review_data.get('ai_score', 0) > 8),
            'status': 'published',
            'imported_at': datetime.utcnow()
        }
        
        try:
            # Use INSERT ... ON CONFLICT DO NOTHING (same as bulk import)
            stmt = insert(Review).values(review_dict)
            stmt = stmt.on_conflict_do_nothing(
                constraint='uq_shop_product_review'
            )
            
            result = self.db.session.execute(stmt)
            self.db.session.commit()
            
            # Check if insert succeeded or was duplicate
            if result.rowcount == 0:
                # Duplicate detected - fetch existing review
                existing_review = Review.query.filter_by(
                    shop_id=shop_id,
                    shopify_product_id=shopify_product_id,
                    source_review_id=source_review_id
                ).first()
                
                if existing_review:
                    db_logger.info(f"[DB] Duplicate review detected: source_review_id={source_review_id}, existing DB ID={existing_review.id}")
                    return {
                        'success': True,
                        'review_id': existing_review.id,
                        'product_id': product.id,
                        'shopify_product_id': shopify_product_id,
                        'duplicate': True,
                        'message': 'Review already imported for this product'
                    }
                else:
                    # This shouldn't happen, but handle edge case
                    db_logger.warning(f"[DB] ON CONFLICT returned 0 rows but no existing review found for source_review_id={source_review_id}")
                    return {
                        'success': False,
                        'error': 'Duplicate detected but existing review not found',
                        'duplicate': True
                    }
            
            # Review was inserted successfully - fetch it to get the ID
            new_review = Review.query.filter_by(
                shop_id=shop_id,
                shopify_product_id=shopify_product_id,
                source_review_id=source_review_id
            ).first()
            
            if not new_review:
                db_logger.error(f"[DB] Review inserted (rowcount=1) but not found in database for source_review_id={source_review_id}")
                return {
                    'success': False,
                    'error': 'Review inserted but not found',
                    'duplicate': False
                }
            
            db_logger.info(f"[DB] Review object created, DB ID: {new_review.id}")
            
            # Add media files (only for newly inserted reviews, not duplicates)
            if images_to_process:
                media_inserts = []
                for image_data in images_to_process:
                    media_inserts.append({
                        'review_id': new_review.id,
                        'media_type': 'image',
                        'media_url': image_data.get('url', ''),
                        'file_size': image_data.get('size'),
                        'width': image_data.get('width'),
                        'height': image_data.get('height'),
                        'status': 'active',
                        'created_at': datetime.utcnow()
                    })
                
                if media_inserts:
                    self.db.session.bulk_insert_mappings(ReviewMedia, media_inserts)
                    self.db.session.commit()
                    db_logger.info(f"[DB] Inserted {len(media_inserts)} media files")
            
            # Update shop's review count (only for new reviews, not duplicates)
            shop = self.db.session.query(self.get_shop_model()).get(shop_id)
            if shop:
                shop.reviews_imported += 1
                self.db.session.commit()
                db_logger.info(f"[DB] Updated shop review count to {shop.reviews_imported}")
            
            db_logger.info(f"[DB] COMMIT SUCCESS - Review {new_review.id} saved to database!")
            
            return {
                'success': True,
                'review_id': new_review.id,
                'product_id': product.id,
                'shopify_product_id': shopify_product_id,
                'duplicate': False,
                'message': 'Review imported successfully'
            }
            
        except Exception as e:
            self.db.session.rollback()
            db_logger.error(f"[DB] Single import error: {str(e)}")
            import traceback
            db_logger.error(traceback.format_exc())
            return {
                'success': False,
                'error': str(e),
                'duplicate': False
            }
    
    def get_product_reviews(self, shop_id, shopify_product_id, limit=20):
        """
        Get reviews for a specific product
        """
        from backend.models_v2 import Review, ReviewMedia, Product
        
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
    
    def get_shop_model(self):
        """Helper to get shop model"""
        from backend.models_v2 import Shop
        return Shop
    
    def check_payment_status(self, shop_id):
        """
        Check if shop has active payment (Loox-style gating)
        """
        from backend.models_v2 import Shop
        
        shop = Shop.query.get(shop_id)
        if not shop:
            return False
        
        if shop.plan == 'free':
            return shop.reviews_imported < shop.review_limit
        
        if shop.plan in ['basic', 'pro']:
            return shop.subscription_status == 'active'
        
        return False
    
    def export_reviews_csv(self, shop_id):
        """
        Export all reviews for a shop to CSV format
        """
        from backend.models_v2 import Review, Product
        
        reviews = Review.query.filter_by(shop_id=shop_id).all()
        
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
        
        return csv_data
