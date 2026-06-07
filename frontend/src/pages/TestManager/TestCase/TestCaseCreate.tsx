// @ts-nocheck
import React, { useEffect, useState } from 'react'
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
import type { Requirement } from '../../../types/requirement'

const AI_IMPORT_DRAFT_KEY = 'ai-assistant:import-draft'

const readAiDraft = (stateDraft: any, destination: string) => {
  if (stateDraft?.source === 'ai-assistant' && stateDraft.destination === destination) return stateDraft

  try {
    const saved = JSON.parse(sessionStorage.getItem(AI_IMPORT_DRAFT_KEY) || 'null')
    return saved?.source === 'ai-assistant' && saved.destination === destination ? saved : null
  } catch {
    return null
  }
}

const firstReadableLine = (content = '', fallback = 'AI 导入测试用例') => {
  const line = content
    .split('\n')
    .map((item) => item.trim())
    .find((item) => item && !item.startsWith('|') && !/^[-*_]{3,}$/.test(item))

  return (line || fallback)
    .replace(/^#{1,6}\s*/, '')
    .replace(/^[\d一二三四五六七八九十]+[.、)]\s*/, '')
    .slice(0, 100)
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
  .replace(/^[\d一二三四五六七八九十]+[.、)]\s*/, '')
  .replace(/^(用例名称|用例标题|标题|测试场景|场景|名称)[:：]\s*/i, '')
  .replace(/[|]/g, '')
  .slice(0, 120)

const splitMarkdownTable = (content = '') => {
  const rows = content
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.startsWith('|') && line.endsWith('|'))
    .map((line) => line.slice(1, -1).split('|').map((cell) => cell.trim()))
    .filter((cells) => cells.some((cell) => cell && !/^:?-{3,}:?$/.test(cell)))

  if (rows.length < 2) return null
  return { headers: rows[0], rows: rows.slice(1) }
}

