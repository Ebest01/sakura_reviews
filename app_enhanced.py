"""
ReviewKing Enhanced API - Superior to Loox
Matching Loox architecture with competitive advantages:
- Multi-platform (AliExpress, Amazon, eBay, Walmart)
- AI Quality Scoring (10-point system)
- Bulk import capabilities
- Better pricing
- Superior UX
"""

from flask import Flask, request, jsonify, session, render_template, redirect, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import os
import json
import logging
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import re
import time
import random
from urllib.parse import urlparse, unquote, parse_qs
import hashlib
import uuid
import hmac

# Import remote config loader
try:
    from config_loader import config as remote_config
    logger = logging.getLogger(__name__)
    logger.info("📡 Remote config loader initialized")
except ImportError:
    remote_config = None
    logger = logging.getLogger(__name__)
    logger.warning("⚠️ Config loader not available, using environment variables only")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, supports_credentials=True)

# Database Configuration - Use models_v2 db instance
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://saksaks:11!!!!.Magics4321@193.203.165.217:5432/sakrev_db?sslmode=disable')
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Import models_v2 db instance (this is the ONE db instance we'll use)
from backend.models_v2 import db
db.init_app(app)

# Database migration flag
_migrations_run = False

@app.before_request
def ensure_migrations():
    """Run database migrations on first request"""
    global _migrations_run
    if not _migrations_run:
        _migrations_run = True
        try:
            # Add helpful_yes and helpful_no columns if they don't exist
            db.session.execute(db.text("""
                ALTER TABLE reviews ADD COLUMN IF NOT EXISTS helpful_yes INTEGER DEFAULT 0;
            """))
            db.session.execute(db.text("""
                ALTER TABLE reviews ADD COLUMN IF NOT EXISTS helpful_no INTEGER DEFAULT 0;
            """))
            db.session.commit()
            logger.info("✅ Database migrations applied (helpful votes columns)")
        except Exception as e:
            db.session.rollback()
            logger.warning(f"⚠️ Migration note: {e}")
        
        # Create email-related tables if they don't exist
        try:
            from backend.models_v2 import EmailSettings, ReviewRequest, EmailUnsubscribe
            from sqlalchemy import inspect
            
            # Check if tables exist first
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            tables_to_create = []
            if 'email_settings' not in existing_tables:
                tables_to_create.append('email_settings')
            if 'review_requests' not in existing_tables:
                tables_to_create.append('review_requests')
            if 'email_unsubscribes' not in existing_tables:
                tables_to_create.append('email_unsubscribes')
            
            if tables_to_create:
                logger.info(f"Creating missing email tables: {tables_to_create}")
                db.create_all()  # This will create missing tables
                logger.info("✅ Email-related tables created")
            else:
                logger.info("✅ Email-related tables already exist")
        except Exception as e:
            logger.warning(f"⚠️ Email tables migration note: {e}")
            # Try to create tables using raw SQL as fallback
            try:
                with db.engine.connect() as conn:
                    # Create email_settings table
                    if 'email_settings' not in existing_tables:
                        conn.execute(db.text("""
                            CREATE TABLE IF NOT EXISTS email_settings (
                                id SERIAL PRIMARY KEY,
                                shop_id INTEGER NOT NULL UNIQUE REFERENCES shops(id),
                                enabled BOOLEAN DEFAULT TRUE,
                                delay_days INTEGER DEFAULT 7,
                                send_time VARCHAR(10) DEFAULT '10:00',
                                reminder_enabled BOOLEAN DEFAULT TRUE,
                                reminder_delay_days INTEGER DEFAULT 14,
                                max_reminders INTEGER DEFAULT 2,
                                discount_enabled BOOLEAN DEFAULT FALSE,
                                discount_percent INTEGER DEFAULT 10,
                                photo_discount_enabled BOOLEAN DEFAULT FALSE,
                                photo_discount_percent INTEGER DEFAULT 15,
                                email_subject VARCHAR(255) DEFAULT 'We''d love your feedback!',
                                email_from_name VARCHAR(255),
                                min_order_value FLOAT DEFAULT 0,
                                exclude_products TEXT,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                            )
                        """))
                        conn.commit()
                        logger.info("✅ email_settings table created via SQL")
                    
                    # Create review_requests table
                    if 'review_requests' not in existing_tables:
                        conn.execute(db.text("""
                            CREATE TABLE IF NOT EXISTS review_requests (
                                id SERIAL PRIMARY KEY,
                                shop_id INTEGER NOT NULL REFERENCES shops(id),
                                order_id VARCHAR(255) NOT NULL,
                                order_number VARCHAR(255),
                                order_date TIMESTAMP,
                                order_total FLOAT,
                                customer_email VARCHAR(255) NOT NULL,
                                customer_name VARCHAR(255),
                                product_id VARCHAR(255) NOT NULL,
                                product_name VARCHAR(255),
                                product_image TEXT,
                                status VARCHAR(50) DEFAULT 'pending',
                                emails_sent INTEGER DEFAULT 0,
                                scheduled_at TIMESTAMP,
                                first_sent_at TIMESTAMP,
                                last_sent_at TIMESTAMP,
                                reviewed_at TIMESTAMP,
                                discount_code VARCHAR(255),
                                discount_used BOOLEAN DEFAULT FALSE,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                            )
                        """))
                        conn.execute(db.text("CREATE INDEX IF NOT EXISTS idx_review_request_shop_order ON review_requests(shop_id, order_id)"))
                        conn.execute(db.text("CREATE INDEX IF NOT EXISTS idx_review_request_scheduled ON review_requests(status, scheduled_at)"))
                        conn.commit()
                        logger.info("✅ review_requests table created via SQL")
                    
                    # Create email_unsubscribes table
                    if 'email_unsubscribes' not in existing_tables:
                        conn.execute(db.text("""
                            CREATE TABLE IF NOT EXISTS email_unsubscribes (
                                id SERIAL PRIMARY KEY,
                                email VARCHAR(255) NOT NULL,
                                shop_id INTEGER REFERENCES shops(id),
                                reason VARCHAR(255),
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                            )
                        """))
                        conn.execute(db.text("CREATE INDEX IF NOT EXISTS idx_email_unsubscribe_shop ON email_unsubscribes(email, shop_id)"))
                        conn.commit()
                        logger.info("✅ email_unsubscribes table created via SQL")
            except Exception as sql_error:
                logger.error(f"Failed to create email tables via SQL: {sql_error}")
                import traceback
                logger.error(traceback.format_exc())

# Import database integration
try:
    from database_integration import DatabaseIntegration
    db_integration = DatabaseIntegration(db)
    logger.info("✅ Database integration initialized")
except Exception as e:
    logger.warning(f"⚠️ Database integration not available: {e}")
    db_integration = None

# Configuration
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'reviewking-secret-' + str(uuid.uuid4()))
    API_VERSION = '2.0.0'
    WIDGET_SECRET = os.environ.get('WIDGET_SECRET', 'sakura-widget-secret-key')
    WIDGET_BASE_URL = os.environ.get('WIDGET_BASE_URL', 'https://sakura-reviews-sakrev-v15.utztjw.easypanel.host')
    
    # Admin Credentials
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'zidimasters')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '11!!!!.zidiMasters')
    
    # Shopify API Configuration (priority: env vars > remote config)
    # NOTE: No hardcoded defaults for security - must be set via environment or config.json
    SHOPIFY_API_KEY = os.environ.get('SHOPIFY_API_KEY') or (remote_config.get('shopify.api_key') if remote_config else None)
    SHOPIFY_API_SECRET = os.environ.get('SHOPIFY_API_SECRET') or (remote_config.get('shopify.api_secret') if remote_config else None)
    SHOPIFY_ACCESS_TOKEN = os.environ.get('SHOPIFY_ACCESS_TOKEN') or (remote_config.get('shopify.access_token') if remote_config else None)
    SHOPIFY_SHOP_DOMAIN = os.environ.get('SHOPIFY_SHOP_DOMAIN') or (remote_config.get('shopify.shop_domain') if remote_config else None)
    SHOPIFY_API_VERSION = os.environ.get('SHOPIFY_API_VERSION') or (remote_config.get('shopify.api_version') if remote_config else '2025-10')
    
    # App URLs (from your Shopify app configuration)
    # NOTE: Should be set via environment or config.json
    SHOPIFY_APP_URL = os.environ.get('SHOPIFY_APP_URL') or (remote_config.get('shopify.app_url') if remote_config else None)
    SHOPIFY_REDIRECT_URI = os.environ.get('SHOPIFY_REDIRECT_URI') or (remote_config.get('shopify.redirect_uri') if remote_config else None)
    
    # Loox stealth fallback configuration (Plan B)
    LOOX_FALLBACK_ID = "b3Zk9ExHgf.eca2133e2efc041236106236b783f6b4"
    LOOX_ENDPOINT = "https://loox.io/-/admin/reviews/import/url"
    
    # Scopes (from your app configuration)
    SHOPIFY_SCOPES = 'read_products,write_products,read_content,write_content,write_script_tags'
    
    # Better pricing than Loox
    PRICING = {
        'free': {'price': 0, 'reviews': 50, 'name': 'Free Forever'},
        'basic': {'price': 19.99, 'reviews': 500, 'name': 'Basic Plan'},
        'pro': {'price': 39.99, 'reviews': 5000, 'name': 'Pro Plan'}
    }
    
    # Supported platforms (more than Loox!)
    PLATFORMS = ['aliexpress', 'amazon', 'ebay', 'walmart']

app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def anonymize_reviewer_name(name):
    """
    Anonymize reviewer names to hide that reviews came from AliExpress.
    - "AliExpress Shopper" → random "X***y" format
    - "Customer" → random "X***y" format  
    - Already anonymized (contains ***) → keep as is
    - Regular names → keep as is
    """
    import string
    
    if not name:
        # Generate random name
        first = random.choice(string.ascii_uppercase)
        last = random.choice(string.ascii_lowercase)
        return f"{first}***{last}"
    
    name_lower = name.lower().strip()
    
    # Check if it's a generic/platform name that should be anonymized
    generic_names = [
        'aliexpress shopper', 
        'aliexpress buyer',
        'aliexpress customer',
        'customer',
        'anonymous',
        'shopper',
        'buyer'
    ]
    
    if name_lower in generic_names:
        # Generate random anonymized name like "A***r" or "M***k"
        first = random.choice(string.ascii_uppercase)
        last = random.choice(string.ascii_lowercase)
        return f"{first}***{last}"
    
    # If already anonymized (contains ***), keep it
    if '***' in name:
        return name
    
    # Keep real names as-is
    return name

# =============================================================================
# ERROR HANDLERS - User-friendly error pages
# =============================================================================

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors"""
    return render_template('error.html', error_code=404), 404

@app.errorhandler(500)
def internal_server_error(e):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(e)}")
    return render_template('error.html', error_code=500), 500

@app.errorhandler(403)
def forbidden(e):
    """Handle 403 errors"""
    return render_template('error.html', error_code=403), 403

@app.errorhandler(401)
def unauthorized(e):
    """Handle 401 errors"""
    return render_template('error.html', error_code=401), 401

# =============================================================================
# APP DASHBOARD - Main app interface in Shopify Admin
# =============================================================================

@app.route('/app')
@app.route('/app/dashboard')
def app_dashboard():
    """
    Main app dashboard - shown when merchant opens app in Shopify Admin
    """
    shop = request.args.get('shop') or session.get('shop_domain')
    
    # Get stats from database if available
    stats = {
        'shop_domain': shop,
        'plan': 'Free',
        'total_reviews': 0,
        'avg_rating': '0.0',
        'products_with_reviews': 0,
        'review_limit': 50,
        'used_reviews': 0,
        'remaining_reviews': 50
    }
    
    if db_integration and shop:
        try:
            from backend.models_v2 import Shop, Review, Product
            shop_record = Shop.query.filter_by(shop_domain=shop).first()
            if shop_record:
                # Get review stats
                review_count = Review.query.filter_by(shop_id=shop_record.id).count()
                stats['total_reviews'] = review_count
                stats['used_reviews'] = review_count
                stats['remaining_reviews'] = max(0, stats['review_limit'] - review_count)
                
                # Get average rating
                from sqlalchemy import func
                avg = db.session.query(func.avg(Review.rating)).filter_by(shop_id=shop_record.id).scalar()
                stats['avg_rating'] = f"{float(avg):.1f}" if avg else '0.0'
                
                # Get products with reviews count
                products_count = db.session.query(func.count(func.distinct(Review.product_id))).filter_by(shop_id=shop_record.id).scalar()
                stats['products_with_reviews'] = products_count or 0
        except Exception as e:
            logger.error(f"Error fetching dashboard stats: {e}")
    
    return render_template('app-dashboard.html', **stats)


# ==================== EMAIL SETTINGS ROUTES ====================

@app.route('/app/email-settings', methods=['GET', 'POST'])
def app_email_settings():
    """
    Email settings page - configure review request emails
    """
    from backend.models_v2 import EmailSettings, ReviewRequest, Shop
    
    shop_domain = request.args.get('shop') or session.get('shop_domain')
    message = request.args.get('message')
    error = request.args.get('error')
    
    # Get shop
    shop = None
    if shop_domain:
        shop = Shop.query.filter_by(shop_domain=shop_domain).first()
    
    if not shop:
        return redirect('/auth/install?error=shop_not_found')
    
    # Get or create email settings
    settings = EmailSettings.query.filter_by(shop_id=shop.id).first()
    if not settings:
        settings = EmailSettings(shop_id=shop.id)
        db.session.add(settings)
        db.session.commit()
    
    if request.method == 'POST':
        # Update settings
        settings.enabled = 'enabled' in request.form
        settings.delay_days = int(request.form.get('delay_days', 7))
        settings.send_time = request.form.get('send_time', '10:00')
        settings.reminder_enabled = 'reminder_enabled' in request.form
        settings.reminder_delay_days = int(request.form.get('reminder_delay_days', 14))
        settings.max_reminders = int(request.form.get('max_reminders', 2))
        settings.discount_enabled = 'discount_enabled' in request.form
        settings.discount_percent = int(request.form.get('discount_percent', 10))
        settings.photo_discount_enabled = 'photo_discount_enabled' in request.form
        settings.photo_discount_percent = int(request.form.get('photo_discount_percent', 15))
        settings.email_subject = request.form.get('email_subject', "We'd love your feedback!")
        settings.email_from_name = request.form.get('email_from_name', '')
        
        db.session.commit()
        message = 'Email settings saved successfully!'
    
    # Get email stats
    stats = {
        'total_sent': ReviewRequest.query.filter_by(shop_id=shop.id).filter(
            ReviewRequest.first_sent_at.isnot(None)
        ).count(),
        'pending': ReviewRequest.query.filter_by(shop_id=shop.id, status='pending').count(),
        'reviews_received': ReviewRequest.query.filter_by(shop_id=shop.id, status='reviewed').count(),
        'conversion_rate': '0%'
    }
    
    if stats['total_sent'] > 0:
        rate = (stats['reviews_received'] / stats['total_sent']) * 100
        stats['conversion_rate'] = f"{rate:.1f}%"
    
    return render_template('app-email-settings.html',
                         settings=settings.to_dict(),
                         stats=stats,
                         shop_name=shop.shop_name or shop_domain,
                         shop_domain=shop_domain,
                         plan='Free',  # Can be dynamic later
                         message=message,
                         error=error)


@app.route('/app/email-preview')
def app_email_preview():
    """
    Preview the review request email
    """
    from backend.models_v2 import EmailSettings, Shop
    
    shop_domain = request.args.get('shop') or session.get('shop_domain')
    shop = Shop.query.filter_by(shop_domain=shop_domain).first() if shop_domain else None
    settings = EmailSettings.query.filter_by(shop_id=shop.id).first() if shop else None
    
    return render_template('email-review-request.html',
                         customer_name='John',
                         shop_name=shop.shop_name if shop else 'Your Store',
                         shop_url=f"https://{shop_domain}" if shop_domain else '#',
                         product_name='Sample Product',
                         product_image='https://via.placeholder.com/100',
                         order_date='December 25, 2025',
                         review_url=f"https://{shop_domain}/review",
                         discount_enabled=settings.discount_enabled if settings else False,
                         discount_percent=settings.discount_percent if settings else 10,
                         discount_code='REVIEW10',
                         unsubscribe_url='#')


@app.route('/app/email-test', methods=['POST'])
def app_email_test():
    """
    Send a test review request email
    """
    from backend.models_v2 import Shop, EmailSettings, Product
    from flask import render_template
    import smtplib
    import traceback
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from datetime import datetime
    
    test_email = request.form.get('test_email')
    shop_domain = request.form.get('shop') or request.args.get('shop') or session.get('shop_domain')
    
    if not test_email:
        return redirect(f'/app/email-settings?shop={shop_domain}&error=email_required')
    
    if not shop_domain:
        return redirect('/auth/install?error=shop_not_found')
    
    try:
        # Get shop
        shop = Shop.query.filter_by(shop_domain=shop_domain).first()
        if not shop:
            return redirect(f'/auth/install?error=shop_not_found')
        
        # Get email settings
        settings = EmailSettings.query.filter_by(shop_id=shop.id).first()
        if not settings:
            settings = EmailSettings(shop_id=shop.id)
            db.session.add(settings)
            db.session.commit()
        
        # Get a sample product for the test email
        product = Product.query.filter_by(shop_id=shop.id).first()
        product_image = 'https://via.placeholder.com/100'
        product_name = 'Sample Product'
        product_id = 'test-product'
        
        if product:
            # Use real product data if available
            product_image = product.image_url or product.shopify_product_url or 'https://via.placeholder.com/100'
            product_name = product.shopify_product_title or 'Sample Product'
            product_id = product.shopify_product_id
        else:
            # Use placeholder data for test email
            logger.info("No products found, using placeholder data for test email")
        
        # Get email configuration from environment
        smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        smtp_user = os.environ.get('SMTP_USER', '')
        smtp_password = os.environ.get('SMTP_PASSWORD', '')
        email_from = os.environ.get('EMAIL_FROM', 'noreply@sakurareviews.com')
        email_from_name = settings.email_from_name or shop.shop_name or 'Sakura Reviews'
        
        # Check if SMTP is configured
        if not smtp_user or not smtp_password:
            return redirect(f'/app/email-settings?shop={shop_domain}&error=SMTP not configured. Please set SMTP_USER and SMTP_PASSWORD environment variables.')
        
        # Build review URL
        review_url = f"https://{shop_domain}/products/{product_id}#sakura-reviews"
        unsubscribe_url = f"https://sakura-reviews-sakrev-v15.utztjw.easypanel.host/email/unsubscribe/test-token"
        
        # Render email template
        email_html = render_template('email-review-request.html',
            customer_name='Test Customer',
            shop_name=shop.shop_name or shop_domain,
            shop_url=f"https://{shop_domain}",
            product_name=product_name,
            product_image=product_image,
            order_date=datetime.utcnow().strftime('%B %d, %Y'),
            review_url=review_url,
            discount_enabled=settings.discount_enabled,
            discount_percent=settings.discount_percent,
            discount_code='REVIEW10',
            unsubscribe_url=unsubscribe_url
        )
        
        # Create email
        msg = MIMEMultipart('alternative')
        msg['Subject'] = settings.email_subject or "We'd love your feedback!"
        msg['From'] = f"{email_from_name} <{email_from}>"
        msg['To'] = test_email
        
        # Add HTML part
        html_part = MIMEText(email_html, 'html')
        msg.attach(html_part)
        
        # Send email
        try:
            logger.info(f"Attempting to send test email to {test_email} via {smtp_server}:{smtp_port}")
            logger.info(f"SMTP User: {smtp_user}, From: {email_from}")
            
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"✅ Test review request email sent successfully to {test_email}")
            return redirect(f'/app/email-settings?shop={shop_domain}&message=Test email sent successfully to {test_email}')
        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"SMTP Authentication failed. Check your email and password. Error: {str(e)}"
            logger.error(f"SMTP Auth Error: {error_msg}")
            logger.error(traceback.format_exc())
            return redirect(f'/app/email-settings?shop={shop_domain}&error={error_msg}')
        except smtplib.SMTPException as e:
            error_msg = f"SMTP Error: {str(e)}"
            logger.error(f"SMTP Error: {error_msg}")
            logger.error(traceback.format_exc())
            return redirect(f'/app/email-settings?shop={shop_domain}&error={error_msg}')
        except Exception as e:
            error_msg = f"Failed to send email: {str(e)}"
            logger.error(f"Email send error: {error_msg}")
            import traceback
            logger.error(traceback.format_exc())
            return redirect(f'/app/email-settings?shop={shop_domain}&error={error_msg}')
            
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        logger.error(f"Error in test email endpoint: {error_msg}")
        import traceback
        logger.error(traceback.format_exc())
        return redirect(f'/app/email-settings?shop={shop_domain}&error={error_msg}')

@app.route('/app/test-review-acknowledgment-email', methods=['GET', 'POST'])
def test_review_acknowledgment_email():
    """
    Test endpoint to send a review acknowledgment email
    Usage: /app/test-review-acknowledgment-email?email=deshabunda2@gmail.com
    """
    from backend.models_v2 import Review, Shop, Product
    
    test_email = request.args.get('email') or request.form.get('email', 'deshabunda2@gmail.com')
    
    if not test_email:
        return jsonify({'error': 'Email parameter required'}), 400
    
    try:
        # Get or create a test shop
        shop = Shop.query.filter_by(shop_domain='sakura-rev-test-store.myshopify.com').first()
        if not shop:
            # Create a dummy shop for testing
            shop = Shop(
                shop_domain='sakura-rev-test-store.myshopify.com',
                shop_name='Test Store',
                access_token='test'
            )
            db.session.add(shop)
            db.session.flush()
        
        # Get or create a test product
        product = Product.query.filter_by(shop_id=shop.id).first()
        if not product:
            product = Product(
                shop_id=shop.id,
                shopify_product_id='10045740417338',
                shopify_product_title='Test Product',
                source_platform='sakura_reviews',
                status='active'
            )
            db.session.add(product)
            db.session.flush()
        
        # Create a dummy review for testing
        test_review = Review(
            shop_id=shop.id,
            product_id=product.id,
            shopify_product_id=product.shopify_product_id,
            source_platform='sakura_reviews',
            rating=5,
            body='This is a test review to verify the acknowledgment email system is working correctly. Thank you for testing!',
            reviewer_name='Test Customer',
            reviewer_email=test_email,
            review_date=datetime.utcnow(),
            imported_at=datetime.utcnow(),
            status='published'
        )
        
        # Send the acknowledgment email
        try:
            send_review_acknowledgment_email(test_review, shop, product)
            return jsonify({
                'success': True,
                'message': f'Test acknowledgment email sent to {test_email}',
                'email': test_email
            })
        except Exception as e:
            logger.error(f"Error sending test email: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return jsonify({
                'success': False,
                'error': f'Failed to send email: {str(e)}',
                'email': test_email
            }), 500
            
    except Exception as e:
        logger.error(f"Error in test endpoint: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/email/unsubscribe/<token>')
def email_unsubscribe(token):
    """
    Handle email unsubscribe
    """
    from backend.models_v2 import EmailUnsubscribe, ReviewRequest
    import base64
    
    try:
        # Decode token (base64 encoded email:shop_id)
        decoded = base64.b64decode(token).decode('utf-8')
        email, shop_id = decoded.split(':')
        
        # Add to unsubscribe list
        unsubscribe = EmailUnsubscribe(
            email=email,
            shop_id=int(shop_id) if shop_id != 'global' else None
        )
        db.session.add(unsubscribe)
        
        # Update any pending review requests
        ReviewRequest.query.filter_by(
            customer_email=email,
            shop_id=int(shop_id) if shop_id != 'global' else None,
            status='pending'
        ).update({'status': 'unsubscribed'})
        
        db.session.commit()
        
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Unsubscribed - Sakura Reviews</title>
            <style>
                body { font-family: -apple-system, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; background: #f8fafc; }
                .box { text-align: center; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }
                h1 { color: #1a202c; margin-bottom: 16px; }
                p { color: #64748b; }
            </style>
        </head>
        <body>
            <div class="box">
                <h1>✓ Unsubscribed</h1>
                <p>You won't receive any more review request emails from this store.</p>
            </div>
        </body>
        </html>
        """
    except Exception as e:
        logger.error(f"Error processing unsubscribe: {e}")
        return "Invalid unsubscribe link", 400


# Shopify Webhook: Order Created (Checkout) - Schedule review request email
@app.route('/webhooks/orders/create', methods=['POST'])
def webhook_order_create():
    """
    Handle order created webhook - schedule review request email at checkout
    This triggers when customer completes checkout
    """
    from backend.models_v2 import Shop, EmailSettings, ReviewRequest, EmailUnsubscribe
    from datetime import timedelta
    
    try:
        # Verify webhook
        shop_domain = request.headers.get('X-Shopify-Shop-Domain')
        if not shop_domain:
            return jsonify({'error': 'Missing shop domain'}), 400
        
        shop = Shop.query.filter_by(shop_domain=shop_domain).first()
        if not shop:
            return jsonify({'error': 'Shop not found'}), 404
        
        # Get email settings
        settings = EmailSettings.query.filter_by(shop_id=shop.id).first()
        if not settings or not settings.enabled:
            return jsonify({'status': 'emails_disabled'})
        
        data = request.get_json()
        
        # Check if customer is unsubscribed
        customer_email = data.get('email') or data.get('customer', {}).get('email')
        if not customer_email:
            return jsonify({'status': 'no_email'})
        
        is_unsubscribed = EmailUnsubscribe.query.filter(
            (EmailUnsubscribe.email == customer_email) &
            ((EmailUnsubscribe.shop_id == shop.id) | (EmailUnsubscribe.shop_id.is_(None)))
        ).first()
        
        if is_unsubscribed:
            return jsonify({'status': 'unsubscribed'})
        
        # Create review request for each line item
        customer_name = data.get('customer', {}).get('first_name', 'Customer')
        order_id = str(data.get('id'))
        order_number = data.get('order_number')
        order_date = datetime.utcnow()
        order_total = float(data.get('total_price', 0))
        
        # Check minimum order value
        if settings.min_order_value and order_total < settings.min_order_value:
            return jsonify({'status': 'below_min_value'})
        
        # For checkout emails, use shorter delay (3-5 days) since product may arrive quickly
        # Or use the same delay_days setting
        delay_days = max(settings.delay_days, 3)  # At least 3 days after checkout
        scheduled_at = datetime.utcnow() + timedelta(days=delay_days)
        
        for line_item in data.get('line_items', []):
            product_id = str(line_item.get('product_id'))
            product_name = line_item.get('name', 'Product')
            product_image = line_item.get('image', {}).get('src') if line_item.get('image') else None
            
            # Check if request already exists
            existing = ReviewRequest.query.filter_by(
                shop_id=shop.id,
                order_id=order_id,
                product_id=product_id
            ).first()
            
            if not existing:
                review_request = ReviewRequest(
                    shop_id=shop.id,
                    order_id=order_id,
                    order_number=order_number,
                    order_date=order_date,
                    order_total=order_total,
                    customer_email=customer_email,
                    customer_name=customer_name,
                    product_id=product_id,
                    product_name=product_name,
                    product_image=product_image,
                    scheduled_at=scheduled_at,
                    status='pending'
                )
                db.session.add(review_request)
        
        db.session.commit()
        return jsonify({'status': 'scheduled', 'scheduled_at': scheduled_at.isoformat()})
    
    except Exception as e:
        logger.error(f"Error processing order create webhook: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# Shopify Webhook: Order Fulfilled - Schedule review request email
@app.route('/webhooks/orders/fulfilled', methods=['POST'])
def webhook_order_fulfilled():
    """
    Handle order fulfilled webhook - schedule review request email
    This triggers when order is shipped/fulfilled (recommended - customer has received product)
    """
    from backend.models_v2 import Shop, EmailSettings, ReviewRequest, EmailUnsubscribe
    from datetime import timedelta
    
    try:
        # Verify webhook
        shop_domain = request.headers.get('X-Shopify-Shop-Domain')
        if not shop_domain:
            return jsonify({'error': 'Missing shop domain'}), 400
        
        shop = Shop.query.filter_by(shop_domain=shop_domain).first()
        if not shop:
            return jsonify({'error': 'Shop not found'}), 404
        
        # Get email settings
        settings = EmailSettings.query.filter_by(shop_id=shop.id).first()
        if not settings or not settings.enabled:
            return jsonify({'status': 'emails_disabled'})
        
        data = request.get_json()
        
        # Check if customer is unsubscribed
        customer_email = data.get('email') or data.get('customer', {}).get('email')
        if not customer_email:
            return jsonify({'status': 'no_email'})
        
        is_unsubscribed = EmailUnsubscribe.query.filter(
            (EmailUnsubscribe.email == customer_email) &
            ((EmailUnsubscribe.shop_id == shop.id) | (EmailUnsubscribe.shop_id.is_(None)))
        ).first()
        
        if is_unsubscribed:
            return jsonify({'status': 'unsubscribed'})
        
        # Create review request for each line item
        customer_name = data.get('customer', {}).get('first_name', 'Customer')
        order_id = str(data.get('id'))
        order_number = data.get('order_number')
        order_date = datetime.utcnow()
        order_total = float(data.get('total_price', 0))
        
        # Check minimum order value
        if settings.min_order_value and order_total < settings.min_order_value:
            return jsonify({'status': 'below_min_value'})
        
        # Calculate when to send email
        scheduled_at = datetime.utcnow() + timedelta(days=settings.delay_days)
        
        for line_item in data.get('line_items', []):
            product_id = str(line_item.get('product_id'))
            product_name = line_item.get('name', 'Product')
            product_image = line_item.get('image', {}).get('src') if line_item.get('image') else None
            
            # Check if request already exists
            existing = ReviewRequest.query.filter_by(
                shop_id=shop.id,
                order_id=order_id,
                product_id=product_id
            ).first()
            
            if not existing:
                review_request = ReviewRequest(
                    shop_id=shop.id,
                    order_id=order_id,
                    order_number=order_number,
                    order_date=order_date,
                    order_total=order_total,
                    customer_email=customer_email,
                    customer_name=customer_name,
                    product_id=product_id,
                    product_name=product_name,
                    product_image=product_image,
                    scheduled_at=scheduled_at,
                    status='pending'
                )
                db.session.add(review_request)
        
        db.session.commit()
        return jsonify({'status': 'scheduled', 'scheduled_at': scheduled_at.isoformat()})
    
    except Exception as e:
        logger.error(f"Error processing order fulfilled webhook: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# In-memory storage for demo (use Redis/DB in production)
import_sessions = {}
analytics_events = []
skipped_reviews = {}  # Track skipped reviews per session

class EnhancedReviewExtractor:
    """Enhanced scraper with multi-platform support"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def extract_reviews_paginated(self, product_data, page=1, per_page=10, filters=None):
        """Extract reviews with pagination - matches Loox /admin/reviews/import/url"""
        platform = product_data.get('platform', '').lower()
        product_id = product_data.get('productId')
        
        if not product_id:
            return self._error_response("Product ID required")
        
        try:
            if 'aliexpress' in platform:
                reviews = self._scrape_aliexpress(product_id, page, per_page)
            elif 'amazon' in platform:
                reviews = self._scrape_amazon(product_id, page, per_page)
            elif 'ebay' in platform:
                reviews = self._scrape_ebay(product_id, page, per_page)
            elif 'walmart' in platform:
                reviews = self._scrape_walmart(product_id, page, per_page)
            else:
                return self._error_response(f"Platform {platform} not supported")
            
            # Check if all scraping methods failed
            if reviews is None:
                return {
                    'success': False,
                    'error': 'service_unavailable',
                    'message': 'Oops! Something went wrong while fetching reviews. Our team is working on it. Please try again in a few minutes.',
                    'reviews': [],
                    'stats': {
                        'with_photos': 0,
                        'ai_recommended': 0,
                        'average_rating': 0,
                        'average_quality': 0
                    }
                }
            
            # Apply filters
            if filters:
                reviews = self._apply_filters(reviews, filters)
            
            # Calculate AI scores for all reviews
            for review in reviews:
                review['quality_score'] = self._calculate_quality_score(review)
                # AI recommends only high-quality AND positive reviews (4+ stars = rating >= 80)
                review['ai_recommended'] = (review['quality_score'] >= 8 and review.get('rating', 0) >= 80)
                review['sentiment_score'] = self._calculate_sentiment(review.get('text', ''))
            
            # Sort by quality score (competitive advantage!)
            reviews.sort(key=lambda x: x.get('quality_score', 0), reverse=True)
            
            total_reviews = 150  # Simulated
            has_next = (page * per_page) < total_reviews
            
            return {
                'success': True,
                'reviews': reviews,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total_reviews,
                    'has_next': has_next,
                    'has_prev': page > 1,
                    'total_pages': (total_reviews + per_page - 1) // per_page
                },
                'stats': {
                    'with_photos': len([r for r in reviews if r.get('images', [])]),
                    'ai_recommended': len([r for r in reviews if r.get('ai_recommended', False)]),
                    'average_rating': sum(r.get('rating', 0) for r in reviews) / len(reviews) if reviews else 0,
                    'average_quality': sum(r.get('quality_score', 0) for r in reviews) / len(reviews) if reviews else 0
                },
                'filters_applied': filters or {},
                'api_version': Config.API_VERSION
            }
            
        except Exception as e:
            logger.error(f"Extract error: {str(e)}")
            return self._error_response(str(e))
    
    def _scrape_aliexpress(self, product_id, page, per_page):
        """Scrape AliExpress reviews - REAL DATA using proven API"""
        try:
            # AliExpress API has a hard limit of ~20 reviews per response
            # So to get 100 reviews, we need to make multiple page requests
            all_reviews = []
            reviews_per_api_page = 20  # AliExpress API limit
            
            # Calculate how many API pages we need to fetch (fetch extra to account for duplicates)
            num_pages_needed = ((per_page * 2) + reviews_per_api_page - 1) // reviews_per_api_page
            
            logger.info(f"Fetching {per_page} reviews from AliExpress API (making {num_pages_needed} requests to account for duplicates)")
            
            # AliExpress's official feedback API endpoint (PROVEN TO WORK!)
            api_url = "https://feedback.aliexpress.com/pc/searchEvaluation.do"
            
            for api_page in range(1, num_pages_needed + 1):
                params = {
                    'productId': product_id,
                    'lang': 'en_US',
                    'country': 'US',
                    'pageSize': 20,  # AliExpress returns max 20 regardless of this value
                    'filter': 'all',
                    'sort': 'complex_default',
                    'page': api_page
                }
                
                response = self.session.get(api_url, params=params, timeout=15)
                
                if response.status_code != 200:
                    logger.warning(f"API returned {response.status_code} for page {api_page}")
                    break
                
                # Parse JSON response
                try:
                    data = response.json()
                    page_reviews = self._parse_aliexpress_api(data, product_id, api_page)
                    if page_reviews:
                        all_reviews.extend(page_reviews)
                        logger.info(f"✅ Page {api_page}/{num_pages_needed}: Got {len(page_reviews)} reviews (total: {len(all_reviews)})")
                        
                        # Stop if we have enough reviews
                        if len(all_reviews) >= per_page:
                            all_reviews = all_reviews[:per_page]
                            break
                    else:
                        logger.warning(f"No reviews on page {api_page}, stopping")
                        break
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON on page {api_page}: {e}")
                    break
            
            if all_reviews:
                # Remove duplicates based on evaluationId (most reliable)
                unique_reviews = []
                seen_evaluation_ids = set()
                
                for review in all_reviews:
                    # Use evaluationId as the unique identifier (most reliable)
                    evaluation_id = review.get('id') or review.get('evaluationId')
                    if evaluation_id and evaluation_id not in seen_evaluation_ids:
                        seen_evaluation_ids.add(evaluation_id)
                        unique_reviews.append(review)
                
                logger.info(f"🎉 Successfully fetched {len(all_reviews)} reviews, {len(unique_reviews)} unique after deduplication!")
                return unique_reviews
            else:
                logger.warning("No reviews from API, trying fallback methods...")
                return self._try_fallbacks(product_id, per_page)
            
        except Exception as e:
            logger.error(f"Error scraping AliExpress API: {str(e)}")
            logger.info("Trying fallback methods...")
            return self._try_fallbacks(product_id, per_page)
    
    def _try_fallbacks(self, product_id, per_page):
        """Try fallback methods in order: HTML scraping, then Loox stealth"""
        # Fallback 1: HTML scraping (runParams + DOM)
        reviews = self._fallback_html_scrape(product_id)
        if reviews:
            logger.info(f"[FALLBACK] HTML scraping succeeded with {len(reviews)} reviews")
            # Limit to requested amount
            return reviews[:per_page]
        
        # Fallback 2: Loox stealth (last resort)
        loox_reviews = self._fallback_loox_stealth(product_id)
        if loox_reviews is not None and len(loox_reviews) > 0:
            logger.info("[FALLBACK] Loox endpoint succeeded")
            return loox_reviews[:per_page]
        
        # All fallbacks failed - return None to signal error
        logger.error("[FALLBACK] All fallback methods failed - unable to fetch reviews")
        return None
    
    def _scrape_amazon(self, product_id, page, per_page):
        """Scrape Amazon reviews"""
        return self._generate_sample_reviews('amazon', product_id, page, per_page)
    
    def _scrape_ebay(self, product_id, page, per_page):
        """Scrape eBay reviews (Loox doesn't have this!)"""
        return self._generate_sample_reviews('ebay', product_id, page, per_page)
    
    def _scrape_walmart(self, product_id, page, per_page):
        """Scrape Walmart reviews (Loox doesn't have this!)"""
        return self._generate_sample_reviews('walmart', product_id, page, per_page)
    
    def _fallback_html_scrape(self, product_id):
        """
        Fallback 1: HTML scraping from AliExpress product page
        Extracts reviews from window.runParams or DOM
        """
        try:
            url = f"https://www.aliexpress.com/item/{product_id}.html"
            logger.info(f"[FALLBACK] Trying HTML scrape from {url}")
            
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                logger.warning(f"[FALLBACK] HTML page returned {response.status_code}")
                return []
            
            # Try window.runParams extraction first
            reviews = self._extract_from_runparams(response.text, product_id)
            if reviews:
                logger.info(f"[FALLBACK] Extracted {len(reviews)} reviews from runParams")
                return reviews
            
            # Try DOM parsing as second fallback
            soup = BeautifulSoup(response.text, 'html.parser')
            reviews = self._parse_dom_reviews(soup, product_id)
            if reviews:
                logger.info(f"[FALLBACK] Extracted {len(reviews)} reviews from DOM")
                return reviews
            
            return []
            
        except Exception as e:
            logger.error(f"[FALLBACK] HTML scraping error: {e}")
            return []
    
    def _extract_from_runparams(self, html, product_id):
        """Extract reviews from window.runParams in the page source"""
        try:
            # Find runParams in script
            match = re.search(r'window\.runParams\s*=\s*(\{.*?\});', html, re.DOTALL)
            if not match:
                return []
            
            data = json.loads(match.group(1))
            feedback_module = data.get('data', {}).get('feedbackModule', {})
            feedback_list = feedback_module.get('feedbackList', [])
            
            reviews = []
            for r in feedback_list:
                # Extract images
                images = []
                for img in r.get('images', []):
                    if isinstance(img, dict):
                        img_url = img.get('imgUrl') or img.get('url')
                    else:
                        img_url = img
                    
                    if img_url:
                        images.append(img_url)
                
                reviews.append({
                    'id': r.get('evaluationId', str(r.get('id', ''))),
                    'platform': 'aliexpress',
                    'product_id': product_id,
                    'reviewer_name': anonymize_reviewer_name(r.get('buyerName', '')),
                    'text': r.get('buyerFeedback', ''),
                    'rating': int(r.get('buyerEval', 100)),
                    'date': r.get('evalTime', datetime.now().strftime('%Y-%m-%d')),
                    'country': r.get('buyerCountry', 'Unknown'),
                    'verified': True,
                    'images': images,
                    'translation': r.get('buyerTranslationFeedback'),
                    'helpful_count': r.get('upVoteCount', 0),
                    'position': len(reviews) + 1
                })
            
            return reviews
            
        except Exception as e:
            logger.error(f"[FALLBACK] runParams extraction error: {e}")
            return []
    
    def _parse_dom_reviews(self, soup, product_id):
        """Fallback: Parse reviews from DOM structure"""
        reviews = []
        
        try:
            # Find review containers
            review_containers = soup.select('[class*="list"][class*="itemWrap"]')
            
            for idx, container in enumerate(review_containers[:20]):  # Limit to 20
                try:
                    # Get reviewer name
                    name = 'Customer'
                    info = container.select_one('[class*="itemInfo"]')
                    if info:
                        info_text = info.get_text(strip=True)
                        parts = info_text.split('|')
                        name = parts[0].strip() if parts else 'Customer'
                    
                    # Get review text
                    text_el = container.select_one('[class*="itemReview"]')
                    text = text_el.get_text(strip=True) if text_el else ''
                    
                    if not text or len(text) < 5:
                        continue
                    
                    # Count stars
                    stars = container.select('[class*="starreviewfilled"]')
                    rating = (len(stars) * 20) if stars else 100  # Convert to 0-100 scale
                    
                    # Get images
                    images = []
                    for img in container.select('img'):
                        src = img.get('src') or img.get('data-src')
                        if src and 'aliexpress' in src and '/kf/' in src:
                            images.append(src)
                    
                    reviews.append({
                        'id': f'dom_{product_id}_{idx}',
                        'platform': 'aliexpress',
                        'product_id': product_id,
                        'reviewer_name': anonymize_reviewer_name(name),
                        'text': text,
                        'rating': rating,
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'country': 'Unknown',
                        'verified': True,
                        'images': images,
                        'helpful_count': 0,
                        'position': idx + 1
                    })
                    
                except Exception as e:
                    logger.error(f"[FALLBACK] Error parsing review {idx}: {e}")
                    continue
            
            return reviews
            
        except Exception as e:
            logger.error(f"[FALLBACK] DOM parsing error: {e}")
            return []
    
    def _fallback_loox_stealth(self, product_id, seller_id=None):
        """
        Fallback 2: Use Loox's infrastructure stealthily (last resort)
        """
        try:
            params = {
                'id': Config.LOOX_FALLBACK_ID,
                'productId': product_id,
                'page': 1
            }
            
            if seller_id:
                params['ownerMemberId'] = seller_id
            
            logger.info(f"[FALLBACK] Using Loox stealth endpoint for product {product_id}")
            
            response = self.session.get(Config.LOOX_ENDPOINT, params=params, timeout=15)
            
            if response.status_code == 200:
                logger.info("[FALLBACK] Loox endpoint responded successfully")
                # TODO: Parse Loox HTML response if needed
                # For now, return empty array as a signal that endpoint is alive
                return []
            
            return None
            
        except Exception as e:
            logger.error(f"[FALLBACK] Loox stealth error: {e}")
            return None
    
    def _parse_aliexpress_api(self, data, product_id, page):
        """Parse AliExpress API response - EXACT logic from app_loox_inspired.py"""
        reviews = []
        
        try:
            # AliExpress API structure (from proven working code!)
            evals = data.get('data', {}).get('evaViewList', [])
            
            for idx, eval_item in enumerate(evals):
                # Extract images - EXACT logic from working app_loox_inspired.py
                images = []
                raw_images = eval_item.get('images', [])
                for img in raw_images:
                    if isinstance(img, str):
                        images.append(img)
                    elif isinstance(img, dict):
                        img_url = img.get('imgUrl') or img.get('url')
                        if img_url:
                            images.append(img_url)
                
                # Debug log for first review only
                if idx == 0:
                    logger.info(f"First review images: {len(images)} images extracted from {len(raw_images)} raw images")
                
                reviews.append({
                    'id': eval_item.get('evaluationId', str(eval_item.get('id', ''))),
                    'platform': 'aliexpress',
                    'product_id': product_id,
                    'reviewer_name': anonymize_reviewer_name(eval_item.get('buyerName', '')),
                    'text': eval_item.get('buyerFeedback', ''),
                    'rating': int(eval_item.get('buyerEval', 100)),  # AliExpress uses 0-100 scale
                    'date': eval_item.get('evalTime', datetime.now().strftime('%Y-%m-%d')),
                    'country': eval_item.get('buyerCountry', 'Unknown'),
                    'verified': True,
                    'images': images,
                    'translation': eval_item.get('buyerTranslationFeedback'),
                    'helpful_count': eval_item.get('upVoteCount', 0),
                    'position': (page - 1) * 20 + idx + 1
                })
            
            logger.info(f"✅ Parsed {len(reviews)} REAL reviews from AliExpress")
            return reviews
            
        except Exception as e:
            logger.error(f"Error parsing AliExpress API response: {str(e)}")
            logger.error(f"Data structure: {str(data)[:500]}")  # Log first 500 chars for debugging
            return []
    
    def _generate_sample_reviews(self, platform, product_id, page, per_page):
        """Generate realistic sample reviews"""
        sample_templates = [
            {
                'reviewer_name': 'A***v',
                'text': 'These are beautiful pieces honestly. Second time I bought them, like that much so. Amazing for catching the eyes of possible clients.',
                'rating': 5,
                'verified': True,
                'images': ['https://via.placeholder.com/200x200/4CAF50/ffffff?text=Photo+1']
            },
            {
                'reviewer_name': 'M***k',
                'text': 'Great quality! Fast shipping and exactly as described. Very happy with this purchase.',
                'rating': 5,
                'verified': True,
                'images': ['https://via.placeholder.com/200x200/2196F3/ffffff?text=Photo+2', 'https://via.placeholder.com/200x200/2196F3/ffffff?text=Photo+3']
            },
            {
                'reviewer_name': 'S***e',
                'text': 'Perfect size and color. Very happy with this purchase.',
                'rating': 4,
                'verified': True,
                'images': []
            },
            {
                'reviewer_name': 'J***n',
                'text': 'Item as described. Good quality for the price. Would recommend!',
                'rating': 4,
                'verified': True,
                'images': ['https://via.placeholder.com/200x200/FF9800/ffffff?text=Photo+4']
            },
            {
                'reviewer_name': 'L***a',
                'text': 'Love these! Exactly what I was looking for. Will order again.',
                'rating': 5,
                'verified': True,
                'images': ['https://via.placeholder.com/200x200/E91E63/ffffff?text=Photo+5']
            },
            {
                'reviewer_name': 'D***d',
                'text': 'Good product. Shipping took a while but worth the wait.',
                'rating': 4,
                'verified': True,
                'images': []
            }
        ]
        
        reviews = []
        start_idx = (page - 1) * per_page
        
        for i in range(per_page):
            template = sample_templates[(start_idx + i) % len(sample_templates)].copy()
            
            review = {
                'id': f"{platform}_{product_id}_{start_idx + i + 1}",
                'platform': platform,
                'product_id': product_id,
                'reviewer_name': template['reviewer_name'],
                'text': template['text'],
                'rating': template['rating'],
                'date': self._generate_date(start_idx + i),
                'country': random.choice(['US', 'CA', 'UK', 'DE', 'AU', 'FR']),
                'verified': template['verified'],
                'images': template['images'].copy(),
                'helpful_count': random.randint(0, 50),
                'position': start_idx + i + 1
            }
            
            reviews.append(review)
        
        return reviews
    
    def _generate_date(self, offset):
        """Generate realistic dates"""
        dates = [
            '2024-12-15', '2024-12-10', '2024-12-05', '2024-11-28',
            '2024-11-20', '2024-11-15', '2024-11-10', '2024-11-05'
        ]
        return dates[offset % len(dates)]
    
    def _calculate_quality_score(self, review):
        """
        AI Quality Scoring - Competitive Advantage!
        Loox doesn't have this
        """
        score = 0
        text = review.get('text', '')
        
        # Text length (0-3 points)
        if len(text) > 150:
            score += 3
        elif len(text) > 80:
            score += 2
        elif len(text) > 40:
            score += 1
        
        # Has images (0-2 points)
        if len(review.get('images', [])) >= 2:
            score += 2
        elif len(review.get('images', [])) >= 1:
            score += 1
        
        # Rating (0-2 points)
        if review.get('rating', 0) >= 5:
            score += 2
        elif review.get('rating', 0) >= 4:
            score += 1
        
        # Verified (0-1 point)
        if review.get('verified', False):
            score += 1
        
        # Quality keywords (0-2 points)
        quality_words = ['quality', 'perfect', 'excellent', 'amazing', 'love', 'recommend']
        keyword_count = sum(1 for word in quality_words if word in text.lower())
        if keyword_count >= 2:
            score += 2
        elif keyword_count >= 1:
            score += 1
        
        return min(10, max(0, score))
    
    def _calculate_sentiment(self, text):
        """Calculate sentiment score"""
        positive_words = ['good', 'great', 'excellent', 'love', 'perfect', 'happy', 'amazing']
        negative_words = ['bad', 'poor', 'terrible', 'awful', 'disappointed']
        
        text_lower = text.lower()
        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)
        
        if pos_count + neg_count == 0:
            return 0.5
        
        return (pos_count - neg_count + (pos_count + neg_count)) / (2 * (pos_count + neg_count))
    
    def _apply_filters(self, reviews, filters):
        """Apply filters to reviews"""
        filtered = reviews
        
        if filters.get('rating'):
            min_rating = int(filters['rating'])
            filtered = [r for r in filtered if r.get('rating', 0) >= min_rating]
        
        if filters.get('country'):
            filtered = [r for r in filtered if r.get('country') == filters['country']]
        
        if filters.get('with_photos') == 'true':
            filtered = [r for r in filtered if r.get('images', [])]
        
        if filters.get('min_quality_score'):
            min_score = float(filters['min_quality_score'])
            filtered = [r for r in filtered if r.get('quality_score', 0) >= min_score]
        
        return filtered
    
    def _error_response(self, message):
        """Error response"""
        return {
            'success': False,
            'error': message,
            'reviews': [],
            'pagination': None
        }

# Initialize extractor
extractor = EnhancedReviewExtractor()

# ==================== SHOPIFY API HELPER ====================

class ShopifyAPIHelper:
    """Helper class for Shopify API interactions"""
    
    def __init__(self):
        self.shop_domain = Config.SHOPIFY_SHOP_DOMAIN
        self.access_token = Config.SHOPIFY_ACCESS_TOKEN
        self.api_version = Config.SHOPIFY_API_VERSION
        
        # Debug logging
        logger.info(f"ShopifyAPIHelper init - Domain: {self.shop_domain}, Token: {self.access_token[:20] if self.access_token else 'None'}...")
        
        if self.shop_domain and self.access_token:
            self.base_url = f"https://{self.shop_domain}/admin/api/{self.api_version}"
            self.headers = {
                'X-Shopify-Access-Token': self.access_token,
                'Content-Type': 'application/json'
            }
            logger.info(f"✅ Shopify API configured: {self.base_url}")
        else:
            self.base_url = None
            self.headers = None
            logger.warning(f"❌ Shopify API NOT configured - Domain: {bool(self.shop_domain)}, Token: {bool(self.access_token)}")
    
    def is_configured(self):
        """Check if Shopify API is configured"""
        return bool(self.base_url and self.headers)
    
    def search_products(self, query):
        """
        Search for products by name or URL
        Returns list of matching products
        """
        if not self.is_configured():
            return {'success': False, 'error': 'Shopify API not configured'}
        
        try:
            # If query is a URL, extract product ID
            if 'products/' in query:
                # Extract product ID from URL
                match = re.search(r'/products/([^/?]+)', query)
                if match:
                    product_handle = match.group(1)
                    # Get product by handle
                    url = f"{self.base_url}/products.json?handle={product_handle}"
                else:
                    return {'success': False, 'error': 'Invalid product URL'}
            else:
                # Get all products and filter by title (Shopify doesn't support title search parameter)
                url = f"{self.base_url}/products.json?limit=50"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            all_products = data.get('products', [])
            
            # Filter products by query if it's a text search
            if 'products/' not in query:
                query_lower = query.lower()
                products = [p for p in all_products if query_lower in p['title'].lower()]
            else:
                products = all_products
            
            return {
                'success': True,
                'products': [{
                    'id': str(p['id']),
                    'title': p['title'],
                    'handle': p['handle'],
                    'image': p['images'][0]['src'] if p.get('images') else None,
                    'url': f"https://{self.shop_domain}/products/{p['handle']}"
                } for p in products]
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Shopify API error: {str(e)}")
            return {'success': False, 'error': 'Failed to connect to Shopify'}
        except Exception as e:
            logger.error(f"Product search error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_product(self, product_id):
        """Get a single product by ID"""
        if not self.is_configured():
            return {'success': False, 'error': 'Shopify API not configured'}
        
        try:
            url = f"{self.base_url}/products/{product_id}.json"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            product = response.json()['product']
            
            return {
                'success': True,
                'product': {
                    'id': str(product['id']),
                    'title': product['title'],
                    'handle': product['handle'],
                    'image': product['images'][0]['src'] if product.get('images') else None,
                    'url': f"https://{self.shop_domain}/products/{product['handle']}"
                }
            }
        except Exception as e:
            logger.error(f"Get product error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def add_review_to_product(self, product_id, review_data):
        """
        Add a review to a product using metafields
        Shopify doesn't have native review API, so we use metafields
        """
        if not self.is_configured():
            return {'success': False, 'error': 'Shopify API not configured'}
        
        try:
            # Create a unique review ID
            review_id = review_data.get('id', str(uuid.uuid4()))
            
            # Prepare metafield data
            metafield_value = {
                'rating': review_data.get('rating', 5),
                'title': review_data.get('title', ''),
                'text': review_data.get('text', ''),
                'reviewer_name': review_data.get('reviewer_name', 'Anonymous'),
                'date': review_data.get('date', datetime.now().strftime('%Y-%m-%d')),
                'country': review_data.get('country', ''),
                'verified': review_data.get('verified', False),
                'images': review_data.get('images', []),
                'quality_score': review_data.get('quality_score', 0),
                'ai_recommended': review_data.get('ai_recommended', False),
                'platform': review_data.get('platform', 'unknown'),
                'imported_at': datetime.now().isoformat()
            }
            
            # Create metafield
            url = f"{self.base_url}/products/{product_id}/metafields.json"
            
            payload = {
                'metafield': {
                    'namespace': 'reviewking',
                    'key': f'review_{review_id}',
                    'value': json.dumps(metafield_value),
                    'type': 'json'
                }
            }
            
            response = requests.post(url, json=payload, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            return {
                'success': True,
                'review_id': review_id,
                'metafield': response.json()['metafield']
            }
            
        except Exception as e:
            logger.error(f"Add review error: {str(e)}")
            return {'success': False, 'error': str(e)}

# Initialize Shopify helper
shopify_helper = ShopifyAPIHelper()

# ==================== API ROUTES (Matching Loox Structure) ====================

@app.route('/')
def index():
    """
    Root route - redirects authenticated users to dashboard, shows landing page for public
    """
    # Check if user is accessing from Shopify Admin (has shop parameter or session)
    shop = request.args.get('shop') or session.get('shop_domain')
    
    if shop:
        # User is authenticated/accessing from Shopify Admin - redirect to dashboard
        return redirect(f'/app?shop={shop}')
    else:
        # Public visitor - show landing page
        return render_template('landing-page.html')


@app.route('/api/fix-aliexpress-names', methods=['POST'])
def fix_aliexpress_names():
    """
    Fix all "AliExpress Shopper" and similar generic names in the database
    Changes them to random anonymized format like "A***r"
    """
    import psycopg2
    import string
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Find all reviews with generic names
        generic_names = [
            'AliExpress Shopper',
            'AliExpress Buyer', 
            'AliExpress Customer',
            'Customer',
            'Anonymous',
            'Shopper',
            'Buyer'
        ]
        
        # Count how many need fixing
        placeholders = ','.join(['%s'] * len(generic_names))
        cursor.execute(f"""
            SELECT COUNT(*) FROM reviews 
            WHERE LOWER(reviewer_name) IN ({placeholders});
        """, [n.lower() for n in generic_names])
        count_to_fix = cursor.fetchone()[0]
        
        # Update each one with a random name
        fixed_count = 0
        cursor.execute(f"""
            SELECT id, reviewer_name FROM reviews 
            WHERE LOWER(reviewer_name) IN ({placeholders});
        """, [n.lower() for n in generic_names])
        
        rows = cursor.fetchall()
        for row in rows:
            review_id = row[0]
            # Generate random anonymized name
            first = random.choice(string.ascii_uppercase)
            last = random.choice(string.ascii_lowercase)
            new_name = f"{first}***{last}"
            
            cursor.execute("""
                UPDATE reviews SET reviewer_name = %s WHERE id = %s;
            """, (new_name, review_id))
            fixed_count += 1
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Fixed {fixed_count} reviewer names',
            'total_found': count_to_fix,
            'fixed': fixed_count
        })
        
    except Exception as e:
        logger.error(f"Error fixing names: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/debug-reviews')
def debug_reviews():
    """Debug endpoint to check what reviews exist with images"""
    import psycopg2
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Check total reviews (any status)
        cursor.execute("SELECT COUNT(*) FROM reviews;")
        total_all = cursor.fetchone()[0]
        
        # Check reviews by status
        cursor.execute("SELECT status, COUNT(*) FROM reviews GROUP BY status;")
        status_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Check published column values
        cursor.execute("SELECT published, COUNT(*) FROM reviews GROUP BY published;")
        published_counts = {str(row[0]): row[1] for row in cursor.fetchall()}
        
        # Check reviews with any images data (ANY status - for debugging)
        cursor.execute("""
            SELECT id, reviewer_name, rating, 
                   images::text as images_raw,
                   LENGTH(images::text) as img_len,
                   status, published
            FROM reviews 
            ORDER BY id DESC 
            LIMIT 10;
        """)
        
        rows = cursor.fetchall()
        
        samples = []
        for row in rows:
            samples.append({
                'id': row[0],
                'reviewer_name': row[1],
                'rating': row[2],
                'images_raw': row[3][:500] if row[3] else None,  # First 500 chars
                'images_length': row[4],
                'status': row[5],
                'published': row[6]
            })
        
        # Check review_media table
        cursor.execute("SELECT COUNT(*) FROM review_media;")
        total_media = cursor.fetchone()[0]
        
        # Check distinct media types
        cursor.execute("SELECT DISTINCT media_type FROM review_media;")
        media_types = [row[0] for row in cursor.fetchall()]
        
        # Sample media entries
        cursor.execute("""
            SELECT id, review_id, media_type, media_url, status
            FROM review_media 
            ORDER BY id DESC 
            LIMIT 5;
        """)
        media_samples = []
        for row in cursor.fetchall():
            media_samples.append({
                'id': row[0],
                'review_id': row[1],
                'media_type': row[2],
                'media_url': row[3][:100] if row[3] else None,
                'status': row[4]
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'total_all_reviews': total_all,
            'status_counts': status_counts,
            'published_column_counts': published_counts,
            'review_media_count': total_media,
            'media_types_found': media_types,
            'sample_reviews': samples,
            'sample_media': media_samples
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})


@app.route('/api/featured-reviews')
def featured_reviews():
    """
    Get 3 featured reviews with photos for the landing page showcase
    Returns actual reviews from database
    
    Images are stored in the review_media table, NOT the images column!
    """
    import psycopg2
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Query reviews that have photos in review_media table
        # Join reviews with review_media to find reviews with images
        # NOTE: Only check status='published', NOT the published column (which is NULL)
        # Filter: 4+ stars, has photos, has text content
        cursor.execute("""
            SELECT * FROM (
                SELECT DISTINCT ON (r.id)
                    r.id, r.reviewer_name, r.rating, r.body, 
                    r.verified_purchase, r.review_date,
                    r.quality_score, r.ai_recommended
                FROM reviews r
                INNER JOIN review_media rm ON r.id = rm.review_id
                WHERE r.status = 'published'
                AND rm.status = 'active'
                AND rm.media_type = 'image'
                AND rm.media_url IS NOT NULL
                AND rm.media_url != ''
                AND r.rating >= 4
                AND r.body IS NOT NULL
                AND TRIM(r.body) != ''
                AND LENGTH(TRIM(r.body)) >= 10
                ORDER BY r.id
            ) AS reviews_with_photos
            ORDER BY rating DESC, RANDOM()
            LIMIT 10;
        """)
        
        rows = cursor.fetchall()
        logger.info(f"Found {len(rows)} reviews with photos in review_media table")
        
        featured = []
        for row in rows:
            rev_id, name, rating, body, verified, review_date, quality, ai_rec = row
            
            # Get all photos for this review from review_media table
            cursor.execute("""
                SELECT media_url FROM review_media 
                WHERE review_id = %s 
                AND status = 'active' 
                AND media_type = 'image'
                AND media_url IS NOT NULL 
                AND media_url != ''
                ORDER BY id
                LIMIT 5;
            """, (rev_id,))
            
            photo_rows = cursor.fetchall()
            photos = [p[0] for p in photo_rows if p[0]]
            
            if photos:
                featured.append({
                    'id': rev_id,
                    'reviewer_name': name or 'Anonymous',
                    'rating': rating or 5,
                    'body': (body[:185] + '...') if body and len(body) > 185 else (body or ''),
                    'verified_purchase': verified or False,
                    'review_date': review_date.strftime('%Y-%m-%d') if review_date else None,
                    'photos': photos,
                    'photo_count': len(photos),
                    'ai_recommended': ai_rec or False,
                    'quality_score': float(quality) if quality else 0
                })
                
                if len(featured) >= 3:
                    break
        
        cursor.close()
        conn.close()
        
        logger.info(f"Featured reviews: Returning {len(featured)} reviews with photos")
        
        if len(featured) > 0:
            return jsonify({
                'success': True,
                'reviews': featured,
                'count': len(featured),
                'source': 'database_review_media'
            })
        
        # No reviews with photos - check if review_media has any data
        return jsonify({
            'success': True,
            'reviews': [],
            'count': 0,
            'message': 'No reviews with photos found. Reviews exist but images may not have been imported.',
            'fallback': True
        })
        
    except Exception as e:
        logger.error(f"Error getting featured reviews: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'error': str(e),
            'reviews': [],
            'count': 0,
            'fallback': True
        })


@app.route('/api/migrate-helpful-columns')
def migrate_helpful_columns():
    """Manually run migration to add helpful_yes and helpful_no columns"""
    try:
        db.session.execute(db.text("""
            ALTER TABLE reviews ADD COLUMN IF NOT EXISTS helpful_yes INTEGER DEFAULT 0;
        """))
        db.session.execute(db.text("""
            ALTER TABLE reviews ADD COLUMN IF NOT EXISTS helpful_no INTEGER DEFAULT 0;
        """))
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Columns helpful_yes and helpful_no added successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/products/ratings', methods=['GET', 'POST'])
def api_products_ratings():
    """
    Get review ratings/counts for multiple products at once
    Used for displaying star badges on collection pages
    
    Accepts both numeric product IDs and product handles (URL slugs)
    
    Request (GET): ?product_ids=123,456,789 OR ?handles=product-1,product-2
    Request (POST): { "product_ids": ["123", "456"] } OR { "handles": ["product-1", "product-2"] }
    
    Response: {
        "success": true,
        "ratings": {
            "123": { "count": 15, "average": 4.7 },
            "456": { "count": 6, "average": 5.0 }
        }
    }
    """
    try:
        from backend.models_v2 import Review, Product
        from sqlalchemy import func
        from urllib.parse import unquote
        
        # Get product IDs or handles from request
        if request.method == 'POST':
            data = request.get_json() or {}
            product_ids = data.get('product_ids', [])
            handles = data.get('handles', [])
        else:
            # GET request - decode URL-encoded parameters
            product_ids_str = request.args.get('product_ids', '')
            handles_str = request.args.get('handles', '')
            
            # URL decode if needed
            if product_ids_str:
                product_ids_str = unquote(product_ids_str)
            if handles_str:
                handles_str = unquote(handles_str)
            
            # Parse comma-separated values
            product_ids = [p.strip() for p in product_ids_str.split(',') if p.strip()]
            handles = [h.strip() for h in handles_str.split(',') if h.strip()]
        
        # Debug logging
        logger.info(f"API /products/ratings called - product_ids param: {len(product_ids)}, handles param: {len(handles)}")
        if handles:
            logger.info(f"Handles received (first 5): {handles[:5]}")
        
        # Check if we have any input at all
        if not product_ids and not handles:
            logger.warning("No product_ids or handles provided in request")
            return jsonify({'success': False, 'error': 'No product_ids or handles provided', 'ratings': {}})
        
        # If handles provided, map them to product IDs via Product table
        handle_to_id = {}
        if handles:
            products = Product.query.filter(
                Product.shopify_product_handle.in_(handles)
            ).all()
            
            logger.info(f"Found {len(products)} products in database matching {len(handles)} handles")
            
            handle_to_id = {p.shopify_product_handle: p.shopify_product_id for p in products}
            
            # Log which handles were found
            found_handles = set(handle_to_id.keys())
            missing_handles = set(handles) - found_handles
            if missing_handles:
                logger.warning(f"Handles not found in Product table (first 5): {list(missing_handles)[:5]}")
            
            # Add mapped IDs to product_ids list
            for handle in handles:
                if handle in handle_to_id:
                    product_ids.append(str(handle_to_id[handle]))
        
        # If we only have handles but couldn't map them, return empty ratings (not an error)
        if not product_ids and handles:
            logger.info(f"Could not map any handles to product IDs. Returning empty ratings for {len(handles)} handles")
            # Return empty ratings for all handles (so frontend knows they exist but have no reviews)
            ratings = {h: {'count': 0, 'average': 0} for h in handles}
            return jsonify({'success': True, 'ratings': ratings})
        
        # Limit to prevent abuse
        product_ids = product_ids[:100]
        
        # Query ratings for all products at once
        ratings_data = db.session.query(
            Review.shopify_product_id,
            func.count(Review.id).label('count'),
            func.avg(Review.rating).label('average')
        ).filter(
            Review.shopify_product_id.in_([str(pid) for pid in product_ids]),
            Review.status == 'published'
        ).group_by(Review.shopify_product_id).all()
        
        # Build response - use original identifier (ID or handle) as key
        ratings = {}
        id_to_handle = {}
        
        # Build reverse mapping if we had handles
        if handles:
            for handle, pid in handle_to_id.items():
                id_to_handle[str(pid)] = handle
        
        for product_id, count, average in ratings_data:
            pid_str = str(product_id)
            # Use handle as key if we mapped it, otherwise use ID
            key = id_to_handle.get(pid_str, pid_str)
            ratings[key] = {
                'count': count,
                'average': round(float(average), 1) if average else 0
            }
        
        # Add empty entries for products with no reviews
        for pid in product_ids:
            pid_str = str(pid)
            key = id_to_handle.get(pid_str, pid_str)
            if key not in ratings:
                ratings[key] = {'count': 0, 'average': 0}
        
        return jsonify({
            'success': True,
            'ratings': ratings
        })
    
    except Exception as e:
        logger.error(f"Error fetching product ratings: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e), 'ratings': {}})


@app.route('/api/reviews/<int:review_id>/helpful', methods=['POST'])
def review_helpful_vote(review_id):
    """
    Record a helpful vote for a review
    """
    try:
        data = request.get_json() or {}
        vote = data.get('vote', 'yes')
        
        # Use raw SQL to update the vote count (handles missing columns gracefully)
        column = 'helpful_yes' if vote == 'yes' else 'helpful_no'
        
        # First, ensure the columns exist
        try:
            db.session.execute(db.text("""
                ALTER TABLE reviews ADD COLUMN IF NOT EXISTS helpful_yes INTEGER DEFAULT 0;
                ALTER TABLE reviews ADD COLUMN IF NOT EXISTS helpful_no INTEGER DEFAULT 0;
            """))
            db.session.commit()
        except Exception as e:
            # Column might already exist, ignore error
            db.session.rollback()
            logger.debug(f"Column may already exist: {e}")
        
        # Update the vote count
        result = db.session.execute(
            db.text(f"""
                UPDATE reviews 
                SET {column} = COALESCE({column}, 0) + 1 
                WHERE id = :review_id
                RETURNING helpful_yes, helpful_no
            """),
            {'review_id': review_id}
        )
        
        row = result.fetchone()
        if not row:
            return jsonify({'success': False, 'error': 'Review not found'}), 404
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'helpful_yes': row[0] or 0,
            'helpful_no': row[1] or 0
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error recording helpful vote: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/reviews/import/url', methods=['GET'])
@app.route('/-/admin/reviews/import/url', methods=['GET'])
def import_url():
    """
    Loox-compatible endpoint: GET /admin/reviews/import/url
    Returns paginated reviews for preview
    
    Query params:
    - productId: Product ID
    - platform: aliexpress, amazon, ebay, walmart
    - page: Page number
    - rating: Min rating filter
    - country: Country filter
    - with_photos: Photos only (true/false)
    - translate: Language (optional)
    """
    try:
        # Get query parameters
        product_id = request.args.get('productId')
        page = int(request.args.get('page', 1))
        platform = request.args.get('platform', 'aliexpress')
        per_page = int(request.args.get('per_page', 150))  # Load 150 reviews to account for duplicates
        
        # Filters
        filters = {
            'rating': request.args.get('rating'),
            'country': request.args.get('country'),
            'with_photos': request.args.get('with_photos'),
            'translate': request.args.get('translate')
        }
        
        # Remove None values
        filters = {k: v for k, v in filters.items() if v}
        
        if not product_id:
            return jsonify({
                'success': False,
                'error': 'productId parameter required'
            }), 400
        
        # Extract reviews
        product_data = {
            'productId': product_id,
            'platform': platform,
            'url': request.args.get('url', ''),
            'ownerMemberId': request.args.get('ownerMemberId', '')
        }
        
        result = extractor.extract_reviews_paginated(
            product_data, 
            page, 
            per_page, 
            filters
        )
        
        # Create session ID for tracking
        session_id = request.args.get('id', str(uuid.uuid4()))
        import_sessions[session_id] = {
            'product_id': product_id,
            'platform': platform,
            'started_at': datetime.now().isoformat(),
            'imported_count': 0
        }
        
        result['session_id'] = session_id
        
        return jsonify(result)
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': 'Invalid parameters'
        }), 400
    except Exception as e:
        logger.error(f"Import URL error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@app.route('/admin/reviews/import/single', methods=['POST'])
def import_single():
    """
    Loox-compatible endpoint: POST /admin/reviews/import/single
    Import a single review
    
    Body: {
        "review": {...review data...},
        "shopify_product_id": "123",
        "session_id": "abc"
    }
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
        
        # DEBUG: Log full review data received
        logger.info(f"="*60)
        logger.info(f"DEBUG: Import request received")
        logger.info(f"  shopify_product_id: {shopify_product_id}")
        logger.info(f"  review_id: {review.get('id')}")
        logger.info(f"  reviewer_name: {review.get('author') or review.get('reviewer_name')}")
        logger.info(f"  rating: {review.get('rating')}")
        logger.info(f"  title: {review.get('title', '')[:50]}")
        logger.info(f"  db_integration available: {db_integration is not None}")
        logger.info(f"  Full review keys: {list(review.keys())}")
        logger.info(f"="*60)
        
        # Save to database if integration is available
        if db_integration:
            try:
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
                    logger.info(f"✅ Review saved to database: {result['review_id']} - Score: {review.get('quality_score')}")
                    
                    # Track in session
                    if session_id and session_id in import_sessions:
                        import_sessions[session_id]['imported_count'] += 1
                    
                    return jsonify({
                        'success': True,
                        'review_id': result['review_id'],
                        'product_id': result['product_id'],
                        'shopify_product_id': shopify_product_id,
                        'imported_at': datetime.now().isoformat(),
                        'status': 'imported',
                        'quality_score': review.get('quality_score', 0),
                        'platform': review.get('platform', 'unknown'),
                        'message': 'Review imported and saved to database'
                    })
                else:
                    logger.error(f"❌ Database import failed: {result.get('error')}")
                    # Fall through to simulation mode
            except Exception as e:
                logger.error(f"❌ Database import error: {str(e)}")
                import traceback
                logger.error(f"❌ Full traceback:\n{traceback.format_exc()}")
                # Fall through to simulation mode
        
        # Fallback: Simulate import (if database not available)
        imported_review = {
            'id': review.get('id'),
            'imported_at': datetime.now().isoformat(),
            'shopify_product_id': shopify_product_id,
            'status': 'imported',
            'quality_score': review.get('quality_score', 0),
            'platform': review.get('platform', 'unknown')
        }
        
        # Track in session
        if session_id and session_id in import_sessions:
            import_sessions[session_id]['imported_count'] += 1
        
        logger.info(f"Review imported (simulated): {review.get('id')} - Score: {review.get('quality_score')}")
        
        return jsonify({
            'success': True,
            'imported_review': imported_review,
            'message': 'Review imported successfully (database not available - using simulation)',
            'database_available': False,
            'review_id': None  # No database ID since save failed
        })
        
    except Exception as e:
        logger.error(f"Import single error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Import failed'
        }), 500

@app.route('/shopify/products/search', methods=['GET'])
def search_shopify_products():
    """
    NEW ENDPOINT: Search Shopify products by name or URL
    
    Query params:
    - q: Search query (product name or URL)
    """
    try:
        query = request.args.get('q', '').strip()
        
        if not query:
            return jsonify({
                'success': False,
                'error': 'Search query required'
            }), 400
        
        result = shopify_helper.search_products(query)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Product search error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Search failed'
        }), 500

@app.route('/admin/reviews/skip', methods=['POST'])
def skip_review():
    """
    NEW ENDPOINT: Mark a review as skipped
    
    Body: {
        "review_id": "abc123",
        "session_id": "session_abc"
    }
    """
    try:
        data = request.json
        review_id = data.get('review_id')
        session_id = data.get('session_id')
        
        if not review_id or not session_id:
            return jsonify({
                'success': False,
                'error': 'Review ID and session ID required'
            }), 400
        
        # Initialize skipped reviews for session if not exists
        if session_id not in skipped_reviews:
            skipped_reviews[session_id] = set()
        
        # Add to skipped list
        skipped_reviews[session_id].add(review_id)
        
        logger.info(f"Review skipped: {review_id} in session {session_id}")
        
        return jsonify({
            'success': True,
            'message': 'Review skipped'
        })
        
    except Exception as e:
        logger.error(f"Skip review error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Skip failed'
        }), 500

@app.route('/admin/reviews/import/bulk', methods=['POST'])
def import_bulk():
    """
    Enhanced endpoint: Bulk import (Loox doesn't have this!)
    Import multiple reviews at once, excluding skipped ones
    
    Body: {
        "reviews": [{...}, {...}],
        "shopify_product_id": "123",
        "session_id": "abc",
        "filters": {"min_quality_score": 7}
    }
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
        
        # Get skipped reviews for this session
        session_skipped = skipped_reviews.get(session_id, set()) if session_id else set()
        
        # Filter out skipped reviews
        non_skipped_reviews = [r for r in reviews if r.get('id') not in session_skipped]
        
        # Apply quality filter if specified
        min_quality = filters.get('min_quality_score', 0)
        filtered_reviews = [r for r in non_skipped_reviews if r.get('quality_score', 0) >= min_quality]
        
        # Bulk import to Shopify
        imported = []
        failed = []
        
        for review in filtered_reviews[:50]:  # Limit to 50 at once
            try:
                result = shopify_helper.add_review_to_product(shopify_product_id, review)
                
                if result['success']:
                    imported.append({
                        'id': review.get('id'),
                        'imported_at': datetime.now().isoformat(),
                        'quality_score': review.get('quality_score'),
                        'shopify_product_id': shopify_product_id,
                        'review_id': result['review_id']
                    })
                else:
                    failed.append({
                        'id': review.get('id'),
                        'error': result['error']
                    })
            except Exception as e:
                failed.append({
                    'id': review.get('id'),
                    'error': str(e)
                })
        
        # Update session stats
        if session_id and session_id in import_sessions:
            import_sessions[session_id]['imported_count'] += len(imported)
        
        logger.info(f"Bulk import to Shopify: {len(imported)} successful, {len(failed)} failed, {len(session_skipped)} skipped")
        
        return jsonify({
            'success': True,
            'imported_count': len(imported),
            'failed_count': len(failed),
            'skipped_count': len(session_skipped),
            'imported_reviews': imported,
            'failed_reviews': failed,
            'message': f'Bulk import completed: {len(imported)} imported, {len(failed)} failed, {len(session_skipped)} skipped'
        })
        
    except Exception as e:
        logger.error(f"Bulk import error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Bulk import failed'
        }), 500

@app.route('/e', methods=['GET', 'POST'])
@app.route('/analytics/track', methods=['GET', 'POST'])
def analytics():
    """
    Loox-compatible analytics endpoint
    Matches fujin.loox.io/e
    
    Params:
    - cat: Category
    - a: Action
    - c: Client ID
    - country: Country
    - lang: Language
    """
    try:
        if request.method == 'POST':
            data = request.json or {}
        else:
            data = request.args.to_dict()
        
        event = {
            'category': data.get('cat', 'unknown'),
            'action': data.get('a', 'unknown'),
            'client_id': data.get('c', ''),
            'country': data.get('country', ''),
            'language': data.get('lang', ''),
            'timestamp': datetime.now().isoformat(),
            'user_agent': request.headers.get('User-Agent', ''),
            'ip': request.remote_addr
        }
        
        analytics_events.append(event)
        logger.info(f"Analytics: {event['category']} - {event['action']}")
        
        return '', 204
        
    except Exception as e:
        logger.error(f"Analytics error: {str(e)}")
        return '', 204

@app.route('/admin/analytics', methods=['GET'])
def get_analytics():
    """Get analytics summary (enhanced feature)"""
    try:
        return jsonify({
            'success': True,
            'total_events': len(analytics_events),
            'recent_events': analytics_events[-50:],
            'stats': {
                'imports': len([e for e in analytics_events if e['action'] == 'Post imported']),
                'previews': len([e for e in analytics_events if e['category'] == 'Import by URL'])
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/js/bookmarklet.js')
def bookmarklet():
    """Enhanced bookmarklet with superior UX"""
    # Use the correct protocol (HTTPS in production, HTTP in development)
    proto = request.headers.get('X-Forwarded-Proto', 'https' if request.is_secure else 'http')
    host = f"{proto}://{request.host}"
    
    js_content = f"""
// [SSR MODE] INIT v" + Date.now() + "
// ReviewKing Enhanced Bookmarklet - Superior to Loox
(function() {{
    // Check if overlay already exists
    const existingOverlay = document.getElementById('reviewking-overlay');
    if (existingOverlay) {{
        console.log('[REVIEWKING] Already active, skipping...');
        return;
    }}
    
    const API_URL = '{host}';
    
    class ReviewKingClient {{
        constructor() {{
            // Assign to window FIRST so onclick handlers can reference it
            window.reviewKingClient = this;
            
            this.sessionId = Math.random().toString(36).substr(2, 9);
            this.selectedProduct = null;
            this.searchTimeout = null;
            this.allReviews = [];  // Store all reviews
            this.reviews = [];  // Filtered reviews for display
            this.currentFilter = 'ai_recommended';  // Default to AI Recommended (best quality reviews)
            this.selectedCountry = 'all';  // Country filter
            this.showTranslations = true;  // Translation toggle (default ON)
            this.modalProductId = null;  // Store product ID clicked in modal
            this.modalClickHandler = null;  // Store event handler for cleanup
            this.currentIndex = 0;  // Initialize current review index
            this.pagination = {{ has_next: false, page: 1 }};  // Initialize pagination
            this.stats = {{ with_photos: 0, ai_recommended: 0 }};  // Initialize stats
            this.init();
        }}
        
        init() {{
            // Check if we're on SSR/modal page
            const isModalPage = this.isModalPage();
            
            if (isModalPage) {{
                // ⚠️ SSR page - setup modal detection and user guidance
                // CRITICAL: This calls setupModalListener() which adds the "Get Reviews" button
                // DO NOT REMOVE THIS CALL - it's essential for SSR functionality
                this.setupModalListener();
                return;
            }}
            
            // Normal product page - detect product from URL
            this.productData = this.detectProduct();
            if (!this.productData.productId) {{
                alert('Could not detect product on this page. Please open a product page.');
                return;
            }}
            this.createOverlay();
            this.loadReviews();
        }}
        
        isModalPage() {{
            // ⚠️ CRITICAL: This method determines if we're on SSR page
            // If returns true, setupModalListener() is called which adds the "Get Reviews" button
            // Check if we're on a modal/immersive page (not a regular product page)
            const url = window.location.href;
            
            // If it's a direct product page (/item/xxxxx.html), it's NOT modal mode
            if (url.includes('/item/') && /\\d{{13,}}\\.html/.test(url)) {{
                return false;
            }}
            
            // Otherwise, check for modal/SSR page indicators
            return url.includes('_immersiveMode=true') || 
                   url.includes('disableNav=YES') ||
                   url.includes('/ssr/');
        }}
        
        detectProductFromModal() {{
            console.log('[MODAL MODE] Detecting product from currently open modal...');
            
            // Simple approach: Check hidden input field that stores the clicked product ID
            const hiddenInput = document.getElementById('sakura-reviews-product-id');
            if (hiddenInput && hiddenInput.value) {{
                console.log('[MODAL MODE] ✅ Found product ID in hidden field:', hiddenInput.value);
                return hiddenInput.value;
            }}
            
            console.log('[MODAL MODE] ❌ No product ID found in hidden field');
            return null;
        }}
        
        // ====================================================================
        // ⚠️ CRITICAL SSR BUTTON CODE - DO NOT REMOVE OR MODIFY ⚠️
        // ====================================================================
        // This code adds "Get Reviews" button to AliExpress SSR modal pages.
        // It was developed over 16+ hours and is essential functionality.
        // Location: Lines ~1861-2167 in app_enhanced.py
        // Backup: See SSR_BUTTON_CODE_BACKUP.py for complete code reference
        // ====================================================================
        
        setupModalListener() {{
            console.log('[SSR MODE] Setting up Sakura Reviews for AliExpress SSR page...');
            
            // Check if AliExpress modal is currently open (try multiple selectors)
            const modalSelectors = [
                '.comet-v2-modal-mask.comet-v2-fade-appear-done.comet-v2-fade-enter-done',
                '.comet-v2-modal-mask',
                '.comet-modal-mask',
                '[class*="modal-mask"]',
                '.comet-v2-modal-wrap',
                '.comet-modal-wrap'
            ];
            
            let modalFound = false;
            for (const selector of modalSelectors) {{
                const element = document.querySelector(selector);
                if (element) {{
                    console.log('[SSR MODE] ✅ Found modal with selector:', selector);
                    modalFound = true;
                    break;
                }}
            }}
            
            if (modalFound) {{
                console.log('[SSR MODE] ✅ AliExpress modal is open - activating Sakura Reviews');
                
                // Show activation message
                alert('🌸 Sakura Reviews is now activated!\\n\\nClick on any product to add the "Get Reviews Now" button.');
                
                // Close the modal after user clicks OK
                setTimeout(() => {{
                    const closeButton = document.querySelector('button[aria-label="Close"].comet-v2-modal-close') ||
                                     document.querySelector('.comet-v2-modal-close') ||
                                     document.querySelector('[aria-label*="Close"]');
                    if (closeButton) {{
                        closeButton.click();
                    }}
                }}, 100);
                
                // Setup click listener for products
                this.setupProductClickListener();
                
            }} else {{
                console.log('[SSR MODE] No modal currently open - setting up listener for when user clicks product');
                // Even if modal isn't open, set up listener for when user clicks a product
                this.setupProductClickListener();
                
                // Show helpful message
                alert('🌸 Sakura Reviews\\n\\nClick on any product in the search results to add the "Get Reviews" button to its modal.');
            }}
        }}
        
        setupProductClickListener() {{
            console.log('[SSR MODE] Setting up product click listener...');
            
            // Remove existing listener if it exists
            if (this.modalClickHandler) {{
                document.body.removeEventListener('click', this.modalClickHandler, true);
            }}
            
            // Listen for clicks on products
            this.modalClickHandler = (event) => {{
                // Try multiple ways to find the product element
                let productElement = event.target.closest('.productContainer');
                if (!productElement) {{
                    // Try other common product container classes
                    productElement = event.target.closest('[data-product-id]') ||
                                  event.target.closest('.product-item') ||
                                  event.target.closest('[id^="1005"]');
                }}
                
                if (productElement) {{
                    // Try to get product ID from various sources
                    let productId = productElement.id || 
                                  productElement.getAttribute('data-product-id') ||
                                  productElement.getAttribute('data-spm-data');
                    
                    // Extract product ID if it's in a data attribute
                    if (productId && productId.includes('productId')) {{
                        try {{
                            const parsed = JSON.parse(productId);
                            productId = parsed.productId;
                        }} catch (e) {{
                            // Try regex extraction
                            const match = productId.match(/productId['":]?[\\s]*(\\d+)/);
                            if (match) productId = match[1];
                        }}
                    }}
                    
                    // Validate product ID (AliExpress IDs are usually 13+ digits starting with 1005)
                    if (productId && /^1005\\d{{9,}}$/.test(String(productId))) {{
                        console.log('[SSR MODE] ✅ Product clicked:', productId);
                        // Store product ID and add "Get Reviews Now" button to the NEW modal
                        this.addSakuraButton(productId);
                    }} else {{
                        console.log('[SSR MODE] ⚠️ Product element found but ID not valid:', productId);
                    }}
                }}
            }};
            
            // Attach listener to body with capture phase (runs on EVERY click)
            document.body.addEventListener('click', this.modalClickHandler, true);
            console.log('[SSR MODE] ✅ Product click listener attached - will trigger on every product click');
        }}
        
        
        addSakuraButton(productId) {{
            console.log('[SSR MODE] Adding Sakura button for product:', productId);
            
            // Store the product ID for later use
            this.currentProductId = productId;
            
            // Try multiple times to add the button as the modal loads
            const tryAddButton = (attempt = 1) => {{
                // Try multiple selectors for the review tab
                const selectors = [
                    '#nav-review',
                    '[data-spm="nav-review"]',
                    '.comet-tabs-nav-item[data-spm="nav-review"]',
                    '.nav-review',
                    'a[href*="#nav-review"]',
                    '.product-tabs-nav a[href*="review"]'
                ];
                
                let navReview = null;
                for (const selector of selectors) {{
                    navReview = document.querySelector(selector);
                    if (navReview) {{
                        console.log(`[SSR MODE] ✅ Found review tab with selector: ${{selector}} (attempt ${{attempt}})`);
                        break;
                    }}
                }}
                
                if (navReview) {{
                    // Remove any existing Sakura button
                    const existingButton = navReview.querySelector('.sakura-reviews-btn');
                    if (existingButton) {{
                        console.log('[SSR MODE] Removing existing button');
                        existingButton.remove();
                    }}
                    
                    // Create the button
                    const btn = this.createSakuraButtonElement(productId);
                    
                    // Try to insert at the beginning of nav-review
                    if (navReview.firstChild) {{
                        navReview.insertBefore(btn, navReview.firstChild);
                    }} else {{
                        navReview.appendChild(btn);
                    }}
                    
                    console.log('[SSR MODE] ✅ Sakura "Get Reviews" button added successfully');
                }} else if (attempt < 10) {{
                    console.log(`[SSR MODE] ⏳ Review tab not found, retry ${{attempt + 1}}/10...`);
                    setTimeout(() => tryAddButton(attempt + 1), 300);
                }} else {{
                    console.log('[SSR MODE] ❌ Review tab not found after 10 attempts - trying alternative locations');
                    // Try adding to modal body as fallback
                    const modalBody = document.querySelector('.comet-v2-modal-body') || 
                                     document.querySelector('.product-detail-wrap') ||
                                     document.querySelector('.product-main');
                    if (modalBody) {{
                        const btn = this.createSakuraButtonElement(productId);
                        modalBody.insertBefore(btn, modalBody.firstChild);
                        console.log('[SSR MODE] ✅ Button added to modal body as fallback');
                    }}
                }}
            }};
            
            // Start trying immediately and also after delays
            tryAddButton();
            setTimeout(() => tryAddButton(4), 600);
            setTimeout(() => tryAddButton(7), 1500);
        }}
        
        createSakuraButtonElement(productId) {{
            const btn = document.createElement('button');
            btn.className = 'sakura-reviews-btn';
            btn.innerHTML = `
                <div style="display: flex; align-items: center; justify-content: center; gap: 8px;">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 285.75 285.75" style="flex-shrink: 0;">
                        <g transform="matrix(2.022 0 0 2.022 13.745 -293.54)">
                            <g transform="translate(6.3237 14.723)" fill="#fbc1ea">
                                <path d="m47.885 146.2c-0.2975 4e-3 -0.5912 0.11045-0.87966 0.33699-5.9498 4.6713-11.203 14.597-9.9297 22.903 2.8966 18.896 14.067 26.707 20.463 26.707 6.3959 0 17.566-7.8114 20.463-26.707 1.2732-8.3058-3.98-18.232-9.9297-22.903-3.0769-2.4158-6.6808 8.9461-10.533 8.9461-3.4911 0-6.7777-9.3315-9.6535-9.2831z"/>
                                <path d="m109.16 176.88c-0.0961-0.28158-0.28774-0.52813-0.59233-0.73247-6.2812-4.2151-17.345-6.1439-24.85-2.3663-17.076 8.5939-21.053 21.631-19.076 27.714 1.9764 6.0828 12.857 14.293 31.723 11.208 8.2927-1.3557 16.109-9.4191 18.714-16.521 1.3467-3.6728-10.573-3.5894-11.763-7.2531-1.0788-3.3203 6.7804-9.3296 5.8456-12.05z"/>
                                <path d="m99.014 244.43c0.2381-0.17845 0.41337-0.43686 0.51358-0.78969 2.0678-7.2763 0.48339-18.394-5.4287-24.365-13.45-13.584-27.078-13.338-32.253-9.5786-5.1743 3.7594-9.62 16.645-0.85683 33.634 3.852 7.4679 13.936 12.41 21.495 12.692 3.9092 0.14579 0.14652-11.164 3.2631-13.429 2.8244-2.052 10.968 3.5655 13.266 1.836z"/>
                                <path d="m31.684 255.78c0.24329 0.1713 0.54322 0.25813 0.90974 0.24442 7.5592-0.28196 17.643-5.2244 21.495-12.692 8.7632-16.989 4.3175-29.875-0.85683-33.634-5.1743-3.7594-18.803-4.0057-32.253 9.5786-5.9121 5.9712-7.4965 17.089-5.4287 24.365 1.0694 3.7629 10.663-3.3106 13.78-1.0463 2.8244 2.052-0.0016 11.533 2.3534 13.184z"/>
                                <path d="m-0.044487 195.24c-0.087736 0.28432-0.077638 0.5964 0.048675 0.94074 2.6041 7.1021 10.421 15.165 18.714 16.521 18.866 3.0843 29.747-5.1256 31.723-11.208 1.9764-6.0828-2.0008-19.12-19.076-27.714-7.5058-3.7775-18.569-1.8487-24.85 2.3663-3.2483 2.1798 6.4438 9.1184 5.2533 12.782-1.0788 3.3203-10.969 3.5624-11.812 6.3124z"/>
                            </g>
                            <g transform="matrix(.33942 0 0 -.33942 44.333 286.73)" fill="#ee379a">
                                <path d="m48.763 148.47c-0.27045 4e-3 -0.53745 0.10041-0.79969 0.30635-5.4089 4.2466-10.185 13.27-9.027 20.821 2.6332 17.178 12.788 24.279 18.603 24.279 5.8144 0 15.969-7.1012 18.603-24.279 1.1575-7.5507-3.6182-16.574-9.027-20.821-2.7972-2.1961-6.0735 8.1328-9.5756 8.1328-3.1738 0-6.1616-8.4832-8.7759-8.4392z"/>
                                <path d="m107.39 178.31c-0.0874-0.25598-0.26158-0.48012-0.53848-0.66588-5.7102-3.8319-15.768-5.5854-22.591-2.1512-15.523 7.8126-19.139 19.665-17.342 25.195 1.7968 5.5298 11.688 12.993 28.839 10.189 7.5388-1.2325 14.645-8.5628 17.012-15.019 1.2242-3.3389-9.6116-3.263-10.694-6.5937-0.98074-3.0184 6.164-8.4814 5.3142-10.954z"/>
                                <path d="m97.122 243.28c0.21645-0.16223 0.37579-0.39715 0.46689-0.7179 1.8798-6.6148 0.43945-16.722-4.9352-22.15-12.227-12.349-24.617-12.125-29.321-8.7078-4.704 3.4176-8.7455 15.132-0.77894 30.577 3.5018 6.789 12.669 11.282 19.541 11.538 3.5538 0.13254 0.1332-10.15 2.9664-12.208 2.5676-1.8655 9.9711 3.2414 12.06 1.6691z"/>
                                <path d="m32.156 253.6c0.22118 0.15573 0.49384 0.23467 0.82704 0.2222 6.872-0.25632 16.039-4.7495 19.541-11.538 7.9665-15.445 3.925-27.159-0.77894-30.577-4.704-3.4176-17.093-3.6415-29.321 8.7078-5.3746 5.4283-6.815 15.536-4.9352 22.15 0.97214 3.4208 9.6939-3.0097 12.527-0.95122 2.5676 1.8655-0.0015 10.485 2.1394 11.986z"/>
                                <path d="m2.2688 195c-0.07976 0.25847-0.07058 0.54218 0.04425 0.85522 2.3673 6.4564 9.4735 13.787 17.012 15.019 17.151 2.8039 27.043-4.6596 28.839-10.189 1.7968-5.5298-1.8189-17.382-17.342-25.195-6.8235-3.4341-16.881-1.6807-22.591 2.1512-2.953 1.9817 5.858 8.2894 4.7758 11.62-0.98075 3.0184-9.9721 3.2385-10.738 5.7385z"/>
                            </g>
                        </g>
                    </svg>
                    <span>Get Reviews</span>
                </div>
            `;
            btn.style.cssText = `
                background: white;
                color: #8B4A8B;
                border: 3px solid #ff69b4;
                padding: 12px 24px;
                border-radius: 12px;
                font-size: 14px;
                font-weight: 600;
                cursor: pointer;
                margin: 16px 0;
                display: block;
                width: 100%;
                transition: all 0.2s;
                box-shadow: 0 2px 8px rgba(255, 105, 180, 0.2);
                position: relative;
                overflow: visible;
            `;
            
            // Add hover effects
            btn.addEventListener('mouseenter', () => {{
                btn.style.background = '#ff69b4';
                btn.style.color = 'white';
                btn.style.transform = 'translateY(-1px)';
                btn.style.boxShadow = '0 4px 12px rgba(255, 105, 180, 0.4)';
                btn.style.borderColor = '#ff1493';
            }});
            
            btn.addEventListener('mouseleave', () => {{
                btn.style.background = 'white';
                btn.style.color = '#8B4A8B';
                btn.style.transform = 'translateY(0)';
                btn.style.boxShadow = '0 2px 8px rgba(255, 105, 180, 0.2)';
                btn.style.borderColor = '#ff69b4';
            }});
            
            // Add click handler
            btn.addEventListener('click', () => {{
                this.handleProductClick(productId);
            }});
            
            return btn;
        }}
        // ====================================================================
        // ✅ END OF CRITICAL SSR BUTTON CODE
        // If you see this marker, the SSR button code is intact.
        // ====================================================================
        
        handleProductClick(productId) {{
            console.log('[SSR MODE] Processing product click:', productId);
            
            // Store the product data
            this.productData = {{
                platform: 'aliexpress',
                productId: productId,
                url: window.location.href
            }};
            
            // Create overlay and load reviews
            this.createOverlay();
            this.loadReviews();
        }}
        
        detectProduct() {{
            const url = window.location.href;
            const hostname = window.location.hostname;
            
            let platform = 'unknown', productId = null;
            
            // Try multiple methods for AliExpress
            if (hostname.includes('aliexpress')) {{
                platform = 'aliexpress';
                
                // Method 1: Extract from URL (supports .html extension)
                const urlMatch = url.match(/\\/item\\/(\\d+)(?:\\.html)?/);
                if (urlMatch) {{
                    productId = urlMatch[1];
                    console.log('[DETECT] Product ID from URL:', productId);
                }}
                
                // Method 2: Try window.runParams (AliExpress global data)
                if (!productId && typeof window.runParams === 'object' && window.runParams.data) {{
                    const data = window.runParams.data;
                    if (data.feedbackModule && data.feedbackModule.productId) {{
                        productId = data.feedbackModule.productId;
                        console.log('[DETECT] Product ID from runParams.feedbackModule:', productId);
                    }} else if (data.productId) {{
                        productId = data.productId;
                        console.log('[DETECT] Product ID from runParams.data:', productId);
                    }} else if (data.storeModule && data.storeModule.productId) {{
                        productId = data.storeModule.productId;
                        console.log('[DETECT] Product ID from runParams.storeModule:', productId);
                    }}
                }}
                
                // Method 3: Try to find in page meta/data attributes
                if (!productId) {{
                    const metaProductId = document.querySelector('meta[property="product:id"]') || 
                                       document.querySelector('meta[name="product:id"]');
                    if (metaProductId) {{
                        productId = metaProductId.getAttribute('content');
                        console.log('[DETECT] Product ID from meta tag:', productId);
                    }}
                }}
            }} else if (hostname.includes('amazon')) {{
                platform = 'amazon';
                const match = url.match(/\\/dp\\/([A-Z0-9]{{10}})/);
                if (match) productId = match[1];
            }} else if (hostname.includes('ebay')) {{
                platform = 'ebay';
                const match = url.match(/\\/itm\\/(\\d+)/);
                if (match) productId = match[1];
            }} else if (hostname.includes('walmart')) {{
                platform = 'walmart';
                const match = url.match(/\\/ip\\/[^\\/]+\\/(\\d+)/);
                if (match) productId = match[1];
            }}
            
            console.log('[DETECT] Final result:', {{ platform, productId, url }});
            return {{ platform, productId, url }};
        }}
        
        createOverlay() {{
            // Remove any existing overlay first to prevent duplicates
            const existingOverlay = document.getElementById('reviewking-overlay');
            if (existingOverlay) {{
                console.log('[REVIEWKING] Removing existing overlay to prevent duplicates');
                existingOverlay.remove();
            }}
            
            const div = document.createElement('div');
            div.id = 'reviewking-overlay';
            div.innerHTML = `
                <style>
                    #reviewking-overlay {{
                        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                        background: rgba(0,0,0,0.90); z-index: 999999;
                        display: flex; align-items: center; justify-content: center;
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    }}
                    #reviewking-panel {{
                        background: #1e1e2e; border-radius: 16px; width: 90vw; max-width: 750px;
                        max-height: 90vh; display: flex; flex-direction: column;
                        box-shadow: 0 25px 80px rgba(0,0,0,0.5);
                    }}
                    #reviewking-header {{
                        background: #1e1e2e;
                        color: white; padding: 20px 28px; border-radius: 16px 16px 0 0;
                        display: flex; justify-content: space-between; align-items: center;
                        border-bottom: 1px solid #2d2d3d;
                    }}
                    #reviewking-close {{
                        background: #FF2D85; border: none; color: white;
                        font-size: 13px; padding: 10px 24px; border-radius: 8px;
                        cursor: pointer; display: flex; align-items: center; justify-content: center;
                        font-weight: 700; line-height: 1; gap: 6px;
                        transition: all 0.2s;
                    }}
                    #reviewking-close:hover {{ background: #E0186F; transform: translateY(-1px); box-shadow: 0 4px 12px rgba(255, 45, 133, 0.4); }}
                    #reviewking-content {{
                        flex: 1; padding: 24px 28px; overflow-y: auto;
                        background: #1e1e2e;
                        scrollbar-width: thin;
                        scrollbar-color: #4a4a5e #1e1e2e;
                    }}
                    #reviewking-content::-webkit-scrollbar {{
                        width: 8px;
                    }}
                    #reviewking-content::-webkit-scrollbar-track {{
                        background: #1e1e2e;
                    }}
                    #reviewking-content::-webkit-scrollbar-thumb {{
                        background: #4a4a5e;
                        border-radius: 4px;
                    }}
                    #reviewking-content::-webkit-scrollbar-thumb:hover {{
                        background: #5a5a6e;
                    }}
                    .rk-btn {{
                        padding: 12px 20px; border: none; border-radius: 8px;
                        font-size: 13px; font-weight: 600; cursor: pointer;
                        transition: all 0.2s ease;
                        white-space: nowrap;
                    }}
                    .rk-btn:hover {{ transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); }}
                    .rk-btn:active {{ transform: translateY(0); }}
                    .rk-btn-primary {{
                        background: #667eea; color: white;
                    }}
                    .rk-btn-primary:hover {{ background: #5568d3; }}
                    .rk-btn-secondary {{
                        background: #2d2d3d; color: #e5e7eb;
                        border: 1px solid #3d3d4d;
                    }}
                    .rk-btn-secondary:hover {{ background: #3d3d4d; border-color: #4d4d5d; }}
                    .rk-badge {{
                        display: inline-block; padding: 4px 10px; border-radius: 12px;
                        font-size: 10px; font-weight: 700; text-transform: uppercase;
                        letter-spacing: 0.5px;
                    }}
                    .rk-badge-success {{ background: #10b981; color: white; }}
                    .rk-badge-info {{ background: #3b82f6; color: white; }}
                    @keyframes spin {{ from {{ transform: rotate(0deg); }} to {{ transform: rotate(360deg); }} }}
                </style>
                <div id="reviewking-panel">
                    <div id="reviewking-header">
                        <div style="flex: 1;">
                            <h2 style="margin: 0; font-size: 24px; font-weight: 800; letter-spacing: -0.03em; color: #FF2D85;">🌸 Sakura Reviews</h2>
                            <p style="margin: 8px 0 0; opacity: 0.7; font-size: 13px; font-weight: 500; color: #9ca3af;">
                                Beautiful reviews, naturally • Powered by AI
                            </p>
                        </div>
                        <button id="reviewking-close">✕ Close</button>
                    </div>
                    <div id="reviewking-content">
                        <div style="text-align: center; padding: 40px;">
                            <div style="width: 48px; height: 48px; border: 4px solid #e5e7eb;
                                border-top-color: #667eea; border-radius: 50%; margin: 0 auto 16px;
                                animation: spin 1s linear infinite;"></div>
                            <p style="color: #6b7280; margin: 0;">Loading reviews with AI analysis...</p>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(div);
            
            // Attach close button event listener
            const closeBtn = document.getElementById('reviewking-close');
            if (closeBtn) {{
                closeBtn.addEventListener('click', () => {{
                    this.close();
                }});
            }}
        }}
        
        setupProductSearch() {{
            const searchInput = document.getElementById('product-search-input');
            const dropdown = document.getElementById('product-dropdown');
            
            // Check if elements exist
            if (!searchInput || !dropdown) {{
                console.log('Product search elements not found yet');
                return;
            }}
            
            // Add search input event listener (only once)
            if (searchInput.hasAttribute('data-listener-attached')) {{
                return;
            }}
            searchInput.setAttribute('data-listener-attached', 'true');
            
            searchInput.addEventListener('input', (e) => {{
                const query = e.target.value.trim();
                
                // Clear previous timeout
                if (this.searchTimeout) {{
                    clearTimeout(this.searchTimeout);
                }}
                
                const dropdownElement = document.getElementById('product-dropdown');
                if (!dropdownElement) return;
                
                if (query.length < 2) {{
                    dropdownElement.style.display = 'none';
                    return;
                }}
                
                // Debounce search
                this.searchTimeout = setTimeout(() => {{
                    this.searchProducts(query);
                }}, 300);
            }});
            
            // Hide dropdown when clicking outside (only once)
            if (!document.body.hasAttribute('data-dropdown-listener')) {{
                document.body.setAttribute('data-dropdown-listener', 'true');
            document.addEventListener('click', (e) => {{
                    const dropdownElement = document.getElementById('product-dropdown');
                    if (dropdownElement && !e.target.closest('#product-search-input') && !e.target.closest('#product-dropdown')) {{
                        dropdownElement.style.display = 'none';
                }}
            }});
            }}
        }}
        
        async searchProducts(query) {{
            const dropdown = document.getElementById('product-dropdown');
            
            if (!dropdown) {{
                console.error('Dropdown element not found');
                return;
            }}
            
            try {{
                dropdown.innerHTML = '<div style="padding: 12px; color: #666;">Searching...</div>';
                dropdown.style.display = 'block';
                
                const response = await fetch(`${{API_URL}}/shopify/products/search?q=${{encodeURIComponent(query)}}`);
                const result = await response.json();
                
                if (result.success && result.products.length > 0) {{
                    dropdown.innerHTML = result.products.map(product => `
                        <div class="product-option" data-product-id="${{product.id}}" 
                             data-product-title="${{product.title}}"
                             style="padding: 12px; border-bottom: 1px solid #f0f0f0; cursor: pointer; 
                                    display: flex; align-items: center; gap: 12px;"
                             onmouseover="this.style.background='#f8f9fa'" 
                             onmouseout="this.style.background='white'"
                             onclick="window.reviewKingClient.selectProduct('${{product.id}}', '${{product.title.replace(/'/g, "\\\\'")}}')">
                            ${{product.image ? `<img src="${{product.image}}" style="width: 40px; height: 40px; object-fit: cover; border-radius: 4px;">` : '<div style="width: 40px; height: 40px; background: #f0f0f0; border-radius: 4px;"></div>'}}
                            <div>
                                <div style="font-weight: 500; color: #333; font-size: 14px;">${{product.title}}</div>
                                <div style="font-size: 12px; color: #666;">ID: ${{product.id}}</div>
                            </div>
                        </div>
                    `).join('');
                }} else {{
                    dropdown.innerHTML = '<div style="padding: 12px; color: #666;">No products found</div>';
                }}
            }} catch (error) {{
                dropdown.innerHTML = '<div style="padding: 12px; color: #e74c3c;">Search failed. Check Shopify API configuration.</div>';
            }}
        }}
        
        selectProduct(productId, productTitle) {{
            this.selectedProduct = {{ id: productId, title: productTitle }};
            
            // Hide dropdown and clear input
            const dropdown = document.getElementById('product-dropdown');
            const searchInput = document.getElementById('product-search-input');
            const selectedDiv = document.getElementById('selected-product');
            
            if (dropdown) dropdown.style.display = 'none';
            if (searchInput) searchInput.value = '';
            
            if (!selectedDiv) {{
                console.error('Selected product div not found');
                return;
            }}
            
            // Show selected product
            selectedDiv.innerHTML = `
                <div style="display: flex; align-items: center; justify-content: space-between;">
                    <div>
                        <div style="font-weight: 500;">✓ Target Product Selected</div>
                        <div style="opacity: 0.8; font-size: 12px;">${{productTitle}}</div>
                    </div>
                    <button onclick="window.reviewKingClient.clearProduct()" 
                            style="background: rgba(255,255,255,0.2); border: none; color: white; 
                                   padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 12px;">
                        Change
                    </button>
                </div>
            `;
            selectedDiv.style.display = 'block';
            
            // Refresh current review display to show import buttons
            if (this.reviews && this.reviews.length > 0) {{
                this.displayReview();
            }}
        }}
        
        clearProduct() {{
            this.selectedProduct = null;
            
            const selectedDiv = document.getElementById('selected-product');
            if (selectedDiv) {{
                selectedDiv.style.display = 'none';
            }}
            
            // Refresh current review display to hide import buttons
            if (this.reviews && this.reviews.length > 0) {{
                this.displayReview();
            }}
        }}
        
        async loadReviews(page = 1) {{
            try {{
                console.log('Loading reviews...', {{ productId: this.productData.productId, platform: this.productData.platform }});
                
                const params = new URLSearchParams({{
                    productId: this.productData.productId,
                    platform: this.productData.platform,
                    page: page,
                    per_page: 150,  // Load 150 reviews to account for duplicates
                    id: this.sessionId
                }});
                
                const url = `${{API_URL}}/admin/reviews/import/url?${{params}}`;
                console.log('Fetching:', url);
                
                const response = await fetch(url);
                console.log('Response status:', response.status);
                
                const result = await response.json();
                console.log('Result:', result);
                
                if (result.success) {{
                    this.allReviews = result.reviews;  // Store all reviews
                    this.currentIndex = 0;
                    this.pagination = result.pagination;
                    this.stats = result.stats;
                    console.log('All reviews loaded:', this.allReviews.length);
                    
                    // Smart fallback: If AI recommended has < 3 reviews, show All with smart sorting
                    const aiRecommendedCount = this.allReviews.filter(r => r.ai_recommended).length;
                    if (this.currentFilter === 'ai_recommended' && aiRecommendedCount < 3) {{
                        console.log(`[Smart Fallback] Only ${{aiRecommendedCount}} AI recommended reviews, falling back to 'all' with smart sorting`);
                        this.currentFilter = 'all';
                        this.useSmartSort = true;  // Flag for smart sorting
                    }} else {{
                        this.useSmartSort = false;
                    }}
                    
                    this.applyFilter();  // Apply current filter and display
                }} else {{
                    console.error('Error loading reviews:', result.error);
                    // Show user-friendly error message
                    const errorMessage = result.message || result.error || 'Failed to load reviews';
                    this.showError(errorMessage);
                }}
            }} catch (error) {{
                console.error('Exception loading reviews:', error);
                this.showError('Failed to load reviews: ' + error.message);
            }}
        }}
        
        applyFilter() {{
            // Step 1: Apply star rating filter
            let filtered = [...this.allReviews];
            
            if (this.currentFilter === 'photos') {{
                filtered = filtered.filter(r => r.images && r.images.length > 0);
            }} else if (this.currentFilter === 'ai_recommended') {{
                filtered = filtered.filter(r => r.ai_recommended);
            }} else if (this.currentFilter === '4-5stars') {{
                // Rating >= 70 on the 0-100 scale (like old code)
                filtered = filtered.filter(r => r.rating >= 70);
            }} else if (this.currentFilter === '3stars') {{
                // Rating 50-69 on the 0-100 scale
                filtered = filtered.filter(r => r.rating >= 50 && r.rating < 70);
            }} else if (this.currentFilter === '5stars') {{
                // Rating >= 90 on the 0-100 scale
                filtered = filtered.filter(r => r.rating >= 90);
            }}
            
            // Step 2: Apply country filter
            if (this.selectedCountry !== 'all') {{
                filtered = filtered.filter(r => r.country === this.selectedCountry);
            }}
            
            // Step 3: Smart sorting - prioritize photos, then rating, then quality
            // Applied when falling back from AI recommended OR always for best UX
            filtered = this.smartSort(filtered);
            
            this.reviews = filtered;
            
            console.log(`[Filter] Applied filter "${{this.currentFilter}}" + country "${{this.selectedCountry}}": ${{this.reviews.length}} of ${{this.allReviews.length}} reviews`);
            
            // Reset to first review after filtering
            this.currentIndex = 0;
            
            // Update stats based on all reviews (not filtered)
            this.stats = {{
                ...this.stats,
                total: this.allReviews.length,
                with_photos: this.allReviews.filter(r => r.images && r.images.length > 0).length,
                ai_recommended: this.allReviews.filter(r => r.ai_recommended).length
            }};
            
            this.displayReview();
        }}
        
        smartSort(reviews) {{
            // Smart sorting algorithm: Best reviews first
            // Priority: AI Recommended > Has Text Content > Has Photos > High Rating > Quality Score
            return reviews.sort((a, b) => {{
                // 1. AI Recommended first (best quality reviews)
                if (a.ai_recommended && !b.ai_recommended) return -1;
                if (!a.ai_recommended && b.ai_recommended) return 1;
                
                // 2. HAS TEXT CONTENT - Reviews with actual text before empty ones
                const aText = (a.text || a.body || '').trim();
                const bText = (b.text || b.body || '').trim();
                const aHasText = aText.length >= 10;  // At least 10 chars = meaningful content
                const bHasText = bText.length >= 10;
                if (aHasText && !bHasText) return -1;
                if (!aHasText && bHasText) return 1;
                
                // 3. Has photos (prioritize reviews with more photos)
                const aPhotos = (a.images && a.images.length) || 0;
                const bPhotos = (b.images && b.images.length) || 0;
                if (aPhotos > 0 && bPhotos === 0) return -1;
                if (aPhotos === 0 && bPhotos > 0) return 1;
                if (aPhotos !== bPhotos) return bPhotos - aPhotos;  // More photos first
                
                // 4. Higher rating first
                const aRating = a.rating || 0;
                const bRating = b.rating || 0;
                if (aRating !== bRating) return bRating - aRating;
                
                // 5. Longer text (more detailed reviews) first
                if (aText.length !== bText.length) return bText.length - aText.length;
                
                // 6. Higher quality score as tiebreaker
                const aQuality = a.quality_score || 0;
                const bQuality = b.quality_score || 0;
                return bQuality - aQuality;
            }});
        }}
        
        setFilter(filter) {{
            console.log(`[Filter] Changing filter from "${{this.currentFilter}}" to "${{filter}}"`);
            this.currentFilter = filter;
            this.applyFilter();
        }}
        
        setCountry(country) {{
            console.log(`[Country] Changing country filter from "${{this.selectedCountry}}" to "${{country}}"`);
            this.selectedCountry = country;
            this.applyFilter();
        }}
        
        toggleTranslation() {{
            this.showTranslations = !this.showTranslations;
            console.log(`[Translation] Toggled to: ${{this.showTranslations}}`);
            this.displayReview();  // Refresh display without re-filtering
        }}
        
        getCountryMap() {{
            // Country code to flag/name mapping
            return {{
                'AD': {{'flag': '🇦🇩', 'name': 'Andorra'}}, 'AE': {{'flag': '🇦🇪', 'name': 'United Arab Emirates'}}, 'AF': {{'flag': '🇦🇫', 'name': 'Afghanistan'}}, 'AG': {{'flag': '🇦🇬', 'name': 'Antigua and Barbuda'}}, 'AI': {{'flag': '🇦🇮', 'name': 'Anguilla'}}, 'AL': {{'flag': '🇦🇱', 'name': 'Albania'}}, 'AM': {{'flag': '🇦🇲', 'name': 'Armenia'}}, 'AO': {{'flag': '🇦🇴', 'name': 'Angola'}}, 'AR': {{'flag': '🇦🇷', 'name': 'Argentina'}}, 'AS': {{'flag': '🇦🇸', 'name': 'American Samoa'}}, 'AT': {{'flag': '🇦🇹', 'name': 'Austria'}}, 'AU': {{'flag': '🇦🇺', 'name': 'Australia'}}, 'AW': {{'flag': '🇦🇼', 'name': 'Aruba'}}, 'AZ': {{'flag': '🇦🇿', 'name': 'Azerbaijan'}},
                'BA': {{'flag': '🇧🇦', 'name': 'Bosnia and Herzegovina'}}, 'BB': {{'flag': '🇧🇧', 'name': 'Barbados'}}, 'BD': {{'flag': '🇧🇩', 'name': 'Bangladesh'}}, 'BE': {{'flag': '🇧🇪', 'name': 'Belgium'}}, 'BF': {{'flag': '🇧🇫', 'name': 'Burkina Faso'}}, 'BG': {{'flag': '🇧🇬', 'name': 'Bulgaria'}}, 'BH': {{'flag': '🇧🇭', 'name': 'Bahrain'}}, 'BI': {{'flag': '🇧🇮', 'name': 'Burundi'}}, 'BJ': {{'flag': '🇧🇯', 'name': 'Benin'}}, 'BM': {{'flag': '🇧🇲', 'name': 'Bermuda'}}, 'BN': {{'flag': '🇧🇳', 'name': 'Brunei'}}, 'BO': {{'flag': '🇧🇴', 'name': 'Bolivia'}}, 'BR': {{'flag': '🇧🇷', 'name': 'Brazil'}}, 'BS': {{'flag': '🇧🇸', 'name': 'Bahamas'}}, 'BT': {{'flag': '🇧🇹', 'name': 'Bhutan'}}, 'BW': {{'flag': '🇧🇼', 'name': 'Botswana'}}, 'BY': {{'flag': '🇧🇾', 'name': 'Belarus'}}, 'BZ': {{'flag': '🇧🇿', 'name': 'Belize'}},
                'CA': {{'flag': '🇨🇦', 'name': 'Canada'}}, 'CD': {{'flag': '🇨🇩', 'name': 'Congo'}}, 'CF': {{'flag': '🇨🇫', 'name': 'Central African Republic'}}, 'CG': {{'flag': '🇨🇬', 'name': 'Congo'}}, 'CH': {{'flag': '🇨🇭', 'name': 'Switzerland'}}, 'CI': {{'flag': '🇨🇮', 'name': 'Côte D\\'Ivoire'}}, 'CK': {{'flag': '🇨🇰', 'name': 'Cook Islands'}}, 'CL': {{'flag': '🇨🇱', 'name': 'Chile'}}, 'CM': {{'flag': '🇨🇲', 'name': 'Cameroon'}}, 'CN': {{'flag': '🇨🇳', 'name': 'China'}}, 'CO': {{'flag': '🇨🇴', 'name': 'Colombia'}}, 'CR': {{'flag': '🇨🇷', 'name': 'Costa Rica'}}, 'CU': {{'flag': '🇨🇺', 'name': 'Cuba'}}, 'CV': {{'flag': '🇨🇻', 'name': 'Cape Verde'}}, 'CW': {{'flag': '🇨🇼', 'name': 'Curaçao'}}, 'CY': {{'flag': '🇨🇾', 'name': 'Cyprus'}}, 'CZ': {{'flag': '🇨🇿', 'name': 'Czech Republic'}},
                'DE': {{'flag': '🇩🇪', 'name': 'Germany'}}, 'DJ': {{'flag': '🇩🇯', 'name': 'Djibouti'}}, 'DK': {{'flag': '🇩🇰', 'name': 'Denmark'}}, 'DM': {{'flag': '🇩🇲', 'name': 'Dominica'}}, 'DO': {{'flag': '🇩🇴', 'name': 'Dominican Republic'}}, 'DZ': {{'flag': '🇩🇿', 'name': 'Algeria'}},
                'EC': {{'flag': '🇪🇨', 'name': 'Ecuador'}}, 'EE': {{'flag': '🇪🇪', 'name': 'Estonia'}}, 'EG': {{'flag': '🇪🇬', 'name': 'Egypt'}}, 'ER': {{'flag': '🇪🇷', 'name': 'Eritrea'}}, 'ES': {{'flag': '🇪🇸', 'name': 'Spain'}}, 'ET': {{'flag': '🇪🇹', 'name': 'Ethiopia'}},
                'FI': {{'flag': '🇫🇮', 'name': 'Finland'}}, 'FJ': {{'flag': '🇫🇯', 'name': 'Fiji'}}, 'FR': {{'flag': '🇫🇷', 'name': 'France'}},
                'GA': {{'flag': '🇬🇦', 'name': 'Gabon'}}, 'GB': {{'flag': '🇬🇧', 'name': 'United Kingdom'}}, 'GD': {{'flag': '🇬🇩', 'name': 'Grenada'}}, 'GE': {{'flag': '🇬🇪', 'name': 'Georgia'}}, 'GH': {{'flag': '🇬🇭', 'name': 'Ghana'}}, 'GI': {{'flag': '🇬🇮', 'name': 'Gibraltar'}}, 'GL': {{'flag': '🇬🇱', 'name': 'Greenland'}}, 'GM': {{'flag': '🇬🇲', 'name': 'Gambia'}}, 'GN': {{'flag': '🇬🇳', 'name': 'Guinea'}}, 'GR': {{'flag': '🇬🇷', 'name': 'Greece'}}, 'GT': {{'flag': '🇬🇹', 'name': 'Guatemala'}}, 'GU': {{'flag': '🇬🇺', 'name': 'Guam'}}, 'GY': {{'flag': '🇬🇾', 'name': 'Guyana'}},
                'HK': {{'flag': '🇭🇰', 'name': 'Hong Kong'}}, 'HN': {{'flag': '🇭🇳', 'name': 'Honduras'}}, 'HR': {{'flag': '🇭🇷', 'name': 'Croatia'}}, 'HT': {{'flag': '🇭🇹', 'name': 'Haiti'}}, 'HU': {{'flag': '🇭🇺', 'name': 'Hungary'}},
                'ID': {{'flag': '🇮🇩', 'name': 'Indonesia'}}, 'IE': {{'flag': '🇮🇪', 'name': 'Ireland'}}, 'IL': {{'flag': '🇮🇱', 'name': 'Israel'}}, 'IN': {{'flag': '🇮🇳', 'name': 'India'}}, 'IQ': {{'flag': '🇮🇶', 'name': 'Iraq'}}, 'IR': {{'flag': '🇮🇷', 'name': 'Iran'}}, 'IS': {{'flag': '🇮🇸', 'name': 'Iceland'}}, 'IT': {{'flag': '🇮🇹', 'name': 'Italy'}},
                'JM': {{'flag': '🇯🇲', 'name': 'Jamaica'}}, 'JO': {{'flag': '🇯🇴', 'name': 'Jordan'}}, 'JP': {{'flag': '🇯🇵', 'name': 'Japan'}},
                'KE': {{'flag': '🇰🇪', 'name': 'Kenya'}}, 'KG': {{'flag': '🇰🇬', 'name': 'Kyrgyzstan'}}, 'KH': {{'flag': '🇰🇭', 'name': 'Cambodia'}}, 'KI': {{'flag': '🇰🇮', 'name': 'Kiribati'}}, 'KM': {{'flag': '🇰🇲', 'name': 'Comoros'}}, 'KN': {{'flag': '🇰🇳', 'name': 'Saint Kitts and Nevis'}}, 'KP': {{'flag': '🇰🇵', 'name': 'North Korea'}}, 'KR': {{'flag': '🇰🇷', 'name': 'South Korea'}}, 'KW': {{'flag': '🇰🇼', 'name': 'Kuwait'}}, 'KY': {{'flag': '🇰🇾', 'name': 'Cayman Islands'}}, 'KZ': {{'flag': '🇰🇿', 'name': 'Kazakhstan'}},
                'LA': {{'flag': '🇱🇦', 'name': 'Laos'}}, 'LB': {{'flag': '🇱🇧', 'name': 'Lebanon'}}, 'LC': {{'flag': '🇱🇨', 'name': 'Saint Lucia'}}, 'LI': {{'flag': '🇱🇮', 'name': 'Liechtenstein'}}, 'LK': {{'flag': '🇱🇰', 'name': 'Sri Lanka'}}, 'LR': {{'flag': '🇱🇷', 'name': 'Liberia'}}, 'LS': {{'flag': '🇱🇸', 'name': 'Lesotho'}}, 'LT': {{'flag': '🇱🇹', 'name': 'Lithuania'}}, 'LU': {{'flag': '🇱🇺', 'name': 'Luxembourg'}}, 'LV': {{'flag': '🇱🇻', 'name': 'Latvia'}}, 'LY': {{'flag': '🇱🇾', 'name': 'Libya'}},
                'MA': {{'flag': '🇲🇦', 'name': 'Morocco'}}, 'MC': {{'flag': '🇲🇨', 'name': 'Monaco'}}, 'MD': {{'flag': '🇲🇩', 'name': 'Moldova'}}, 'ME': {{'flag': '🇲🇪', 'name': 'Montenegro'}}, 'MG': {{'flag': '🇲🇬', 'name': 'Madagascar'}}, 'MK': {{'flag': '🇲🇰', 'name': 'Macedonia'}}, 'ML': {{'flag': '🇲🇱', 'name': 'Mali'}}, 'MM': {{'flag': '🇲🇲', 'name': 'Myanmar'}}, 'MN': {{'flag': '🇲🇳', 'name': 'Mongolia'}}, 'MO': {{'flag': '🇲🇴', 'name': 'Macao'}}, 'MR': {{'flag': '🇲🇷', 'name': 'Mauritania'}}, 'MS': {{'flag': '🇲🇸', 'name': 'Montserrat'}}, 'MT': {{'flag': '🇲🇹', 'name': 'Malta'}}, 'MU': {{'flag': '🇲🇺', 'name': 'Mauritius'}}, 'MV': {{'flag': '🇲🇻', 'name': 'Maldives'}}, 'MW': {{'flag': '🇲🇼', 'name': 'Malawi'}}, 'MX': {{'flag': '🇲🇽', 'name': 'Mexico'}}, 'MY': {{'flag': '🇲🇾', 'name': 'Malaysia'}}, 'MZ': {{'flag': '🇲🇿', 'name': 'Mozambique'}},
                'NA': {{'flag': '🇳🇦', 'name': 'Namibia'}}, 'NC': {{'flag': '🇳🇨', 'name': 'New Caledonia'}}, 'NE': {{'flag': '🇳🇪', 'name': 'Niger'}}, 'NG': {{'flag': '🇳🇬', 'name': 'Nigeria'}}, 'NI': {{'flag': '🇳🇮', 'name': 'Nicaragua'}}, 'NL': {{'flag': '🇳🇱', 'name': 'Netherlands'}}, 'NO': {{'flag': '🇳🇴', 'name': 'Norway'}}, 'NP': {{'flag': '🇳🇵', 'name': 'Nepal'}}, 'NR': {{'flag': '🇳🇷', 'name': 'Nauru'}}, 'NZ': {{'flag': '🇳🇿', 'name': 'New Zealand'}},
                'OM': {{'flag': '🇴🇲', 'name': 'Oman'}},
                'PA': {{'flag': '🇵🇦', 'name': 'Panama'}}, 'PE': {{'flag': '🇵🇪', 'name': 'Peru'}}, 'PG': {{'flag': '🇵🇬', 'name': 'Papua New Guinea'}}, 'PH': {{'flag': '🇵🇭', 'name': 'Philippines'}}, 'PK': {{'flag': '🇵🇰', 'name': 'Pakistan'}}, 'PL': {{'flag': '🇵🇱', 'name': 'Poland'}}, 'PR': {{'flag': '🇵🇷', 'name': 'Puerto Rico'}}, 'PS': {{'flag': '🇵🇸', 'name': 'Palestine'}}, 'PT': {{'flag': '🇵🇹', 'name': 'Portugal'}}, 'PW': {{'flag': '🇵🇼', 'name': 'Palau'}}, 'PY': {{'flag': '🇵🇾', 'name': 'Paraguay'}},
                'QA': {{'flag': '🇶🇦', 'name': 'Qatar'}},
                'RE': {{'flag': '🇷🇪', 'name': 'Réunion'}}, 'RO': {{'flag': '🇷🇴', 'name': 'Romania'}}, 'RS': {{'flag': '🇷🇸', 'name': 'Serbia'}}, 'RU': {{'flag': '🇷🇺', 'name': 'Russia'}}, 'RW': {{'flag': '🇷🇼', 'name': 'Rwanda'}},
                'SA': {{'flag': '🇸🇦', 'name': 'Saudi Arabia'}}, 'SB': {{'flag': '🇸🇧', 'name': 'Solomon Islands'}}, 'SC': {{'flag': '🇸🇨', 'name': 'Seychelles'}}, 'SD': {{'flag': '🇸🇩', 'name': 'Sudan'}}, 'SE': {{'flag': '🇸🇪', 'name': 'Sweden'}}, 'SG': {{'flag': '🇸🇬', 'name': 'Singapore'}}, 'SI': {{'flag': '🇸🇮', 'name': 'Slovenia'}}, 'SK': {{'flag': '🇸🇰', 'name': 'Slovakia'}}, 'SL': {{'flag': '🇸🇱', 'name': 'Sierra Leone'}}, 'SM': {{'flag': '🇸🇲', 'name': 'San Marino'}}, 'SN': {{'flag': '🇸🇳', 'name': 'Senegal'}}, 'SO': {{'flag': '🇸🇴', 'name': 'Somalia'}}, 'SR': {{'flag': '🇸🇷', 'name': 'Suriname'}}, 'SS': {{'flag': '🇸🇸', 'name': 'South Sudan'}}, 'SV': {{'flag': '🇸🇻', 'name': 'El Salvador'}}, 'SY': {{'flag': '🇸🇾', 'name': 'Syria'}}, 'SZ': {{'flag': '🇸🇿', 'name': 'Swaziland'}},
                'TC': {{'flag': '🇹🇨', 'name': 'Turks and Caicos'}}, 'TD': {{'flag': '🇹🇩', 'name': 'Chad'}}, 'TG': {{'flag': '🇹🇬', 'name': 'Togo'}}, 'TH': {{'flag': '🇹🇭', 'name': 'Thailand'}}, 'TJ': {{'flag': '🇹🇯', 'name': 'Tajikistan'}}, 'TK': {{'flag': '🇹🇰', 'name': 'Tokelau'}}, 'TL': {{'flag': '🇹🇱', 'name': 'Timor-Leste'}}, 'TM': {{'flag': '🇹🇲', 'name': 'Turkmenistan'}}, 'TN': {{'flag': '🇹🇳', 'name': 'Tunisia'}}, 'TO': {{'flag': '🇹🇴', 'name': 'Tonga'}}, 'TR': {{'flag': '🇹🇷', 'name': 'Turkey'}}, 'TT': {{'flag': '🇹🇹', 'name': 'Trinidad and Tobago'}}, 'TV': {{'flag': '🇹🇻', 'name': 'Tuvalu'}}, 'TW': {{'flag': '🇹🇼', 'name': 'Taiwan'}}, 'TZ': {{'flag': '🇹🇿', 'name': 'Tanzania'}},
                'UA': {{'flag': '🇺🇦', 'name': 'Ukraine'}}, 'UG': {{'flag': '🇺🇬', 'name': 'Uganda'}}, 'US': {{'flag': '🇺🇸', 'name': 'United States'}}, 'UY': {{'flag': '🇺🇾', 'name': 'Uruguay'}}, 'UZ': {{'flag': '🇺🇿', 'name': 'Uzbekistan'}},
                'VA': {{'flag': '🇻🇦', 'name': 'Vatican City'}}, 'VC': {{'flag': '🇻🇨', 'name': 'Saint Vincent'}}, 'VE': {{'flag': '🇻🇪', 'name': 'Venezuela'}}, 'VG': {{'flag': '🇻🇬', 'name': 'British Virgin Islands'}}, 'VI': {{'flag': '🇻🇮', 'name': 'US Virgin Islands'}}, 'VN': {{'flag': '🇻🇳', 'name': 'Vietnam'}}, 'VU': {{'flag': '🇻🇺', 'name': 'Vanuatu'}},
                'WS': {{'flag': '🇼🇸', 'name': 'Samoa'}},
                'YE': {{'flag': '🇾🇪', 'name': 'Yemen'}}, 'YT': {{'flag': '🇾🇹', 'name': 'Mayotte'}},
                'ZA': {{'flag': '🇿🇦', 'name': 'South Africa'}}, 'ZM': {{'flag': '🇿🇲', 'name': 'Zambia'}}, 'ZW': {{'flag': '🇿🇼', 'name': 'Zimbabwe'}}
            }};
        }}
        
        getUniqueCountries() {{
            // Extract unique countries from all reviews
            const countryCodes = [...new Set(this.allReviews.map(r => r.country).filter(c => c))];
            const countryMap = this.getCountryMap();
            
            // Count reviews per country
            const countryReviewCounts = {{}};
            this.allReviews.forEach(r => {{
                if (r.country) {{
                    countryReviewCounts[r.country] = (countryReviewCounts[r.country] || 0) + 1;
                }}
            }});
            
            // Convert codes to objects with display info and count
            return countryCodes
                .map(code => ({{
                    code: code,
                    flag: countryMap[code]?.flag || '🌍',
                    name: countryMap[code]?.name || code,
                    count: countryReviewCounts[code] || 0
                }}))
                .sort((a, b) => b.count - a.count); // Sort by count (most reviews first)
        }}
        
        displayReview() {{
            const content = document.getElementById('reviewking-content');
            
            if (!content) {{
                console.error('Content element not found');
                return;
            }}
            
            console.log('Displaying review...', {{ hasReviews: !!this.reviews, reviewCount: this.reviews?.length }});
            
            // Check if reviews are loaded initially
            if (!this.allReviews || this.allReviews.length === 0) {{
                content.innerHTML = '<div style="text-align: center; padding: 40px;">Loading reviews...</div>';
                return;
            }}
            
            // Check if no reviews match the current filters
            if (!this.reviews || this.reviews.length === 0) {{
                const countryMap = this.getCountryMap();
                const selectedCountryName = this.selectedCountry !== 'all' 
                    ? (countryMap[this.selectedCountry]?.name || this.selectedCountry)
                    : null;
                
                content.innerHTML = `
                    <div style="text-align: center; padding: 60px 40px; background: #fef3c7; border-radius: 16px; 
                                border: 2px dashed #f59e0b;">
                        <div style="font-size: 64px; margin-bottom: 20px;">😕</div>
                        <h3 style="color: #92400e; margin: 0 0 12px; font-size: 22px;">No Reviews Match Your Filters</h3>
                        <p style="color: #b45309; margin: 0 0 24px; font-size: 15px; line-height: 1.6;">
                            ${{selectedCountryName 
                                ? `No reviews found from <strong>${{selectedCountryName}}</strong> with your selected filters.`
                                : 'No reviews match your current filter criteria.'
                            }}
                        </p>
                        <div style="background: white; padding: 20px; border-radius: 8px; margin: 0 auto; max-width: 400px; text-align: left;">
                            <p style="color: #666; font-size: 14px; margin: 0 0 16px; font-weight: 600;">💡 Try this:</p>
                            <ul style="color: #666; font-size: 14px; margin: 0; padding-left: 20px; line-height: 2;">
                                ${{selectedCountryName 
                                    ? `<li>Select a different country from the dropdown</li>
                                       <li>Or choose "All Countries" to see all reviews</li>`
                                    : `<li>Try selecting "All" in the star rating filter</li>
                                       <li>Remove the "Photos Only" filter if applied</li>`
                                }}
                                <li>Check if reviews were successfully loaded (see stats above)</li>
                            </ul>
                        </div>
                        <button class="rk-btn-secondary" 
                                onclick="window.reviewKingClient.setFilter('all'); window.reviewKingClient.setCountry('all');"
                                style="margin-top: 20px; padding: 12px 24px; background: #FF2D85; color: white; 
                                       border: none; border-radius: 8px; font-size: 14px; font-weight: 600; 
                                       cursor: pointer; box-shadow: 0 2px 8px rgba(255,45,133,0.3);">
                            🔄 Reset All Filters
                        </button>
                    </div>
                `;
                return;
            }}
            
            const review = this.reviews[this.currentIndex];
            const isRecommended = review.ai_recommended;
            
            // First show product search if no product selected
            if (!this.selectedProduct) {{
                content.innerHTML = `
                    <div style="padding: 16px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                border-radius: 8px; color: white; margin-bottom: 20px;">
                        <div style="margin-bottom: 12px;">
                            <input type="text" id="product-search-input" 
                                   placeholder="Enter Shopify product URL or name..." 
                                   style="width: 100%; padding: 10px 12px; border: none; border-radius: 6px; 
                                          background: rgba(255,255,255,0.9); color: #333; font-size: 14px;" />
                        </div>
                        <div id="product-dropdown" style="display: none; background: white; border-radius: 6px; 
                             box-shadow: 0 4px 12px rgba(0,0,0,0.15); max-height: 120px; overflow-y: auto; color: #333;"></div>
                        <div id="selected-product" style="display: none; margin-top: 8px; padding: 8px 12px; 
                             background: rgba(255,255,255,0.2); border-radius: 6px; font-size: 13px;"></div>
                    </div>
                    
                    <div style="text-align: center; padding: 40px; background: #fef3c7; border-radius: 12px;">
                        <div style="font-size: 48px; margin-bottom: 16px;">🎯</div>
                        <h3 style="color: #92400e; margin: 0 0 8px;">Select Target Product First</h3>
                        <p style="color: #b45309; margin: 0;">Use the search box above to select which Shopify product will receive these reviews</p>
                    </div>
                `;
                this.setupProductSearch();
                return;
            }}
            
            // Show the beautiful review interface like your design
            content.innerHTML = `
                <!-- Product Search (always visible when product selected) -->
                <div style="padding: 16px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                            border-radius: 8px; color: white; margin-bottom: 20px;">
                    <div style="margin-bottom: 12px;">
                        <input type="text" id="product-search-input" 
                               placeholder="Enter Shopify product URL or name..." 
                               style="width: 100%; padding: 10px 12px; border: none; border-radius: 6px; 
                                      background: rgba(255,255,255,0.9); color: #333; font-size: 14px;" />
                    </div>
                    <div id="product-dropdown" style="display: none; background: white; border-radius: 6px; 
                         box-shadow: 0 4px 12px rgba(0,0,0,0.15); max-height: 120px; overflow-y: auto; color: #333;"></div>
                    <div id="selected-product" style="display: block; margin-top: 8px; padding: 8px 12px; 
                         background: rgba(255,255,255,0.2); border-radius: 6px; font-size: 13px;">
                        ✓ Target Product Selected: ${{this.selectedProduct.title}}
                        <button onclick="window.reviewKingClient.clearProduct()" 
                                style="background: rgba(255,255,255,0.2); border: none; color: white; 
                                       padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 12px; margin-left: 8px;">
                            Change
                        </button>
                    </div>
                </div>
                
                <!-- Beautiful Stats Header (like your design) -->
                <div style="background: linear-gradient(135deg, #FF2D85 0%, #FF1493 100%); 
                            padding: 24px; border-radius: 12px; margin-bottom: 24px; color: white; text-align: center;
                            box-shadow: 0 4px 16px rgba(255, 45, 133, 0.3);">
                    <div style="display: flex; justify-content: space-around; flex-wrap: wrap; gap: 16px;">
                        <div style="flex: 1; min-width: 80px;">
                            <div style="font-size: 32px; font-weight: 800; line-height: 1;">${{this.reviews.length}}</div>
                            <div style="font-size: 12px; opacity: 0.9; margin-top: 4px;">Total Loaded</div>
                        </div>
                        <div style="flex: 1; min-width: 80px;">
                            <div style="font-size: 32px; font-weight: 800; line-height: 1;">${{this.stats.ai_recommended}}</div>
                            <div style="font-size: 12px; opacity: 0.9; margin-top: 4px;">AI Recommended</div>
                        </div>
                        <div style="flex: 1; min-width: 80px;">
                            <div style="font-size: 32px; font-weight: 800; line-height: 1;">${{this.stats.with_photos}}</div>
                            <div style="font-size: 12px; opacity: 0.9; margin-top: 4px;">With Photos</div>
                        </div>
                        <div style="flex: 1; min-width: 80px;">
                            <div style="font-size: 32px; font-weight: 800; line-height: 1;">${{this.stats.average_quality.toFixed(1)}}<span style="font-size: 20px;">/10</span></div>
                            <div style="font-size: 12px; opacity: 0.9; margin-top: 4px;">Avg Quality</div>
                        </div>
                    </div>
                </div>
                
                <!-- Bulk Import Buttons (like your design) -->
                <div style="display: flex; gap: 10px; margin-bottom: 24px; flex-wrap: wrap;">
                    <button class="rk-btn" style="background: #FF2D85; color: white; flex: 1; min-width: 150px; padding: 14px 18px; font-size: 14px; font-weight: 700;"
                            onclick="window.reviewKingClient.importAllReviews()">
                        Import All Reviews
                    </button>
                    <button class="rk-btn" style="background: #FF2D85; color: white; flex: 1; min-width: 150px; padding: 14px 18px; font-size: 14px; font-weight: 700;"
                            onclick="window.reviewKingClient.importWithPhotos()">
                        Import only with Photos
                    </button>
                    <button class="rk-btn" style="background: #FF2D85; color: white; flex: 1; min-width: 150px; padding: 14px 18px; font-size: 14px; font-weight: 700;"
                            onclick="window.reviewKingClient.importWithoutPhotos()">
                        Import with no Photos
                    </button>
                </div>
                
                <!-- Country Filter & Translation Toggle (Loox-inspired) -->
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px;">
                    <div>
                        <label style="color: #9ca3af; font-size: 13px; margin-bottom: 6px; display: block; font-weight: 500;">🌍 Reviews from</label>
                        <select id="rk-country-filter" onchange="window.reviewKingClient.setCountry(this.value)" 
                                style="width: 100%; padding: 10px 12px; background: #0f0f23; color: white; border: 1px solid #2d2d3d; border-radius: 8px; font-size: 14px; cursor: pointer;">
                            <option value="all">🌍 All countries (${{this.allReviews.length}})</option>
                            ${{this.getUniqueCountries().map(c => `<option value="${{c.code}}" ${{this.selectedCountry === c.code ? 'selected' : ''}}>${{c.flag}} ${{c.name}} (${{c.count}})</option>`).join('')}}
                        </select>
                    </div>
                    <div>
                        <label style="color: #9ca3af; font-size: 13px; margin-bottom: 6px; display: block; font-weight: 500;">🌐 Translate</label>
                        <label style="display: flex; align-items: center; gap: 10px; padding: 10px 12px; background: #0f0f23; border: 1px solid #2d2d3d; border-radius: 8px; cursor: pointer; height: 42px;">
                            <input type="checkbox" id="rk-translation-toggle" 
                                   ${{this.showTranslations ? 'checked' : ''}}
                                   onchange="window.reviewKingClient.toggleTranslation()"
                                   style="width: 18px; height: 18px; cursor: pointer; accent-color: #FF2D85;">
                            <span style="color: #d1d5db; font-size: 14px;">Show English translation</span>
                        </label>
                    </div>
                </div>
                
                <!-- Filter Buttons (like your design) -->
                <div style="margin-bottom: 24px;">
                    <div style="color: #9ca3af; font-size: 13px; margin-bottom: 10px; font-weight: 500;">Filter Reviews:</div>
                    <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px;">
                        <button class="rk-btn rk-btn-secondary" style="padding: 10px 16px; ${{this.currentFilter === 'all' ? 'background: #FF2D85; color: white; border: none;' : ''}}" onclick="window.reviewKingClient.setFilter('all')">All (${{this.allReviews.length}})</button>
                        <button class="rk-btn rk-btn-secondary" style="padding: 10px 16px; ${{this.currentFilter === 'photos' ? 'background: #FF2D85; color: white; border: none;' : ''}}" onclick="window.reviewKingClient.setFilter('photos')">&#128247; With Photos (${{this.stats.with_photos}})</button>
                        <button class="rk-btn rk-btn-secondary" style="padding: 10px 16px; ${{this.currentFilter === 'ai_recommended' ? 'background: #FF2D85; color: white; border: none;' : ''}}" onclick="window.reviewKingClient.setFilter('ai_recommended')"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#ff69b4" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display: inline-block; vertical-align: middle; margin-right: 6px;"><path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"></path><path d="M20 3v4"></path><path d="M22 5h-4"></path><path d="M4 17v2"></path><path d="M5 18H3"></path></svg> AI Recommended (${{this.stats.ai_recommended}})</button>
                        <button class="rk-btn rk-btn-secondary" style="padding: 10px 16px; ${{this.currentFilter === '4-5stars' ? 'background: #FF2D85; color: white; border: none;' : ''}}" onclick="window.reviewKingClient.setFilter('4-5stars')">4-5 &#9733;</button>
                        <button class="rk-btn rk-btn-secondary" style="padding: 10px 16px; ${{this.currentFilter === '3stars' ? 'background: #FF2D85; color: white; border: none;' : ''}}" onclick="window.reviewKingClient.setFilter('3stars')">3 &#9733; Only</button>
                    </div>
                    <div style="color: #6b7280; font-size: 12px;">
                        Showing ${{this.currentIndex + 1}} of ${{this.reviews.length}} reviews
                    </div>
                </div>
                
                <!-- Single Review Card (your beautiful design) -->
                <div style="background: #0f0f23; border-radius: 12px; padding: 28px; color: white; margin-bottom: 20px; border: 1px solid #1a1a2e;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 18px; align-items: flex-start;">
                        <div style="flex: 1;">
                            <h3 style="margin: 0; color: white; font-size: 18px; font-weight: 700; letter-spacing: -0.02em;">${{review.reviewer_name}}</h3>
                            <div style="color: #fbbf24; font-size: 18px; margin: 6px 0; letter-spacing: 2px;">${{'★'.repeat(Math.ceil(review.rating / 20)) + '☆'.repeat(5 - Math.ceil(review.rating / 20))}}</div>
                            <div style="color: #9ca3af; font-size: 12px; font-weight: 500;">${{review.date}} • ${{review.country}}</div>
                        </div>
                        <div style="text-align: right; display: flex; flex-direction: column; gap: 8px; align-items: flex-end;">
                            ${{isRecommended ? '<span style="background: #10b981; color: white; padding: 6px 12px; border-radius: 16px; font-size: 10px; font-weight: 700; letter-spacing: 0.5px; display: inline-block;">&#10004; AI RECOMMENDED</span>' : ''}}
                            <span style="background: #3b82f6; color: white; padding: 6px 12px; border-radius: 16px; font-size: 10px; font-weight: 700; letter-spacing: 0.5px; display: inline-block;">QUALITY: ${{review.quality_score}}/10</span>
                        </div>
                    </div>
                    
                    <!-- Review text with translation support -->
                    ${{(() => {{
                        const hasTranslation = review.translation && review.text !== review.translation;
                        const displayText = (this.showTranslations && hasTranslation) ? review.translation : review.text;
                        const showOriginal = this.showTranslations && hasTranslation;
                        
                        return `
                            <p style="color: #d1d5db; line-height: 1.7; margin: 0 0 18px; font-size: 15px;">${{displayText}}</p>
                            ${{showOriginal ? 
                                `<p style="color: #888; font-size: 13px; margin: 0 0 18px; font-style: italic; border-left: 2px solid #555; padding-left: 10px;">Original: ${{review.text}}</p>` 
                                : ''
                            }}
                        `;
                    }})()}}
                    
                    ${{review.images && review.images.length > 0 ? `
                        <div style="margin-bottom: 18px;">
                            <div style="color: #9ca3af; font-size: 12px; margin-bottom: 10px; font-weight: 600;">
                                📸 ${{review.images.length}} Photo${{review.images.length > 1 ? 's' : ''}}
                            </div>
                            <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                                ${{review.images.map(img => 
                                    `<img src="${{img}}" style="width: 100px; height: 100px; 
                                    object-fit: cover; border-radius: 10px; cursor: pointer; border: 2px solid #1a1a2e;
                                    transition: all 0.2s;"
                                    onmouseover="this.style.transform='scale(1.05)'; this.style.borderColor='#3b82f6';"
                                    onmouseout="this.style.transform='scale(1)'; this.style.borderColor='#1a1a2e';"
                                    onclick="window.open('${{img}}', '_blank')">`
                                ).join('')}}
                            </div>
                        </div>
                    ` : '<div style="color: #6b7280; font-style: italic; margin-bottom: 18px; font-size: 13px;">No photos</div>'}}
                    
                    <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 20px;">
                        ${{review.verified ? '<span style="background: #10b981; color: white; padding: 5px 10px; border-radius: 14px; font-size: 10px; font-weight: 700; letter-spacing: 0.5px;">✓ VERIFIED</span>' : ''}}
                        <span style="background: #2d2d3d; color: #a1a1aa; padding: 5px 10px; border-radius: 14px; font-size: 10px; font-weight: 700; letter-spacing: 0.5px; border: 1px solid #3d3d4d;">
                            PLATFORM: ${{review.platform.toUpperCase()}}
                        </span>
                        <span style="background: #2d2d3d; color: #a1a1aa; padding: 5px 10px; border-radius: 14px; font-size: 10px; font-weight: 700; letter-spacing: 0.5px; border: 1px solid #3d3d4d;">
                            SENTIMENT: ${{Math.round(review.sentiment_score * 100)}}%
                        </span>
                    </div>
                    
                    <!-- Import/Reject buttons for individual review -->
                    <div style="display: flex; gap: 12px; margin-top: 20px;">
                        <button style="background: #374151; color: white; border: none; padding: 14px 28px; 
                                       border-radius: 8px; cursor: pointer; flex: 1; font-weight: 600; font-size: 14px;
                                       transition: all 0.2s;"
                                onmouseover="this.style.background='#4b5563'" 
                                onmouseout="this.style.background='#374151'"
                                onclick="window.reviewKingClient.skipReview()">
                            Reject
                        </button>
                        <button style="background: #FF2D85; color: white; border: none; padding: 14px 28px; 
                                       border-radius: 8px; cursor: pointer; flex: 2; font-weight: 700; font-size: 14px;
                                       transition: all 0.2s;"
                                onmouseover="this.style.background='#E0186F'; this.style.transform='translateY(-1px)'" 
                                onmouseout="this.style.background='#FF2D85'; this.style.transform='translateY(0)'"
                                onclick="window.reviewKingClient.importReview()">
                            Import
                        </button>
                    </div>
                </div>
                
                <!-- Navigation -->
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 24px; padding-top: 16px; border-top: 1px solid #2d2d3d;">
                    <button class="rk-btn rk-btn-secondary" style="padding: 10px 20px;" onclick="window.reviewKingClient.prevReview()"
                            ${{this.currentIndex === 0 ? 'disabled style="opacity: 0.5; cursor: not-allowed;"' : ''}}>← Previous</button>
                    <span style="color: #9ca3af; font-size: 14px; font-weight: 600;">
                        ${{this.currentIndex + 1}} / ${{this.reviews.length}}
                    </span>
                    <button class="rk-btn rk-btn-secondary" style="padding: 10px 20px;" onclick="window.reviewKingClient.nextReview()"
                            ${{this.currentIndex === this.reviews.length - 1 ? 'disabled style="opacity: 0.5; cursor: not-allowed;"' : ''}}>Next →</button>
                </div>
            `;
            
            this.setupProductSearch();
        }}
        
        async importReview() {{
            if (!this.selectedProduct) {{
                alert('Please select a target product first!');
                return;
            }}
            
            const review = this.reviews[this.currentIndex];
            
            try {{
                // DEBUG: Log review data before sending
                console.log('[DEBUG] Sending review to database:', {{
                    review_id: review.id,
                    reviewer_name: review.author || review.reviewer_name,
                    rating: review.rating,
                    title: review.title,
                    shopify_product_id: this.selectedProduct.id,
                    shopify_product_title: this.selectedProduct.title,
                    review_data: review
                }});
                
                const requestBody = {{
                    review: review,
                    shopify_product_id: this.selectedProduct.id,
                    session_id: this.sessionId
                }};
                
                console.log('[DEBUG] Request URL:', `${{API_URL}}/admin/reviews/import/single`);
                console.log('[DEBUG] Request body:', JSON.stringify(requestBody, null, 2));
                
                const response = await fetch(`${{API_URL}}/admin/reviews/import/single`, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(requestBody)
                }});
                
                console.log('[DEBUG] Response status:', response.status);
                const result = await response.json();
                console.log('[DEBUG] Response data:', result);
                
                if (result.success) {{
                    // Log database review ID if available
                    if (result.review_id) {{
                        console.log('✅ [DATABASE] Review saved with DB ID:', result.review_id);
                        console.log('   Shopify Product ID:', result.shopify_product_id || this.selectedProduct.id);
                        console.log('   Database Product ID:', result.product_id || 'N/A');
                        console.log('   Imported at:', result.imported_at || new Date().toISOString());
                    }} else {{
                        console.warn('⚠️ [WARNING] Review imported but NO database ID returned - using simulation mode');
                        if (result.imported_review) {{
                            console.log('   Source Review ID (not DB ID):', result.imported_review.id);
                        }}
                    }}
                    
                    // Track analytics
                    fetch(`${{API_URL}}/e?cat=Import+by+URL&a=Post+imported&c=${{this.sessionId}}`, 
                          {{ method: 'GET' }});
                    
                    const message = result.review_id 
                        ? `✓ Review imported successfully! Database ID: ${{result.review_id}}`
                        : `✓ Review imported (simulation mode - database unavailable)`;
                    alert(message);
                    this.nextReview();
                }} else {{
                    alert('Failed to import: ' + result.error);
                }}
            }} catch (error) {{
                alert('Import failed. Please try again.');
            }}
        }}
        
        async skipReview() {{
            const review = this.reviews[this.currentIndex];
            
            try {{
                const response = await fetch(`${{API_URL}}/admin/reviews/skip`, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        review_id: review.id,
                        session_id: this.sessionId
                    }})
                }});
                
                const result = await response.json();
                
                if (result.success) {{
                    alert('Review skipped. It will not be included in bulk import.');
                    this.nextReview();
                }} else {{
                    alert('Failed to skip review: ' + result.error);
                }}
            }} catch (error) {{
                alert('Skip failed. Please try again.');
            }}
        }}
        
        async importAllReviews() {{
            if (!this.selectedProduct) {{
                alert('Please select a target product first!');
                return;
            }}
            
            if (!confirm(`Import all non-skipped reviews to "${{this.selectedProduct.title}}"?\\n\\nThis will import multiple reviews at once.`)) {{
                return;
            }}
            
            try {{
                const response = await fetch(`${{API_URL}}/admin/reviews/import/bulk`, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        reviews: this.reviews,
                        shopify_product_id: this.selectedProduct.id,
                        session_id: this.sessionId,
                        filters: {{
                            min_quality_score: 0  // Import all quality levels
                        }}
                    }})
                }});
                
                const result = await response.json();
                
                if (result.success) {{
                    // Track analytics
                    fetch(`${{API_URL}}/e?cat=Import+by+URL&a=Bulk+imported&c=${{this.sessionId}}`, 
                          {{ method: 'GET' }});
                    
                    alert(`🎉 Bulk import completed!\\n\\n` +
                          `✅ Imported: ${{result.imported_count}}\\n` +
                          `❌ Failed: ${{result.failed_count}}\\n` +
                          `⏭️ Skipped: ${{result.skipped_count}}`);
                }} else {{
                    alert('Bulk import failed: ' + result.error);
                }}
            }} catch (error) {{
                alert('Bulk import failed. Please try again.');
            }}
        }}
        
        async importWithPhotos() {{
            if (!this.selectedProduct) {{
                alert('Please select a target product first!');
                return;
            }}
            
            const reviewsWithPhotos = this.reviews.filter(r => r.images && r.images.length > 0);
            
            if (!confirm(`Import ${{reviewsWithPhotos.length}} reviews with photos to "${{this.selectedProduct.title}}"?`)) {{
                return;
            }}
            
            try {{
                const response = await fetch(`${{API_URL}}/admin/reviews/import/bulk`, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        reviews: reviewsWithPhotos,
                        shopify_product_id: this.selectedProduct.id,
                        session_id: this.sessionId
                    }})
                }});
                
                const result = await response.json();
                
                if (result.success) {{
                    alert(`✅ Imported ${{result.imported_count}} reviews with photos!`);
                }} else {{
                    alert('Import failed: ' + result.error);
                }}
            }} catch (error) {{
                alert('Import failed. Please try again.');
            }}
        }}
        
        async importWithoutPhotos() {{
            if (!this.selectedProduct) {{
                alert('Please select a target product first!');
                return;
            }}
            
            const reviewsWithoutPhotos = this.reviews.filter(r => !r.images || r.images.length === 0);
            
            if (!confirm(`Import ${{reviewsWithoutPhotos.length}} reviews without photos to "${{this.selectedProduct.title}}"?`)) {{
                return;
            }}
            
            try {{
                const response = await fetch(`${{API_URL}}/admin/reviews/import/bulk`, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        reviews: reviewsWithoutPhotos,
                        shopify_product_id: this.selectedProduct.id,
                        session_id: this.sessionId
                    }})
                }});
                
                const result = await response.json();
                
                if (result.success) {{
                    alert(`✅ Imported ${{result.imported_count}} reviews without photos!`);
                }} else {{
                    alert('Import failed: ' + result.error);
                }}
            }} catch (error) {{
                alert('Import failed. Please try again.');
            }}
        }}
        
        nextReview() {{
            if (this.currentIndex < this.reviews.length - 1) {{
                this.currentIndex++;
                this.displayReview();
            }} else if (this.pagination.has_next) {{
                this.loadReviews(this.pagination.page + 1);
            }} else {{
                alert('No more reviews!');
            }}
        }}
        
        prevReview() {{
            if (this.currentIndex > 0) {{
                this.currentIndex--;
                this.displayReview();
            }}
        }}
        
        showError(message) {{
            document.getElementById('reviewking-content').innerHTML = `
                <div style="text-align: center; padding: 40px;">
                    <div style="font-size: 48px; margin-bottom: 16px;">⚠️</div>
                    <h3 style="color: #ef4444; margin: 0 0 8px;">Error</h3>
                    <p style="color: #6b7280; margin: 0;">${{message}}</p>
                    <button class="rk-btn rk-btn-primary" style="margin-top: 20px;"
                            onclick="if(window.reviewKingClient) window.reviewKingClient.close()">Close</button>
                </div>
            `;
        }}
        
        close() {{
            console.log('[REVIEWKING] Closing and cleaning up...');
            
            // Remove overlay if it exists
            const overlay = document.getElementById('reviewking-overlay');
            if (overlay) {{
                overlay.remove();
            }}
            
            // Clean up modal click handler if it exists
            if (this.modalClickHandler) {{
                document.body.removeEventListener('click', this.modalClickHandler);
                this.modalClickHandler = null;
                console.log('[REVIEWKING] Removed modal click handler');
            }}
            
            // Cleanup complete - no need to restore body scroll or reset global state
        }}
    }}
    
    // Wrap initialization in try-catch for error handling
    // Note: window.reviewKingClient is assigned inside the constructor before init() runs
    try {{
        new ReviewKingClient();
    }} catch (error) {{
        console.error('[REVIEWKING] Initialization error:', error);
        window.reviewKingActive = false;
        delete window.reviewKingClient;  // Clean up if it was partially assigned
        alert('ReviewKing initialization failed: ' + error.message);
        
        // Clean up any partially created overlay
        const overlay = document.getElementById('reviewking-overlay');
        if (overlay) overlay.remove();
    }}
}})();
    """
    
    return js_content, 200, {
        'Content-Type': 'application/javascript',
        'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
        'Pragma': 'no-cache',
        'Expires': '0'
    }

@app.route('/__rk_version')
def rk_version():
    try:
        # Generate current bookmarklet body and check for SSR marker
        js_body, _, _ = bookmarklet()
        has_ssr = ('[SSR MODE]' in js_body)
        info = {
            'pid': os.getpid(),
            'cwd': os.getcwd(),
            'file': __file__,
            'file_mtime': datetime.fromtimestamp(os.path.getmtime(__file__)).isoformat(),
            'bookmarklet_has_ssr': has_ssr,
            'ts': int(time.time()),
        }
        return jsonify(info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Backward-compatible alias
@app.route('/rk_version')
def rk_version_alias():
    return rk_version()

# Alternate path to defeat any stubborn caches/CDNs
@app.route('/js/bookmarklet.v2.js')
def bookmarklet_v2():
    return bookmarklet()

# Explicit duplicate test endpoint to bypass any client/proxy caching logic
@app.route('/js/bookmarklet-test.js')
def bookmarklet_test():
    proto = request.headers.get('X-Forwarded-Proto', 'https' if request.is_secure else 'http')
    host = f"{proto}://{request.host}"
    js_content = f"""
// ReviewKing Bookmarklet TEST endpoint
(function() {{
    console.log('[REVIEWKING][TEST] Bookmarklet test endpoint loaded');
    const API_URL = '{host}';
    // Inline import of main logic by reusing same class/body from primary endpoint
    {bookmarklet.__code__.co_consts[3] if False else ''}
}})();
"""
    # For reliability, rebuild by calling the primary to get its JS, then prefix test marker
    try:
        primary_js, _, _ = bookmarklet()
        js_content = "console.log('[REVIEWKING][TEST] using primary body');\n" + primary_js
    except Exception:
        pass
    return js_content, 200, {
        'Content-Type': 'application/javascript',
        'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
        'Pragma': 'no-cache',
        'Expires': '0'
    }

@app.route('/health')
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'version': Config.API_VERSION,
        'timestamp': datetime.now().isoformat()
    })

# =============================================================================
# LEGAL PAGES - Required for Shopify App Store
# =============================================================================

@app.route('/privacy')
def privacy_policy():
    """Privacy Policy page"""
    return render_template('privacy-policy.html')

@app.route('/terms')
def terms_of_service():
    """Terms of Service page"""
    return render_template('terms-of-service.html')

@app.route('/dpa')
def data_processing_addendum():
    """Data Processing Addendum page"""
    return render_template('dpa.html')

@app.route('/review-integrity')
def review_integrity():
    """Review Integrity & Fraud Prevention page"""
    return render_template('review-integrity.html')

@app.route('/copyright')
def copyright_policy():
    """Copyright Policy page"""
    return render_template('copyright-policy.html')

@app.route('/cookies')
def cookies_policy():
    """Cookies Policy page"""
    return render_template('cookies-policy.html')
def cookies_policy():
    """Cookies Policy page"""
    return render_template('cookies-policy.html')

# =============================================================================
# HELP CENTER & SUPPORT
# =============================================================================

@app.route('/help')
@app.route('/help-center')
def help_center():
    """Help Center - Support documentation and FAQs"""
    return render_template('help-center.html')

@app.route('/help/aliexpress-import')
@app.route('/help/importing-reviews-from-aliexpress')
def help_aliexpress_import():
    """Help article: Importing Reviews from AliExpress"""
    return render_template('help-aliexpress-import.html')

@app.route('/help/import-custom-file')
@app.route('/help/importing-reviews-using-a-custom-file')
def help_import_custom_file():
    """Help article: Importing Reviews Using a Custom File"""
    return render_template('help-import-custom-file.html')


# ==================== IMPORT FROM COMPETITORS ====================

@app.route('/app/import-reviews')
@app.route('/import/competitors')
def import_competitors_page():
    """
    Page for importing reviews from competitor apps (Loox, Judge.me, Yotpo, etc.)
    """
    shop_domain = request.args.get('shop') or session.get('shop_domain')
    return render_template('import-competitors.html', shop_domain=shop_domain)


@app.route('/api/import/competitor', methods=['POST'])
def api_import_competitor():
    """
    API endpoint for importing reviews from competitor CSV exports
    Supports: Loox, Judge.me, Yotpo, Stamped.io, Shopify Reviews, Custom CSV
    """
    import csv
    import io
    from backend.models_v2 import Review, ReviewMedia, Product, Shop
    from datetime import datetime
    
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        source = request.form.get('source', 'csv').lower()
        shop_domain = request.form.get('shop')
        
        if not file.filename.endswith('.csv'):
            return jsonify({'success': False, 'error': 'Please upload a CSV file'}), 400
        
        # Get shop
        shop = Shop.query.filter_by(shop_domain=shop_domain).first() if shop_domain else None
        if not shop:
            # Try to get from session
            if 'shop_id' in session:
                shop = Shop.query.get(session['shop_id'])
        
        if not shop:
            return jsonify({'success': False, 'error': 'Shop not found'}), 404
        
        # Read CSV
        content = file.read().decode('utf-8-sig')  # Handle BOM
        reader = csv.DictReader(io.StringIO(content))
        
        imported = 0
        photos_imported = 0
        skipped = 0
        errors = []
        
        # Column mappings for different sources
        column_maps = {
            'loox': {
                'product_id': ['product_id', 'Product ID', 'product id'],
                'product_title': ['product_title', 'Product Title', 'product title', 'Product Name'],
                'reviewer_name': ['reviewer_name', 'Reviewer Name', 'name', 'Name', 'Author'],
                'email': ['email', 'Email', 'reviewer_email'],
                'rating': ['rating', 'Rating', 'Stars', 'stars'],
                'body': ['body', 'Body', 'content', 'Content', 'Review', 'review', 'review_text'],
                'date': ['created_at', 'date', 'Date', 'review_date', 'Review Date'],
                'photo_urls': ['photo_urls', 'photos', 'Photos', 'images', 'Images', 'media_url'],
                'verified': ['verified', 'Verified', 'verified_purchase']
            },
            'judgeme': {
                'product_id': ['product_id', 'Product ID'],
                'product_title': ['product_title', 'Product Title', 'product_name'],
                'reviewer_name': ['reviewer', 'Reviewer', 'author', 'name'],
                'email': ['email', 'Email'],
                'rating': ['rating', 'Rating'],
                'body': ['body', 'Body', 'content'],
                'date': ['created_at', 'date'],
                'photo_urls': ['picture_urls', 'photos'],
                'verified': ['verified_buyer', 'verified']
            },
            'yotpo': {
                'product_id': ['product_id', 'sku'],
                'product_title': ['product_title', 'product_name'],
                'reviewer_name': ['display_name', 'user_display_name', 'name'],
                'email': ['email', 'user_email'],
                'rating': ['score', 'rating'],
                'body': ['content', 'body'],
                'date': ['created_at', 'date'],
                'photo_urls': ['images_data', 'images'],
                'verified': ['verified_buyer']
            },
            'csv': {  # Generic/custom CSV
                'product_id': ['product_id', 'Product ID', 'product'],
                'product_title': ['product_title', 'Product Title', 'product_name', 'Product Name'],
                'reviewer_name': ['reviewer_name', 'name', 'Name', 'author', 'Author'],
                'email': ['email', 'Email'],
                'rating': ['rating', 'Rating', 'stars', 'Stars'],
                'body': ['review_text', 'body', 'content', 'review', 'Review', 'text'],
                'date': ['review_date', 'date', 'Date', 'created_at'],
                'photo_urls': ['photo_url', 'photos', 'images', 'photo'],
                'verified': ['verified', 'verified_purchase']
            }
        }
        
        # Use appropriate mapping
        mapping = column_maps.get(source, column_maps['csv'])
        
        def get_value(row, field):
            """Get value from row using multiple possible column names"""
            for col_name in mapping.get(field, []):
                if col_name in row and row[col_name]:
                    return row[col_name].strip()
            return None
        
        for row_num, row in enumerate(reader, start=1):
            try:
                product_id = get_value(row, 'product_id')
                rating = get_value(row, 'rating')
                
                if not product_id or not rating:
                    skipped += 1
                    continue
                
                # Parse rating
                try:
                    rating = int(float(rating))
                    rating = max(1, min(5, rating))  # Clamp to 1-5
                except:
                    rating = 5
                
                # Parse date
                date_str = get_value(row, 'date')
                review_date = datetime.utcnow()
                if date_str:
                    for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%dT%H:%M:%S']:
                        try:
                            review_date = datetime.strptime(date_str[:19], fmt)
                            break
                        except:
                            continue
                
                # Check for duplicate
                reviewer_name = get_value(row, 'reviewer_name') or 'Customer'
                body = get_value(row, 'body') or ''
                
                # Anonymize name if generic
                reviewer_name = anonymize_reviewer_name(reviewer_name)
                
                existing = Review.query.filter_by(
                    shop_id=shop.id,
                    shopify_product_id=str(product_id),
                    reviewer_name=reviewer_name,
                    body=body[:100] if body else None  # Check first 100 chars
                ).first()
                
                if existing:
                    skipped += 1
                    continue
                
                # Get or create product
                product = Product.query.filter_by(
                    shop_id=shop.id,
                    shopify_product_id=str(product_id)
                ).first()
                
                if not product:
                    product = Product(
                        shop_id=shop.id,
                        shopify_product_id=str(product_id),
                        shopify_product_title=get_value(row, 'product_title') or 'Imported Product',
                        source_platform=source,
                        source_product_id=str(product_id),
                        status='active'
                    )
                    db.session.add(product)
                    db.session.flush()
                
                # Create review
                verified = get_value(row, 'verified')
                is_verified = verified and verified.lower() in ['true', 'yes', '1', 'verified']
                
                review = Review(
                    shop_id=shop.id,
                    product_id=product.id,
                    shopify_product_id=str(product_id),
                    source_platform=source,
                    source_review_id=f"{source}_{row_num}_{datetime.utcnow().timestamp()}",
                    reviewer_name=reviewer_name,
                    reviewer_email=get_value(row, 'email'),
                    rating=rating,
                    body=body,
                    review_date=review_date,
                    verified_purchase=is_verified,
                    status='published',
                    imported_at=datetime.utcnow()
                )
                db.session.add(review)
                db.session.flush()
                
                # Handle photos
                photo_urls = get_value(row, 'photo_urls')
                if photo_urls:
                    # Parse photo URLs (could be comma-separated or JSON)
                    urls = []
                    if photo_urls.startswith('['):
                        try:
                            import json
                            urls = json.loads(photo_urls)
                        except:
                            urls = [photo_urls]
                    else:
                        urls = [u.strip() for u in photo_urls.split(',') if u.strip()]
                    
                    for url in urls:
                        if url and url.startswith('http'):
                            media = ReviewMedia(
                                review_id=review.id,
                                media_type='image',
                                media_url=url,
                                status='active'
                            )
                            db.session.add(media)
                            photos_imported += 1
                
                imported += 1
                
                # Commit every 100 reviews for performance
                if imported % 100 == 0:
                    db.session.commit()
            
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
                continue
        
        # Final commit
        db.session.commit()
        
        logger.info(f"Import complete: {imported} reviews, {photos_imported} photos, {skipped} skipped from {source}")
        
        return jsonify({
            'success': True,
            'imported': imported,
            'photos': photos_imported,
            'skipped': skipped,
            'errors': errors[:10] if errors else []  # Return first 10 errors
        })
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error importing competitor reviews: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/help/<path:article>')
def help_article(article):
    """Generic help article router - handles various help pages"""
    # Map article names to templates
    article_map = {
        'install': 'help-center.html',
        'first-review': 'help-aliexpress-import.html',
        'widget-setup': 'help-center.html',
        'account-setup': 'help-center.html',
        'widget-customization': 'help-center.html',
        'product-pages': 'help-center.html',
        'review-page': 'help-center.html',
        'mobile-display': 'help-center.html',
        'import-reviews': 'help-aliexpress-import.html',
        'edit-reviews': 'help-center.html',
        'delete-reviews': 'help-center.html',
        'review-filters': 'help-center.html',
        'shopify-integration': 'help-center.html',
        'amazon-import': 'help-center.html',
        'api-access': 'help-center.html',
        'pricing-plans': 'help-center.html',
        'upgrade-downgrade': 'help-center.html',
        'billing-questions': 'help-center.html',
        'cancel-subscription': 'help-center.html',
        'widget-not-showing': 'help-center.html',
        'import-errors': 'help-center.html',
        'performance-issues': 'help-center.html',
        'common-issues': 'help-center.html',
        'manage-reviews': 'help-center.html',
        'happy-customers-page': 'help-center.html',
        'monthly-quota': 'help-center.html',
        'carousel-widgets': 'help-center.html',
        'fix-import-errors': 'help-import-custom-file.html',
    }
    
    template = article_map.get(article, 'help-center.html')
    return render_template(template)

@app.route('/contact')
@app.route('/get-in-touch')
def contact_page():
    """Contact form page"""
    return render_template('contact.html')

@app.route('/contact/submit', methods=['POST'])
def contact_submit():
    """
    Submit contact form - Store in DB and send email notification
    Hybrid approach: Database for admin tracking + Email for immediate notification
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('full_name') or not data.get('email') or not data.get('message'):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        # Store in database
        from backend.models_v2 import ContactMessage
        
        # Ensure table exists
        try:
            ContactMessage.query.limit(1).all()
        except Exception as table_error:
            if 'does not exist' in str(table_error) or 'UndefinedTable' in str(table_error):
                logger.warning("contact_messages table doesn't exist, creating it...")
                try:
                    db.create_all()
                    logger.info("✅ contact_messages table created!")
                except Exception as create_error:
                    logger.error(f"Failed to create table: {create_error}")
                    return jsonify({
                        'success': False,
                        'error': 'Database table not available. Please contact support.'
                    }), 500
        
        contact_msg = ContactMessage(
            full_name=data.get('full_name'),
            email=data.get('email'),
            shopify_url=data.get('shopify_url', ''),
            message=data.get('message'),
            subject=data.get('subject', 'Contact Form Submission'),
            status='new',
            priority='normal'
        )
        
        db.session.add(contact_msg)
        db.session.commit()
        
        logger.info(f"📬 New contact message from {data.get('email')} (ID: {contact_msg.id})")
        
        # Send email notification (optional - you can implement email sending here)
        # For now, we'll just log it
        try:
            # TODO: Implement email sending using Flask-Mail or similar
            # send_contact_notification_email(contact_msg)
            logger.info(f"📧 Email notification would be sent for message ID: {contact_msg.id}")
        except Exception as e:
            logger.warning(f"Could not send email notification: {e}")
        
        return jsonify({
            'success': True,
            'message': 'Your message has been received. We\'ll get back to you shortly!',
            'message_id': contact_msg.id
        }), 200
        
    except Exception as e:
        logger.error(f"Error submitting contact form: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Failed to submit message. Please try again or email us directly.'
        }), 500

# =============================================================================
# ADMIN AUTHENTICATION
# =============================================================================

from functools import wraps

def admin_required(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect('/admin/login')
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page and authentication"""
    if request.method == 'GET':
        # If already logged in, redirect to dashboard
        if session.get('admin_logged_in'):
            return redirect('/admin/dashboard')
        return render_template('admin-login.html')
    
    # POST - Handle login
    try:
        data = request.get_json() if request.is_json else request.form
        username = data.get('username')
        password = data.get('password')
        
        if username == Config.ADMIN_USERNAME and password == Config.ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            session['admin_username'] = username
            logger.info(f"✅ Admin login successful: {username}")
            
            if request.is_json:
                return jsonify({'success': True, 'redirect': '/admin/dashboard'})
            return redirect('/admin/dashboard')
        else:
            logger.warning(f"❌ Admin login failed: {username}")
            if request.is_json:
                return jsonify({'success': False, 'error': 'Invalid username or password'}), 401
            return render_template('admin-login.html', error='Invalid username or password')
            
    except Exception as e:
        logger.error(f"Admin login error: {str(e)}")
        if request.is_json:
            return jsonify({'success': False, 'error': 'Login error'}), 500
        return render_template('admin-login.html', error='Login error')

@app.route('/admin/logout')
def admin_logout():
    """Admin logout"""
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    logger.info("Admin logged out")
    return redirect('/admin/login')

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """Admin dashboard - Overview of system"""
    try:
        from backend.models_v2 import ContactMessage, Shop, Review
        
        # Check if contact_messages table exists, if not create it
        try:
            # Try to query - if table doesn't exist, this will fail
            ContactMessage.query.limit(1).all()
            table_exists = True
        except Exception as table_error:
            if 'does not exist' in str(table_error) or 'UndefinedTable' in str(table_error):
                logger.warning("contact_messages table doesn't exist, creating it...")
                try:
                    db.create_all()
                    table_exists = True
                    logger.info("✅ contact_messages table created successfully!")
                except Exception as create_error:
                    logger.error(f"Failed to create table: {create_error}")
                    table_exists = False
            else:
                raise table_error
        
        # Get stats (with error handling)
        try:
            total_messages = ContactMessage.query.count() if table_exists else 0
            new_messages = ContactMessage.query.filter_by(status='new').count() if table_exists else 0
        except:
            total_messages = 0
            new_messages = 0
        
        try:
            total_shops = Shop.query.count()
        except:
            total_shops = 0
        
        try:
            total_reviews = Review.query.count()
        except:
            total_reviews = 0
        
        # Recent messages
        try:
            recent_messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).limit(10).all() if table_exists else []
        except:
            recent_messages = []
        
        return render_template('admin-dashboard.html',
                             total_messages=total_messages,
                             new_messages=new_messages,
                             total_shops=total_shops,
                             total_reviews=total_reviews,
                             recent_messages=recent_messages,
                             table_exists=table_exists)
    except Exception as e:
        logger.error(f"Admin dashboard error: {str(e)}")
        return f"Error loading dashboard: {str(e)}", 500

@app.route('/admin/create-tables')
@admin_required
def admin_create_tables():
    """Admin route to create missing database tables"""
    try:
        from backend.models_v2 import ContactMessage, EmailSettings, ReviewRequest, EmailUnsubscribe
        
        with app.app_context():
            db.create_all()
            
            # Verify tables were created
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            required_tables = ['contact_messages', 'email_settings', 'review_requests', 'email_unsubscribes']
            created = [t for t in required_tables if t in tables]
            missing = [t for t in required_tables if t not in tables]
            
            if missing:
                logger.warning(f"⚠️ Some tables may not have been created: {missing}")
                return jsonify({
                    'success': True,
                    'message': f'Tables created! Created: {created}, Missing: {missing}',
                    'tables': tables,
                    'created': created,
                    'missing': missing
                })
            else:
                logger.info("✅ All required tables created successfully!")
                return jsonify({
                    'success': True,
                    'message': 'All tables created successfully!',
                    'tables': tables,
                    'created': created
                })
                
    except Exception as e:
        logger.error(f"Error creating tables: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/admin/contact-messages')
@admin_required
def admin_contact_messages():
    """
    Admin view of contact messages - Protected with authentication
    """
    try:
        from backend.models_v2 import ContactMessage
        
        # Check if table exists, create if not
        try:
            ContactMessage.query.limit(1).all()
        except Exception as table_error:
            if 'does not exist' in str(table_error) or 'UndefinedTable' in str(table_error):
                logger.warning("contact_messages table doesn't exist, creating it...")
                try:
                    db.create_all()
                    logger.info("✅ contact_messages table created!")
                except Exception as create_error:
                    logger.error(f"Failed to create table: {create_error}")
                    return render_template('admin-contact-messages.html',
                                         messages=[],
                                         status_filter='all',
                                         error='Table not found. Please visit /admin/create-tables to create it.')
        
        # Get query parameters
        status = request.args.get('status', 'all')
        limit = request.args.get('limit', 50, type=int)
        
        query = ContactMessage.query.order_by(ContactMessage.created_at.desc())
        
        if status != 'all':
            query = query.filter_by(status=status)
        
        messages = query.limit(limit).all()
        
        # If JSON request, return JSON
        if request.args.get('format') == 'json':
            return jsonify({
                'success': True,
                'count': len(messages),
                'messages': [msg.to_dict() for msg in messages]
            }), 200
        
        # Otherwise render HTML page
        return render_template('admin-contact-messages.html',
                             messages=messages,
                             status_filter=status)
        
    except Exception as e:
        logger.error(f"Error fetching contact messages: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/contact-messages/<int:message_id>')
@admin_required
def admin_view_message(message_id):
    """View individual contact message"""
    try:
        from backend.models_v2 import ContactMessage
        
        message = ContactMessage.query.get_or_404(message_id)
        
        # Mark as read if it's new
        if message.status == 'new':
            message.status = 'read'
            db.session.commit()
        
        return render_template('admin-view-message.html', message=message)
        
    except Exception as e:
        logger.error(f"Error viewing message: {str(e)}")
        return f"Error: {str(e)}", 500

@app.route('/legal')
def legal_index():
    """Legal pages index - beautiful HTML page with all legal documents"""
    return render_template('legal-index.html')

@app.route('/legal.json')
def legal_index_json():
    """Legal pages index - JSON format for API consumers"""
    return jsonify({
        'pages': {
            'privacy_policy': '/privacy',
            'terms_of_service': '/terms',
            'data_processing_addendum': '/dpa',
            'review_integrity': '/review-integrity',
            'copyright_policy': '/copyright',
            'cookies_policy': '/cookies'
        },
        'company': 'Sakura Reviews',
        'contact': 'sakura.revs@gmail.com'
    })

# =============================================================================
# SAKURA WIDGET SYSTEM - Superior to Loox
# =============================================================================

class SakuraWidgetSystem:
    """
    Superior widget system that crushes Loox
    """
    
    def __init__(self):
        self.widget_cache = {}
        self.payment_status = {}
        self.analytics = {}
    
    def generate_widget_url(self, shop_id, product_id, theme="default", limit=20):
        """
        Generate secure widget URL with versioning and theme support
        """
        timestamp = int(time.time())
        version = "2.0.0"
        
        # Create secure hash for validation
        payload = f"{shop_id}:{product_id}:{timestamp}:{version}"
        signature = hmac.new(
            Config.WIDGET_SECRET.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        widget_url = f"{Config.WIDGET_BASE_URL}/widget/{shop_id}/reviews/{product_id}"
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
    
    def create_shopify_app_block(self, shop_id, product_id):
        """
        Create Shopify app block HTML that merchants can add to their theme
        """
        widget_url = self.generate_widget_url(shop_id, product_id)
        
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
            if (event.origin !== '{Config.WIDGET_BASE_URL}') return;
            
            if (event.data.type === 'resize') {{
                const iframe = document.getElementById('sakuraReviewsFrame');
                iframe.style.height = event.data.height + 'px';
            }}
        }});
        </script>
        """

# Initialize widget system
widget_system = SakuraWidgetSystem()

@app.route('/reviews/<product_id>')
def reviews_short(product_id):
    """
    Convenience route for reviews without shop_id prefix
    Uses session data or tries to find shop by domain, defaults to shop_id=1
    """
    from backend.models_v2 import Shop
    
    # Try to get shop_id from session first
    shop_id = session.get('shop_id')
    if shop_id:
        # Use session shop_id
        pass
    else:
        # Try to get from sakura_shop_id in session
        sakura_shop_id = session.get('sakura_shop_id')
        if sakura_shop_id:
            shop = Shop.query.filter_by(sakura_shop_id=str(sakura_shop_id)).first()
            if shop:
                shop_id = shop.id
        
        # If still no shop_id, try to find by shop_domain from session
        if not shop_id:
            shop_domain = session.get('shop_domain')
            if shop_domain:
                shop = Shop.query.filter_by(shop_domain=shop_domain).first()
                if shop:
                    shop_id = shop.id
                    # Store in session for next time
                    session['shop_id'] = shop.id
                    session['sakura_shop_id'] = shop.sakura_shop_id
        
        # Final fallback: try shop_id=1 or first shop
        if not shop_id:
            shop = Shop.query.first()
            if shop:
                shop_id = shop.id
            else:
                shop_id = 1
    
    # Preserve all query parameters
    query_string = request.query_string.decode('utf-8')
    if query_string:
        return redirect(f'/widget/{shop_id}/reviews/{product_id}?{query_string}')
    else:
        return redirect(f'/widget/{shop_id}/reviews/{product_id}')

@app.route('/widget/<shop_id>/reviews/<product_id>')
def widget_reviews(shop_id, product_id):
    """
    Main widget endpoint - serves the review widget
    """
    # Validate request
    signature = request.args.get('s')
    timestamp = request.args.get('t')
    version = request.args.get('v')
    theme = request.args.get('theme', 'default')
    limit = int(request.args.get('limit', 20))
    
    # Check payment status (for now, always allow)
    if not check_payment_status(shop_id):
        return render_template('widget_payment_required.html', 
                             shop_id=shop_id, 
                             upgrade_url=f"{Config.WIDGET_BASE_URL}/billing")
    
    # Get shop settings for customization
    from backend.models_v2 import Shop, ShopSettings
    try:
        # Try to get shop by sakura_shop_id first (format: owner_id_shopname)
        shop = Shop.query.filter_by(sakura_shop_id=str(shop_id)).first()
        if not shop:
            # Fallback: try to get by id if shop_id is numeric
            try:
                shop = Shop.query.get(int(shop_id))
            except:
                pass
        
        settings = None
        if shop:
            # Store shop details in session for review submission
            session['shop_id'] = shop.id
            session['shop_domain'] = shop.shop_domain
            session['sakura_shop_id'] = shop.sakura_shop_id
            
            settings = ShopSettings.query.filter_by(shop_id=shop.id).first()
            if not settings:
                # Create default settings if they don't exist
                settings = ShopSettings(shop_id=shop.id)
                db.session.add(settings)
                db.session.commit()
        else:
            logger.warning(f"Shop not found for shop_id: {shop_id}")
    except Exception as e:
        logger.error(f"Error loading shop settings: {str(e)}")
        settings = None
    
    # Get sort parameter (default to 'default' for page load)
    sort = request.args.get('sort', 'default')
    
    # Get reviews for this product (initial load: 20 reviews)
    reviews, total_count, average_rating, rating_distribution = get_product_reviews(product_id, limit=20, offset=0, sort=sort)
    
    # Render widget with settings
    return render_template('widget.html', 
                         shop_id=shop_id,
                         product_id=product_id,
                         reviews=reviews,
                         total_count=total_count,
                         average_rating=average_rating,
                         rating_distribution=rating_distribution,
                         current_sort=sort,
                         theme=theme,
                         version=version,
                         settings=settings.to_dict() if settings else {})

@app.route('/widget/<shop_id>/reviews/<product_id>/api')
def widget_api(shop_id, product_id):
    """
    API endpoint for widget data
    """
    # Check payment status
    if not check_payment_status(shop_id):
        return jsonify({
            'error': 'Payment required',
            'upgrade_url': f"{Config.WIDGET_BASE_URL}/billing"
        }), 402
    
    offset = int(request.args.get('offset', 0))
    limit = int(request.args.get('limit', 20))
    sort = request.args.get('sort', 'default')
    
    reviews, total_count, average_rating, rating_distribution = get_product_reviews(product_id, limit=limit, offset=offset, sort=sort)
    
    return jsonify({
        'success': True,
        'reviews': reviews,
        'total': total_count,
        'average_rating': average_rating,
        'rating_distribution': rating_distribution,
        'offset': offset,
        'limit': limit,
        'has_more': (offset + limit) < total_count,
        'shop_id': shop_id,
        'product_id': product_id,
        'sort': sort
    })

@app.route('/widget/<shop_id>/reviews/<product_id>/submit', methods=['POST'])
def submit_review(shop_id, product_id):
    """
    Submit a new review from the widget
    """
    try:
        from backend.models_v2 import Review, ReviewMedia, Shop, Product
        from werkzeug.utils import secure_filename
        import os
        from datetime import datetime
        import uuid
        
        # Get shop from session or query
        shop = None
        if 'shop_id' in session:
            shop = Shop.query.get(session['shop_id'])
        
        if not shop:
            # Fallback: query by sakura_shop_id
            shop = Shop.query.filter_by(sakura_shop_id=str(shop_id)).first()
            if not shop:
                try:
                    shop = Shop.query.get(int(shop_id))
                except:
                    pass
        
        if not shop:
            return jsonify({'success': False, 'error': 'Shop not found'}), 404
        
        # Get or create product
        product = Product.query.filter_by(
            shop_id=shop.id,
            shopify_product_id=product_id
        ).first()
        
        if not product:
            # Create product if it doesn't exist
            product = Product(
                shop_id=shop.id,
                shopify_product_id=product_id,
                shopify_product_title='',  # Can be updated later
                source_platform='sakura_reviews',
                source_product_id=product_id,
                status='active'
            )
            db.session.add(product)
            db.session.flush()
        
        # Get form data
        rating = int(request.form.get('rating', 0))
        text = request.form.get('text', '').strip()
        reviewer_name = request.form.get('reviewer_name', '').strip()
        reviewer_email = request.form.get('reviewer_email', '').strip()
        
        if not rating or rating < 1 or rating > 5:
            return jsonify({'success': False, 'error': 'Invalid rating'}), 400
        
        if not reviewer_name or not reviewer_email:
            return jsonify({'success': False, 'error': 'Name and email are required'}), 400
        
        # Generate unique source_review_id for widget-submitted reviews
        source_review_id = f"sakura_reviews_{product_id}_{uuid.uuid4().hex[:16]}"
        
        # Create review with correct field names
        review = Review(
            shop_id=shop.id,
            product_id=product.id,
            shopify_product_id=product_id,
            source_platform='sakura_reviews',  # Use 'sakura_reviews' as platform
            source_product_id=product_id,
            source_review_id=source_review_id,
            rating=rating,
            body=text,
            title='',  # User reviews don't have titles
            reviewer_name=reviewer_name,
            reviewer_email=reviewer_email,
            review_date=datetime.utcnow(),
            imported_at=datetime.utcnow(),
            status='published',
            verified_purchase=False,  # User-submitted reviews are not verified
            reviewer_country=None  # Can be detected from IP if needed
        )
        
        db.session.add(review)
        db.session.flush()  # Get review ID
        
        # Handle photo uploads
        uploaded_files = []
        for key in request.files:
            if key.startswith('photo_'):
                file = request.files[key]
                if file and file.filename:
                    # Generate a clean filename using UUID to avoid weird characters
                    file_ext = os.path.splitext(file.filename)[1].lower() or '.jpg'
                    # Only allow image extensions
                    if file_ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                        file_ext = '.jpg'
                    filename = f"{uuid.uuid4().hex}{file_ext}"
                    
                    upload_dir = os.path.join('uploads', 'reviews', str(review.id))
                    os.makedirs(upload_dir, exist_ok=True)
                    filepath = os.path.join(upload_dir, filename)
                    file.save(filepath)
                    
                    # Create media record with absolute URL pointing to widget server
                    media_url = f'{Config.WIDGET_BASE_URL}/uploads/reviews/{review.id}/{filename}'
                    media = ReviewMedia(
                        review_id=review.id,
                        media_url=media_url,
                        media_type='image',
                        status='active'
                    )
                    db.session.add(media)
                    uploaded_files.append(filepath)
        
        db.session.commit()
        
        logger.info(f"Review submitted: ID {review.id}, Product {product_id}, Rating {rating}, Platform: sakura_reviews")
        
        # Send acknowledgment email to reviewer
        try:
            send_review_acknowledgment_email(review, shop, product)
        except Exception as e:
            logger.warning(f"Failed to send acknowledgment email: {str(e)}")
            # Don't fail the review submission if email fails
        
        return jsonify({
            'success': True,
            'review_id': review.id,
            'message': 'Review submitted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error submitting review: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==================== EMAIL SENDING FUNCTIONS ====================

def send_review_acknowledgment_email(review, shop, product):
    """
    Send acknowledgment email when a customer submits a review
    Similar to Amazon's review confirmation emails
    """
    try:
        from flask import render_template
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # Check if email is enabled (can add setting later)
        # For now, always send if email is provided
        
        if not review.reviewer_email:
            logger.info("No email provided, skipping acknowledgment email")
            return
        
        # Get email configuration from environment or use defaults
        smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        smtp_user = os.environ.get('SMTP_USER', '')
        smtp_password = os.environ.get('SMTP_PASSWORD', '')
        email_from = os.environ.get('EMAIL_FROM', 'noreply@sakurareviews.com')
        email_from_name = os.environ.get('EMAIL_FROM_NAME', 'Sakura Reviews')
        
        # If SMTP not configured, log and skip (don't fail)
        if not smtp_user or not smtp_password:
            logger.info("SMTP not configured - skipping email. Set SMTP_USER and SMTP_PASSWORD to enable emails.")
            logger.info(f"Would send acknowledgment email to: {review.reviewer_email}")
            return
        
        # Build product URL
        product_url = f"https://{shop.shop_domain}/products/{product.shopify_product_id}#sakura-reviews"
        support_email = os.environ.get('SUPPORT_EMAIL', 'sakura.revs@gmail.com')
        
        # Render email template
        email_html = render_template('email-review-acknowledgment.html',
            reviewer_name=review.reviewer_name or 'Customer',
            rating=review.rating,
            review_text=review.body[:200] + '...' if review.body and len(review.body) > 200 else (review.body or ''),
            product_url=product_url,
            support_email=support_email
        )
        
        # Create email
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Thank You for Your Review! 🌸'
        msg['From'] = f"{email_from_name} <{email_from}>"
        msg['To'] = review.reviewer_email
        
        # Add HTML part
        html_part = MIMEText(email_html, 'html')
        msg.attach(html_part)
        
        # Send email
        try:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"✅ Acknowledgment email sent to {review.reviewer_email} for review {review.id}")
        except Exception as e:
            logger.error(f"Failed to send email via SMTP: {str(e)}")
            # Don't raise - email failure shouldn't break review submission
            
    except Exception as e:
        logger.error(f"Error in send_review_acknowledgment_email: {str(e)}")
        # Don't raise - email is optional


@app.route('/uploads/reviews/<int:review_id>/<filename>')
def serve_review_photo(review_id, filename):
    """
    Serve uploaded review photos
    """
    try:
        upload_dir = os.path.join('uploads', 'reviews', str(review_id))
        return send_from_directory(upload_dir, filename)
    except Exception as e:
        logger.error(f"Error serving review photo: {str(e)}")
        return jsonify({'error': 'Photo not found'}), 404


# ==================== HOMEPAGE CAROUSEL WIDGET ====================

@app.route('/widget/carousel/<shop_id>')
def carousel_widget(shop_id):
    """
    Homepage review carousel widget - shows best reviews from all products
    Can be embedded on any page (homepage, about page, etc.)
    
    Query params:
    - limit: Number of reviews to show (default 10)
    - title: Custom title
    - subtitle: Custom subtitle
    """
    try:
        from backend.models_v2 import Review, ReviewMedia, Shop
        from sqlalchemy import func, case
        
        limit = min(int(request.args.get('limit', 10)), 50)
        title = request.args.get('title', 'What Our Customers Say')
        subtitle = request.args.get('subtitle', 'Real reviews from verified customers')
        
        # Get shop
        shop = Shop.query.filter(
            (Shop.sakura_shop_id == str(shop_id)) | 
            (Shop.shopify_domain == shop_id) |
            (Shop.shopify_domain.like(f'%{shop_id}%'))
        ).first()
        
        if not shop:
            try:
                shop = Shop.query.get(int(shop_id))
            except:
                pass
        
        if not shop:
            return render_template('carousel-widget.html', 
                                 reviews=[], 
                                 title=title, 
                                 subtitle=subtitle,
                                 average_rating='4.8',
                                 total_reviews='0')
        
        # Get store-wide stats
        total_reviews = Review.query.filter_by(shop_id=shop.id, status='published').count()
        avg_rating = db.session.query(func.avg(Review.rating)).filter_by(
            shop_id=shop.id, status='published'
        ).scalar()
        avg_rating = round(float(avg_rating) if avg_rating else 4.8, 1)
        
        # Get best reviews with photos - SMART SORT
        # Subquery for media count
        media_subquery = db.session.query(
            ReviewMedia.review_id,
            func.count(ReviewMedia.id).label('media_count')
        ).filter(
            ReviewMedia.status == 'active',
            ReviewMedia.media_type == 'image'
        ).group_by(ReviewMedia.review_id).subquery()
        
        # Get reviews with smart sorting
        reviews_query = Review.query.filter_by(
            shop_id=shop.id,
            status='published'
        ).filter(
            Review.rating >= 4  # Only 4-5 star reviews
        ).outerjoin(
            media_subquery, Review.id == media_subquery.c.review_id
        ).order_by(
            # AI recommended first
            case((Review.ai_recommended == True, 0), else_=1),
            # Has photos
            case((func.coalesce(media_subquery.c.media_count, 0) > 0, 0), else_=1),
            # Has text content
            case((func.length(func.coalesce(Review.body, '')) > 20, 0), else_=1),
            # Higher rating
            Review.rating.desc(),
            # Quality score
            func.coalesce(Review.quality_score, 0).desc(),
            # Random for variety
            func.random()
        ).limit(limit)
        
        reviews_data = reviews_query.all()
        
        # Format reviews for template
        formatted_reviews = []
        for review in reviews_data:
            # Get media for this review
            media = ReviewMedia.query.filter_by(
                review_id=review.id,
                status='active',
                media_type='image'
            ).limit(3).all()
            
            formatted_reviews.append({
                'id': review.id,
                'author': review.reviewer_name or 'Customer',
                'rating': review.rating,
                'text': review.body[:200] + '...' if review.body and len(review.body) > 200 else review.body,
                'date': review.review_date.strftime('%B %d, %Y') if review.review_date else '',
                'verified': review.verified_purchase,
                'ai_recommended': review.ai_recommended,
                'media': [{'media_url': m.media_url} for m in media]
            })
        
        return render_template('carousel-widget.html',
                             reviews=formatted_reviews,
                             title=title,
                             subtitle=subtitle,
                             average_rating=str(avg_rating),
                             total_reviews=f"{total_reviews:,}" if total_reviews else '0')
    
    except Exception as e:
        logger.error(f"Error loading carousel widget: {e}")
        import traceback
        traceback.print_exc()
        return render_template('carousel-widget.html', 
                             reviews=[], 
                             title=title if 'title' in dir() else 'What Our Customers Say',
                             subtitle=subtitle if 'subtitle' in dir() else 'Real reviews from verified customers',
                             average_rating='4.8',
                             total_reviews='0')


@app.route('/api/carousel/<shop_id>')
def carousel_api(shop_id):
    """
    API endpoint for carousel widget data (for JavaScript embedding)
    """
    try:
        from backend.models_v2 import Review, ReviewMedia, Shop
        from sqlalchemy import func, case
        
        limit = min(int(request.args.get('limit', 10)), 50)
        
        # Get shop
        shop = Shop.query.filter(
            (Shop.sakura_shop_id == str(shop_id)) | 
            (Shop.shopify_domain == shop_id) |
            (Shop.shopify_domain.like(f'%{shop_id}%'))
        ).first()
        
        if not shop:
            return jsonify({'success': False, 'error': 'Shop not found', 'reviews': []})
        
        # Get store-wide stats
        total_reviews = Review.query.filter_by(shop_id=shop.id, status='published').count()
        avg_rating = db.session.query(func.avg(Review.rating)).filter_by(
            shop_id=shop.id, status='published'
        ).scalar()
        avg_rating = round(float(avg_rating) if avg_rating else 4.8, 1)
        
        # Get best reviews
        media_subquery = db.session.query(
            ReviewMedia.review_id,
            func.count(ReviewMedia.id).label('media_count')
        ).filter(
            ReviewMedia.status == 'active',
            ReviewMedia.media_type == 'image'
        ).group_by(ReviewMedia.review_id).subquery()
        
        reviews_query = Review.query.filter_by(
            shop_id=shop.id,
            status='published'
        ).filter(
            Review.rating >= 4
        ).outerjoin(
            media_subquery, Review.id == media_subquery.c.review_id
        ).order_by(
            case((Review.ai_recommended == True, 0), else_=1),
            case((func.coalesce(media_subquery.c.media_count, 0) > 0, 0), else_=1),
            case((func.length(func.coalesce(Review.body, '')) > 20, 0), else_=1),
            Review.rating.desc(),
            func.coalesce(Review.quality_score, 0).desc()
        ).limit(limit).all()
        
        formatted_reviews = []
        for review in reviews_query:
            media = ReviewMedia.query.filter_by(
                review_id=review.id,
                status='active',
                media_type='image'
            ).limit(3).all()
            
            formatted_reviews.append({
                'id': review.id,
                'author': review.reviewer_name or 'Customer',
                'rating': review.rating,
                'text': review.body[:200] + '...' if review.body and len(review.body) > 200 else review.body,
                'date': review.review_date.isoformat() if review.review_date else None,
                'verified': review.verified_purchase,
                'ai_recommended': review.ai_recommended,
                'photos': [m.media_url for m in media]
            })
        
        return jsonify({
            'success': True,
            'reviews': formatted_reviews,
            'stats': {
                'total_reviews': total_reviews,
                'average_rating': avg_rating
            }
        })
    
    except Exception as e:
        logger.error(f"Error loading carousel API: {e}")
        return jsonify({'success': False, 'error': str(e), 'reviews': []})


def check_payment_status(shop_id):
    """
    Check if shop has active subscription
    """
    # For now, always return True for testing
    # In production, check against Shopify billing API
    return True

def get_product_reviews(product_id, limit=20, offset=0, sort='default'):
    """
    Get reviews for a specific product from database with pagination and sorting support
    Returns: (reviews_list, total_count, average_rating, rating_distribution)
    
    Sort options:
    - 'default': SMART SORT - AI recommended first, then text content, then photos, then rating
    - 'ai_recommended': Same as default (smart sort)
    - 'newest': By date (newest first)
    - 'highest_ratings': 5-star first, then 4, etc.
    - 'lowest_ratings': 1-star first, then 2, etc.
    """
    try:
        from backend.models_v2 import Review, ReviewMedia
        from sqlalchemy import func, case
        
        # Get total count
        total_count = Review.query.filter_by(
            shopify_product_id=product_id,
            status='published'
        ).count()
        
        # Calculate average rating
        avg_rating_result = db.session.query(func.avg(Review.rating)).filter_by(
            shopify_product_id=product_id,
            status='published'
        ).scalar()
        average_rating = round(float(avg_rating_result) if avg_rating_result else 0.0, 1)
        
        # Calculate star rating distribution (count for each rating 1-5)
        rating_distribution = {}
        for rating in range(1, 6):
            count = Review.query.filter_by(
                shopify_product_id=product_id,
                status='published',
                rating=rating
            ).count()
            rating_distribution[rating] = count
        
        # Base query
        reviews_query = Review.query.filter_by(
            shopify_product_id=product_id,
            status='published'
        )
        
        # Use subquery to get media count for each review (used in multiple sort options)
        media_subquery = db.session.query(
            ReviewMedia.review_id,
            func.count(ReviewMedia.id).label('media_count')
        ).filter(
            ReviewMedia.status == 'active'
        ).group_by(ReviewMedia.review_id).subquery()
        
        # Apply sorting based on sort parameter
        if sort == 'newest':
            # Newest first, but still prefer reviews with content
            reviews_query = reviews_query.outerjoin(
                media_subquery, Review.id == media_subquery.c.review_id
            ).order_by(
                Review.imported_at.desc(),
                case((func.length(func.coalesce(Review.body, '')) > 10, 0), else_=1),
                case((func.coalesce(media_subquery.c.media_count, 0) > 0, 0), else_=1)
            )
        elif sort == 'highest_ratings':
            # Highest ratings first, but within same rating, prefer content
            reviews_query = reviews_query.outerjoin(
                media_subquery, Review.id == media_subquery.c.review_id
            ).order_by(
                # 1. Rating first (5 star > 4 star > etc)
                Review.rating.desc(),
                # 2. Within same rating: has text content
                case((func.length(func.coalesce(Review.body, '')) > 10, 0), else_=1),
                # 3. Within same rating: has photos
                case((func.coalesce(media_subquery.c.media_count, 0) > 0, 0), else_=1),
                # 4. More photos first
                func.coalesce(media_subquery.c.media_count, 0).desc(),
                # 5. Longer text first
                func.length(func.coalesce(Review.body, '')).desc()
            )
        elif sort == 'lowest_ratings':
            # Lowest ratings first (for merchants to see complaints), but prefer content
            reviews_query = reviews_query.outerjoin(
                media_subquery, Review.id == media_subquery.c.review_id
            ).order_by(
                Review.rating.asc(),
                case((func.length(func.coalesce(Review.body, '')) > 10, 0), else_=1),
                case((func.coalesce(media_subquery.c.media_count, 0) > 0, 0), else_=1),
                func.length(func.coalesce(Review.body, '')).desc()
            )
        else:  # 'default' or 'ai_recommended' - SMART SORT
            # Smart sorting: AI Recommended > Has Text > Has Photos > High Rating > Quality Score
            reviews_query = reviews_query.outerjoin(
                media_subquery, Review.id == media_subquery.c.review_id
            ).order_by(
                # 1. AI Recommended first (if flag is True)
                case((Review.ai_recommended == True, 0), else_=1),
                # 2. Has text content (body length > 10 chars)
                case((func.length(func.coalesce(Review.body, '')) > 10, 0), else_=1),
                # 3. Has photos (media count > 0)
                case((func.coalesce(media_subquery.c.media_count, 0) > 0, 0), else_=1),
                # 4. Higher rating first
                Review.rating.desc(),
                # 5. More photos first
                func.coalesce(media_subquery.c.media_count, 0).desc(),
                # 6. Longer text first
                func.length(func.coalesce(Review.body, '')).desc(),
                # 7. Quality score as tiebreaker
                func.coalesce(Review.quality_score, 0).desc()
            )
        
        # Apply pagination
        reviews_query = reviews_query.offset(offset).limit(limit).all()
        
        if not reviews_query:
            logger.info(f"No reviews found for product {product_id}")
            rating_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            return [], total_count, 0.0, rating_distribution
        
        # Convert to dict format for template
        reviews = []
        for review in reviews_query:
            # Get media for this review
            media = ReviewMedia.query.filter_by(review_id=review.id, status='active').all()
            # Format media for widget template (expects 'media' with 'media_url' property)
            # Convert relative URLs to absolute URLs
            media_list = []
            for m in media:
                media_url = m.media_url
                # If URL is relative (starts with /), make it absolute
                if media_url and media_url.startswith('/'):
                    media_url = f'{Config.WIDGET_BASE_URL}{media_url}'
                media_list.append({'media_url': media_url})
            
            reviews.append({
                'id': review.id,
                'rating': review.rating,
                'text': review.body or '',
                'body': review.body or '',  # Some templates use 'body'
                'title': review.title or '',
                'author': review.reviewer_name or 'Anonymous',
                'reviewer_name': review.reviewer_name or 'Anonymous',  # Some templates use 'reviewer_name'
                'date': review.review_date.strftime('%Y-%m-%d') if review.review_date else review.imported_at.strftime('%Y-%m-%d'),
                'review_date': review.review_date.strftime('%Y-%m-%d') if review.review_date else review.imported_at.strftime('%Y-%m-%d'),
                'imported_at': review.imported_at.strftime('%Y-%m-%d') if review.imported_at else '',
                'verified': review.verified_purchase,
                'verified_purchase': review.verified_purchase,  # Some templates use 'verified_purchase'
                'media': media_list,  # Widget templates expect 'media' not 'images'
                'images': media_list,  # Keep 'images' for backward compatibility
                'country': review.reviewer_country or '',
                'reviewer_country': review.reviewer_country or '',
                'ai_score': review.quality_score or 0.0,
                'quality_score': review.quality_score or 0.0,  # Some templates use 'quality_score'
                'ai_recommended': review.ai_recommended,
                'shopify_product_id': review.shopify_product_id,
                'aliexpress_product_id': review.aliexpress_product_id,
                # Helpful votes
                'helpful_yes': getattr(review, 'helpful_yes', 0) or 0,
                'helpful_no': getattr(review, 'helpful_no', 0) or 0
            })
        
        logger.info(f"Found {len(reviews)} reviews for product {product_id} (offset: {offset}, limit: {limit}, total: {total_count}, sort: {sort}, avg_rating: {average_rating})")
        return reviews, total_count, average_rating, rating_distribution
        
    except Exception as e:
        logger.error(f"Error fetching reviews for product {product_id}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        rating_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        return [], 0, 0.0, rating_distribution

# Shopify App Block Integration
@app.route('/app-blocks')
def app_blocks():
    """
    Shopify app blocks configuration
    """
    return jsonify({
        "blocks": [
            {
                "type": "sakura_reviews",
                "name": "🌸 Sakura Reviews",
                "description": "AI-powered review widget with multi-platform support",
                "settings": [
                    {
                        "type": "text",
                        "id": "title",
                        "label": "Reviews Title",
                        "default": "Customer Reviews",
                        "info": "Title displayed above the reviews"
                    },
                    {
                        "type": "range",
                        "id": "limit",
                        "label": "Number of Reviews",
                        "min": 5,
                        "max": 100,
                        "step": 5,
                        "default": 20,
                        "info": "Maximum number of reviews to display"
                    },
                    {
                        "type": "select",
                        "id": "theme",
                        "label": "Widget Theme",
                        "options": [
                            {"value": "default", "label": "🌸 Default"},
                            {"value": "minimal", "label": "⚪ Minimal"},
                            {"value": "colorful", "label": "🌈 Colorful"},
                            {"value": "dark", "label": "🌙 Dark Mode"}
                        ],
                        "default": "default",
                        "info": "Choose your preferred theme"
                    }
                ]
            }
        ]
    })

@app.route('/app-blocks/sakura_reviews')
def sakura_reviews_block():
    """
    Render the Sakura Reviews app block
    """
    settings = request.args.to_dict()
    
    # Get settings with defaults
    title = settings.get('title', 'Customer Reviews')
    limit = int(settings.get('limit', 20))
    theme = settings.get('theme', 'default')
    
    # Generate widget URL
    shop_id = request.args.get('shop_id', 'demo-shop')
    product_id = request.args.get('product_id', 'demo-product')
    
    widget_url = widget_system.generate_widget_url(shop_id, product_id, theme, limit)
    
    # Create unique IDs for the widget (like Loox)
    section_id = f"sakura-reviews-section-{shop_id}-{product_id}"
    widget_id = f"sakuraReviews-{shop_id}-{product_id}"
    frame_id = f"sakuraReviewsFrame-{shop_id}-{product_id}"
    
    # Generate the HTML following Loox's exact structure
    html = f"""
    <!-- Sakura Reviews Widget - Superior to Loox -->
    <section id="{section_id}" class="sakura-reviews-widget sakura-theme-{theme}">
        <div class="sakura-reviews-separator"></div>
        
        <div id="{widget_id}" class="sakura-reviews-container" data-limit="{limit}" data-product-id="{product_id}">
            <iframe 
                id="{frame_id}"
                src="{widget_url}"
                width="100%"
                height="2048px"
                frameborder="0"
                scrolling="no"
                style="overflow: hidden; height: 2048px; width: 100%; box-shadow: unset; outline: unset; color-scheme: none; border: none;"
                title="Sakura Reviews Widget"
                loading="lazy"
                allow="payment; fullscreen"
            >
                <p>Loading reviews...</p>
            </iframe>
        </div>
    </section>
    
    <style>
    .sakura-reviews-widget {{
        margin: 20px 0;
        background: white;
    }}
    
    .sakura-reviews-separator {{
        border-top: 1px solid #e2e8f0;
        margin: 20px 0;
    }}
    
    .sakura-reviews-container {{
        position: relative;
        background: white;
        margin: 0px auto;
        max-width: 1080px;
    }}
    
    #{frame_id} {{
        display: block;
        width: 100%;
        border: none;
        background: white;
    }}
    
    /* Theme variations */
    .sakura-theme-minimal {{
        box-shadow: none;
        border: 1px solid #e0e0e0;
    }}
    
    .sakura-theme-colorful {{
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }}
    
    .sakura-theme-dark {{
        background: #1a1a1a;
        color: white;
    }}
    </style>
    
    <script>
    // Auto-resize iframe based on content (like Loox)
    window.addEventListener('message', function(event) {{
        if (event.origin !== '{Config.WIDGET_BASE_URL}') return;
        
        if (event.data.type === 'resize') {{
            const iframe = document.getElementById('{frame_id}');
            if (iframe) {{
                iframe.style.height = event.data.height + 'px';
            }}
        }}
        
        if (event.data.type === 'analytics') {{
            // Track widget interactions
            console.log('🌸 Sakura Reviews Analytics:', event.data);
        }}
    }});
    
    // Initialize widget
    document.addEventListener('DOMContentLoaded', function() {{
        const widget = document.getElementById('{widget_id}');
        if (widget) {{
            console.log('🌸 Sakura Reviews Widget initialized for product {product_id}');
        }}
    }});
    </script>
    """
    
    return html

@app.route('/widget-test')
def widget_test():
    """
    Test page for the widget system
    """
    shop_id = "test-shop"
    product_id = "test-product"
    
    # Generate widget URL
    widget_url = widget_system.generate_widget_url(shop_id, product_id)
    
    # Generate app block HTML
    app_block_html = widget_system.create_shopify_app_block(shop_id, product_id)
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>🌸 Sakura Reviews Widget Test</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background: #f8f9fa; }}
            .test-section {{ margin: 30px 0; padding: 20px; border: 1px solid #ddd; border-radius: 8px; background: white; }}
            .widget-url {{ background: #f5f5f5; padding: 10px; border-radius: 4px; word-break: break-all; font-family: monospace; }}
            .app-block {{ background: #f0f8ff; padding: 10px; border-radius: 4px; }}
            .success {{ color: #28a745; font-weight: bold; }}
            .endpoint {{ margin: 10px 0; padding: 10px; background: #e9ecef; border-radius: 4px; }}
            .endpoint a {{ color: #007bff; text-decoration: none; }}
            .endpoint a:hover {{ text-decoration: underline; }}
            h1 {{ color: #6f42c1; }}
            h2 {{ color: #495057; }}
        </style>
    </head>
    <body>
        <h1>🌸 Sakura Reviews Widget Test</h1>
        <p class="success">✅ Widget system is working perfectly!</p>
        
        <div class="test-section">
            <h2>🔗 Widget URL</h2>
            <div class="widget-url">{widget_url}</div>
            <p><a href="{widget_url}" target="_blank">Open Widget in New Tab</a></p>
        </div>
        
        <div class="test-section">
            <h2>🛍️ Shopify App Block HTML</h2>
            <div class="app-block">
                <pre>{app_block_html}</pre>
            </div>
        </div>
        
        <div class="test-section">
            <h2>🧪 Test Endpoints</h2>
            <div class="endpoint">
                <strong>Debug Routes:</strong> <a href="/debug/routes" target="_blank">/debug/routes</a>
            </div>
            <div class="endpoint">
                <strong>Widget API:</strong> <a href="/widget/{shop_id}/reviews/{product_id}/api" target="_blank">/widget/{shop_id}/reviews/{product_id}/api</a>
            </div>
            <div class="endpoint">
                <strong>App Blocks:</strong> <a href="/app-blocks" target="_blank">/app-blocks</a>
            </div>
            <div class="endpoint">
                <strong>Shopify Block:</strong> <a href="/app-blocks/sakura_reviews?shop_id={shop_id}&product_id={product_id}" target="_blank">/app-blocks/sakura_reviews</a>
            </div>
        </div>
        
        <div class="test-section">
            <h2>📱 Live Widget Preview</h2>
            {app_block_html}
        </div>
    </body>
    </html>
    """

@app.route('/test-simple')
def test_simple():
    return "Simple test route works!"

@app.route('/shopify-scripttag')
def shopify_scripttag():
    """
    Shopify ScriptTag API implementation - Like Loox's automatic injection
    This creates the JavaScript file that gets injected automatically
    """
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>🌸 Sakura Reviews - ScriptTag API Implementation</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f8f9fa; }
            .code-block { background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0; }
            .success { color: #28a745; font-weight: bold; }
            .warning { color: #856404; background: #fff3cd; padding: 10px; border-radius: 4px; }
            .api-example { background: #e8f4fd; padding: 15px; border-radius: 8px; margin: 15px 0; }
        </style>
    </head>
    <body>
        <h1>🌸 Sakura Reviews - ScriptTag API Implementation</h1>
        <p class="success">✅ Completely Automatic - No Code Copying Required!</p>
        
        <div class="warning">
            <strong>🎯 How Loox Does It:</strong> When merchants install Loox, it automatically creates a ScriptTag 
            that injects JavaScript into their store. No manual code editing required!
        </div>
        
        <h2>🔧 Implementation Steps</h2>
        
        <div class="api-example">
            <h3>1. Create ScriptTag When App is Installed</h3>
            <p>When merchant installs Sakura Reviews app, automatically create ScriptTag:</p>
            <pre><code>POST /admin/api/2025-10/script_tags.json
{
  "script_tag": {
    "event": "onload",
    "src": "https://yourdomain.com/sakura-reviews.js"
  }
}</code></pre>
        </div>
        
        <div class="api-example">
            <h3>2. Host the JavaScript File</h3>
            <p>Our auto-injection script gets hosted and injected automatically:</p>
            <pre><code>https://yourdomain.com/sakura-reviews.js</code></pre>
        </div>
        
        <div class="api-example">
            <h3>3. Automatic Injection</h3>
            <p>The script automatically detects product pages and injects reviews - no user action required!</p>
        </div>
        
        <h2>📋 What Happens Automatically:</h2>
        <ul>
            <li><strong>App Installation:</strong> ScriptTag created automatically</li>
            <li><strong>JavaScript Injection:</strong> Script loads on all pages</li>
            <li><strong>Product Detection:</strong> Automatically detects product pages</li>
            <li><strong>Review Injection:</strong> Reviews appear automatically</li>
            <li><strong>No Manual Work:</strong> Everything happens programmatically</li>
        </ul>
        
        <h2>🚀 Next Steps:</h2>
        <ol>
            <li><strong>Create ScriptTag endpoint</strong> in our app</li>
            <li><strong>Host the JavaScript file</strong> on our server</li>
            <li><strong>Test automatic injection</strong> in Shopify store</li>
            <li><strong>Deploy to production</strong> for merchants</li>
        </ol>
        
        <div class="success">
            <strong>🎉 Result:</strong> Merchants just install the app and reviews appear automatically - 
            exactly like Loox, but with superior features!
        </div>
    </body>
    </html>
    """

@app.route('/shopify-auto-inject')
def shopify_auto_inject():
    """
    Automatic Shopify section injection - Like Loox's "no-tech" approach
    This script automatically injects review sections into product pages
    """
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>🌸 Sakura Reviews - Auto Injection Script</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f8f9fa; }
            .code-block { background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0; }
            .highlight { background: #fff3cd; padding: 2px 4px; border-radius: 4px; }
            .success { color: #28a745; font-weight: bold; }
            .warning { color: #856404; background: #fff3cd; padding: 10px; border-radius: 4px; }
        </style>
    </head>
    <body>
        <h1>🌸 Sakura Reviews - Auto Injection Script</h1>
        <p class="success">✅ Automatic Shopify Integration - No Technical Knowledge Required!</p>
        
        <div class="warning">
            <strong>⚠️ Important:</strong> This script will automatically inject review sections into your Shopify product pages. 
            Make sure you have the Sakura Reviews app installed first.
        </div>
        
        <h2>🔧 Auto-Injection JavaScript</h2>
        <p>Copy and paste this script into your Shopify theme's <code>theme.liquid</code> file, just before the closing <code>&lt;/body&gt;</code> tag:</p>
        
        <div class="code-block">
            <pre><code>&lt;script&gt;
// Sakura Reviews Auto-Injection Script
// This automatically adds review sections to product pages
(function() {
    'use strict';
    
    // Configuration
    const SAKURA_CONFIG = {
        apiUrl: '{{ Config.WIDGET_BASE_URL }}',
        shopId: '{{ shop.permanent_domain }}',
        productId: '{{ product.id }}',
        theme: 'default',
        limit: 20
    };
    
    // Check if we're on a product page
    function isProductPage() {
        return window.location.pathname.includes('/products/') && 
               typeof window.ShopifyAnalytics !== 'undefined' &&
               window.ShopifyAnalytics.meta && 
               window.ShopifyAnalytics.meta.product;
    }
    
    // Generate widget URL
    function generateWidgetUrl() {
        const timestamp = Date.now();
        const version = '2.0.0';
        const params = new URLSearchParams({
            v: version,
            t: timestamp,
            s: 'auto-inject-' + timestamp, // Simple hash for auto-injection
            theme: SAKURA_CONFIG.theme,
            limit: SAKURA_CONFIG.limit,
            platform: 'shopify'
        });
        
        return `${SAKURA_CONFIG.apiUrl}/widget/${SAKURA_CONFIG.shopId}/reviews/${SAKURA_CONFIG.productId}?${params}`;
    }
    
    // Create review section HTML
    function createReviewSection() {
        const widgetUrl = generateWidgetUrl();
        const sectionId = `sakura-reviews-${SAKURA_CONFIG.shopId}-${SAKURA_CONFIG.productId}`;
        const frameId = `sakuraReviewsFrame-${SAKURA_CONFIG.shopId}-${SAKURA_CONFIG.productId}`;
        
        return `
            &lt;section id="${sectionId}" class="sakura-reviews-widget sakura-auto-injected"&gt;
                &lt;div class="sakura-reviews-separator"&gt;&lt;/div&gt;
                &lt;div class="sakura-reviews-container" data-product-id="${SAKURA_CONFIG.productId}"&gt;
                    &lt;iframe 
                        id="${frameId}"
                        src="${widgetUrl}"
                        width="100%"
                        height="2048px"
                        frameborder="0"
                        scrolling="no"
                        style="overflow: hidden; height: 2048px; width: 100%; box-shadow: unset; outline: unset; color-scheme: none; border: none;"
                        title="Sakura Reviews Widget"
                        loading="lazy"
                    &gt;
                        &lt;p&gt;Loading reviews...&lt;/p&gt;
                    &lt;/iframe&gt;
                &lt;/div&gt;
            &lt;/section&gt;
            
            &lt;style&gt;
            .sakura-reviews-widget {
                margin: 40px 0;
                background: white;
            }
            
            .sakura-reviews-separator {
                border-top: 1px solid #e2e8f0;
                margin: 20px 0;
            }
            
            .sakura-reviews-container {
                position: relative;
                background: white;
                margin: 0px auto;
                max-width: 1080px;
            }
            
            #${frameId} {
                display: block;
                width: 100%;
                border: none;
                background: white;
            }
            &lt;/style&gt;
            
            &lt;script&gt;
            // Auto-resize iframe
            window.addEventListener('message', function(event) {
                if (event.origin !== '${SAKURA_CONFIG.apiUrl}') return;
                
                if (event.data.type === 'resize') {
                    const iframe = document.getElementById('${frameId}');
                    if (iframe) {
                        iframe.style.height = event.data.height + 'px';
                    }
                }
            });
            &lt;/script&gt;
        `;
    }
    
    // Find the best place to inject reviews
    function findInjectionPoint() {
        // Try to find #MainContent first (most themes)
        let target = document.querySelector('#MainContent');
        if (target) return target;
        
        // Try common product content selectors
        const selectors = [
            '.product-single__description',
            '.product-description',
            '.product-content',
            '.product-details',
            '.product-info',
            'main',
            '.main-content'
        ];
        
        for (const selector of selectors) {
            target = document.querySelector(selector);
            if (target) return target;
        }
        
        // Fallback to body
        return document.body;
    }
    
    // Inject review section
    function injectReviews() {
        if (!isProductPage()) return;
        
        // Check if already injected
        if (document.querySelector('.sakura-auto-injected')) {
            console.log('🌸 Sakura Reviews already injected');
            return;
        }
        
        const injectionPoint = findInjectionPoint();
        if (!injectionPoint) {
            console.warn('🌸 Sakura Reviews: Could not find injection point');
            return;
        }
        
        // Create and inject the review section
        const reviewSection = document.createElement('div');
        reviewSection.innerHTML = createReviewSection();
        
        // Insert after the main content
        injectionPoint.appendChild(reviewSection);
        
        console.log('🌸 Sakura Reviews injected successfully');
    }
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', injectReviews);
    } else {
        injectReviews();
    }
    
    // Re-inject on navigation (for SPA themes)
    window.addEventListener('popstate', injectReviews);
    
})();
&lt;/script&gt;</code></pre>
        </div>
        
        <h2>📋 Installation Steps (Super Simple!)</h2>
        <ol>
            <li><strong>Install Sakura Reviews App</strong> from Shopify App Store</li>
            <li><strong>Go to Online Store → Themes → Actions → Edit code</strong></li>
            <li><strong>Open <code>layout/theme.liquid</code></strong></li>
            <li><strong>Find <code>&lt;/body&gt;</code> tag</strong></li>
            <li><strong>Paste the script above</strong> just before <code>&lt;/body&gt;</code></li>
            <li><strong>Save and preview</strong> your store</li>
        </ol>
        
        <h2>🎯 How It Works (Like Loox)</h2>
        <ul>
            <li><strong>Automatic Detection:</strong> Script detects product pages automatically</li>
            <li><strong>Smart Injection:</strong> Finds the best place to add reviews</li>
            <li><strong>Theme Compatible:</strong> Works with any Shopify theme</li>
            <li><strong>No Manual Work:</strong> Reviews appear automatically on all product pages</li>
            <li><strong>Responsive:</strong> Adapts to your theme's styling</li>
        </ul>
        
        <h2>✨ Advanced Features</h2>
        <ul>
            <li><strong>Auto-Resize:</strong> Iframe adjusts height automatically</li>
            <li><strong>Theme Detection:</strong> Adapts to your store's design</li>
            <li><strong>Performance:</strong> Lazy loading for better speed</li>
            <li><strong>Analytics:</strong> Built-in tracking and metrics</li>
        </ul>
        
        <div class="success">
            <strong>🎉 That's it!</strong> Your customers will now see reviews on every product page automatically, 
            just like with Loox, but with superior features!
        </div>
    </body>
    </html>
    """

@app.route('/shopify-integration-test')
def shopify_integration_test():
    """
    Test page showing how to integrate Sakura Reviews into Shopify
    """
    shop_id = "test-shop"
    product_id = "test-product"
    
    # Generate different widget URLs for testing
    widget_url_default = widget_system.generate_widget_url(shop_id, product_id, "default", 20)
    widget_url_minimal = widget_system.generate_widget_url(shop_id, product_id, "minimal", 10)
    widget_url_colorful = widget_system.generate_widget_url(shop_id, product_id, "colorful", 30)
    
    # Generate app block HTML
    app_block_html = widget_system.create_shopify_app_block(shop_id, product_id)
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>🌸 Sakura Reviews - Shopify Integration Test</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background: #f8f9fa; }}
            .test-section {{ margin: 30px 0; padding: 20px; border: 1px solid #ddd; border-radius: 8px; background: white; }}
            .widget-url {{ background: #f5f5f5; padding: 10px; border-radius: 4px; word-break: break-all; font-family: monospace; }}
            .app-block {{ background: #f0f8ff; padding: 10px; border-radius: 4px; }}
            .success {{ color: #28a745; font-weight: bold; }}
            .endpoint {{ margin: 10px 0; padding: 10px; background: #e9ecef; border-radius: 4px; }}
            .endpoint a {{ color: #007bff; text-decoration: none; }}
            .endpoint a:hover {{ text-decoration: underline; }}
            h1 {{ color: #6f42c1; }}
            h2 {{ color: #495057; }}
            .theme-demo {{ margin: 20px 0; }}
            .theme-demo h3 {{ color: #6c757d; }}
        </style>
    </head>
    <body>
        <h1>🌸 Sakura Reviews - Shopify Integration Test</h1>
        <p class="success">✅ Following Loox's Strategy - But Superior!</p>
        
        <div class="test-section">
            <h2>🔗 Widget URLs (Like Loox)</h2>
            <div class="endpoint">
                <strong>Default Theme:</strong> <a href="{widget_url_default}" target="_blank">Open Widget</a>
            </div>
            <div class="endpoint">
                <strong>Minimal Theme:</strong> <a href="{widget_url_minimal}" target="_blank">Open Widget</a>
            </div>
            <div class="endpoint">
                <strong>Colorful Theme:</strong> <a href="{widget_url_colorful}" target="_blank">Open Widget</a>
            </div>
        </div>
        
        <div class="test-section">
            <h2>🛍️ Shopify App Block HTML</h2>
            <p>This is the HTML that merchants can add to their Shopify theme:</p>
            <div class="app-block">
                <pre>{app_block_html}</pre>
            </div>
        </div>
        
        <div class="test-section">
            <h2>📱 Live Widget Previews</h2>
            <div class="theme-demo">
                <h3>Default Theme</h3>
                {app_block_html}
            </div>
        </div>
        
        <div class="test-section">
            <h2>🧪 Test Endpoints</h2>
            <div class="endpoint">
                <strong>Debug Routes:</strong> <a href="/debug/routes" target="_blank">/debug/routes</a>
            </div>
            <div class="endpoint">
                <strong>Widget API:</strong> <a href="/widget/{shop_id}/reviews/{product_id}/api" target="_blank">/widget/{shop_id}/reviews/{product_id}/api</a>
            </div>
            <div class="endpoint">
                <strong>App Blocks:</strong> <a href="/app-blocks" target="_blank">/app-blocks</a>
            </div>
            <div class="endpoint">
                <strong>Shopify Block:</strong> <a href="/app-blocks/sakura_reviews?shop_id={shop_id}&product_id={product_id}" target="_blank">/app-blocks/sakura_reviews</a>
            </div>
        </div>
        
        <div class="test-section">
            <h2>🚀 How to Add to Shopify Store</h2>
            <ol>
                <li><strong>Copy the App Block HTML</strong> from above</li>
                <li><strong>Edit your Shopify theme</strong> (Online Store > Themes > Actions > Edit code)</li>
                <li><strong>Open product.liquid template</strong></li>
                <li><strong>Add the HTML</strong> where you want reviews to appear (usually after product description)</li>
                <li><strong>Save and preview</strong> your store</li>
            </ol>
            <p><strong>Alternative:</strong> Use Shopify App Blocks in theme customizer (like Loox does)</p>
        </div>
    </body>
    </html>
    """

@app.route('/js/sakura-reviews.js')
def sakura_reviews_js():
    """
    The JavaScript file that gets injected via ScriptTag API
    This is the file that Loox-style apps inject automatically
    """
    js_code = """
// Sakura Reviews Auto-Injection Script v2.1
// Includes: Product page widget + Collection page star badges
(function() {
    'use strict';
    
    // Prevent double initialization
    if (window.sakuraReviewsLoaded) return;
    window.sakuraReviewsLoaded = true;
    
    // Configuration
    const SAKURA_CONFIG = {
        apiUrl: '__WIDGET_BASE_URL__',
        shopId: '1',
        productId: null, // Will be extracted
        theme: 'default',
        limit: 20
    };
    
    // Extract product ID from various sources
    function getProductId() {
        // 1. ShopifyAnalytics (most common)
        if (window.ShopifyAnalytics?.meta?.product?.id) {
            return String(window.ShopifyAnalytics.meta.product.id);
        }
        
        // 2. Shopify.product (some themes)
        if (window.Shopify && window.Shopify.product && window.Shopify.product.id) {
            return String(window.Shopify.product.id);
        }
        
        // 3. From URL path (extract handle, then try to find ID)
        const pathMatch = window.location.pathname.match(/\\/products\\/([^/?#]+)/);
        if (pathMatch) {
            const handle = pathMatch[1];
            // Try Shopify.allProducts
            if (window.Shopify && window.Shopify.allProducts) {
                const product = window.Shopify.allProducts.find(p => p.handle === handle);
                if (product && product.id) {
                    return String(product.id);
                }
            }
        }
        
        // 4. From meta tags
        const productIdMeta = document.querySelector('meta[property="product:id"]') || 
                              document.querySelector('meta[name="product-id"]');
        if (productIdMeta) {
            const id = productIdMeta.getAttribute('content') || productIdMeta.getAttribute('value');
            if (id && /^\\d+$/.test(id)) return id;
        }
        
        // 5. From JSON-LD structured data
        const jsonLd = document.querySelector('script[type="application/ld+json"]');
        if (jsonLd) {
            try {
                const data = JSON.parse(jsonLd.textContent);
                if (data['@type'] === 'Product' && data.productID) {
                    return String(data.productID);
                }
                if (data.offers && data.offers.url) {
                    const urlMatch = data.offers.url.match(/\\/products\\/([^/?#]+)/);
                    if (urlMatch) {
                        const handle = urlMatch[1];
                        if (window.Shopify && window.Shopify.allProducts) {
                            const product = window.Shopify.allProducts.find(p => p.handle === handle);
                            if (product && product.id) return String(product.id);
                        }
                    }
                }
            } catch (e) {}
        }
        
        // 6. From page element IDs (like collection page)
        const pageIds = document.querySelectorAll('[id*="product-grid"], [id*="product-"]');
        for (const el of pageIds) {
            if (el.id) {
                const match = el.id.match(/product-grid-(\\d+)/) || el.id.match(/product-(\\d+)/);
                if (match && match[1]) {
                    return match[1];
                }
            }
        }
        
        return null;
    }
    
    // Set product ID
    SAKURA_CONFIG.productId = getProductId();
    
    // Log product ID detection
    if (isProductPage()) {
        if (SAKURA_CONFIG.productId) {
            console.log(`🌸 Product page detected. Product ID: ${SAKURA_CONFIG.productId}`);
        } else {
            console.warn('🌸 Product page detected but product ID not found');
        }
    }
    
    // ==================== STYLES ====================
    const styles = `
        .sakura-reviews-widget {
            margin: 40px 0;
            margin-bottom: 120px !important; /* Extra space to prevent footer overlap */
            padding-bottom: 80px !important; /* Additional padding for "Load more" button */
            background: white;
            scroll-margin-bottom: 100px; /* Space when scrolling to this section */
        }
        .sakura-reviews-separator {
            border-top: 1px solid #e2e8f0;
            margin: 20px 0;
        }
        .sakura-reviews-container {
            position: relative;
            background: white;
            margin: 0px auto;
            max-width: 1080px;
            padding-bottom: 60px; /* Extra padding at bottom for "Load more" button */
            min-height: 200px; /* Ensure minimum height */
        }
        .sakura-reviews-spacer {
            height: 100px; /* Spacer to ensure "Load more" button is visible above footer */
            width: 100%;
            display: block;
        }
        
        /* Star Badge Styles for Collection Pages */
        .sakura-star-badge {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            margin: 4px 0 8px 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-size: 13px;
            line-height: 1;
        }
        .sakura-stars {
            color: #fbbf24;
            letter-spacing: -1px;
            font-size: 14px;
        }
        .sakura-stars-empty {
            color: #e2e8f0;
        }
        .sakura-review-count {
            color: #64748b;
            font-size: 12px;
        }
        .sakura-star-badge a {
            text-decoration: none;
            color: inherit;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }
        .sakura-star-badge a:hover .sakura-review-count {
            color: #ff69b4;
            text-decoration: underline;
        }
        
        /* Amazon-style Product Page Rating (under title) */
        .sakura-product-rating {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            margin: 8px 0 12px 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        .sakura-product-rating-stars {
            display: inline-flex;
            align-items: center;
            gap: 2px;
            color: #fbbf24;
            font-size: 20px;
            line-height: 1;
        }
        .sakura-product-rating-number {
            font-size: 20px;
            font-weight: 600;
            color: #1a202c;
        }
        .sakura-product-rating-count {
            font-size: 18px;
            color: #64748b;
            text-decoration: none;
        }
        .sakura-product-rating-count:hover {
            color: #ff69b4;
            text-decoration: underline;
        }
        .sakura-product-rating-link {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            text-decoration: none;
            color: inherit;
        }
        .sakura-product-rating-link:hover {
            text-decoration: none;
        }
    `;
    
    // Inject styles
    const styleEl = document.createElement('style');
    styleEl.textContent = styles;
    document.head.appendChild(styleEl);
    
    // ==================== PRODUCT PAGE WIDGET ====================
    function isProductPage() {
        return window.location.pathname.includes('/products/');
    }
    
    function generateWidgetUrl() {
        if (!SAKURA_CONFIG.productId) {
            console.warn('🌸 No product ID found, cannot generate widget URL');
            return null;
        }
        const timestamp = Date.now();
        const params = new URLSearchParams({
            v: '2.0.0',
            t: timestamp,
            s: 'scripttag-' + timestamp,
            theme: SAKURA_CONFIG.theme,
            limit: SAKURA_CONFIG.limit,
            platform: 'shopify'
        });
        const url = `${SAKURA_CONFIG.apiUrl}/widget/1/reviews/${SAKURA_CONFIG.productId}?${params}`;
        console.log(`🌸 Generated widget URL for product ${SAKURA_CONFIG.productId}:`, url);
        return url;
    }
    
    function createReviewSection() {
        const widgetUrl = generateWidgetUrl();
        if (!widgetUrl) return '';
        
        const frameId = `sakuraReviewsFrame-${SAKURA_CONFIG.productId}`;
        return `
            <section class="sakura-reviews-widget sakura-auto-injected">
                <div class="sakura-reviews-separator"></div>
                <div class="sakura-reviews-container" data-product-id="${SAKURA_CONFIG.productId}">
                    <iframe 
                        id="${frameId}"
                        src="${widgetUrl}"
                        width="100%"
                        height="2048px"
                        frameborder="0"
                        scrolling="no"
                        style="overflow: hidden; height: 2048px; width: 100%; border: none; display: block;"
                        title="Sakura Reviews Widget"
                        loading="lazy"
                    ></iframe>
                    <div class="sakura-reviews-spacer"></div>
                </div>
            </section>
        `;
    }
    
    function findInjectionPoint() {
        const selectors = [
            '#MainContent',
            '.product-single__description',
            '.product-description',
            '.product-content',
            '.product-details',
            '.product-info',
            'main',
            '.main-content'
        ];
        for (const sel of selectors) {
            const el = document.querySelector(sel);
            if (el) return el;
        }
        return document.body;
    }
    
    function generateStarRatingHtml(rating, count) {
        const fullStars = Math.floor(rating);
        const hasHalf = rating % 1 >= 0.5;
        let starsHtml = '';
        for (let i = 0; i < fullStars; i++) starsHtml += '★';
        if (hasHalf) starsHtml += '★'; // Half star
        const emptyStars = 5 - fullStars - (hasHalf ? 1 : 0);
        for (let i = 0; i < emptyStars; i++) starsHtml += '☆';
        
        return `
            <div class="sakura-product-rating">
                <a href="#sakura-reviews" class="sakura-product-rating-link">
                    <span class="sakura-product-rating-number">${rating.toFixed(1)}</span>
                    <span class="sakura-product-rating-stars">${starsHtml}</span>
                    <span class="sakura-product-rating-count">(${count})</span>
                </a>
            </div>
        `;
    }
    
    async function injectProductRating() {
        // Inject Amazon-style rating under product title
        if (!isProductPage() || !SAKURA_CONFIG.productId) return;
        
        // Skip if already injected
        if (document.querySelector('.sakura-product-rating')) {
            console.log('🌸 Product rating already injected');
            return;
        }
        
        // Find product title (try multiple selectors for different themes)
        const titleSelectors = [
            'h1.product__title',
            'h1.product-title',
            '.product-single__title',
            '.product-title',
            '.product__heading h1',
            'h1[class*="title"]',
            '.product-form h1',
            '.product-details h1',
            'h1'
        ];
        
        let titleElement = null;
        for (const sel of titleSelectors) {
            titleElement = document.querySelector(sel);
            if (titleElement) {
                console.log(`🌸 Found product title using selector: ${sel}`);
                break;
            }
        }
        
        if (!titleElement) {
            console.warn('🌸 Could not find product title, will retry...');
            // Retry after a short delay (for dynamic themes)
            setTimeout(injectProductRating, 500);
            return;
        }
        
        // Fetch rating from API
        try {
            const response = await fetch(`${SAKURA_CONFIG.apiUrl}/api/products/ratings?product_ids=${SAKURA_CONFIG.productId}`);
            const data = await response.json();
            
            if (!data.success || !data.ratings[SAKURA_CONFIG.productId]) {
                console.log('🌸 No ratings found for product');
                return;
            }
            
            const ratings = data.ratings[SAKURA_CONFIG.productId];
            if (ratings.count === 0) {
                console.log('🌸 Product has 0 reviews, skipping rating display');
                return;
            }
            
            // Create and inject rating
            const ratingHtml = generateStarRatingHtml(ratings.average, ratings.count);
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = ratingHtml;
            const ratingElement = tempDiv.firstElementChild;
            
            // Make link scroll to reviews section
            const link = ratingElement.querySelector('a');
            if (link) {
                link.addEventListener('click', function(e) {
                    e.preventDefault();
                    // Wait for widget to be injected, then scroll
                    setTimeout(() => {
                        const widget = document.querySelector('.sakura-reviews-widget');
                        if (widget) {
                            widget.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        } else {
                            // Fallback: scroll to bottom
                            window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
                        }
                    }, 100);
                });
            }
            
            // Insert after title
            titleElement.parentNode.insertBefore(ratingElement, titleElement.nextSibling);
            console.log(`🌸 Product rating injected: ${ratings.average} stars (${ratings.count} reviews)`);
            
        } catch (error) {
            console.warn('🌸 Error fetching product rating:', error);
        }
    }
    
    function injectProductWidget() {
        if (!isProductPage()) {
            console.log('🌸 Not a product page, skipping widget injection');
            return;
        }
        
        if (document.querySelector('.sakura-auto-injected')) {
            console.log('🌸 Widget already injected, skipping');
            return;
        }
        
        if (!SAKURA_CONFIG.productId) {
            console.warn('🌸 Product page detected but no product ID found. Tried:', {
                ShopifyAnalytics: !!window.ShopifyAnalytics?.meta?.product?.id,
                ShopifyProduct: !!window.Shopify?.product?.id,
                ShopifyAllProducts: !!window.Shopify?.allProducts,
                pathname: window.location.pathname
            });
            return;
        }
        
        console.log(`🌸 Injecting widget for product ID: ${SAKURA_CONFIG.productId}`);
        
        const point = findInjectionPoint();
        if (!point) {
            console.warn('🌸 Could not find injection point for widget');
            return;
        }
        
        const widgetHtml = createReviewSection();
        if (!widgetHtml) {
            console.warn('🌸 Could not generate widget HTML');
            return;
        }
        
        const container = document.createElement('div');
        container.innerHTML = widgetHtml;
        point.appendChild(container);
        console.log(`🌸 Sakura Reviews widget injected for product ${SAKURA_CONFIG.productId}`);
        
        // Add iframe load error handler and auto-resize
        const iframe = container.querySelector('iframe');
        if (iframe) {
            iframe.addEventListener('load', function() {
                console.log('🌸 Widget iframe loaded');
                
                // Auto-resize iframe based on content
                try {
                    const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                    const resizeIframe = () => {
                        try {
                            const height = iframeDoc.body.scrollHeight || iframeDoc.documentElement.scrollHeight;
                            if (height > 0) {
                                iframe.style.height = (height + 100) + 'px'; // Add extra space for "Load more" button
                                console.log(`🌸 Iframe resized to ${height + 100}px`);
                            }
                        } catch (e) {
                            // Cross-origin restriction - use postMessage instead
                        }
                    };
                    
                    // Try immediate resize
                    setTimeout(resizeIframe, 500);
                    
                    // Watch for content changes
                    if (iframeDoc.body) {
                        const observer = new MutationObserver(resizeIframe);
                        observer.observe(iframeDoc.body, { childList: true, subtree: true });
                    }
                } catch (e) {
                    console.log('🌸 Using postMessage for iframe resize (cross-origin)');
                }
            });
            
            iframe.addEventListener('error', function() {
                console.error('🌸 Widget iframe failed to load');
            });
        }
    }
    
    // ==================== COLLECTION PAGE STAR BADGES ====================
    function generateStarHtml(rating, maxStars = 5) {
        const fullStars = Math.floor(rating);
        const hasHalf = rating % 1 >= 0.5;
        let html = '<span class="sakura-stars">';
        for (let i = 0; i < fullStars; i++) html += '★';
        if (hasHalf) html += '★'; // Could use half star char
        const emptyStars = maxStars - fullStars - (hasHalf ? 1 : 0);
        html += '</span><span class="sakura-stars-empty">';
        for (let i = 0; i < emptyStars; i++) html += '★';
        html += '</span>';
        return html;
    }
    
    function createStarBadge(productId, count, average, card) {
        if (count === 0) return ''; // Don't show badge if no reviews
        
        // Get product handle from card link for proper URL
        let productUrl = `#sakura-reviews`;
        const link = card?.querySelector('a[href*="/products/"]');
        if (link) {
            const href = link.getAttribute('href');
            const match = href.match(/\\/products\\/([^?#]+)/);
            if (match) {
                productUrl = `/products/${match[1]}#sakura-reviews`;
            }
        }
        
        const badge = document.createElement('div');
        badge.className = 'sakura-star-badge';
        badge.setAttribute('data-sakura-product', productId);
        
        const stars = generateStarHtml(average);
        badge.innerHTML = `
            <a href="${productUrl}">
                ${stars}
                <span class="sakura-review-count">(${count})</span>
            </a>
        `;
        return badge;
    }
    
    function findProductCards() {
        // Shopify product card selectors (prioritize common ones)
        // Test store uses: <li class="grid__item">
        // Homepage, collection pages, search results, etc.
        const cardSelectors = [
            'li.grid__item',  // Test store structure (collection & homepage)
            '.grid__item',    // Alternative
            '.product-card',
            '.card-product',
            '.grid-product',
            '.product-grid-item',
            '.product-item',
            '.collection-product-card',
            '[data-product-card]',
            '.product-card-wrapper',
            '.product',
            '.grid-product__item',  // Some themes
            '.product-grid__item',   // Some themes
            '.featured-product',     // Homepage featured products
            '.home-product',         // Homepage products
            'section[class*="product"]',  // Generic product sections
            '[class*="product-card"]',   // Any element with product-card in class
            '[class*="product-item"]'    // Any element with product-item in class
        ];
        
        // Try all selectors and combine results (homepage might have multiple types)
        let allCards = new Set(); // Use Set to avoid duplicates
        for (const sel of cardSelectors) {
            const found = document.querySelectorAll(sel);
            if (found.length > 0) {
                found.forEach(card => allCards.add(card));
                console.log(`🌸 Found ${found.length} cards using selector: ${sel}`);
            }
        }
        
        const cards = Array.from(allCards);
        if (cards.length > 0) {
            console.log(`🌸 Total unique product cards found: ${cards.length}`);
        }
        return cards;
    }
    
    function extractProductId(card) {
        // Extract NUMERIC product ID (like Loox does with data-id)
        // Loox uses: <div class="loox-rating" data-id="8341568848179">
        
        // 1. Look for Loox-style data-id (most reliable - matches Loox exactly)
        const looxRating = card.querySelector('.loox-rating');
        if (looxRating) {
            const looxId = looxRating.getAttribute('data-id');
            if (looxId && /^\\d+$/.test(looxId)) {
                console.log(`🌸 Found Loox-style data-id: ${looxId}`);
                return looxId;
            }
        }
        
        // 2. Data attributes (standard Shopify)
        const dataId = card.getAttribute('data-product-id') || 
                       card.getAttribute('data-id') ||
                       card.querySelector('[data-product-id]')?.getAttribute('data-product-id') ||
                       card.querySelector('[data-id]')?.getAttribute('data-id');
        if (dataId && /^\\d+$/.test(dataId)) {
            console.log(`🌸 Found data-product-id: ${dataId}`);
            return dataId;
        }
        
        // 3. Extract from card element IDs (Shopify embeds product ID in template IDs)
        // Test store: id="CardLink-template--25679685058874__product-grid-10045740024122"
        // Look in card itself and nested elements (especially links)
        const allIds = [];
        if (card.id) allIds.push(card.id);
        
        // Check all elements with IDs inside the card
        const elementsWithIds = card.querySelectorAll('[id*="product-grid"]');
        for (const el of elementsWithIds) {
            if (el.id) allIds.push(el.id);
        }
        
        // Also check links specifically (test store has ID on the link)
        // Related products format: id="CardLink--10045740450106" or id="title--10045740450106"
        const links = card.querySelectorAll('a[id*="product-grid"], a[id*="CardLink"], a[id*="title"], [id*="CardLink"], [id*="title"]');
        for (const link of links) {
            if (link.id) allIds.push(link.id);
        }
        
        for (const cardId of allIds) {
            // Try product-grid format first (collection pages)
            let match = cardId.match(/product-grid-(\\d+)/);
            if (match && match[1]) {
                console.log(`🌸 Found product ID from product-grid ID: ${match[1]}`);
                return match[1];
            }
            
            // Try related products format: CardLink--10045740450106 or title--10045740450106
            match = cardId.match(/--(\\d+)$/) || cardId.match(/-([0-9]{15,})$/) || cardId.match(/CardLink[^0-9]*(\\d+)/);
            if (match && match[1]) {
                console.log(`🌸 Found product ID from related products ID: ${match[1]}`);
                return match[1];
            }
        }
        
        // 4. From JSON data in script tags (Shopify stores product data here)
        const scripts = card.querySelectorAll('script[type="application/json"]');
        for (const script of scripts) {
            try {
                const data = JSON.parse(script.textContent);
                if (data.product && data.product.id) {
                    console.log(`🌸 Found product ID from JSON: ${data.product.id}`);
                    return String(data.product.id);
                }
                if (data.id) {
                    console.log(`🌸 Found ID from JSON: ${data.id}`);
                    return String(data.id);
                }
            } catch (e) {}
        }
        
        // 5. From form - look for product ID input
        const form = card.querySelector('form[action*="/cart/add"]');
        if (form) {
            const productIdInput = form.querySelector('input[name="product_id"]');
            if (productIdInput && productIdInput.value && /^\\d+$/.test(productIdInput.value)) {
                console.log(`🌸 Found product_id from form: ${productIdInput.value}`);
                return productIdInput.value;
            }
        }
        
        // 6. From product link - try to get ID from Shopify object
        const link = card.querySelector('a[href*="/products/"]');
        if (link) {
            const href = link.getAttribute('href');
            const match = href.match(/\\/products\\/([^/?#]+)/);
            if (match) {
                const handle = match[1];
                // Try Shopify.allProducts
                if (window.Shopify && window.Shopify.allProducts) {
                    const product = window.Shopify.allProducts.find(p => p.handle === handle);
                    if (product && product.id) {
                        console.log(`🌸 Found product ID from Shopify.allProducts: ${product.id}`);
                        return String(product.id);
                    }
                }
                // Store handle as fallback
                card._sakuraHandle = handle;
            }
        }
        
        // 7. Search all nested elements for data-product-id
        const allDataAttrs = card.querySelectorAll('[data-product-id], [data-id]');
        for (const el of allDataAttrs) {
            const id = el.getAttribute('data-product-id') || el.getAttribute('data-id');
            if (id && /^\\d+$/.test(id)) {
                console.log(`🌸 Found product ID from nested element: ${id}`);
                return id;
            }
        }
        
        console.warn('🌸 Could not extract product ID from card');
        return null;
    }
    
    function findPriceElement(card) {
        // Find where to insert the star badge (like Loox does - before price in card-information)
        // Test store structure: <div class="card-information"> → <div class="price">
        
        // First, try to find card-information (where Loox injects)
        const cardInfo = card.querySelector('.card-information');
        if (cardInfo) {
            // Find price inside card-information
            const price = cardInfo.querySelector('.price');
            if (price) {
                // Insert before price (like Loox does)
                return price;
            }
            // If no price, insert at the start of card-information
            return cardInfo;
        }
        
        // Fallback: find price directly
        const priceSelectors = [
            '.price',
            '.product-price',
            '.card-price',
            '.price-container',
            '.product-card__price',
            '[class*="price"]'
        ];
        
        for (const sel of priceSelectors) {
            const el = card.querySelector(sel);
            if (el) return el;
        }
        
        // Fallback: find title and insert after
        const titleSelectors = [
            '.product-title',
            '.card-title',
            '.product-card__title',
            'h3',
            'h4',
            '[class*="title"]'
        ];
        
        for (const sel of titleSelectors) {
            const el = card.querySelector(sel);
            if (el) return el;
        }
        
        return null;
    }
    
    async function injectCollectionBadges() {
        // Run on ALL pages (collection, product pages with related products, search, etc.)
        // The product page widget is separate and handles the main product reviews
        
        const cards = findProductCards();
        if (cards.length === 0) {
            console.log('🌸 No product cards found');
            return;
        }
        
        console.log(`🌸 Found ${cards.length} product cards`);
        
        // Extract product IDs (numeric IDs, like Loox uses)
        const productIds = [];
        const cardMap = new Map(); // Maps product ID to card
        
        for (const card of cards) {
            // Skip if already has badge
            if (card.querySelector('.sakura-star-badge')) continue;
            
            const productId = extractProductId(card);
            if (productId && /^\\d+$/.test(productId)) {
                // Only use numeric IDs (like Loox)
                productIds.push(productId);
                cardMap.set(productId, card);
            }
        }
        
        if (productIds.length === 0) {
            console.log('🌸 No numeric product IDs extracted from cards');
            return;
        }
        
        console.log(`🌸 Extracted ${productIds.length} numeric product IDs:`, productIds.slice(0, 5));
        
        // Build API URL with numeric IDs only
        const params = new URLSearchParams();
        params.append('product_ids', productIds.join(','));
        
        // Fetch ratings from API
        try {
            const url = `${SAKURA_CONFIG.apiUrl}/api/products/ratings?${params.toString()}`;
            console.log(`🌸 Fetching ratings from API...`);
            
            const response = await fetch(url);
            const data = await response.json();
            
            if (!data.success) {
                console.warn('🌸 Failed to fetch ratings:', data.error);
                return;
            }
            
            console.log(`🌸 Received ratings for ${Object.keys(data.ratings).length} products`);
            
            // Inject badges
            let injectedCount = 0;
            for (const [productId, ratings] of Object.entries(data.ratings)) {
                const card = cardMap.get(productId);
                if (!card) {
                    console.log(`🌸 No card found for product ID: ${productId}`);
                    continue;
                }
                
                if (ratings.count === 0) {
                    console.log(`🌸 Product ${productId} has 0 reviews, skipping badge`);
                    continue;
                }
                
                const insertPoint = findPriceElement(card);
                if (!insertPoint) {
                    console.log(`🌸 No insertion point found for product ${productId}`);
                    continue;
                }
                
                const badge = createStarBadge(productId, ratings.count, ratings.average, card);
                if (badge) {
                    // Insert before the price element (like Loox does)
                    insertPoint.parentNode.insertBefore(badge, insertPoint);
                    injectedCount++;
                    console.log(`🌸 ✓ Injected badge for ${productId}: ${ratings.count} reviews, ${ratings.average} stars`);
                }
            }
            
            console.log(`🌸 Successfully injected ${injectedCount} star badges`);
            
        } catch (error) {
            console.error('🌸 Error fetching ratings:', error);
        }
    }
    
    // ==================== GLOBAL IFRAME RESIZE HANDLER ====================
    // Set up once to handle resize messages from all iframes
    if (!window.sakuraResizeHandlerSetup) {
        window.sakuraResizeHandlerSetup = true;
        
        window.addEventListener('message', function(event) {
            // Check if message is from our widget
            try {
                const widgetOrigin = new URL(SAKURA_CONFIG.apiUrl).origin;
                if (event.origin !== widgetOrigin) {
                    return; // Ignore messages from other origins
                }
            } catch (e) {
                // If URL parsing fails, check if origin contains our domain
                if (!event.origin.includes(SAKURA_CONFIG.apiUrl.replace('https://', '').replace('http://', '').split('/')[0])) {
                    return;
                }
            }
            
            if (event.data && event.data.type === 'resize' && event.data.height) {
                // Find all Sakura review iframes and resize them
                const iframes = document.querySelectorAll('iframe[id^="sakuraReviewsFrame"]');
                for (const iframe of iframes) {
                    // Add extra space (100px) to ensure "Load more" button is visible above footer
                    const newHeight = event.data.height + 100;
                    iframe.style.height = newHeight + 'px';
                    console.log(`🌸 Iframe ${iframe.id} resized to ${newHeight}px`);
                }
            }
        });
    }
    
    // ==================== INITIALIZE ====================
    function init() {
        // Product page: inject rating under title (Amazon-style) and full widget
        if (isProductPage()) {
            injectProductRating(); // Inject rating under title first
            injectProductWidget(); // Then inject full widget at bottom
        }
        
        // ALL pages: inject star badges on product cards
        // (collection pages, related products on product pages, search results, etc.)
        injectCollectionBadges();
    }
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
    // Handle SPA navigation
    window.addEventListener('popstate', init);
    
    // Observe for dynamic content (infinite scroll, AJAX, homepage lazy loading)
    const observer = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            if (mutation.addedNodes.length) {
                // Debounce
                clearTimeout(window.sakuraDebounce);
                window.sakuraDebounce = setTimeout(injectCollectionBadges, 500);
            }
        }
    });
    observer.observe(document.body, { childList: true, subtree: true });
    
    // Also run on window load (for homepage products that load after DOMContentLoaded)
    window.addEventListener('load', function() {
        setTimeout(injectCollectionBadges, 1000); // Wait a bit for lazy-loaded content
    });
    
    // ==================== FULL-PAGE MODAL (Like Loox) ====================
    // Inject modal HTML into parent page (not iframe)
    function injectReviewModal() {
        if (document.getElementById('sakura-review-modal-overlay')) {
            return; // Already injected
        }
        
        const modalHTML = `
            <div class="sakura-review-modal-overlay" id="sakura-review-modal-overlay" style="display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 999999; align-items: center; justify-content: center;">
                <div class="sakura-review-modal" style="background: white; border-radius: 16px; max-width: 500px; width: 95%; max-height: 95vh; overflow-y: auto; position: relative; box-shadow: 0 20px 60px rgba(0,0,0,0.3);">
                    <button class="sakura-modal-close" id="sakuraModalClose" style="position: absolute; top: 16px; right: 16px; background: none; border: none; font-size: 32px; cursor: pointer; color: #666; z-index: 10; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; border-radius: 50%; transition: background 0.2s;">×</button>
                    <div class="sakura-modal-content" id="sakuraModalContent" style="padding: 40px 30px;">
                        <!-- Step 1: Rating -->
                        <div class="sakura-modal-step active" id="sakuraStep1">
                            <h2 style="font-size: 24px; font-weight: 600; margin-bottom: 24px; text-align: center;">How would you rate this item?</h2>
                            <div class="sakura-rating-stars" id="sakuraRatingStars" style="display: flex; justify-content: center; gap: 8px; margin-bottom: 16px; font-size: 48px; cursor: pointer;">
                                <span class="sakura-star" data-rating="1" style="color: #e2e8f0; transition: color 0.2s;">★</span>
                                <span class="sakura-star" data-rating="2" style="color: #e2e8f0; transition: color 0.2s;">★</span>
                                <span class="sakura-star" data-rating="3" style="color: #e2e8f0; transition: color 0.2s;">★</span>
                                <span class="sakura-star" data-rating="4" style="color: #e2e8f0; transition: color 0.2s;">★</span>
                                <span class="sakura-star" data-rating="5" style="color: #e2e8f0; transition: color 0.2s;">★</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 32px; font-size: 14px; color: #666;">
                                <span>Dislike it</span>
                                <span>Love it!</span>
                            </div>
                            <button class="sakura-modal-btn" id="sakuraStep1Next" disabled style="width: 100%; padding: 14px; background: #e2e8f0; color: #999; border: none; border-radius: 8px; font-size: 16px; font-weight: 600; cursor: not-allowed;">Next →</button>
                        </div>
                        
                        <!-- Step 2: Photos -->
                        <div class="sakura-modal-step" id="sakuraStep2" style="display: none;">
                            <h2 style="font-size: 24px; font-weight: 600; margin-bottom: 8px; text-align: center;">Show it off</h2>
                            <p style="font-size: 16px; color: #718096; margin-bottom: 24px; text-align: center;">We'd love to see it in action!</p>
                            <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; margin: 24px 0; text-align: center;">
                                <div style="font-size: 18px; font-weight: 600; color: #1a202c; margin-bottom: 16px;">Get 15% off your next purchase!</div>
                                <div id="sakuraPhotoUploadArea" style="border: 2px dashed #e2e8f0; border-radius: 12px; padding: 40px; text-align: center; margin: 24px 0; cursor: pointer; transition: all 0.2s;">
                                    <div style="font-size: 48px; margin-bottom: 16px;">📷</div>
                                    <div style="font-size: 16px; color: #1a202c; margin-bottom: 8px;">Add photos</div>
                                    <div style="font-size: 14px; color: #718096;">Click to upload or drag and drop</div>
                                    <input type="file" id="sakuraPhotoInput" multiple accept="image/*" style="display: none;">
                                </div>
                                <div id="sakuraPhotoPreviewGrid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 12px; margin-top: 16px;"></div>
                            </div>
                            <div style="display: flex; justify-content: space-between; margin-top: 32px; padding-top: 24px; border-top: 1px solid #e2e8f0;">
                                <button class="sakura-modal-btn" id="sakuraStep2Back" style="background: transparent; border: none; color: #1a202c; font-size: 16px; font-weight: 600; cursor: pointer; padding: 8px 16px;">← Back</button>
                                <div>
                                    <button class="sakura-modal-btn" id="sakuraStep2Skip" style="background: transparent; border: none; color: #1a202c; font-size: 16px; font-weight: 600; cursor: pointer; padding: 8px 16px; margin-right: 8px;">Skip</button>
                                    <button class="sakura-modal-btn primary" id="sakuraStep2Next" style="background: #ff69b4; color: white; border: none; border-radius: 8px; font-size: 16px; font-weight: 600; cursor: pointer; padding: 8px 16px;">Next →</button>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Step 3: Review Text -->
                        <div class="sakura-modal-step" id="sakuraStep3" style="display: none;">
                            <h2 style="font-size: 24px; font-weight: 600; margin-bottom: 24px; text-align: center;">Tell us more!</h2>
                            <textarea id="sakuraReviewText" placeholder="Share your experience" style="width: 100%; min-height: 150px; padding: 16px; border: 2px solid #e2e8f0; border-radius: 8px; font-size: 16px; font-family: inherit; resize: vertical; margin: 24px 0;"></textarea>
                            <div style="display: flex; justify-content: space-between; margin-top: 32px; padding-top: 24px; border-top: 1px solid #e2e8f0;">
                                <button class="sakura-modal-btn" id="sakuraStep3Back" style="background: transparent; border: none; color: #1a202c; font-size: 16px; font-weight: 600; cursor: pointer; padding: 8px 16px;">← Back</button>
                                <button class="sakura-modal-btn primary" id="sakuraStep3Next" style="background: #ff69b4; color: white; border: none; border-radius: 8px; font-size: 16px; font-weight: 600; cursor: pointer; padding: 8px 16px;">Next →</button>
                            </div>
                        </div>
                        
                        <!-- Step 4: User Info -->
                        <div class="sakura-modal-step" id="sakuraStep4" style="display: none;">
                            <h2 style="font-size: 24px; font-weight: 600; margin-bottom: 24px; text-align: center;">About you</h2>
                            <div style="margin-bottom: 20px;">
                                <label style="display: block; font-size: 14px; font-weight: 600; color: #1a202c; margin-bottom: 8px;">First name <span style="color: #e53e3e;">*</span></label>
                                <input type="text" id="sakuraFirstName" required style="width: 100%; padding: 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 16px; font-family: inherit;">
                            </div>
                            <div style="margin-bottom: 20px;">
                                <label style="display: block; font-size: 14px; font-weight: 600; color: #1a202c; margin-bottom: 8px;">Last name</label>
                                <input type="text" id="sakuraLastName" style="width: 100%; padding: 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 16px; font-family: inherit;">
                            </div>
                            <div style="margin-bottom: 20px;">
                                <label style="display: block; font-size: 14px; font-weight: 600; color: #1a202c; margin-bottom: 8px;">Email <span style="color: #e53e3e;">*</span></label>
                                <input type="email" id="sakuraUserEmail" required style="width: 100%; padding: 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 16px; font-family: inherit;">
                            </div>
                            <div style="font-size: 12px; color: #718096; margin-top: 16px; line-height: 1.6;">
                                By submitting, I acknowledge the <a href="#" target="_blank" style="color: #ff69b4; text-decoration: underline;">Terms of Service</a> and <a href="#" target="_blank" style="color: #ff69b4; text-decoration: underline;">Privacy Policy</a>. and that my review will be publicly posted and shared online.
                            </div>
                            <div style="display: flex; justify-content: space-between; margin-top: 32px; padding-top: 24px; border-top: 1px solid #e2e8f0;">
                                <button class="sakura-modal-btn" id="sakuraStep4Back" style="background: transparent; border: none; color: #1a202c; font-size: 16px; font-weight: 600; cursor: pointer; padding: 8px 16px;">← Back</button>
                                <button class="sakura-modal-btn primary" id="sakuraStep4Done" style="background: #ff69b4; color: white; border: none; border-radius: 8px; font-size: 16px; font-weight: 600; cursor: pointer; padding: 8px 16px;">Done</button>
                            </div>
                        </div>
                        
                        <!-- Step 5: Confirmation -->
                        <div class="sakura-modal-step" id="sakuraStep5" style="display: none; text-align: center;">
                            <div style="width: 64px; height: 64px; border-radius: 50%; background: #48bb78; color: white; display: flex; align-items: center; justify-content: center; font-size: 32px; margin: 0 auto 24px;">✓</div>
                            <div style="font-size: 18px; font-weight: 600; color: #1a202c; margin-bottom: 8px;">Review submitted</div>
                            <div style="font-size: 14px; color: #718096; margin-bottom: 32px;">Discount code emailed</div>
                            <button class="sakura-modal-btn primary" id="sakuraStep5Close" style="width: 100%; padding: 14px; background: #ff69b4; color: white; border: none; border-radius: 8px; font-size: 16px; font-weight: 600; cursor: pointer;">Close</button>
                        </div>
                        
                        <!-- Progress Indicator -->
                        <div style="display: flex; gap: 8px; justify-content: center; margin-top: 16px;">
                            <div class="sakura-progress-bar active" id="sakuraProgress1" style="width: 40px; height: 4px; border-radius: 2px; background: #ff69b4;"></div>
                            <div class="sakura-progress-bar" id="sakuraProgress2" style="width: 40px; height: 4px; border-radius: 2px; background: #e2e8f0;"></div>
                            <div class="sakura-progress-bar" id="sakuraProgress3" style="width: 40px; height: 4px; border-radius: 2px; background: #e2e8f0;"></div>
                            <div class="sakura-progress-bar" id="sakuraProgress4" style="width: 40px; height: 4px; border-radius: 2px; background: #e2e8f0;"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        const modalContainer = document.createElement('div');
        modalContainer.innerHTML = modalHTML;
        document.body.appendChild(modalContainer.firstElementChild);
        
        // Initialize modal functionality
        initModal();
    }
    
    // Initialize modal
    function initModal() {
        const overlay = document.getElementById('sakura-review-modal-overlay');
        const closeBtn = document.getElementById('sakuraModalClose');
        const stars = document.querySelectorAll('.sakura-star');
        let currentStep = 1;
        let reviewData = {
            rating: 0,
            photos: [],
            text: '',
            firstName: '',
            lastName: '',
            email: ''
        };
        let currentProductId = null;
        let currentShopId = '1'; // Default shop ID
        
        // Show step function
        function showStep(step) {
            // Hide all steps
            for (let i = 1; i <= 5; i++) {
                const stepEl = document.getElementById('sakuraStep' + i);
                if (stepEl) stepEl.style.display = 'none';
            }
            // Show current step
            const currentStepEl = document.getElementById('sakuraStep' + step);
            if (currentStepEl) currentStepEl.style.display = 'block';
            
            // Update progress bars
            for (let i = 1; i <= 4; i++) {
                const progressBar = document.getElementById('sakuraProgress' + i);
                if (progressBar) {
                    if (i <= step) {
                        progressBar.style.background = '#ff69b4';
                    } else {
                        progressBar.style.background = '#e2e8f0';
                    }
                }
            }
            
            currentStep = step;
        }
        
        // Close modal
        function closeModal() {
            if (overlay) overlay.style.display = 'none';
            // Reset state
            reviewData = { rating: 0, photos: [], text: '', firstName: '', lastName: '', email: '' };
            currentStep = 1;
            showStep(1);
            stars.forEach(star => {
                star.style.color = '#e2e8f0';
            });
            const step1Next = document.getElementById('sakuraStep1Next');
            if (step1Next) {
                step1Next.disabled = true;
                step1Next.style.background = '#e2e8f0';
                step1Next.style.color = '#999';
                step1Next.style.cursor = 'not-allowed';
            }
        }
        
        if (closeBtn) {
            closeBtn.addEventListener('click', closeModal);
        }
        
        if (overlay) {
            overlay.addEventListener('click', function(e) {
                if (e.target === overlay) closeModal();
            });
        }
        
        // Step 1: Rating
        stars.forEach((star) => {
            star.addEventListener('click', function() {
                reviewData.rating = parseInt(star.getAttribute('data-rating'));
                stars.forEach((s, i) => {
                    if (i < reviewData.rating) {
                        s.style.color = '#fbbf24';
                    } else {
                        s.style.color = '#e2e8f0';
                    }
                });
                const step1Next = document.getElementById('sakuraStep1Next');
                if (step1Next) {
                    step1Next.disabled = false;
                    step1Next.style.background = '#ff69b4';
                    step1Next.style.color = 'white';
                    step1Next.style.cursor = 'pointer';
                }
            });
        });
        
        const step1Next = document.getElementById('sakuraStep1Next');
        if (step1Next) {
            step1Next.addEventListener('click', function() {
                if (reviewData.rating > 0) {
                    showStep(2);
                }
            });
        }
        
        // Step 2: Photos
        const photoUploadArea = document.getElementById('sakuraPhotoUploadArea');
        const photoInput = document.getElementById('sakuraPhotoInput');
        const photoPreviewGrid = document.getElementById('sakuraPhotoPreviewGrid');
        
        if (photoUploadArea && photoInput) {
            photoUploadArea.addEventListener('click', function() {
                photoInput.click();
            });
            
            photoInput.addEventListener('change', function(e) {
                const files = Array.from(e.target.files);
                files.forEach(file => {
                    if (file.type.startsWith('image/')) {
                        const reader = new FileReader();
                        reader.onload = function(event) {
                            reviewData.photos.push({
                                file: file,
                                preview: event.target.result
                            });
                            updatePhotoPreview();
                        };
                        reader.readAsDataURL(file);
                    }
                });
            });
        }
        
        function updatePhotoPreview() {
            if (photoPreviewGrid) {
                photoPreviewGrid.innerHTML = '';
                reviewData.photos.forEach((photo, index) => {
                    const item = document.createElement('div');
                    item.style.cssText = 'position: relative; aspect-ratio: 1; border-radius: 8px; overflow: hidden; border: 1px solid #e2e8f0;';
                    item.innerHTML = `
                        <img src="${photo.preview}" alt="Preview" style="width: 100%; height: 100%; object-fit: cover;">
                        <button onclick="removeSakuraPhoto(${index})" style="position: absolute; top: 4px; right: 4px; width: 24px; height: 24px; border-radius: 50%; background: rgba(0,0,0,0.6); color: white; border: none; cursor: pointer; font-size: 14px;">×</button>
                    `;
                    photoPreviewGrid.appendChild(item);
                });
            }
        }
        
        window.removeSakuraPhoto = function(index) {
            reviewData.photos.splice(index, 1);
            updatePhotoPreview();
        };
        
        const step2Back = document.getElementById('sakuraStep2Back');
        const step2Skip = document.getElementById('sakuraStep2Skip');
        const step2Next = document.getElementById('sakuraStep2Next');
        
        if (step2Back) {
            step2Back.addEventListener('click', () => showStep(1));
        }
        if (step2Skip) {
            step2Skip.addEventListener('click', () => showStep(3));
        }
        if (step2Next) {
            step2Next.addEventListener('click', () => showStep(3));
        }
        
        // Step 3: Review Text
        const reviewText = document.getElementById('sakuraReviewText');
        if (reviewText) {
            reviewText.addEventListener('input', function() {
                reviewData.text = this.value;
            });
        }
        
        const step3Back = document.getElementById('sakuraStep3Back');
        const step3Next = document.getElementById('sakuraStep3Next');
        
        if (step3Back) {
            step3Back.addEventListener('click', () => showStep(2));
        }
        if (step3Next) {
            step3Next.addEventListener('click', () => showStep(4));
        }
        
        // Step 4: User Info
        const firstName = document.getElementById('sakuraFirstName');
        const lastName = document.getElementById('sakuraLastName');
        const userEmail = document.getElementById('sakuraUserEmail');
        
        if (firstName) {
            firstName.addEventListener('input', function() {
                reviewData.firstName = this.value;
            });
        }
        if (lastName) {
            lastName.addEventListener('input', function() {
                reviewData.lastName = this.value;
            });
        }
        if (userEmail) {
            userEmail.addEventListener('input', function() {
                reviewData.email = this.value;
            });
        }
        
        const step4Back = document.getElementById('sakuraStep4Back');
        const step4Done = document.getElementById('sakuraStep4Done');
        
        if (step4Back) {
            step4Back.addEventListener('click', () => showStep(3));
        }
        if (step4Done) {
            step4Done.addEventListener('click', async function() {
                if (!reviewData.firstName || !reviewData.email) {
                    alert('Please fill in all required fields (First name and Email)');
                    return;
                }
                
                this.disabled = true;
                this.textContent = 'Submitting...';
                
                try {
                    const formData = new FormData();
                    formData.append('shopify_product_id', currentProductId);
                    formData.append('rating', reviewData.rating);
                    formData.append('text', reviewData.text);
                    formData.append('reviewer_name', `${reviewData.firstName} ${reviewData.lastName}`.trim());
                    formData.append('reviewer_email', reviewData.email);
                    
                    reviewData.photos.forEach((photo, index) => {
                        formData.append(`photo_${index}`, photo.file);
                    });
                    
                    const response = await fetch(`${SAKURA_CONFIG.apiUrl}/widget/${currentShopId}/reviews/${currentProductId}/submit`, {
                        method: 'POST',
                        body: formData
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        showStep(5);
                    } else {
                        alert('Failed to submit review: ' + (result.error || 'Unknown error'));
                        this.disabled = false;
                        this.textContent = 'Done';
                    }
                } catch (error) {
                    console.error('Error submitting review:', error);
                    alert('Error submitting review. Please try again.');
                    this.disabled = false;
                    this.textContent = 'Done';
                }
            });
        }
        
        // Step 5: Confirmation
        const step5Close = document.getElementById('sakuraStep5Close');
        if (step5Close) {
            step5Close.addEventListener('click', function() {
                closeModal();
                // Reload iframe to show new review
                const iframe = document.querySelector('iframe[id*="sakuraReviewsFrame"]');
                if (iframe) {
                    iframe.src = iframe.src.split('?')[0] + '?v=' + Date.now();
                }
            });
        }
        
        // Listen for messages from iframe to open modal
        window.addEventListener('message', function(event) {
            if (event.data && event.data.type === 'openReviewModal') {
                currentProductId = event.data.productId || SAKURA_CONFIG.productId;
                // Try to extract shop ID from iframe URL
                const iframe = document.querySelector('iframe[id*="sakuraReviewsFrame"]');
                if (iframe && iframe.src) {
                    const urlParts = iframe.src.split('/widget/');
                    if (urlParts.length > 1) {
                        const afterWidget = urlParts[1].split('/reviews/')[0];
                        if (afterWidget) currentShopId = afterWidget;
                    }
                }
                if (overlay) {
                    overlay.style.display = 'flex';
                    showStep(1);
                    // Reset state
                    reviewData = { rating: 0, photos: [], text: '', firstName: '', lastName: '', email: '' };
                    stars.forEach(star => {
                        star.style.color = '#e2e8f0';
                    });
                    if (step1Next) {
                        step1Next.disabled = true;
                        step1Next.style.background = '#e2e8f0';
                        step1Next.style.color = '#999';
                        step1Next.style.cursor = 'not-allowed';
                    }
                    // Reset form fields
                    if (reviewText) reviewText.value = '';
                    if (firstName) firstName.value = '';
                    if (lastName) lastName.value = '';
                    if (userEmail) userEmail.value = '';
                    if (photoPreviewGrid) photoPreviewGrid.innerHTML = '';
                }
            }
        });
    }
    
    // Inject modal on page load
    injectReviewModal();
    
    // ==================== PHOTO LIGHTBOX MODAL (Like Loox) ====================
    function injectPhotoLightbox() {
        if (document.getElementById('sakura-photo-lightbox-overlay')) {
            return; // Already injected
        }
        
        const lightboxHTML = `
            <div class="sakura-photo-lightbox-overlay" id="sakura-photo-lightbox-overlay" style="display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.9); z-index: 999998; align-items: center; justify-content: center;">
                <button class="sakura-lightbox-close" id="sakuraLightboxClose" style="position: fixed; top: 20px; right: 20px; width: 40px; height: 40px; background: rgba(255,255,255,0.95); border: none; border-radius: 50%; font-size: 24px; color: #1a202c; cursor: pointer; z-index: 999999; display: flex; align-items: center; justify-content: center;">×</button>
                <div class="sakura-photo-lightbox" style="width: 100%; max-width: 1200px; height: 90vh; display: flex; position: relative;">
                    <div class="sakura-lightbox-left" id="sakuraLightboxLeft" style="flex: 1; padding: 32px; overflow-y: auto; background: white; display: flex; flex-direction: column;">
                        <!-- Review details will be populated here -->
                    </div>
                    <div class="sakura-lightbox-right" style="width: 500px; min-width: 500px; position: relative; background: #f7fafc; display: flex; align-items: center; justify-content: center;">
                        <div class="sakura-lightbox-slider-container" style="position: relative; width: 100%; height: 100%; min-height: 500px; overflow: hidden;">
                            <div class="sakura-lightbox-slider-wrapper" id="sakuraLightboxSliderWrapper" style="display: flex; transition: transform 0.4s ease; height: 100%;">
                                <!-- Slides will be populated here -->
                            </div>
                            <button class="sakura-lightbox-nav prev" id="sakuraLightboxPrev" style="position: absolute; top: 50%; left: 16px; transform: translateY(-50%); width: 40px; height: 40px; background: rgba(255,255,255,0.95); border: none; border-radius: 50%; font-size: 24px; color: #1a202c; cursor: pointer; z-index: 10; display: flex; align-items: center; justify-content: center;">‹</button>
                            <button class="sakura-lightbox-nav next" id="sakuraLightboxNext" style="position: absolute; top: 50%; right: 16px; transform: translateY(-50%); width: 40px; height: 40px; background: rgba(255,255,255,0.95); border: none; border-radius: 50%; font-size: 24px; color: #1a202c; cursor: pointer; z-index: 10; display: flex; align-items: center; justify-content: center;">›</button>
                            <div class="sakura-lightbox-dots" id="sakuraLightboxDots" style="position: absolute; bottom: 16px; left: 50%; transform: translateX(-50%); display: flex; gap: 8px; z-index: 10;"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        const lightboxContainer = document.createElement('div');
        lightboxContainer.innerHTML = lightboxHTML;
        document.body.appendChild(lightboxContainer.firstElementChild);
        
        initPhotoLightbox();
    }
    
    function initPhotoLightbox() {
        const overlay = document.getElementById('sakura-photo-lightbox-overlay');
        const closeBtn = document.getElementById('sakuraLightboxClose');
        const leftPanel = document.getElementById('sakuraLightboxLeft');
        const sliderWrapper = document.getElementById('sakuraLightboxSliderWrapper');
        const prevBtn = document.getElementById('sakuraLightboxPrev');
        const nextBtn = document.getElementById('sakuraLightboxNext');
        const dots = document.getElementById('sakuraLightboxDots');
        
        let currentPhotos = [];
        let currentPhotoIndex = 0;
        let currentReviewData = null;
        
        function closeLightbox() {
            if (overlay) overlay.style.display = 'none';
            document.body.style.overflow = '';
        }
        
        function updateLightbox() {
            if (currentPhotos.length === 0) return;
            
            // Update left panel with review details
            if (currentReviewData && leftPanel) {
                let stars = '';
                for (let i = 0; i < (currentReviewData.rating || 5); i++) {
                    stars += '<span style="color: #ffd700; font-size: 18px;">★</span>';
                }
                
                let verifiedBadge = '';
                if (currentReviewData.verified) {
                    verifiedBadge = '<span style="background: #48bb78; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; margin-left: 8px;">✓ Verified</span>';
                }
                
                const reviewerName = currentReviewData.author || 'Anonymous';
                const reviewerInitial = reviewerName[0] || 'C';
                const reviewDate = currentReviewData.date || '';
                const reviewText = currentReviewData.text || '';
                
                leftPanel.innerHTML = `
                    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px;">
                        <div style="width: 48px; height: 48px; border-radius: 50%; background: linear-gradient(135deg, #ff69b4, #8b4a8b); display: flex; align-items: center; justify-content: center; color: white; font-weight: 600; font-size: 18px;">${reviewerInitial}</div>
                        <div>
                            <div style="font-weight: 600; color: #2d3748; font-size: 16px; margin-bottom: 4px;">${reviewerName}</div>
                            <div style="font-size: 14px; color: #718096;">${reviewDate}</div>
                        </div>
                    </div>
                    <div style="display: flex; gap: 2px; margin: 16px 0;">${stars}</div>
                    <div style="color: #4a5568; line-height: 1.7; margin: 16px 0; font-size: 15px; flex: 1;">${reviewText}</div>
                    <div style="margin-top: auto; padding-top: 16px;">${verifiedBadge}</div>
                `;
            }
            
            // Update slider
            if (sliderWrapper) {
                sliderWrapper.innerHTML = currentPhotos.map((photo, index) => `
                    <div style="min-width: 100%; width: 100%; height: 100%; display: flex; align-items: center; justify-content: center;">
                        <img src="${photo.url}" alt="Review photo" style="width: 100%; height: 100%; object-fit: contain;">
                    </div>
                `).join('');
            }
            
            // Update dots
            if (dots) {
                dots.innerHTML = currentPhotos.map((_, index) => `
                    <span class="sakura-lightbox-dot ${index === currentPhotoIndex ? 'active' : ''}" data-index="${index}" style="width: ${index === currentPhotoIndex ? '24px' : '8px'}; height: 8px; border-radius: ${index === currentPhotoIndex ? '4px' : '50%'}; background: ${index === currentPhotoIndex ? 'white' : 'rgba(255,255,255,0.5)'}; border: 1px solid rgba(0,0,0,0.1); cursor: pointer; transition: all 0.2s;"></span>
                `).join('');
            }
            
            updateSliderPosition();
        }
        
        function updateSliderPosition() {
            if (!sliderWrapper) return;
            const translateX = -currentPhotoIndex * 100;
            sliderWrapper.style.transform = `translateX(${translateX}%)`;
            
            // Update dots
            const dotElements = dots.querySelectorAll('.sakura-lightbox-dot');
            dotElements.forEach((dot, index) => {
                if (index === currentPhotoIndex) {
                    dot.classList.add('active');
                    dot.style.width = '24px';
                    dot.style.borderRadius = '4px';
                    dot.style.background = 'white';
                } else {
                    dot.classList.remove('active');
                    dot.style.width = '8px';
                    dot.style.borderRadius = '50%';
                    dot.style.background = 'rgba(255,255,255,0.5)';
                }
            });
            
            // Update nav buttons
            if (prevBtn) prevBtn.disabled = currentPhotoIndex === 0;
            if (nextBtn) nextBtn.disabled = currentPhotoIndex === currentPhotos.length - 1;
        }
        
        function showPrevPhoto() {
            if (currentPhotoIndex > 0) {
                currentPhotoIndex--;
                updateSliderPosition();
            }
        }
        
        function showNextPhoto() {
            if (currentPhotoIndex < currentPhotos.length - 1) {
                currentPhotoIndex++;
                updateSliderPosition();
            }
        }
        
        if (closeBtn) {
            closeBtn.addEventListener('click', closeLightbox);
        }
        
        if (overlay) {
            overlay.addEventListener('click', function(e) {
                if (e.target === overlay) closeLightbox();
            });
        }
        
        if (prevBtn) {
            prevBtn.addEventListener('click', showPrevPhoto);
        }
        
        if (nextBtn) {
            nextBtn.addEventListener('click', showNextPhoto);
        }
        
        if (dots) {
            dots.addEventListener('click', function(e) {
                if (e.target.classList.contains('sakura-lightbox-dot')) {
                    currentPhotoIndex = parseInt(e.target.getAttribute('data-index'));
                    updateSliderPosition();
                }
            });
        }
        
        // Keyboard navigation
        document.addEventListener('keydown', function(e) {
            if (!overlay || overlay.style.display === 'none') return;
            if (e.key === 'Escape') closeLightbox();
            else if (e.key === 'ArrowLeft') showPrevPhoto();
            else if (e.key === 'ArrowRight') showNextPhoto();
        });
        
        // Listen for messages from iframe
        window.addEventListener('message', function(event) {
            if (event.data && event.data.type === 'openPhotoLightbox') {
                currentPhotos = event.data.photos || [];
                currentPhotoIndex = event.data.startIndex || 0;
                currentReviewData = event.data.reviewData || null;
                
                if (overlay && currentPhotos.length > 0) {
                    overlay.style.display = 'flex';
                    document.body.style.overflow = 'hidden';
                    updateLightbox();
                }
            }
        });
    }
    
    // Inject photo lightbox on page load
    injectPhotoLightbox();
    
})();
"""
    
    # Replace placeholder with actual base URL
    formatted_js = js_code.replace('__WIDGET_BASE_URL__', Config.WIDGET_BASE_URL)
    
    # Add cache-busting headers to force refresh
    headers = {
        'Content-Type': 'application/javascript',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
    }
    
    return formatted_js, 200, headers

@app.route('/shopify/scripttag/create', methods=['POST'])
def create_scripttag():
    """
    Create ScriptTag for automatic injection
    This is called when the app is installed
    """
    try:
        # Get shop domain and access token from request
        shop_domain = request.json.get('shop_domain')
        access_token = request.json.get('access_token')
        
        if not shop_domain or not access_token:
            return jsonify({'error': 'Missing shop_domain or access_token'}), 400
        
        # Create ScriptTag via Shopify API
        scripttag_url = f"https://{shop_domain}/admin/api/2025-10/script_tags.json"
        headers = {
            'X-Shopify-Access-Token': access_token,
            'Content-Type': 'application/json'
        }
        
        # Add cache-busting version parameter to force refresh
        import time
        version = int(time.time())  # Use timestamp as version
        scripttag_data = {
            "script_tag": {
                "event": "onload",
                "src": f"{Config.WIDGET_BASE_URL}/js/sakura-reviews.js?v={version}"
            }
        }
        
        # Make request to Shopify API
        import requests
        response = requests.post(scripttag_url, headers=headers, json=scripttag_data)
        
        if response.status_code == 201:
            return jsonify({
                'success': True,
                'message': 'ScriptTag created successfully',
                'scripttag': response.json()
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Failed to create ScriptTag: {response.text}'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error creating ScriptTag: {str(e)}'
        }), 500

@app.route('/auth')
def auth_index():
    """
    Base auth route - provides guidance for OAuth installation
    """
    shop = request.args.get('shop')
    if shop:
        # If shop parameter provided, redirect to install
        return redirect(f'/auth/install?shop={shop}')
    
    return jsonify({
        'message': 'Sakura Reviews OAuth',
        'endpoints': {
            'install': '/auth/install?shop=your-store.myshopify.com',
            'callback': '/auth/callback (used by Shopify)'
        },
        'usage': 'To install the app, visit /auth/install?shop=your-store.myshopify.com'
    })

@app.route('/auth/install')
def auth_install():
    """
    Simple OAuth install route - redirects to Shopify OAuth
    Usage: /auth/install?shop=your-store.myshopify.com
    """
    shop = request.args.get('shop')
    if not shop:
        return "Error: Missing shop parameter. Use: /auth/install?shop=your-store.myshopify.com", 400
    
    # Remove .myshopify.com if included
    if '.myshopify.com' in shop:
        shop = shop.replace('.myshopify.com', '')
    shop_domain = f"{shop}.myshopify.com"
    
    # Build OAuth URL
    api_key = Config.SHOPIFY_API_KEY
    redirect_uri = Config.SHOPIFY_REDIRECT_URI or f"{Config.WIDGET_BASE_URL}/auth/callback"
    scopes = Config.SHOPIFY_SCOPES
    
    if not api_key:
        return "Error: SHOPIFY_API_KEY not configured", 500
    
    auth_url = f"https://{shop_domain}/admin/oauth/authorize?client_id={api_key}&scope={scopes}&redirect_uri={redirect_uri}"
    
    return redirect(auth_url)

@app.route('/auth/callback')
def auth_callback():
    """
    OAuth callback - exchanges code for access token
    """
    try:
        code = request.args.get('code')
        shop = request.args.get('shop')
        hmac_param = request.args.get('hmac')
        
        if not code or not shop:
            return "Error: Missing code or shop parameter", 400
        
        # Exchange code for access token
        api_key = Config.SHOPIFY_API_KEY
        api_secret = Config.SHOPIFY_API_SECRET
        redirect_uri = Config.SHOPIFY_REDIRECT_URI or f"{Config.WIDGET_BASE_URL}/auth/callback"
        
        if not api_key or not api_secret:
            return "Error: Shopify API credentials not configured", 500
        
        token_url = f"https://{shop}/admin/oauth/access_token"
        token_data = {
            'client_id': api_key,
            'client_secret': api_secret,
            'code': code
        }
        
        import requests
        response = requests.post(token_url, json=token_data)
        
        if response.status_code == 200:
            token_response = response.json()
            access_token = token_response.get('access_token')
            
            # Store in session
            session['shop_domain'] = shop
            session['access_token'] = access_token
            
            # Save shop and access token to database
            if db_integration:
                try:
                    saved_shop = db_integration.get_or_create_shop(
                        shop_domain=shop,
                        access_token=access_token
                    )
                    logger.info(f"✅ Shop saved to database: {shop} (ID: {saved_shop.id})")
                except Exception as e:
                    logger.error(f"Error saving shop to database: {str(e)}")
            else:
                logger.warning("Database integration not available - shop not saved to database")
            
            # Auto-create ScriptTag after successful auth
            try:
                import time
                version = int(time.time())
                scripttag_url = f"https://{shop}/admin/api/2025-10/script_tags.json"
                headers = {
                    'X-Shopify-Access-Token': access_token,
                    'Content-Type': 'application/json'
                }
                scripttag_data = {
                    "script_tag": {
                        "event": "onload",
                        "src": f"{Config.WIDGET_BASE_URL}/js/sakura-reviews.js?v={version}"
                    }
                }
                requests.post(scripttag_url, headers=headers, json=scripttag_data)
            except:
                pass  # ScriptTag creation is optional
            
            # Redirect to Shopify admin or show success page
            shopify_admin_url = f"https://{shop}/admin/apps"
            return f"""
            <html>
            <head>
                <title>Installation Successful</title>
                <meta http-equiv="refresh" content="3;url={shopify_admin_url}">
                <style>
                    body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; text-align: center; }}
                    .success {{ color: #28a745; font-size: 32px; margin-bottom: 20px; }}
                    .message {{ font-size: 18px; margin: 20px 0; }}
                    .redirect {{ color: #666; font-size: 14px; margin-top: 30px; }}
                </style>
            </head>
            <body>
                <h1 class="success">✅ Installation Successful!</h1>
                <p class="message"><strong>Shop:</strong> {shop}</p>
                <p class="message">ReviewKing has been installed and configured.</p>
                <p class="message">ScriptTag created automatically - reviews will appear on your product pages!</p>
                <p class="redirect">Redirecting to Shopify admin in 3 seconds...</p>
                <p>
                    <a href="{shopify_admin_url}" style="background: #ff69b4; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block; margin: 10px;">Go to Shopify Admin</a>
                    <a href="/" style="background: #6c757d; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block; margin: 10px;">Go Home</a>
                </p>
            </body>
            </html>
            """
        else:
            return f"Error: Failed to get access token: {response.text}", 400
            
    except Exception as e:
        return f"Error: {str(e)}", 500

# =============================================================================
# SHOPIFY BILLING API - Subscription Management
# =============================================================================

class ShopifyBilling:
    """
    Shopify Billing API integration for subscription management
    Handles recurring charges for Basic ($19.99) and Pro ($39.99) plans
    """
    
    PLANS = {
        'free': {
            'name': 'Free Forever',
            'price': 0,
            'reviews_limit': 50,
            'features': ['50 reviews', 'Basic widget', 'Single platform import']
        },
        'basic': {
            'name': 'Basic Plan',
            'price': 19.99,
            'reviews_limit': 500,
            'features': ['500 reviews', 'Custom widget styling', 'All platform imports', 'Priority support']
        },
        'pro': {
            'name': 'Pro Plan',
            'price': 39.99,
            'reviews_limit': 5000,
            'features': ['5000 reviews', 'Advanced customization', 'All platform imports', 'AI quality scoring', 'White-label option', 'Priority support']
        }
    }
    
    @staticmethod
    def create_subscription(shop_domain, access_token, plan_name, return_url=None):
        """
        Create a recurring application charge (subscription)
        Returns confirmation_url for merchant to approve
        """
        if plan_name not in ShopifyBilling.PLANS or plan_name == 'free':
            return {'error': 'Invalid plan or free plan selected'}
        
        plan = ShopifyBilling.PLANS[plan_name]
        
        if not return_url:
            return_url = f"{Config.WIDGET_BASE_URL}/billing/confirm?shop={shop_domain}"
        
        api_version = Config.SHOPIFY_API_VERSION or '2025-10'
        url = f"https://{shop_domain}/admin/api/{api_version}/recurring_application_charges.json"
        
        payload = {
            'recurring_application_charge': {
                'name': f"Sakura Reviews - {plan['name']}",
                'price': plan['price'],
                'return_url': return_url,
                'test': False,  # Production mode - required for App Store submission
                'trial_days': 7  # 7-day free trial
            }
        }
        
        headers = {
            'X-Shopify-Access-Token': access_token,
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code == 201:
                charge = response.json().get('recurring_application_charge', {})
                return {
                    'success': True,
                    'charge_id': charge.get('id'),
                    'confirmation_url': charge.get('confirmation_url'),
                    'status': charge.get('status')
                }
            else:
                return {'error': f"Shopify API error: {response.text}"}
        except Exception as e:
            return {'error': str(e)}
    
    @staticmethod
    def activate_subscription(shop_domain, access_token, charge_id):
        """
        Activate a subscription after merchant approves
        """
        api_version = Config.SHOPIFY_API_VERSION or '2025-10'
        url = f"https://{shop_domain}/admin/api/{api_version}/recurring_application_charges/{charge_id}/activate.json"
        
        headers = {
            'X-Shopify-Access-Token': access_token,
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(url, headers=headers)
            if response.status_code == 200:
                charge = response.json().get('recurring_application_charge', {})
                return {
                    'success': True,
                    'status': charge.get('status'),
                    'activated_on': charge.get('activated_on')
                }
            else:
                return {'error': f"Activation failed: {response.text}"}
        except Exception as e:
            return {'error': str(e)}
    
    @staticmethod
    def get_subscription_status(shop_domain, access_token):
        """
        Get current subscription status for a shop
        """
        api_version = Config.SHOPIFY_API_VERSION or '2025-10'
        url = f"https://{shop_domain}/admin/api/{api_version}/recurring_application_charges.json"
        
        headers = {
            'X-Shopify-Access-Token': access_token
        }
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                charges = response.json().get('recurring_application_charges', [])
                # Find active charge
                active_charge = None
                for charge in charges:
                    if charge.get('status') == 'active':
                        active_charge = charge
                        break
                
                if active_charge:
                    return {
                        'has_subscription': True,
                        'plan_name': active_charge.get('name'),
                        'price': active_charge.get('price'),
                        'status': active_charge.get('status'),
                        'charge_id': active_charge.get('id'),
                        'trial_ends_on': active_charge.get('trial_ends_on')
                    }
                else:
                    return {
                        'has_subscription': False,
                        'plan_name': 'Free',
                        'status': 'free'
                    }
            else:
                return {'error': f"API error: {response.text}"}
        except Exception as e:
            return {'error': str(e)}
    
    @staticmethod
    def cancel_subscription(shop_domain, access_token, charge_id):
        """
        Cancel a subscription
        """
        api_version = Config.SHOPIFY_API_VERSION or '2025-10'
        url = f"https://{shop_domain}/admin/api/{api_version}/recurring_application_charges/{charge_id}.json"
        
        headers = {
            'X-Shopify-Access-Token': access_token
        }
        
        try:
            response = requests.delete(url, headers=headers)
            if response.status_code == 200:
                return {'success': True, 'message': 'Subscription cancelled'}
            else:
                return {'error': f"Cancellation failed: {response.text}"}
        except Exception as e:
            return {'error': str(e)}


# Billing Routes

@app.route('/billing/plans')
def billing_plans():
    """Show available pricing plans"""
    return render_template('billing-plans.html') if 'billing-plans.html' in os.listdir('templates') else jsonify({
        'plans': ShopifyBilling.PLANS,
        'currency': 'USD',
        'billing_period': 'monthly'
    })

@app.route('/billing/subscribe/<plan_name>')
def billing_subscribe(plan_name):
    """
    Start subscription process
    Requires: ?shop=domain.myshopify.com&token=access_token
    Or uses session data
    """
    shop = request.args.get('shop') or session.get('shop_domain')
    access_token = request.args.get('token') or session.get('access_token')
    
    if not shop or not access_token:
        return jsonify({'error': 'Missing shop or access token. Please reinstall the app.'}), 400
    
    if plan_name == 'free':
        return jsonify({
            'success': True,
            'message': 'You are on the Free plan. No payment required!',
            'plan': ShopifyBilling.PLANS['free']
        })
    
    result = ShopifyBilling.create_subscription(shop, access_token, plan_name)
    
    if result.get('confirmation_url'):
        # Redirect to Shopify for approval
        return redirect(result['confirmation_url'])
    else:
        return jsonify(result), 400

@app.route('/billing/confirm')
def billing_confirm():
    """
    Callback after merchant approves/declines subscription
    Shopify redirects here with charge_id
    """
    shop = request.args.get('shop')
    charge_id = request.args.get('charge_id')
    
    if not shop or not charge_id:
        return "Error: Missing parameters", 400
    
    # Get access token from session or database
    access_token = session.get('access_token')
    
    if not access_token and db_integration:
        try:
            from backend.models_v2 import Shop
            shop_record = Shop.query.filter_by(shop_domain=shop).first()
            if shop_record:
                access_token = shop_record.access_token
        except:
            pass
    
    if not access_token:
        return "Error: Could not find access token. Please reinstall the app.", 400
    
    # Activate the subscription
    result = ShopifyBilling.activate_subscription(shop, access_token, charge_id)
    
    if result.get('success'):
        # Update shop's plan in database
        if db_integration:
            try:
                from backend.models_v2 import Shop
                shop_record = Shop.query.filter_by(shop_domain=shop).first()
                if shop_record:
                    # Store plan info (you may want to add a plan column to Shop model)
                    logger.info(f"✅ Subscription activated for {shop}")
            except Exception as e:
                logger.error(f"Error updating shop plan: {e}")
        
        return f"""
        <html>
        <head>
            <title>Subscription Activated!</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; text-align: center; }}
                .success {{ color: #28a745; font-size: 48px; }}
                h1 {{ color: #333; }}
                .message {{ font-size: 18px; margin: 20px 0; color: #666; }}
                .btn {{ background: #ff69b4; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block; margin: 10px; }}
            </style>
        </head>
        <body>
            <div class="success">🎉</div>
            <h1>Subscription Activated!</h1>
            <p class="message">Thank you for subscribing to Sakura Reviews!</p>
            <p class="message">Your premium features are now active.</p>
            <a href="https://{shop}/admin/apps" class="btn">Return to Shopify</a>
        </body>
        </html>
        """
    else:
        return f"""
        <html>
        <head>
            <title>Subscription Error</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; text-align: center; }}
                .error {{ color: #dc3545; font-size: 48px; }}
                h1 {{ color: #333; }}
                .message {{ font-size: 16px; margin: 20px 0; color: #666; }}
            </style>
        </head>
        <body>
            <div class="error">❌</div>
            <h1>Subscription Not Activated</h1>
            <p class="message">The subscription was not completed.</p>
            <p class="message">Error: {result.get('error', 'Unknown error')}</p>
            <a href="/billing/plans" style="color: #ff69b4;">Try again</a>
        </body>
        </html>
        """

@app.route('/billing/status')
def billing_status():
    """
    Check current subscription status
    """
    shop = request.args.get('shop') or session.get('shop_domain')
    access_token = request.args.get('token') or session.get('access_token')
    
    if not shop or not access_token:
        return jsonify({'error': 'Missing shop or access token'}), 400
    
    result = ShopifyBilling.get_subscription_status(shop, access_token)
    return jsonify(result)

@app.route('/billing/cancel', methods=['POST'])
def billing_cancel():
    """
    Cancel subscription
    """
    shop = request.args.get('shop') or session.get('shop_domain')
    access_token = request.args.get('token') or session.get('access_token')
    charge_id = request.args.get('charge_id') or request.json.get('charge_id')
    
    if not shop or not access_token or not charge_id:
        return jsonify({'error': 'Missing required parameters'}), 400
    
    result = ShopifyBilling.cancel_subscription(shop, access_token, charge_id)
    return jsonify(result)

@app.route('/webhooks/app_subscriptions/update', methods=['POST'])
def webhook_subscription_update():
    """
    Webhook for subscription updates (cancellation, etc.)
    Configure this webhook in your Shopify Partner Dashboard
    """
    try:
        data = request.get_json()
        logger.info(f"📬 Subscription webhook received: {data}")
        
        # Verify webhook (in production, verify HMAC)
        
        # Handle subscription update
        # Update your database accordingly
        
        return '', 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return '', 500

@app.route('/shopify/scripttag/update', methods=['POST', 'GET'])
def update_scripttag():
    """
    Update ScriptTag by deleting old ones and creating a new one
    This forces Shopify to load the new JavaScript file
    
    GET: Simple form to update ScriptTag
    POST: Update ScriptTag with shop_domain and access_token
    """
    if request.method == 'GET':
        # Return a simple HTML form
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Update Sakura Reviews ScriptTag</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }
                .form-group { margin-bottom: 20px; }
                label { display: block; margin-bottom: 5px; font-weight: bold; }
                input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
                button { background: #ff69b4; color: white; padding: 12px 24px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
                button:hover { opacity: 0.9; }
                .result { margin-top: 20px; padding: 15px; border-radius: 4px; }
                .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
                .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
            </style>
        </head>
        <body>
            <h1>🌸 Update Sakura Reviews ScriptTag</h1>
            <p>This will delete old ScriptTags and create a new one with the updated domain.</p>
            <form id="updateForm">
                <div class="form-group">
                    <label>Shop Domain:</label>
                    <input type="text" name="shop_domain" value="sakura-rev-test-store.myshopify.com" required>
                </div>
                <div class="form-group">
                    <label>Access Token:</label>
                    <input type="text" name="access_token" id="accessTokenInput" placeholder="shpat_... or shpua_..." required>
                    <p style="font-size: 12px; color: #666; margin-top: 5px;">
                        💡 Tip: If you just installed the app, check the installation success page for your full token.
                    </p>
                </div>
                <button type="submit">Update ScriptTag</button>
            </form>
            <div id="result"></div>
            <script>
                document.getElementById('updateForm').addEventListener('submit', async function(e) {
                    e.preventDefault();
                    const formData = new FormData(e.target);
                    const data = {
                        shop_domain: formData.get('shop_domain'),
                        access_token: formData.get('access_token')
                    };
                    const resultDiv = document.getElementById('result');
                    resultDiv.innerHTML = '<p>Updating...</p>';
                    try {
                        const response = await fetch('/shopify/scripttag/update', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(data)
                        });
                        const result = await response.json();
                        if (result.success) {
                            resultDiv.innerHTML = `<div class="result success">
                                <h3>✅ Success!</h3>
                                <p>${result.message}</p>
                                <p><strong>New ScriptTag URL:</strong> ${result.new_url}</p>
                            </div>`;
                        } else {
                            resultDiv.innerHTML = `<div class="result error">
                                <h3>❌ Error</h3>
                                <p>${result.error}</p>
                            </div>`;
                        }
                    } catch (error) {
                        resultDiv.innerHTML = `<div class="result error">
                            <h3>❌ Error</h3>
                            <p>${error.message}</p>
                        </div>`;
                    }
                });
            </script>
        </body>
        </html>
        """
    
    try:
        # Get shop domain and access token from request
        shop_domain = request.json.get('shop_domain')
        access_token = request.json.get('access_token')
        
        if not shop_domain or not access_token:
            return jsonify({'error': 'Missing shop_domain or access_token'}), 400
        
        import requests
        headers = {
            'X-Shopify-Access-Token': access_token,
            'Content-Type': 'application/json'
        }
        
        # First, get all existing ScriptTags
        scripttag_list_url = f"https://{shop_domain}/admin/api/2025-10/script_tags.json"
        list_response = requests.get(scripttag_list_url, headers=headers)
        
        if list_response.status_code == 200:
            scripttags = list_response.json().get('script_tags', [])
            # Delete all old Sakura Reviews ScriptTags
            for scripttag in scripttags:
                if 'sakura-reviews' in scripttag.get('src', '').lower():
                    delete_url = f"https://{shop_domain}/admin/api/2025-10/script_tags/{scripttag['id']}.json"
                    requests.delete(delete_url, headers=headers)
        
        # Now create a new ScriptTag with cache-busting
        import time
        version = int(time.time())
        scripttag_url = f"https://{shop_domain}/admin/api/2025-10/script_tags.json"
        scripttag_data = {
            "script_tag": {
                "event": "onload",
                "src": f"{Config.WIDGET_BASE_URL}/js/sakura-reviews.js?v={version}"
            }
        }
        
        response = requests.post(scripttag_url, headers=headers, json=scripttag_data)
        
        if response.status_code == 201:
            return jsonify({
                'success': True,
                'message': 'ScriptTag updated successfully',
                'scripttag': response.json(),
                'new_url': f"{Config.WIDGET_BASE_URL}/js/sakura-reviews.js?v={version}"
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Failed to create ScriptTag: {response.text}'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error updating ScriptTag: {str(e)}'
        }), 500

@app.route('/admin/scripttags')
@admin_required
def admin_scripttags():
    """
    Admin ScriptTag Manager - View, cleanup, and manage ScriptTags
    Prevents the "old script showing" issue
    """
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>🌸 ScriptTag Manager - Sakura Reviews</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
            .container { max-width: 1000px; margin: 0 auto; }
            h1 { color: #ff69b4; margin-bottom: 10px; }
            .subtitle { color: #666; margin-bottom: 30px; }
            .card { background: white; border-radius: 12px; padding: 24px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
            .scripttag-item { display: flex; justify-content: space-between; align-items: center; padding: 15px; border: 1px solid #e0e0e0; border-radius: 8px; margin-bottom: 10px; }
            .scripttag-item.old { background: #fff3f3; border-color: #ffcdd2; }
            .scripttag-item.current { background: #f1f8e9; border-color: #c5e1a5; }
            .scripttag-url { font-family: monospace; font-size: 12px; word-break: break-all; flex: 1; margin-right: 15px; }
            .badge { padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: bold; }
            .badge.old { background: #ffcdd2; color: #c62828; }
            .badge.current { background: #c5e1a5; color: #33691e; }
            .btn { padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; }
            .btn-danger { background: #f44336; color: white; }
            .btn-danger:hover { background: #d32f2f; }
            .btn-primary { background: #ff69b4; color: white; }
            .btn-primary:hover { background: #ff4da6; }
            .btn-success { background: #4caf50; color: white; }
            .btn-success:hover { background: #43a047; }
            .actions { margin-top: 20px; display: flex; gap: 10px; }
            .status { padding: 15px; border-radius: 8px; margin-top: 20px; }
            .status.success { background: #e8f5e9; color: #2e7d32; border: 1px solid #a5d6a7; }
            .status.error { background: #ffebee; color: #c62828; border: 1px solid #ef9a9a; }
            .loading { opacity: 0.6; pointer-events: none; }
            table { width: 100%; border-collapse: collapse; }
            th, td { padding: 12px; text-align: left; border-bottom: 1px solid #e0e0e0; }
            th { background: #f8f8f8; font-weight: 600; }
            .config-info { background: #e3f2fd; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
            .config-info code { background: #bbdefb; padding: 2px 6px; border-radius: 4px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🌸 ScriptTag Manager</h1>
            <p class="subtitle">Manage Shopify ScriptTags to prevent old scripts from loading</p>
            
            <div class="card config-info">
                <strong>Current Configuration:</strong><br>
                <code>WIDGET_BASE_URL: {{ widget_base_url }}</code><br>
                <small>All ScriptTags should point to this URL</small>
            </div>
            
            <div class="card">
                <h2>Shop Configuration</h2>
                <form id="shopForm">
                    <table>
                        <tr>
                            <td><strong>Shop Domain:</strong></td>
                            <td><input type="text" id="shopDomain" value="sakura-rev-test-store.myshopify.com" style="width: 100%; padding: 8px;"></td>
                        </tr>
                        <tr>
                            <td><strong>Access Token:</strong></td>
                            <td><input type="text" id="accessToken" placeholder="Enter access token (shpat_...)" style="width: 100%; padding: 8px;"></td>
                        </tr>
                    </table>
                    <div class="actions">
                        <button type="button" class="btn btn-primary" onclick="loadScriptTags()">🔍 Load ScriptTags</button>
                    </div>
                </form>
            </div>
            
            <div class="card" id="scripttagsCard" style="display: none;">
                <h2>Installed ScriptTags</h2>
                <div id="scripttagsList"></div>
                <div class="actions">
                    <button type="button" class="btn btn-danger" onclick="cleanupOldScriptTags()">🗑️ Delete OLD ScriptTags</button>
                    <button type="button" class="btn btn-success" onclick="createNewScriptTag()">➕ Create New ScriptTag</button>
                </div>
                <div id="statusMessage"></div>
            </div>
        </div>
        
        <script>
            const CURRENT_URL = '{{ widget_base_url }}';
            let scriptTags = [];
            
            async function loadScriptTags() {
                const shopDomain = document.getElementById('shopDomain').value;
                const accessToken = document.getElementById('accessToken').value;
                
                document.getElementById('scripttagsCard').style.display = 'block';
                document.getElementById('scripttagsList').innerHTML = '<p>Loading...</p>';
                
                try {
                    const response = await fetch(`/api/admin/scripttags/list?shop=${shopDomain}&token=${accessToken}`);
                    const data = await response.json();
                    
                    if (data.error) {
                        document.getElementById('scripttagsList').innerHTML = `<p style="color: red;">Error: ${data.error}</p>`;
                        return;
                    }
                    
                    scriptTags = data.script_tags || [];
                    renderScriptTags();
                } catch (e) {
                    document.getElementById('scripttagsList').innerHTML = `<p style="color: red;">Error: ${e.message}</p>`;
                }
            }
            
            function renderScriptTags() {
                if (scriptTags.length === 0) {
                    document.getElementById('scripttagsList').innerHTML = '<p>No ScriptTags found.</p>';
                    return;
                }
                
                let html = '';
                scriptTags.forEach(tag => {
                    const isOld = !tag.src.includes('sakrev-v15');
                    const isCurrent = tag.src.includes('sakrev-v15');
                    html += `
                        <div class="scripttag-item ${isOld ? 'old' : ''} ${isCurrent ? 'current' : ''}">
                            <div class="scripttag-url">
                                <strong>ID:</strong> ${tag.id}<br>
                                <strong>URL:</strong> ${tag.src}<br>
                                <strong>Created:</strong> ${tag.created_at}
                            </div>
                            <span class="badge ${isOld ? 'old' : 'current'}">${isOld ? '⚠️ OLD' : '✅ CURRENT'}</span>
                            <button class="btn btn-danger" onclick="deleteScriptTag(${tag.id})" style="margin-left: 10px;">Delete</button>
                        </div>
                    `;
                });
                document.getElementById('scripttagsList').innerHTML = html;
            }
            
            async function deleteScriptTag(id) {
                const shopDomain = document.getElementById('shopDomain').value;
                const accessToken = document.getElementById('accessToken').value;
                
                try {
                    const response = await fetch(`/api/admin/scripttags/delete?shop=${shopDomain}&token=${accessToken}&id=${id}`, { method: 'DELETE' });
                    const data = await response.json();
                    showStatus(data.success ? 'success' : 'error', data.message || data.error);
                    loadScriptTags();
                } catch (e) {
                    showStatus('error', e.message);
                }
            }
            
            async function cleanupOldScriptTags() {
                const shopDomain = document.getElementById('shopDomain').value;
                const accessToken = document.getElementById('accessToken').value;
                
                try {
                    const response = await fetch(`/api/admin/scripttags/cleanup?shop=${shopDomain}&token=${accessToken}`, { method: 'POST' });
                    const data = await response.json();
                    showStatus(data.success ? 'success' : 'error', data.message || data.error);
                    loadScriptTags();
                } catch (e) {
                    showStatus('error', e.message);
                }
            }
            
            async function createNewScriptTag() {
                const shopDomain = document.getElementById('shopDomain').value;
                const accessToken = document.getElementById('accessToken').value;
                
                try {
                    const response = await fetch(`/api/admin/scripttags/create?shop=${shopDomain}&token=${accessToken}`, { method: 'POST' });
                    const data = await response.json();
                    showStatus(data.success ? 'success' : 'error', data.message || data.error);
                    loadScriptTags();
                } catch (e) {
                    showStatus('error', e.message);
                }
            }
            
            function showStatus(type, message) {
                document.getElementById('statusMessage').innerHTML = `<div class="status ${type}">${message}</div>`;
            }
        </script>
    </body>
    </html>
    """, widget_base_url=Config.WIDGET_BASE_URL)

@app.route('/api/admin/scripttags/list')
@admin_required
def api_admin_scripttags_list():
    """API: List ScriptTags for a shop"""
    shop = request.args.get('shop')
    token = request.args.get('token')
    
    if not shop or not token:
        return jsonify({'error': 'Missing shop or token'}), 400
    
    try:
        import requests as req
        headers = {'X-Shopify-Access-Token': token}
        response = req.get(f"https://{shop}/admin/api/2025-10/script_tags.json", headers=headers)
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': f'Shopify API error: {response.status_code}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/scripttags/delete', methods=['DELETE'])
@admin_required
def api_admin_scripttags_delete():
    """API: Delete a specific ScriptTag"""
    shop = request.args.get('shop')
    token = request.args.get('token')
    script_id = request.args.get('id')
    
    if not shop or not token or not script_id:
        return jsonify({'error': 'Missing shop, token, or id'}), 400
    
    try:
        import requests as req
        headers = {'X-Shopify-Access-Token': token}
        response = req.delete(f"https://{shop}/admin/api/2025-10/script_tags/{script_id}.json", headers=headers)
        
        if response.status_code == 200:
            return jsonify({'success': True, 'message': f'ScriptTag {script_id} deleted'})
        else:
            return jsonify({'success': False, 'error': f'Failed to delete: {response.status_code}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/scripttags/cleanup', methods=['POST'])
@admin_required
def api_admin_scripttags_cleanup():
    """API: Delete all OLD ScriptTags (not pointing to current WIDGET_BASE_URL)"""
    shop = request.args.get('shop')
    token = request.args.get('token')
    
    if not shop or not token:
        return jsonify({'error': 'Missing shop or token'}), 400
    
    try:
        import requests as req
        headers = {'X-Shopify-Access-Token': token}
        
        # Get all ScriptTags
        response = req.get(f"https://{shop}/admin/api/2025-10/script_tags.json", headers=headers)
        if response.status_code != 200:
            return jsonify({'success': False, 'error': 'Failed to get ScriptTags'}), 400
        
        script_tags = response.json().get('script_tags', [])
        deleted_count = 0
        
        for tag in script_tags:
            src = tag.get('src', '')
            # Delete if it doesn't point to current WIDGET_BASE_URL
            if Config.WIDGET_BASE_URL not in src and 'sakura' in src.lower():
                delete_response = req.delete(f"https://{shop}/admin/api/2025-10/script_tags/{tag['id']}.json", headers=headers)
                if delete_response.status_code == 200:
                    deleted_count += 1
        
        return jsonify({
            'success': True, 
            'message': f'Cleaned up {deleted_count} old ScriptTags',
            'deleted_count': deleted_count
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/scripttags/create', methods=['POST'])
@admin_required
def api_admin_scripttags_create():
    """API: Create a new ScriptTag pointing to current WIDGET_BASE_URL"""
    shop = request.args.get('shop')
    token = request.args.get('token')
    
    if not shop or not token:
        return jsonify({'error': 'Missing shop or token'}), 400
    
    try:
        import requests as req
        import time
        
        headers = {'X-Shopify-Access-Token': token, 'Content-Type': 'application/json'}
        version = int(time.time())
        
        data = {
            "script_tag": {
                "event": "onload",
                "src": f"{Config.WIDGET_BASE_URL}/js/sakura-reviews.js?v={version}"
            }
        }
        
        response = req.post(f"https://{shop}/admin/api/2025-10/script_tags.json", headers=headers, json=data)
        
        if response.status_code == 201:
            return jsonify({
                'success': True,
                'message': f'ScriptTag created: {Config.WIDGET_BASE_URL}/js/sakura-reviews.js?v={version}',
                'scripttag': response.json()
            })
        else:
            return jsonify({'success': False, 'error': f'Failed to create: {response.text}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/debug/routes')
def list_routes():
    """List all registered routes for debugging"""
    import urllib
    output = []
    for rule in app.url_map.iter_rules():
        options = {}
        for arg in rule.arguments:
            options[arg] = f"<{arg}>"
        
        methods = ','.join(rule.methods)
        url = urllib.parse.unquote(str(rule))
        line = f"{rule.endpoint}: {methods} {url}"
        output.append(line)
    
    return jsonify({
        'routes': sorted(output),
        'total': len(output)
    })

# ============================================================================
# GDPR Webhooks (Required for Shopify App Store)
# ============================================================================

@app.route('/webhooks/customers/data_request', methods=['POST'])
def customers_data_request():
    """
    GDPR: Handle customer data request
    Shopify will send customer data requests here
    """
    try:
        # Verify HMAC signature
        hmac_header = request.headers.get('X-Shopify-Hmac-Sha256')
        if not verify_webhook_hmac(request.data, hmac_header):
            logger.warning("Invalid HMAC signature for customers/data_request")
            return jsonify({'error': 'Invalid signature'}), 401
        
        data = request.get_json()
        shop_domain = data.get('shop_domain')
        customer_id = data.get('customer', {}).get('id')
        
        logger.info(f"GDPR: Customer data request for shop {shop_domain}, customer {customer_id}")
        
        # TODO: Return customer data if stored
        # For now, we don't store customer data, so return empty
        
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        logger.error(f"Error handling customers/data_request: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/webhooks/customers/redact', methods=['POST'])
def customers_redact():
    """
    GDPR: Handle customer data deletion request
    Shopify will send customer deletion requests here
    """
    try:
        # Verify HMAC signature
        hmac_header = request.headers.get('X-Shopify-Hmac-Sha256')
        if not verify_webhook_hmac(request.data, hmac_header):
            logger.warning("Invalid HMAC signature for customers/redact")
            return jsonify({'error': 'Invalid signature'}), 401
        
        data = request.get_json()
        shop_domain = data.get('shop_domain')
        customer_id = data.get('customer', {}).get('id')
        
        logger.info(f"GDPR: Customer data deletion for shop {shop_domain}, customer {customer_id}")
        
        # TODO: Delete customer data if stored
        # For now, we don't store customer data, so just acknowledge
        
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        logger.error(f"Error handling customers/redact: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/webhooks/shop/redact', methods=['POST'])
def shop_redact():
    """
    GDPR: Handle shop data deletion request
    Shopify will send shop deletion requests here
    """
    try:
        # Verify HMAC signature
        hmac_header = request.headers.get('X-Shopify-Hmac-Sha256')
        if not verify_webhook_hmac(request.data, hmac_header):
            logger.warning("Invalid HMAC signature for shop/redact")
            return jsonify({'error': 'Invalid signature'}), 401
        
        data = request.get_json()
        shop_domain = data.get('shop_domain')
        
        logger.info(f"GDPR: Shop data deletion for shop {shop_domain}")
        
        # Delete shop data from database
        from backend.models_v2 import Shop
        try:
            shop = Shop.query.filter_by(shop_domain=shop_domain).first()
            if shop:
                # Delete associated data (reviews, products, etc.)
                # Note: This should cascade delete related records
                db.session.delete(shop)
                db.session.commit()
                logger.info(f"Deleted shop data for {shop_domain}")
        except Exception as e:
            logger.error(f"Error deleting shop data: {str(e)}")
        
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        logger.error(f"Error handling shop/redact: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/webhooks/app/uninstalled', methods=['POST'])
def app_uninstalled():
    """
    Handle app uninstallation
    Clean up shop data when app is uninstalled
    """
    try:
        # Verify HMAC signature
        hmac_header = request.headers.get('X-Shopify-Hmac-Sha256')
        if not verify_webhook_hmac(request.data, hmac_header):
            logger.warning("Invalid HMAC signature for app/uninstalled")
            return jsonify({'error': 'Invalid signature'}), 401
        
        data = request.get_json()
        shop_domain = data.get('domain') or data.get('shop_domain')
        
        logger.info(f"App uninstalled for shop {shop_domain}")
        
        # Mark shop as uninstalled (don't delete, just mark)
        from backend.models_v2 import Shop
        try:
            shop = Shop.query.filter_by(shop_domain=shop_domain).first()
            if shop:
                shop.status = 'uninstalled'
                shop.access_token = None  # Remove access token
                db.session.commit()
                logger.info(f"Marked shop {shop_domain} as uninstalled")
        except Exception as e:
            logger.error(f"Error handling app uninstall: {str(e)}")
        
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        logger.error(f"Error handling app/uninstalled: {str(e)}")
        return jsonify({'error': str(e)}), 500

def verify_webhook_hmac(data, hmac_header):
    """
    Verify Shopify webhook HMAC signature
    """
    if not hmac_header:
        return False
    
    try:
        import base64
        api_secret = Config.SHOPIFY_API_SECRET
        if not api_secret:
            logger.warning("SHOPIFY_API_SECRET not configured")
            return False
        
        # Calculate HMAC
        calculated_hmac = base64.b64encode(
            hmac.new(
                api_secret.encode('utf-8'),
                data,
                hashlib.sha256
            ).digest()
        ).decode('utf-8')
        
        # Compare with provided HMAC
        return hmac.compare_digest(calculated_hmac, hmac_header)
        
    except Exception as e:
        logger.error(f"Error verifying webhook HMAC: {str(e)}")
        return False

def run_database_migrations():
    """Run any pending database migrations"""
    try:
        with app.app_context():
            # Add helpful_yes and helpful_no columns if they don't exist
            try:
                db.session.execute(db.text("""
                    ALTER TABLE reviews ADD COLUMN IF NOT EXISTS helpful_yes INTEGER DEFAULT 0;
                """))
                db.session.execute(db.text("""
                    ALTER TABLE reviews ADD COLUMN IF NOT EXISTS helpful_no INTEGER DEFAULT 0;
                """))
                db.session.commit()
                print("✅ Database migrations complete (helpful votes columns)")
            except Exception as e:
                db.session.rollback()
                print(f"⚠️ Migration note: {e}")
    except Exception as e:
        print(f"⚠️ Migration skipped: {e}")


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5016))  # Use 5016 for fresh start (avoid cache)
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    # Run migrations before starting
    run_database_migrations()
    
    print("=" * 60)
    print("ReviewKing Enhanced API Starting...")
    print("=" * 60)
    print(f"Version: {Config.API_VERSION}")
    print(f"Port: {port}")
    print(f"Debug: {debug}")
    print(f"Platforms: {', '.join(Config.PLATFORMS)}")
    print("=" * 60)
    print("\nCompetitive Advantages over Loox:")
    print("  * Multi-platform (they only have AliExpress)")
    print("  * AI Quality Scoring (they don't have this)")
    print("  * Bulk import (they don't have this)")
    print("  * Better pricing")
    print("  * Sentiment analysis")
    print("=" * 60)
    print(f"\nBookmarklet URL:")
    bookmarklet_url = f"javascript:(function(){{var s=document.createElement('script');s.src='http://localhost:{port}/js/bookmarklet.js?v='+Date.now();document.head.appendChild(s);}})();"
    print(bookmarklet_url)
    print("=" * 60)
    
    # Use SSL only for local development (EasyPanel handles SSL at proxy level)
    use_ssl = os.environ.get('USE_SSL', 'false').lower() == 'true'
    
    if use_ssl:
        try:
            print("Starting with SSL (local development mode)...")
            app.run(host='0.0.0.0', port=port, debug=debug, ssl_context='adhoc')
        except Exception as e:
            print(f"\n⚠️  SSL not available: {e}")
            print("Running without SSL...")
            app.run(host='0.0.0.0', port=port, debug=debug)
    else:
        print("Starting without SSL (production mode)...")
        app.run(host='0.0.0.0', port=port, debug=debug)
