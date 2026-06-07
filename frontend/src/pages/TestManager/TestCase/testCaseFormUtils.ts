import {
  AutomationLevel,
  Complexity,
  Priority,
  TestCaseType,
  type TestStep,
} from '../../../types/testmanager'

export const AI_IMPORT_DRAFT_KEY = 'ai-assistant:import-draft'

export const emptyStep = (stepNumber = 1): TestStep => ({
  step_number: stepNumber,
  action: '',
  expected_result: '',
  test_data: '',
})

export const cleanText = (value = '') => value
  .replace(/<br\s*\/?>/gi, '\n')
  .replace(/<\/?(p|div|li|ul|ol|tr|td|th)>/gi, '\n')
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

export const cleanTitle = (value = '') => cleanText(value)
  .replace(/^#{1,6}\s*/, '')
  .replace(/^\s*(?:\d+|[一二三四五六七八九十]+)[.、)]\s*/, '')
  .replace(/^(用例名称|用例标题|标题|测试场景|场景|名称)[:：]\s*/i, '')
  .replace(/[|]/g, '')
  .slice(0, 120)

const splitMarkdownTable = (content = '') => {
  const rows = content
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.startsWith('|') && line.endsWith('|'))
    .map((line) => line.slice(1, -1).split('|').map((cell) => cleanText(cell)))
    .filter((cells) => cells.some((cell) => cell && !/^:?-{3,}:?$/.test(cell)))

  if (rows.length < 2) return null
  return { headers: rows[0], rows: rows.slice(1) }
}

