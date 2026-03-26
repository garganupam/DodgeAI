from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os

from llm_pipeline import handle_chat_query_stream
from graph_store import get_graph_store

app = FastAPI(
    title="Rajjo SAP Analytics API",
    description="Graph-first querying over SAP Order-to-Cash data",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restrict for prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Graph Endpoints ────────────────────────────────────────────────────────

@app.get("/graph/stats")
async def get_stats():
    """Get high-level statistics of the in-memory graph."""
    gs = get_graph_store()
    return gs.get_stats()

@app.get("/graph/nodes")
async def get_nodes(
    type: str = Query("Order", description="Node entity_type (Order, Customer, Product, etc.)"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """Retrieve nodes by entity type with pagination."""
    gs = get_graph_store()
    nodes = gs.get_nodes_by_type(type, limit, offset)
    
    # Fast path: format nodes as cytoscape elements
    cy_elements = []
    for n in nodes:
        cy_elements.append({
            "data": {
                "id": n["id"],
                "label": n.get("label", n["id"]),
                "type": n.get("entity_type"),
                **n
            }
        })
    return {"nodes": cy_elements, "total": len(nodes), "limit": limit, "offset": offset}

@app.get("/graph/expand/{node_id}")
async def expand_node(node_id: str):
    """Return an ego-graph (immediate neighbors and connecting edges) for a single node."""
    gs = get_graph_store()
    res = gs.expand_node(node_id)
    
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
        
    cy_elements = []
    
    # Center node
    center = res["center_node"]
    cy_elements.append({
        "data": {
            "id": center["id"],
            "label": center.get("label", center["id"]),
            "type": center.get("entity_type"),
            **center
        }
    })
    
    # Neighbor nodes
    for n in res["neighbors"]:
        cy_elements.append({
            "data": {
                "id": n["id"],
                "label": n.get("label", n["id"]),
                "type": n.get("entity_type"),
                **n
            }
        })
        
    # Connecting edges
    for e in res["edges"]:
        # generate stable, unique ID for Cytoscape side
        edge_id = f"{e['source']}-{e['relationship_type']}-{e['target']}"
        cy_elements.append({
            "data": {
                "id": edge_id,
                "source": e["source"],
                "target": e["target"],
                "label": e["relationship_type"],
                "weight": e.get("weight", 1.0)
            }
        })
        
    return {"elements": cy_elements}

@app.get("/graph/path/{from_id}/{to_id}")
async def get_path(from_id: str, to_id: str):
    """Find the shortest path between two nodes in the graph."""
    gs = get_graph_store()
    res = gs.get_shortest_path(from_id, to_id)
    
    if not res.get("path_found"):
        raise HTTPException(status_code=404, detail=res.get("error"))
        
    cy_elements = []
    
    for n in res["nodes"]:
        cy_elements.append({
            "data": {
                "id": n["id"],
                "label": n.get("label", n["id"]),
                "type": n.get("entity_type"),
                **n
            }
        })
        
    for e in res["edges"]:
        edge_id = f"{e['source']}-{e['relationship_type']}-{e['target']}"
        cy_elements.append({
            "data": {
                "id": edge_id,
                "source": e["source"],
                "target": e["target"],
                "label": e["relationship_type"],
                "weight": e.get("weight", 1.0)
            }
        })
        
    return {"elements": cy_elements}


@app.get("/graph/all")
async def get_all_graph():
    """Retrieve the entire graph formatted for Cytoscape."""
    gs = get_graph_store()
    res = gs.get_entire_graph()
    
    cy_elements = []
    
    for n in res["nodes"]:
        cy_elements.append({
            "data": {
                "id": n["id"],
                "label": n.get("label", n["id"]),
                "type": n.get("entity_type"),
                **n
            }
        })
        
    for e in res["edges"]:
        edge_id = f"{e['source']}-{e.get('relationship_type', 'link')}-{e['target']}"
        cy_elements.append({
            "data": {
                "id": edge_id,
                "source": e["source"],
                "target": e["target"],
                "label": e.get("relationship_type"),
                "weight": e.get("weight", 1.0)
            }
        })
        
    return {"elements": cy_elements}

# ─── Query Endpoints ────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []  # [{"role": "user", "content": "..."}, ...]

@app.post("/query/chat")
async def chat_query(req: ChatRequest):
    """
    NL-to-SQL query pipeline with guardrails.
    Streams back data: {"status": "..."} followed by data: {"chunk": "..."}
    """
    return StreamingResponse(
        handle_chat_query_stream(req.message, req.history), 
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False if os.environ.get("PORT") else True)
