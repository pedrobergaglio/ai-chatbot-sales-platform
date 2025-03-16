import os
import sqlite3
from database import init_db

def reset_database():
    # Remove existing database file
    try:
        os.remove('messages.db')
        print("Existing database removed successfully")
    except FileNotFoundError:
        print("No existing database found")

    # Initialize fresh database
    init_db()
    print("New database initialized successfully")

if __name__ == '__main__':
    reset_database()