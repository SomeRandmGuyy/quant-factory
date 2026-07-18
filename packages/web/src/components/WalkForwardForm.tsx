import { useState, useEffect } from 'react';
import { fetchStrategies } from '../api/client';
import type { Strategy, WalkForwardRequest } from '../types';

interface Props {
  onSubmit: (request: WalkForwardRequest) => void;
  isRunning: boolean;
}

export default function WalkForwardForm({ onSubmit, isRunning }: Props) {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [formData, setFormData] = useState({
    strategy_name: '',
    tickers: 'AAPL,MSFT',
    start_date: '2024-01-02',
    end_date: '2024-02-29',
    initial_capital: 100000,
    provider: 'csv' as 'csv' | 'yahoo',
    train_days: 10,
    test_days: 5,
    step_days: 5,
    mode: 'rolling' as 'rolling' | 'expanding',
  });

  useEffect(() => {
    fetchStrategies().then(setStrategies).catch(console.error);
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      strategy_name: formData.strategy_name,
      tickers: formData.tickers.split(',').map((t) => t.trim()).filter(Boolean),
      start_date: formData.start_date,
      end_date: formData.end_date,
      initial_capital: Number(formData.initial_capital),
      provider: formData.provider,
      train_days: Number(formData.train_days),
      test_days: Number(formData.test_days),
      step_days: Number(formData.step_days),
      mode: formData.mode,
      save_experiment: true,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 bg-white p-6 rounded-lg shadow-md">
      <h2 className="text-2xl font-bold text-gray-900">Walk-Forward (OOS)</h2>
      <p className="text-sm text-gray-500">
        Evaluates the strategy on successive out-of-sample windows. Train windows are reserved for future optimization.
      </p>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Strategy</label>
        <select
          required
          disabled={isRunning}
          value={formData.strategy_name}
          onChange={(e) => setFormData({ ...formData, strategy_name: e.target.value })}
          className="w-full px-3 py-2 border rounded-md"
        >
          <option value="">Select…</option>
          {strategies.map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Tickers</label>
        <input className="w-full px-3 py-2 border rounded-md" disabled={isRunning}
          value={formData.tickers} onChange={(e) => setFormData({ ...formData, tickers: e.target.value })} />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Start</label>
          <input type="date" className="w-full px-3 py-2 border rounded-md" disabled={isRunning}
            value={formData.start_date} onChange={(e) => setFormData({ ...formData, start_date: e.target.value })} />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">End</label>
          <input type="date" className="w-full px-3 py-2 border rounded-md" disabled={isRunning}
            value={formData.end_date} onChange={(e) => setFormData({ ...formData, end_date: e.target.value })} />
        </div>
      </div>
      <div className="grid grid-cols-3 gap-2">
        <div>
          <label className="block text-xs text-gray-600">Train days</label>
          <input type="number" min={1} className="w-full px-2 py-1 border rounded" disabled={isRunning}
            value={formData.train_days} onChange={(e) => setFormData({ ...formData, train_days: Number(e.target.value) })} />
        </div>
        <div>
          <label className="block text-xs text-gray-600">Test days</label>
          <input type="number" min={1} className="w-full px-2 py-1 border rounded" disabled={isRunning}
            value={formData.test_days} onChange={(e) => setFormData({ ...formData, test_days: Number(e.target.value) })} />
        </div>
        <div>
          <label className="block text-xs text-gray-600">Step days</label>
          <input type="number" min={1} className="w-full px-2 py-1 border rounded" disabled={isRunning}
            value={formData.step_days} onChange={(e) => setFormData({ ...formData, step_days: Number(e.target.value) })} />
        </div>
      </div>
      <button type="submit" disabled={isRunning}
        className="w-full bg-indigo-600 text-white py-3 rounded-md hover:bg-indigo-700 disabled:bg-gray-400 font-medium">
        {isRunning ? 'Running walk-forward…' : 'Run Walk-Forward'}
      </button>
    </form>
  );
}
