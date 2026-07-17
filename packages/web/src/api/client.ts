/**
 * API client for Quant Factory backend.
 */

import type { Strategy, BacktestRequest, BacktestEvent, BacktestResults } from '../types';
import { parseSseChunk } from './sse';

const API_BASE_URL = '/api';

export async function fetchStrategies(): Promise<Strategy[]> {
  const response = await fetch(`${API_BASE_URL}/strategies`);
  if (!response.ok) {
    throw new Error('Failed to fetch strategies');
  }
  return response.json();
}

function mapCompleteResults(r: Record<string, unknown>): BacktestResults {
  const metrics = (r.metrics || {}) as Record<string, number | null>;
  const tradeHistory = (r.trade_history as unknown[]) || [];
  return {
    strategy_name: String(r.strategy_name ?? ''),
    start_date: String(r.start_date ?? ''),
    end_date: String(r.end_date ?? ''),
    initial_capital: Number(r.initial_capital ?? 0),
    final_value: Number(r.final_value ?? 0),
    total_return: Number(metrics.total_return ?? 0) * 100,
    sharpe_ratio: metrics.sharpe_ratio ?? null,
    sortino_ratio: metrics.sortino_ratio ?? null,
    max_drawdown: Number(metrics.max_drawdown ?? 0) * 100,
    win_rate: Number(metrics.win_rate ?? 0) * 100,
    num_trades: Number(metrics.num_trades ?? tradeHistory.length ?? 0),
    metrics,
    equity_curve: r.equity_curve as Array<Record<string, unknown>> | undefined,
  };
}

/**
 * Run a backtest with Server-Sent Events streaming.
 */
export async function runBacktest(
  request: BacktestRequest,
  onEvent: (event: BacktestEvent) => void
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/backtest/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error('Failed to start backtest');
  }
  if (!response.body) {
    throw new Error('No response body');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split('\n\n');
    buffer = chunks.pop() || '';

    for (const chunk of chunks) {
      const parsed = parseSseChunk(chunk);
      if (!parsed) continue;

      const { eventType, data } = parsed;

      if (eventType === 'error') {
        const err =
          typeof data === 'object' && data && 'error' in data
            ? String((data as { error: string }).error)
            : String(data);
        onEvent({ type: 'error', data: err });
        continue;
      }

      if (typeof data !== 'object' || data === null) continue;
      const obj = data as Record<string, unknown>;

      if (obj.error) {
        onEvent({ type: 'error', data: String(obj.error) });
        continue;
      }

      if (obj.stage === 'complete' && obj.results && typeof obj.results === 'object') {
        onEvent({
          type: 'complete',
          data: mapCompleteResults(obj.results as Record<string, unknown>),
        });
        continue;
      }

      onEvent({
        type: 'progress',
        data: {
          stage: obj.stage as string | undefined,
          message: obj.message as string | undefined,
          progress: typeof obj.progress === 'number' ? obj.progress : 0,
          date: obj.date as string | undefined,
          portfolio_value: obj.portfolio_value as number | undefined,
        },
      });
    }
  }
}
