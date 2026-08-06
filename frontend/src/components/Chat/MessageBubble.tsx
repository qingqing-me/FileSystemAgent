import ReactMarkdown from 'react-markdown';
import type { Message } from '../../types';
import SourceCitation from './SourceCitation';

interface Props {
  message: Message;
}

export default function MessageBubble({ message }: Props) {
  const isUser = message.role === 'user';

  return (
    <div style={{
      ...styles.wrapper,
      justifyContent: isUser ? 'flex-end' : 'flex-start',
    }}>
      <div style={{
        ...styles.bubble,
        backgroundColor: isUser ? '#2563eb' : '#f1f5f9',
        color: isUser ? '#fff' : '#1e293b',
        borderBottomRightRadius: isUser ? 4 : 14,
        borderBottomLeftRadius: isUser ? 14 : 4,
      }}>
        {isUser ? (
          <div style={styles.content}>{message.content}</div>
        ) : (
          <div className="markdown-body" style={{ fontSize: 15, lineHeight: 1.6 }}>
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        )}
        {!isUser && message.sources.length > 0 && (
          <SourceCitation sources={message.sources} />
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    display: 'flex',
    marginBottom: 16,
    padding: '0 16px',
  },
  bubble: {
    maxWidth: '80%',
    padding: '12px 16px',
    borderRadius: 14,
    fontSize: 15,
    lineHeight: 1.6,
    wordBreak: 'break-word',
  },
  content: {
    whiteSpace: 'pre-wrap',
  },
};
