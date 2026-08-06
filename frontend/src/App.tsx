import { useState } from 'react';
import ChatWindow from './components/Chat/ChatWindow';
import SourceList from './components/Admin/SourceList';
import StatsPanel from './components/Admin/StatsPanel';

type Tab = 'chat' | 'admin';

export default function App() {
  const [tab, setTab] = useState<Tab>('chat');

  return (
    <div style={styles.root}>
      {/* Sidebar */}
      <nav style={styles.sidebar}>
        <div style={styles.logo}>📚 GXU Agent</div>
        <div style={styles.nav}>
          <button
            onClick={() => setTab('chat')}
            style={{
              ...styles.navBtn,
              backgroundColor: tab === 'chat' ? '#e0e7ff' : 'transparent',
              color: tab === 'chat' ? '#2563eb' : '#64748b',
            }}
          >
            💬 聊天
          </button>
          <button
            onClick={() => setTab('admin')}
            style={{
              ...styles.navBtn,
              backgroundColor: tab === 'admin' ? '#e0e7ff' : 'transparent',
              color: tab === 'admin' ? '#2563eb' : '#64748b',
            }}
          >
            ⚙️ 管理
          </button>
        </div>
      </nav>

      {/* Main content */}
      <main style={styles.main}>
        {tab === 'chat' ? (
          <ChatWindow />
        ) : (
          <div style={{ padding: 24, maxWidth: 900 }}>
            <StatsPanel />
            <SourceList />
          </div>
        )}
      </main>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  root: {
    display: 'flex',
    height: '100vh',
    backgroundColor: '#f1f5f9',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans SC", sans-serif',
  },
  sidebar: {
    width: 200,
    backgroundColor: '#fff',
    borderRight: '1px solid #e5e7eb',
    display: 'flex',
    flexDirection: 'column',
    padding: '20px 12px',
  },
  logo: {
    fontSize: 16,
    fontWeight: 700,
    color: '#1e293b',
    marginBottom: 32,
    padding: '0 8px',
  },
  nav: {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  },
  navBtn: {
    padding: '10px 12px',
    border: 'none',
    borderRadius: 8,
    fontSize: 14,
    cursor: 'pointer',
    textAlign: 'left',
    fontWeight: 500,
    background: 'none',
  },
  main: {
    flex: 1,
    overflow: 'hidden',
  },
};
