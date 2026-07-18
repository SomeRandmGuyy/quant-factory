import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface Point {
  date: string;
  drawdown: number;
}

export default function UnderwaterChart({ data }: { data: Point[] }) {
  if (!data.length) {
    return (
      <div className="bg-white p-6 rounded-lg shadow-md text-gray-400 h-64 flex items-center justify-center">
        Underwater curve appears after a backtest.
      </div>
    );
  }
  const chartData = data.map((d) => ({
    date: String(d.date),
    drawdown: Number(d.drawdown) * 100,
  }));
  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h2 className="text-2xl font-bold text-gray-900 mb-4">Underwater (Drawdown %)</h2>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" tick={{ fontSize: 11 }}
            tickFormatter={(v) => {
              const d = new Date(v);
              return `${d.getMonth() + 1}/${d.getDate()}`;
            }}
          />
          <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${v.toFixed(0)}%`} />
          <Tooltip formatter={(v: number) => [`${Number(v).toFixed(2)}%`, 'Drawdown']} />
          <Line type="monotone" dataKey="drawdown" stroke="#ef4444" strokeWidth={2} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
