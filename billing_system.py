import math
import datetime
from database import get_db_connection
from models import Usage, Bill

def start_usage(resource_id: int, service_id: int, user_name: str, start_time: datetime.datetime) -> Usage:
    # Starts using a resource and checks constraints
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Check capacity and lock row to prevent double booking
            cursor.execute(
                "SELECT name, capacity, current_occupancy FROM resources WHERE id = %s FOR UPDATE;",
                (resource_id,)
            )
            res_row = cursor.fetchone()
            if not res_row:
                raise ValueError(f"Resource with ID {resource_id} does not exist.")
            res_name, capacity, current_occupancy = res_row

            # Get service details
            cursor.execute(
                "SELECT resource_id, name FROM services WHERE id = %s;",
                (service_id,)
            )
            svc_row = cursor.fetchone()
            if not svc_row:
                raise ValueError(f"Service with ID {service_id} does not exist.")
            svc_resource_id, svc_name = svc_row

            if svc_resource_id != resource_id:
                raise ValueError(f"Service '{svc_name}' does not belong to resource '{res_name}'.")

            # Check capacity
            if current_occupancy >= capacity:
                raise ValueError(f"Cannot start usage. Capacity for '{res_name}' is already full.")

            # Increment active occupancy
            cursor.execute(
                "UPDATE resources SET current_occupancy = current_occupancy + 1 WHERE id = %s;",
                (resource_id,)
            )

            # Insert usage record
            cursor.execute(
                """
                INSERT INTO usages (resource_id, service_id, user_name, start_time, status)
                VALUES (%s, %s, %s, %s, 'ACTIVE')
                RETURNING id;
                """,
                (resource_id, service_id, user_name, start_time)
            )
            usage_id = cursor.fetchone()[0]

        conn.commit()
        return Usage(usage_id, resource_id, service_id, user_name, start_time, None, "ACTIVE")
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def stop_usage(usage_id: int, end_time: datetime.datetime) -> Bill:
    # Stops usage session, updates capacity, and calculates bill
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Lock usage session row
            cursor.execute(
                """
                SELECT u.resource_id, u.service_id, u.user_name, u.start_time, u.status, r.name
                FROM usages u
                JOIN resources r ON u.resource_id = r.id
                WHERE u.id = %s FOR UPDATE;
                """,
                (usage_id,)
            )
            usage_row = cursor.fetchone()
            if not usage_row:
                raise ValueError(f"Usage session with ID {usage_id} does not exist.")
            
            res_id, svc_id, user_name, start_time, status, res_name = usage_row

            if status != "ACTIVE":
                raise ValueError(f"Usage session {usage_id} is already stopped.")

            if end_time < start_time:
                raise ValueError("End time cannot be earlier than start time.")

            # Get pricing rules
            cursor.execute(
                "SELECT first_hour_rate, additional_hour_rate FROM services WHERE id = %s;",
                (svc_id,)
            )
            svc_row = cursor.fetchone()
            if not svc_row:
                raise ValueError(f"Service pricing rules not found for service ID {svc_id}.")
            first_hour_rate, additional_hour_rate = svc_row

            # Calculate times
            duration_seconds = (end_time - start_time).total_seconds()
            total_minutes = int(math.ceil(duration_seconds / 60.0))

            rounded_hours = int(math.ceil(duration_seconds / 3600.0))
            if rounded_hours <= 0:
                rounded_hours = 1  # 1 hour minimum

            # Calculate total amount
            total_amount = first_hour_rate
            if rounded_hours > 1:
                total_amount += (rounded_hours - 1) * additional_hour_rate

            # Complete usage session
            cursor.execute(
                "UPDATE usages SET end_time = %s, status = 'COMPLETED' WHERE id = %s;",
                (end_time, usage_id)
            )

            # Decrement active slots
            cursor.execute(
                "UPDATE resources SET current_occupancy = current_occupancy - 1 WHERE id = %s;",
                (res_id,)
            )

            # Create bill log
            cursor.execute(
                """
                INSERT INTO bills (usage_id, user_name, resource_name, start_time, end_time,
                                   total_duration_minutes, rounded_hours, total_amount)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (usage_id, user_name, res_name, start_time, end_time,
                 total_minutes, rounded_hours, total_amount)
            )
            bill_id = cursor.fetchone()[0]

        conn.commit()
        return Bill(bill_id, usage_id, user_name, res_name, start_time, end_time,
                    total_minutes, rounded_hours, total_amount)
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
