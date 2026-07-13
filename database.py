import os
import json
import psycopg2

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "db_config.json")

def load_db_config():
    # Load database credentials from config file
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(f"Configuration file '{CONFIG_FILE}' not found.")
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def get_db_connection():
    # Establish connection to PG
    config = load_db_config()
    return psycopg2.connect(
        host=config.get("host", "localhost"),
        port=config.get("port", 5432),
        database=config.get("database", "postgres"),
        user=config.get("user", "postgres"),
        password=config.get("password", "")
    )


def ensure_database_exists():
    # Create the database if it does not exist
    config = load_db_config()
    target_db = config.get("database", "postgres")

    if target_db.lower() != "postgres":
        try:
            temp_conn = psycopg2.connect(
                host=config.get("host", "localhost"),
                port=config.get("port", 5432),
                database="postgres",
                user=config.get("user", "postgres"),
                password=config.get("password", "")
            )
            temp_conn.autocommit = True
            with temp_conn.cursor() as cursor:
                cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (target_db,))
                exists = cursor.fetchone()
                if not exists:
                    print(f"Creating database '{target_db}'...")
                    cursor.execute(f'CREATE DATABASE "{target_db}";')
            temp_conn.close()
        except Exception:
            pass


def initialize_db():
    # Create tables and seed initial catalog data if empty
    ensure_database_exists()
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Create Tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS resources (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    capacity INT NOT NULL,
                    current_occupancy INT NOT NULL DEFAULT 0
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS services (
                    id SERIAL PRIMARY KEY,
                    resource_id INT REFERENCES resources(id) ON DELETE CASCADE,
                    name VARCHAR(100) NOT NULL,
                    first_hour_rate INT NOT NULL,
                    additional_hour_rate INT NOT NULL
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usages (
                    id SERIAL PRIMARY KEY,
                    resource_id INT REFERENCES resources(id),
                    service_id INT REFERENCES services(id),
                    user_name VARCHAR(100) NOT NULL,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bills (
                    id SERIAL PRIMARY KEY,
                    usage_id INT REFERENCES usages(id),
                    user_name VARCHAR(100) NOT NULL,
                    resource_name VARCHAR(100) NOT NULL,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP NOT NULL,
                    total_duration_minutes INT NOT NULL,
                    rounded_hours INT NOT NULL,
                    total_amount INT NOT NULL
                );
            """)

            # Seed data
            cursor.execute("SELECT COUNT(*) FROM resources;")
            count = cursor.fetchone()[0]
            if count == 0:
                print("Seeding catalog...")
                cursor.execute(
                    "INSERT INTO resources (name, capacity) VALUES (%s, %s) RETURNING id;",
                    ("Meeting Room A", 2)
                )
                r1_id = cursor.fetchone()[0]

                cursor.execute(
                    "INSERT INTO resources (name, capacity) VALUES (%s, %s) RETURNING id;",
                    ("Gym Treadmill", 1)
                )
                r2_id = cursor.fetchone()[0]

                cursor.execute(
                    "INSERT INTO resources (name, capacity) VALUES (%s, %s) RETURNING id;",
                    ("Dedicated Workstation", 5)
                )
                r3_id = cursor.fetchone()[0]

                cursor.execute(
                    "INSERT INTO services (resource_id, name, first_hour_rate, additional_hour_rate) VALUES (%s, %s, %s, %s);",
                    (r1_id, "Hourly Meeting Room Booking", 30, 10)
                )
                cursor.execute(
                    "INSERT INTO services (resource_id, name, first_hour_rate, additional_hour_rate) VALUES (%s, %s, %s, %s);",
                    (r2_id, "Hourly Treadmill Access", 50, 20)
                )
                cursor.execute(
                    "INSERT INTO services (resource_id, name, first_hour_rate, additional_hour_rate) VALUES (%s, %s, %s, %s);",
                    (r3_id, "Hourly Workspace rental", 25, 15)
                )

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def reset_db_schema():
    # Helper to clean up database for tests
    ensure_database_exists()
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            print("Wiping existing database...")
            cursor.execute("DROP TABLE IF EXISTS bills CASCADE;")
            cursor.execute("DROP TABLE IF EXISTS usages CASCADE;")
            cursor.execute("DROP TABLE IF EXISTS services CASCADE;")
            cursor.execute("DROP TABLE IF EXISTS resources CASCADE;")
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

    initialize_db()
