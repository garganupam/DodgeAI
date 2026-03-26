import os
import json
import sqlite3
from huggingface_hub import InferenceClient
from graph_store import DB_PATH

# ─── Configuration ───────────────────────────────────────────────────────────
from dotenv import load_dotenv

# Load .env file from the parent directory (Desktop/Rajjo/.env)
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(dotenv_path)

API_KEY = os.environ.get("HF_API_KEY")
client = None
if API_KEY:
    client = InferenceClient(api_key=API_KEY)

# HuggingFace open-source models (free Inference API)
MODEL = "Qwen/Qwen2.5-72B-Instruct"

# ─── Prompts ─────────────────────────────────────────────────────────────────

CLASSIFIER_PROMPT = """You are a domain classifier for an SAP Order-to-Cash analytics system.
Your job is to determine if the user's query is relevant to the dataset.
The dataset covers: Sales Orders, Customers (Business Partners), Products, Deliveries, Billing/Invoices, and Payments.
If the query is relevant (even somewhat), return TRUE.
If it is completely off-topic (e.g., general knowledge questions, creative writing requests, irrelevant topics, weather, sports, general coding help, unrelated trivia), return FALSE.
Output ONLY a valid JSON object with a single boolean key "in_domain".
Example: {"in_domain": true}
"""

SCHEMA_INFO = """
Table: sales_orders (sales_order PK, sold_to_party, creation_date, total_net_amount, delivery_status, billing_status)
Table: sales_order_items (sales_order, item_number, material, requested_qty, net_amount, plant)
Table: customers (customer_id PK, full_name, is_blocked)
Table: products (product PK, description, product_group)
Table: deliveries (delivery_document PK, goods_movement_status, shipping_point)
Table: billing_documents (billing_document PK, creation_date, is_cancelled, total_net_amount, accounting_document, sold_to_party)
Table: billing_document_items (billing_document, item_number, material, billing_qty, net_amount, reference_so)
Table: payments (accounting_document, clearing_date, amount, customer)

Graph Tables (Crucial for traversing flows between documents):
Table: nodes
- id (TEXT PK, e.g., 'ORD-12345', 'DEL-67890', 'INV-54321', 'PROD-S89', 'CUST-310', 'PAY-987')
- entity_type (TEXT: 'Order', 'Delivery', 'Invoice', 'Product', 'Customer', 'Payment')
- label (TEXT)

Table: edges
- source_id (TEXT, refers to nodes.id)
- target_id (TEXT, refers to nodes.id)
- relationship_type (TEXT: 'DELIVERED_VIA', 'BILLED_AS', 'BILLED_TO', 'PLACED', 'CONTAINS', 'FULFILLED_FROM', 'PAID_FOR', 'SETTLED_BY')
"""

SQL_SYSTEM_PROMPT = f"""You are a SQL expert for an SAP Order-to-Cash SQLite database.
Your goal is to translate the user's natural language question into a valid SQLite query.
Output ONLY the raw SQL query. No markdown formatting, no explanations, no ```sql``` blocks.
Use the following schema:
{SCHEMA_INFO}

Guidelines:
- Node IDs have prefixes: ORD- for Orders, DEL- for Deliveries, INV- for Invoices, PAY- for Payments, CUST- for Customers, PROD- for Products.
- ALWAYS use the prefix when querying the `nodes` or `edges` tables (e.g., 'INV-90628266' instead of '90628266').
- To answer questions about products associated with billing/invoices, ALWAYS JOIN `billing_document_items` to `billing_documents`.
- To trace an end-to-end flow FROM a Billing/Delivery ID:
    1. Find the Sales Order linked to that ID (using `edges` with `relationship_type` 'BILLED_AS' or 'DELIVERED_VIA').
    2. Then find all other nodes linked to that Sales Order.
- Example Trace Full Flow (Starting from Invoice 90504301): 
  `SELECT * FROM edges WHERE source_id IN (SELECT source_id FROM edges WHERE target_id = 'INV-90504301') OR target_id IN (SELECT source_id FROM edges WHERE target_id = 'INV-90504301') OR source_id = 'INV-90504301' OR target_id = 'INV-90504301'`
- To identify broken/incomplete flows:
    - 'Delivered but not billed': `SELECT * FROM sales_orders WHERE sales_order NOT IN (SELECT reference_so FROM billing_document_items) AND sales_order IN (SELECT SUBSTR(source_id, 5) FROM edges WHERE relationship_type = 'DELIVERED_VIA')`
    - 'Billed without delivery': `SELECT * FROM sales_orders WHERE sales_order IN (SELECT reference_so FROM billing_document_items) AND sales_order NOT IN (SELECT SUBSTR(source_id, 5) FROM edges WHERE relationship_type = 'DELIVERED_VIA')`
- Example finding products associated with highest billing docs: `SELECT material, COUNT(DISTINCT billing_document) AS invoice_count FROM billing_document_items GROUP BY material ORDER BY invoice_count DESC`
- Always use `LIKE` for text searches (e.g., `full_name LIKE '%Nelson%'`)
- Limit results to 50 unless required to aggregate everything.
"""

