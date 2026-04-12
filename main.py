"""
main.py
The entry point for the Habit Tracker CLI. 
This file acts as the 'Controller' in our architecture. It handles user interactions 
via the terminal, parses commands using the Click library, and routes those commands 
to either the OOP Habit class or the Functional Analytics module.
"""

import click
import sys
import db

# Import our Object-Oriented module for managing individual habit data
from habit import Habit

# Import our Functional Programming module for data analysis
from analytics import (
    get_all_habits_data, 
    filter_by_periodicity, 
    get_tracker_data_for_habit, 
    calculate_streak,
    find_longest_streak_all_habits
)

# --- CLI BASE GROUP ---


@click.group()
def cli():
    """Habit Tracker CLI - Manage and analyze your habits to build better routines."""
    # --- ZERO FRICTION STARTUP ---
    # Automatically create tables and seed the 4-week data on the very first launch!
    db.create_tables()
    db.seed_data()
    pass

# --- CLI COMMANDS ---

@cli.command()
@click.option('--name', prompt=click.style('Habit Name', fg='blue'), help='The name of the habit')
@click.option('--period', type=click.Choice(['Daily', 'Weekly'], case_sensitive=False), prompt=click.style('Periodicity', fg='blue'), help='Frequency of the habit')
def create(name, period):
    """Create a new habit and save it to the database."""
    # Step 1: Instantiate a new Habit object (OOP)
    new_habit = Habit(name, period)
    
    try:
        # Step 2: Attempt to save it to the database
        new_habit.store()
        click.secho(f"✓ Success! Habit '{name}' created.", fg='green', bold=True)
    
    except ValueError:
        # Step 3: Handle the case where the habit already exists (IntegrityError caught in habit.py)
        click.secho(f"⚠ Warning: The habit '{name}' already exists.", fg='yellow')
        
        # Step 4: Give the user the option to overwrite it safely
        if click.confirm(click.style("Do you want to overwrite it? (All history will be lost)", fg='yellow')):
            new_habit.delete()  # Deletes the old habit and its history via CASCADE
            new_habit.store()   # Stores the fresh habit
            click.secho(f"✓ Habit '{name}' has been overwritten.", fg='green')
        else:
            click.echo("Operation cancelled.")

@cli.command()
@click.option('--name', prompt=click.style('Habit Name', fg='blue'), help='The name of the habit to check off')
def check(name):
    """Check off a habit, marking it as completed for the current period."""
    # Step 1: Retrieve the existing habit from the database
    h = Habit.get_by_name(name)
    
    if h:
        # Step 2: If it exists, call its OOP method to log a new tracker event
        h.check_off()
        click.secho(f"✓ Checked off '{h.name}' successfully!", fg='green', bold=True)
    else:
        # Step 3: Handle user typos or missing habits
        click.secho(f"✗ Error: Habit '{name}' does not exist.", fg='red')

@cli.command()
@click.option('--name', prompt=click.style('Habit Name', fg='blue'), help='The name of the habit to delete')
def delete(name):
    """Permanently delete a habit and all its tracking history."""
    h = Habit.get_by_name(name)
    
    if h:
        # Step 1: Ask for confirmation because deletion is permanent and wipes tracker history
        msg = click.style(f"Are you sure you want to delete '{h.name}' and all its history?", fg='red')
        if click.confirm(msg):
            # Step 2: Execute the deletion
            h.delete()
            click.secho(f"🗑 Habit '{h.name}' deleted.", fg='red')
    else:
        click.secho(f"✗ Error: Habit '{name}' not found.", fg='red')

@cli.command()
@click.option('--period', type=click.Choice(['Daily', 'Weekly'], case_sensitive=False), help='Filter by periodicity')
def list(period):
    """List all tracked habits in a clean table format."""
    # Step 1: Fetch raw data for all habits
    habits = get_all_habits_data()
    
    # Step 2: If the user provided a --period flag, filter the data using functional programming
    if period:
        habits = filter_by_periodicity(habits, period)
        title = f"{period.capitalize()} Habits"
    else:
        title = "All Habits"

    # Step 3: Handle the edge case of an empty database
    if not habits:
        click.secho("No habits found.", fg='yellow')
        return

    # Step 4: Print a formatted table header
    click.echo(f"\n{title}")
    click.secho(f"{'Name':<20} | {'Period':<10} | {'Created At':<20}", fg='blue', bold=True)
    click.echo("-" * 55)

    # Step 5: Loop through and print each habit, formatting the date for clean UI
    for habit in habits:
        date_str = habit['created_at'].split()[0] # Strip the timestamp, keep only YYYY-MM-DD
        click.echo(f"{habit['name']:<20} | {habit['periodicity']:<10} | {date_str:<20}")
    click.echo("-" * 55 + "\n")

@cli.command()
@click.option('--name', help='Analyze the streak for a specific habit')
@click.option('--all', is_flag=True, help='Find the longest streak across all tracked habits')
def analyze(name, all):
    """Analyze habits to view streaks and evaluate consistency."""
    
    # Branch 1: The user wants to find the global champion habit
    if all:
        best_name, streak = find_longest_streak_all_habits()
        if best_name:
            click.secho(f"🏆 The Champion Habit: '{best_name}'", fg='green', bold=True)
            click.secho(f"🔥 Longest Streak: {streak} periods", fg='green')
        else:
            click.secho("No habits or data found to analyze.", fg='yellow')
    
    # Branch 2: The user wants to analyze one specific habit
    elif name:
        h = Habit.get_by_name(name)
        if h:
            # Fetch the raw timestamps and calculate the streak based on its specific periodicity
            dates = get_tracker_data_for_habit(h.name)
            streak = calculate_streak(dates, h.periodicity)
            
            # Print the formatted output
            click.secho(f"Habit: ", nl=False) # nl=False prevents a new line, keeping text on the same row
            click.secho(f"{h.name}", fg='blue', bold=True)
            click.secho(f"Current Streak: ", nl=False)
            click.secho(f"{streak} periods", fg='green', bold=True)
        else:
            click.secho(f"✗ Error: Habit '{name}' not found.", fg='red')
            
    # Branch 3: The user typed `analyze` without any flags, so we show them the help menu
    else:
        ctx = click.get_current_context()
        click.echo(ctx.get_help())

# --- MAIN EXECUTION BLOCK ---

if __name__ == '__main__':
    try:
        # Start the CLI interface
        cli(standalone_mode=False)
        
    except click.exceptions.UsageError as e:
        # Catches incorrect command usage (e.g., missing required arguments)
        click.secho(f"\n⚠ Usage Error: {e}", fg='red', bold=True)
        click.echo("\n--- Correct Usage ---")
        if e.ctx:
            click.echo(e.ctx.get_help())
        else:
            click.echo(cli.get_help(click.Context(cli)))
        sys.exit(1)
        
    except click.exceptions.ClickException as e:
        # Catches general Click library errors
        click.secho(f"Error: {e}", fg='red')
        sys.exit(1)
        
