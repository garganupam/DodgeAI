import sqlite3
import json

conn = sqlite3.connect('rajjo.db')
conn.row_factory = sqlite3.Row

types = ['BILLED_TO', 'CONTAINS', 'DELIVERED_VIA', 'FULFILLED_FROM', 'PAID_FOR', 'PLACED', 'SETTLED_BY']
result = {}

for t in types:
    edges = [dict(r) for r in conn.execute(f"SELECT * FROM edges WHERE relationship_type = '{t}' LIMIT 1")]
    result[t] = edges

print(json.dumps(result, indent=2))
