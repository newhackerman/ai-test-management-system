import React, { useMemo } from 'react'

import { Badge } from '@/components/ui/Badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Risk, RiskLevel, getRiskLevelText } from '@/services/riskService'

interface RiskMatrixProps {
  risks: Risk[]
  onRiskClick?: (risk: Risk) => void
}

const levelStyles: Record<RiskLevel, string> = {
  [RiskLevel.LOW]: 'bg-green-50 text-green-700 border-green-200',
  [RiskLevel.MEDIUM]: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  [RiskLevel.HIGH]: 'bg-orange-50 text-orange-700 border-orange-200',
  [RiskLevel.CRITICAL]: 'bg-red-50 text-red-700 border-red-200',
}

const clampPercent = (value?: number) => {
  const safeValue = Number.isFinite(Number(value)) ? Number(value) : 0
  return Math.max(0, Math.min(1, safeValue > 1 ? safeValue / 100 : safeValue))
}

const cellClass = (row: number, column: number) => {
  const score = (5 - row) * (column + 1)
  if (score >= 20) return 'bg-red-50 hover:bg-red-100 border-red-200'
  if (score >= 15) return 'bg-orange-50 hover:bg-orange-100 border-orange-200'
  if (score >= 8) return 'bg-yellow-50 hover:bg-yellow-100 border-yellow-200'
  return 'bg-green-50 hover:bg-green-100 border-green-200'
}

export const RiskMatrix: React.FC<RiskMatrixProps> = ({ risks, onRiskClick }) => {
  const matrix = useMemo(() => {
    const rows: Risk[][][] = Array.from({ length: 5 }, () =>
      Array.from({ length: 5 }, () => [] as Risk[]),
    )

    risks.forEach((risk) => {
      const probability = Math.min(4, Math.max(0, Math.ceil(clampPercent(Number(risk.probability)) * 5) - 1))
      const impact = Math.min(4, Math.max(0, Math.ceil((Number(risk.impact_score || 1) / 10) * 5) - 1))
      rows[4 - probability][impact].push(risk)
    })

    return rows
  }, [risks])

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex flex-col gap-3 text-lg md:flex-row md:items-center md:justify-between">
          <span>风险矩阵</span>
          <div className="flex flex-wrap gap-2">
            {Object.values(RiskLevel).map((level) => (
              <Badge key={level} variant="outline" className={levelStyles[level]}>
                {getRiskLevelText(level)}
              </Badge>
            ))}
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <div className="grid min-w-[760px] grid-cols-[84px_repeat(5,minmax(0,1fr))] gap-2">
            <div />
            {['1-2', '3-4', '5-6', '7-8', '9-10'].map((label) => (
              <div key={label} className="text-center text-xs text-muted-foreground">
                影响 {label}
              </div>
            ))}

            {matrix.map((row, rowIndex) => (
              <React.Fragment key={rowIndex}>
                <div className="flex items-center justify-end text-xs text-muted-foreground">
                  概率 {5 - rowIndex}
                </div>
                {row.map((cell, colIndex) => (
                  <button
                    key={`${rowIndex}-${colIndex}`}
                    type="button"
                    className={`min-h-24 rounded-md border p-2 text-left transition-colors disabled:cursor-default ${cellClass(rowIndex, colIndex)}`}
                    disabled={cell.length === 0}
                    onClick={() => cell[0] && onRiskClick?.(cell[0])}
                  >
                    <div className="text-sm font-medium">{cell.length} 条风险</div>
                    <div className="mt-2 space-y-1">
                      {cell.slice(0, 3).map((risk) => (
                        <div key={risk.id} className="truncate text-xs">
                          {risk.risk_name}
                        </div>
                      ))}
                      {cell.length > 3 && (
                        <div className="text-xs text-muted-foreground">+{cell.length - 3}</div>
                      )}
                    </div>
                  </button>
                ))}
              </React.Fragment>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export default RiskMatrix
