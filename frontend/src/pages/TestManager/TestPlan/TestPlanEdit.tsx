// @ts-nocheck
import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
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
import { useTestPlan, useUpdateTestPlan } from '../../../hooks/testmanager/useTestPlan'
import { TestType } from '../../../types/testmanager'
import ProjectService from '../../../services/projectService'
import userService from '../../../services/user-service'

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

const defaultFormValues: TestPlanFormData = {
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

const buildFormFromPlan = (plan: any): TestPlanFormData => ({
  project_id: Number(plan?.project_id || 0),
  plan_name: plan?.plan_name || '',
  description: plan?.description || '',
  test_type: plan?.test_type || TestType.FUNCTIONAL,
  test_strategy: plan?.test_strategy || '',
  test_scope: plan?.test_scope || '',
  planned_start_date: plan?.planned_start_date ? String(plan.planned_start_date).slice(0, 10) : '',
  planned_end_date: plan?.planned_end_date ? String(plan.planned_end_date).slice(0, 10) : '',
  test_manager_id: Number(plan?.test_manager_id || 0),
})

const TestPlanEdit: React.FC = () => {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const planId = Number(id)
  const { data: testPlan, isLoading, error } = useTestPlan(planId)
  const updateTestPlan = useUpdateTestPlan()
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
    defaultValues: defaultFormValues,
  })

  useEffect(() => {
    if (!testPlan) return
    form.reset(buildFormFromPlan(testPlan))
  }, [form, testPlan?.id])

  useEffect(() => {
    let cancelled = false

    Promise.all([
      ProjectService.getProjects({ page: 1, size: 100, sort: 'updated_at', order: 'desc' }),
      userService.getUsers({ page: 1, size: 100, sort_by: 'created_at', sort_order: 'desc' }),
    ])
      .then(([projectResponse, userResponse]) => {
        if (cancelled) return
        setProjects(projectResponse.data || [])
        setUsers(userResponse.users || [])
      })
      .catch((loadError) => {
        if (!cancelled) setReferenceError(loadError?.message || '加载项目和人员失败')
      })

    return () => {
      cancelled = true
    }
  }, [])

  const onSubmit = async (data: TestPlanFormData) => {
    const managerId = Number(data.test_manager_id || 0)
    if (!managerId) {
      setReferenceError('请选择测试经理')
      return
    }

    setReferenceError('')
    await updateTestPlan.mutateAsync({
      id: planId,
      data: {
        plan_name: data.plan_name,
        description: data.description || undefined,
        test_strategy: data.test_strategy || undefined,
        test_scope: data.test_scope || undefined,
        planned_start_date: data.planned_start_date || undefined,
        planned_end_date: data.planned_end_date || undefined,
        test_manager_id: managerId,
      },
    })
    navigate(`/test-manager/test-plans/${planId}`)
  }

  if (isLoading) {
    return <div className="flex h-64 items-center justify-center text-gray-500 dark:text-gray-400">正在加载测试计划...</div>
  }

  if (error || !testPlan) {
    return (
      <div className="space-y-4">
        <Link to="/test-manager/test-plans">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="w-4 h-4 mr-2" />
            返回列表
          </Button>
        </Link>
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          测试计划不存在或加载失败
        </div>
      </div>
    )
  }

  const saving = updateTestPlan.isPending

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to="/test-manager/test-plans">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="w-4 h-4 mr-2" />
              返回列表
            </Button>
          </Link>
          <span className="text-sm text-muted-foreground">{testPlan.plan_code || `#${planId}`}</span>
        </div>
      </div>

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          {referenceError && (
            <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {referenceError}
            </div>
          )}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div className="space-y-4 lg:col-span-2">
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
                        <Select value={field.value} onValueChange={field.onChange} disabled>
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
                        <p className="text-xs text-gray-500 dark:text-gray-400">测试类型由创建时确定，编辑时不修改。</p>
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

            <div className="space-y-4">
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
                            value={String(field.value || '')}
                            disabled
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
                        <p className="text-xs text-gray-500 dark:text-gray-400">所属项目由创建时确定，编辑时不修改。</p>
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
                            value={String(field.value || '')}
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
                    <Button type="submit" disabled={saving} className="w-full">
                      <Save className="w-4 h-4 mr-2" />
                      {saving ? '保存中...' : '保存修改'}
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => navigate(`/test-manager/test-plans/${planId}`)}
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

export default TestPlanEdit