const normalizeHeader = (value = '') => cleanImportedText(value)
  .toLowerCase()
  .replace(/[\s_*`~#：:，,。.、；;（）()[\]{}<>《》]/g, '')

const pickColumnIndex = (headers: string[], aliases: string[], excludes: string[] = []) => {
  const normalizedAliases = aliases.map(normalizeHeader).filter(Boolean)
  const normalizedExcludes = excludes.map(normalizeHeader).filter(Boolean)
  let best = { index: -1, score: 0 }

  headers.forEach((header, index) => {
    const normalized = normalizeHeader(header)
    if (!normalized || normalizedExcludes.some((exclude) => normalized.includes(exclude))) return

    const score = normalizedAliases.reduce((current, alias) => {
      if (normalized === alias) return Math.max(current, 100)
      if (normalized.startsWith(alias)) return Math.max(current, 80)
      if (normalized.includes(alias)) return Math.max(current, 60)
      if (alias.includes(normalized) && normalized.length >= 2) return Math.max(current, 40)
      return current
    }, 0)

    if (score > best.score) best = { index, score }
  })

  return best.score > 0 ? best.index : -1
}

const pickColumn = (headers: string[], row: string[], aliases: string[], excludes: string[] = []) => {
  const index = pickColumnIndex(headers, aliases, excludes)
  return index >= 0 ? cleanImportedText(row[index] || '') : ''
}

const getColumnValue = (table: any, aliases: string[], excludes: string[] = []) => {
  const firstRow = table?.rows?.[0] || []
  return pickColumn(table?.headers || [], firstRow, aliases, excludes)
}

const splitListItems = (value = '') => {
  const normalized = cleanImportedText(value)
    .replace(/([。；;])\s*(?=(?:\d+|[一二三四五六七八九十]+)[.、)]\s*)/g, '$1\n')
    .replace(/\s+(?=(?:\d+|[一二三四五六七八九十]+)[.、)]\s*)/g, '\n')
    .replace(/\n\s*[-*]\s+/g, '\n')

  const lines = normalized
    .split('\n')
    .map((line) => line
      .replace(/^\s*(?:步骤|step)?\s*(?:\d+|[一二三四五六七八九十]+)[.、)：:)]\s*/i, '')
      .replace(/^\s*[-*]\s*/, '')
      .trim())
    .filter(Boolean)

  if (lines.length > 1) return lines

  if (!lines.length) return []
  const fallback = lines[0]
  const semicolonParts = fallback
    .split(/[；;]/)
    .map((item) => item.trim())
    .filter(Boolean)
  return semicolonParts.length > 1 ? semicolonParts : [fallback]
}

const splitDataItems = (value = '') => {
  const normalized = cleanImportedText(value)
  if (!normalized) return []
  const hasNumberedItems = /(?:^|\n)\s*(?:\d+|[一二三四五六七八九十]+)[.、)]\s*/.test(normalized)
  if (!hasNumberedItems && !normalized.includes('\n')) return [normalized]
  return splitListItems(value)
}

const buildStepItems = (actionText = '', expectedText = '', testDataText = '') => {
  const actions = splitListItems(actionText)
  const expectedItems = splitListItems(expectedText)
  const dataItems = splitDataItems(testDataText)
  const fallbackExpected = cleanImportedText(expectedText) || '符合该步骤的预期结果。'

  if (!actions.length) return []
  return actions.map((action, index) => ({
    step_number: index + 1,
    action,
    expected_result: expectedItems[index] || (expectedItems.length === 1 ? expectedItems[0] : fallbackExpected),
    test_data: dataItems[index] || (dataItems.length === 1 ? dataItems[0] : ''),
  }))
}

const extractSectionValue = (content = '', labels: string[]) => {
  const normalizedLabels = labels.map((label) => label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  const pattern = new RegExp(`(?:^|\\n)\\s*(?:${normalizedLabels.join('|')})\\s*[:：]\\s*([^\\n]+(?:\\n(?!\\s*\\S+\\s*[:：]).+)*)`, 'i')
  const match = cleanImportedText(content).match(pattern)
  return cleanImportedText(match?.[1] || '')
}

const parsePriority = (value = '') => {
  const text = cleanImportedText(value).toLowerCase()
  if (/critical|blocker|p0|严重|紧急|最高/.test(text)) return Priority.CRITICAL
  if (/high|p1|高/.test(text)) return Priority.HIGH
  if (/low|p3|低/.test(text)) return Priority.LOW
  return Priority.MEDIUM
}

const parseCaseType = (value = '') => {
  const text = cleanImportedText(value).toLowerCase()
  if (/api|接口|integration|集成/.test(text)) return TestCaseType.INTEGRATION
  if (/system|系统/.test(text)) return TestCaseType.SYSTEM
  if (/acceptance|验收/.test(text)) return TestCaseType.ACCEPTANCE
  if (/regression|回归/.test(text)) return TestCaseType.REGRESSION
  if (/smoke|冒烟/.test(text)) return TestCaseType.SMOKE
  if (/non[_\s-]?functional|非功能|兼容/.test(text)) return TestCaseType.NON_FUNCTIONAL
  if (/performance|性能/.test(text)) return TestCaseType.PERFORMANCE
  if (/security|安全/.test(text)) return TestCaseType.SECURITY
  if (/usability|易用/.test(text)) return TestCaseType.USABILITY
  return TestCaseType.FUNCTIONAL
}

const titleAliases = ['用例标题', '用例名称', '测试标题', '标题', '名称', '测试场景', '场景', 'case title', 'title', 'case name']
const titleExcludes = ['编号', 'id', 'code', '步骤', '预期', '结果', '数据', '参数', '优先级', '类型', '前置']
const moduleAliases = ['模块', '功能模块', '所属模块', '业务模块', 'module', 'feature']
const descriptionAliases = ['描述', '用例描述', '测试目标', '测试目的', '目的', '说明', 'description']
const preconditionAliases = ['前置条件', '前置', '执行前提', '条件', 'precondition', 'given']
const stepAliases = ['测试步骤', '操作步骤', '执行步骤', '步骤描述', '操作内容', '操作', '动作', '步骤', 'action', 'actions', 'step', 'steps']
const stepExcludes = ['步骤编号', '序号', '编号', 'id', 'no', 'number']
const expectedAliases = ['预期结果', '期望结果', '预期', '结果', 'expected result', 'expected']
const dataAliases = ['测试数据', '数据', '参数', '入参', 'test data', 'data']
const priorityAliases = ['优先级', 'priority']
const typeAliases = ['类型', '用例类型', '测试类型', 'case type', 'type']
const requirementAliases = ['关联需求', '需求ID', '需求编号', '需求编码', '需求标题', '需求', 'requirement id', 'requirement code', 'requirement']

const parseRequirementId = (value = '') => {
  const text = cleanImportedText(value)
  if (/^\d+$/.test(text)) return Number(text)
  const explicit = text.match(/(?:需求ID|requirement id|req id)\s*[:：#-]?\s*(\d+)/i)
  return explicit ? Number(explicit[1]) : 0
}

const requirementLabel = (requirement: Requirement) => {
  const code = requirement.requirement_code || `REQ-${requirement.id}`
  return `${code} - ${requirement.title}`
}

const findRequirementByReference = (requirements: Requirement[], reference = '') => {
  const text = cleanImportedText(reference).toLowerCase()
  if (!text) return null
  const parsedId = parseRequirementId(text)
  if (parsedId) return requirements.find((item) => Number(item.id) === parsedId) || null

  return requirements.find((item) => {
    const code = (item.requirement_code || '').toLowerCase()
    const title = (item.title || '').toLowerCase()
    return Boolean(
      (code && (text.includes(code) || code.includes(text))) ||
      (title && (text.includes(title) || title.includes(text)))
    )
  }) || null
}

const buildInitialForm = (draft: any) => {
  if (!draft) {
    return {
      requirement_id: 0,
      _requirement_reference: '',
      case_title: '',
      case_description: '',
      case_type: TestCaseType.FUNCTIONAL,
      module: '',
      priority: Priority.MEDIUM,
      complexity: Complexity.MEDIUM,
      automation_level: AutomationLevel.MANUAL,
      preconditions: '',
      expected_result: '',
    }
  }

  const content = draft?.content || ''
  const table = splitMarkdownTable(content)
  const headers = table?.headers || []
  const rows = table?.rows || []
  const tableTitleIndex = pickColumnIndex(headers, titleAliases, titleExcludes)
  const tableTitleValues = tableTitleIndex >= 0
    ? rows.map((row) => cleanTitle(row[tableTitleIndex] || '')).filter(Boolean)
    : []
  const rowsBelongToSameCase = tableTitleIndex < 0 || Array.from(new Set(tableTitleValues)).length <= 1
  const joinColumnValues = (aliases: string[], excludes: string[] = []) => {
    const index = pickColumnIndex(headers, aliases, excludes)
    if (index < 0 || rows.length <= 1 || !rowsBelongToSameCase) return ''
    const values = rows.map((row) => cleanImportedText(row[index] || '')).filter(Boolean)
    const uniqueValues = Array.from(new Set(values))
    if (uniqueValues.length <= 1) return uniqueValues[0] || ''
    return values.map((value, index) => `${index + 1}. ${value}`).join('\n')
  }
  const title = (
    getColumnValue(table, titleAliases, titleExcludes)
    || extractSectionValue(content, titleAliases)
    || draft?.title
    || firstReadableLine(content)
  )
  const module = getColumnValue(table, moduleAliases) || extractSectionValue(content, moduleAliases)
  const description = (
    getColumnValue(table, descriptionAliases)
    || extractSectionValue(content, descriptionAliases)
    || `由 AI 助手导入：${cleanTitle(title)}${module ? `（${cleanTitle(module)}）` : ''}。`
  )
  const preconditions = (
    getColumnValue(table, preconditionAliases)
    || extractSectionValue(content, preconditionAliases)
    || '无特殊前置条件。'
  )
  const expectedResult = (
    joinColumnValues(expectedAliases)
    || getColumnValue(table, expectedAliases)
    || extractSectionValue(content, expectedAliases)
    || '按测试步骤执行后，实际结果符合业务需求和验收标准。'
  )
  const priority = getColumnValue(table, priorityAliases)
  const caseType = getColumnValue(table, typeAliases)
  const requirementReference = (
    getColumnValue(table, requirementAliases)
    || extractSectionValue(content, requirementAliases)
  )

  return {
    requirement_id: parseRequirementId(requirementReference),
    _requirement_reference: requirementReference,
    case_title: cleanTitle(title),
    case_description: cleanImportedText(description),
    case_type: parseCaseType(caseType),
    module: cleanTitle(module).slice(0, 80),
    priority: parsePriority(priority),
    complexity: Complexity.MEDIUM,
    automation_level: AutomationLevel.MANUAL,
    preconditions,
    expected_result: expectedResult,
  }
}

const buildInitialSteps = (draft: any) => {
  if (!draft) return [{ step_number: 1, action: '', expected_result: '', test_data: '' }]

  const table = splitMarkdownTable(draft?.content || '')
  if (table) {
    const stepIndex = pickColumnIndex(table.headers, stepAliases, stepExcludes)
    const expectedIndex = pickColumnIndex(table.headers, expectedAliases)
    const dataIndex = pickColumnIndex(table.headers, dataAliases)
    const titleIndex = pickColumnIndex(table.headers, titleAliases, titleExcludes)

    const titleValues = titleIndex >= 0
      ? table.rows.map((row) => cleanTitle(row[titleIndex] || '')).filter(Boolean)
      : []
    const uniqueTitles = Array.from(new Set(titleValues))
    const rowsBelongToSameCase = titleIndex < 0 || uniqueTitles.length <= 1

    if (stepIndex >= 0 && table.rows.length > 1 && rowsBelongToSameCase) {
      const rowSteps = table.rows
        .map((row, index) => ({
          step_number: index + 1,
          action: cleanImportedText(row[stepIndex] || row[0] || ''),
          expected_result: cleanImportedText(row[expectedIndex] || row[row.length - 1] || '符合该步骤的预期结果。'),
          test_data: dataIndex >= 0 ? cleanImportedText(row[dataIndex] || '') : '',
        }))
        .filter((step) => step.action)

      if (rowSteps.length) return rowSteps
    }

    const firstRow = table.rows[0] || []
    const actionText = stepIndex >= 0 ? firstRow[stepIndex] : ''
    const expectedText = expectedIndex >= 0 ? firstRow[expectedIndex] : firstRow[firstRow.length - 1] || ''
    const testData = dataIndex >= 0 ? firstRow[dataIndex] : ''
    const parsedSteps = buildStepItems(actionText, expectedText, testData)

    if (parsedSteps.length) return parsedSteps
  }

  const sectionSteps = buildStepItems(
    extractSectionValue(draft?.content || '', stepAliases),
    extractSectionValue(draft?.content || '', expectedAliases),
    extractSectionValue(draft?.content || '', dataAliases),
  )
  if (sectionSteps.length) return sectionSteps

  return [
    {
      step_number: 1,
      action: draft ? '根据 AI 导入内容拆分并补充具体测试操作。' : '',
      expected_result: draft ? '实际结果符合 AI 分析中的预期与验收条件。' : '',
      test_data: '',
    },
  ]
}

const TestCaseCreate: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const [aiDraft] = useState(() => readAiDraft((location.state as any)?.aiImport, 'test-case'))
  const createTestCase = useCreateTestCase()
  const [form, setForm] = useState(() => buildInitialForm(aiDraft))
  const [steps, setSteps] = useState(() => buildInitialSteps(aiDraft))
  const [requirements, setRequirements] = useState<Requirement[]>([])
  const [requirementsLoading, setRequirementsLoading] = useState(false)
  const [requirementsError, setRequirementsError] = useState('')

  useEffect(() => {
    if (aiDraft) sessionStorage.removeItem(AI_IMPORT_DRAFT_KEY)
  }, [aiDraft])

  useEffect(() => {
    let cancelled = false
    setRequirementsLoading(true)
    requirementService.getRequirements({ page: 1, size: 100, sort_by: 'updated_at', sort_order: 'desc' })
      .then((response) => {
        if (cancelled) return
        const nextRequirements = response.data || []
        setRequirements(nextRequirements)
        setRequirementsError('')

        setForm((current) => {
          if (Number(current.requirement_id || 0) > 0) return current
          const matched = findRequirementByReference(nextRequirements, current._requirement_reference)
          return matched ? { ...current, requirement_id: matched.id } : current
        })
      })
      .catch((error) => {
        if (!cancelled) setRequirementsError(error?.message || '加载需求失败')
      })
      .finally(() => {
        if (!cancelled) setRequirementsLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  const updateForm = (key: string, value: any) => setForm((current) => ({ ...current, [key]: value }))

  const updateStep = (index: number, key: string, value: string) => {
    setSteps((current) => current.map((step, stepIndex) => (
      stepIndex === index ? { ...step, [key]: value } : step
    )))
  }

  const addStep = () => {
    setSteps((current) => [
      ...current,
      { step_number: current.length + 1, action: '', expected_result: '', test_data: '' },
    ])
  }

  const removeStep = (index: number) => {
    setSteps((current) => current
      .filter((_, stepIndex) => stepIndex !== index)
      .map((step, stepIndex) => ({ ...step, step_number: stepIndex + 1 })))
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    const { _requirement_reference, ...formData } = form
    const result = await createTestCase.mutateAsync({
      ...formData,
      requirement_id: Number(form.requirement_id || 0) || undefined,
      case_title: cleanTitle(form.case_title),
      case_description: cleanImportedText(form.case_description),
      module: cleanTitle(form.module).slice(0, 80),
      preconditions: cleanImportedText(form.preconditions),
      expected_result: cleanImportedText(form.expected_result),
      test_steps: steps.map((step, index) => ({
        ...step,
        step_number: index + 1,
        action: cleanImportedText(step.action),
        expected_result: cleanImportedText(step.expected_result),
        test_data: cleanImportedText(step.test_data || ''),
      })),
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
          <p className="text-gray-600">填写基础信息、前置条件、步骤和预期结果。</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {aiDraft && (
          <Card className="border-blue-200 bg-blue-50">
            <CardContent className="p-4 text-sm text-blue-800">
              已从 AI 助手导入测试用例草稿。保存前请核对标题、步骤、测试数据和预期结果。
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader>
            <CardTitle>基本信息</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Field label="用例标题">
              <Input value={form.case_title} onChange={(e) => updateForm('case_title', e.target.value)} required />
            </Field>
            <Field label="模块">
              <Input value={form.module} onChange={(e) => updateForm('module', e.target.value)} />
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
              {form._requirement_reference && !form.requirement_id && !requirementsLoading && (
                <span className="text-xs text-amber-600">
                  AI 提到的需求未自动匹配：{form._requirement_reference}
                </span>
              )}
            </Field>
            <Field label="用例类型">
              <Select value={form.case_type} onValueChange={(value) => updateForm('case_type', value)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value={TestCaseType.FUNCTIONAL}>功能测试</SelectItem>
                  <SelectItem value={TestCaseType.NON_FUNCTIONAL}>非功能测试</SelectItem>
                  <SelectItem value={TestCaseType.INTEGRATION}>集成测试</SelectItem>
                  <SelectItem value={TestCaseType.SYSTEM}>系统测试</SelectItem>
                  <SelectItem value={TestCaseType.ACCEPTANCE}>验收测试</SelectItem>
                  <SelectItem value={TestCaseType.REGRESSION}>回归测试</SelectItem>
                  <SelectItem value={TestCaseType.SMOKE}>冒烟测试</SelectItem>
                  <SelectItem value={TestCaseType.PERFORMANCE}>性能测试</SelectItem>
                  <SelectItem value={TestCaseType.SECURITY}>安全测试</SelectItem>
                  <SelectItem value={TestCaseType.USABILITY}>易用性测试</SelectItem>
                </SelectContent>
              </Select>
            </Field>
            <Field label="优先级">
              <Select value={form.priority} onValueChange={(value) => updateForm('priority', value)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value={Priority.CRITICAL}>紧急</SelectItem>
                  <SelectItem value={Priority.HIGH}>高</SelectItem>
                  <SelectItem value={Priority.MEDIUM}>中</SelectItem>
                  <SelectItem value={Priority.LOW}>低</SelectItem>
                </SelectContent>
              </Select>
            </Field>
            <Field label="复杂度">
              <Select value={form.complexity} onValueChange={(value) => updateForm('complexity', value)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value={Complexity.SIMPLE}>简单</SelectItem>
                  <SelectItem value={Complexity.MEDIUM}>中等</SelectItem>
                  <SelectItem value={Complexity.COMPLEX}>复杂</SelectItem>
                </SelectContent>
              </Select>
            </Field>
            <Field label="自动化级别">
              <Select value={form.automation_level} onValueChange={(value) => updateForm('automation_level', value)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value={AutomationLevel.MANUAL}>手动</SelectItem>
                  <SelectItem value={AutomationLevel.SEMI_AUTO}>半自动</SelectItem>
                  <SelectItem value={AutomationLevel.FULL_AUTO}>全自动</SelectItem>
                </SelectContent>
              </Select>
            </Field>
            <div className="md:col-span-2">
              <Field label="描述">
                <Textarea rows={3} value={form.case_description} onChange={(e) => updateForm('case_description', e.target.value)} />
              </Field>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>前置条件与预期</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Field label="前置条件">
              <Textarea rows={3} value={form.preconditions} onChange={(e) => updateForm('preconditions', e.target.value)} />
            </Field>
            <Field label="总体预期结果">
              <Textarea rows={3} value={form.expected_result} onChange={(e) => updateForm('expected_result', e.target.value)} />
            </Field>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>测试步骤</CardTitle>
              <Button type="button" variant="outline" size="sm" onClick={addStep}>
                <Plus className="mr-1 h-4 w-4" />
                添加步骤
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {steps.map((step, index) => (
              <div key={index} className="rounded-md border p-4">
                <div className="mb-3 flex items-center justify-between">
                  <span className="font-medium">步骤 {index + 1}</span>
                  {steps.length > 1 && (
                    <Button type="button" variant="ghost" size="sm" onClick={() => removeStep(index)}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  )}
                </div>
                <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                  <Field label="操作">
                    <Textarea rows={2} value={step.action} onChange={(e) => updateStep(index, 'action', e.target.value)} required />
                  </Field>
                  <Field label="预期结果">
                    <Textarea rows={2} value={step.expected_result} onChange={(e) => updateStep(index, 'expected_result', e.target.value)} required />
                  </Field>
                  <div className="md:col-span-2">
                    <Field label="测试数据">
                      <Input value={step.test_data} onChange={(e) => updateStep(index, 'test_data', e.target.value)} />
                    </Field>
                  </div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <div className="flex justify-end">
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

export default TestCaseCreate
