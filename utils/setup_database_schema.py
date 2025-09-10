#!/usr/bin/env python3
"""
Database Schema Setup Script

This script sets up the chatbot_schema with proper PostgreSQL roles and permissions.
Run this as the database owner to configure the schema for the application.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_database_connection(use_sp=True):
    """Get database connection using environment variables"""
    try:
        import sys
        sys.path.append('.')
        from utils.chat_database import build_db_uri
        
        username = os.getenv("CLIENT_ID")
        instance_name = os.getenv("DB_INSTANCE_NAME")
        
        if not username or not instance_name:
            print("❌ Error: CLIENT_ID and DB_INSTANCE_NAME must be set in .env file")
            return None
            
        db_uri = build_db_uri(username, instance_name, use_sp=use_sp)
        engine = create_engine(db_uri)
        return engine
        
    except Exception as e:
        print(f"❌ Error creating database connection: {e}")
        return None

def setup_schema():
    """Set up the schema with proper roles and permissions"""
    engine = get_database_connection(use_sp=False)
    if not engine:
        return False
    
    schema_name = os.getenv("SCHEMA_NAME", "chatbot_schema")
    print(f"🔧 Setting up {schema_name}...")
    client_id = os.getenv("CLIENT_ID")
    
    # 1. Create schema
    print("📋 Creating schema...")
    try:
        with engine.connect() as conn:
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
            conn.commit()
            print("✅ Schema created")
    except SQLAlchemyError as e:
        print(f"❌ Error creating schema: {e}")
        return False
    
    # 2. Grant permissions to CLIENT_ID
    print(f"🔑 Granting permissions to {client_id}...")
    try:
        with engine.connect() as conn:
            conn.execute(text(f'GRANT USAGE, CREATE ON SCHEMA {schema_name} TO "{client_id}"'))
            conn.commit()
            print(f"✅ Permissions granted to {client_id}")
    except SQLAlchemyError as e:
        print(f"⚠️ Error granting permissions: {e}")
    
    # 3. Create and configure chatbot_app role
    print("👤 Setting up chatbot_app role...")
    try:
        with engine.connect() as conn:
            # Create role
            conn.execute(text("CREATE ROLE chatbot_app NOLOGIN"))
            # Grant to CLIENT_ID
            conn.execute(text(f'GRANT chatbot_app TO "{client_id}"'))
            # Grant permissions
            conn.execute(text(f"GRANT USAGE, CREATE ON SCHEMA {schema_name} TO chatbot_app"))
            conn.commit()
            print("✅ chatbot_app role configured")
    except SQLAlchemyError as e:
        if "already exists" in str(e).lower():
            print("✅ chatbot_app role already exists")
        else:
            print(f"⚠️ Role setup skipped: {e}")
    
    print("✅ Schema setup completed successfully!")
    return True

def verify_schema():
    """Verify that the schema was created correctly"""
    engine = get_database_connection(use_sp=True)
    if not engine:
        return False
    
    schema_name = os.getenv("SCHEMA_NAME", "chatbot_schema")
    
    try:
        with engine.connect() as conn:
            print("🔍 Verifying schema setup...")
            
            # Check schema and role existence
            schema_exists = conn.execute(text(f"SELECT 1 FROM information_schema.schemata WHERE schema_name = '{schema_name}'")).fetchone()
            role_exists = conn.execute(text("SELECT 1 FROM pg_roles WHERE rolname = 'chatbot_app'")).fetchone()
            
            print(f"✅ Schema exists: {bool(schema_exists)}")
            print(f"✅ Role exists: {bool(role_exists)}")
            
            return bool(schema_exists and role_exists)
            
    except SQLAlchemyError as e:
        print(f"❌ Verification failed: {e}")
        return False

def main():
    """Main function to run schema setup"""
    print("🚀 Database Schema Setup")
    print("=" * 50)
    
    # Check environment variables
    required_vars = ['DATABRICKS_HOST', 'DB_INSTANCE_NAME', 'CLIENT_ID', 'CLIENT_SECRET']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    # Check for SCHEMA_NAME (optional, defaults to chatbot_schema)
    schema_name = os.getenv("SCHEMA_NAME", "chatbot_schema")
    print(f"📋 Using schema: {schema_name}")
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please check your .env file")
        return False
    
    print("✅ Environment variables configured")
    
    # Setup schema
    if setup_schema():
        print("\n🔍 Verifying setup...")
        if verify_schema():
            print("\n🎉 Schema setup completed successfully!")
            print("\n📝 Next steps:")
            print(f"1. The application can now use the {schema_name} schema")
            print("2. Tables will be created automatically when the app starts")
            print("3. The app will use the chatbot_app role for operations")
            return True
        else:
            print("\n❌ Schema verification failed")
            return False
    else:
        print("\n❌ Schema setup failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 