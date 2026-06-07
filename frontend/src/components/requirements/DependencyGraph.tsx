import React, { useState, useEffect, useRef } from 'react'
import { RequirementDependency, Requirement, DependencyType } from '@/types/requirement'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Tooltip } from '@/components/ui/Tooltip'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { cn } from '@/lib/utils'

// 依赖类型配置
const DEPENDENCY_CONFIG: Record<DependencyType, {
  label: string
  color: string
  bgColor: string
  description: string
  icon: string
  lineStyle: string
}> = {
  DEPENDS_ON: {
    label: '依赖于',
    color: 'text-blue-600',
    bgColor: 'bg-blue-100',
    description: '当前需求依赖于目标需求完成',
    icon: '🔗',
    lineStyle: 'solid'
  },
  BLOCKS: {
    label: '阻塞',
    color: 'text-red-600',
    bgColor: 'bg-red-100',
    description: '当前需求阻塞目标需求开始',
    icon: '🚫',
    lineStyle: 'dashed'
  },
  RELATES_TO: {
    label: '关联',
    color: 'text-green-600',
    bgColor: 'bg-green-100',
    description: '与目标需求存在业务关联',
    icon: '🔄',
    lineStyle: 'dotted'
  },
  CONFLICTS_WITH: {
    label: '冲突',
    color: 'text-orange-600',
    bgColor: 'bg-orange-100',
    description: '与目标需求存在冲突',
    icon: '⚡',
    lineStyle: 'double'
  },
  DUPLICATES: {
    label: '重复',
    color: 'text-purple-600',
    bgColor: 'bg-purple-100',
    description: '与目标需求重复',
    icon: '📋',
    lineStyle: 'solid'
  },
  REPLACES: {
    label: '替代',
    color: 'text-teal-600',
    bgColor: 'bg-teal-100',
    description: '替代目标需求',
    icon: '🔄',
    lineStyle: 'solid'
  }
}

// 需求节点组件
interface RequirementNodeProps {
  requirement: Requirement
  isSelected?: boolean
  isHighlighted?: boolean
  onClick?: () => void
  onMouseEnter?: () => void
  onMouseLeave?: () => void
  position: { x: number; y: number }
  className?: string
}

const RequirementNode: React.FC<RequirementNodeProps> = ({
  requirement,
  isSelected,
  isHighlighted,
  onClick,
  onMouseEnter,
  onMouseLeave,
  position,
  className
}) => {
  const getStatusColor = (status: string) => {
    const statusColors: Record<string, string> = {
      DRAFT: 'bg-gray-100 text-gray-700',
      PENDING_REVIEW: 'bg-yellow-100 text-yellow-700',
      REVIEWING: 'bg-blue-100 text-blue-700',
      APPROVED: 'bg-green-100 text-green-700',
      IN_DEVELOPMENT: 'bg-purple-100 text-purple-700',
      TESTING: 'bg-indigo-100 text-indigo-700',
      COMPLETED: 'bg-emerald-100 text-emerald-700',
      DEPLOYED: 'bg-teal-100 text-teal-700',
      CLOSED: 'bg-slate-100 text-slate-700',
      CANCELLED: 'bg-red-100 text-red-700'
    }
    return statusColors[status] || 'bg-gray-100 text-gray-700'
  }

  return (
    <div
      className={cn(
        'absolute cursor-pointer transition-all duration-200 transform',
        isSelected && 'scale-110 z-10',
        isHighlighted && 'ring-2 ring-primary ring-offset-2',
        className
      )}
      style={{
        left: position.x,
        top: position.y,
        transform: 'translate(-50%, -50%)'
      }}
      onClick={onClick}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    >
      <Tooltip content={
        <div className="space-y-1">
          <p className="font-medium">{requirement.title}</p>
          <p className="text-xs text-muted-foreground">{requirement.requirement_code}</p>
          <p className="text-xs">{requirement.description?.substring(0, 100)}...</p>
        </div>
      }>
        <div className={cn(
          'p-3 rounded-lg border-2 bg-white shadow-sm min-w-[120px] max-w-[200px]',
          isSelected ? 'border-primary' : 'border-gray-200',
          'hover:shadow-md'
        )}>
          <div className="space-y-2">
            <div className="text-xs font-mono text-muted-foreground">
              {requirement.requirement_code}
            </div>
            <div className="text-sm font-medium line-clamp-2">
              {requirement.title}
            </div>
            <Badge 
              variant="secondary" 
              className={cn('text-xs', getStatusColor(requirement.status))}
            >
              {requirement.status}
            </Badge>
          </div>
        </div>
      </Tooltip>
    </div>
  )
}

// 连接线组件
interface ConnectionLineProps {
  from: { x: number; y: number }
  to: { x: number; y: number }
  dependencyType: DependencyType
  isHighlighted?: boolean
}

