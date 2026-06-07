// @ts-nocheck
import React, { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Plus, Save, Trash2 } from 'lucide-react'
import { Button } from '../../../components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/Card'
import { Input } from '../../../components/ui/Input'
import { Textarea } from '../../../components/ui/Textarea'
import { useTestCase, useUpdateTestCase } from '../../../hooks/testmanager/useTestCase'
import {
  AutomationLevel,
  Complexity,
  Priority,
  TestCaseStatus,
  TestCaseType,
} from '../../../types/testmanager'
import requirementService from '../../../services/requirementService'
import type { Requirement } from '../../../types/requirement'

const requirementLabel = (requirement: Requirement) => {
  const code = requirement.requirement_code || `REQ-${requirement.id}`
  return `${code} - ${requirement.title}`
}

const emptyStep = (stepNumber: number) => ({
  step_number: stepNumber,
  action: '',
  expected_result: '',
  test_data: '',
})

const labels = {
  type: {
    [TestCaseType.FUNCTIONAL]: '功能测试',
    [TestCaseType.NON_FUNCTIONAL]: '非功能测试',
    [TestCaseType.INTEGRATION]: '集成测试',
    [TestCaseType.SYSTEM]: '系统测试',
    [TestCaseType.ACCEPTANCE]: '验收测试',
    [TestCaseType.REGRESSION]: '回归测试',
    [TestCaseType.SMOKE]: '冒烟测试',
    [TestCaseType.PERFORMANCE]: '性能测试',
    [TestCaseType.SECURITY]: '安全测试',
    [TestCaseType.USABILITY]: '易用性测试',
  },
  priority: {
    [Priority.CRITICAL]: '紧急',
    [Priority.HIGH]: '高',
    [Priority.MEDIUM]: '中',
    [Priority.LOW]: '低',
  },
  complexity: {
    [Complexity.SIMPLE]: '简单',
    [Complexity.MEDIUM]: '中等',
    [Complexity.COMPLEX]: '复杂',
  },
  automation: {
    [AutomationLevel.MANUAL]: '手动',
    [AutomationLevel.SEMI_AUTO]: '半自动',
    [AutomationLevel.FULL_AUTO]: '全自动',
  },
  status: {
    [TestCaseStatus.DRAFT]: '草稿',
    [TestCaseStatus.APPROVED]: '已批准',
    [TestCaseStatus.ACTIVE]: '活跃',
    [TestCaseStatus.DEPRECATED]: '已废弃',
    [TestCaseStatus.ARCHIVED]: '已归档',
  },
}

