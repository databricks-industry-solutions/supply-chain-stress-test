#!/usr/bin/env python3
"""
LangGraph Checkpoint Schema Setup Script

This script sets up the database schema for LangGraph checkpointing functionality.
It creates the necessary tables and indexes for storing checkpoint data.
Run this as the database owner to configure the checkpoint schema for the application.
"""

import os
import sys
import uuid
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv
from databricks.sdk import WorkspaceClient

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_schema_name():
    """Get the schema name from environment variable with fallback"""
    return os.getenv('SCHEMA_NAME', 'chatbot_schema')

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

def setup_checkpoint_schema():
    """Set up the checkpoint schema with LangGraph tables"""
    engine = get_database_connection(use_sp=True)
    if not engine:
        return False
    
    schema_name = get_schema_name()
    print(f"🔧 Setting up LangGraph checkpoint schema in {schema_name}...")
    client_id = os.getenv("CLIENT_ID")
    
    # 1. Ensure schema exists
    print("📋 Ensuring schema exists...")
    try:
        with engine.connect() as conn:
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
            conn.commit()
            print("✅ Schema verified")
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
    
    # 3. Set up LangGraph checkpoint tables
    print("🏗️ Setting up LangGraph checkpoint tables...")
    try:
        # Import psycopg and PostgresSaver
        import psycopg
        from langgraph.checkpoint.postgres import PostgresSaver
        
        # Get database connection details for psycopg
        username = os.getenv("CLIENT_ID")
        instance_name = os.getenv("DB_INSTANCE_NAME")
        
        # Get Databricks workspace client
        w = WorkspaceClient(
            host=os.getenv("DATABRICKS_HOST"), 
            client_id=os.getenv("CLIENT_ID"), 
            client_secret=os.getenv("CLIENT_SECRET")
        )
        
        # Get database instance details
        instance = w.database.get_database_instance(name=instance_name)
        host = instance.read_write_dns
        
        # Get access token for database authentication
        cred = w.database.generate_database_credential(request_id=str(uuid.uuid4()), instance_names=[instance_name])
        pgpassword = cred.token
        
        # Format username for connection
        if "@" in username:
            username = username.replace("@", "%40")
        
        # Create psycopg connection
        conn_string = f"postgresql://{username}:{pgpassword}@{host}:5432/databricks_postgres"
        
        # Connect with autocommit and dict row factory
        conn = psycopg.connect(
            conn_string,
            autocommit=True,
            row_factory=psycopg.rows.dict_row,
        )
        
        # Set search path to our schema
        with conn.cursor() as cur:
            cur.execute(f"SET search_path TO {schema_name}")
        
        # Create the PostgresSaver with connection
        checkpointer = PostgresSaver(conn)
        
        # This call runs migrations and ensures required tables exist
        checkpointer.setup()
        
        print("✅ LangGraph checkpoint tables created successfully")
        
        # Close connection
        conn.close()
        
    except ImportError as e:
        print(f"❌ Missing required packages: {e}")
        print("Please install: pip install psycopg[binary] langgraph")
        return False
    except Exception as e:
        print(f"❌ Error setting up checkpoint tables: {e}")
        return False
    
    print("✅ Checkpoint schema setup completed successfully!")
    return True

def verify_checkpoint_schema():
    """Verify that the checkpoint schema was created correctly"""
    engine = get_database_connection(use_sp=True)
    if not engine:
        return False
    
    schema_name = get_schema_name()
    
    try:
        with engine.connect() as conn:
            print("🔍 Verifying checkpoint schema setup...")
            
            # Check if schema exists
            schema_exists = conn.execute(text(f"SELECT 1 FROM information_schema.schemata WHERE schema_name = '{schema_name}'")).fetchone()
            print(f"✅ Schema exists: {bool(schema_exists)}")
            
            if not schema_exists:
                return False
            
            # Check for LangGraph checkpoint tables
            checkpoint_tables = [
                'checkpoints',
                'checkpoint_writes',
                'checkpoint_blobs'
            ]
            
            tables_exist = {}
            for table in checkpoint_tables:
                table_exists = conn.execute(text(f"""
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = '{schema_name}' AND table_name = '{table}'
                """)).fetchone()
                tables_exist[table] = bool(table_exists)
                print(f"✅ Table '{table}' exists: {bool(table_exists)}")
            
            all_tables_exist = all(tables_exist.values())
            
            if all_tables_exist:
                print("✅ All checkpoint tables verified")
            else:
                print("⚠️ Some checkpoint tables are missing")
            
            return all_tables_exist
            
    except SQLAlchemyError as e:
        print(f"❌ Verification failed: {e}")
        return False

def list_checkpoint_tables():
    """List all tables in the checkpoint schema"""
    engine = get_database_connection(use_sp=True)
    if not engine:
        return False
    
    schema_name = get_schema_name()
    
    try:
        with engine.connect() as conn:
            print(f"📋 Tables in schema '{schema_name}':")
            
            # Get all tables in the schema
            tables = conn.execute(text(f"""
                SELECT table_name, table_type 
                FROM information_schema.tables 
                WHERE table_schema = '{schema_name}'
                ORDER BY table_name
            """)).fetchall()
            
            if tables:
                for table in tables:
                    print(f"  - {table[0]} ({table[1]})")
            else:
                print("  No tables found")
            
            return True
            
    except SQLAlchemyError as e:
        print(f"❌ Error listing tables: {e}")
        return False

def main():
    """Main function to run checkpoint schema setup"""
    print("🚀 LangGraph Checkpoint Schema Setup")
    print("=" * 50)
    
    # Check environment variables
    required_vars = ['DATABRICKS_HOST', 'DB_INSTANCE_NAME', 'CLIENT_ID', 'CLIENT_SECRET']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please check your .env file")
        return False
    
    print("✅ Environment variables configured")
    
    # Check for SCHEMA_NAME (optional, defaults to chatbot_schema)
    schema_name = get_schema_name()
    print(f"📋 Using schema: {schema_name}")
    
    # Setup checkpoint schema
    if setup_checkpoint_schema():
        print("\n🔍 Verifying setup...")
        if verify_checkpoint_schema():
            print("\n🎉 Checkpoint schema setup completed successfully!")
            print("\n📝 Next steps:")
            print(f"1. LangGraph checkpoint tables are ready in {schema_name} schema")
            print("2. You can now use PostgresSaver for checkpointing in your LangGraph workflows")
            print("3. The checkpoint data will be stored in the following tables:")
            print("   - checkpoints: Main checkpoint storage")
            print("   - checkpoint_writes: Write operations tracking")
            print("   - checkpoint_blobs: Binary data storage")
            
            print("\n📋 Schema contents:")
            list_checkpoint_tables()
            
            return True
        else:
            print("\n❌ Checkpoint schema verification failed")
            return False
    else:
        print("\n❌ Checkpoint schema setup failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
