import { useState, useEffect } from 'react';
import type { SystemStats } from '../../types';
import { fetchStats } from '../../services/api';

export default function StatsPanel() {
  const [stats, setStats] = useState<SystemStats | null>(null);

  useEffect(() => {
    fetchStats()
      .then(setStats)
      .catch(console.error);
  }, []);

  if (!stats) return null;

  const cards = [
    { label: '文档总数', value: stats.total_sources, color: '#3b82f6' },
    { label: '已索引', value: stats.indexed_sources, color: '#22c55e' },
    { label: '向量块数', value: stats.total_chunks, color: '#8b5cf6' },
    { label: '错误', value: stats.error_sources, color: '#ef4444' },
  ];

  return (
    <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
      {cards.map((card) => (
        <div key={card.label} style={{
          flex: 1,
          padding: '16px 20px',
          backgroundColor: '#fff',
          borderRadius: 12,
          border: '1px solid #e5e7eb',
          textAlign: 'center',
        }}>
          <div style={{ fontSize: 28, fontWeight: 700, color: card.color }}>
            {card.value}
          </div>
          <div style={{ fontSize: 13, color: '#94a3b8', marginTop: 4 }}>
            {card.label}
          </div>
        </div>
      ))}
    </div>
  );
}
