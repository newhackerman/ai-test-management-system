import { useMemo, useState } from 'react'
import { Download, Eye, EyeOff, Network, RotateCcw, ZoomIn, ZoomOut } from 'lucide-react'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Loading } from '@/components/ui/Loading'

interface TraceabilityNode {
  id: string
  type: 'REQUIREMENT' | 'DESIGN' | 'TEST_CASE' | 'IMPLEMENTATION'
  code: string
  title: string
  status: string
  level: number
}

interface TraceabilityLink {
  id: string
  source: string
  target: string
  relationship: 'DERIVES_FROM' | 'IMPLEMENTS' | 'TESTS' | 'DEPENDS_ON' | 'SATISFIES'
  strength: number
  coverage: 'COVERED' | 'PARTIAL' | 'UNCOVERED'
}

interface PositionedNode extends TraceabilityNode {
  x: number
  y: number
}

interface TraceabilityVisualizationProps {
  filters?: any
  loading: boolean
  onRefresh: () => void
}

const nodes: TraceabilityNode[] = [
  { id: 'req-001', type: 'REQUIREMENT', code: 'REQ-2026-001', title: '用户登录功能', status: 'APPROVED', level: 0 },
  { id: 'req-002', type: 'REQUIREMENT', code: 'REQ-2026-002', title: '数据导出功能', status: 'APPROVED', level: 0 },
  { id: 'des-001', type: 'DESIGN', code: 'DES-2026-001', title: '登录模块设计', status: 'COMPLETED', level: 1 },
  { id: 'des-002', type: 'DESIGN', code: 'DES-2026-002', title: '导出模块设计', status: 'IN_PROGRESS', level: 1 },
  { id: 'tc-001', type: 'TEST_CASE', code: 'TC-2026-001', title: '登录功能测试', status: 'PASSED', level: 2 },
  { id: 'tc-002', type: 'TEST_CASE', code: 'TC-2026-002', title: '导出功能测试', status: 'PENDING', level: 2 },
  { id: 'impl-001', type: 'IMPLEMENTATION', code: 'IMPL-2026-001', title: '登录功能实现', status: 'COMPLETED', level: 3 },
]

const links: TraceabilityLink[] = [
  { id: 'link-001', source: 'req-001', target: 'des-001', relationship: 'IMPLEMENTS', strength: 1, coverage: 'COVERED' },
  { id: 'link-002', source: 'req-002', target: 'des-002', relationship: 'IMPLEMENTS', strength: 0.8, coverage: 'PARTIAL' },
  { id: 'link-003', source: 'des-001', target: 'tc-001', relationship: 'TESTS', strength: 1, coverage: 'COVERED' },
  { id: 'link-004', source: 'des-002', target: 'tc-002', relationship: 'TESTS', strength: 0.5, coverage: 'UNCOVERED' },
  { id: 'link-005', source: 'des-001', target: 'impl-001', relationship: 'IMPLEMENTS', strength: 1, coverage: 'COVERED' },
]

const typeLabels = {
  REQUIREMENT: '需求',
  DESIGN: '设计',
  TEST_CASE: '测试用例',
  IMPLEMENTATION: '实现',
}

const relationshipLabels = {
  DERIVES_FROM: '派生',
  IMPLEMENTS: '实现',
  TESTS: '测试',
  DEPENDS_ON: '依赖',
  SATISFIES: '满足',
}

const coverageLabels = {
  COVERED: '已覆盖',
  PARTIAL: '部分覆盖',
  UNCOVERED: '未覆盖',
}

const getNodeColor = (type: TraceabilityNode['type']) => {
  const colors = {
    REQUIREMENT: '#3b82f6',
    DESIGN: '#10b981',
    TEST_CASE: '#f59e0b',
    IMPLEMENTATION: '#8b5cf6',
  }
  return colors[type]
}

const getNodeIcon = (type: TraceabilityNode['type']) => {
  const icons = {
    REQUIREMENT: 'R',
    DESIGN: 'D',
    TEST_CASE: 'T',
    IMPLEMENTATION: 'I',
  }
  return icons[type]
}

const getLinkColor = (coverage: TraceabilityLink['coverage']) => {
  const colors = {
    COVERED: '#10b981',
    PARTIAL: '#f59e0b',
    UNCOVERED: '#ef4444',
  }
  return colors[coverage]
}

