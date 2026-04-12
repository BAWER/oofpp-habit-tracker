"""
habit.py
Contains the Habit class (Object-Oriented logic) for managing individual habits 
and their persistence in the SQLite database. 
By keeping database queries related to a specific habit inside this class, 
we achieve high cohesion and strict encapsulation.
"""

import sqlite3
from datetime import datetime
from db import get_db

class Habit:
    """
    Represents a single behavior the user wants to track.
    Encapsulates the state (name, periodicity) and the behavior (saving, deleting, logging).
    """

    def __init__(self, name: str, periodicity: str, created_at=None):
        # Step 1: Normalize the name by making it lowercase and removing leading/trailing spaces.
        # This ensures that "Gym", "gym", and " gym " are all treated as the exact same habit.
        self.name = name.lower().strip()
        
        # Step 2: Store the periodicity (e.g., 'Daily' or 'Weekly')
        self.periodicity = periodicity
        
        # Step 3: Handle the creation timestamp.
        # If a date is provided (e.g., when loading from the DB), use it.
        # Otherwise, generate the exact current time (used when creating a brand new habit).
        self.created_at = created_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def store(self):
        """
        Saves the current habit instance to the database.
        Raises ValueError if a habit with the same name already exists.
        """
        # Step 1: Open a connection to the database
        conn = get_db()
        try:
            # Step 2: Use a context manager ('with conn:'). 
            # This automatically commits the transaction if successful, or rolls it back if it crashes.
            with conn:
                conn.execute(
                    "INSERT INTO habit (name, periodicity, created_at) VALUES (?, ?, ?)",
                    (self.name, self.periodicity, self.created_at)
                )
        except sqlite3.IntegrityError:
            # Step 3: Our database schema defines 'name' as the PRIMARY KEY.
            # If the user tries to save a habit name that already exists, SQLite throws an IntegrityError.
            # We catch that here and raise a standard Python ValueError for the CLI to handle gracefully.
            raise ValueError(f"Habit '{self.name}' already exists.")
        finally:
            # Step 4: Always close the connection, even if an error occurred, to prevent database locks.
            conn.close()

    def delete(self):
        """
        Removes the habit from the database. 
        Note: The 'ON DELETE CASCADE' rule in the database automatically 
        deletes all associated tracking history, preventing orphan data.
        """
        conn = get_db()
        try:
            with conn:
                # Step 1: Execute the delete command
                cursor = conn.execute("DELETE FROM habit WHERE name = ?", (self.name,))
                
                # Step 2: Check if any rows were actually deleted. 
                # If rowcount is 0, the habit didn't exist in the database.
                if cursor.rowcount == 0:
                    raise ValueError(f"Habit '{self.name}' does not exist.")
        finally:
            conn.close()

    def check_off(self, checkoff_date=None):
        """
        Records a completion event for this habit.
        Allows passing a specific date (useful for testing), otherwise uses 'now'.
        """
        # Step 1: Determine the check-off time. 
        # By allowing checkoff_date to be passed in as an argument, we make this method 
        # highly testable, as we can simulate check-offs that happened weeks ago.
        checkoff_date = checkoff_date or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        conn = get_db()
        try:
            with conn:
                # Step 2: Insert a new log into the tracker table, linking it to this habit's name.
                conn.execute(
                    "INSERT INTO tracker (habit_name, checkoff_date) VALUES (?, ?)",
                    (self.name, checkoff_date)
                )
        finally:
            conn.close()

    @staticmethod
    def get_all():
        """
        Retrieves all habits currently stored in the database.
        Uses @staticmethod because it doesn't operate on a single existing instance, 
        but rather acts as a "factory" to generate multiple new instances.
        """
        conn = get_db()
        try:
            # Step 1: Fetch all rows from the 'habit' table
            rows = conn.execute("SELECT * FROM habit").fetchall()
            
            # Step 2: Reconstruct ("hydrate") Habit objects from the raw database rows 
            # using a list comprehension, and return the list of objects.
            return [Habit(row['name'], row['periodicity'], row['created_at']) for row in rows]
        finally:
            conn.close()

    @staticmethod
    def get_by_name(name: str):
        """
        Retrieves a single habit by its name.
        Returns a Habit object if found, or None if it doesn't exist.
        """
        conn = get_db()
        try:
            # Step 1: Query the database for a specific, normalized name
            row = conn.execute("SELECT * FROM habit WHERE name = ?", (name.lower().strip(),)).fetchone()
            
            # Step 2: If a row is found, convert it into a Habit object and return it
            if row:
                return Habit(row['name'], row['periodicity'], row['created_at'])
            
            # Step 3: If no row is found, return None so the CLI knows it doesn't exist
            return None
        finally:
            conn.close()