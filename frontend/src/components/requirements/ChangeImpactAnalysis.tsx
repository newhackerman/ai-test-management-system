import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Progress } from '@/components/ui/Progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs'
import { Alert, AlertDescription } from '@/components/ui/Alert'
import { 
  TrendingUp, 
  AlertTriangle, 
  Clock, 
  DollarSign, 
  Users, 
  FileText,
  GitBranch,
  Target,
  Zap,
  Shield,
  Download,
  RefreshCw
} from 'lucide-react'
import { RequirementChangeRequest } from '@/types/requirement'
import { traceabilityService, downloadJson, type ChangeImpactAnalysisResponse, type ImpactItem } from '@/services/traceabilityService'

/** 后端风险等级（小写）映射到前端展示等级；后端没有 CRITICAL。 */
function mapRiskLevel(level: string): 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' {
  const v = (level || '').toLowerCase()
  if (v === 'high') return 'HIGH'
  if (v === 'medium') return 'MEDIUM'
  if (v === 'critical') return 'CRITICAL'
  return 'LOW'
}

/** 后端对象标题形如 “编码 标题”，拆回编码与标题。 */
function splitCodeTitle(objectTitle: string): { code: string; title: string } {
  const [first, ...rest] = (objectTitle || '').split(' ')
  return rest.length ? { code: first, title: rest.join(' ') } : { code: '', title: objectTitle || '' }
}

/**
 * 把后端影响分析映射为前端展示结构。
 * 影响评分按“风险基线 + 直接影响×2 + 间接影响×1（封顶 100）”计算；
 * 领域得分是该领域影响项占全部影响项的比例；时间线与资源影响后端
 * 不提供，置零如实展示，不编造数据。
 */
function mapToImpactData(resp: ChangeImpactAnalysisResponse): ImpactAnalysisData {
  const risk = mapRiskLevel(resp.risk_level)
  const baseScore = { LOW: 25, MEDIUM: 50, HIGH: 75, CRITICAL: 90 }[risk]
  const impactScore = Math.min(100, baseScore + resp.direct_impacts.length * 2 + resp.indirect_impacts.length)
  const all = [...resp.direct_impacts, ...resp.indirect_impacts]
  const area = (items: ImpactItem[]) => ({
    score: all.length ? Math.round((items.length / all.length) * 100) : 0,
    items: items.map((i) => i.impact_description),
  })
  const reqItems = (items: ImpactItem[], relationship: string) =>
    items
      .filter((i) => i.object_type === 'requirement')
      .map((i) => {
        const { code, title } = splitCodeTitle(i.object_title)
        return { id: i.object_id, code, title, impact_level: i.impact_level as 'LOW' | 'MEDIUM' | 'HIGH', relationship }
      })
  return {
    overall_risk: risk,
    impact_score: impactScore,
    affected_areas: {
      technical: area(all.filter((i) => i.object_type === 'task')),
      functional: area(all.filter((i) => i.object_type === 'requirement')),
      schedule: { score: 0, items: ['本次分析未涉及进度数据'] },
      cost: { score: 0, items: ['本次分析未涉及成本数据'] },
      quality: area(all.filter((i) => i.object_type === 'test_case')),
    },
    affected_requirements: [
      ...reqItems(resp.direct_impacts, '直接依赖'),
      ...reqItems(resp.indirect_impacts, '间接影响'),
    ],
    affected_test_cases: all
      .filter((i) => i.object_type === 'test_case')
      .map((i) => {
        const { title } = splitCodeTitle(i.object_title)
        return { id: i.object_id, name: title || i.object_title, impact_level: i.impact_level as 'LOW' | 'MEDIUM' | 'HIGH', action_required: i.impact_description }
      }),
    affected_tasks: all
      .filter((i) => i.object_type === 'task')
      .map((i) => {
        const { title } = splitCodeTitle(i.object_title)
        return { id: i.object_id, name: title || i.object_title, impact_level: i.impact_level as 'LOW' | 'MEDIUM' | 'HIGH', status: '—' }
      }),
    recommendations: resp.recommendations.map((description) => ({
      type: 'RISK_MITIGATION' as const,
      priority: risk === 'HIGH' || risk === 'CRITICAL' ? ('HIGH' as const) : ('MEDIUM' as const),
      description,
      action_items: [description],
    })),
    timeline_impact: { estimated_delay: 0, critical_path_affected: false, milestone_impact: [] },
    resource_impact: { additional_effort: 0, skill_requirements: [], team_members_affected: 0 },
  }
}