const ConnectionLine: React.FC<ConnectionLineProps> = ({
  from,
  to,
  dependencyType,
  isHighlighted
}) => {
  const config = DEPENDENCY_CONFIG[dependencyType]
  
  // 计算箭头方向
  const dx = to.x - from.x
  const dy = to.y - from.y
  const angle = Math.atan2(dy, dx)
  
  // 箭头大小
  const arrowSize = 8
  const arrowX = to.x - arrowSize * Math.cos(angle)
  const arrowY = to.y - arrowSize * Math.sin(angle)

  return (
    <g>
      {/* 连接线 */}
      <line
        x1={from.x}
        y1={from.y}
        x2={arrowX}
        y2={arrowY}
        stroke={isHighlighted ? '#3b82f6' : '#6b7280'}
        strokeWidth={isHighlighted ? 3 : 2}
        strokeDasharray={
          config.lineStyle === 'dashed' ? '5,5' :
          config.lineStyle === 'dotted' ? '2,2' :
          config.lineStyle === 'double' ? '0' : '0'
        }
        markerEnd="url(#arrowhead)"
      />
      
      {/* 箭头 */}
      <polygon
        points={`${to.x},${to.y} ${arrowX - arrowSize/2 * Math.sin(angle)},${arrowY + arrowSize/2 * Math.cos(angle)} ${arrowX + arrowSize/2 * Math.sin(angle)},${arrowY - arrowSize/2 * Math.cos(angle)}`}
        fill={isHighlighted ? '#3b82f6' : '#6b7280'}
      />
      
      {/* 依赖类型标签 */}
      <text
        x={(from.x + to.x) / 2}
        y={(from.y + to.y) / 2 - 10}
        textAnchor="middle"
        className="text-xs fill-current text-muted-foreground"
        style={{ fontSize: '10px' }}
      >
        {config.icon}
      </text>
    </g>
  )
}

interface DependencyGraphProps {
  requirements: Requirement[]
  dependencies: RequirementDependency[]
  selectedRequirementId?: number
  onRequirementSelect?: (requirement: Requirement) => void
  onDependencyCreate?: (sourceId: number, targetId: number, type: DependencyType) => void
  className?: string
}

