import { useState } from 'react';
import BacktestForm from './components/BacktestForm';
import EquityCurve from './components/EquityCurve';
import MetricsCard from './components/MetricsCard';
import UnderwaterChart from './components/UnderwaterChart';
import WalkForwardForm from './components/WalkForwardForm';
import WalkForwardResults from './components/WalkForwardResults';
import ExperimentsList from './components/ExperimentsList';
import { runBacktest, runWalkForward } from './api/client';
import type {
  BacktestRequest,
  BacktestResults,
  ProgressEvent,
  WalkForwardRequest,
  WalkForwardReport,
} from './types';

type Tab = 'backtest' | 'walkforward' | 'history';

interface DataPoint {
  date: string;
  value: number;
  benchmark?: number;
}

export default function App() {
  const [tab, setTab] = useState<Tab>('backtest');
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [equityCurveData, setEquityCurveData] = useState<DataPoint[]>([]);
  const [results, setResults] = useState<BacktestResults | null>(null);
  const [wfReport, setWfReport] = useState<WalkForwardReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleBacktestSubmit = async (request: BacktestRequest) => {
    setIsRunning(true);
    setProgress(0);
    setEquityCurveData([]);
    setResults(null);
    setError(null);
    try {
      await runBacktest(request, (event) => {
        if (event.type === 'progress') {
          const data = event.data as ProgressEvent;
          setProgress((data.progress ?? 0) * 100);
          if (data.date && data.portfolio_value != null) {
            setEquityCurveData((prev) => [
              ...prev,
              { date: data.date!, value: data.portfolio_value! },
            ]);
          }
        } else if (event.type === 'complete') {
          const complete = event.data as BacktestResults;
          setResults(complete);
          if (complete.equity_curve && Array.isArray(complete.equity_curve)) {
            const benchMap = new Map<string, number>();
            if (complete.benchmark_equity_curve) {
              for (const row of complete.benchmark_equity_curve) {
                const d = String(row.date ?? '');
                benchMap.set(d, Number(row.total_value ?? 0));
              }
            }
            setEquityCurveData(
              complete.equity_curve.map((row) => {
                const d = String(row.date ?? '');
                return {
                  date: d,
                  value: Number(row.total_value ?? row.value ?? 0),
                  benchmark: benchMap.has(d) ? benchMap.get(d) : undefined,
                };
              })
            );
          }
          setProgress(100);
          setIsRunning(false);
        } else if (event.type === 'error') {
          setError(event.data as string);
          setIsRunning(false);
        }
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      setIsRunning(false);
    }
  };

  const handleWalkForward = async (request: WalkForwardRequest) => {
    setIsRunning(true);
    setError(null);
    setWfReport(null);
    try {
      const report = await runWalkForward(request);
      setWfReport(report);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Walk-forward failed');
    } finally {
      setIsRunning(false);
    }
  };

  const tabBtn = (id: Tab, label: string) => (
    <button
      key={id}
      onClick={() => setTab(id)}
      className={`px-4 py-2 text-sm font-medium rounded-md ${
        tab === id ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 border'
      }`}
    >
      {label}
    </button>
  );

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-bold text-gray-900">Quant Factory</h1>
          <p className="mt-1 text-sm text-gray-500">
            Algorithmic Trading Backtesting Platform — Phase 2 risk & portfolio controls
          </p>
          <div className="mt-4 flex gap-2">
            {tabBtn('backtest', 'Backtest')}
            {tabBtn('walkforward', 'Walk-Forward')}
            {tabBtn('history', 'History')}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {isRunning && tab === 'backtest' && (
          <div className="mb-6 bg-white p-4 rounded-lg shadow-md">
            <div className="flex justify-between mb-2 text-sm">
              <span>Running Backtest</span>
              <span>{progress.toFixed(1)}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2.5">
              <div className="bg-blue-600 h-2.5 rounded-full" style={{ width: `${progress}%` }} />
            </div>
          </div>
        )}

        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-800">
            {error}
          </div>
        )}

        {tab === 'backtest' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-1">
              <BacktestForm onSubmit={handleBacktestSubmit} isRunning={isRunning} />
            </div>
            <div className="lg:col-span-2 space-y-6">
              <EquityCurve data={equityCurveData} isRunning={isRunning} />
              <UnderwaterChart data={results?.underwater_curve?.map((u) => ({ date: String(u.date), drawdown: Number(u.drawdown) })) ?? []} />
              <MetricsCard results={results} />
            </div>
          </div>
        )}

        {tab === 'walkforward' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-1">
              <WalkForwardForm onSubmit={handleWalkForward} isRunning={isRunning} />
            </div>
            <div className="lg:col-span-2">
              <WalkForwardResults report={wfReport} />
            </div>
          </div>
        )}

        {tab === 'history' && <ExperimentsList />}
      </main>

      <footer className="bg-white border-t border-gray-200 mt-12">
        <div className="max-w-7xl mx-auto px-4 py-6 text-center text-sm text-gray-500">
          Quant Factory v0.1.0 — Phase 2 portfolio construction & risk
        </div>
      </footer>
    </div>
  );
}
