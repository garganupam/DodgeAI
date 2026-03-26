import sqlite3
import json
import networkx as nx
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "rajjo.db")

class GraphStore:
    """In-memory NetworkX wrapper over SQLite graph data."""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.graph = nx.DiGraph()
        self._load_graph()
        
    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _load_graph(self):
        """Loads all nodes and edges from SQLite into NetworkX."""
        if not os.path.exists(self.db_path):
            print(f"⚠ Warning: Database {self.db_path} not found. Run etl.py first.")
            return

        with self._get_connection() as conn:
            # Load Nodes
            cur = conn.execute("SELECT id, entity_type, label, properties_json FROM nodes")
            node_count = 0
            for row in cur:
                props = json.loads(row["properties_json"])
                self.graph.add_node(
                    row["id"], 
                    entity_type=row["entity_type"], 
                    label=row["label"], 
                    **props
                )
                node_count += 1
                
            # Load Edges
            cur = conn.execute("SELECT source_id, target_id, relationship_type, weight FROM edges")
            edge_count = 0
            for row in cur:
                self.graph.add_edge(
                    row["source_id"], 
                    row["target_id"], 
                    relationship_type=row["relationship_type"],
                    weight=row["weight"]
                )
                edge_count += 1
                
        print(f"GraphStore initialized with {node_count} nodes and {edge_count} edges.")

    def get_node(self, node_id: str) -> dict | None:
        """Get a single node with its properties."""
        if node_id in self.graph:
            return {"id": node_id, **self.graph.nodes[node_id]}
        return None

    def get_nodes_by_type(self, entity_type: str, limit: int = 50, offset: int = 0) -> list[dict]:
        """Get a paginated list of nodes by their entity_type."""
        nodes = []
        for n, data in self.graph.nodes(data=True):
            if data.get("entity_type") == entity_type:
                nodes.append({"id": n, **data})
        
        # Sort by ID for consistent pagination
        nodes.sort(key=lambda x: x["id"])
        return nodes[offset:offset+limit]

    def expand_node(self, node_id: str) -> dict:
        """Returns the node, its incoming/outgoing edges, and neighboring nodes."""
        if node_id not in self.graph:
            return {"error": f"Node {node_id} not found."}

        center_node = {"id": node_id, **self.graph.nodes[node_id]}
        edges = []
        neighbors = {}

        # Outgoing edges
        for target, edge_data in self.graph[node_id].items():
            edges.append({
                "source": node_id, 
                "target": target, 
                **edge_data
            })
            neighbors[target] = {"id": target, **self.graph.nodes[target]}

        # Incoming edges
        for source, source_edges in self.graph.pred[node_id].items():
            edges.append({
                "source": source, 
                "target": node_id, 
                **source_edges
            })
            neighbors[source] = {"id": source, **self.graph.nodes[source]}

        return {
            "center_node": center_node,
            "neighbors": list(neighbors.values()),
            "edges": edges
        }

    def get_shortest_path(self, from_id: str, to_id: str) -> dict:
        """Finds shortest path between two nodes, returning nodes and edges."""
        if from_id not in self.graph or to_id not in self.graph:
            return {"error": "One or both nodes not found."}
            
        try:
            # Undirected search because SAP relationships might go either way
            # (e.g. Order -> Customer vs Customer -> Order)
            path_nodes = nx.shortest_path(self.graph.to_undirected(), source=from_id, target=to_id)
            
            nodes = [{"id": n, **self.graph.nodes[n]} for n in path_nodes]
            edges = []
            
            # Extract the actual directed edges that make up this path
            for i in range(len(path_nodes) - 1):
                u = path_nodes[i]
                v = path_nodes[i+1]
                
                # Check actual direction in the DiGraph
                if self.graph.has_edge(u, v):
                    edges.append({"source": u, "target": v, **self.graph[u][v]})
                elif self.graph.has_edge(v, u):
                    edges.append({"source": v, "target": u, **self.graph[v][u]})
                    
            return {
                "path_found": True,
                "nodes": nodes,
                "edges": edges
            }
        except nx.NetworkXNoPath:
            return {"path_found": False, "error": "No path exists between these nodes."}

    def get_entire_graph(self) -> dict:
        """Returns all nodes and edges in the graph."""
        nodes = []
        for n, data in self.graph.nodes(data=True):
            nodes.append({"id": n, **data})
            
        edges = []
        for u, v, data in self.graph.edges(data=True):
            edges.append({"source": u, "target": v, **data})
            
        return {"nodes": nodes, "edges": edges}

    def get_stats(self) -> dict:
        """Return basic graph statistics."""
        node_counts = {}
        for _, data in self.graph.nodes(data=True):
            etype = data.get("entity_type", "Unknown")
            node_counts[etype] = node_counts.get(etype, 0) + 1
            
        edge_counts = {}
        for _, _, data in self.graph.edges(data=True):
            rtype = data.get("relationship_type", "Unknown")
            edge_counts[rtype] = edge_counts.get(rtype, 0) + 1
            
        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "node_types": node_counts,
            "edge_types": edge_counts
        }

# Singleton instance for the FastAPI app to import
graph_db = None

def get_graph_store() -> GraphStore:
    global graph_db
    if graph_db is None:
        graph_db = GraphStore()
    return graph_db

# Simple test stub
if __name__ == "__main__":
    gs = GraphStore()
    print(json.dumps(gs.get_stats(), indent=2))
