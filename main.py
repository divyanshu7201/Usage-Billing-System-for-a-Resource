import sys
import datetime
import math
import psycopg2
from database import initialize_db, get_db_connection
import billing_system

def print_header(title: str):
    print("\n" + "=" * 50)
    print(f" {title.upper()} ".center(50, "="))
    print("=" * 50)


def display_resources():
    print_header("Resources & Services Catalog")
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, name, capacity, current_occupancy FROM resources ORDER BY id;")
            resources = cursor.fetchall()
            for r_id, name, capacity, occupancy in resources:
                print(f"\nResource ID: {r_id} | Name: {name}")
                print(f"Capacity: {capacity} | Current Occupancy: {occupancy} | Available: {capacity - occupancy}")
                
                cursor.execute(
                    "SELECT id, name, first_hour_rate, additional_hour_rate FROM services WHERE resource_id = %s ORDER BY id;",
                    (r_id,)
                )
                services = cursor.fetchall()
                print("  Available Services & Pricing (INR):")
                for s_id, s_name, first_rate, addl_rate in services:
                    print(f"    - [{s_id}] {s_name}:")
                    print(f"      First Hour: INR {first_rate} | Each Addl. Hour: INR {addl_rate}")
    except Exception as e:
        print(f"Error fetching resources: {e}")
    finally:
        conn.close()
    print("-" * 50)


def display_active_usages():
    print_header("Active Usage Sessions")
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT u.id, u.user_name, r.name, s.name, u.start_time
                FROM usages u
                JOIN resources r ON u.resource_id = r.id
                JOIN services s ON u.service_id = s.id
                WHERE u.status = 'ACTIVE'
                ORDER BY u.id;
                """
            )
            active = cursor.fetchall()
            if not active:
                print("No active sessions currently running.")
                print("-" * 50)
                return

            for idx, (u_id, user_name, res_name, svc_name, start_time) in enumerate(active, 1):
                print(f"{idx}. Usage ID: {u_id}")
                print(f"   User Name: {user_name}")
                print(f"   Resource: {res_name}")
                print(f"   Service: {svc_name}")
                print(f"   Started At: {start_time.strftime('%I:%M %p')} (Today)")
    except Exception as e:
        print(f"Error fetching active sessions: {e}")
    finally:
        conn.close()
    print("-" * 50)


def display_billing_history():
    print_header("Generated Bills (Billing History)")
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, usage_id, user_name, resource_name, start_time, end_time,
                       total_duration_minutes, rounded_hours, total_amount
                FROM bills
                ORDER BY id;
                """
            )
            bills = cursor.fetchall()
            if not bills:
                print("No bills generated yet.")
                print("-" * 50)
                return

            for b_id, u_id, user_name, res_name, start_time, end_time, duration, rounded, amount in bills:
                print(f"\nBill ID: {b_id} | Usage ID: {u_id}")
                print(f"User: {user_name} | Resource: {res_name}")
                print(f"Duration: {start_time.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p')}")
                print(f"Total Time: {duration} minutes ({rounded} rounded hour(s))")
                print(f"Total Amount Charged: INR {amount}")
    except Exception as e:
        print(f"Error fetching billing history: {e}")
    finally:
        conn.close()
    print("-" * 50)


def prompt_for_time(prompt_label: str) -> datetime.datetime:
    # Prompt the user to select either current system time or input manual time
    print(f"\nTime selection for: {prompt_label}")
    print("1. Use Current System Time")
    print("2. Enter Manual Time (HH:MM, 24-Hour Format)")
    
    while True:
        choice = input("Select option (1 or 2): ").strip()
        if choice == "1":
            return datetime.datetime.now()
        elif choice == "2":
            while True:
                time_str = input("Enter time (e.g. 10:00 or 15:30): ").strip()
                try:
                    parts = time_str.split(":")
                    if len(parts) != 2:
                        raise ValueError
                    h, m = int(parts[0]), int(parts[1])
                    if not (0 <= h <= 23 and 0 <= m <= 59):
                        raise ValueError
                    # Combine with current date
                    today = datetime.datetime.now().date()
                    return datetime.datetime(today.year, today.month, today.day, h, m)
                except ValueError:
                    print("Invalid time format. Please enter as HH:MM (e.g., 09:15 or 14:00).")
        else:
            print("Invalid choice. Please enter 1 or 2.")