interface ImpactAnalysisData {
  overall_risk: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  impact_score: number
  affected_areas: {
    technical: {
      score: number
      items: string[]
    }
    functional: {
      score: number
      items: string[]
    }
    schedule: {
      score: number
      items: string[]
    }
    cost: {
      score: number
      items: string[]
    }
    quality: {
      score: number
      items: string[]
    }
  }
  affected_requirements: Array<{
    id: number
    code: string
    title: string
    impact_level: 'LOW' | 'MEDIUM' | 'HIGH'
    relationship: string
  }>
  affected_test_cases: Array<{
    id: number
    name: string
    impact_level: 'LOW' | 'MEDIUM' | 'HIGH'
    action_required: string
  }>
  affected_tasks: Array<{
    id: number
    name: string
    impact_level: 'LOW' | 'MEDIUM' | 'HIGH'
    status: string
  }>
  recommendations: Array<{
    type: 'RISK_MITIGATION' | 'PROCESS_IMPROVEMENT' | 'RESOURCE_ALLOCATION' | 'TIMELINE_ADJUSTMENT'
    priority: 'HIGH' | 'MEDIUM' | 'LOW'
    description: string
    action_items: string[]
  }>
  timeline_impact: {
    estimated_delay: number
    critical_path_affected: boolean
    milestone_impact: Array<{
      milestone: string
      original_date: string
      new_date: string
    }>
  }
  resource_impact: {
    additional_effort: number
    skill_requirements: string[]
    team_members_affected: number
  }
}

interface ChangeImpactAnalysisProps {
  changeRequest: RequirementChangeRequest
  onClose: () => void
}

