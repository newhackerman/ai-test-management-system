export interface TemplateVariable {
  name: string
  type: 'string' | 'number' | 'boolean' | 'array' | 'object'
  description: string
  required: boolean
  default_value?: unknown
  validation_rules?: Record<string, unknown>
}

export interface PromptTemplate {
  id: number
  name: string
  title: string
  description: string
  category: string
  subcategory?: string
  content: string
  variables: TemplateVariable[]
  default_values: Record<string, unknown>
  example_context: Record<string, unknown>
  supported_providers: string[]
  supported_models: string[]
  use_cases: string[]
  tags: string[]
  visibility: 'PRIVATE' | 'TEAM' | 'PUBLIC'
  owner_id: number
  team_id?: number
  is_featured: boolean
  is_verified: boolean
  version: string
  parent_template_id?: number
  is_latest_version: boolean
  usage_count: number
  rating_avg: number
  rating_count: number
  last_used_at?: string
  created_at: string
  updated_at: string
}

export interface PromptTemplateCreate {
  name: string
  title: string
  description: string
  category: string
  subcategory?: string
  content: string
  variables: TemplateVariable[]
  default_values?: Record<string, unknown>
  example_context?: Record<string, unknown>
  supported_providers?: string[]
  supported_models?: string[]
  use_cases?: string[]
  tags?: string[]
  visibility: 'PRIVATE' | 'TEAM' | 'PUBLIC'
  team_id?: number
}

export interface PromptTemplateUpdate extends Partial<PromptTemplateCreate> {}

export interface TemplateSearchRequest {
  query?: string
  category?: string
  visibility?: string
  owner_id?: number
  is_featured?: boolean
  is_verified?: boolean
  tags?: string[]
  sort_by?: string
  sort_order?: 'asc' | 'desc'
  page?: number
  size?: number
}

export interface TemplateListResponse {
  templates: PromptTemplate[]
  total: number
  page: number
  size: number
  pages: number
}

export interface TemplateRenderRequest {
  template_id: number
  context: Record<string, unknown>
}

export interface TemplateRenderResponse {
  rendered_content: string
  template_id: number
  template_name: string
  variables_used: string[]
  missing_variables: string[]
}

export interface TemplateUsage {
  template_id: number
  ai_provider: string
  ai_model?: string
  use_case?: string
  success: boolean
  tokens_used?: number
  response_time?: number
  user_rating?: number
  user_feedback?: string
  variable_values?: Record<string, unknown>
}

export interface TemplateStatistics {
  total_templates: number
  public_templates: number
  private_templates: number
  featured_templates: number
  category_distribution: Record<string, number>
  usage_statistics: Record<string, unknown>
  top_templates: PromptTemplate[]
  recent_templates: PromptTemplate[]
}

export interface TemplateCategory {
  value: string
  label: string
  description: string
}

export interface VisibilityOption {
  value: string
  label: string
  description: string
}

export interface TestScenario {
  name: string
  context: Record<string, unknown>
  expected_output?: string
  evaluation_criteria?: string[]
  ai_provider?: string
  ai_model?: string
}

export interface TestResult {
  success: boolean
  ai_provider: string
  ai_model: string
  prompt: string
  response?: string
  error?: string
  response_time: number
  token_usage: number
  timestamp: string
  scenario_index?: number
  scenario_name?: string
  expected_output?: string
  evaluation_criteria?: string[]
}

export interface TemplateTestRequest {
  context: Record<string, unknown>
  ai_provider?: string
  ai_model?: string
  test_scenarios?: TestScenario[]
}

export interface PerformanceMetrics {
  avg_response_time: number
  min_response_time: number
  max_response_time: number
  total_token_usage: number
  avg_token_usage: number
}

export interface TemplateTestResponse {
  success: boolean
  template_id: number
  template_name: string
  rendered_content: string
  variables_used: string[]
  test_results: TestResult[]
  success_rate: number
  total_tests: number
  successful_tests: number
  test_timestamp: string
  performance_metrics: PerformanceMetrics
  error?: string
  missing_variables?: string[]
}

export interface TestCase {
  name: string
  context: Record<string, unknown>
  expected_output?: string
  scenarios?: TestScenario[]
}

export interface BatchTemplateTestRequest {
  test_cases: TestCase[]
  ai_providers?: string[]
  ai_models?: string[]
}

