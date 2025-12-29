"""
Create contact_messages table for storing contact form submissions
Run this once to add the table to your database
"""
import os
import sys
from flask import Flask
from backend.models_v2 import db, ContactMessage

# Create Flask app
app = Flask(__name__)

# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://saksaks:11!!!!.Magics4321@193.203.165.217:5432/sakrev_db?sslmode=disable')
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

def create_contact_messages_table():
    """Create the contact_messages table"""
    with app.app_context():
        try:
            # Create table
            db.create_all()
            print("✅ Contact messages table created successfully!")
            
            # Verify table exists
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'contact_messages' in tables:
                print("✅ Verified: contact_messages table exists")
                return True
            else:
                print("❌ Error: contact_messages table not found")
                return False
                
        except Exception as e:
            print(f"❌ Error creating table: {str(e)}")
            return False

if __name__ == '__main__':
    print("Creating contact_messages table...")
    success = create_contact_messages_table()
    sys.exit(0 if success else 1)

