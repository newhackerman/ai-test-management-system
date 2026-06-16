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
  const [loading, setLoading] = useState(true)
  const [regenerating, setRegenerating] = useState(false)

  useEffect(() => {
    loadImpactAnalysis()
  }, [changeRequest.id])

  const loadImpactAnalysis = async () => {
    setLoading(true)
    try {
      // TODO: 调用影响分析API
      // const analysis = await changeService.getImpactAnalysis(changeRequest.id)
      // setAnalysisData(analysis)
      
      // 模拟数据
      const mockAnalysis: ImpactAnalysisData = {
        overall_risk: 'MEDIUM',
        impact_score: 65,
        affected_areas: {
          technical: {
            score: 70,
            items: ['数据库架构调整', 'API接口变更', '第三方集成影响']
          },
          functional: {
            score: 60,
            items: ['用户界面调整', '业务流程变更', '权限控制更新']
          },
          schedule: {
            score: 55,
            items: ['开发周期延长', '测试时间增加', '部署计划调整']
          },
          cost: {
            score: 45,
            items: ['额外开发成本', '测试资源投入', '培训成本']
          },
          quality: {
            score: 50,
            items: ['代码复杂度增加', '测试覆盖率要求', '文档更新需求']
          }
        },
        affected_requirements: [
          {
            id: 103,
            code: 'REQ-2024-003',
            title: '用户权限管理',
            impact_level: 'HIGH',
            relationship: '直接依赖'
          },
          {
            id: 104,
            code: 'REQ-2024-004',
            title: '系统日志记录',
            impact_level: 'MEDIUM',
            relationship: '间接影响'
          }
        ],
        affected_test_cases: [
          {
            id: 201,
            name: '登录功能测试',
            impact_level: 'HIGH',
            action_required: '需要重新设计测试用例'
          },
          {
            id: 202,
            name: '权限验证测试',
            impact_level: 'MEDIUM',
            action_required: '需要更新测试数据'
          }
        ],
        affected_tasks: [
          {
            id: 301,
            name: '前端登录页面开发',
            impact_level: 'HIGH',
            status: '进行中'
          },
          {
            id: 302,
            name: '后端认证服务',
            impact_level: 'MEDIUM',
            status: '已完成'
          }
        ],
        recommendations: [
          {
            type: 'RISK_MITIGATION',
            priority: 'HIGH',
            description: '建议进行详细的技术方案评审',
            action_items: [
              '组织技术架构评审会议',
              '制定详细的实施计划',
              '准备回滚方案'
            ]
          },
          {
            type: 'TIMELINE_ADJUSTMENT',
            priority: 'MEDIUM',
            description: '建议调整项目时间线',
            action_items: [
              '重新评估里程碑时间',
              '调整资源分配',
              '通知相关干系人'
            ]
          }
        ],
        timeline_impact: {
          estimated_delay: 5,
          critical_path_affected: true,
          milestone_impact: [
            {
              milestone: '功能开发完成',
              original_date: '2024-02-15',
              new_date: '2024-02-20'
            }
          ]
        },
        resource_impact: {
          additional_effort: 8,
          skill_requirements: ['前端开发', '后端开发', '测试'],
          team_members_affected: 3
        }
      }
      setAnalysisData(mockAnalysis)
    } catch (error) {
      console.error('加载影响分析失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const regenerateAnalysis = async () => {
    setRegenerating(true)
    try {
      // TODO: 调用重新生成分析API
      // await changeService.regenerateImpactAnalysis(changeRequest.id)
      await loadImpactAnalysis()
    } catch (error) {
      console.error('重新生成分析失败:', error)
    } finally {
      setRegenerating(false)
    }
  }

  const exportAnalysis = () => {
    // TODO: 实现导出功能
    console.log('导出影响分析报告')
  }

  const getRiskBadge = (risk: string) => {
    const riskConfig = {
      LOW: { color: 'bg-green-100 text-green-800', text: '低风险' },
      MEDIUM: { color: 'bg-yellow-100 text-yellow-800', text: '中等风险' },
      HIGH: { color: 'bg-orange-100 text-orange-800', text: '高风险' },
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
                        <span className="w-1 h-1 bg-gray-400 rounded-full mt-2 mr-2 flex-shrink-0"></span>
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
              <span className={`font-medium ${analysisData.timeline_impact.critical_path_affected ? 'text-red-600' : 'text-green-600'}`}>
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