export function ChangeImpactAnalysis({
  changeRequest,
  onClose
}: ChangeImpactAnalysisProps) {
  const [analysisData, setAnalysisData] = useState<ImpactAnalysisData | null>(null)
  const [rawAnalysis, setRawAnalysis] = useState<ChangeImpactAnalysisResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [regenerating, setRegenerating] = useState(false)

  useEffect(() => {
    loadImpactAnalysis()
  }, [changeRequest.id])

  const loadImpactAnalysis = async () => {
    setLoading(true)
    try {
      // 后端每次调用都重新计算：直接影响/间接影响/风险等级/建议均来自真实追溯链接
      const resp = await traceabilityService.analyzeChangeImpact(
        changeRequest.requirement_id,
        changeRequest.description || changeRequest.title,
      )
      setRawAnalysis(resp)
      setAnalysisData(mapToImpactData(resp))
    } catch (error) {
      console.error('加载影响分析失败:', error)
      setAnalysisData(null)
    } finally {
      setLoading(false)
    }
  }

  const regenerateAnalysis = async () => {
    setRegenerating(true)
    try {
      // 后端分析是实时计算的，重新调用即重新生成
      await loadImpactAnalysis()
    } catch (error) {
      console.error('重新生成分析失败:', error)
    } finally {
      setRegenerating(false)
    }
  }

  const exportAnalysis = () => {
    if (!rawAnalysis) return
    downloadJson(
      `impact-analysis-${changeRequest.change_request_code || changeRequest.id}.json`,
      { changeRequest, analysis: rawAnalysis, mapped: analysisData },
    )
  }

  const getRiskBadge = (risk: string) => {
    const riskConfig = {
      LOW: { color: 'bg-green-100 text-green-800', text: '低风险' },
      MEDIUM: { color: 'bg-yellow-100 text-yellow-800', text: '中等风险' },
      HIGH: { color: 'bg-orange-100 text-orange-800 dark:text-orange-300 dark:bg-orange-900/30', text: '高风险' },
      CRITICAL: { color: 'bg-red-100 text-red-800 dark:text-red-300 dark:bg-red-900/30', text: '严重风险' }
    }

    const config = riskConfig[risk as keyof typeof riskConfig]
    return (
      <Badge className={config.color}>
        <AlertTriangle className="w-3 h-3 mr-1" />
        {config.text}
      </Badge>
    )
  }

  const getImpactLevelBadge = (level: string) => {
    const levelConfig = {
      LOW: { color: 'bg-green-100 text-green-800', text: '低影响' },
      MEDIUM: { color: 'bg-yellow-100 text-yellow-800', text: '中等影响' },
      HIGH: { color: 'bg-red-100 text-red-800 dark:text-red-300 dark:bg-red-900/30', text: '高影响' }
    }

    const config = levelConfig[level as keyof typeof levelConfig]
    return (
      <Badge className={config.color}>
        {config.text}
      </Badge>
    )
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2">正在分析变更影响...</span>
      </div>
    )
  }

  if (!analysisData) {
    return (
      <Alert>
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>
          无法加载影响分析数据，请稍后重试。
        </AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="space-y-6">
      {/* 标题和操作 */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">变更影响分析</h2>
          <p className="text-gray-600 mt-1 dark:text-gray-400">
            {changeRequest.change_request_code} - {changeRequest.title}
          </p>
        </div>
        <div className="flex space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={regenerateAnalysis}
            disabled={regenerating}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${regenerating ? 'animate-spin' : ''}`} />
            重新分析
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={exportAnalysis}
          >
            <Download className="w-4 h-4 mr-2" />
            导出报告
          </Button>
        </div>
      </div>

      {/* 总体风险评估 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <TrendingUp className="w-5 h-5 mr-2" />
            总体影响评估
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center">
              <div className="text-3xl font-bold text-gray-900 mb-2 dark:text-gray-100">
                {analysisData.impact_score}
              </div>
              <div className="text-sm text-gray-600 mb-2 dark:text-gray-400">影响评分</div>
              <Progress value={analysisData.impact_score} className="w-full" />
            </div>
            <div className="text-center">
              <div className="mb-2">
                {getRiskBadge(analysisData.overall_risk)}
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">整体风险等级</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600 mb-2 dark:text-blue-400">
                {analysisData.timeline_impact.estimated_delay}天
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">预计延期</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 详细分析 */}
      <Tabs defaultValue="areas" className="w-full">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="areas">影响领域</TabsTrigger>
          <TabsTrigger value="requirements">相关需求</TabsTrigger>
          <TabsTrigger value="tests">测试用例</TabsTrigger>
          <TabsTrigger value="tasks">开发任务</TabsTrigger>
          <TabsTrigger value="recommendations">建议措施</TabsTrigger>
        </TabsList>

        {/* 影响领域 */}
        <TabsContent value="areas">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.entries(analysisData.affected_areas).map(([area, data]) => (
              <Card key={area}>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm flex items-center justify-between">
                    <span className="capitalize">
                      {area === 'technical' ? '技术影响' :
                       area === 'functional' ? '功能影响' :
                       area === 'schedule' ? '进度影响' :
                       area === 'cost' ? '成本影响' : '质量影响'}
                    </span>
                    <Badge variant="outline">{data.score}%</Badge>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <Progress value={data.score} className="mb-3" />
                  <ul className="space-y-1">
                    {data.items.map((item, index) => (
                      <li key={index} className="text-sm text-gray-600 flex items-start dark:text-gray-400">
                        <span className="w-1 h-1 bg-gray-400 rounded-full mt-2 mr-2 flex-shrink-0 dark:bg-gray-500"></span>
                        {item}
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* 相关需求 */}
        <TabsContent value="requirements">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <FileText className="w-5 h-5 mr-2" />
                受影响的需求 ({analysisData.affected_requirements.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {analysisData.affected_requirements.map((req) => (
                  <div key={req.id} className="flex items-center justify-between p-3 border rounded-lg">
                    <div>
                      <div className="font-medium text-gray-900 dark:text-gray-100">{req.title}</div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">{req.code}</div>
                      <div className="text-sm text-gray-600 mt-1 dark:text-gray-400">{req.relationship}</div>
                    </div>
                    <div>
                      {getImpactLevelBadge(req.impact_level)}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* 测试用例 */}
        <TabsContent value="tests">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Shield className="w-5 h-5 mr-2" />
                受影响的测试用例 ({analysisData.affected_test_cases.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {analysisData.affected_test_cases.map((test) => (
                  <div key={test.id} className="flex items-center justify-between p-3 border rounded-lg">
                    <div>
                      <div className="font-medium text-gray-900 dark:text-gray-100">{test.name}</div>
                      <div className="text-sm text-gray-600 mt-1 dark:text-gray-400">{test.action_required}</div>
                    </div>
                    <div>
                      {getImpactLevelBadge(test.impact_level)}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* 开发任务 */}
        <TabsContent value="tasks">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Target className="w-5 h-5 mr-2" />
                受影响的开发任务 ({analysisData.affected_tasks.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {analysisData.affected_tasks.map((task) => (
                  <div key={task.id} className="flex items-center justify-between p-3 border rounded-lg">
                    <div>
                      <div className="font-medium text-gray-900 dark:text-gray-100">{task.name}</div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">状态: {task.status}</div>
                    </div>
                    <div>
                      {getImpactLevelBadge(task.impact_level)}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* 建议措施 */}
        <TabsContent value="recommendations">
          <div className="space-y-4">
            {analysisData.recommendations.map((rec, index) => (
              <Card key={index}>
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span className="flex items-center">
                      <Zap className="w-5 h-5 mr-2" />
                      {rec.type === 'RISK_MITIGATION' ? '风险缓解' :
                       rec.type === 'PROCESS_IMPROVEMENT' ? '流程改进' :
                       rec.type === 'RESOURCE_ALLOCATION' ? '资源分配' : '时间调整'}
                    </span>
                    <Badge variant={rec.priority === 'HIGH' ? 'destructive' : 
                                  rec.priority === 'MEDIUM' ? 'default' : 'secondary'}>
                      {rec.priority === 'HIGH' ? '高优先级' :
                       rec.priority === 'MEDIUM' ? '中优先级' : '低优先级'}
                    </Badge>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-700 mb-3 dark:text-gray-300">{rec.description}</p>
                  <div className="space-y-2">
                    <div className="text-sm font-medium text-gray-900 dark:text-gray-100">行动项:</div>
                    <ul className="space-y-1">
                      {rec.action_items.map((item, itemIndex) => (
                        <li key={itemIndex} className="text-sm text-gray-600 flex items-start dark:text-gray-400">
                          <span className="w-1 h-1 bg-blue-400 rounded-full mt-2 mr-2 flex-shrink-0"></span>
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>

      {/* 时间线和资源影响 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Clock className="w-5 h-5 mr-2" />
              时间线影响
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">预计延期:</span>
              <span className="font-medium">{analysisData.timeline_impact.estimated_delay} 天</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">关键路径影响:</span>
              <span className={`font-medium ${analysisData.timeline_impact.critical_path_affected ? 'text-red-600' : 'text-green-600 dark:text-green-400'}`}>
                {analysisData.timeline_impact.critical_path_affected ? '是' : '否'}
              </span>
            </div>
            {analysisData.timeline_impact.milestone_impact.length > 0 && (
              <div>
                <div className="text-sm font-medium text-gray-900 mb-2 dark:text-gray-100">里程碑影响:</div>
                {analysisData.timeline_impact.milestone_impact.map((milestone, index) => (
                  <div key={index} className="text-sm text-gray-600 dark:text-gray-400">
                    {milestone.milestone}: {milestone.original_date} → {milestone.new_date}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Users className="w-5 h-5 mr-2" />
              资源影响
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">额外工作量:</span>
              <span className="font-medium">{analysisData.resource_impact.additional_effort} 人天</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">影响团队成员:</span>
              <span className="font-medium">{analysisData.resource_impact.team_members_affected} 人</span>
            </div>
            <div>
              <div className="text-sm font-medium text-gray-900 mb-2 dark:text-gray-100">技能要求:</div>
              <div className="flex flex-wrap gap-1">
                {analysisData.resource_impact.skill_requirements.map((skill, index) => (
                  <Badge key={index} variant="outline">{skill}</Badge>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default ChangeImpactAnalysis