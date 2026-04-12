"""
test_project.py
Comprehensive unit test suite for the Habit Tracker application.
Covers CRUD operations (habit.py) and functional logic (analytics.py).
Follows the standard 'Arrange, Act, Assert' pattern for software testing.
"""

import pytest
import sqlite3
import os
import tempfile
from datetime import datetime, timedelta

from habit import Habit
import db
from analytics import (
    get_all_habits_data,
    filter_by_periodicity,
    get_tracker_data_for_habit,
    calculate_streak,
    find_longest_streak_all_habits
)

# --- FIXTURES ---

@pytest.fixture
def test_db():
    """
    Sets up a temporary, isolated SQLite database for testing.
    This is a critical best practice: it ensures running tests does not 
    accidentally overwrite or delete the user's actual live habit data.
    """
    # Step 1: Create a secure temporary file
    fd, temp_name = tempfile.mkstemp(suffix=".db")
    os.close(fd) # Close the file handle so SQLite can access it
    
    # Step 2: Swap the live database name in db.py with our temporary file
    original_db_name = db.DB_NAME
    db.DB_NAME = temp_name
    
    # Step 3: Initialize the tables in this fresh, empty database
    db.create_tables()
    
    # Yield hands control over to the actual test function being run
    yield temp_name  
    
    # Step 4: TEARDOWN phase. After the test finishes, restore the original 
    # database name and delete the temporary test file to free up system memory.
    db.DB_NAME = original_db_name
    if os.path.exists(temp_name):
        try:
            os.remove(temp_name)
        except PermissionError:
            pass

# --- 1. HABIT CLASS TESTS (CRUD Operations) ---

def test_habit_creation(test_db):
    """Test a) Habit creation."""
    # Arrange & Act: Create and store a new habit
    h = Habit("run", "Daily")
    h.store()
    
    # Assert: Fetch it back and ensure the properties match exactly
    fetched = Habit.get_by_name("run")
    assert fetched is not None
    assert fetched.name == "run"
    assert fetched.periodicity == "Daily"

def test_habit_duplication_error(test_db):
    """Test that creating a duplicate habit raises a ValueError."""
    # Arrange: Store the first habit
    h1 = Habit("swim", "Weekly")
    h1.store()
    
    # Act & Assert: Attempt to store an identical habit and expect a ValueError
    h2 = Habit("swim", "Weekly")
    with pytest.raises(ValueError):
        h2.store()

def test_habit_deletion(test_db):
    """Test a) Habit deletion."""
    # Arrange: Create and store a habit
    h = Habit("yoga", "Daily")
    h.store()
    
    # Act: Delete it
    h.delete()
    
    # Assert: Ensure it no longer exists in the database
    assert Habit.get_by_name("yoga") is None

def test_check_off(test_db):
    """Test a) Habit editing/updating (checking off)."""
    # Arrange: Create a habit and check it off once
    h = Habit("read", "Daily")
    h.store()
    h.check_off()
    
    # Act: Manually query the tracker table to count the logs
    conn = db.get_db()
    count = conn.execute("SELECT count(*) FROM tracker WHERE habit_name='read'").fetchone()[0]
    conn.close()
    
    # Assert: There should be exactly 1 tracker log for this habit
    assert count == 1


# --- 2. ANALYTICS MODULE TESTS ---

def test_analytics_daily_streak_calculation(test_db):
    """Test b) Streak calculation logic for Daily habits."""
    # Arrange: Create a daily habit
    h = Habit("code", "Daily")
    h.store()
    
    # Act: Manually backdate check-offs for 3 consecutive days
    today = datetime.now()
    h.check_off(checkoff_date=(today - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"))
    h.check_off(checkoff_date=(today - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"))
    h.check_off(checkoff_date=today.strftime("%Y-%m-%d %H:%M:%S"))
    
    # Assert: The functional calculator should read the data and return a streak of 3
    data = get_tracker_data_for_habit("code")
    streak = calculate_streak(data, "Daily")  
    
    assert streak == 3

def test_analytics_weekly_streak_calculation(test_db):
    """Test b) Streak calculation logic for Weekly habits."""
    # Arrange: Create a weekly habit
    h = Habit("tennis", "Weekly")
    h.store()
    
    # Act: Manually backdate check-offs for exactly 1, 2, and 3 weeks ago
    today = datetime.now()
    h.check_off(checkoff_date=(today - timedelta(weeks=2)).strftime("%Y-%m-%d %H:%M:%S"))
    h.check_off(checkoff_date=(today - timedelta(weeks=1)).strftime("%Y-%m-%d %H:%M:%S"))
    h.check_off(checkoff_date=today.strftime("%Y-%m-%d %H:%M:%S"))
    
    # Assert: The functional calculator should recognize consecutive weeks and return a streak of 3
    data = get_tracker_data_for_habit("tennis")
    streak = calculate_streak(data, "Weekly")
    
    assert streak == 3

def test_filter_by_periodicity(test_db):
    """Test b) Filtering habits by periodicity."""
    # Arrange: Store a mix of Daily and Weekly habits
    Habit("run", "Daily").store()
    Habit("read", "Daily").store()
    Habit("gym", "Weekly").store()
    
    # Act: Fetch all and apply the functional filters
    all_habits = get_all_habits_data()
    daily_habits = filter_by_periodicity(all_habits, "Daily")
    weekly_habits = filter_by_periodicity(all_habits, "Weekly")
    
    # Assert: The lists should be filtered correctly
    assert len(daily_habits) == 2
    assert len(weekly_habits) == 1

# --- 3. PREDEFINED DATA & 4-WEEK TIME-SERIES TESTS ---

def test_predefined_data_analytics(test_db):
    """
    Test using the 4-weeks of predefined time-series data to verify streak calculations
    and the find_longest_streak_all_habits functionality as strictly requested by the rubric.
    """
    # Act: Trigger the automated seeding module
    db.seed_data()
    
    # Assert 1: Verify exactly 5 predefined habits were loaded
    all_habits = get_all_habits_data()
    assert len(all_habits) == 5
    
    # Assert 2: Verify the 4-week time-series data for a Daily habit ("reading" has 28 perfect days)
    reading_dates = get_tracker_data_for_habit("reading")
    assert calculate_streak(reading_dates, "Daily") == 28
    
    # Assert 3: Verify the 4-week time-series data for a Weekly habit ("gym" has 4 perfect weeks)
    gym_dates = get_tracker_data_for_habit("gym")
    assert calculate_streak(gym_dates, "Weekly") == 4
    
    # Assert 4: Verify the global champion function works and accurately compares different periodicities
    best_habit, max_streak = find_longest_streak_all_habits()
    assert best_habit in ["reading", "meditation"]  # Both were seeded with a 28-day streak
    assert max_streak == 28