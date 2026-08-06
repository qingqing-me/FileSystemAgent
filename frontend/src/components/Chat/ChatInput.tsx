import { useState, useRef } from 'react';

interface Props {
  onSend: (question: string) => void;
  disabled: boolean;
}

export default function ChatInput({ onSend, disabled }: Props) {
  const [input, setInput] = useState('');
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setInput('');
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div style={styles.container}>
      <textarea
        ref={inputRef}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="输入你的问题，例如：保研需要什么条件？"
        rows={2}
        disabled={disabled}
        style={styles.textarea}
      />
      <button
        onClick={handleSend}
        disabled={disabled || !input.trim()}
        style={{
          ...styles.button,
          opacity: disabled || !input.trim() ? 0.5 : 1,
        }}
      >
        发送
      </button>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    gap: 12,
    padding: '16px 24px',
    borderTop: '1px solid #e5e7eb',
    backgroundColor: '#fff',
    alignItems: 'flex-end',
  },
  textarea: {
    flex: 1,
    padding: '10px 14px',
    border: '1px solid #d1d5db',
    borderRadius: 10,
    fontSize: 15,
    fontFamily: 'inherit',
    resize: 'none',
    outline: 'none',
    lineHeight: 1.5,
  },
  button: {
    padding: '10px 24px',
    backgroundColor: '#2563eb',
    color: '#fff',
    border: 'none',
    borderRadius: 10,
    fontSize: 15,
    cursor: 'pointer',
    whiteSpace: 'nowrap',
    fontWeight: 600,
  },
};
