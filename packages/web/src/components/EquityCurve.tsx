import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface DataPoint {
  date: string;
  value: number;
  benchmark?: number;
}

interface EquityCurveProps {
  data: DataPoint[];
  isRunning: boolean;
}

export default function EquityCurve({ data, isRunning }: EquityCurveProps) {
  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold text-gray-900">Portfolio Value</h2>
        {isRunning && <span className="text-blue-600 text-sm">Running…</span>}
      </div>
      {data.length === 0 ? (
        <div className="flex items-center justify-center h-80 text-gray-400">
          <p>No data to display. Run a backtest to see results.</p>
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 12 }}
              tickFormatter={(value) => {
                const date = new Date(value);
                return `${date.getMonth() + 1}/${date.getDate()}`;
              }}
            />
            <YAxis tick={{ fontSize: 12 }} tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`} />
            <Tooltip
              formatter={(value: number, name: string) => [`$${Number(value).toFixed(2)}`, name]}
              labelFormatter={(label) => new Date(label).toLocaleDateString()}
            />
            <Legend />
            <Line type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2} dot={false} name="Strategy" isAnimationActive={false} />
            {data.some((d) => d.benchmark != null) && (
              <Line type="monotone" dataKey="benchmark" stroke="#9ca3af" strokeWidth={2} dot={false} name="Benchmark" isAnimationActive={false} />
            )}
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
