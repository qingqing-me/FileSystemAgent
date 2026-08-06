import { useState, useEffect } from 'react';
import type { DocumentSource } from '../../types';
import { fetchSources } from '../../services/api';

export default function SourceList() {
  const [sources, setSources] = useState<DocumentSource[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSources();
  }, []);

  const loadSources = async () => {
    try {
      const data = await fetchSources();
      setSources(data);
    } catch (e) {
      console.error('Failed to load sources:', e);
    } finally {
      setLoading(false);
    }
  };

  const statusBadge = (status: string) => {
    const colors: Record<string, string> = {
      indexed: '#22c55e',
      indexing: '#f59e0b',
      pending: '#94a3b8',
      error: '#ef4444',
    };
    const labels: Record<string, string> = {
      indexed: '已索引',
      indexing: '索引中',
      pending: '待处理',
      error: '错误',
    };
    return (
      <span style={{
        padding: '2px 8px',
        borderRadius: 10,
        fontSize: 12,
        fontWeight: 600,
        backgroundColor: (colors[status] || '#94a3b8') + '20',
        color: colors[status] || '#94a3b8',
      }}>
        {labels[status] || status}
      </span>
    );
  };

  if (loading) return <div style={{ padding: 20, color: '#94a3b8' }}>加载中...</div>;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h3 style={{ margin: 0 }}>📄 文档列表 ({sources.length})</h3>
        <button onClick={loadSources} style={styles.refreshBtn}>刷新</button>
      </div>
      <div style={styles.table}>
        <div style={styles.tableHeader}>
          <span style={{ flex: 3 }}>标题</span>
          <span style={{ flex: 1 }}>部门</span>
          <span style={{ flex: 1 }}>日期</span>
          <span style={{ flex: 1 }}>分块数</span>
          <span style={{ flex: 1 }}>状态</span>
        </div>
        {sources.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center', color: '#94a3b8' }}>
            暂无文档，请运行摄入脚本导入文件
          </div>
        ) : (
          sources.map((s) => (
            <div key={s.id} style={styles.tableRow}>
              <span style={{ flex: 3, fontWeight: 500 }}>{s.title}</span>
              <span style={{ flex: 1, color: '#64748b' }}>{s.department}</span>
              <span style={{ flex: 1, color: '#64748b' }}>{s.date}</span>
              <span style={{ flex: 1, color: '#64748b' }}>{s.chunk_count}</span>
              <span style={{ flex: 1 }}>{statusBadge(s.status)}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  refreshBtn: {
    padding: '6px 16px',
    border: '1px solid #d1d5db',
    borderRadius: 8,
    backgroundColor: '#fff',
    cursor: 'pointer',
    fontSize: 13,
  },
  table: {
    border: '1px solid #e5e7eb',
    borderRadius: 10,
    overflow: 'hidden',
  },
  tableHeader: {
    display: 'flex',
    padding: '10px 16px',
    backgroundColor: '#f8fafc',
    fontWeight: 600,
    fontSize: 13,
    color: '#475569',
    borderBottom: '1px solid #e5e7eb',
  },
  tableRow: {
    display: 'flex',
    padding: '10px 16px',
    borderBottom: '1px solid #f1f5f9',
    fontSize: 14,
    alignItems: 'center',
  },
};
