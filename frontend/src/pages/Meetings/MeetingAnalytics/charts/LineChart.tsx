import React from 'react'
import { 
  LineChart as RechartsLineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer 
} from 'recharts'

interface LineData {
  [key: string]: any
}

interface LineConfig {
  key: string
  color: string
  name?: string
  strokeWidth?: number
  strokeDasharray?: string
}

interface LineChartProps {
  data: LineData[]
  lines: LineConfig[]
  xKey: string
  title?: string
  height?: number
  showGrid?: boolean
  showLegend?: boolean
  className?: string
}

const LineChart: React.FC<LineChartProps> = ({
  data,
  lines,
  xKey,
  title,
  height = 300,
  showGrid = true,
  showLegend = true,
  className
}) => {
  return (
    <div className={className}>
      {title && (
        <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <RechartsLineChart data={data}>
          {showGrid && <CartesianGrid strokeDasharray="3 3" />}
          <XAxis dataKey={xKey} />
          <YAxis />
          <Tooltip />
          {showLegend && <Legend />}
          {lines.map((line, index) => (
            <Line
              key={index}
              type="monotone"
              dataKey={line.key}
              stroke={line.color}
              name={line.name || line.key}
              strokeWidth={line.strokeWidth || 2}
              strokeDasharray={line.strokeDasharray}
            />
          ))}
        </RechartsLineChart>
      </ResponsiveContainer>
    </div>
  )
}

export default LineChart