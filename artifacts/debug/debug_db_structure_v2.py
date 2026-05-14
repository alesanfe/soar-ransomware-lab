#!/usr/bin/env python3
import sqlite3
import tempfile
import os
from datetime import datetime

def main():
    # Create test database to understand structure
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tf:
        db_path = tf.name
        
        # Initialize database like DataManager does
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create tables like DataManager
        cursor.execute("""
            CREATE TABLE metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value REAL,
                unit TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                source TEXT,
                tags TEXT
            )
        """)
        
        # Insert test data like DataManager does
        cursor.execute("""
            INSERT INTO metrics (metric_name, metric_value, unit, timestamp, source, tags)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ('memory_usage', 1024, 'percent', datetime.now(), None, None))
        
        conn.commit()
        
        # Query and print structure
        cursor.execute("SELECT * FROM metrics WHERE metric_name = ?", ('memory_usage',))
        row = cursor.fetchone()
        if row:
            print('Row structure:')
            for i, value in enumerate(row):
                print(f"  [{i}] {repr(value)}")
        else:
            print('No row found')
        
        conn.close()
        os.unlink(db_path)

if __name__ == "__main__":
    main()
