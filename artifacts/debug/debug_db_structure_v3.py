#!/usr/bin/env python3
import sqlite3
import tempfile
import os
from datetime import datetime

def main():
    # Test case data structure
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tf:
        db_path = tf.name
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("""
            CREATE TABLE cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                severity TEXT NOT NULL,
                status TEXT DEFAULT 'open',
                alert_id TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert test data
        cursor.execute("""
            INSERT INTO cases (case_id, title, description, severity, alert_id)
            VALUES (?, ?, ?, ?, ?)
        """, ('CASE-002', 'Test Case', 'Test description', 'medium', 'ALERT-008'))
        
        conn.commit()
        
        # Query and check exact values
        cursor.execute("SELECT * FROM cases WHERE case_id = ?", ('CASE-002',))
        row = cursor.fetchone()
        
        if row:
            print('Stored values:')
            for i, value in enumerate(row):
                print(f"  [{i}] {repr(value)}")
            
            # Check title specifically
            title_value = row[2] if len(row) > 2 else "N/A"
            print(f'Title length: {len(title_value) if len(title_value) > 2 else "N/A"}')
            print(f'Title repr: {repr(title_value)}')
        
        conn.close()
        os.unlink(db_path)

if __name__ == "__main__":
    main()
