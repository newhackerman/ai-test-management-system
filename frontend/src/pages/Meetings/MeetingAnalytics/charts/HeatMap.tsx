import React from 'react'
import { cn } from '@/lib/utils'

interface HeatMapData {
  x: string | number
  y: string | number
  value: number
  label?: string
}

interface HeatMapProps {
  data: HeatMapData[]
  title?: string
  width?: number
  height?: number
  cellSize?: number
  colorScale?: string[]
  showLabels?: boolean
  className?: string
  onCellClick?: (data: HeatMapData) => void
}

const defaultColorScale = [
  '#f7fafc', '#e2e8f0', '#cbd5e0', '#a0aec0', 
  '#718096', '#4a5568', '#2d3748', '#1a202c'
]

const HeatMap: React.FC<HeatMapProps> = ({
  data,
  title,
  width = 600,
  height = 400,
  cellSize = 20,
  colorScale = defaultColorScale,
  showLabels = false,
  className,
  onCellClick
}) => {
  // 获取唯一的 x 和 y 值
  const xValues = Array.from(new Set(data.map(d => d.x))).sort()
  const yValues = Array.from(new Set(data.map(d => d.y))).sort()
  
  // 获取数值范围
  const values = data.map(d => d.value)
  const minValue = Math.min(...values)
  const maxValue = Math.max(...values)
  
  // 计算颜色
  const getColor = (value: number) => {
    if (maxValue === minValue) return colorScale[0]
    
    const normalized = (value - minValue) / (maxValue - minValue)
    const colorIndex = Math.floor(normalized * (colorScale.length - 1))
    return colorScale[Math.min(colorIndex, colorScale.length - 1)]
  }
  
  // 创建数据映射
  const dataMap = new Map<string, HeatMapData>()
  data.forEach(d => {
    dataMap.set(`${d.x}-${d.y}`, d)
  })
  
  return (
    <div className={className}>
      {title && (
        <h3 className="text-lg font-semibold text-gray-900 mb-4 dark:text-gray-100">{title}</h3>
      )}
      
      <div className="overflow-auto">
        <svg width={width} height={height} className="border border-gray-200 dark:border-gray-700">
          {/* Y轴标签 */}
          {yValues.map((y, yIndex) => (
            <text
              key={`y-${yIndex}`}
              x={40}
              y={60 + yIndex * (cellSize + 2) + cellSize / 2}
              textAnchor="end"
              dominantBaseline="middle"
              className="text-xs fill-gray-600 dark:fill-gray-300"
            >
              {y}
            </text>
          ))}
          
          {/* X轴标签 */}
          {xValues.map((x, xIndex) => (
            <text
              key={`x-${xIndex}`}
              x={50 + xIndex * (cellSize + 2) + cellSize / 2}
              y={35}
              textAnchor="middle"
              dominantBaseline="middle"
              className="text-xs fill-gray-600 dark:fill-gray-300"
            >
              {x}
            </text>
          ))}
          
          {/* 热力图单元格 */}
          {yValues.map((y, yIndex) =>
            xValues.map((x, xIndex) => {
              const cellData = dataMap.get(`${x}-${y}`)
              const value = cellData?.value || 0
              const color = getColor(value)
              
              return (
                <g key={`cell-${xIndex}-${yIndex}`}>
                  <rect
                    x={50 + xIndex * (cellSize + 2)}
                    y={50 + yIndex * (cellSize + 2)}
                    width={cellSize}
                    height={cellSize}
                    fill={color}
                    stroke="#fff"
                    strokeWidth={1}
                    className={cn(
                      "transition-opacity hover:opacity-80",
                      onCellClick && "cursor-pointer"
                    )}
                    onClick={() => cellData && onCellClick?.(cellData)}
                  />
                  
                  {showLabels && cellData && (
                    <text
                      x={50 + xIndex * (cellSize + 2) + cellSize / 2}
                      y={50 + yIndex * (cellSize + 2) + cellSize / 2}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      className="text-xs fill-gray-800 pointer-events-none dark:fill-gray-200"
                    >
                      {cellData.label || value}
                    </text>
                  )}
                </g>
              )
            })
          )}
        </svg>
        
        {/* 颜色图例 */}
        <div className="mt-4 flex items-center space-x-2">
          <span className="text-sm text-gray-600 dark:text-gray-400">低</span>
          <div className="flex">
            {colorScale.map((color, index) => (
              <div
                key={index}
                className="w-4 h-4"
                style={{ backgroundColor: color }}
              />
            ))}
          </div>
          <span className="text-sm text-gray-600 dark:text-gray-400">高</span>
          <span className="text-sm text-gray-500 ml-4 dark:text-gray-400">
            范围: {minValue.toFixed(1)} - {maxValue.toFixed(1)}
          </span>
        </div>
      </div>
    </div>
  )
}

export default HeatMap