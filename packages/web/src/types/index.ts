/**
 * TypeScript types for Quant Factory API contracts.
 */

export type DataProviderName = 'csv' | 'yahoo';

export interface Strategy {
  id: string;
  name: string;
  description: string;
}

export interface BacktestRequest {
  strategy_name: string;
  tickers: string[];
  start_date: string;
  end_date: string;
  initial_capital: number;
  commission_bps?: number;
  slippage_bps?: number;
  rebalance_frequency?: number;
  provider?: DataProviderName;
}

export interface BacktestResults {
  strategy_name: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  final_value: number;
  total_return: number;
  sharpe_ratio: number | null;
  sortino_ratio: number | null;
  max_drawdown: number;
  win_rate: number;
  num_trades: number;
  metrics?: Record<string, number | string | null>;
  equity_curve?: Array<Record<string, unknown>>;
}

export interface ProgressEvent {
  stage?: string;
  message?: string;
  progress: number;
  date?: string;
  portfolio_value?: number;
  results?: BacktestResults | Record<string, unknown>;
}

export type BacktestEvent =
  | { type: 'progress'; data: ProgressEvent }
  | { type: 'complete'; data: BacktestResults }
  | { type: 'error'; data: string };
