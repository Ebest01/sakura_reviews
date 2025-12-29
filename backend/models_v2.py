"""
ReviewKing Database Models v2.0 - Proper Schema Design
Based on Loox's strategy: Owner -> Shop -> Product -> Review -> Media
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Index
import json

db = SQLAlchemy()

class ShopOwner(db.Model):
    """
    Shop Owner Model - One owner can have multiple shops
    This represents the person/company who owns Shopify stores
    """
    __tablename__ = 'shop_owners'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255))
    
    # Billing Information (for multi-shop billing)
    billing_email = db.Column(db.String(255))
    billing_address = db.Column(db.Text)
    
    # Account Status
    status = db.Column(db.String(50), default='active')  # active, suspended, deleted
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login_at = db.Column(db.DateTime)
    
    # Relationships
    shops = db.relationship('Shop', backref='owner', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<ShopOwner {self.email}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'shop_count': self.shops.count(),
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Shop(db.Model):
    """
    Shopify Shop Model - One owner can have multiple shops
    """
    __tablename__ = 'shops'
    
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('shop_owners.id'), nullable=False, index=True)
    
    # Shopify Information
    shop_domain = db.Column(db.String(255), unique=True, nullable=False, index=True)
    access_token = db.Column(db.Text, nullable=False)
    
    # Shop Details
    shop_name = db.Column(db.String(255))
    shop_email = db.Column(db.String(255))
    shop_owner = db.Column(db.String(255))
    country_code = db.Column(db.String(10))
    currency = db.Column(db.String(10))
    
    # Plan & Limits (per shop)
    plan = db.Column(db.String(50), default='free')  # free, basic, pro
    review_limit = db.Column(db.Integer, default=50)
    reviews_imported = db.Column(db.Integer, default=0)
    
    # Subscription (per shop)
    subscription_id = db.Column(db.String(255))
    subscription_status = db.Column(db.String(50), default='inactive')
    subscription_started_at = db.Column(db.DateTime)
    subscription_expires_at = db.Column(db.DateTime)
    
    # Loox-style Shop ID (for widget URLs)
    sakura_shop_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    
    # Timestamps
    installed_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active_at = db.Column(db.DateTime, default=datetime.utcnow)
    uninstalled_at = db.Column(db.DateTime)
    
    # Relationships
    products = db.relationship('Product', backref='shop', lazy='dynamic', cascade='all, delete-orphan')
    reviews = db.relationship('Review', backref='shop', lazy='dynamic', cascade='all, delete-orphan')
    imports = db.relationship('Import', backref='shop', lazy='dynamic', cascade='all, delete-orphan')
    settings = db.relationship('ShopSettings', backref='shop', uselist=False, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Shop {self.shop_domain}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'owner_id': self.owner_id,
            'shop_domain': self.shop_domain,
            'shop_name': self.shop_name,
            'sakura_shop_id': self.sakura_shop_id,
            'plan': self.plan,
            'review_limit': self.review_limit,
            'reviews_imported': self.reviews_imported,
            'subscription_status': self.subscription_status,
            'installed_at': self.installed_at.isoformat() if self.installed_at else None
        }
    
    def can_import_reviews(self, count=1):
        """Check if shop can import more reviews"""
        return (self.reviews_imported + count) <= self.review_limit
    
    def is_payment_active(self):
        """Check if shop has active payment (Loox-style gating)"""
        if self.plan == 'free':
            return self.reviews_imported < self.review_limit
        
        if self.plan in ['basic', 'pro']:
            return self.subscription_status == 'active'
        
        return False

class Product(db.Model):
    """
    Product Model - One shop has multiple products
    """
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shops.id'), nullable=False, index=True)
    
    # Shopify Product Information
    shopify_product_id = db.Column(db.String(255), nullable=False, index=True)
    shopify_product_title = db.Column(db.String(500))
    shopify_product_handle = db.Column(db.String(255))
    shopify_product_url = db.Column(db.Text)
    
    # Source Product Information (for import tracking)
    source_platform = db.Column(db.String(50))  # aliexpress, amazon, ebay, walmart
    source_product_id = db.Column(db.String(255))  # Generic (for amazon, ebay, etc.)
    aliexpress_product_id = db.Column(db.String(255))  # AliExpress product ID (e.g., "1005006661162689")
    source_product_url = db.Column(db.Text)
    
    # Product Metadata
    price = db.Column(db.Float)
    currency = db.Column(db.String(10))
    image_url = db.Column(db.Text)
    
    # Status
    status = db.Column(db.String(50), default='active')  # active, inactive, deleted
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    reviews = db.relationship('Review', backref='product', lazy='dynamic', cascade='all, delete-orphan')
    
    __table_args__ = (
        Index('idx_shop_product', 'shop_id', 'shopify_product_id'),
        Index('idx_source_product', 'source_platform', 'source_product_id'),
        Index('idx_aliexpress_product', 'aliexpress_product_id'),
    )
    
    def __repr__(self):
        return f'<Product {self.shopify_product_id} - {self.shopify_product_title}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'shop_id': self.shop_id,
            'shopify_product_id': self.shopify_product_id,
            'shopify_product_title': self.shopify_product_title,
            'shopify_product_handle': self.shopify_product_handle,
            'source_platform': self.source_platform,
            'source_product_id': self.source_product_id,
            'aliexpress_product_id': self.aliexpress_product_id,
            'price': self.price,
            'currency': self.currency,
            'image_url': self.image_url,
            'status': self.status,
            'review_count': self.reviews.filter_by(status='published').count(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Review(db.Model):
    """
    Review Model - One product has multiple reviews
    """
    __tablename__ = 'reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shops.id'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    
    # Shopify Product ID (for direct queries without joining products table)
    shopify_product_id = db.Column(db.String(255), index=True)
    
    # Source Information
    source_platform = db.Column(db.String(50), nullable=False)  # aliexpress, amazon, etc.
    source_product_id = db.Column(db.String(255), nullable=False)  # Generic (for amazon, ebay, etc.)
    aliexpress_product_id = db.Column(db.String(255))  # AliExpress product ID (e.g., "1005006661162689")
    source_review_id = db.Column(db.String(255), unique=True, index=True)
    source_url = db.Column(db.Text)
    
    # Review Content
    reviewer_name = db.Column(db.String(255))
    reviewer_email = db.Column(db.String(255))
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    title = db.Column(db.String(500))
    body = db.Column(db.Text)
    
    # Review Metadata
    verified_purchase = db.Column(db.Boolean, default=False)
    reviewer_country = db.Column(db.String(10))
    review_date = db.Column(db.DateTime)
    
    # AI Quality Scoring (competitive advantage)
    quality_score = db.Column(db.Float)
    ai_recommended = db.Column(db.Boolean, default=False)
    sentiment_score = db.Column(db.Float)
    
    # Status
    status = db.Column(db.String(50), default='pending')  # pending, published, hidden, deleted
    
    # Timestamps
    imported_at = db.Column(db.DateTime, default=datetime.utcnow)
    published_at = db.Column(db.DateTime)
    
    # Relationships
    media = db.relationship('ReviewMedia', backref='review', lazy='dynamic', cascade='all, delete-orphan')
    
    __table_args__ = (
        Index('idx_shop_product_review', 'shop_id', 'product_id'),
        Index('idx_source_review', 'source_platform', 'source_review_id'),
    )
    
    def __repr__(self):
        return f'<Review {self.id} - {self.rating}★ from {self.source_platform}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'shop_id': self.shop_id,
            'product_id': self.product_id,
            'shopify_product_id': self.shopify_product_id,
            'source_platform': self.source_platform,
            'source_product_id': self.source_product_id,
            'aliexpress_product_id': self.aliexpress_product_id,  # AliExpress product ID (for clarity)
            'source_review_id': self.source_review_id,
            'reviewer_name': self.reviewer_name,
            'rating': self.rating,
            'title': self.title,
            'body': self.body,
            'verified_purchase': self.verified_purchase,
            'reviewer_country': self.reviewer_country,
            'review_date': self.review_date.isoformat() if self.review_date else None,
            'quality_score': self.quality_score,
            'ai_recommended': self.ai_recommended,
            'status': self.status,
            'media_count': self.media.count(),
            'imported_at': self.imported_at.isoformat() if self.imported_at else None
        }

class ReviewMedia(db.Model):
    """
    Review Media Model - One review can have multiple media files
    """
    __tablename__ = 'review_media'
    
    id = db.Column(db.Integer, primary_key=True)
    review_id = db.Column(db.Integer, db.ForeignKey('reviews.id'), nullable=False, index=True)
    
    # Media Information
    media_type = db.Column(db.String(20), nullable=False)  # image, video
    media_url = db.Column(db.Text, nullable=False)
    media_thumbnail = db.Column(db.Text)  # For videos
    
    # Media Metadata
    file_size = db.Column(db.Integer)
    width = db.Column(db.Integer)
    height = db.Column(db.Integer)
    duration = db.Column(db.Integer)  # For videos (seconds)
    
    # Status
    status = db.Column(db.String(20), default='active')  # active, deleted, failed
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_review_media', 'review_id', 'media_type'),
    )
    
    def __repr__(self):
        return f'<ReviewMedia {self.id} - {self.media_type}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'review_id': self.review_id,
            'media_type': self.media_type,
            'media_url': self.media_url,
            'media_thumbnail': self.media_thumbnail,
            'file_size': self.file_size,
            'width': self.width,
            'height': self.height,
            'duration': self.duration,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Import(db.Model):
    """
    Import Job Model - Track bulk import operations
    """
    __tablename__ = 'imports'
    
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shops.id'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    
    # Import Details
    source_platform = db.Column(db.String(50), nullable=False)
    source_product_id = db.Column(db.String(255), nullable=False)
    source_url = db.Column(db.Text)
    
    shopify_product_id = db.Column(db.String(255))
    shopify_product_title = db.Column(db.String(500))
    
    # Import Configuration
    filters = db.Column(db.JSON)  # Filter settings
    max_reviews = db.Column(db.Integer)
    
    # Progress & Status
    status = db.Column(db.String(50), default='pending')  # pending, processing, completed, failed
    total_found = db.Column(db.Integer, default=0)
    total_imported = db.Column(db.Integer, default=0)
    total_failed = db.Column(db.Integer, default=0)
    
    # Error Handling
    error_message = db.Column(db.Text)
    
    # Timestamps
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<Import {self.id} - {self.status}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'shop_id': self.shop_id,
            'product_id': self.product_id,
            'source_platform': self.source_platform,
            'source_product_id': self.source_product_id,
            'shopify_product_id': self.shopify_product_id,
            'status': self.status,
            'total_found': self.total_found,
            'total_imported': self.total_imported,
            'total_failed': self.total_failed,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

class ShopSettings(db.Model):
    """
    Shop Settings Model - Per-shop customization
    """
    __tablename__ = 'shop_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shops.id'), nullable=False, unique=True)
    
    # Display Settings
    show_verified_badge = db.Column(db.Boolean, default=True)
    show_reviewer_country = db.Column(db.Boolean, default=True)
    show_review_photos = db.Column(db.Boolean, default=True)
    show_ai_scores = db.Column(db.Boolean, default=True)
    
    # Import Settings
    auto_publish = db.Column(db.Boolean, default=False)
    min_rating_filter = db.Column(db.Integer, default=3)
    require_photos = db.Column(db.Boolean, default=False)
    
    # Widget Customization
    widget_theme = db.Column(db.String(50), default='light')
    widget_position = db.Column(db.String(50), default='bottom')
    custom_css = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'show_verified_badge': self.show_verified_badge,
            'show_reviewer_country': self.show_reviewer_country,
            'show_review_photos': self.show_review_photos,
            'show_ai_scores': self.show_ai_scores,
            'auto_publish': self.auto_publish,
            'min_rating_filter': self.min_rating_filter,
            'require_photos': self.require_photos,
            'widget_theme': self.widget_theme,
            'widget_position': self.widget_position,
            'custom_css': self.custom_css
        }

class ContactMessage(db.Model):
    """
    Contact Form Messages - Store user inquiries
    """
    __tablename__ = 'contact_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Contact Information
    full_name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False, index=True)
    shopify_url = db.Column(db.String(500))
    
    # Message
    subject = db.Column(db.String(255))
    message = db.Column(db.Text, nullable=False)
    
    # Status
    status = db.Column(db.String(50), default='new')  # new, read, replied, closed
    priority = db.Column(db.String(50), default='normal')  # low, normal, high, urgent
    
    # Response
    admin_notes = db.Column(db.Text)
    replied_at = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<ContactMessage {self.email} - {self.subject}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'full_name': self.full_name,
            'email': self.email,
            'shopify_url': self.shopify_url,
            'subject': self.subject,
            'message': self.message,
            'status': self.status,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class EmailSettings(db.Model):
    """
    Email Settings per Shop - Controls review request emails
    """
    __tablename__ = 'email_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shops.id'), nullable=False, unique=True, index=True)
    
    # Email Enabled
    enabled = db.Column(db.Boolean, default=True)
    
    # Timing
    delay_days = db.Column(db.Integer, default=7)  # Days after order to send email
    send_time = db.Column(db.String(10), default='10:00')  # Time to send (HH:MM)
    
    # Reminders
    reminder_enabled = db.Column(db.Boolean, default=True)
    reminder_delay_days = db.Column(db.Integer, default=14)  # Days after first email
    max_reminders = db.Column(db.Integer, default=2)
    
    # Incentives
    discount_enabled = db.Column(db.Boolean, default=False)
    discount_percent = db.Column(db.Integer, default=10)
    photo_discount_enabled = db.Column(db.Boolean, default=False)
    photo_discount_percent = db.Column(db.Integer, default=15)
    
    # Email Content
    email_subject = db.Column(db.String(255), default="We'd love your feedback!")
    email_from_name = db.Column(db.String(255))  # Custom from name
    
    # Filters
    min_order_value = db.Column(db.Float, default=0)  # Minimum order value to send email
    exclude_products = db.Column(db.Text)  # JSON array of product IDs to exclude
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<EmailSettings shop_id={self.shop_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'shop_id': self.shop_id,
            'enabled': self.enabled,
            'delay_days': self.delay_days,
            'send_time': self.send_time,
            'reminder_enabled': self.reminder_enabled,
            'reminder_delay_days': self.reminder_delay_days,
            'max_reminders': self.max_reminders,
            'discount_enabled': self.discount_enabled,
            'discount_percent': self.discount_percent,
            'photo_discount_enabled': self.photo_discount_enabled,
            'photo_discount_percent': self.photo_discount_percent,
            'email_subject': self.email_subject,
            'email_from_name': self.email_from_name,
            'min_order_value': self.min_order_value,
            'exclude_products': json.loads(self.exclude_products) if self.exclude_products else []
        }


class ReviewRequest(db.Model):
    """
    Review Request Tracking - Tracks email requests sent to customers
    """
    __tablename__ = 'review_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shops.id'), nullable=False, index=True)
    
    # Order Information
    order_id = db.Column(db.String(255), nullable=False, index=True)
    order_number = db.Column(db.String(255))
    order_date = db.Column(db.DateTime)
    order_total = db.Column(db.Float)
    
    # Customer Information
    customer_email = db.Column(db.String(255), nullable=False, index=True)
    customer_name = db.Column(db.String(255))
    
    # Product Information
    product_id = db.Column(db.String(255), nullable=False)
    product_name = db.Column(db.String(255))
    product_image = db.Column(db.Text)
    
    # Email Status
    status = db.Column(db.String(50), default='pending')  # pending, sent, reminded, reviewed, unsubscribed
    emails_sent = db.Column(db.Integer, default=0)
    
    # Timestamps
    scheduled_at = db.Column(db.DateTime, index=True)  # When to send
    first_sent_at = db.Column(db.DateTime)
    last_sent_at = db.Column(db.DateTime)
    reviewed_at = db.Column(db.DateTime)
    
    # Discount Code (if incentives enabled)
    discount_code = db.Column(db.String(255))
    discount_used = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_review_request_shop_order', 'shop_id', 'order_id'),
        Index('idx_review_request_scheduled', 'status', 'scheduled_at'),
    )
    
    def __repr__(self):
        return f'<ReviewRequest {self.order_id} - {self.customer_email}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'order_number': self.order_number,
            'order_date': self.order_date.isoformat() if self.order_date else None,
            'customer_email': self.customer_email,
            'customer_name': self.customer_name,
            'product_id': self.product_id,
            'product_name': self.product_name,
            'product_image': self.product_image,
            'status': self.status,
            'emails_sent': self.emails_sent,
            'scheduled_at': self.scheduled_at.isoformat() if self.scheduled_at else None,
            'first_sent_at': self.first_sent_at.isoformat() if self.first_sent_at else None,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None
        }


class EmailUnsubscribe(db.Model):
    """
    Email Unsubscribe List - Customers who don't want review request emails
    """
    __tablename__ = 'email_unsubscribes'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, index=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shops.id'), index=True)  # NULL = global unsubscribe
    
    # Reason
    reason = db.Column(db.String(255))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_email_unsubscribe_shop', 'email', 'shop_id'),
    )
    
    def __repr__(self):
        return f'<EmailUnsubscribe {self.email}>'