export interface BatchTestResult {
  ai_provider: string
  ai_model: string
  test_results: Array<{
    test_case_index: number
    test_case_name: string
    result: TemplateTestResponse
  }>
  success_rate: number
  total_cases: number
  successful_cases: number
}

export interface BatchTemplateTestResponse {
  success: boolean
  template_id: number
  template_name: string
  batch_results: BatchTestResult[]
  overall_success_rate: number
  total_provider_model_combinations: number
  total_test_cases: number
  test_timestamp: string
}

export interface TemplateTestHistoryResponse {
  template_id: number
  template_name: string
  test_history: TestHistoryItem[]
  total: number
  page: number
  size: number
  pages: number
}

export interface TestHistoryItem {
  id: number
  test_timestamp: string
  ai_provider: string
  ai_model: string
  success_rate: number
  total_tests: number
  successful_tests: number
  performance_metrics: PerformanceMetrics
}

export interface TemplateEvaluationRequest {
  criteria: string[]
  test_data: Array<{
    context: Record<string, unknown>
    ai_provider?: string
    ai_model?: string
  }>
}

export interface PerformanceTestResult {
  test_index: number
  response_time: number
  success: boolean
  token_usage: number
  result: TemplateTestResponse
}

export interface TemplateEvaluationResponse {
  success: boolean
  template_id: number
  template_name: string
  performance_results: PerformanceTestResult[]
  performance_metrics: PerformanceMetrics
  evaluation_timestamp: string
}

export interface TestValidation {
  isValid: boolean
  score: number
  issues: string[]
}

const STORAGE_KEY = 'prompt_templates'

class PromptTemplateService {
  private templates: PromptTemplate[] = this.loadTemplates()

  async createTemplate(templateData: PromptTemplateCreate): Promise<PromptTemplate> {
    const now = new Date().toISOString()
    const template: PromptTemplate = {
      ...templateData,
      id: Date.now(),
      default_values: templateData.default_values || {},
      example_context: templateData.example_context || {},
      supported_providers: templateData.supported_providers || ['openai'],
      supported_models: templateData.supported_models || [],
      use_cases: templateData.use_cases || [],
      tags: templateData.tags || [],
      owner_id: 1,
      is_featured: false,
      is_verified: false,
      version: '1.0.0',
      is_latest_version: true,
      usage_count: 0,
      rating_avg: 0,
      rating_count: 0,
      created_at: now,
      updated_at: now,
    }
    this.templates = [template, ...this.templates]
    this.persist()
    return template
  }

  async getTemplate(templateId: number): Promise<PromptTemplate> {
    const template = this.templates.find((item) => item.id === templateId)
    if (!template) throw new Error('模板不存在')
    return template
  }

  async updateTemplate(templateId: number, templateData: PromptTemplateUpdate): Promise<PromptTemplate> {
    const template = await this.getTemplate(templateId)
    const updated: PromptTemplate = { ...template, ...templateData, updated_at: new Date().toISOString() }
    this.templates = this.templates.map((item) => (item.id === templateId ? updated : item))
    this.persist()
    return updated
  }

  async deleteTemplate(templateId: number): Promise<void> {
    this.templates = this.templates.filter((item) => item.id !== templateId)
    this.persist()
  }

  async searchTemplates(searchRequest: TemplateSearchRequest): Promise<TemplateListResponse> {
    return this.list(searchRequest)
  }

  async getTemplates(params: TemplateSearchRequest = {}): Promise<TemplateListResponse> {
    return this.list(params)
  }

  async getMyTemplates(params: TemplateSearchRequest = {}): Promise<TemplateListResponse> {
    return this.list({ ...params, owner_id: 1 })
  }

  async renderTemplate(templateId: number, context: Record<string, unknown>): Promise<TemplateRenderResponse> {
    const template = await this.getTemplate(templateId)
    const rendered_content = this.previewTemplate(template.content, context)
    const variables = this.extractVariables(template.content)
    const missing_variables = variables.filter((name) => context[name] == null && template.default_values[name] == null)
    return {
      rendered_content,
      template_id: templateId,
      template_name: template.name,
      variables_used: variables.filter((name) => !missing_variables.includes(name)),
      missing_variables,
    }
  }

