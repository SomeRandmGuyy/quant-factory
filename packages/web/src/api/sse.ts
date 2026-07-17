/**
 * Parse a single SSE message chunk (event + data lines).
 */
export type ParsedSse = {
  eventType: string;
  data: unknown;
};

export function parseSseChunk(chunk: string): ParsedSse | null {
  if (!chunk.trim()) return null;

  let eventType = 'message';
  let dataLine = '';

  for (const line of chunk.split('\n')) {
    if (line.startsWith('event:')) {
      eventType = line.slice(6).trim();
    } else if (line.startsWith('data:')) {
      dataLine = line.slice(5).trim();
    }
  }

  if (!dataLine) return null;

  try {
    return { eventType, data: JSON.parse(dataLine) };
  } catch {
    return { eventType, data: dataLine };
  }
}
