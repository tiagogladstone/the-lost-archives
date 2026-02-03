import os
import supabase
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def setup_database():
    """
    Connects to Supabase and executes the schema.sql file to set up the database tables.
    """
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL and SUPABASE_KEY environment variables are required.")
        return

    try:
        # Initialize the Supabase client
        client = supabase.create_client(supabase_url, supabase_key)
        print("Successfully connected to Supabase.")

        # Read the schema.sql file
        try:
            with open("database/schema.sql", "r") as f:
                schema_sql = f.read()
            print("Successfully read schema.sql file.")
        except FileNotFoundError:
            print("Error: database/schema.sql not found.")
            return

        # Execute the SQL schema
        # The supabase-py library doesn't have a direct way to execute raw multi-statement SQL.
        # A common approach is to use the PostgREST API via rpc() for functions,
        # but for initial setup, it's often easier to run this SQL directly in the Supabase dashboard's SQL Editor.
        # This script serves as a way to automate it if you have direct DB connection tools,
        # or as a clear reference for the setup process.

        # For automation, you'd typically use a library like psycopg2.
        # This script will print the SQL and instructions instead of executing it directly
        # to avoid adding more dependencies and requiring direct DB connection strings.

        print("\n--- Supabase Setup Script ---")
        print("This script helps initialize your database schema.")
        print("Please execute the following SQL in your Supabase project's SQL Editor.")
        print("Navigate to: Dashboard -> SQL Editor -> New Query")
        print("--------------------------------------------------")
        print(schema_sql)
        print("--------------------------------------------------")

        # Example of how you would run it with a direct DB connection (e.g., using psycopg2)
        # conn = psycopg2.connect(database_url)
        # cur = conn.cursor()
        # cur.execute(schema_sql)
        # conn.commit()
        # cur.close()
        # conn.close()
        # print("Schema successfully applied to the database.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    setup_database()