  async recordUsage(templateId: number, usageData: TemplateUsage): Promise<void> {
    const template = await this.getTemplate(templateId)
    await this.updateTemplate(templateId, {
      usage_count: template.usage_count + 1,
      last_used_at: new Date().toISOString(),
    } as PromptTemplateUpdate)
    void usageData
  }

  async getStatistics(): Promise<TemplateStatistics> {
    const category_distribution = this.templates.reduce<Record<string, number>>((acc, template) => {
      acc[template.category] = (acc[template.category] || 0) + 1
      return acc
    }, {})

    return {
      total_templates: this.templates.length,
      public_templates: this.templates.filter((item) => item.visibility === 'PUBLIC').length,
      private_templates: this.templates.filter((item) => item.visibility === 'PRIVATE').length,
      featured_templates: this.templates.filter((item) => item.is_featured).length,
      category_distribution,
      usage_statistics: {},
      top_templates: [...this.templates].sort((left, right) => right.usage_count - left.usage_count).slice(0, 5),
      recent_templates: [...this.templates].sort((left, right) => right.updated_at.localeCompare(left.updated_at)).slice(0, 5),
    }
  }

  async getCategories(): Promise<TemplateCategory[]> {
    return [
      { value: 'test_case', label: '测试用例', description: '测试用例生成和优化' },
      { value: 'requirements', label: '需求分析', description: '需求理解、拆分和评审' },
      { value: 'defect', label: '缺陷分析', description: '缺陷定位和修复建议' },
      { value: 'report', label: '报告生成', description: '测试报告和总结' },
    ]
  }

  async getVisibilityOptions(): Promise<VisibilityOption[]> {
    return [
      { value: 'PRIVATE', label: '私有', description: '仅本人可见' },
      { value: 'TEAM', label: '团队', description: '团队成员可见' },
      { value: 'PUBLIC', label: '公开', description: '所有用户可见' },
    ]
  }

