# DodgeAI - Technical Architecture & Design Decisions

This document outlines the core technical decisions, architectural patterns, and security guardrails implemented in the DodgeAI SAP Analytics platform.

## 🏗 Architectural Decisions

### 1. Decoupled Graph-Ready Stack
- **Backend (FastAPI)**: Chosen for its native support for asynchronous operations and Server-Sent Events (SSE). This is critical for streaming LLM responses while simultaneously processing graph queries.
- **Frontend (React + Cytoscape.js)**: While many graph tools are heavy, Cytoscape.js provides a high-performance, customizable canvas that handles hundreds of nodes with ease, essential for mapping complex SAP Order-to-Cash flows.

### 2. Hybrid Data Layer (SQL + Graph)
- **SQLite**: Stores the structured relational data (Sales Orders, Invoices, Payments). It was chosen for its zero-configuration overhead and portability, making the entire analytics engine "plug-and-play."
- **NetworkX (In-Memory Graph)**: On startup, the system loads the relational links into an in-memory NetworkX graph. This allows for **instantaneous pathfinding** (e.g., "Find how Order X became Payment Y") without expensive recursive SQL joins.

## 🗄 Database Design & "Shadow Nodes"
One unique challenge in SAP data is missing or incomplete records.
- **Shadow Node Strategy**: If a billing item references a Sales Order that isn't in the main `sales_orders` table, the ETL automatically generates a "Shadow Node." This ensures that the visual document flow remains unbroken even if specific header records are missing.
- **Relational Integrity**: We maintain specialized tables like `billing_document_items` to avoid the "ambiguous join" problem common in flat-file SAP exports.

## 🧠 LLM Prompting Strategy
The system uses a highly specialized prompting strategy to transform natural language into precision SQL:
- **Schema Injection**: The exact SQLite schema and relationship types (e.g., `BILLED_AS`, `SETTLED_BY`) are injected into every prompt.
- **ID Canonicalization**: The LLM is instructed to handle SAP ID prefixes (`ORD-`, `INV-`, `DEL-`) autonomously. It identifies whether a user is asking for a "document" or a "flow" and adjusts the SQL accordingly.
- **Complex Flow Tracing**: Instead of simple lookups, the LLM is trained to identify the central "Sales Order" as the anchor for all end-to-end traces.

## 🛡 Security & Guardrails

### 1. Two-Step Intent Classification
Before any SQL is generated, the system runs a **Domain Classifier**. If a user asks a question unrelated to SAP Order-to-Cash (e.g., "What is the weather?"), the system rejects it immediately. This prevents prompt-injection attacks and reduces token cost.

### 2. Read-Only Execution Environment
The database connection used by the LLM pipeline is strictly **read-only**. Even if an LLM were manipulated into generating a `DELETE` or `DROP` statement, the SQLite engine would block the execution at the driver level.

### 3. Syntax Validation
The system validates the generated SQL against the injected schema before execution. If the LLM generates a non-existent column, the backend catches the error and provides a "soft failure" message rather than crashing or returning garbled data.

---
