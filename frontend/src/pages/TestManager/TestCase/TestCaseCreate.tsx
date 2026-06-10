// @ts-nocheck
import React, { useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { ArrowLeft, Plus, Save, Trash2 } from 'lucide-react'
import { Button } from '../../../components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/Card'
import { Input } from '../../../components/ui/Input'
import { Textarea } from '../../../components/ui/Textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/Select'
import { useCreateTestCase } from '../../../hooks/testmanager/useTestCase'
import { AutomationLevel, Complexity, Priority, TestCaseType } from '../../../types/testmanager'
import requirementService from '../../../services/requirementService'
import { testPlanService } from '../../../services/testmanager/testPlanService'
import userService from '../../../services/user-service'
import type { Requirement } from '../../../types/requirement'
import type { TestPlan, TestStep } from '../../../types/testmanager'
import type { User } from '../../../types'
import {
  AUTOMATION_LABELS,
  COMPLEXITY_LABELS,
  PRIORITY_LABELS,
  TEST_CASE_TYPE_LABELS,
} from './testCaseLabels'
import {
  AI_IMPORT_DRAFT_KEY,
  buildFormFromAiDraft,
  buildStepsFromAiDraft,
  cleanText,
  cleanTitle,
  emptyStep,
  normalizeSteps,
  readAiDraft,
} from './testCaseFormUtils'

const defaultForm = {
  test_plan_id: 0,
  requirement_id: 0,
  assignee_id: 0,
  case_title: '',
  case_description: '',
  case_type: TestCaseType.FUNCTIONAL,
  module: '',
  priority: Priority.MEDIUM,
  complexity: Complexity.MEDIUM,
  automation_level: AutomationLevel.MANUAL,
  preconditions: '',
  expected_result: '',
  tags_text: '',
}

const TestCaseCreate: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const [aiDraft] = useState(() => readAiDraft((location.state as any)?.aiImport, 'test-case'))
  const createTestCase = useCreateTestCase()
  const [form, setForm] = useState(() => ({ ...defaultForm, ...(aiDraft ? buildFormFromAiDraft(aiDraft) : {}) }))
  const [steps, setSteps] = useState<TestStep[]>(() => buildStepsFromAiDraft(aiDraft))
  const [requirements, setRequirements] = useState<Requirement[]>([])
  const [testPlans, setTestPlans] = useState<TestPlan[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [submitError, setSubmitError] = useState('')

  useEffect(() => {
    if (aiDraft) sessionStorage.removeItem(AI_IMPORT_DRAFT_KEY)
  }, [aiDraft])

  useEffect(() => {
    let cancelled = false
    Promise.allSettled([
      requirementService.getRequirements({ page: 1, size: 100, sort_by: 'updated_at', sort_order: 'desc' }),
      testPlanService.getTestPlans({ page: 1, size: 100 }),
      userService.getUsers({ page: 1, size: 100, status: 'active' }),
    ]).then(([requirementsResult, plansResult, usersResult]) => {
      if (cancelled) return
      if (requirementsResult.status === 'fulfilled') setRequirements(requirementsResult.value.data || [])
      if (plansResult.status === 'fulfilled') setTestPlans(plansResult.value.data || [])
      if (usersResult.status === 'fulfilled') setUsers(usersResult.value.users || [])
    })
    return () => {
      cancelled = true
    }
  }, [])

  const planOptions = useMemo(() => testPlans.map((plan) => ({
    value: String(plan.id),
    label: `${plan.plan_code || `TP-${plan.id}`} - ${plan.plan_name}`,
  })), [testPlans])

  const requirementOptions = useMemo(() => requirements.map((requirement) => ({
    value: String(requirement.id),
    label: `${requirement.requirement_code || `REQ-${requirement.id}`} - ${requirement.title}`,
  })), [requirements])

  const userOptions = useMemo(() => users.map((user) => ({
    value: String(user.id),
    label: user.real_name || user.nickname || user.username,
  })), [users])

  const updateForm = (key: string, value: any) => {
    setSubmitError('')
    setForm((current) => ({ ...current, [key]: value }))
  }

  const updateStep = (index: number, key: keyof TestStep, value: string) => {
    setSubmitError('')
    setSteps((current) => current.map((step, stepIndex) => (
      stepIndex === index ? { ...step, [key]: value } : step
    )))
  }

  const addStep = () => {
    setSteps((current) => [...current, emptyStep(current.length + 1)])
  }

  const removeStep = (index: number) => {
    setSteps((current) => {
      const next = current.filter((_, stepIndex) => stepIndex !== index)
      return normalizeSteps(next.length ? next : [emptyStep(1)])
    })
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    const normalizedSteps = normalizeSteps(steps)
    if (!cleanTitle(form.case_title)) {
      setSubmitError('请填写测试用例标题')
      return
    }
    if (!normalizedSteps.some((step) => step.action && step.expected_result)) {
      setSubmitError('至少需要填写一个包含操作和预期结果的测试步骤')
      return
    }

    const result = await createTestCase.mutateAsync({
      test_plan_id: Number(form.test_plan_id || 0) || undefined,
      requirement_id: Number(form.requirement_id || 0) || undefined,
      assignee_id: Number(form.assignee_id || 0) || undefined,
      case_title: cleanTitle(form.case_title),
      case_description: cleanText(form.case_description),
      case_type: form.case_type,
      module: cleanTitle(form.module).slice(0, 80),
      priority: form.priority,
      complexity: form.complexity,
      automation_level: form.automation_level,
      preconditions: cleanText(form.preconditions),
      expected_result: cleanText(form.expected_result),
      test_steps: normalizedSteps,
      tags: cleanText(form.tags_text).split(/[，,\n]/).map((tag) => tag.trim()).filter(Boolean),
    })
    navigate(`/test-manager/test-cases/${result.id}`)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link to="/test-manager/test-cases">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="mr-2 h-4 w-4" />
            返回列表
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold">创建测试用例</h1>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {aiDraft && (
          <Card className="border-blue-200 bg-blue-50">
            <CardContent className="p-4 text-sm text-blue-800">
              已从 AI 助手导入测试用例草稿，请核对标题、步骤、测试数据和预期结果后保存。
            </CardContent>
          </Card>
        )}

        {submitError && (
          <Card className="border-red-200 bg-red-50">
            <CardContent className="p-4 text-sm text-red-700">{submitError}</CardContent>
          </Card>
        )}

        <Card>
          <CardHeader><CardTitle>基础信息</CardTitle></CardHeader>
          <CardContent className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Field label="用例标题">
              <Input value={form.case_title} onChange={(event) => updateForm('case_title', event.target.value)} required />
            </Field>
            <Field label="功能模块">
              <Input value={form.module} onChange={(event) => updateForm('module', event.target.value)} placeholder="例如：登录、订单、报表" />
            </Field>
            <Field label="关联测试计划">
              <OptionSelect value={String(form.test_plan_id || '')} placeholder="暂不关联测试计划" options={planOptions} onChange={(value) => updateForm('test_plan_id', Number(value || 0))} />
            </Field>
            <Field label="关联需求">
              <OptionSelect value={String(form.requirement_id || '')} placeholder="暂不关联需求" options={requirementOptions} onChange={(value) => updateForm('requirement_id', Number(value || 0))} />
            </Field>
            <Field label="负责人">
              <OptionSelect value={String(form.assignee_id || '')} placeholder="暂不分配" options={userOptions} onChange={(value) => updateForm('assignee_id', Number(value || 0))} />
            </Field>
            <Field label="用例类型">
              <EnumSelect value={form.case_type} options={TEST_CASE_TYPE_LABELS} onChange={(value) => updateForm('case_type', value)} />
            </Field>
            <Field label="优先级">
              <EnumSelect value={form.priority} options={PRIORITY_LABELS} onChange={(value) => updateForm('priority', value)} />
            </Field>
            <Field label="复杂度">
              <EnumSelect value={form.complexity} options={COMPLEXITY_LABELS} onChange={(value) => updateForm('complexity', value)} />
            </Field>
            <Field label="自动化级别">
              <EnumSelect value={form.automation_level} options={AUTOMATION_LABELS} onChange={(value) => updateForm('automation_level', value)} />
            </Field>
            <Field label="标签">
              <Input value={form.tags_text} onChange={(event) => updateForm('tags_text', event.target.value)} placeholder="多个标签用逗号分隔" />
            </Field>
            <div className="md:col-span-2">
              <Field label="描述">
                <Textarea rows={3} value={form.case_description} onChange={(event) => updateForm('case_description', event.target.value)} />
              </Field>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>执行条件与总体预期</CardTitle></CardHeader>
          <CardContent className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Field label="前置条件">
              <Textarea rows={4} value={form.preconditions} onChange={(event) => updateForm('preconditions', event.target.value)} />
            </Field>
            <Field label="总体预期结果">
              <Textarea rows={4} value={form.expected_result} onChange={(event) => updateForm('expected_result', event.target.value)} />
            </Field>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>测试步骤</CardTitle>
              <Button type="button" variant="outline" size="sm" onClick={addStep}>
                <Plus className="mr-2 h-4 w-4" />
                添加步骤
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {steps.map((step, index) => (
              <div key={index} className="grid gap-3 rounded-md border p-4 md:grid-cols-[80px_1fr_1fr_1fr_auto]">
                <div className="text-sm font-medium text-gray-600">步骤 {index + 1}</div>
                <Textarea rows={2} value={step.action} onChange={(event) => updateStep(index, 'action', event.target.value)} placeholder="操作步骤" required />
                <Textarea rows={2} value={step.expected_result} onChange={(event) => updateStep(index, 'expected_result', event.target.value)} placeholder="该步骤预期结果" required />
                <Textarea rows={2} value={String(step.test_data || '')} onChange={(event) => updateStep(index, 'test_data', event.target.value)} placeholder="测试数据" />
                <Button type="button" variant="ghost" size="icon" onClick={() => removeStep(index)} disabled={steps.length <= 1} aria-label="删除步骤">
                  <Trash2 className="h-4 w-4 text-red-500" />
                </Button>
              </div>
            ))}
          </CardContent>
        </Card>

        <div className="flex justify-end gap-3">
          <Link to="/test-manager/test-cases"><Button type="button" variant="outline">取消</Button></Link>
          <Button type="submit" disabled={createTestCase.isPending}>
            <Save className="mr-2 h-4 w-4" />
            {createTestCase.isPending ? '保存中...' : '保存测试用例'}
          </Button>
        </div>
      </form>
    </div>
  )
}

const Field = ({ label, children }: { label: string; children: React.ReactNode }) => (
  <label className="block space-y-2 text-sm font-medium">
    <span>{label}</span>
    {children}
  </label>
)

const EnumSelect = ({ value, options, onChange }: { value: string; options: Record<string, string>; onChange: (value: string) => void }) => (
  <select value={value} onChange={(event) => onChange(event.target.value)} className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
    {Object.entries(options).map(([optionValue, label]) => <option key={optionValue} value={optionValue}>{label}</option>)}
  </select>
)

const OptionSelect = ({ value, placeholder, options, onChange }: { value: string; placeholder: string; options: Array<{ value: string; label: string }>; onChange: (value: string) => void }) => (
  <Select value={value || 'none'} onValueChange={(next) => onChange(next === 'none' ? '' : next)}>
    <SelectTrigger><SelectValue placeholder={placeholder} /></SelectTrigger>
    <SelectContent>
      <SelectItem value="none">{placeholder}</SelectItem>
      {options.map((option) => <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>)}
    </SelectContent>
  </Select>
)

export default TestCaseCreate
