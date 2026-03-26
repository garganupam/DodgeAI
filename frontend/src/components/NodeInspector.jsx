import React from 'react';
import { X } from 'lucide-react';

export default function NodeInspector({ node, onClose }) {
  if (!node) return null;

  // Render properties nicely
  const skipProps = ['id', 'label', 'entity_type', 'type'];
  
  return (
    <div className="inspector-panel">
      <div className="inspector-header">
        <div className="inspector-title">
          <span className="inspector-type">
            {node.entity_type || 'Unknown Entity'}
          </span>
        </div>
        <button className="close-btn" onClick={onClose}><X size={16} /></button>
      </div>
      
      <div className="inspector-content">
        <div className="prop-row">
          <div className="prop-label">Entity</div>
          <div className="prop-val">{node.entity_type}</div>
        </div>
        <div className="prop-row">
          <div className="prop-label">Primary ID</div>
          <div className="prop-val" style={{fontFamily: 'monospace'}}>{node.id}</div>
        </div>

        {Object.entries(node).map(([key, val]) => {
          if (skipProps.includes(key)) return null;
          // Skip complex objects or empty strings
          if (typeof val === 'object' || val === '' || val === null) return null;
          
          // Format numeric amounts for currency
          let displayVal = val;
          if ((key.toLowerCase().includes('amount') || key.toLowerCase().includes('total')) && typeof val === 'number') {
            displayVal = `$${val.toLocaleString()}`;
          }
          
          // Prettify keys (camelCase to Title Case approx)
          let displayKey = key.replace(/([A-Z])/g, ' $1').replace(/^./, function(str){ return str.toUpperCase(); }).replace(/_/g, ' ');

          return (
            <div className="prop-row" key={key}>
              <div className="prop-label">{displayKey}</div>
              <div className="prop-val">{displayVal}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
