import React from 'react'
import { 
  BarChart as RechartsBarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer 
} from 'recharts'

interface BarChartProps {
  data: any[]
  xKey: string
  yKey: string
  title?: string
  color?: string
  height?: number
  showGrid?: boolean
  showLegend?: boolean
  className?: string
}

const BarChart: React.FC<BarChartProps> = ({
  data,
  xKey,
  yKey,
  title,
  color = '#3B82F6',
  height = 300,
  showGrid = true,
  showLegend = false,
  className
}) => {
  return (
    <div className={className}>
      {title && (
        <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <RechartsBarChart data={data}>
          {showGrid && <CartesianGrid strokeDasharray="3 3" />}
          <XAxis dataKey={xKey} />
          <YAxis />
          <Tooltip />
          {showLegend && <Legend />}
          <Bar dataKey={yKey} fill={color} />
        </RechartsBarChart>
      </ResponsiveContainer>
    </div>
  )
}

export default BarChart