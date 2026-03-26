"""
ETL Script for Rajjo — SAP O2C Graph-First Analytics Platform
Reads all JSONL files from the SAP dataset, creates a SQLite graph store
with nodes, edges, and denormalized relational tables.
"""

import json
import os
import sqlite3
import glob
from pathlib import Path

# ─── Configuration ───────────────────────────────────────────────────────────
DATASET_DIR = os.environ.get(
    "DATASET_DIR",
    r"C:\Users\HP\Downloads\sap-order-to-cash-dataset\sap-o2c-data"
)
DB_PATH = os.path.join(os.path.dirname(__file__), "rajjo.db")


# ─── Helpers ─────────────────────────────────────────────────────────────────
def read_jsonl_dir(dir_path: str) -> list[dict]:
    """Read all .jsonl files in a directory, return list of dicts."""
    records = []
    for fpath in sorted(glob.glob(os.path.join(dir_path, "*.jsonl"))):
        with open(fpath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    return records


def load_table(table_name: str) -> list[dict]:
    """Load a table from the dataset directory."""
    dir_path = os.path.join(DATASET_DIR, table_name)
    if not os.path.isdir(dir_path):
        print(f"  ⚠ Directory not found: {dir_path}")
        return []
    records = read_jsonl_dir(dir_path)
    print(f"  ✓ {table_name}: {len(records)} records")
    return records


# ─── Schema Creation ─────────────────────────────────────────────────────────
def create_schema(conn: sqlite3.Connection):
    """Create graph tables (nodes, edges) and relational tables."""
    cur = conn.cursor()

    # ── Graph tables ──
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nodes (
            id TEXT PRIMARY KEY,
            entity_type TEXT NOT NULL,
            label TEXT NOT NULL,
            properties_json TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            relationship_type TEXT NOT NULL,
            weight REAL DEFAULT 1.0,
            FOREIGN KEY (source_id) REFERENCES nodes(id),
            FOREIGN KEY (target_id) REFERENCES nodes(id)
        )
    """)

    # ── Relational tables (for SQL queries) ──
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sales_orders (
            sales_order TEXT PRIMARY KEY,
            order_type TEXT,
            sales_org TEXT,
            distribution_channel TEXT,
            sold_to_party TEXT,
            creation_date TEXT,
            total_net_amount REAL,
            currency TEXT,
            delivery_status TEXT,
            billing_status TEXT,
            incoterms TEXT,
            incoterms_location TEXT,
            payment_terms TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sales_order_items (
            sales_order TEXT,
            item_number TEXT,
            material TEXT,
            requested_qty REAL,
            qty_unit TEXT,
            net_amount REAL,
            currency TEXT,
            material_group TEXT,
            plant TEXT,
            storage_location TEXT,
            PRIMARY KEY (sales_order, item_number)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS billing_documents (
            billing_document TEXT PRIMARY KEY,
            doc_type TEXT,
            creation_date TEXT,
            billing_date TEXT,
            is_cancelled INTEGER,
            cancelled_doc TEXT,
            total_net_amount REAL,
            currency TEXT,
            company_code TEXT,
            fiscal_year TEXT,
            accounting_document TEXT,
            sold_to_party TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS deliveries (
            delivery_document TEXT PRIMARY KEY,
            creation_date TEXT,
            goods_movement_date TEXT,
            goods_movement_status TEXT,
            picking_status TEXT,
            shipping_point TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            accounting_document TEXT,
            item TEXT,
            company_code TEXT,
            fiscal_year TEXT,
            clearing_date TEXT,
            clearing_document TEXT,
            amount REAL,
            currency TEXT,
            customer TEXT,
            posting_date TEXT,
            gl_account TEXT,
            PRIMARY KEY (accounting_document, item)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS billing_document_items (
            billing_document TEXT,
            item_number TEXT,
            material TEXT,
            billing_qty REAL,
            qty_unit TEXT,
            net_amount REAL,
            currency TEXT,
            reference_so TEXT,
            reference_so_item TEXT,
            PRIMARY KEY (billing_document, item_number)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product TEXT PRIMARY KEY,
            product_type TEXT,
            product_old_id TEXT,
            gross_weight REAL,
            net_weight REAL,
            weight_unit TEXT,
            product_group TEXT,
            base_unit TEXT,
            description TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id TEXT PRIMARY KEY,
            full_name TEXT,
            category TEXT,
            grouping_code TEXT,
            is_blocked INTEGER,
            creation_date TEXT
        )
    """)

    # ── Indexes ──
    cur.execute("CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(entity_type)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_edges_rel ON edges(relationship_type)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_so_customer ON sales_orders(sold_to_party)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_soi_material ON sales_order_items(material)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_billing_customer ON billing_documents(sold_to_party)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_payments_customer ON payments(customer)")

    conn.commit()


