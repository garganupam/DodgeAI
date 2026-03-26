import React, { useState, useEffect } from 'react';
import GraphCanvas from './components/GraphCanvas';
import ChatPanel from './components/ChatPanel';
import NodeInspector from './components/NodeInspector';
import { Layers, Maximize, Minimize, AlignLeft } from 'lucide-react';

export default function App() {
  const [selectedNode, setSelectedNode] = useState(null);
  const [highlightedNodeIds, setHighlightedNodeIds] = useState([]);
  const [chatInputTrigger, setChatInputTrigger] = useState("");
  const [isFullScreen, setIsFullScreen] = useState(false);

  // When a node is clicked in the graph, open the inspector
  const handleNodeClick = (nodeData) => {
    setSelectedNode(nodeData);
    setChatInputTrigger(`${nodeData.id} - Find detailed information linked to this`);
  };

  const handleSetHighlights = React.useCallback((nodeIds) => {
    setHighlightedNodeIds(prev => {
      // Prevent infinite loop by not updating if values are the same
      if (prev.length === nodeIds.length && prev.every((v, i) => v === nodeIds[i])) {
        return prev;
      }
      return nodeIds;
    });
  }, []);

  return (
    <div className="app-container">
      {/* 70% Left Panel -> Graph */}
      <div className="graph-section" style={{ display: isFullScreen ? 'none' : 'block' }}>
        
        {/* Header Title path */}
        <div className="app-header-bar">
          <AlignLeft size={16} className="icon"/>
          <span>| Mapping / <strong>Order to Cash</strong></span>
        </div>

        {/* Floating Graph Controls */}
        <div className="graph-toolbar">
          <button 
            className="toolbar-btn" 
            onClick={() => setIsFullScreen(true)}
            title="Maximize Canvas"
          >
            <Maximize size={14} style={{transform: 'rotate(45deg)'}} />
            Maximize
          </button>
          
          <button 
            className="toolbar-btn dark" 
            onClick={() => setHighlightedNodeIds([])}
            title="Reset View / Show All"
          >
            <Layers size={14} />
            Show Entire Graph
          </button>
        </div>

        <GraphCanvas 
          onNodeClick={handleNodeClick} 
          highlightedNodeIds={highlightedNodeIds}
          selectedNode={selectedNode}
          isFullScreen={isFullScreen}
          onExitFullScreen={() => setIsFullScreen(false)}
        />

        {selectedNode && (
          <NodeInspector 
            node={selectedNode} 
            onClose={() => setSelectedNode(null)} 
          />
        )}
      </div>

      {/* 30% Right Panel -> Chat */}
      <div className="chat-section" style={{ display: isFullScreen ? 'none' : 'flex' }}>
        <ChatPanel 
          initialInput={chatInputTrigger} 
          onNodesMentioned={handleSetHighlights}
        />
      </div>

      {/* Fullscreen Overlay State */}
      {isFullScreen && (
         <div style={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', zIndex: 999, background: '#fff' }}>
            <div className="graph-toolbar" style={{ top: 20, left: 20 }}>
              <button className="toolbar-btn" onClick={() => setIsFullScreen(false)}>
                <Minimize size={14} style={{transform: 'rotate(45deg)'}} />
                Minimize
              </button>
              <button className="toolbar-btn dark" onClick={() => setHighlightedNodeIds([])}>
                <Layers size={14} /> Show Entire Graph
              </button>
            </div>
            
            <GraphCanvas 
              onNodeClick={handleNodeClick} 
              highlightedNodeIds={highlightedNodeIds}
              selectedNode={selectedNode}
              isFullScreen={isFullScreen}
            />
            
            {selectedNode && (
              <NodeInspector node={selectedNode} onClose={() => setSelectedNode(null)} />
            )}
         </div>
      )}
    </div>
  );
}