const TestCaseEdit: React.FC = () => {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const caseId = Number(id)
  const { data: testCase, isLoading, error } = useTestCase(caseId)
  const updateTestCase = useUpdateTestCase()
  const [requirements, setRequirements] = useState<Requirement[]>([])
  const [requirementsLoading, setRequirementsLoading] = useState(false)
  const [requirementsError, setRequirementsError] = useState('')
  const [form, setForm] = useState<any | null>(null)
  const [steps, setSteps] = useState<any[]>([])

  useEffect(() => {
    let cancelled = false
    setRequirementsLoading(true)
    requirementService.getRequirements({ page: 1, size: 100, sort_by: 'updated_at', sort_order: 'desc' })
      .then((response) => {
        if (!cancelled) {
          setRequirements(response.data || [])
          setRequirementsError('')
        }
      })
      .catch((loadError) => {
        if (!cancelled) setRequirementsError(loadError?.message || '需求加载失败')
      })
      .finally(() => {
        if (!cancelled) setRequirementsLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!testCase) return
    setForm({
      requirement_id: Number(testCase.requirement_id || 0),
      case_title: testCase.case_title || '',
      case_description: testCase.case_description || '',
      case_type: testCase.case_type || TestCaseType.FUNCTIONAL,
      module: testCase.module || '',
      priority: testCase.priority || Priority.MEDIUM,
      complexity: testCase.complexity || Complexity.MEDIUM,
      automation_level: testCase.automation_level || AutomationLevel.MANUAL,
      preconditions: testCase.preconditions || '',
      expected_result: testCase.expected_result || '',
      status: testCase.status || TestCaseStatus.DRAFT,
    })
    const nextSteps = Array.isArray(testCase.test_steps) && testCase.test_steps.length
      ? testCase.test_steps.map((step, index) => ({
        step_number: index + 1,
        action: step.action || '',
        expected_result: step.expected_result || '',
        test_data: step.test_data || '',
      }))
      : [emptyStep(1)]
    setSteps(nextSteps)
  }, [testCase])

  const updateForm = (key: string, value: any) => {
    setForm((current: any) => ({ ...current, [key]: value }))
  }

  const updateStep = (index: number, key: string, value: string) => {
    setSteps((current) => current.map((step, stepIndex) => (
      stepIndex === index ? { ...step, [key]: value } : step
    )))
  }

  const addStep = () => {
    setSteps((current) => [...current, emptyStep(current.length + 1)])
  }

  const removeStep = (index: number) => {
    setSteps((current) => current
      .filter((_, stepIndex) => stepIndex !== index)
      .map((step, stepIndex) => ({ ...step, step_number: stepIndex + 1 })))
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!form) return
    const result = await updateTestCase.mutateAsync({
      id: caseId,
      data: {
        ...form,
        requirement_id: Number(form.requirement_id || 0) || null,
        test_steps: steps.map((step, index) => ({
          step_number: index + 1,
          action: String(step.action || '').trim(),
          expected_result: String(step.expected_result || '').trim(),
          test_data: String(step.test_data || '').trim(),
        })),
      },
    })
    navigate(`/test-manager/test-cases/${result.id}`)
  }

  if (isLoading || !form) {
    return <div className="flex h-64 items-center justify-center">加载中...</div>
  }

  if (error || !testCase) {
    return <div className="text-center text-red-500">测试用例加载失败</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link to={`/test-manager/test-cases/${caseId}`}>
          <Button variant="ghost" size="sm">
            <ArrowLeft className="mr-2 h-4 w-4" />
            返回详情
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold">编辑测试用例</h1>
          <p className="text-gray-600">{testCase.case_code}</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>基本信息</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Field label="用例标题">
              <Input value={form.case_title} onChange={(event) => updateForm('case_title', event.target.value)} required />
            </Field>
            <Field label="模块">
              <Input value={form.module} onChange={(event) => updateForm('module', event.target.value)} />
            </Field>
            <Field label="关联需求">
              <select
                value={String(form.requirement_id || '')}
                onChange={(event) => updateForm('requirement_id', Number(event.target.value || 0))}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              >
                <option value="">不关联需求</option>
                {requirements.map((requirement) => (
                  <option key={requirement.id} value={String(requirement.id)}>
                    {requirementLabel(requirement)}
                  </option>
                ))}
              </select>
              {requirementsLoading && <span className="text-xs text-gray-500">需求加载中...</span>}
              {requirementsError && <span className="text-xs text-red-600">{requirementsError}</span>}
            </Field>
            <Field label="用例类型">
              <EnumSelect value={form.case_type} options={labels.type} onChange={(value) => updateForm('case_type', value)} />
            </Field>
            <Field label="优先级">
              <EnumSelect value={form.priority} options={labels.priority} onChange={(value) => updateForm('priority', value)} />
            </Field>
            <Field label="复杂度">
              <EnumSelect value={form.complexity} options={labels.complexity} onChange={(value) => updateForm('complexity', value)} />
            </Field>
            <Field label="自动化级别">
              <EnumSelect value={form.automation_level} options={labels.automation} onChange={(value) => updateForm('automation_level', value)} />
            </Field>
            <Field label="状态">
              <EnumSelect value={form.status} options={labels.status} onChange={(value) => updateForm('status', value)} />
            </Field>
            <div className="md:col-span-2">
              <Field label="描述">
                <Textarea rows={3} value={form.case_description} onChange={(event) => updateForm('case_description', event.target.value)} />
              </Field>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>执行条件与结果</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Field label="前置条件">
              <Textarea rows={4} value={form.preconditions} onChange={(event) => updateForm('preconditions', event.target.value)} />
            </Field>
            <Field label="预期结果">
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
                <Textarea rows={2} value={step.action} onChange={(event) => updateStep(index, 'action', event.target.value)} placeholder="操作步骤" />
                <Textarea rows={2} value={step.expected_result} onChange={(event) => updateStep(index, 'expected_result', event.target.value)} placeholder="步骤预期结果" />
                <Textarea rows={2} value={step.test_data} onChange={(event) => updateStep(index, 'test_data', event.target.value)} placeholder="测试数据" />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => removeStep(index)}
                  disabled={steps.length <= 1}
                  aria-label="删除步骤"
                >
                  <Trash2 className="h-4 w-4 text-red-500" />
                </Button>
              </div>
            ))}
          </CardContent>
        </Card>

        <div className="flex justify-end gap-3">
          <Link to={`/test-manager/test-cases/${caseId}`}>
            <Button type="button" variant="outline">取消</Button>
          </Link>
          <Button type="submit" disabled={updateTestCase.isPending}>
            <Save className="mr-2 h-4 w-4" />
            保存
          </Button>
        </div>
      </form>
    </div>
  )
}

const Field = ({ label, children }: { label: string; children: React.ReactNode }) => (
  <label className="space-y-2">
    <span className="text-sm font-medium text-gray-700">{label}</span>
    {children}
  </label>
)

const EnumSelect = ({ value, options, onChange }: { value: string; options: Record<string, string>; onChange: (value: string) => void }) => (
  <select
    value={value}
    onChange={(event) => onChange(event.target.value)}
    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
  >
    {Object.entries(options).map(([optionValue, label]) => (
      <option key={optionValue} value={optionValue}>{label}</option>
    ))}
  </select>
)

export default TestCaseEdit
