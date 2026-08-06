const BASE_URL = '';

export async function sendMessage(
  question: string,
  conversationId: string | null,
  onToken: (token: string) => void,
  onSources: (sources: any[]) => void,
  onDone: () => void,
  onError: (error: string) => void,
): Promise<void> {
  try {
    const response = await fetch(`${BASE_URL}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, conversation_id: conversationId }),
    });

    if (!response.ok) {
      onError(`请求失败: ${response.status}`);
      return;
    }

    const reader = response.body?.getReader();
    if (!reader) {
      onError('无法读取响应流');
      return;
    }

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Parse SSE events from buffer
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      let currentEvent = '';
      for (const line of lines) {
        if (line.startsWith('event: ')) {
          currentEvent = line.slice(7).trim();
        } else if (line.startsWith('data: ')) {
          const data = line.slice(6);
          handleSSEEvent(currentEvent, data, onToken, onSources, onDone, onError);
        }
      }
    }
  } catch (e: any) {
    onError(`网络错误: ${e.message}`);
  }
}

function handleSSEEvent(
  event: string,
  data: string,
  onToken: (token: string) => void,
  onSources: (sources: any[]) => void,
  onDone: () => void,
  onError: (error: string) => void,
) {
  switch (event) {
    case 'token':
      onToken(data);
      break;
    case 'sources':
      try {
        const sources = JSON.parse(data);
        onSources(sources);
      } catch {
        // ignore parse errors
      }
      break;
    case 'done':
      onDone();
      break;
    case 'error':
      onError(data);
      break;
  }
}

export async function fetchSources(): Promise<any[]> {
  const res = await fetch(`${BASE_URL}/api/admin/sources`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchStats(): Promise<any> {
  const res = await fetch(`${BASE_URL}/api/admin/stats`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
