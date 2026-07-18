/**
 * BacktestForm component.
 * 
 * Input form for configuring and launching backtests.
 * Handles strategy selection, ticker input, date range, and initial capital.
 */

import { useState, useEffect } from 'react';
import { fetchStrategies } from '../api/client';
import type { Strategy, BacktestRequest } from '../types';

interface BacktestFormProps {
  onSubmit: (request: BacktestRequest) => void;
  isRunning: boolean;
}

export default function BacktestForm({ onSubmit, isRunning }: BacktestFormProps) {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [formData, setFormData] = useState({
    strategy_name: '',
    tickers: 'AAPL,MSFT,TSLA',
    start_date: '2024-01-01',
    end_date: '2024-06-30',
    initial_capital: 100000,
    provider: 'csv' as 'csv' | 'yahoo',
    benchmark_ticker: '',
    impact_bps: 0,
  });

  // Load strategies on mount
  useEffect(() => {
    fetchStrategies()
      .then(setStrategies)
      .catch(error => console.error('Failed to load strategies:', error));
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    const request: BacktestRequest = {
      strategy_name: formData.strategy_name,
      tickers: formData.tickers.split(',').map(t => t.trim()).filter(Boolean),
      start_date: formData.start_date,
      end_date: formData.end_date,
      initial_capital: Number(formData.initial_capital),
      provider: formData.provider,
      impact_bps: Number(formData.impact_bps) || 0,
      benchmark_ticker: formData.benchmark_ticker.trim() || null,
      save_experiment: true,
    };
    
    onSubmit(request);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6 bg-white p-6 rounded-lg shadow-md">
      <h2 className="text-2xl font-bold text-gray-900">Configure Backtest</h2>
      
      {/* Strategy Selection */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Trading Strategy
        </label>
        <select
          value={formData.strategy_name}
          onChange={(e) => setFormData({ ...formData, strategy_name: e.target.value })}
          required
          disabled={isRunning}
          className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
        >
          <option value="">Select a strategy...</option>
          {strategies.map(strategy => (
            <option key={strategy.id} value={strategy.id}>
              {strategy.name}
            </option>
          ))}
        </select>
        {formData.strategy_name && (
          <p className="mt-1 text-sm text-gray-500">
            {strategies.find(s => s.id === formData.strategy_name)?.description}
          </p>
        )}
      </div>

      {/* Tickers */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Tickers (comma-separated)
        </label>
        <input
          type="text"
          value={formData.tickers}
          onChange={(e) => setFormData({ ...formData, tickers: e.target.value })}
          required
          disabled={isRunning}
          placeholder="AAPL,MSFT,TSLA"
          className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
        />
      </div>

      {/* Date Range */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Start Date
          </label>
          <input
            type="date"
            value={formData.start_date}
            onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
            required
            disabled={isRunning}
            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            End Date
          </label>
          <input
            type="date"
            value={formData.end_date}
            onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
            required
            disabled={isRunning}
            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
          />
        </div>
      </div>


      {/* Data provider */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Data Source
        </label>
        <select
          value={formData.provider}
          onChange={(e) => setFormData({ ...formData, provider: e.target.value as 'csv' | 'yahoo' })}
          disabled={isRunning}
          className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
        >
          <option value="csv">Local CSV (offline)</option>
          <option value="yahoo">Yahoo Finance (live)</option>
        </select>
        <p className="mt-1 text-sm text-gray-500">
          CSV uses files under the server data directory. Yahoo requires network access.
        </p>
      </div>

      {/* Initial Capital */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Initial Capital ($)
        </label>
        <input
          type="number"
          value={formData.initial_capital}
          onChange={(e) => setFormData({ ...formData, initial_capital: Number(e.target.value) })}
          required
          min="1000"
          step="1000"
          disabled={isRunning}
          className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
        />
      </div>


      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Benchmark ticker (optional)
        </label>
        <input
          type="text"
          value={formData.benchmark_ticker}
          onChange={(e) => setFormData({ ...formData, benchmark_ticker: e.target.value })}
          disabled={isRunning}
          placeholder="SPY"
          className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Impact bps (0 = off)
        </label>
        <input
          type="number"
          value={formData.impact_bps}
          onChange={(e) => setFormData({ ...formData, impact_bps: Number(e.target.value) })}
          disabled={isRunning}
          min="0"
          step="1"
          className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
        />
      </div>

      {/* Submit Button */}
      <button
        type="submit"
        disabled={isRunning}
        className="w-full bg-blue-600 text-white py-3 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:bg-gray-400 disabled:cursor-not-allowed font-medium"
      >
        {isRunning ? 'Running Backtest...' : 'Run Backtest'}
      </button>
    </form>
  );
}
