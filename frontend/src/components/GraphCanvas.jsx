import React, { useEffect, useRef, useState } from 'react';
import cytoscape from 'cytoscape';
import dagre from 'cytoscape-dagre';
import { Network } from 'lucide-react';

// Register layout extension
cytoscape.use(dagre);

export default function GraphCanvas({ onNodeClick, highlightedNodeIds, selectedNode, isFullScreen }) {
  const containerRef = useRef(null);
  const cyRef = useRef(null);
  const [loading, setLoading] = useState(true);
  const [elements, setElements] = useState([]);

  // Fetch initial nodes
  useEffect(() => {
    const fetchNodes = async () => {
      try {
        const res = await fetch('http://localhost:8000/graph/all');
        const data = await res.json();
        setElements(data.elements);
        setLoading(false);
      } catch (err) {
        console.error("Failed to fetch initial graph:", err);
        setLoading(false);
      }
    };
    fetchNodes();
  }, []);

  // Initialize Cytoscape
  useEffect(() => {
    if (loading || !containerRef.current || !elements.length) return;

    if (cyRef.current) {
      cyRef.current.destroy();
    }

    const typeColors = {
      Order: '#3b82f6',
      Customer: '#10b981',
      Product: '#8b5cf6',
      Delivery: '#f59e0b',
      Invoice: '#ef4444',
      Payment: '#06b6d4',
      Plant: '#d946ef'
    };

    const cy = cytoscape({
      container: containerRef.current,
      elements: elements,
      style: [
        {
          selector: 'node',
          style: {
            'background-color': '#ffffff',
            'border-color': (ele) => typeColors[ele.data('type')] || '#94a3b8',
            'border-width': 1.5,
            'width': 6,
            'height': 6,
            'label': '', // no label by default to match clean dot look
            'transition-property': 'background-color, border-color, border-width, width, height, opacity',
            'transition-duration': 0.2
          }
        },
        {
          selector: 'edge',
          style: {
            'width': 1,
            'line-color': '#bfdbfe', /* Pale blue */
            'curve-style': 'bezier',
            'transition-property': 'width, line-color, opacity',
            'transition-duration': 0.2
          }
        },
        {
          selector: '.highlighted',
          style: {
            'width': 14,
            'height': 14,
            'border-width': 3,
            'border-color': (ele) => typeColors[ele.data('type')] || '#0f172a',
            'background-color': '#ffffff',
            'z-index': 100
          }
        },
        {
          selector: 'edge.highlighted',
          style: {
            'width': 3,
            'line-color': '#3b82f6',
            'z-index': 99
          }
        },
        {
          selector: '.dimmed',
          style: {
            'opacity': 0.15
          }
        }
      ],
      layout: {
        name: 'dagre',
        rankDir: 'LR',
        nodeSep: 40,
        rankSep: 120
      },
      minZoom: 0.1,
      maxZoom: 4
    });

    // Event listeners
    cy.on('tap', 'node', (evt) => {
      const node = evt.target;
      if (onNodeClick) onNodeClick(node.data());
    });

    cy.on('mouseover', 'node', (e) => {
      document.body.style.cursor = 'pointer';
    });

    cy.on('mouseout', 'node', () => {
      document.body.style.cursor = 'default';
    });

    cyRef.current = cy;

    return () => {
      document.body.style.cursor = 'default';
      cy.destroy();
    };
  }, [loading, elements]); // Re-run if totally new elements are loaded

  // Handle cross-component highlighting
  useEffect(() => {
    if (!cyRef.current || !highlightedNodeIds) return;
    const cy = cyRef.current;
    
    cy.elements().removeClass('highlighted dimmed');
    
    if (highlightedNodeIds.length > 0) {
      let foundEles = cy.collection();
      highlightedNodeIds.forEach(id => {
        foundEles = foundEles.union(cy.getElementById(id));
      });
      
      if (foundEles.length > 0) {
        // Dim everything
        cy.elements().addClass('dimmed');
        
        // Highlight nodes
        foundEles.removeClass('dimmed').addClass('highlighted');
        
        // Find connecting edges between these nodes and highlight them too
        const connectingEdges = foundEles.edgesWith(foundEles);
        connectingEdges.removeClass('dimmed').addClass('highlighted');

        // Optional: also highlight incident edges to give context
        const incidentEdges = foundEles.connectedEdges();
        incidentEdges.removeClass('dimmed').addClass('highlighted');
        
        // Add neighbors to the non-dimmed collection so we can see what they connect to
        const neighbors = incidentEdges.connectedNodes();
        neighbors.removeClass('dimmed').addClass('highlighted'); // semi-highlight or full

        const allToFit = foundEles.union(neighbors);

        cy.animate({
          fit: { eles: allToFit, padding: 100 },
          duration: 700,
          easing: 'ease-out-cubic'
        });
      }
    } else {
       // Reset view to fit all if no highlights
       cy.animate({
         fit: { padding: 50 },
         duration: 500
       });
    }
  }, [highlightedNodeIds]);

  const handleExpandNode = async (nodeId) => {
    try {
      const res = await fetch(`http://localhost:8000/graph/expand/${nodeId}`);
      if (!res.ok) return;
      const data = await res.json();
      
      if (data.elements && data.elements.length > 0 && cyRef.current) {
        // Only append new elements
        cyRef.current.add(data.elements);
        // Rerun layout
        cyRef.current.layout({
          name: 'dagre',
          rankDir: 'LR',
          animate: true,
          animationDuration: 500
        }).run();
      }
    } catch (err) {
      console.error("Expand error:", err);
    }
  };

  // Listen for fullscreen toggle to resize
  useEffect(() => {
    if (cyRef.current) {
      setTimeout(() => cyRef.current.resize(), 50);
    }
  }, [isFullScreen]);

  return (
    <div style={{ 
      width: '100%', 
      height: '100%', 
      position: 'relative',
      background: '#ffffff'
    }}>
      {/* We only render "Load Neighbors" here since the layout moved other buttons to App.jsx */}
      <div style={{ position: 'absolute', bottom: 20, right: 20, zIndex: 10 }}>
        {selectedNode && (
          <button className="toolbar-btn" onClick={() => handleExpandNode(selectedNode.id)}>
            <Network size={14} /> Load Neighbors
          </button>
        )}
      </div>

      {loading ? (
        <div style={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center' }}>
          <div className="status-indicator loading">
             <div className="dot"></div>
             Loading Mapping Data...
          </div>
        </div>
      ) : (
        <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
      )}
    </div>
  );
}
