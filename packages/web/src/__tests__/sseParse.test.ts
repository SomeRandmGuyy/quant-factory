import { describe, it, expect } from 'vitest';
import { parseSseChunk } from '../api/sse';

describe('parseSseChunk', () => {
  it('parses data-only progress events', () => {
    const parsed = parseSseChunk('data: {"stage":"running","progress":0.3}');
    expect(parsed).not.toBeNull();
    expect(parsed!.eventType).toBe('message');
    expect((parsed!.data as { stage: string }).stage).toBe('running');
  });

  it('parses error events', () => {
    const parsed = parseSseChunk('event: error\ndata: {"error":"boom"}');
    expect(parsed!.eventType).toBe('error');
    expect((parsed!.data as { error: string }).error).toBe('boom');
  });

  it('parses complete stage with results', () => {
    const chunk =
      'data: {"stage":"complete","progress":1,"results":{"strategy_name":"Value Moat","equity_curve":[{"date":"2024-01-02","total_value":100}]}}';
    const parsed = parseSseChunk(chunk);
    expect((parsed!.data as { stage: string }).stage).toBe('complete');
  });

  it('returns null for empty chunk', () => {
    expect(parseSseChunk('')).toBeNull();
  });
});