# ─── ETL Functions ───────────────────────────────────────────────────────────

def etl_customers(conn: sqlite3.Connection, data: list[dict]):
    """Ingest business partners as Customer nodes."""
    cur = conn.cursor()
    for rec in data:
        cid = f"CUST-{rec['businessPartner']}"
        name = rec.get("businessPartnerFullName", rec.get("businessPartnerName", ""))
        props = {
            "customer_id": rec["businessPartner"],
            "name": name,
            "category": rec.get("businessPartnerCategory", ""),
            "grouping": rec.get("businessPartnerGrouping", ""),
            "is_blocked": rec.get("businessPartnerIsBlocked", False),
            "creation_date": rec.get("creationDate", ""),
        }
        cur.execute(
            "INSERT OR REPLACE INTO nodes (id, entity_type, label, properties_json) VALUES (?,?,?,?)",
            (cid, "Customer", name, json.dumps(props))
        )
        cur.execute(
            "INSERT OR REPLACE INTO customers VALUES (?,?,?,?,?,?)",
            (rec["businessPartner"], name, rec.get("businessPartnerCategory",""),
             rec.get("businessPartnerGrouping",""), int(rec.get("businessPartnerIsBlocked", False)),
             rec.get("creationDate",""))
        )
    conn.commit()
    print(f"  → {len(data)} Customer nodes created")


def etl_products(conn: sqlite3.Connection, products_data: list[dict], descriptions: list[dict]):
    """Ingest products as Product nodes."""
    cur = conn.cursor()
    # Build description lookup
    desc_map = {d["product"]: d["productDescription"] for d in descriptions}

    for rec in products_data:
        pid = f"PROD-{rec['product']}"
        desc = desc_map.get(rec["product"], rec.get("productOldId", rec["product"]))
        props = {
            "product_id": rec["product"],
            "old_id": rec.get("productOldId", ""),
            "type": rec.get("productType", ""),
            "group": rec.get("productGroup", ""),
            "description": desc,
            "gross_weight": rec.get("grossWeight", ""),
            "net_weight": rec.get("netWeight", ""),
            "weight_unit": rec.get("weightUnit", ""),
        }
        cur.execute(
            "INSERT OR REPLACE INTO nodes (id, entity_type, label, properties_json) VALUES (?,?,?,?)",
            (pid, "Product", desc, json.dumps(props))
        )
        cur.execute(
            "INSERT OR REPLACE INTO products VALUES (?,?,?,?,?,?,?,?,?)",
            (rec["product"], rec.get("productType",""), rec.get("productOldId",""),
             float(rec.get("grossWeight",0)), float(rec.get("netWeight",0)),
             rec.get("weightUnit",""), rec.get("productGroup",""),
             rec.get("baseUnit",""), desc)
        )
    conn.commit()
    print(f"  → {len(products_data)} Product nodes created")