const calculateLayout = (
  sourceNodes: TraceabilityNode[],
  sourceLinks: TraceabilityLink[],
  viewMode: 'hierarchy' | 'force' | 'circular',
): PositionedNode[] => {
  const width = 900
  const height = 560

  if (viewMode === 'circular') {
    const centerX = width / 2
    const centerY = height / 2
    const radius = Math.min(width, height) / 3
    return sourceNodes.map((node, index) => {
      const angle = (2 * Math.PI * index) / Math.max(sourceNodes.length, 1)
      return { ...node, x: centerX + radius * Math.cos(angle), y: centerY + radius * Math.sin(angle) }
    })
  }

  if (viewMode === 'force') {
    return sourceNodes.map((node, index) => ({
      ...node,
      x: 100 + ((index * 170) % 700),
      y: 120 + ((index * 97) % 320),
    }))
  }

  const levels = Array.from(new Set(sourceNodes.map((node) => node.level))).sort((a, b) => a - b)
  return sourceNodes.map((node) => {
    const levelIndex = levels.indexOf(node.level)
    const levelNodes = sourceNodes.filter((item) => item.level === node.level)
    const nodeIndex = levelNodes.findIndex((item) => item.id === node.id)
    return {
      ...node,
      x: (width / (levelNodes.length + 1)) * (nodeIndex + 1),
      y: (height / (levels.length + 1)) * (levelIndex + 1),
    }
  })
}

