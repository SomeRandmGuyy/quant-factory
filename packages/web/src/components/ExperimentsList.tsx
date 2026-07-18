import { useEffect, useState } from 'react';
import { listExperiments } from '../api/client';
import type { ExperimentSummary } from '../types';

export default function ExperimentsList() {
  const [rows, setRows] = useState<ExperimentSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    listExperiments()
      .then(setRows)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load'));
  };

  useEffect(() => { load(); }, []);

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold">Experiment History</h2>
        <button onClick={load} className="text-sm text-blue-600 hover:underline">Refresh</button>
      </div>
      {error && <p className="text-red-600 text-sm mb-2">{error}</p>}
      {rows.length === 0 ? (
        <p className="text-gray-400">No experiments yet. Run a backtest or walk-forward.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b">
                <th className="py-2 pr-3">ID</th>
                <th className="py-2 pr-3">Kind</th>
                <th className="py-2 pr-3">Strategy</th>
                <th className="py-2 pr-3">When</th>
                <th className="py-2">Metrics snapshot</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-b border-gray-100">
                  <td className="py-2 pr-3">{r.id}</td>
                  <td className="py-2 pr-3">{r.kind}</td>
                  <td className="py-2 pr-3">{r.strategy_name}</td>
                  <td className="py-2 pr-3">{r.created_at ? new Date(r.created_at).toLocaleString() : '—'}</td>
                  <td className="py-2 font-mono text-xs max-w-md truncate">
                    {r.metrics ? JSON.stringify(r.metrics) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
