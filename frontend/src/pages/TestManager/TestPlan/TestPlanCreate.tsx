// @ts-nocheck
import React, { useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { ArrowLeft, Save, X } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '../../../components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/Card'
import { Input } from '../../../components/ui/Input'
import { Textarea } from '../../../components/ui/Textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/Select'
import { DatePicker } from '../../../components/ui/DatePicker'
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '../../../components/ui/Form'
import { useCreateTestPlan } from '../../../hooks/testmanager/useTestPlan'
import { TestType } from '../../../types/testmanager'
import ProjectService from '../../../services/projectService'
import userService from '../../../services/user-service'

const AI_IMPORT_DRAFT_KEY = 'ai-assistant:import-draft'

const testPlanSchema = z.object({
  project_id: z.coerce.number().optional(),
  plan_name: z.string().min(1, '请输入计划名称').max(200, '计划名称不能超过200个字符'),
  description: z.string().optional(),
  test_type: z.nativeEnum(TestType, { required_error: '请选择测试类型' }),
  test_strategy: z.string().optional(),
  test_scope: z.string().optional(),
  planned_start_date: z.string().optional(),
  planned_end_date: z.string().optional(),
  test_manager_id: z.coerce.number().optional(),
})

type TestPlanFormData = z.infer<typeof testPlanSchema>

const toDate = (value?: string) => (value ? new Date(value) : undefined)
const toDateString = (date?: Date) => (date ? date.toISOString().slice(0, 10) : '')

const readAiDraft = (stateDraft: any, destination: string) => {
  if (stateDraft?.source === 'ai-assistant' && stateDraft.destination === destination) return stateDraft

  try {
    const saved = JSON.parse(sessionStorage.getItem(AI_IMPORT_DRAFT_KEY) || 'null')
    return saved?.source === 'ai-assistant' && saved.destination === destination ? saved : null
  } catch {
    return null
  }
}

const cleanImportedText = (value = '') => value
  .replace(/<br\s*\/?>/gi, '\n')
  .replace(/<\/?(p|div|li|ul|ol)>/gi, '\n')
  .replace(/\*\*(.*?)\*\*/g, '$1')
  .replace(/`([^`]+)`/g, '$1')
  .replace(/^\s*>\s?/gm, '')
  .replace(/&nbsp;/gi, ' ')
  .replace(/&amp;/gi, '&')
  .replace(/&lt;/gi, '<')
  .replace(/&gt;/gi, '>')
  .replace(/\r/g, '')
  .replace(/[ \t]+\n/g, '\n')
  .replace(/\n{3,}/g, '\n\n')
  .trim()

const cleanTitle = (value = '') => cleanImportedText(value)
  .replace(/^#{1,6}\s*/, '')
  .replace(/^[\d一二三四五六七八九十]+[.、]\s*/, '')
  .replace(/^(测试计划名称|计划名称|名称|标题|title|plan name)[:：]\s*/i, '')
  .replace(/[|]/g, '')
  .slice(0, 120)

const firstReadableLine = (content = '', fallback = 'AI 导入测试计划') => {
  const line = content
    .split('\n')
    .map((item) => item.trim())
    .find((item) => item && !item.startsWith('|') && !/^[-*_]{3,}$/.test(item))
  return cleanTitle(line || fallback)
}

const sectionAliases = {
  title: ['测试计划名称', '计划名称', '测试计划标题', '计划标题', '名称', '标题', 'plan name', 'title'],
  type: ['测试类型', '计划类型', '类型', 'test type', 'type'],
  description: ['计划描述', '测试计划描述', '描述', '总体描述', '概述', '简介', 'description', 'overview'],
  objective: ['测试目标', '计划目标', '目标', '目的', '业务目标', 'objective', 'goal'],
  background: ['项目背景', '业务背景', '背景', 'background'],
  scope: ['测试范围', '范围', '测试边界', '覆盖范围', 'scope'],
  outOfScope: ['不在范围', '不测范围', '排除范围', '非测试范围', 'out of scope'],
  strategy: ['测试策略', '策略', '测试方案', '整体策略', 'strategy', 'approach'],
  method: ['测试方法', '测试手段', '执行方式', '方法', 'method'],
  entry: ['进入准则', '准入准则', '入口准则', '启动准则', 'entry criteria'],
  exit: ['退出准则', '准出准则', '完成准则', '结束准则', 'exit criteria'],
  resources: ['资源安排', '资源计划', '人员安排', '测试资源', '环境资源', 'resources'],
  risks: ['风险与应对', '风险应对', '风险', '风险分析', '风险及对策', 'risks'],
  schedule: ['时间安排', '计划时间', '进度安排', '里程碑', '测试周期', 'schedule', 'timeline'],
  deliverables: ['交付物', '测试交付物', '输出物', 'deliverables'],
}

const allSectionLabels = Object.values(sectionAliases).flat()

const escapeRegExp = (value: string) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

const stripSectionPrefix = (value = '') => cleanImportedText(value)
  .replace(/^\s*(?:[-*+]\s*)?/, '')
  .replace(/^#{1,6}\s*/, '')
  .replace(/^[\d一二三四五六七八九十]+[.、)、)]\s*/, '')
  .trim()

const isSectionHeading = (line = '') => {
  const text = stripSectionPrefix(line).replace(/\s+/g, ' ')
  if (!text || /^[-|:：\s]+$/.test(text)) return false
  return allSectionLabels.some((label) => {
    const pattern = new RegExp(`^${escapeRegExp(label)}(?:\\s*[:：\\-—]\\s*.*|\\s*)$`, 'i')
    return pattern.test(text)
  })
}

const extractTableValue = (lines: string[], labels: string[]) => {
  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed.startsWith('|') || /^[-|:\s]+$/.test(trimmed)) continue
    const cells = trimmed
      .split('|')
      .map((cell) => cleanImportedText(cell))
      .filter(Boolean)
    if (cells.length < 2) continue
    const key = stripSectionPrefix(cells[0]).replace(/[:：]$/, '')
    if (!labels.some((label) => new RegExp(`^${escapeRegExp(label)}$`, 'i').test(key))) continue
    return cleanImportedText(cells.slice(1).join('\n'))
  }
  return ''
}

const extractSectionValue = (content = '', labels: string[]) => {
  const lines = cleanImportedText(content).split('\n')
  const tableValue = extractTableValue(lines, labels)
  if (tableValue) return tableValue

  const labelPattern = labels.map(escapeRegExp).join('|')
  const startRegExp = new RegExp(
    `^\\s*(?:[-*+]\\s*)?(?:#{1,6}\\s*)?(?:[\\d一二三四五六七八九十]+[.、)、)]\\s*)?(?:${labelPattern})(?:\\s*[:：\\-—]\\s*(.*)|\\s*)$`,
    'i',
  )

  for (let index = 0; index < lines.length; index += 1) {
    const match = lines[index].match(startRegExp)
    if (!match) continue

    const values = []
    if (match[1]) values.push(match[1])
    for (let next = index + 1; next < lines.length; next += 1) {
      const line = lines[next].trim()
      if (!line) {
        if (values.length) break
        continue
      }
      const nestedMatch = line.match(startRegExp)
      if (nestedMatch) {
        if (nestedMatch[1]) {
          values.push(nestedMatch[1])
          continue
        }
        if (!values.length) continue
      }
      if (isSectionHeading(line)) break
      values.push(line.replace(/^[-*]\s*/, ''))
    }
    return cleanImportedText(values.join('\n'))
  }
  return ''
}