export function TraceabilityVisualization({ loading, onRefresh }: TraceabilityVisualizationProps) {
  const [selectedNode, setSelectedNode] = useState<PositionedNode | null>(null)
  const [viewMode, setViewMode] = useState<'hierarchy' | 'force' | 'circular'>('hierarchy')
  const [showLabels, setShowLabels] = useState(true)
  const [filterByType, setFilterByType] = useState<string>('ALL')
  const [zoom, setZoom] = useState(1)

  const filteredNodes = useMemo(
    () => (filterByType === 'ALL' ? nodes : nodes.filter((node) => node.type === filterByType)),
    [filterByType],
  )

  const filteredLinks = useMemo(
    () =>
      links.filter(
        (link) =>
          filteredNodes.some((node) => node.id === link.source) &&
          filteredNodes.some((node) => node.id === link.target),
      ),
    [filteredNodes],
  )

  const positionedNodes = useMemo(
    () => calculateLayout(filteredNodes, filteredLinks, viewMode),
    [filteredNodes, filteredLinks, viewMode],
  )

  const nodeMap = useMemo(
    () => new Map(positionedNodes.map((node) => [node.id, node])),
    [positionedNodes],
  )

  const handleExport = () => {
    const svg = document.getElementById('traceability-visualization-svg')
    if (!svg) return

    const svgData = new XMLSerializer().serializeToString(svg)
    const blob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' })
    const link = document.createElement('a')
    link.download = 'traceability-visualization.svg'
    link.href = URL.createObjectURL(blob)
    link.click()
    URL.revokeObjectURL(link.href)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loading />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="flex flex-wrap gap-2">
          <select value={viewMode} onChange={(event) => setViewMode(event.target.value as any)} className="h-9 rounded-md border px-3 text-sm">
            <option value="hierarchy">层次布局</option>
            <option value="force">力导向布局</option>
            <option value="circular">环形布局</option>
          </select>
          <select value={filterByType} onChange={(event) => setFilterByType(event.target.value)} className="h-9 rounded-md border px-3 text-sm">
            <option value="ALL">全部类型</option>
            <option value="REQUIREMENT">需求</option>
            <option value="DESIGN">设计</option>
            <option value="TEST_CASE">测试用例</option>
            <option value="IMPLEMENTATION">实现</option>
          </select>
          <Button variant="outline" size="sm" onClick={() => setShowLabels((value) => !value)}>
            {showLabels ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            {showLabels ? '隐藏标签' : '显示标签'}
          </Button>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => setZoom((value) => Math.min(value * 1.2, 3))}>
            <ZoomIn className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="sm" onClick={() => setZoom((value) => Math.max(value / 1.2, 0.3))}>
            <ZoomOut className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="sm" onClick={() => setZoom(1)}>
            <RotateCcw className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="sm" onClick={onRefresh}>
            <Network className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="sm" onClick={handleExport}>
            <Download className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="flex flex-col gap-4 lg:flex-row">
        <Card className="flex-1">
          <CardContent className="p-0">
            <svg
              id="traceability-visualization-svg"
              width="100%"
              height="600"
              viewBox="0 0 900 560"
              className="rounded-lg border"
              style={{ background: '#fafafa' }}
            >
              <defs>
                <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                  <polygon points="0 0, 10 3.5, 0 7" fill="#666" />
                </marker>
              </defs>
              <g transform={`translate(0 0) scale(${zoom})`}>
                {filteredLinks.map((link) => {
                  const source = nodeMap.get(link.source)
                  const target = nodeMap.get(link.target)
                  if (!source || !target) return null
                  return (
                    <line
                      key={link.id}
                      x1={source.x}
                      y1={source.y}
                      x2={target.x}
                      y2={target.y}
                      stroke={getLinkColor(link.coverage)}
                      strokeWidth={Math.max(1, link.strength * 3)}
                      strokeOpacity="0.65"
                      markerEnd="url(#arrowhead)"
                    />
                  )
                })}

                {positionedNodes.map((node) => (
                  <g key={node.id} transform={`translate(${node.x}, ${node.y})`} className="cursor-pointer" onClick={() => setSelectedNode(node)}>
                    <circle
                      r="20"
                      fill={getNodeColor(node.type)}
                      stroke={selectedNode?.id === node.id ? '#2563eb' : '#fff'}
                      strokeWidth={selectedNode?.id === node.id ? 3 : 2}
                    />
                    <text textAnchor="middle" dy="0.3em" fill="white" fontSize="12" fontWeight="bold">
                      {getNodeIcon(node.type)}
                    </text>
                    {showLabels && (
                      <text textAnchor="middle" dy="35" fill="#374151" fontSize="10">
                        {node.code}
                      </text>
                    )}
                  </g>
                ))}
              </g>
            </svg>
          </CardContent>
        </Card>

        {selectedNode && (
          <Card className="w-full lg:w-80">
            <CardHeader>
              <CardTitle className="flex items-center text-lg">
                <div className="mr-2 h-4 w-4 rounded-full" style={{ backgroundColor: getNodeColor(selectedNode.type) }} />
                节点详情
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Detail label="编号" value={selectedNode.code} />
              <Detail label="标题" value={selectedNode.title} />
              <div>
                <label className="text-sm font-medium text-gray-600 dark:text-gray-400">类型</label>
                <div className="mt-1">
                  <Badge variant="outline">{typeLabels[selectedNode.type]}</Badge>
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-600 dark:text-gray-400">状态</label>
                <div className="mt-1">
                  <Badge>{selectedNode.status}</Badge>
                </div>
              </div>
              <Detail label="层级" value={`第 ${selectedNode.level + 1} 层`} />

              <div>
                <label className="text-sm font-medium text-gray-600 dark:text-gray-400">相关关系</label>
                <div className="mt-2 space-y-2">
                  {links
                    .filter((link) => link.source === selectedNode.id || link.target === selectedNode.id)
                    .map((link) => (
                      <div key={link.id} className="rounded bg-gray-50 p-2 text-xs dark:bg-gray-800/50">
                        <div className="flex items-center justify-between gap-2">
                          <span>
                            {link.source === selectedNode.id ? '指向' : '来自'} {relationshipLabels[link.relationship]}
                          </span>
                          <Badge variant="outline" className={link.coverage === 'COVERED' ? 'text-green-600' : link.coverage === 'PARTIAL' ? 'text-yellow-600' : 'text-red-600 dark:text-red-400'}>
                            {coverageLabels[link.coverage]}
                          </Badge>
                        </div>
                      </div>
                    ))}
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col gap-4 md:flex-row md:justify-between">
            <Legend title="节点类型" items={[
              ['bg-blue-500', '需求'],
              ['bg-green-500', '设计'],
              ['bg-yellow-500', '测试用例'],
              ['bg-purple-500 dark:bg-purple-900/20', '实现'],
            ]} />
            <Legend title="链接状态" items={[
              ['bg-green-500', '已覆盖'],
              ['bg-yellow-500', '部分覆盖'],
              ['bg-red-500', '未覆盖'],
            ]} line />
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <label className="text-sm font-medium text-gray-600 dark:text-gray-400">{label}</label>
      <p className="text-sm text-gray-900 dark:text-gray-100">{value}</p>
    </div>
  )
}

function Legend({ title, items, line = false }: { title: string; items: string[][]; line?: boolean }) {
  return (
    <div>
      <h4 className="mb-2 text-sm font-medium text-gray-900 dark:text-gray-100">{title}</h4>
      <div className="flex flex-wrap gap-4">
        {items.map(([color, label]) => (
          <div key={label} className="flex items-center gap-2">
            <div className={`${line ? 'h-1 w-4' : 'h-4 w-4 rounded-full'} ${color}`} />
            <span className="text-sm text-gray-600 dark:text-gray-400">{label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default TraceabilityVisualization