def etl_orders(conn: sqlite3.Connection, headers: list[dict], items: list[dict]):
    """Ingest sales orders as Order nodes + edges to Customers and Products."""
    cur = conn.cursor()

    for rec in headers:
        oid = f"ORD-{rec['salesOrder']}"
        label = f"Order {rec['salesOrder']}"
        amt = float(rec.get("totalNetAmount", 0))
        props = {
            "sales_order": rec["salesOrder"],
            "type": rec.get("salesOrderType", ""),
            "sales_org": rec.get("salesOrganization", ""),
            "channel": rec.get("distributionChannel", ""),
            "customer": rec.get("soldToParty", ""),
            "creation_date": rec.get("creationDate", ""),
            "total_net_amount": amt,
            "currency": rec.get("transactionCurrency", ""),
            "delivery_status": rec.get("overallDeliveryStatus", ""),
            "payment_terms": rec.get("customerPaymentTerms", ""),
            "incoterms": rec.get("incotermsClassification", ""),
            "location": rec.get("incotermsLocation1", ""),
        }
        cur.execute(
            "INSERT OR REPLACE INTO nodes (id, entity_type, label, properties_json) VALUES (?,?,?,?)",
            (oid, "Order", label, json.dumps(props))
        )
        cur.execute(
            "INSERT OR REPLACE INTO sales_orders VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (rec["salesOrder"], rec.get("salesOrderType",""), rec.get("salesOrganization",""),
             rec.get("distributionChannel",""), rec.get("soldToParty",""),
             rec.get("creationDate",""), amt, rec.get("transactionCurrency",""),
             rec.get("overallDeliveryStatus",""), rec.get("overallOrdReltdBillgStatus",""),
             rec.get("incotermsClassification",""), rec.get("incotermsLocation1",""),
             rec.get("customerPaymentTerms",""))
        )

        # Edge: Customer → PLACED → Order
        cust_id = rec.get("soldToParty", "")
        if cust_id:
            cur.execute(
                "INSERT INTO edges (source_id, target_id, relationship_type, weight) VALUES (?,?,?,?)",
                (f"CUST-{cust_id}", oid, "PLACED", amt)
            )

    # Process line items
    for rec in items:
        so = rec["salesOrder"]
        item_num = rec["salesOrderItem"]
        material = rec.get("material", "")
        net = float(rec.get("netAmount", 0))

        cur.execute(
            "INSERT OR REPLACE INTO sales_order_items VALUES (?,?,?,?,?,?,?,?,?,?)",
            (so, item_num, material, float(rec.get("requestedQuantity",0)),
             rec.get("requestedQuantityUnit",""), net,
             rec.get("transactionCurrency",""), rec.get("materialGroup",""),
             rec.get("productionPlant",""), rec.get("storageLocation",""))
        )

        # Edge: Order → CONTAINS → Product
        if material:
            cur.execute(
                "INSERT INTO edges (source_id, target_id, relationship_type, weight) VALUES (?,?,?,?)",
                (f"ORD-{so}", f"PROD-{material}", "CONTAINS", net)
            )

        # Edge: Order → FULFILLED_FROM → Plant (create plant node if needed)
        plant = rec.get("productionPlant", "")
        if plant:
            plant_id = f"PLANT-{plant}"
            cur.execute(
                "INSERT OR IGNORE INTO nodes (id, entity_type, label, properties_json) VALUES (?,?,?,?)",
                (plant_id, "Plant", f"Plant {plant}", json.dumps({"plant_code": plant}))
            )
            cur.execute(
                "INSERT INTO edges (source_id, target_id, relationship_type, weight) VALUES (?,?,?,?)",
                (f"ORD-{so}", plant_id, "FULFILLED_FROM", 1.0)
            )

    conn.commit()
    print(f"  → {len(headers)} Order nodes + {len(items)} line items → edges created")


