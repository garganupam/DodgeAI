import sqlite3
import json

conn = sqlite3.connect('rajjo.db')
conn.row_factory = sqlite3.Row

edges = [dict(r) for r in conn.execute("SELECT * FROM edges LIMIT 5")]
products = [dict(r) for r in conn.execute("SELECT * FROM products LIMIT 5")]
billing = [dict(r) for r in conn.execute("SELECT * FROM billing_documents LIMIT 5")]
sales_items = [dict(r) for r in conn.execute("SELECT * FROM sales_order_items LIMIT 5")]
sales = [dict(r) for r in conn.execute("SELECT * FROM sales_orders LIMIT 5")]
edges_bil = [dict(r) for r in conn.execute("SELECT * FROM edges WHERE relationship_type = 'BILLED_AS' LIMIT 5")]

output = {
    "edges": edges,
    "products": products,
    "billing": billing,
    "sales_items": sales_items,
    "sales": sales,
    "edges_bil": edges_bil
}

with open("db_inspect.json", "w") as f:
    json.dump(output, f, indent=2)
