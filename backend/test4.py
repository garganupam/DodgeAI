import sqlite3
import json

conn = sqlite3.connect('rajjo.db')
conn.row_factory = sqlite3.Row

edges = [dict(r) for r in conn.execute("SELECT * FROM edges WHERE source_id LIKE '%90504248%' OR target_id LIKE '%90504248%'")]

print(json.dumps(edges, indent=2))