export const DependencyGraph: React.FC<DependencyGraphProps> = ({
  requirements,
  dependencies,
  selectedRequirementId,
  onRequirementSelect,
  onDependencyCreate,
  className
}) => {
  const [selectedRequirement, setSelectedRequirement] = useState<Requirement | null>(null)
  const [highlightedNodes, setHighlightedNodes] = useState<Set<number>>(new Set())
  const [viewMode, setViewMode] = useState<'all' | 'selected' | 'dependencies'>('all')
  const [layout, setLayout] = useState<'force' | 'hierarchical' | 'circular'>('force')
  const containerRef = useRef<HTMLDivElement>(null)

  // 计算节点位置
  const calculateNodePositions = () => {
    const containerWidth = containerRef.current?.clientWidth || 800
    const containerHeight = containerRef.current?.clientHeight || 600
    
    const positions: Record<number, { x: number; y: number }> = {}
    
    if (layout === 'circular') {
      // 圆形布局
      const centerX = containerWidth / 2
      const centerY = containerHeight / 2
      const radius = Math.min(containerWidth, containerHeight) / 3
      
      requirements.forEach((req, index) => {
        const angle = (2 * Math.PI * index) / requirements.length
        positions[req.id] = {
          x: centerX + radius * Math.cos(angle),
          y: centerY + radius * Math.sin(angle)
        }
      })
    } else if (layout === 'hierarchical') {
      // 层次布局
      const levels: Record<number, number> = {}
      const visited = new Set<number>()
      
      // 计算层级
      const calculateLevel = (reqId: number, level: number = 0) => {
        if (visited.has(reqId)) return
        visited.add(reqId)
        levels[reqId] = Math.max(levels[reqId] || 0, level)
        
        const dependents = dependencies
          .filter(dep => dep.source_requirement_id === reqId)
          .map(dep => dep.target_requirement_id)
        
        dependents.forEach(depId => calculateLevel(depId, level + 1))
      }
      
      requirements.forEach(req => calculateLevel(req.id))
      
      // 按层级分组
      const levelGroups: Record<number, number[]> = {}
      Object.entries(levels).forEach(([reqId, level]) => {
        if (!levelGroups[level]) levelGroups[level] = []
        levelGroups[level].push(parseInt(reqId))
      })
      
      // 计算位置
      const maxLevel = Math.max(...Object.keys(levelGroups).map(Number))
      const levelHeight = containerHeight / (maxLevel + 1)
      
      Object.entries(levelGroups).forEach(([level, reqIds]) => {
        const levelNum = parseInt(level)
        const y = levelHeight * (levelNum + 0.5)
        const nodeWidth = containerWidth / (reqIds.length + 1)
        
        reqIds.forEach((reqId, index) => {
          positions[reqId] = {
            x: nodeWidth * (index + 1),
            y: y
          }
        })
      })
    } else {
      // 力导向布局（简化版）
      requirements.forEach((req, index) => {
        const cols = Math.ceil(Math.sqrt(requirements.length))
        const row = Math.floor(index / cols)
        const col = index % cols
        
        positions[req.id] = {
          x: (containerWidth / (cols + 1)) * (col + 1),
          y: (containerHeight / (Math.ceil(requirements.length / cols) + 1)) * (row + 1)
        }
      })
    }
    
    return positions
  }

  const nodePositions = calculateNodePositions()

  // 处理需求选择
  const handleRequirementClick = (requirement: Requirement) => {
    setSelectedRequirement(requirement)
    onRequirementSelect?.(requirement)
    
    // 高亮相关节点
    const relatedIds = new Set<number>()
    relatedIds.add(requirement.id)
    
    dependencies.forEach(dep => {
      if (dep.source_requirement_id === requirement.id) {
        relatedIds.add(dep.target_requirement_id)
      }
      if (dep.target_requirement_id === requirement.id) {
        relatedIds.add(dep.source_requirement_id)
      }
    })
    
    setHighlightedNodes(relatedIds)
  }

  // 获取显示的需求
  const getVisibleRequirements = () => {
    if (viewMode === 'all') return requirements
    if (viewMode === 'selected' && selectedRequirement) {
      return requirements.filter(req => highlightedNodes.has(req.id))
    }
    if (viewMode === 'dependencies') {
      const connectedIds = new Set<number>()
      dependencies.forEach(dep => {
        connectedIds.add(dep.source_requirement_id)
        connectedIds.add(dep.target_requirement_id)
      })
      return requirements.filter(req => connectedIds.has(req.id))
    }
    return requirements
  }

  const visibleRequirements = getVisibleRequirements()

  return (
    <Card className={cn('w-full h-full', className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>需求依赖关系图</CardTitle>
          <div className="flex items-center gap-2">
            <Select value={viewMode} onValueChange={(value: any) => setViewMode(value)}>
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部显示</SelectItem>
                <SelectItem value="selected">相关需求</SelectItem>
                <SelectItem value="dependencies">有依赖</SelectItem>
              </SelectContent>
            </Select>
            
            <Select value={layout} onValueChange={(value: any) => setLayout(value)}>
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="force">自由布局</SelectItem>
                <SelectItem value="hierarchical">层次布局</SelectItem>
                <SelectItem value="circular">圆形布局</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="p-0">
        <div 
          ref={containerRef}
          className="relative w-full h-96 overflow-hidden border rounded-lg bg-gray-50"
        >
          {/* SVG 连接线层 */}
          <svg className="absolute inset-0 w-full h-full pointer-events-none">
            <defs>
              <marker
                id="arrowhead"
                markerWidth="10"
                markerHeight="7"
                refX="9"
                refY="3.5"
                orient="auto"
              >
                <polygon
                  points="0 0, 10 3.5, 0 7"
                  fill="#6b7280"
                />
              </marker>
            </defs>
            
            {dependencies.map((dep, index) => {
              const sourcePos = nodePositions[dep.source_requirement_id]
              const targetPos = nodePositions[dep.target_requirement_id]
              
              if (!sourcePos || !targetPos) return null
              
              const isHighlighted = highlightedNodes.has(dep.source_requirement_id) || 
                                   highlightedNodes.has(dep.target_requirement_id)
              
              return (
                <ConnectionLine
                  key={index}
                  from={sourcePos}
                  to={targetPos}
                  dependencyType={dep.dependency_type}
                  isHighlighted={isHighlighted}
                />
              )
            })}
          </svg>
          
          {/* 需求节点层 */}
          {visibleRequirements.map((requirement) => {
            const position = nodePositions[requirement.id]
            if (!position) return null
            
            return (
              <RequirementNode
                key={requirement.id}
                requirement={requirement}
                position={position}
                isSelected={selectedRequirement?.id === requirement.id}
                isHighlighted={highlightedNodes.has(requirement.id)}
                onClick={() => handleRequirementClick(requirement)}
              />
            )
          })}
          
          {/* 空状态 */}
          {visibleRequirements.length === 0 && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center text-muted-foreground">
                <p className="text-lg mb-2">📊</p>
                <p>暂无需求数据</p>
              </div>
            </div>
          )}
        </div>
        
        {/* 图例 */}
        <div className="p-4 border-t bg-white">
          <h4 className="text-sm font-medium mb-3">依赖关系图例</h4>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {Object.entries(DEPENDENCY_CONFIG).map(([type, config]) => (
              <div key={type} className="flex items-center gap-2">
                <span className="text-sm">{config.icon}</span>
                <Badge variant="outline" className={cn('text-xs', config.bgColor, config.color)}>
                  {config.label}
                </Badge>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export default DependencyGraph