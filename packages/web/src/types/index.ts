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
  benchmark_ticker?: string | null;
  impact_bps?: number;
  save_experiment?: boolean;
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
  benchmark_equity_curve?: Array<Record<string, unknown>>;
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

export interface WalkForwardRequest {
  strategy_name: string;
  tickers: string[];
  start_date: string;
  end_date: string;
  initial_capital?: number;
  provider?: DataProviderName;
  train_days: number;
  test_days: number;
  step_days: number;
  mode?: 'rolling' | 'expanding';
  save_experiment?: boolean;
}

export interface WalkForwardFold {
  train_start: string;
  train_end: string;
  test_start: string;
  test_end: string;
  metrics: Record<string, number | null>;
  num_trades: number;
}

export interface WalkForwardReport {
  strategy_name: string;
  tickers: string[];
  folds: WalkForwardFold[];
  aggregate: {
    n_folds: number;
    oos_total_return_mean: number;
    oos_total_return_std: number;
    oos_sharpe_mean: number;
  };
}

export interface ExperimentSummary {
  id: number;
  name: string | null;
  kind: string;
  strategy_name: string;
  created_at: string | null;
  params: Record<string, unknown> | null;
  metrics: Record<string, unknown> | null;
  status: string;
}
