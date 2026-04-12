"""
db.py
Manages the SQLite database connection, schema creation, and automatic data seeding.
This file acts as the data persistence layer for the Habit Tracker application.
"""

import sqlite3
from datetime import datetime, timedelta

# Step 1: Define the database name as a global variable.
# We do this so our pytest suite (in test_project.py) can dynamically 
# swap this out for a temporary file, ensuring tests don't ruin real user data.
DB_NAME = "main.db"

def get_db():
    """
    Returns a configured database connection.
    Enables dictionary-like row access and enforces foreign key constraints.
    """
    # Step 1: Connect to the database file (creates it if it doesn't exist)
    conn = sqlite3.connect(DB_NAME)
    
    # Step 2: Use Row factory so we can access columns by name (e.g., row['name'])
    conn.row_factory = sqlite3.Row
    
    # Step 3: SQLite disables foreign keys by default. We MUST enable them 
    # for our 'ON DELETE CASCADE' rule to work properly when deleting habits.
    conn.execute("PRAGMA foreign_keys = 1") 
    
    return conn

def create_tables():
    """
    Initializes the database schema (Tables: habit, tracker).
    Uses 'IF NOT EXISTS' to safely run on every startup without overwriting data.
    """
    conn = get_db()
    
    # Step 1: Create the parent 'habit' table
    # We use 'name' as the PRIMARY KEY since habit names must be unique.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS habit (
            name TEXT PRIMARY KEY,
            periodicity TEXT,
            created_at DATETIME
        )
    """)

    # Step 2: Create the child 'tracker' table for logging check-offs
    # The FOREIGN KEY links back to the habit table. 
    # 'ON DELETE CASCADE' means if a habit is deleted, all its tracking history is instantly wiped.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tracker (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_name TEXT,
            checkoff_date DATETIME,
            FOREIGN KEY (habit_name) REFERENCES habit(name) ON DELETE CASCADE
        )
    """)
    
    # Step 3: Save changes and close the connection
    conn.commit()
    conn.close()

def seed_data():
    """
    Populates the database with 5 predefined habits and 4 weeks (28 days) 
    of time-series check-off data to fulfill the portfolio testing requirements.
    """
    conn = get_db()
    cursor = conn.cursor()

    # Step 1: Check if the database already has data. 
    # If it does, we exit immediately so we don't mess up the user's actual habits.
    cursor.execute("SELECT COUNT(*) FROM habit")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return  
        
    print("Seeding database with 4 weeks of predefined data...")
    
    # Step 2: Insert 5 Predefined Habits, backdating their creation date to 28 days ago
    now = datetime.now()
    habits = [
        ("reading", "Daily", (now - timedelta(days=28)).strftime("%Y-%m-%d %H:%M:%S")),
        ("meditation", "Daily", (now - timedelta(days=28)).strftime("%Y-%m-%d %H:%M:%S")),
        ("coding", "Daily", (now - timedelta(days=28)).strftime("%Y-%m-%d %H:%M:%S")),
        ("gym", "Weekly", (now - timedelta(days=28)).strftime("%Y-%m-%d %H:%M:%S")),
        ("hiking", "Weekly", (now - timedelta(days=28)).strftime("%Y-%m-%d %H:%M:%S"))
    ]
    cursor.executemany("INSERT INTO habit (name, periodicity, created_at) VALUES (?, ?, ?)", habits)

    # Step 3: Generate the time-series check-off data
    tracker_data = []

    # --- Daily Habits (28 days of history) ---
    for i in range(28):
        # Travel back in time 'i' days
        check_date = (now - timedelta(days=i)).strftime("%Y-%m-%d %H:%M:%S")
        
        # Perfect streaks for reading and meditation
        tracker_data.append(("reading", check_date))
        tracker_data.append(("meditation", check_date))
        
        # Make 'coding' intentionally miss a few days so the analytics engine has varied data to test
        if i % 3 != 0: 
            tracker_data.append(("coding", check_date))

    # --- Weekly Habits (4 weeks of history) ---
    for i in range(4):
        # Travel back in time 'i' weeks
        check_date = (now - timedelta(weeks=i)).strftime("%Y-%m-%d %H:%M:%S")
        
        # Perfect streaks for gym and hiking
        tracker_data.append(("gym", check_date))
        tracker_data.append(("hiking", check_date))

    # Step 4: Bulk insert all the dummy tracking data into the database
    cursor.executemany("INSERT INTO tracker (habit_name, checkoff_date) VALUES (?, ?)", tracker_data)
    
    conn.commit()
    conn.close()
    print("Seeding complete.")

# --- INITIALIZATION BLOCK ---
# If this file is run directly (e.g., `python db.py`), it sets up the database.
if __name__ == "__main__":
    create_tables()
    seed_data()