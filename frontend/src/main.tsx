import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

// Minimal global styles
const style = document.createElement('style');
style.textContent = `
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { margin: 0; font-family: "SimSun", "宋体", "Songti SC", serif; }
  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { background: #94a3b8; }

  /* Markdown 渲染 — 紧凑 */
  .markdown-body { font-size: 15px; line-height: 1.6; color: #1e293b; }
  .markdown-body > :first-child { margin-top: 0; }
  .markdown-body > :last-child { margin-bottom: 0; }
  .markdown-body p { margin: 0 0 6px; }
  .markdown-body p:last-child { margin-bottom: 0; }
  .markdown-body h1, .markdown-body h2, .markdown-body h3,
  .markdown-body h4, .markdown-body h5, .markdown-body h6 {
    margin: 10px 0 4px; font-weight: 700; line-height: 1.4;
  }
  .markdown-body h1 { font-size: 1.25em; }
  .markdown-body h2 { font-size: 1.18em; }
  .markdown-body h3 { font-size: 1.1em; }
  .markdown-body h4, .markdown-body h5, .markdown-body h6 { font-size: 1em; }
  .markdown-body ul, .markdown-body ol { margin: 0 0 6px; padding-left: 22px; }
  .markdown-body li { margin: 2px 0; }
  .markdown-body strong { font-weight: 700; }
  .markdown-body em { font-style: italic; }
  .markdown-body a { color: #2563eb; text-decoration: none; }
  .markdown-body a:hover { text-decoration: underline; }
  .markdown-body code {
    background: #f1f5f9; padding: 1px 5px; border-radius: 4px;
    font-family: "SF Mono", Consolas, Menlo, monospace; font-size: 0.9em;
  }
  .markdown-body pre {
    background: #0f172a; color: #e2e8f0; padding: 10px 14px;
    border-radius: 8px; overflow-x: auto; margin: 6px 0;
  }
  .markdown-body pre code { background: none; padding: 0; color: inherit; }
  .markdown-body blockquote {
    border-left: 3px solid #2563eb; padding-left: 12px; margin: 6px 0;
    color: #64748b;
  }
  .markdown-body table { border-collapse: collapse; margin: 6px 0; width: 100%; }
  .markdown-body th, .markdown-body td {
    border: 1px solid #e2e8f0; padding: 4px 8px; text-align: left;
  }
  .markdown-body th { background: #f8fafc; font-weight: 600; }

  @keyframes pulse {
    0%, 100% { opacity: 0.3; }
    50% { opacity: 1; }
  }
`;
document.head.appendChild(style);

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