const normalizeHeader = (value = '') => cleanText(value).toLowerCase().replace(/[\s_*`~#：:，,。；;()[\]{}<>]/g, '')

const findColumn = (headers: string[], aliases: string[]) => {
  const normalizedAliases = aliases.map(normalizeHeader)
  return headers.findIndex((header) => {
    const normalized = normalizeHeader(header)
    return normalizedAliases.some((alias) => normalized === alias || normalized.includes(alias))
  })
}

const pickSection = (content: string, labels: string[]) => {
  const escaped = labels.map((label) => label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  const pattern = new RegExp(`(?:^|\\n)\\s*(?:${escaped.join('|')})\\s*[:：]\\s*([^\\n]+(?:\\n(?!\\s*\\S+\\s*[:：]).+)*)`, 'i')
  return cleanText(cleanText(content).match(pattern)?.[1] || '')
}

const splitItems = (value = '') => {
  const normalized = cleanText(value)
    .replace(/([。；;])\s*(?=(?:\d+|[一二三四五六七八九十]+)[.、)]\s*)/g, '$1\n')
    .replace(/\s+(?=(?:\d+|[一二三四五六七八九十]+)[.、)]\s*)/g, '\n')
  const lines = normalized
    .split('\n')
    .map((line) => line.replace(/^\s*(?:步骤|step)?\s*(?:\d+|[一二三四五六七八九十]+)[.、)：:)]\s*/i, '').replace(/^\s*[-*]\s*/, '').trim())
    .filter(Boolean)

  if (lines.length > 1) return lines
  return lines[0] ? lines[0].split(/[；;]/).map((item) => item.trim()).filter(Boolean) : []
}

const parsePriority = (value = '') => {
  const text = cleanText(value).toLowerCase()
  if (/critical|blocker|p0|紧急|严重|最高/.test(text)) return Priority.CRITICAL
  if (/high|p1|高/.test(text)) return Priority.HIGH
  if (/low|p3|低/.test(text)) return Priority.LOW
  return Priority.MEDIUM
}

const parseCaseType = (value = '') => {
  const text = cleanText(value).toLowerCase()
  if (/integration|集成|接口|api/.test(text)) return TestCaseType.INTEGRATION
  if (/system|系统/.test(text)) return TestCaseType.SYSTEM
  if (/acceptance|验收/.test(text)) return TestCaseType.ACCEPTANCE
  if (/regression|回归/.test(text)) return TestCaseType.REGRESSION
  if (/smoke|冒烟/.test(text)) return TestCaseType.SMOKE
  if (/performance|性能/.test(text)) return TestCaseType.PERFORMANCE
  if (/security|安全/.test(text)) return TestCaseType.SECURITY
  if (/usability|易用/.test(text)) return TestCaseType.USABILITY
  if (/non.?functional|非功能/.test(text)) return TestCaseType.NON_FUNCTIONAL
  return TestCaseType.FUNCTIONAL
}

export const readAiDraft = (stateDraft: any, destination: string) => {
  if (stateDraft?.source === 'ai-assistant' && stateDraft.destination === destination) return stateDraft
  try {
    const saved = JSON.parse(sessionStorage.getItem(AI_IMPORT_DRAFT_KEY) || 'null')
    return saved?.source === 'ai-assistant' && saved.destination === destination ? saved : null
  } catch {
    return null
  }
}

export const buildFormFromAiDraft = (draft: any) => {
  const content = cleanText(draft?.content || '')
  const table = splitMarkdownTable(content)
  const headers = table?.headers || []
  const firstRow = table?.rows?.[0] || []
  const getCell = (aliases: string[]) => {
    const index = findColumn(headers, aliases)
    return index >= 0 ? cleanText(firstRow[index] || '') : ''
  }

  const title = cleanTitle(
    getCell(['用例标题', '用例名称', '标题', '场景', 'case title', 'title', 'name']) ||
    pickSection(content, ['用例标题', '用例名称', '标题', '测试场景']) ||
    draft?.title ||
    content.split('\n').map(cleanTitle).find(Boolean) ||
    'AI 导入测试用例'
  )

  return {
    test_plan_id: 0,
    requirement_id: 0,
    case_title: title,
    case_description: cleanText(
      getCell(['描述', '用例描述', '测试目的', 'description']) ||
      pickSection(content, ['描述', '用例描述', '测试目的', '说明']) ||
      `由 AI 助手导入：${title}`
    ),
    case_type: parseCaseType(getCell(['类型', '用例类型', '测试类型', 'case type', 'type'])),
    module: cleanTitle(getCell(['模块', '功能模块', 'module', 'feature'])).slice(0, 80),
    priority: parsePriority(getCell(['优先级', 'priority'])),
    complexity: Complexity.MEDIUM,
    automation_level: AutomationLevel.MANUAL,
    preconditions: cleanText(getCell(['前置条件', '前置', 'precondition']) || pickSection(content, ['前置条件', '前置']) || '无特殊前置条件'),
    expected_result: cleanText(getCell(['预期结果', '期望结果', 'expected']) || pickSection(content, ['预期结果', '期望结果']) || '实际结果符合业务需求和验收标准'),
  }
}

export const buildStepsFromAiDraft = (draft: any): TestStep[] => {
  if (!draft) return [emptyStep(1)]

  const content = cleanText(draft?.content || '')
  const table = splitMarkdownTable(content)
  if (table) {
    const stepIndex = findColumn(table.headers, ['测试步骤', '操作步骤', '执行步骤', '步骤', 'action', 'steps'])
    const expectedIndex = findColumn(table.headers, ['预期结果', '期望结果', 'expected'])
    const dataIndex = findColumn(table.headers, ['测试数据', '数据', '参数', 'test data', 'data'])
    if (stepIndex >= 0) {
      const steps = table.rows.map((row, index) => ({
        step_number: index + 1,
        action: cleanText(row[stepIndex] || ''),
        expected_result: cleanText(row[expectedIndex] || row[row.length - 1] || '符合该步骤预期'),
        test_data: cleanText(row[dataIndex] || ''),
      })).filter((step) => step.action)
      if (steps.length) return steps
    }
  }

  const actions = splitItems(pickSection(content, ['测试步骤', '操作步骤', '执行步骤', '步骤']))
  const expected = splitItems(pickSection(content, ['预期结果', '期望结果']))
  if (actions.length) {
    return actions.map((action, index) => ({
      step_number: index + 1,
      action,
      expected_result: expected[index] || expected[0] || '符合该步骤预期',
      test_data: '',
    }))
  }

  return [{
    step_number: 1,
    action: '根据 AI 导入内容补充具体测试操作',
    expected_result: '实际结果符合 AI 分析中的预期和验收条件',
    test_data: '',
  }]
}

export const normalizeSteps = (steps: TestStep[]) => {
  const normalized = steps
    .map((step) => ({
      ...step,
      action: cleanText(step.action),
      expected_result: cleanText(step.expected_result),
      test_data: cleanText(String(step.test_data || '')),
    }))
    .filter((step) => step.action || step.expected_result)
    .map((step, index) => ({ ...step, step_number: index + 1 }))

  return normalized.length ? normalized : [emptyStep(1)]
}