def etl_deliveries(conn: sqlite3.Connection, headers: list[dict], items: list[dict]):
    """Ingest deliveries as Delivery nodes + edges to Orders."""
    cur = conn.cursor()

    for rec in headers:
        did = f"DEL-{rec['deliveryDocument']}"
        label = f"Delivery {rec['deliveryDocument']}"
        gm_status = rec.get("overallGoodsMovementStatus", "")
        props = {
            "delivery_document": rec["deliveryDocument"],
            "creation_date": rec.get("creationDate", ""),
            "goods_movement_date": rec.get("actualGoodsMovementDate", ""),
            "goods_movement_status": gm_status,
            "picking_status": rec.get("overallPickingStatus", ""),
            "shipping_point": rec.get("shippingPoint", ""),
        }
        cur.execute(
            "INSERT OR REPLACE INTO nodes (id, entity_type, label, properties_json) VALUES (?,?,?,?)",
            (did, "Delivery", label, json.dumps(props))
        )
        cur.execute(
            "INSERT OR REPLACE INTO deliveries VALUES (?,?,?,?,?,?)",
            (rec["deliveryDocument"], rec.get("creationDate",""),
             rec.get("actualGoodsMovementDate"), gm_status,
             rec.get("overallPickingStatus",""), rec.get("shippingPoint",""))
        )

    # Link deliveries to orders via delivery items
    for rec in items:
        # Support multiple field names for referencing sales orders
        so = rec.get("referenceSDDocument") or rec.get("referenceSdDocument") or rec.get("salesOrder") or ""
        dd = rec.get("deliveryDocument", "")
        if so and dd:
            # SHADOW NODE: Ensure Delivery node exists
            cur.execute(
                "INSERT OR IGNORE INTO nodes (id, entity_type, label, properties_json) VALUES (?,?,?,?)",
                (f"DEL-{dd}", "Delivery", f"Delivery {dd}", json.dumps({"delivery_document": dd, "is_shadow": True}))
            )
            # SHADOW NODE: Ensure Order node exists
            cur.execute(
                "INSERT OR IGNORE INTO nodes (id, entity_type, label, properties_json) VALUES (?,?,?,?)",
                (f"ORD-{so}", "Order", f"Order {so}", json.dumps({"sales_order": so, "is_shadow": True}))
            )
            cur.execute(
                "INSERT INTO edges (source_id, target_id, relationship_type, weight) VALUES (?,?,?,?)",
                (f"ORD-{so}", f"DEL-{dd}", "DELIVERED_VIA", 1.0)
            )

    conn.commit()
    print(f"  → {len(headers)} Delivery nodes created")


