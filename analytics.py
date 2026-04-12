"""
analytics.py
Contains functional programming logic to analyze habit data.
Functions here strictly adhere to functional paradigms: they receive inputs, 
process them mathematically without altering the database (no side effects), 
and return a deterministic output.
"""

from db import get_db
from datetime import datetime, timedelta

# --- DATA FETCHING FUNCTIONS ---
# These functions act as the boundary between our database and our pure functional logic.

def get_all_habits_data():
    """Returns a list of all habit definitions from the DB as dictionary-like rows."""
    # Step 1: Open database connection
    conn = get_db()
    try:
        # Step 2: Fetch all records from the habit table
        rows = conn.execute("SELECT * FROM habit").fetchall()
        return rows
    finally:
        # Step 3: Ensure the connection is closed
        conn.close()

def get_tracker_data_for_habit(habit_name: str):
    """Returns a list of datetime objects representing all check-offs for a specific habit."""
    conn = get_db()
    try:
        # Step 1: Query the tracker table, filtering by normalized name, and order chronologically
        rows = conn.execute(
            "SELECT checkoff_date FROM tracker WHERE habit_name = ? ORDER BY checkoff_date", 
            (habit_name.lower().strip(),)
        ).fetchall()
        
        # Step 2: Use a list comprehension to transform raw database strings into Python datetime objects.
        # .split('.')[0] acts as a safety measure to strip out microseconds if they exist, 
        # ensuring the strptime format strictly matches "%Y-%m-%d %H:%M:%S".
        return [datetime.strptime(row['checkoff_date'].split('.')[0], '%Y-%m-%d %H:%M:%S') for row in rows]
    finally:
        conn.close()

# --- FUNCTIONAL ANALYSIS (Pure Logic) ---
# These functions do not touch the database. They only perform logic on the data passed into them.

def filter_by_periodicity(habits, period: str):
    """Filters a list of habit rows by the given periodicity (Daily or Weekly)."""
    # Step 1: Use a pure functional list comprehension to filter the dataset.
    # We use .lower() on both sides to make the filter case-insensitive.
    return [habit for habit in habits if habit['periodicity'].lower() == period.lower()]

def calculate_streak(dates, periodicity: str):
    """
    Calculates the longest streak of consecutive check-offs.
    Applies different mathematical rules based on whether the habit is Daily or Weekly.
    """
    # Base Case: If the habit has never been checked off, the streak is 0.
    if not dates:
        return 0

    longest_streak = 0
    current_streak = 1

    # --- BRANCH 1: DAILY HABITS ---
    if periodicity.lower() == 'daily':
        # Step 1: Normalize the data. 
        # By extracting just the .date() (stripping the hours/minutes) and putting it in a set(), 
        # we automatically remove duplicate check-offs that happened on the exact same day.
        unique_dates = sorted(list(set(d.date() for d in dates)))
        
        # Step 2: Iterate through the sorted dates comparing each day to the previous day.
        for i in range(1, len(unique_dates)):
            # Mathematically subtract the dates to find the gap in days
            delta = (unique_dates[i] - unique_dates[i-1]).days
            
            if delta == 1:
                # The dates are exactly 1 day apart; the streak continues.
                current_streak += 1
            else:
                # The gap is larger than 1 day; the streak is broken. 
                # Save the highest streak found so far and reset the counter.
                longest_streak = max(longest_streak, current_streak)
                current_streak = 1
                
    # --- BRANCH 2: WEEKLY HABITS ---
    elif periodicity.lower() == 'weekly':
        # Step 1: Normalize the data to ISO Weeks.
        # timedelta(days=d.weekday()) calculates how many days past Monday the current date is.
        # Subtracting that rolls the date back to the exact Monday of that week.
        # This brilliantly groups any check-offs within the same Mon-Sun window into one single 'Week' identifier.
        unique_weeks = sorted(list(set(d.date() - timedelta(days=d.weekday()) for d in dates)))
        
        # Step 2: Iterate through the sorted Mondays comparing each to the previous.
        for i in range(1, len(unique_weeks)):
            # Mathematically subtract the Mondays to find the gap in days
            delta = (unique_weeks[i] - unique_weeks[i-1]).days
            
            if delta == 7:
                # The difference between two consecutive Mondays is exactly 7 days; the streak continues.
                current_streak += 1
            else:
                # The gap is larger than 7 days; a week was missed and the streak is broken.
                longest_streak = max(longest_streak, current_streak)
                current_streak = 1

    # Step 3: Return the largest streak found (covers the edge case where the longest streak is the current one).
    return max(longest_streak, current_streak)

def find_longest_streak_all_habits():
    """
    Calculates the streaks for every habit in the database and returns a tuple 
    containing the name of the habit with the longest streak and the streak count.
    """
    # Step 1: Fetch the master list of all habits
    all_habits = get_all_habits_data()
    
    max_streak = 0
    best_habit = None

    # Step 2: Loop through each habit to calculate its individual score
    for habit in all_habits:
        name = habit['name']
        periodicity = habit['periodicity']
        
        # Step 3: Fetch the raw time-series data for this specific habit
        dates = get_tracker_data_for_habit(name)
        
        # Step 4: Calculate the streak, passing its specific periodicity to apply the correct math rule
        streak = calculate_streak(dates, periodicity) 
        
        # Step 5: If this habit's streak beats the current reigning champion, update the leaderboard
        if streak > max_streak:
            max_streak = streak
            best_habit = name
            
    # Step 6: Return the final winner
    return (best_habit, max_streak)