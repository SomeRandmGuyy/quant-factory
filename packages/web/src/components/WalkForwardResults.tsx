import type { WalkForwardReport } from '../types';

export default function WalkForwardResults({ report }: { report: WalkForwardReport | null }) {
  if (!report) {
    return (
      <div className="bg-white p-6 rounded-lg shadow-md text-gray-400">
        Run a walk-forward analysis to see OOS folds here.
      </div>
    );
  }
  const a = report.aggregate;
  return (
    <div className="bg-white p-6 rounded-lg shadow-md space-y-4">
      <h2 className="text-2xl font-bold">Walk-Forward Results</h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div><p className="text-sm text-gray-500">Folds</p><p className="text-xl font-bold">{a.n_folds}</p></div>
        <div><p className="text-sm text-gray-500">OOS Return (mean)</p><p className="text-xl font-bold">{(a.oos_total_return_mean * 100).toFixed(2)}%</p></div>
        <div><p className="text-sm text-gray-500">OOS Return (std)</p><p className="text-xl font-bold">{(a.oos_total_return_std * 100).toFixed(2)}%</p></div>
        <div><p className="text-sm text-gray-500">OOS Sharpe (mean)</p><p className="text-xl font-bold">{a.oos_sharpe_mean?.toFixed(2) ?? 'N/A'}</p></div>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500 border-b">
              <th className="py-2 pr-4">Test start</th>
              <th className="py-2 pr-4">Test end</th>
              <th className="py-2 pr-4">Return</th>
              <th className="py-2 pr-4">Sharpe</th>
              <th className="py-2">Trades</th>
            </tr>
          </thead>
          <tbody>
            {report.folds.map((f, i) => (
              <tr key={i} className="border-b border-gray-100">
                <td className="py-2 pr-4">{f.test_start}</td>
                <td className="py-2 pr-4">{f.test_end}</td>
                <td className="py-2 pr-4">{((f.metrics.total_return ?? 0) * 100).toFixed(2)}%</td>
                <td className="py-2 pr-4">{f.metrics.sharpe_ratio?.toFixed(2) ?? '—'}</td>
                <td className="py-2">{f.num_trades}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
