(function(root, factory) {
  const client = factory();
  if (typeof module === 'object' && module.exports) module.exports = client;
  else root.RuangkerjaAiStream = client;
})(typeof globalThis === 'object' ? globalThis : this, function() {
  async function read(stream, onDelta) {
    const reader = stream.getReader();
    const decoder = new TextDecoder('utf-8', { fatal: true });
    let pending = '';
    let text = '';
    let done = false;
    let size = 0;
    let reachedEnd = false;
    try {
      for (;;) {
        const chunk = await reader.read();
        size += chunk.value?.byteLength ?? 0;
        if (size > 2 * 1024 * 1024) throw new Error('Respons AI melewati batas.');
        pending += decoder.decode(chunk.value, { stream: !chunk.done });
        const lines = pending.split('\n');
        pending = lines.pop();
        for (const line of lines) {
          const event = JSON.parse(line);
          if (done) throw new Error('Respons AI memiliki data setelah selesai.');
          if (typeof event.error === 'string') throw new Error(event.error);
          if (event.done === true) done = true;
          else if (typeof event.delta === 'string') {
            text += event.delta;
            onDelta(event.delta);
          } else throw new Error('Format dari host AI tidak valid.');
        }
        if (chunk.done) {
          reachedEnd = true;
          break;
        }
      }
      if (!done || pending || !text.trim()) throw new Error('Respons AI terputus sebelum selesai.');
      return text;
    } finally {
      if (!reachedEnd) await reader.cancel().catch(() => {});
      reader.releaseLock();
    }
  }

  return { read };
});
