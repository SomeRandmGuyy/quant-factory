/**
 * API client for Quant Factory backend.
 */

import type { Strategy, BacktestRequest, BacktestEvent, BacktestResults } from '../types';

const API_BASE_URL = '/api';

export async function fetchStrategies(): Promise<Strategy[]> {
  const response = await fetch(`${API_BASE_URL}/strategies`);
  if (!response.ok) {
    throw new Error('Failed to fetch strategies');
  }
  return response.json();
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
      if (!chunk.trim()) continue;

      let eventType = 'message';
      let dataLine = '';
      for (const line of chunk.split('\n')) {
        if (line.startsWith('event:')) {
          eventType = line.slice(6).trim();
        } else if (line.startsWith('data:')) {
          dataLine = line.slice(5).trim();
        }
      }
      if (!dataLine) continue;

      try {
        if (eventType === 'error') {
          const parsed = JSON.parse(dataLine);
          onEvent({ type: 'error', data: parsed.error || dataLine });
          continue;
        }

        const parsed = JSON.parse(dataLine);

        if (parsed.error) {
          onEvent({ type: 'error', data: String(parsed.error) });
          continue;
        }

        // Final payload: stage complete with results, or legacy complete event
        if (parsed.stage === 'complete' && parsed.results) {
          const r = parsed.results;
          const metrics = r.metrics || {};
          const results: BacktestResults = {
            strategy_name: r.strategy_name,
            start_date: r.start_date,
            end_date: r.end_date,
            initial_capital: r.initial_capital,
            final_value: r.final_value,
            total_return: (metrics.total_return ?? 0) * 100,
            sharpe_ratio: metrics.sharpe_ratio ?? null,
            sortino_ratio: metrics.sortino_ratio ?? null,
            max_drawdown: (metrics.max_drawdown ?? 0) * 100,
            win_rate: (metrics.win_rate ?? 0) * 100,
            num_trades: metrics.num_trades ?? (r.trade_history?.length ?? 0),
            metrics,
            equity_curve: r.equity_curve,
          };
          onEvent({ type: 'complete', data: results });
          continue;
        }

        onEvent({
          type: 'progress',
          data: {
            stage: parsed.stage,
            message: parsed.message,
            progress: typeof parsed.progress === 'number' ? parsed.progress : 0,
            date: parsed.date,
            portfolio_value: parsed.portfolio_value,
          },
        });
      } catch (err) {
        console.error('Failed to parse SSE data:', err, dataLine);
      }
    }
  }
}
