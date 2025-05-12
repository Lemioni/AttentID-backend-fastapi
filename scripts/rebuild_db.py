import os
import sys
import subprocess
import psycopg2

# Add parent directory to path so we can import from app
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from app.core.database import settings

def main():
    print("Starting database rebuild...")
    
    # Connect to PostgreSQL
    print("Connecting to PostgreSQL...")
    conn_string = settings.database_url
    
    # Extract server connection parameters (without DB name)
    conn_parts = conn_string.split('/')
    server_conn = '/'.join(conn_parts[:-1]) + '/postgres'
    db_name = conn_parts[-1]
    
    try:
        # Connect to postgres DB to be able to drop/create the target DB
        conn = psycopg2.connect(server_conn)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Drop the database if it exists
        print(f"Dropping database if it exists: {db_name}")
        cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")
        
        # Create the database
        print(f"Creating database: {db_name}")
        cursor.execute(f"CREATE DATABASE {db_name}")
        
        # Close connection to server
        cursor.close()
        conn.close()
        
        # Connect to the newly created database
        print(f"Connecting to database: {db_name}")
        conn = psycopg2.connect(conn_string)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Read and execute the SQL file
        print("Executing SQL script...")
        with open(os.path.join(parent_dir, 'migrations', 'create_tables.sql'), 'r') as f:
            sql_script = f.read()
            cursor.execute(sql_script)
        
        # Close connection
        cursor.close()
        conn.close()
        
        print("Database rebuild completed successfully!")
        
    except Exception as e:
        print(f"Error rebuilding database: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()