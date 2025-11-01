#!/usr/bin/env python3
"""
Connect to Easypanel PostgreSQL Database
"""
import psycopg2
import pandas as pd
from sqlalchemy import create_engine
import sys

# Database connection details
DB_CONFIG = {
    'host': '193.203.165.217',
    'port': 5432,
    'database': 'sakrev_db',
    'user': 'saksaks',
    'password': '11!!!!.Magics4321'
}

def test_connection():
    """Test basic connection to the database"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("SUCCESS: Connected to Easypanel PostgreSQL!")
        
        # Get database info
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"PostgreSQL Version: {version[0]}")
        
        # List all tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public';
        """)
        tables = cursor.fetchall()
        
        if tables:
            print(f"\nFound {len(tables)} tables:")
            for table in tables:
                print(f"  - {table[0]}")
        else:
            print("\nNo tables found in the database")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"ERROR: Connection failed: {e}")
        return False

def explore_tables():
    """Explore the structure of tables"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public';
        """)
        tables = cursor.fetchall()
        
        for table in tables:
            table_name = table[0]
            print(f"\nTable: {table_name}")
            
            # Get column information
            cursor.execute(f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position;
            """)
            columns = cursor.fetchall()
            
            for col in columns:
                nullable = "NULL" if col[2] == "YES" else "NOT NULL"
                print(f"  - {col[0]} ({col[1]}) {nullable}")
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            count = cursor.fetchone()[0]
            print(f"  Rows: {count}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"ERROR: Error exploring tables: {e}")

def query_data(table_name, limit=10):
    """Query data from a specific table"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        
        # Use pandas for better data display
        engine = create_engine(f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
        
        query = f"SELECT * FROM {table_name} LIMIT {limit};"
        df = pd.read_sql(query, engine)
        
        print(f"\nData from {table_name} (first {limit} rows):")
        print(df.to_string(index=False))
        
        conn.close()
        
    except Exception as e:
        print(f"ERROR: Error querying {table_name}: {e}")

if __name__ == "__main__":
    print("Connecting to Easypanel Sakura Reviews Database...")
    print("=" * 60)
    
    if test_connection():
        print("\n" + "=" * 60)
        explore_tables()
        
        # If you want to query specific data, uncomment and modify:
        # query_data("your_table_name", limit=5)
