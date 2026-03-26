# DodgeAI - SAP Order-to-Cash Graph Analytics

DodgeAI is a graph-first, LLM-powered analytics platform for SAP Order-to-Cash (O2C) data. It allows users to trace document flows (Sales Order → Delivery → Invoice → Payment) and analyze bottlenecks using natural language.

## 🚀 Key Features

- **Natural Language Querying**: Query your SAP data as if you're talking to an expert.
- **Dynamic Graph Visualization**: Immediate visual feedback for document relationships and statuses.
- **Autonomous Path Tracing**: Intelligently connects disconnected document segments using a central Sales Order identification logic.
- **Shadow Node Support**: Automatically identifies missing header records and populates placeholders to maintain graph connectivity.

## 🛠 Tech Stack

- **Backend**: FastAPI (Python), SQLite3, NetworkX (Graph Store), HuggingFace Inference API (Qwen 2.5).
- **Frontend**: React (Vite), Cytoscape.js (Graph Engine), Lucide Icons, Vanilla CSS.

## 🧠 System Workflow

1.  **User Input**: User asks a question (e.g., *"Which products have the highest billing documents?"*).
2.  **NL-to-SQL Conversion**: A custom-prompted LLM (Qwen 2.5) translates the natural language into optimized SQLite queries.
3.  **Data Extraction**: The backend executes the SQL against `rajjo.db` (Invoices, Orders, Deliveries, Payments).
4.  **Graph Synthesis**: The system extracts the corresponding nodes and edges via **NetworkX**, identifying all connected document chains.
5.  **Response Synthesis**: The AI summarizes the findings, referencing specific IDs that the frontend uses to highlight the graph canvas.

## 📦 Project Structure

```text
DodgeAI/
├── backend/
│   ├── etl.py            # Data ingestion & Shadow Node generation
│   ├── main.py           # FastAPI application & CORS
│   ├── llm_pipeline.py   # SQL generation & Answer synthesis
│   ├── graph_store.py    # NetworkX graph operations
│   ├── rajjo.db          # SQLite persistent storage
│   └── requirements.txt  # Python dependencies
└── frontend/
    ├── src/
    │   ├── components/   # Graph & Chat UI components
    │   └── App.jsx       # Layout & Application state
    └── vercel.json       # Vercel deployment config
```

## ⚙️ Local Setup

### 1. Backend
```bash
cd backend
pip install -r requirements.txt
# Add HF_API_KEY to your .env file
python main.py
```

### 2. Frontend
```bash
cd frontend
npm install
npm run dev
```

## 🌐 Deployment

### 1. Railway (Backend)
1.  Connect your GitHub repo to **Railway**.
2.  Select the `/backend` directory.
3.  Add the `HF_API_KEY` environment variable.
4.  The `Procfile` will handle the rest.

### 2. Vercel (Frontend)
1.  Connect your GitHub repo to **Vercel**.
2.  Select the `/frontend` directory.
3.  Add the `VITE_API_BASE_URL` environment variable pointing to your Railway URL.

---
Built with ❤️ for SAP Analytics by Dodge AI Team.