SYNTHESIS_SYSTEM_PROMPT = """You are an AI assistant for an SAP O2C Analytics platform.
You have been given a user's question, the SQL query executed to answer it, and the raw JSON results from the database.
Your task is to synthesize a helpful, natural, and concise answer for the user based strictly on the data provided.

Crucial UX requirement:
If the data references specific IDs (like a Sales Order number, Customer ID, Product ID, Delivery ID, Invoice ID, or Payment document), you MUST mention those IDs in your response. The frontend UI relies on these IDs to highlight nodes in the graph canvas.

IDs typically look like:
- Order: just the numeric string (e.g. 740506) or ORD-740506
- Customer: e.g. 310000108
- Product: S8907367001003
- Billing/Invoice: 91150187
- Delivery: 840000305
- Payment/Journal Entry: 9400635958

Format your answer in markdown. Be professional and data-driven.
"""


# ─── Pipeline Core ───────────────────────────────────────────────────────────

def execute_sql(query: str) -> list[dict]:
    """Execute read-only SQL against the local SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        if not query.strip().upper().startswith("SELECT"):
            return [{"error": "Only SELECT queries are allowed."}]
            
        cur = conn.execute(query)
        results = [dict(row) for row in cur.fetchmany(50)]
        return results
    except Exception as e:
        return [{"error": str(e)}]
    finally:
        conn.close()

def format_history(history: list[dict]) -> str:
    """Format previous chat turns for context."""
    if not history:
        return ""
    
    formatted = "Recent conversation history:\n"
    for msg in history[-5:]:
        role = "User" if msg.get("role") == "user" else "Assistant"
        formatted += f"{role}: {msg.get('content')}\n"
    return formatted + "\n"

async def handle_chat_query_stream(message: str, history: list[dict]):
    """
    Two-stage pipeline:
    1. Guardrail check
    2. SQL generation + Execution
    3. Answer synthesis (Streamed)
    """
    if not client:
        yield 'data: {"chunk": "Error: HF_API_KEY environment variable not set. Get a free token at https://huggingface.co/settings/tokens"}\n\n'
        return

    hist_context = format_history(history)
    
    # ── Stage 1: Domain Guardrail ──
    try:
        clf_res = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": CLASSIFIER_PROMPT},
                {"role": "user", "content": f"{hist_context}User Query: {message}"}
            ],
            temperature=0,
            max_tokens=100
        )
        clf_text = clf_res.choices[0].message.content
        try:
            is_in_domain = json.loads(clf_text).get("in_domain", True)
        except json.JSONDecodeError:
            is_in_domain = True
        
        if not is_in_domain:
            # STRICT REQUIREMENT FOR DOMAIN REJECTION
            yield 'data: {"chunk": "This system is designed to answer questions related to the provided dataset only."}\n\n'
            return
    except Exception as e:
        print(f"Classifier error: {e}")
        # Fail open
        pass

    # ── Stage 2: SQL Generation ──
    try:
        yield 'data: {"status": "Generating query..."}\n\n'
        
        sql_res = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SQL_SYSTEM_PROMPT},
                {"role": "user", "content": f"{hist_context}User Query: {message}"}
            ],
            temperature=0,
            max_tokens=1000
        )
        raw_sql = sql_res.choices[0].message.content.strip()
        
        # Clean up if model leaked markdown
        if raw_sql.startswith("```sql"):
            raw_sql = raw_sql[6:]
        if raw_sql.startswith("```"):
            raw_sql = raw_sql[3:]
        if raw_sql.endswith("```"):
            raw_sql = raw_sql[:-3]
        raw_sql = raw_sql.strip()

        yield f'data: {{"status": "Executing SQL...", "sql": {json.dumps(raw_sql)}}}\n\n'
        
        # TERMINAL LOGGING FOR DEBUG
        print(f"\n[DEBUG] MESSAGE: {message}")
        print(f"[DEBUG] SQL: {raw_sql}")

        # Execute Query
        db_results = execute_sql(raw_sql)
        
        print(f"[DEBUG] RESULTS COUNT: {len(db_results)}")

        # Check for empty results
        if not db_results:
            db_results_str = "No records found matching the query."
        else:
            db_results_str = json.dumps(db_results, default=str)
            
    except Exception as e:
        error_payload = json.dumps({"chunk": f"Error generating or executing query: {str(e)}"})
        yield f"data: {error_payload}\n\n"
        return

    # ── Stage 3: Answer Synthesis (Streaming) ──
    try:
        yield 'data: {"status": "Synthesizing answer..."}\n\n'
        
        prompt = f"""
{hist_context}
User Question: {message}

Generated SQL:
{raw_sql}

Database Results:
{db_results_str}

Synthesize a response for the user.
"""
        response_stream = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2048,
            stream=True
        )
        
        iterator = iter(response_stream)
        while True:
            try:
                chunk = next(iterator)
                if hasattr(chunk, "choices") and chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta and hasattr(delta, "content") and delta.content:
                        payload = json.dumps({"chunk": delta.content})
                        yield f"data: {payload}\n\n"
            except StopIteration:
                break
            except IndexError:
                # HuggingFace sometimes throws IndexError on the final empty chunk
                break
            except Exception as e:
                print(f"Ignored streaming error: {e}")
                break
                
    except Exception as e:
        error_payload = json.dumps({"chunk": f"\n\nError synthesizing response: {str(e)}"})
        yield f"data: {error_payload}\n\n"
