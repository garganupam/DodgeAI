***1. Project Vision***
Goal: Build a graph-first SAP Order-to-Cash (O2C) analytics platform with an LLM-driven Natural Language interface.

***2. The Implementation Prompts***
**A. Graph & Relational Data Ingestion (ETL)**
"Create an ingestion script 

etl.py
 to process SAP JSONL files into a hybrid SQLite + NetworkX architecture. Map the following document flow: Order --(DELIVERED_VIA)--> Delivery --(BILLED_AS)--> Invoice --(SETTLED_BY)--> Payment.

CRITICAL REFINEMENT: If a billing item references a Sales Order that is missing its header record, implement a 'Shadow Node' functionality to create a placeholder dot on the graph. Use referenceSdDocument for mapping."

**B. LLM Pipeline & Prompt Engineering**
"Develop an LLM pipeline in 

llm_pipeline.py
 using Qwen 2.5 on HuggingFace.

**Instructions:**

Translate user questions into valid SQLite.
Inject a detailed schema including a dedicated billing_document_items table for accurate material-based results.
Tracing Strategy: If asked to trace starting from an Invoice ID, the AI must first identify the parent Sales Order using the edges table and then expand to all related documents."

**C. Frontend Graph Visualization**
"Develop a React frontend using cytoscape.js. The interface should feature a 70/30 split between a graph canvas and a chat panel.

**UX Enhancements:**

Nodes should glow/highlight when their IDs are mentioned in the chat.
Implement a 'Node Inspector' for detailed document drill-downs.
Handle SPA routing with Vercel configuration."

***3. Critical Fix Archive (The "Stale Process" & "Key Mismatch" Resolution)***
Process Management: Discovered that a 35-hour-old background process was hijacking the port, causing new code changes to be ignored. Implemented a global taskkill /F /IM python.exe cleanup protocol.
Field Mapping Bug: Resolved the 'zero records found' issue by identifying that the dataset uses referenceSdDocument (SAP Standard) instead of the generic salesDocument key.

***4. Architectural Stack***
Backend: FastAPI, NetworkX, SQLite3.
Frontend: React, Vite, Cytoscape.js.
Synthesizer: HuggingFace Inference API (Qwen 2.5 72B).


***Normal Prompts***

1. In the pipeline convert the code that takes huggingface LLm api key
2. Make sure the table schema is correct and the data is ingested properly
3. The table must be connected to each other in a way that we can trace the flow of the data
4. The frontend must be able to display the graph and the chat panel
5. The chat panel must be able to display the response from the LLM
7. The nodes must be color-coded based on the type of document
9. The graph must be able to display the data in a way that is easy to understand
11. The graph should show the  conncetions between the data related in the giving dataset from any folder 
12. The folders must be interconnected to each other so that data can be retrived easily. 
