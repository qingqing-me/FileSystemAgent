import { useState, useRef, useEffect } from 'react';
import type { Message, SourceInfo } from '../../types';
import { sendMessage } from '../../services/api';
import ChatInput from './ChatInput';
import MessageBubble from './MessageBubble';

export default function ChatWindow() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [streaming, setStreaming] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [pendingSources, setPendingSources] = useState<SourceInfo[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streaming]);

  const handleSend = async (question: string) => {
    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: question,
      sources: [],
      createdAt: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    setStreaming('');
    setPendingSources([]);

    let fullAnswer = '';
    let sources: SourceInfo[] = [];

    await sendMessage(
      question,
      conversationId,
      (token) => {
        fullAnswer += token;
        setStreaming(fullAnswer);
      },
      (srcs) => {
        sources = srcs;
        setPendingSources(srcs);
      },
      () => {
        const assistantMsg: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: fullAnswer,
          sources,
          createdAt: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, assistantMsg]);
        setStreaming('');
        setPendingSources([]);
        setLoading(false);
      },
      (error) => {
        setStreaming(`❌ ${error}`);
        setLoading(false);
      },
    );
  };

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700 }}>📚 校园文件智能助手</h2>
        <span style={styles.subtitle}>广西大学官方文件查询</span>
      </div>

      {/* Messages */}
      <div style={styles.messageList}>
        {messages.length === 0 && !loading && (
          <div style={styles.empty}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>📖</div>
            <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>欢迎使用校园文件查询助手</div>
            <div style={{ fontSize: 14, color: '#94a3b8' }}>
              你可以问我关于学校规章制度、保研政策、奖学金评定等问题
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {/* Streaming answer */}
        {streaming && (
          <MessageBubble
            message={{
              id: 'streaming',
              role: 'assistant',
              content: streaming,
              sources: pendingSources,
              createdAt: '',
            }}
          />
        )}

        {/* Loading indicator (before first token) */}
        {loading && !streaming && (
          <div style={styles.thinking}>
            <span style={styles.dot}>●</span>
            <span style={styles.dot}>●</span>
            <span style={styles.dot}>●</span>
            <span style={{ marginLeft: 8, color: '#94a3b8' }}>思考中...</span>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <ChatInput onSend={handleSend} disabled={loading} />
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    maxWidth: 800,
    margin: '0 auto',
    backgroundColor: '#fff',
    boxShadow: '0 0 40px rgba(0,0,0,0.06)',
  },
  header: {
    padding: '16px 24px',
    borderBottom: '1px solid #e5e7eb',
    backgroundColor: '#fff',
    display: 'flex',
    alignItems: 'center',
    gap: 12,
  },
  subtitle: {
    fontSize: 12,
    color: '#94a3b8',
  },
  messageList: {
    flex: 1,
    overflowY: 'auto',
    padding: '16px 0',
  },
  empty: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    color: '#64748b',
  },
  thinking: {
    display: 'flex',
    alignItems: 'center',
    padding: '12px 24px',
  },
  dot: {
    fontSize: 8,
    color: '#94a3b8',
    marginRight: 4,
    animation: 'pulse 1.4s infinite',
  },
};
