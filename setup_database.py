"""
Database Setup Script for ReviewKing
====================================

This script sets up the PostgreSQL database with proper schema
for enterprise-scale review management.
"""
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Initialize Flask app for database setup
app = Flask(__name__)

# Database configuration - EasyPanel PostgreSQL
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://saksaks:11!!!!.Magics4321@193.203.165.217:5432/sakrev_db?sslmode=disable')
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Import our models first
from backend.models import Shop, Review, Import, Settings, db

# Initialize database with the same instance
db.init_app(app)

def setup_database():
    """
    Create database tables and initial data
    """
    print("Setting up ReviewKing Database...")
    print(f"Database URL: {DATABASE_URL}")
    
    try:
        # Create all tables
        with app.app_context():
            print("Creating database tables...")
            db.create_all()
            print("SUCCESS: Tables created successfully!")
            
            # Create demo shop
            print("Creating demo shop...")
            
            # Check if demo shop already exists
            demo_shop = Shop.query.filter_by(shop_domain="sakura-rev-test-store.myshopify.com").first()
            
            if not demo_shop:
                # Create demo shop
                demo_shop = Shop(
                    shop_domain="sakura-rev-test-store.myshopify.com",
                    access_token="demo-token",
                    shop_name="Sakura Test Store",
                    shop_email="demo@sakura-reviews.com",
                    shop_owner="Demo Owner",
                    plan='free',
                    review_limit=50,
                    reviews_imported=0
                )
                db.session.add(demo_shop)
                db.session.flush()
                
                # Create shop settings
                shop_settings = Settings(
                    shop_id=demo_shop.id,
                    show_verified_badge=True,
                    show_reviewer_country=True,
                    show_review_photos=True,
                    auto_publish=True,
                    min_rating_filter=3,
                    widget_theme='light'
                )
                db.session.add(shop_settings)
                
                db.session.commit()
                
                print(f"SUCCESS: Demo shop created with ID: {demo_shop.id}")
                print("SUCCESS: Shop settings configured")
            else:
                print("SUCCESS: Demo shop already exists")
            
            # Show database stats
            print("\nDatabase Statistics:")
            print(f"   Shops: {Shop.query.count()}")
            print(f"   Reviews: {Review.query.count()}")
            print(f"   Imports: {Import.query.count()}")
            print(f"   Settings: {Settings.query.count()}")
            
            print("\nSUCCESS: Database setup complete!")
            print("\nNext steps:")
            print("1. Test database connection")
            print("2. Import reviews to specific products")
            print("3. Test widget with product-specific reviews")
            
    except Exception as e:
        print(f"ERROR: Database setup failed: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Make sure PostgreSQL is running")
        print("2. Check database URL: postgresql://user:pass@host:port/database")
        print("3. Create database: createdb reviewking")
        raise

def test_database_connection():
    """
    Test database connection
    """
    try:
        with app.app_context():
            # Test basic query
            shops = Shop.query.limit(1).all()
            print("SUCCESS: Database connection successful!")
            return True
    except Exception as e:
        print(f"ERROR: Database connection failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing database connection...")
    try:
        with app.app_context():
            # Test basic connection (don't query tables yet)
            with db.engine.connect() as conn:
                conn.execute(db.text('SELECT 1'))
            print("SUCCESS: Database connection successful!")
            setup_database()
    except Exception as e:
        print(f"ERROR: Database connection failed: {str(e)}")
        print("\nPlease fix database connection first:")
        print("1. Install PostgreSQL")
        print("2. Create database: createdb reviewking")
        print("3. Set DATABASE_URL environment variable")
        print("4. Systematic troubleshooting:")
        print("   - Check if PostgreSQL is running")
        print("   - Verify database URL format")
        print("   - Ensure database exists")
        print("   - Check network connectivity to EasyPanel")
