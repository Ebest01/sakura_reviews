"""
ReviewKing Configuration
Environment-aware configuration for development and production
"""
import os
from datetime import timedelta

class Config:
    """Base configuration"""
    # App Info
    APP_NAME = "ReviewKing"
    VERSION = "1.0.0"
    
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql://localhost/reviewking')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }
    
    # Shopify API
    SHOPIFY_API_KEY = os.environ.get('SHOPIFY_API_KEY')
    SHOPIFY_API_SECRET = os.environ.get('SHOPIFY_API_SECRET')
    SHOPIFY_SCOPES = 'read_products,write_products,read_product_listings'
    SHOPIFY_REDIRECT_URI = os.environ.get('SHOPIFY_REDIRECT_URI', 'http://localhost:5000/auth/callback')
    SHOPIFY_APP_URL = os.environ.get('SHOPIFY_APP_URL', 'http://localhost:5000')
    
    # Redis & Celery (for async tasks)
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL
    
    # Review Import Limits
    FREE_TIER_REVIEW_LIMIT = 50
    BASIC_TIER_REVIEW_LIMIT = 500
    PRO_TIER_REVIEW_LIMIT = 5000
    
    # Subscription Plans
    SUBSCRIPTION_PLANS = {
        'free': {
            'name': 'Free Plan',
            'price': 0,
            'review_limit': 50,
            'features': ['Basic review import', 'AliExpress & Amazon support']
        },
        'basic': {
            'name': 'Basic Plan',
            'price': 19.99,
            'review_limit': 500,
            'features': ['All Free features', 'AI quality scoring', 'Photo imports', 'Email support']
        },
        'pro': {
            'name': 'Pro Plan',
            'price': 49.99,
            'review_limit': 5000,
            'features': ['All Basic features', 'Bulk import', 'Priority support', 'Custom branding']
        }
    }
    
    # Scraping Settings
    SCRAPING_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    SCRAPING_TIMEOUT = 30
    SCRAPING_RETRY_ATTEMPTS = 3
    
    # Security
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # CORS
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000').split(',')
    
    # Monitoring
    SENTRY_DSN = os.environ.get('SENTRY_DSN')
    
    # Feature Flags
    ENABLE_AMAZON_SCRAPING = os.environ.get('ENABLE_AMAZON_SCRAPING', 'true').lower() == 'true'
    ENABLE_ALIEXPRESS_SCRAPING = os.environ.get('ENABLE_ALIEXPRESS_SCRAPING', 'true').lower() == 'true'
    ENABLE_AI_SCORING = os.environ.get('ENABLE_AI_SCORING', 'true').lower() == 'true'

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SESSION_COOKIE_SECURE = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    
class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'postgresql://localhost/reviewking_test'

# Config dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

