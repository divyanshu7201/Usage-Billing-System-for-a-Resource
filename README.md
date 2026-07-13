# Resource Usage & Billing System

A terminal-based Python application that connects to a local PostgreSQL database to manage checking in and checking out of shared resources (like meeting rooms, workstations, or gym treadmills), tracks capacities, and calculates billing amount based on time duration rules.

---

## 1. Assignment Overview & Guidelines

This project has been developed in strict accordance with the guidelines and deliverables specified in the assignment paper:

### General Guidelines Met:
* **Programming Language**: Developed using **Python 3** for maximum readability and clean logic.
* **No Frameworks or External Libraries**: Written in pure Python without using any business logic frameworks (like Flask, Django, FastAPI, or ORMs).
* **Database Implementation**: Built with a persistent **PostgreSQL** database backend (treated as a plus point in evaluation), utilizing the standard connection driver.
* **Data Model Design**: Relational table structure designed to reflect how enterprise database schemas are normalized.
* **Executable Deliverables**: Runnable via terminal/command line interface (`main.py`). A programmatic automated test suite is also provided (`test_system.py`).
* **Documentation**: Mandatory README file containing logic, data structures, and test scenarios.

---

## 2. Problem Statement & Rules

The system manages shared facilities with limited concurrent capacities where users must be charged based on duration of usage. 

### Seeded Facilities & Rules:
1. **Meeting Room A** (Capacity: 2 | First Hour: INR 30 | Addl. Hour: INR 10)
2. **Gym Treadmill** (Capacity: 1 | First Hour: INR 50 | Addl. Hour: INR 20)
3. **Dedicated Workstation** (Capacity: 5 | First Hour: INR 25 | Addl. Hour: INR 15)

### Core Logic Rules:
* **Capacity Limit**: If a resource is occupied up to its maximum capacity, any check-in request is rejected.
* **Occupancy Release**: When usage is stopped, the resource slot is freed immediately.
* **Billing Round-up Rule**: Any usage beyond a full hour is rounded up to the next complete hour (e.g., 1 hour 20 minutes rounds up to 2 hours).
* **Minimum Billing**: If a session is shorter than 1 hour, it is charged at the rate of exactly 1 hour.
* **Pricing Formula**: `total_amount = first_hour_rate + (rounded_hours - 1) * additional_hour_rate` (if `rounded_hours >= 1`).

---

## 3. Design & Architecture

The project is structured into four main files:
* **`models.py`**: Contains python classes (`Resource`, `Service`, `Usage`, `Bill`) mapping to the database table records.
* **`database.py`**: Handles connection configurations, schema creation, database auto-creation on startup, and pre-seeding catalog items.
* **`billing_system.py`**: Handles business transactions (occupancy increment, concurrency checks, stop checks, and duration calculations).
* **`main.py`**: The console interface that shows the menus and captures inputs.

---

## 4. Logic & Approach

The core transactional flow operates under standard ACID properties to ensure database consistency:

### A. Start Usage (Check-in)
1. **Concurrency Lock**: Select and lock the resource row using `SELECT ... FOR UPDATE` to block concurrent check-in queries from reading stale capacity counts.
2. **Validation**: Check if the selected resource is within its capacity limits (`current_occupancy < capacity`). If full, roll back and reject the check-in.
3. **Database Write**: Update the resource table to increment occupancy, insert an active usage record with start timestamp, and commit the transaction.

### B. Stop Usage & Billing (Check-out)
1. **Invoice Calculations**:
   - Calculate total elapsed time.
   - Round up any partial hour to the next full hour (e.g. 1 hour 20 minutes rounds to 2 hours) using `math.ceil()`.
   - Charge the base `first_hour_rate`, and add `additional_hour_rate` for each additional rounded hour. If duration is under 1 hour, charge a minimum of 1 hour.
2. **Database Write**: Lock the active usage record, update status to `COMPLETED` with stop timestamp, decrement resource active occupancy (freeing the slot), write the final bill, and commit the transaction.

---

## 5. Database Schema

The database consists of the following tables:
- **`resources`**: Stores ID, name, capacity, and current active occupancy count.
- **`services`**: Stores service packages with rates (first hour vs additional hour costs).
- **`usages`**: Stores active or completed check-in transactions.
- **`bills`**: Stores generated invoices.

---

## 6. Data Structures Used

