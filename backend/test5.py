import sqlite3
import json

conn = sqlite3.connect('rajjo.db')
conn.row_factory = sqlite3.Row

edges_ord_inv = [dict(r) for r in conn.execute("SELECT * FROM edges WHERE (source_id LIKE 'ORD%' AND target_id LIKE 'INV%') OR (source_id LIKE 'INV%' AND target_id LIKE 'ORD%') LIMIT 5")]
edges_del_inv = [dict(r) for r in conn.execute("SELECT * FROM edges WHERE (source_id LIKE 'DEL%' AND target_id LIKE 'INV%') OR (source_id LIKE 'INV%' AND target_id LIKE 'DEL%') LIMIT 5")]
edges_ord_del = [dict(r) for r in conn.execute("SELECT * FROM edges WHERE (source_id LIKE 'ORD%' AND target_id LIKE 'DEL%') OR (source_id LIKE 'DEL%' AND target_id LIKE 'ORD%') LIMIT 5")]

print("ORD-INV:", json.dumps(edges_ord_inv, indent=2))
print("DEL-INV:", json.dumps(edges_del_inv, indent=2))
print("ORD-DEL:", json.dumps(edges_ord_del, indent=2))
