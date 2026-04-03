import os
import re

def refactor_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. psycopg2 imports and connection setup
    content = content.replace('import sqlite3', 'import psycopg2\nimport psycopg2.extras')
    content = content.replace('except sqlite3.IntegrityError', 'except psycopg2.IntegrityError')
    
    # Note: endpoints.py uses PRAGMA table_info(users) which needs manual fixing
    
    # 2. SQLite date functions -> Postgres date functions
    content = re.sub(r"date\('now',\s*'-(\d+)\s+days'\)", r"CURRENT_DATE - INTERVAL '\1 days'", content)
    content = re.sub(r"date\('now',\s*'-(\d+)\s+months'\)", r"CURRENT_DATE - INTERVAL '\1 months'", content)
    content = re.sub(r"date\('now',\s*'start of month'\)", r"date_trunc('month', CURRENT_DATE)", content)
    content = re.sub(r"DATE\('now'\)", r"CURRENT_DATE", content)
    
    # 3. SQLite string formatting -> Postgres
    content = re.sub(r"strftime\('%Y-%m',\s*([^)]+)\)", r"TO_CHAR(\1, 'YYYY-MM')", content)
    
    # 4. Parameter bindings
    # Replace ? with %s when it is used as a SQL parameter marker
    # A simple approach: replace '?' with '%s' where it's not inside a string if possible.
    # Actually, all ? in these files are for SQL parameters or in print/f-strings?
    # Let's do a careful replace: Only replace '?' if it's near SQL keywords or inside execute calls.
    # To be safe, let's just replace all ` ?` followed by `,`, `)`, or whitespace, or `?` inside `VALUES (...)`.
    content = re.sub(r'(?<=\s|\(|,|=)\?(?=\s|\)|,)', '%s', content)
    
    # 5. Row factory in database.py
    if 'database.py' in filepath:
        content = content.replace('conn.row_factory = psycopg2.Row', 'from psycopg2.extras import RealDictCursor\n    conn.cursor_factory = RealDictCursor')
        # Wait, get_db() context manager doesn't use the cursor directly in connection
        # It should be:
        # conn = psycopg2.connect(**params, cursor_factory=RealDictCursor)
        # So:
        content = content.replace('conn.row_factory = psycopg2.Row\n', '')
        content = content.replace(
            'conn = psycopg2.connect(**params)',
            'from psycopg2.extras import RealDictCursor\n    conn = psycopg2.connect(**params, cursor_factory=RealDictCursor)'
        )
    
    # 6. lastrowid replacements
    # mostly in endpoints.py and database.py and populate.py
    # We will need to change execute("INSERT ...", (...)) to execute("INSERT ... RETURNING id", (...))
    # and use fetchone()[0] instead of lastrowid.
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

base_dir = r"c:\Projects\College Projects\smb-one-web\insights"
files_to_refactor = [
    os.path.join(base_dir, 'database.py'),
    os.path.join(base_dir, 'api', 'endpoints.py'),
    os.path.join(base_dir, 'populate_smb_data.py')
]

for file in files_to_refactor:
    print(f"Refactoring {file}")
    refactor_file(file)

print("Done")