def etl_billing(conn: sqlite3.Connection, headers: list[dict], items: list[dict]):
    """Ingest billing documents as Invoice nodes + edges."""
    cur = conn.cursor()

    for rec in headers:
        bid = f"INV-{rec['billingDocument']}"
        is_cancelled = rec.get("billingDocumentIsCancelled", False)
        label = f"Invoice {rec['billingDocument']}" + (" (Cancelled)" if is_cancelled else "")
        amt = float(rec.get("totalNetAmount", 0))
        props = {
            "billing_document": rec["billingDocument"],
            "type": rec.get("billingDocumentType", ""),
            "creation_date": rec.get("creationDate", ""),
            "billing_date": rec.get("billingDocumentDate", ""),
            "is_cancelled": is_cancelled,
            "cancelled_doc": rec.get("cancelledBillingDocument", ""),
            "total_net_amount": amt,
            "currency": rec.get("transactionCurrency", ""),
            "accounting_document": rec.get("accountingDocument", ""),
            "sold_to_party": rec.get("soldToParty", ""),
        }
        cur.execute(
            "INSERT OR REPLACE INTO nodes (id, entity_type, label, properties_json) VALUES (?,?,?,?)",
            (bid, "Invoice", label, json.dumps(props))
        )
        cur.execute(
            "INSERT OR REPLACE INTO billing_documents VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (rec["billingDocument"], rec.get("billingDocumentType",""),
             rec.get("creationDate",""), rec.get("billingDocumentDate",""),
             int(is_cancelled), rec.get("cancelledBillingDocument",""),
             amt, rec.get("transactionCurrency",""),
             rec.get("companyCode",""), rec.get("fiscalYear",""),
             rec.get("accountingDocument",""), rec.get("soldToParty",""))
        )

        # Edge: Customer → BILLED_TO
        cust = rec.get("soldToParty", "")
        if cust:
            cur.execute(
                "INSERT INTO edges (source_id, target_id, relationship_type, weight) VALUES (?,?,?,?)",
                (bid, f"CUST-{cust}", "BILLED_TO", amt)
            )

    # Link invoices to orders via billing items
    for rec in items:
        # Support multiple field names for referencing sales documents
        so = rec.get("referenceSdDocument") or rec.get("referenceSDDocument") or rec.get("salesDocument") or rec.get("salesOrder") or ""
        item_num = rec.get("billingDocumentItem", "")
        bd = rec.get("billingDocument", "")
        material = rec.get("material", "")
        
        if bd and item_num:
            # SHADOW NODE: Ensure Invoice node exists
            cur.execute(
                "INSERT OR IGNORE INTO nodes (id, entity_type, label, properties_json) VALUES (?,?,?,?)",
                (f"INV-{bd}", "Invoice", f"Invoice {bd}", json.dumps({"billing_document": bd, "is_shadow": True}))
            )
            cur.execute(
                "INSERT OR REPLACE INTO billing_document_items VALUES (?,?,?,?,?,?,?,?,?)",
                (bd, item_num, material, float(rec.get("billingQuantity", 0)),
                 rec.get("billingQuantityUnit", ""), float(rec.get("netAmount", 0)),
                 rec.get("transactionCurrency", ""), so, 
                 rec.get("referenceSdDocumentItem", rec.get("referenceSDDocumentItem", "")))
            )

        if so and bd:
            # SHADOW NODE: Ensure Order node exists
            cur.execute(
                "INSERT OR IGNORE INTO nodes (id, entity_type, label, properties_json) VALUES (?,?,?,?)",
                (f"ORD-{so}", "Order", f"Order {so}", json.dumps({"sales_order": so, "is_shadow": True}))
            )
            cur.execute(
                "INSERT INTO edges (source_id, target_id, relationship_type, weight) VALUES (?,?,?,?)",
                (f"ORD-{so}", f"INV-{bd}", "BILLED_AS", float(rec.get("netAmount", 0)))
            )

    conn.commit()
    print(f"  → {len(headers)} Invoice nodes created")


def etl_payments(conn: sqlite3.Connection, data: list[dict]):
    """Ingest payments as Payment nodes + edges to Invoices."""
    cur = conn.cursor()
    seen = set()

    for rec in data:
        acct_doc = rec["accountingDocument"]
        pid = f"PAY-{acct_doc}"
        amt = float(rec.get("amountInTransactionCurrency", 0))

        if pid not in seen:
            seen.add(pid)
            label = f"Payment {acct_doc}"
            props = {
                "accounting_document": acct_doc,
                "company_code": rec.get("companyCode", ""),
                "fiscal_year": rec.get("fiscalYear", ""),
                "clearing_date": rec.get("clearingDate", ""),
                "clearing_document": rec.get("clearingAccountingDocument", ""),
                "amount": amt,
                "currency": rec.get("transactionCurrency", ""),
                "customer": rec.get("customer", ""),
                "posting_date": rec.get("postingDate", ""),
                "gl_account": rec.get("glAccount", ""),
            }
            cur.execute(
                "INSERT OR REPLACE INTO nodes (id, entity_type, label, properties_json) VALUES (?,?,?,?)",
                (pid, "Payment", label, json.dumps(props))
            )

        cur.execute(
            "INSERT OR REPLACE INTO payments VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (acct_doc, rec.get("accountingDocumentItem",""),
             rec.get("companyCode",""), rec.get("fiscalYear",""),
             rec.get("clearingDate",""), rec.get("clearingAccountingDocument",""),
             amt, rec.get("transactionCurrency",""),
             rec.get("customer",""), rec.get("postingDate",""),
             rec.get("glAccount",""))
        )

        # Edge: Payment → PAID_FOR → Customer
        cust = rec.get("customer", "")
        if cust and pid in seen:
            cur.execute(
                "INSERT INTO edges (source_id, target_id, relationship_type, weight) VALUES (?,?,?,?)",
                (pid, f"CUST-{cust}", "PAID_FOR", abs(amt))
            )

    conn.commit()
    print(f"  → {len(seen)} Payment nodes created from {len(data)} records")


