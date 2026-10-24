import sqlite3
import json

conn = sqlite3.connect('studiocrm.db')
cursor = conn.cursor()

cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print(f"Total tables found: {len(tables)}")
for name, sql in tables:
    print(f"\n================ TABLE: {name} ================")
    print(sql)

print("\n================ ROW COUNTS & SAMPLE DATA ================")
for (name, _) in tables:
    if name.startswith('sqlite_'):
        continue
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {name}")
        cnt = cursor.fetchone()[0]
        print(f"\n--- {name} (count: {cnt}) ---")
        cursor.execute(f"PRAGMA table_info({name});")
        columns = [f"{col[1]} ({col[2]})" for col in cursor.fetchall()]
        print("Columns:", ", ".join(columns))
        
        cursor.execute(f"SELECT * FROM {name} LIMIT 3")
        rows = cursor.fetchall()
        for r in rows:
            print("  Sample row:", r)
    except Exception as exc:
        print(f"Error querying {name}: {exc}")