### A. Python (In-Memory) Structures
- **Custom Classes**: `Resource`, `Service`, `Usage`, and `Bill` serve as clean data container classes to map SQL query result tuples into Python objects with named properties.
- **Lists**: Used to hold collections of objects returned from database queries (e.g. lists of catalog resources, active sessions, and billing records).
- **Tuples**: Read-only sequences returned natively by `psycopg2` query results (like `cursor.fetchone()` or `cursor.fetchall()`) which are unpacked to populate objects.
- **Dictionaries**: Used to load settings from `db_config.json` and represent serialized models through `.to_dict()`.
- **Datetime Objects**: `datetime.datetime` is used to represent timestamps and calculate time differences.

### B. Relational Database Structures
- **Relational Tables**: Grid structures with rows and columns mapped to database tables.
- **Primary Keys**: Auto-incrementing `SERIAL` integer identifiers for unique row matching.
- **Foreign Keys**: Pointers mapping relationships between tables (e.g. `usages.resource_id` references `resources.id`) to enforce data integrity.

---

## 7. Setup & Configuration

### Prerequisites
- Python 3 installed.
- install PostgreSQL database connector `psycopg2-binary`:
  ```bash
  pip install psycopg2-binary
  ```
- PostgreSQL running locally.

### Config Connection
Open the file `db_config.json` in the root folder and set your database connection parameters:
```json
{
  "host": "localhost",
  "port": 5432,
  "database": "BillingSystem",
  "user": "postgres",
  "password": "YOUR_POSTGRESQL_PASSWORD"
}
```

---

## 8. How to Run & Test

Execute the script in the terminal:
```bash
python main.py
```
*(On start, it checks if the database `BillingSystem` exists, creates it if not, builds the tables, and seeds the catalog if the tables are empty.)*

### Step-by-Step Scenario Verification

#### Scenario A: Billing duration rounding check (1 hour 20 minutes)
1. Select Option **2** (Start Resource Usage).
2. Choose Resource `1` (Meeting Room A) and Service `1` (Hourly Meeting Room Booking).
3. Set Name as `Alice`.
4. Choose Option **2** (Manual Time) for start time and enter `10:00`.
5. Select Option **3** (Stop Resource Usage & Generate Bill) for Usage ID `1`.
6. Select Option **2** (Manual Time) for stop time and enter `11:20`.
7. **Expected Result**: 80 minutes total duration. Billed as 2 hours (1 hr 20 min rounded up). Total invoice is **INR 40** (30 first hour + 10 additional hour).

#### Scenario B: Capacity restriction check
1. Select Option **2** to start usage on Gym Treadmill (Resource `2`, capacity is 1). Set Name as `John`.
2. Try starting another usage session on Resource `2` again.
3. **Expected Result**: System rejects immediately because the active capacity slot is full:
   `[ERROR/REJECTED] Cannot start usage. Capacity for 'Gym Treadmill' is already full.`
4. Check out John using Option **3** to free up the slot.

---

## 9. Web UI Extension (Added Advantage Design)

As highlighted in the guidelines, building a user interface is an optional addition that provides a **major advantage during evaluation**. To keep the project 100% compliant with the **"no external frameworks or libraries"** rule, a Web UI architecture can be implemented using only Python standard libraries:

### Architecture:
1. **API Server Backend**: A lightweight REST API server built using Python's native **`http.server.BaseHTTPRequestHandler`** (part of Python's standard library). It hosts API endpoints and routes GET/POST payloads as JSON.
2. **Frontend Dashboard**: A responsive single-page web dashboard built using standard vanilla **HTML5**, **CSS3**, and browser-native **JavaScript**. No external frameworks (like React, Vue, or Angular) or styling packages are required.

### Exposed Standard API Endpoints:
* `GET /api/resources`: Retrieves all seeded catalog resources, capacities, and rates.
* `GET /api/usages`: Retrieves all active check-in sessions.
* `GET /api/history`: Retrieves billing transaction history logs.
* `POST /api/usages/start`: Takes a JSON body (`{"resource_id": int, "service_id": int, "user_name": str, "start_time": str}`) to begin occupancy.
* `POST /api/usages/stop`: Takes a JSON body (`{"usage_id": int, "end_time": str}`) to compute the bill, release the slot, and return the invoice details.

This design showcases that a modern web system can be written completely from scratch without importing external library code.