  validateTemplateSyntax(content: string): { isValid: boolean; errors: string[] } {
    const errors: string[] = []
    const openBraces = (content.match(/\{/g) || []).length
    const closeBraces = (content.match(/\}/g) || []).length
    if (openBraces !== closeBraces) errors.push('模板中的大括号不匹配')
    this.extractVariables(content).forEach((name) => {
      if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(name)) errors.push(`变量名 ${name} 格式不正确`)
    })
    return { isValid: errors.length === 0, errors }
  }

  extractVariables(content: string): string[] {
    const variables = new Set<string>()
    const pattern = /\{([a-zA-Z_][a-zA-Z0-9_]*)\}/g
    let match: RegExpExecArray | null
    while ((match = pattern.exec(content)) !== null) variables.add(match[1])
    return Array.from(variables)
  }

  previewTemplate(content: string, context: Record<string, unknown>): string {
    return this.extractVariables(content).reduce((result, key) => {
      const value = context[key] == null ? `{${key}}` : String(context[key])
      return result.replace(new RegExp(`\\{${key}\\}`, 'g'), value)
    }, content)
  }

  async createTemplateVersion(templateId: number, templateData: PromptTemplateUpdate): Promise<PromptTemplate> {
    const template = await this.getTemplate(templateId)
    return this.createTemplate({
      ...template,
      ...templateData,
      parent_template_id: templateId,
      version: this.nextVersion(template.version),
    } as PromptTemplateCreate & { parent_template_id?: number; version?: string })
  }

  async getTemplateVersions(templateId: number): Promise<PromptTemplate[]> {
    return this.templates.filter((item) => item.id === templateId || item.parent_template_id === templateId)
  }

  async getTemplateVersionByNumber(templateId: number, version: string): Promise<PromptTemplate> {
    const versions = await this.getTemplateVersions(templateId)
    const template = versions.find((item) => item.version === version)
    if (!template) throw new Error('模板版本不存在')
    return template
  }

  async getLatestTemplateVersion(templateId: number): Promise<PromptTemplate> {
    const versions = await this.getTemplateVersions(templateId)
    return versions.find((item) => item.is_latest_version) || versions[0] || this.getTemplate(templateId)
  }

  async rollbackToVersion(templateId: number, version: string): Promise<PromptTemplate> {
    const target = await this.getTemplateVersionByNumber(templateId, version)
    return this.updateTemplate(templateId, target)
  }

  async compareTemplateVersions(templateId: number, version1: string, version2: string): Promise<any> {
    const left = await this.getTemplateVersionByNumber(templateId, version1)
    const right = await this.getTemplateVersionByNumber(templateId, version2)
    return { left, right, changed: left.content !== right.content }
  }

  async deleteTemplateVersion(templateId: number, version: string): Promise<void> {
    const target = await this.getTemplateVersionByNumber(templateId, version)
    if (target.id !== templateId) await this.deleteTemplate(target.id)
  }

  async getTemplateVersionHistory(templateId: number): Promise<any> {
    const versions = await this.getTemplateVersions(templateId)
    return { versions, total: versions.length }
  }

  async setTemplateAsLatest(templateId: number, version: string): Promise<PromptTemplate> {
    const target = await this.getTemplateVersionByNumber(templateId, version)
    this.templates = this.templates.map((item) => ({
      ...item,
      is_latest_version: item.id === target.id,
    }))
    this.persist()
    return target
  }

  async testTemplate(templateId: number, testRequest: TemplateTestRequest): Promise<TemplateTestResponse> {
    const template = await this.getTemplate(templateId)
    const scenarios = testRequest.test_scenarios?.length
      ? testRequest.test_scenarios
      : [this.createTestScenario('默认场景', testRequest.context)]

    const test_results = scenarios.map((scenario, index) => {
      const prompt = this.previewTemplate(template.content, scenario.context)
      return {
        success: true,
        ai_provider: scenario.ai_provider || testRequest.ai_provider || 'openai',
        ai_model: scenario.ai_model || testRequest.ai_model || 'gpt-4',
        prompt,
        response: `模拟响应：${prompt.slice(0, 120)}`,
        response_time: 0.2,
        token_usage: Math.max(1, Math.ceil(prompt.length / 4)),
        timestamp: new Date().toISOString(),
        scenario_index: index,
        scenario_name: scenario.name,
        expected_output: scenario.expected_output,
        evaluation_criteria: scenario.evaluation_criteria,
      }
    })

    const performance_metrics = this.calculatePerformance(test_results)
    return {
      success: true,
      template_id: templateId,
      template_name: template.name,
      rendered_content: this.previewTemplate(template.content, testRequest.context),
      variables_used: this.extractVariables(template.content),
      test_results,
      success_rate: 1,
      total_tests: test_results.length,
      successful_tests: test_results.length,
      test_timestamp: new Date().toISOString(),
      performance_metrics,
    }
  }

  async batchTestTemplate(templateId: number, request: BatchTemplateTestRequest): Promise<BatchTemplateTestResponse> {
    const template = await this.getTemplate(templateId)
    const providers = request.ai_providers?.length ? request.ai_providers : ['openai']
    const models = request.ai_models?.length ? request.ai_models : ['gpt-4']
    const batch_results: BatchTestResult[] = []

    for (const ai_provider of providers) {
      for (const ai_model of models) {
        const test_results = await Promise.all(
          request.test_cases.map(async (testCase, index) => ({
            test_case_index: index,
            test_case_name: testCase.name,
            result: await this.testTemplate(templateId, {
              context: testCase.context,
              ai_provider,
              ai_model,
              test_scenarios: testCase.scenarios,
            }),
          })),
        )
        batch_results.push({
          ai_provider,
          ai_model,
          test_results,
          success_rate: 1,
          total_cases: test_results.length,
          successful_cases: test_results.length,
        })
      }
    }

    return {
      success: true,
      template_id: templateId,
      template_name: template.name,
      batch_results,
      overall_success_rate: 1,
      total_provider_model_combinations: providers.length * models.length,
      total_test_cases: request.test_cases.length,
      test_timestamp: new Date().toISOString(),
    }
  }

  async getTemplateTestHistory(templateId: number, params: { page?: number; size?: number } = {}): Promise<TemplateTestHistoryResponse> {
    const template = await this.getTemplate(templateId)
    const size = params.size || 10
    return {
      template_id: templateId,
      template_name: template.name,
      test_history: [],
      total: 0,
      page: params.page || 1,
      size,
      pages: 0,
    }
  }

  async evaluateTemplatePerformance(templateId: number, request: TemplateEvaluationRequest): Promise<TemplateEvaluationResponse> {
    const template = await this.getTemplate(templateId)
    const performance_results = await Promise.all(
      request.test_data.map(async (testData, index) => {
        const result = await this.testTemplate(templateId, testData)
        return {
          test_index: index,
          response_time: result.performance_metrics.avg_response_time,
          success: result.success,
          token_usage: result.performance_metrics.total_token_usage,
          result,
        }
      }),
    )
    return {
      success: true,
      template_id: templateId,
      template_name: template.name,
      performance_results,
      performance_metrics: this.calculatePerformance(performance_results.map((item) => ({
        success: item.success,
        response_time: item.response_time,
        token_usage: item.token_usage,
      } as TestResult))),
      evaluation_timestamp: new Date().toISOString(),
    }
  }

  createTestScenario(name: string, context: Record<string, unknown>, expectedOutput?: string): TestScenario {
    return { name, context, expected_output: expectedOutput, ai_provider: 'openai', ai_model: 'gpt-4' }
  }

  validateTestResult(result: TestResult, expectedOutput?: string): TestValidation {
    const issues: string[] = []
    if (!result.success) issues.push(result.error || '测试执行失败')
    if (result.response_time > 10) issues.push('响应时间过长')
    if (result.token_usage > 4000) issues.push('Token 使用量过高')
    if (expectedOutput && result.response && this.calculateSimilarity(result.response, expectedOutput) < 0.7) {
      issues.push('输出内容与期望不符')
    }
    return { isValid: issues.length === 0, score: Math.max(0, 1 - issues.length * 0.25), issues }
  }

  private list(params: TemplateSearchRequest): TemplateListResponse {
    const page = params.page || 1
    const size = params.size || 20
    const query = params.query?.trim().toLowerCase()
    let templates = this.templates.filter((template) => {
      const matchesQuery = !query || [template.name, template.title, template.description, template.content]
        .some((value) => value.toLowerCase().includes(query))
      const matchesCategory = !params.category || template.category === params.category
      const matchesVisibility = !params.visibility || template.visibility === params.visibility
      const matchesOwner = !params.owner_id || template.owner_id === params.owner_id
      const matchesFeatured = params.is_featured == null || template.is_featured === params.is_featured
      const matchesVerified = params.is_verified == null || template.is_verified === params.is_verified
      const matchesTags = !params.tags?.length || params.tags.every((tag) => template.tags.includes(tag))
      return matchesQuery && matchesCategory && matchesVisibility && matchesOwner && matchesFeatured && matchesVerified && matchesTags
    })

    templates = templates.sort((left, right) => {
      const field = params.sort_by || 'updated_at'
      const direction = params.sort_order === 'asc' ? 1 : -1
      return String((left as any)[field] || '').localeCompare(String((right as any)[field] || '')) * direction
    })

    const total = templates.length
    const pages = Math.ceil(total / size)
    return {
      templates: templates.slice((page - 1) * size, page * size),
      total,
      page,
      size,
      pages,
    }
  }

  private loadTemplates(): PromptTemplate[] {
    if (typeof localStorage === 'undefined') return []
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
    } catch {
      return []
    }
  }

  private persist() {
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.templates))
    }
  }

  private nextVersion(version: string): string {
    const [major = 1, minor = 0, patch = 0] = version.split('.').map(Number)
    return [major, minor, patch + 1].join('.')
  }

  private calculatePerformance(results: TestResult[]): PerformanceMetrics {
    const responseTimes = results.map((item) => item.response_time)
    const tokenUsage = results.map((item) => item.token_usage)
    const total_token_usage = tokenUsage.reduce((sum, value) => sum + value, 0)
    return {
      avg_response_time: responseTimes.reduce((sum, value) => sum + value, 0) / Math.max(responseTimes.length, 1),
      min_response_time: Math.min(...responseTimes, 0),
      max_response_time: Math.max(...responseTimes, 0),
      total_token_usage,
      avg_token_usage: total_token_usage / Math.max(tokenUsage.length, 1),
    }
  }

  private calculateSimilarity(text1: string, text2: string): number {
    const left = new Set(text1.toLowerCase().split(/\s+/))
    const right = new Set(text2.toLowerCase().split(/\s+/))
    const intersection = Array.from(left).filter((word) => right.has(word)).length
    const union = new Set([...Array.from(left), ...Array.from(right)]).size
    return union === 0 ? 1 : intersection / union
  }
}

export const promptTemplateService = new PromptTemplateService()
export default promptTemplateService
