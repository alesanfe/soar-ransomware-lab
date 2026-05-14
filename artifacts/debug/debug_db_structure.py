#!/usr/bin/env python3
import sqlite3
import tempfile
import os

def main():
    # Create test database to understand structure
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tf:
        db_path = tf.name
        
        # Initialize database like DataManager does
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create tables like DataManager
        cursor.execute("""
            CREATE TABLE alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id TEXT UNIQUE NOT NULL,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                hostname TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                data TEXT,
                status TEXT DEFAULT 'new',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert test data
        cursor.execute("""
            INSERT INTO alerts (alert_id, alert_type, severity, hostname, data, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ('TEST-001', 'test_type', 'high', 'test_host', '{"test": "value"}', 'new'))
        
        conn.commit()
        
        # Query and print structure
        cursor.execute("SELECT * FROM alerts WHERE alert_id = ?", ('TEST-001',))
        row = cursor.fetchone()
        if row:
            print('Row structure:')
            for i, value in enumerate(row):
                print(f'  [{i}] {repr(value)}')
        else:
            print('No row found')
        
        conn.close()
        os.unlink(db_path)

if __name__ == "__main__":
    main()
