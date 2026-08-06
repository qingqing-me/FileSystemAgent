import type { SourceInfo } from '../../types';

interface Props {
  sources: SourceInfo[];
}

export default function SourceCitation({ sources }: Props) {
  if (!sources.length) return null;

  return (
    <div style={styles.container}>
      <div style={styles.title}>📎 参考来源</div>
      <div style={styles.list}>
        {sources.map((s, i) => (
          <div key={i} style={styles.item}>
            <div style={styles.itemTitle}>
              [{i + 1}] {s.title}
            </div>
            <div style={styles.meta}>
              {s.department && `${s.department} · `}{s.date}
            </div>
            <div style={styles.snippet}>{s.snippet}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    marginTop: 12,
    padding: 12,
    backgroundColor: '#f8fafc',
    borderRadius: 8,
    border: '1px solid #e2e8f0',
  },
  title: {
    fontSize: 13,
    fontWeight: 600,
    color: '#475569',
    marginBottom: 8,
  },
  list: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  item: {
    padding: '6px 8px',
    backgroundColor: '#fff',
    borderRadius: 6,
    border: '1px solid #e2e8f0',
  },
  itemTitle: {
    fontSize: 13,
    fontWeight: 500,
    color: '#1e293b',
  },
  meta: {
    fontSize: 11,
    color: '#94a3b8',
    marginTop: 2,
  },
  snippet: {
    fontSize: 12,
    color: '#64748b',
    marginTop: 4,
    lineHeight: 1.5,
  },
};
