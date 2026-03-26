import React, { useState, useEffect, useRef } from 'react';
import { Send, MoreHorizontal } from 'lucide-react';
import { marked } from 'marked';
import DOMPurify from 'dompurify';

export default function ChatPanel({ initialInput, onNodesMentioned }) {
  const [messages, setMessages] = useState([
    { 
      role: 'ai', 
      content: 'Hi! I can help you analyze the **Order to Cash** process.' 
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [apiStatus, setApiStatus] = useState('');
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (initialInput) {
      setInput(initialInput);
    }
  }, [initialInput]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, apiStatus]);

  // Sync node mentions whenever messages update
  useEffect(() => {
    // Collect all mentioned IDs from both User and AI messages
    const ids = new Set();
    const idRegex = /(ORD-\d+|\d{6,12}|CUST-\d+|PROD-\w+|DEL-\d+|INV-\d+|PAY-\d+)/g;
    messages.forEach(msg => {
      const matches = msg.content.match(idRegex);
      if (matches) {
        matches.forEach(m => {
          // Attempt to canonicalize
          if (/^\d{6}$/.test(m)) ids.add(`ORD-${m}`);
          else if (/^\d{9}$/.test(m)) ids.add(`CUST-${m}`);
          else ids.add(m);
        });
      }
    });
    if (onNodesMentioned && ids.size > 0) {
      onNodesMentioned(Array.from(ids));
    }
  }, [messages, onNodesMentioned]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);
    setApiStatus('Connecting...');

    try {
      // Build history context (last 5 message contents only)
      const history = messages.slice(-5).map(m => ({ role: m.role, content: m.content }));
      
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      const response = await fetch(`${apiBaseUrl}/query/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMessage, history })
      });

      if (!response.ok) throw new Error("API Network Error");

      // Set up SSE reading
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let aiResponseContent = "";

      setMessages(prev => [...prev, { role: 'ai', content: '' }]);

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value, { stream: true });
        // Split by the SSE 'data: ' prefix
        const lines = chunk.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.substring(6));
              
              if (data.status) {
                setApiStatus(data.status);
              }
              if (data.chunk) {
                aiResponseContent += data.chunk;
                setApiStatus(''); // clear loading status
                // Update the last message
                setMessages(prev => {
                  const newMsgs = [...prev];
                  newMsgs[newMsgs.length - 1].content = aiResponseContent;
                  return newMsgs;
                });
              }
            } catch (e) {
               console.error("JSON parse error on stream chunk:", line);
            }
          }
        }
      }
    } catch (err) {
      setMessages(prev => [...prev, { role: 'ai', content: `**Error:** connecting to the server. Is the FastAPI backend running on port 8000?` }]);
    } finally {
      setIsLoading(false);
      setApiStatus('');
    }
  };

  // Convert markdown and attach some custom highlight spans to node IDs
  const renderMessageContent = (content) => {
    let cleanHtml = DOMPurify.sanitize(marked.parse(content));
    return { __html: cleanHtml };
  };

  return (
    <>
      <div className="chat-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div className="chat-title">Chat with Graph</div>
          <MoreHorizontal size={20} color="var(--text-muted)" />
        </div>
        <div className="chat-subtitle">Order to Cash</div>
      </div>
      
      <div className="chat-messages">
        {messages.map((m, idx) => (
          <div key={idx} className={`message-row ${m.role}`}>
            
            {m.role === 'ai' ? (
               <div className="avatar ai">D</div>
            ) : (
               <div className="avatar user">You</div>
            )}
            
            <div className="message-content-wrapper">
              <div className="message-sender">
                {m.role === 'ai' ? 'Dodge AI' : 'You'}
                {m.role === 'ai' && <span className="message-role-tag">Graph Agent</span>}
              </div>
              <div className="message">
                {m.content === '' && isLoading && idx === messages.length - 1 ? (
                   <span style={{fontStyle: 'italic', opacity: 0.5}}>Thinking...</span>
                ) : (
                   <div dangerouslySetInnerHTML={renderMessageContent(m.content)} />
                )}
              </div>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-container">
        <div className="input-wrapper">
          <div className={`status-indicator ${isLoading ? 'loading' : ''}`}>
             <div className="dot"></div>
             {isLoading ? (apiStatus || 'Connecting...') : 'Dodge AI is awaiting instructions'}
          </div>
          
          <form onSubmit={handleSubmit} className="chat-form">
            <input
              type="text"
              className="chat-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Analyze anything"
              disabled={isLoading}
            />
            <button type="submit" className="chat-submit" disabled={!input.trim() || isLoading}>
              Send
            </button>
          </form>
        </div>
      </div>
    </>
  );
}