def handle_start_usage():
    print_header("Start Resource Usage")
    
    # Show available resources
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, name, capacity, current_occupancy FROM resources ORDER BY id;")
            resources = cursor.fetchall()
            print("Available Resources:")
            for r_id, name, capacity, occupancy in resources:
                print(f"  - [{r_id}] {name} (Capacity: {capacity}, Available Slots: {capacity - occupancy})")
    except Exception as e:
        print(f"Error displaying resources: {e}")
        conn.close()
        return
    finally:
        conn.close()

    try:
        res_id = int(input("\nEnter Resource ID (number, e.g. 1): ").strip())
    except ValueError:
        print("Error: Resource ID must be a number.")
        return

    # Show services for selected resource
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, name, first_hour_rate, additional_hour_rate FROM services WHERE resource_id = %s ORDER BY id;", (res_id,))
            services = cursor.fetchall()
            if not services:
                print("Error: No services found for this Resource ID.")
                return
            
            print("\nAvailable Services:")
            for s_id, s_name, first_rate, addl_rate in services:
                print(f"  - [{s_id}] {s_name} (1st Hour: INR {first_rate}, Addl Hour: INR {addl_rate})")
    except Exception as e:
        print(f"Error: {e}")
        return
    finally:
        conn.close()

    try:
        svc_id = int(input("\nEnter Service ID (number, e.g. 1): ").strip())
    except ValueError:
        print("Error: Service ID must be a number.")
        return

    user_name = input("\nEnter User Name: ").strip()
    if not user_name:
        print("Error: User Name cannot be empty.")
        return

    start_time = prompt_for_time("START TIME")

    try:
        usage = billing_system.start_usage(res_id, svc_id, user_name, start_time)
        print(f"\n[SUCCESS] Usage started successfully!")
        print(f"Usage ID: {usage.id}")
        print(f"User: {usage.user_name}")
        print(f"Start Time: {usage.start_time.strftime('%I:%M %p')}")
    except ValueError as e:
        print(f"\n[ERROR/REJECTED] {e}")
    except Exception as e:
        print(f"\n[SYSTEM ERROR] {e}")


def handle_stop_usage():
    print_header("Stop Resource Usage & Generate Bill")
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT u.id, u.user_name, r.name, u.start_time
                FROM usages u
                JOIN resources r ON u.resource_id = r.id
                WHERE u.status = 'ACTIVE'
                ORDER BY u.id;
                """
            )
            active = cursor.fetchall()
            if not active:
                print("No active usage sessions to stop.")
                return
            
            print("Active Usage Sessions:")
            for u_id, user_name, res_name, start_time in active:
                print(f"  - [{u_id}] User: {user_name} | Resource: {res_name} | Started At: {start_time.strftime('%I:%M %p')}")
    except Exception as e:
        print(f"Error: {e}")
        return
    finally:
        conn.close()

    try:
        usage_id = int(input("\nEnter Usage ID to stop (number, e.g. 1): ").strip())
    except ValueError:
        print("Error: Usage ID must be a number.")
        return

    conn = get_db_connection()
    start_time = None
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT start_time, status FROM usages WHERE id = %s;", (usage_id,))
            row = cursor.fetchone()
            if not row:
                print("Error: Usage ID not found.")
                return
            if row[1] != 'ACTIVE':
                print("Error: This usage session is already stopped.")
                return
            start_time = row[0]
    except Exception as e:
        print(f"Error: {e}")
        return
    finally:
        conn.close()

    while True:
        end_time = prompt_for_time("STOP TIME")
        if end_time >= start_time:
            break
        print(f"Error: Stop time cannot be earlier than start time ({start_time.strftime('%I:%M %p')}). Please try again.")

    try:
        bill = billing_system.stop_usage(usage_id, end_time)
        print(f"\n[SUCCESS] Usage stopped. Bill generated successfully!")
        print(f"Bill ID: {bill.id}")
        print(f"User Name: {bill.user_name}")
        print(f"Resource: {bill.resource_name}")
        print(f"Usage Period: {bill.start_time.strftime('%I:%M %p')} - {bill.end_time.strftime('%I:%M %p')}")
        print(f"Total Duration: {bill.total_duration_minutes} minutes")
        print(f"Rounded Hours Billed: {bill.rounded_hours} hour(s)")
        print(f"Total Bill Amount: INR {bill.total_amount}")
    except ValueError as e:
        print(f"\n[ERROR] {e}")
    except Exception as e:
        print(f"\n[SYSTEM ERROR] {e}")


def main():
    try:
        initialize_db()
    except psycopg2.OperationalError as e:
        print("\n" + "!" * 60)
        print(" DATABASE CONNECTION ERROR ".center(60, "!"))
        print("!" * 60)
        print("Could not connect to the local PostgreSQL database server.")
        print(f"Details: {e}")
        print("\nACTION REQUIRED:")
        print("1. Make sure your local PostgreSQL service is running.")
        print("2. Verify/edit the credentials in 'db_config.json'.")
        print("!" * 60 + "\n")
        sys.exit(1)

    while True:
        print("\n" + "=" * 50)
        print("RESOURCE USAGE & BILLING SYSTEM".center(50))
        print("=" * 50)
        print("1. View Resources & Services Catalog")
        print("2. Start Resource Usage (Check-in)")
        print("3. Stop Resource Usage & Generate Bill (Check-out)")
        print("4. View Active Usage Sessions")
        print("5. View Billing History (All Bills)")
        print("6. Exit")
        print("=" * 50)
        
        choice = input("Enter your choice (1-6): ").strip()
        
        if choice == "1":
            display_resources()
        elif choice == "2":
            handle_start_usage()
        elif choice == "3":
            handle_stop_usage()
        elif choice == "4":
            display_active_usages()
        elif choice == "5":
            display_billing_history()
        elif choice == "6":
            print("\nThank you for using the Resource Usage & Billing System. Goodbye!")
            break
        else:
            print("\nInvalid choice! Please select an option between 1 and 6.")


if __name__ == "__main__":
    main()