const joinNamedSections = (sections: Array<[string, string]>) => cleanImportedText(
  sections
    .filter(([, value]) => Boolean(cleanImportedText(value)))
    .map(([label, value]) => `${label}：${cleanImportedText(value)}`)
    .join('\n\n'),
)

const parseTestType = (value = '') => {
  const text = cleanImportedText(value).toLowerCase()
  if (/performance|性能/.test(text)) return TestType.PERFORMANCE
  if (/security|安全/.test(text)) return TestType.SECURITY
  if (/integration|接口|api|集成/.test(text)) return TestType.INTEGRATION
  if (/regression|回归/.test(text)) return TestType.REGRESSION
  if (/acceptance|验收/.test(text)) return TestType.ACCEPTANCE
  return TestType.FUNCTIONAL
}

const buildInitialForm = (draft: any): TestPlanFormData => {
  if (!draft) {
    return {
      project_id: 0,
      plan_name: '',
      description: '',
      test_type: TestType.FUNCTIONAL,
      test_strategy: '',
      test_scope: '',
      planned_start_date: '',
      planned_end_date: '',
      test_manager_id: 0,
    }
  }

  const content = draft?.content || ''
  const title = (
    extractSectionValue(content, sectionAliases.title)
    || draft?.title
    || firstReadableLine(content)
  )
  const description = joinNamedSections([
    ['计划描述', extractSectionValue(content, sectionAliases.description)],
    ['测试目标', extractSectionValue(content, sectionAliases.objective)],
    ['背景概述', extractSectionValue(content, sectionAliases.background)],
  ]) || (
    extractSectionValue(content, [...sectionAliases.description, ...sectionAliases.objective, ...sectionAliases.background])
    || cleanImportedText(content).slice(0, 1200)
  )
  const strategy = joinNamedSections([
    ['测试策略', extractSectionValue(content, sectionAliases.strategy)],
    ['测试方法', extractSectionValue(content, sectionAliases.method)],
    ['进入准则', extractSectionValue(content, sectionAliases.entry)],
    ['退出准则', extractSectionValue(content, sectionAliases.exit)],
    ['资源安排', extractSectionValue(content, sectionAliases.resources)],
    ['风险与应对', extractSectionValue(content, sectionAliases.risks)],
    ['时间安排', extractSectionValue(content, sectionAliases.schedule)],
    ['交付物', extractSectionValue(content, sectionAliases.deliverables)],
  ])
  const scope = joinNamedSections([
    ['测试范围', extractSectionValue(content, sectionAliases.scope)],
    ['不在范围', extractSectionValue(content, sectionAliases.outOfScope)],
  ])
  const type = extractSectionValue(content, sectionAliases.type) || content
  const dates = cleanImportedText(content).match(/\d{4}[-/]\d{1,2}[-/]\d{1,2}/g) || []

  return {
    project_id: 0,
    plan_name: cleanTitle(title),
    description,
    test_type: parseTestType(type),
    test_strategy: strategy,
    test_scope: scope,
    planned_start_date: dates[0]?.replace(/\//g, '-') || '',
    planned_end_date: dates[1]?.replace(/\//g, '-') || '',
    test_manager_id: 0,
  }
}

const TestPlanCreate: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const createTestPlan = useCreateTestPlan()
  const [aiDraft] = useState(() => readAiDraft((location.state as any)?.aiImport, 'test-plan'))
  const [projects, setProjects] = useState([])
  const [users, setUsers] = useState([])
  const [referenceError, setReferenceError] = useState('')

  const testTypeOptions = useMemo(() => [
    { value: TestType.FUNCTIONAL, label: '功能测试' },
    { value: TestType.PERFORMANCE, label: '性能测试' },
    { value: TestType.SECURITY, label: '安全测试' },
    { value: TestType.INTEGRATION, label: '集成测试' },
    { value: TestType.REGRESSION, label: '回归测试' },
    { value: TestType.ACCEPTANCE, label: '验收测试' },
  ], [])

  const form = useForm<TestPlanFormData>({
    resolver: zodResolver(testPlanSchema),
    defaultValues: buildInitialForm(aiDraft),
  })

  useEffect(() => {
    if (aiDraft) sessionStorage.removeItem(AI_IMPORT_DRAFT_KEY)
  }, [aiDraft])

  useEffect(() => {
    let cancelled = false

    Promise.all([
      ProjectService.getProjects({ page: 1, size: 100, sort: 'updated_at', order: 'desc' }),
      userService.getUsers({ page: 1, size: 100, sort_by: 'created_at', sort_order: 'desc' }),
    ])
      .then(([projectResponse, userResponse]) => {
        if (cancelled) return
        const nextProjects = projectResponse.data || []
        const nextUsers = userResponse.users || []
        setProjects(nextProjects)
        setUsers(nextUsers)
        const currentValues = form.getValues()
        form.reset({
          ...currentValues,
          project_id: currentValues.project_id || Number(nextProjects[0]?.id || 0),
          test_manager_id: currentValues.test_manager_id || Number(nextUsers[0]?.id || 0),
        })
      })
      .catch((error) => {
        if (!cancelled) setReferenceError(error?.message || '加载项目和人员失败')
      })

    return () => {
      cancelled = true
    }
  }, [form])

  const onSubmit = async (data: TestPlanFormData) => {
    const projectId = Number(data.project_id || projects[0]?.id || 0)
    const managerId = Number(data.test_manager_id || users[0]?.id || 0)
    if (!projectId) {
      setReferenceError('请选择所属项目')
      return
    }
    if (!managerId) {
      setReferenceError('请选择测试经理')
      return
    }

    setReferenceError('')
    const result = await createTestPlan.mutateAsync({
      ...data,
      project_id: projectId,
      test_manager_id: managerId,
      planned_start_date: data.planned_start_date || undefined,
      planned_end_date: data.planned_end_date || undefined,
    })
    navigate(`/test-manager/test-plans/${result.id}`)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to="/test-manager/test-plans">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="w-4 h-4 mr-2" />
              返回列表
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold">创建测试计划</h1>
          </div>
        </div>
      </div>

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          {aiDraft && (
            <Card className="border-blue-200 bg-blue-50">
              <CardContent className="p-4 text-sm text-blue-800">
                已从 AI 助手导入测试计划草稿。保存前请核对计划名称、测试类型、范围、策略和时间安排。
              </CardContent>
            </Card>
          )}
          {referenceError && (
            <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {referenceError}
            </div>
          )}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>基本信息</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <FormField
                    control={form.control}
                    name="plan_name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>计划名称 *</FormLabel>
                        <FormControl>
                          <Input placeholder="请输入测试计划名称" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="test_type"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>测试类型 *</FormLabel>
                        <Select value={field.value} onValueChange={field.onChange}>
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue placeholder="请选择测试类型" />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            {testTypeOptions.map((option) => (
                              <SelectItem key={option.value} value={option.value}>
                                {option.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="description"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>描述</FormLabel>
                        <FormControl>
                          <Textarea placeholder="请输入测试计划描述" rows={3} {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>测试策略与范围</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <FormField
                    control={form.control}
                    name="test_strategy"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>测试策略</FormLabel>
                        <FormControl>
                          <Textarea placeholder="描述测试策略和方法" rows={4} {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="test_scope"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>测试范围</FormLabel>
                        <FormControl>
                          <Textarea placeholder="定义测试范围和边界" rows={4} {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </CardContent>
              </Card>
            </div>

            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>关联信息</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <FormField
                    control={form.control}
                    name="project_id"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>所属项目 *</FormLabel>
                        <FormControl>
                          <select
                            value={String(field.value || projects[0]?.id || '')}
                            onChange={(event) => field.onChange(Number(event.target.value))}
                            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                          >
                            <option value="">请选择项目</option>
                            {projects.map((project) => (
                              <option key={project.id} value={String(project.id)}>
                                {project.project_name || project.name || `项目 #${project.id}`}
                              </option>
                            ))}
                          </select>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="test_manager_id"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>测试经理 *</FormLabel>
                        <FormControl>
                          <select
                            value={String(field.value || users[0]?.id || '')}
                            onChange={(event) => field.onChange(Number(event.target.value))}
                            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                          >
                            <option value="">请选择测试经理</option>
                            {users.map((user) => (
                              <option key={user.id} value={String(user.id)}>
                                {user.real_name || user.nickname || user.username || `用户 #${user.id}`}
                              </option>
                            ))}
                          </select>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>时间安排</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <FormField
                    control={form.control}
                    name="planned_start_date"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>计划开始日期</FormLabel>
                        <FormControl>
                          <DatePicker
                            selected={toDate(field.value)}
                            onSelect={(date) => field.onChange(toDateString(date))}
                            placeholder="选择开始日期"
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="planned_end_date"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>计划结束日期</FormLabel>
                        <FormControl>
                          <DatePicker
                            selected={toDate(field.value)}
                            onSelect={(date) => field.onChange(toDateString(date))}
                            placeholder="选择结束日期"
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <div className="flex flex-col space-y-2">
                    <Button type="submit" disabled={createTestPlan.isPending} className="w-full">
                      <Save className="w-4 h-4 mr-2" />
                      {createTestPlan.isPending ? '创建中...' : '创建测试计划'}
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => navigate('/test-manager/test-plans')}
                      className="w-full"
                    >
                      <X className="w-4 h-4 mr-2" />
                      取消
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </form>
      </Form>
    </div>
  )
}

export default TestPlanCreate
