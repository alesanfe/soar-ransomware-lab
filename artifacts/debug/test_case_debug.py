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
        
        # Insert test data with different title variations
        test_cases = [
            ('CASE-001', 'Test Case', 'Test description'),  # No spaces
            ('CASE-002', ' Test Case', 'Test description'),  # Leading space
            ('CASE-003', 'Test  Case', 'Test description'),  # Internal space
        ]
        
        for case_id, title, description in test_cases:
            cursor.execute("""
                INSERT INTO cases (case_id, title, description, severity, alert_id)
                VALUES (?, ?, ?, ?, ?)
            """, (case_id, title, description, 'medium', None))
            conn.commit()
            
            # Query and check what gets stored
            cursor.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,))
            row = cursor.fetchone()
            
            print(f'Input: "{title}"')
            print(f'Stored: "{row[2] if row else "None"}"')
            print(f'Retrieved: "{row[2] if row else "None"}"')
            print()
        
        conn.close()
        os.unlink(db_path)

if __name__ == "__main__":
    main()
