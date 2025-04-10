from app import db, User, UserPreferences
import sqlite3
from datetime import datetime

def update_database():
    # Create new tables
    with sqlite3.connect('health_tracker.db') as conn:
        cursor = conn.cursor()
        
        # Add new columns to users table
        try:
            cursor.execute('''ALTER TABLE users ADD COLUMN email TEXT''')
            cursor.execute('''ALTER TABLE users ADD COLUMN birth_date DATE''')
            cursor.execute('''ALTER TABLE users ADD COLUMN gender TEXT''')
            cursor.execute('''ALTER TABLE users ADD COLUMN activity_level TEXT''')
            cursor.execute('''ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP''')
        except sqlite3.OperationalError as e:
            print(f"Some columns might already exist: {e}")

        # Create user_preferences table
        cursor.execute('''CREATE TABLE IF NOT EXISTS user_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            daily_water_goal INTEGER DEFAULT 2000,
            daily_steps_goal INTEGER DEFAULT 10000,
            theme TEXT DEFAULT 'light',
            FOREIGN KEY (user_id) REFERENCES users(id)
        )''')
        
        # Add default preferences for existing users
        cursor.execute('SELECT id FROM users')
        existing_users = cursor.fetchall()
        
        for user_id in existing_users:
            cursor.execute('''INSERT OR IGNORE INTO user_preferences 
                (user_id, daily_water_goal, daily_steps_goal, theme)
                VALUES (?, 2000, 10000, 'light')''', (user_id[0],))
        
        conn.commit()
        print("Database update completed successfully!")

if __name__ == "__main__":
    update_database() 