# ─── Link billing docs to payments via shared accountingDocument ─────────
def link_invoices_to_payments(conn: sqlite3.Connection):
    """Create edges between Invoices and Payments via accountingDocument."""
    cur = conn.cursor()
    cur.execute("""
        SELECT b.billing_document, b.accounting_document
        FROM billing_documents b
        WHERE b.accounting_document IS NOT NULL AND b.accounting_document != ''
    """)
    count = 0
    for row in cur.fetchall():
        inv_id = f"INV-{row[0]}"
        pay_id = f"PAY-{row[1]}"
        # Check payment node exists
        check = conn.execute("SELECT 1 FROM nodes WHERE id = ?", (pay_id,)).fetchone()
        if check:
            conn.execute(
                "INSERT INTO edges (source_id, target_id, relationship_type, weight) VALUES (?,?,?,?)",
                (inv_id, pay_id, "SETTLED_BY", 1.0)
            )
            count += 1
    conn.commit()
    print(f"  → {count} Invoice↔Payment edges created")


# ─── Main ────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  Rajjo ETL — SAP O2C Graph Builder")
    print("=" * 60)
    print(f"\nDataset: {DATASET_DIR}")
    print(f"Database: {DB_PATH}\n")

    # Remove old DB
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("  ✓ Removed old database\n")

    conn = sqlite3.connect(DB_PATH)
    create_schema(conn)
    print("  ✓ Schema created\n")

    # ── Load data ──
    print("Loading data...")
    customers = load_table("business_partners")
    products_raw = load_table("products")
    product_descs = load_table("product_descriptions")
    order_headers = load_table("sales_order_headers")
    order_items = load_table("sales_order_items")
    delivery_headers = load_table("outbound_delivery_headers")
    delivery_items = load_table("outbound_delivery_items")
    billing_headers = load_table("billing_document_headers")
    billing_cancellations = load_table("billing_document_cancellations")
    if billing_cancellations:
        billing_headers.extend(billing_cancellations)
    billing_items = load_table("billing_document_items")
    payments_data = load_table("payments_accounts_receivable")

    # ── Run ETL ──
    print("\nBuilding graph...")
    etl_customers(conn, customers)
    etl_products(conn, products_raw, product_descs)
    etl_orders(conn, order_headers, order_items)
    etl_deliveries(conn, delivery_headers, delivery_items)
    etl_billing(conn, billing_headers, billing_items)
    etl_payments(conn, payments_data)
    link_invoices_to_payments(conn)

    # ── Summary ──
    print("\n" + "=" * 60)
    node_count = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    edge_count = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]

    print(f"  Total nodes: {node_count}")
    print(f"  Total edges: {edge_count}")
    print("\n  Node types:")
    for row in conn.execute("SELECT entity_type, COUNT(*) FROM nodes GROUP BY entity_type ORDER BY COUNT(*) DESC"):
        print(f"    {row[0]}: {row[1]}")
    print("\n  Edge types:")
    for row in conn.execute("SELECT relationship_type, COUNT(*) FROM edges GROUP BY relationship_type ORDER BY COUNT(*) DESC"):
        print(f"    {row[0]}: {row[1]}")
    print("=" * 60)

    conn.close()
    print(f"\n✓ Database saved to: {DB_PATH}")


if __name__ == "__main__":
    main()
