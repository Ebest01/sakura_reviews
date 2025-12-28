"""Create database tables for models_v2"""
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Initialize Flask app
app = Flask(__name__)

# Database configuration - EasyPanel PostgreSQL
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://saksaks:11!!!!.Magics4321@193.203.165.217:5432/sakrev_db?sslmode=disable')
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Import v2 models FIRST (they define their own db instance)
from backend.models_v2 import db, ShopOwner, Shop, Product, Review, ReviewMedia, Import, ShopSettings

# Initialize the models_v2 db instance with our app
db.init_app(app)

def setup_v2_database():
    """Create v2 database tables"""
    print("Setting up ReviewKing Database (v2 schema)...")
    print(f"Database URL: {DATABASE_URL.replace('11!!!!.Magics4321', '*****')}")
    
    try:
        with app.app_context():
            print("Creating v2 database tables...")
            db.create_all()
            print("SUCCESS: v2 tables created!")
            
            # Verify tables exist
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            required_tables = ['shop_owners', 'shops', 'products', 'reviews', 'review_media', 'imports', 'shop_settings']
            missing = [t for t in required_tables if t not in tables]
            
            if missing:
                print(f"WARNING: Missing tables: {missing}")
            else:
                print("SUCCESS: All required tables exist!")
            
            print("\nTables in database:")
            for table in sorted(tables):
                print(f"  - {table}")
                
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    setup_v2_database()

