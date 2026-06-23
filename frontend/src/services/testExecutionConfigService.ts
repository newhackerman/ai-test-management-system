import { ConfigService, type ConfigItem } from './config-service'

export type TestExecutionEnvironment = 'dev' | 'test' | 'staging' | 'prod' | 'demo' | 'perf'
export type TestRunnerType = 'local' | 'ssh' | 'agent' | 'docker' | 'kubernetes' | 'ci'
export type ResultCollectionMode = 'local' | 'ssh_download' | 'docker_volume' | 'agent_callback' | 'kubernetes_logs' | 'ci_artifact'

export interface TestExecutionConfig {
  id: string
  name: string
  environment: TestExecutionEnvironment
  framework: string
  framework_label: string
  browser: string
  parallel_count: number
  retry_count: number
  timeout: number
  headless: boolean
  runner_type: TestRunnerType
  runner_name?: string
  runner_host?: string
  runner_port?: number
  runner_user?: string
  runner_os?: string
  runner_workdir?: string
  credential_ref?: string
  agent_id?: string
  agent_callback_url?: string
  docker_image?: string
  docker_network?: string
  docker_volumes?: string
  docker_args?: string
  kubernetes_context?: string
  kubernetes_namespace?: string
  kubernetes_image?: string
  kubernetes_job_template?: string
  ci_provider?: string
  ci_pipeline_url?: string
  ci_project?: string
  ci_branch?: string
  ci_token_ref?: string
  ci_variables?: string
  tool_home?: string
  executable_path?: string
  command?: string
  command_template?: string
  pre_command?: string
  post_command?: string
  working_directory?: string
  result_collection: ResultCollectionMode
  result_directory?: string
  result_file_pattern?: string
  report_directory?: string
  result_format?: string
  artifact_patterns?: string
  jmeter_properties?: string
  distributed_hosts?: string
  environment_variables?: Record<string, string>
  description?: string
  enabled: boolean
  created_at?: string
  updated_at?: string
}

export const TEST_EXECUTION_CONFIG_KEY = 'test_execution.configs'

export const EXECUTION_ENVIRONMENTS: Array<{ value: TestExecutionEnvironment; label: string }> = [
  { value: 'dev', label: '开发环境' },
  { value: 'test', label: '测试环境' },
  { value: 'staging', label: '预发环境' },
  { value: 'prod', label: '生产环境' },
  { value: 'demo', label: '演示环境' },
  { value: 'perf', label: '性能测试环境' },
]

export const FRAMEWORK_OPTIONS = [
  { value: 'auto', label: '自动识别导入脚本' },
  { value: 'jmeter', label: 'JMeter 性能/接口脚本' },
  { value: 'playwright', label: 'Playwright UI 自动化' },
  { value: 'selenium', label: 'Selenium UI 自动化' },
  { value: 'pytest', label: 'Pytest / Python 脚本' },
  { value: 'javascript', label: 'Node.js / JavaScript 脚本' },
  { value: 'har', label: 'HAR 接口回放' },
  { value: 'custom_command', label: '自定义命令' },
]

export const BROWSER_OPTIONS = [
  { value: 'chrome', label: 'Chrome' },
  { value: 'firefox', label: 'Firefox' },
  { value: 'edge', label: 'Edge' },
]

export const RUNNER_TYPE_OPTIONS: Array<{ value: TestRunnerType; label: string; description: string }> = [
  { value: 'local', label: '本机执行', description: '由当前平台服务所在机器直接执行脚本' },
  { value: 'ssh', label: 'SSH 远程机器', description: '通过 SSH 在指定测试机执行脚本并拉取结果' },
  { value: 'agent', label: '执行 Agent', description: '由部署在测试机上的 Agent 回传结果' },
  { value: 'docker', label: 'Docker 容器', description: '在指定容器镜像中执行测试' },
  { value: 'kubernetes', label: 'Kubernetes Job', description: '在集群中创建一次性测试任务' },
  { value: 'ci', label: 'CI/CD 流水线', description: '触发 Jenkins/GitLab 等流水线并收集构建产物' },
]

export const RESULT_COLLECTION_OPTIONS: Array<{ value: ResultCollectionMode; label: string }> = [
  { value: 'local', label: '本机目录读取' },
  { value: 'ssh_download', label: 'SSH 下载结果' },
  { value: 'docker_volume', label: 'Docker 挂载目录' },
  { value: 'agent_callback', label: 'Agent 回传' },
  { value: 'kubernetes_logs', label: 'Kubernetes 日志/产物' },
  { value: 'ci_artifact', label: '流水线产物' },
]

export const RESULT_FORMAT_OPTIONS = [
  { value: 'jtl', label: 'JMeter JTL' },
  { value: 'junit', label: 'JUnit XML' },
  { value: 'playwright-report', label: 'Playwright Report' },
  { value: 'allure', label: 'Allure Report' },
  { value: 'json', label: 'JSON' },
  { value: 'text', label: '文本日志' },
]

const DEFAULT_COMMAND_TEMPLATES: Record<string, string> = {
  jmeter: 'jmeter -n -t {script} -l {result_jtl} -j {log_file} -e -o {report_dir}',
  playwright: 'npx playwright test {script}',
  selenium: 'python {script}',
  pytest: 'pytest {script} --junitxml={result_file}',
  javascript: 'node {script}',
  har: '',
  custom_command: '',
}

const createId = () => {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID()
  }
  return `exec-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

const getDefaultRunnerType = (framework: string): TestRunnerType => (framework === 'jmeter' ? 'ssh' : 'local')
const getDefaultCollectionMode = (runnerType: TestRunnerType): ResultCollectionMode => (
  runnerType === 'ssh'
    ? 'ssh_download'
    : runnerType === 'docker'
      ? 'docker_volume'
      : runnerType === 'agent'
        ? 'agent_callback'
        : runnerType === 'kubernetes'
          ? 'kubernetes_logs'
          : runnerType === 'ci'
            ? 'ci_artifact'
            : 'local'
)
const getDefaultResultFormat = (framework: string) => (
  framework === 'jmeter'
    ? 'jtl'
    : framework === 'playwright'
      ? 'playwright-report'
      : framework === 'pytest' || framework === 'selenium'
        ? 'junit'
        : framework === 'har' || framework === 'javascript'
          ? 'json'
          : 'text'
)

export const createDefaultExecutionConfigs = (environment: TestExecutionEnvironment): TestExecutionConfig[] => {
  const now = new Date().toISOString()
  const environmentLabel = EXECUTION_ENVIRONMENTS.find((item) => item.value === environment)?.label || environment
  return [
    normalizeConfig({
      id: createId(),
      name: `${environmentLabel} - 自动识别本机执行`,
      environment,
      framework: 'auto',
      framework_label: '自动识别导入脚本',
      runner_type: 'local',
      result_collection: 'local',
      description: '默认由平台服务所在机器执行导入脚本；适合 Playwright、Pytest、HAR 或本机已安装工具的脚本。',
      enabled: true,
      created_at: now,
      updated_at: now,
    }, environment),
    normalizeConfig({
      id: createId(),
      name: `${environmentLabel} - JMeter 测试机执行`,
      environment,
      framework: 'jmeter',
      framework_label: 'JMeter 性能/接口脚本',
      runner_type: 'ssh',
      runner_name: `${environmentLabel} JMeter 节点`,
      runner_port: 22,
      runner_workdir: '/opt/test-runs/jmeter',
      command_template: DEFAULT_COMMAND_TEMPLATES.jmeter,
      result_collection: 'ssh_download',
      result_format: 'jtl',
      result_file_pattern: '*.jtl',
      report_directory: 'report',
      timeout: 1800,
      description: '适合把 JMX 上传到指定 JMeter 测试机执行，再下载 JTL 和 HTML 报告。',
      enabled: false,
      created_at: now,
      updated_at: now,
    }, environment),
    normalizeConfig({
      id: createId(),
      name: `${environmentLabel} - Playwright Docker 执行`,
      environment,
      framework: 'playwright',
      framework_label: 'Playwright UI 自动化',
      runner_type: 'docker',
      runner_name: `${environmentLabel} Playwright 容器`,
      docker_image: 'mcr.microsoft.com/playwright:v1.49.1-jammy',
      command_template: DEFAULT_COMMAND_TEMPLATES.playwright,
      result_collection: 'docker_volume',
      result_format: 'playwright-report',
      artifact_patterns: 'playwright-report/**\ntest-results/**',
      report_directory: 'playwright-report',
      timeout: 1800,
      description: '适合把导入的 Playwright 脚本放入标准浏览器镜像执行，并从挂载目录采集报告。',
      enabled: false,
      created_at: now,
      updated_at: now,
    }, environment),
  ]
}

const normalizeNumber = (value: unknown, fallback: number, min: number, max: number) => {
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) return fallback
  return Math.min(max, Math.max(min, Math.round(parsed)))
}

const normalizeString = (value: unknown) => {
  const text = String(value || '').trim()
  return text || undefined
}

const normalizeEnvironmentVariables = (value: unknown) => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return undefined
  const entries = Object.entries(value).reduce<Record<string, string>>((acc, [key, val]) => {
    const normalizedKey = String(key || '').trim()
    if (normalizedKey) acc[normalizedKey] = String(val ?? '')
    return acc
  }, {})
  return Object.keys(entries).length ? entries : undefined
}

const normalizeRunnerType = (value: unknown, framework: string): TestRunnerType => {
  const normalized = String(value || '').trim() as TestRunnerType
  return RUNNER_TYPE_OPTIONS.some((item) => item.value === normalized) ? normalized : getDefaultRunnerType(framework)
}

const normalizeCollectionMode = (value: unknown, runnerType: TestRunnerType): ResultCollectionMode => {
  const normalized = String(value || '').trim() as ResultCollectionMode
  return RESULT_COLLECTION_OPTIONS.some((item) => item.value === normalized) ? normalized : getDefaultCollectionMode(runnerType)
}

export const normalizeConfig = (config: Partial<TestExecutionConfig>, environment: TestExecutionEnvironment): TestExecutionConfig => {
  const framework = String(config.framework || 'auto')
  const frameworkLabel = config.framework_label || FRAMEWORK_OPTIONS.find((item) => item.value === framework)?.label || framework
  const runnerType = normalizeRunnerType(config.runner_type, framework)
  const resultCollection = normalizeCollectionMode(config.result_collection, runnerType)
  const now = new Date().toISOString()

  return {
    id: config.id || createId(),
    name: String(config.name || frameworkLabel),
    environment,
    framework,
    framework_label: String(frameworkLabel),
    browser: String(config.browser || 'chrome'),
    parallel_count: normalizeNumber(config.parallel_count, 1, 1, 100),
    retry_count: normalizeNumber(config.retry_count, 0, 0, 20),
    timeout: normalizeNumber(config.timeout, framework === 'jmeter' ? 1800 : 900, 1, 1800),
    headless: config.headless !== false,
    runner_type: runnerType,
    runner_name: normalizeString(config.runner_name),
    runner_host: normalizeString(config.runner_host),
    runner_port: normalizeNumber(config.runner_port, runnerType === 'ssh' ? 22 : 0, 0, 65535) || undefined,
    runner_user: normalizeString(config.runner_user),
    runner_os: normalizeString(config.runner_os),
    runner_workdir: normalizeString(config.runner_workdir),
    credential_ref: normalizeString(config.credential_ref),
    agent_id: normalizeString(config.agent_id),
    agent_callback_url: normalizeString(config.agent_callback_url),
    docker_image: normalizeString(config.docker_image),
    docker_network: normalizeString(config.docker_network),
    docker_volumes: normalizeString(config.docker_volumes),
    docker_args: normalizeString(config.docker_args),
    kubernetes_context: normalizeString(config.kubernetes_context),
    kubernetes_namespace: normalizeString(config.kubernetes_namespace),
    kubernetes_image: normalizeString(config.kubernetes_image),
    kubernetes_job_template: normalizeString(config.kubernetes_job_template),
    ci_provider: normalizeString(config.ci_provider),
    ci_pipeline_url: normalizeString(config.ci_pipeline_url),
    ci_project: normalizeString(config.ci_project),
    ci_branch: normalizeString(config.ci_branch),
    ci_token_ref: normalizeString(config.ci_token_ref),
    ci_variables: normalizeString(config.ci_variables),
    tool_home: normalizeString(config.tool_home),
    executable_path: normalizeString(config.executable_path),
    command: normalizeString(config.command),
    command_template: normalizeString(config.command_template) || DEFAULT_COMMAND_TEMPLATES[framework],
    pre_command: normalizeString(config.pre_command),
    post_command: normalizeString(config.post_command),
    working_directory: normalizeString(config.working_directory),
    result_collection: resultCollection,
    result_directory: normalizeString(config.result_directory),
    result_file_pattern: normalizeString(config.result_file_pattern) || (framework === 'jmeter' ? '*.jtl' : undefined),
    report_directory: normalizeString(config.report_directory) || (framework === 'jmeter' ? 'report' : undefined),
    result_format: normalizeString(config.result_format) || getDefaultResultFormat(framework),
    artifact_patterns: normalizeString(config.artifact_patterns),
    jmeter_properties: normalizeString(config.jmeter_properties),
    distributed_hosts: normalizeString(config.distributed_hosts),
    environment_variables: normalizeEnvironmentVariables(config.environment_variables),
    description: normalizeString(config.description),
    enabled: config.enabled !== false,
    created_at: config.created_at || now,
    updated_at: now,
  }
}

const parseConfigValue = (item: ConfigItem | undefined, environment: TestExecutionEnvironment): TestExecutionConfig[] => {
  if (!item?.config_value) return []

  try {
    const raw = JSON.parse(item.config_value)
    const list = Array.isArray(raw) ? raw : []
    return list.map((entry) => normalizeConfig(entry, environment))
  } catch {
    return []
  }
}

const findStorageConfig = async (environment: TestExecutionEnvironment) => {
  const response = await ConfigService.getConfigs({
    environment,
    search: TEST_EXECUTION_CONFIG_KEY,
    page: 1,
    size: 100,
  })
  return response.items.find((item) => item.config_key === TEST_EXECUTION_CONFIG_KEY)
}

export class TestExecutionConfigService {
  static async list(environment: TestExecutionEnvironment): Promise<TestExecutionConfig[]> {
    const item = await findStorageConfig(environment)
    return parseConfigValue(item, environment)
  }

  static async listAll(): Promise<TestExecutionConfig[]> {
    const results = await Promise.all(
      EXECUTION_ENVIRONMENTS.map(async ({ value }) => {
        try {
          return await this.list(value)
        } catch {
          return []
        }
      }),
    )
    return results.flat()
  }

  static async saveList(environment: TestExecutionEnvironment, configs: TestExecutionConfig[]): Promise<TestExecutionConfig[]> {
    const normalized = configs.map((config) => normalizeConfig(config, environment))
    const storageConfig = await findStorageConfig(environment)
    const payload = JSON.stringify(normalized, null, 2)
    const description = '测试执行配置：维护执行节点、工具路径、命令模板、并发重试、结果目录和产物采集方式。'

    if (storageConfig) {
      await ConfigService.updateConfig(TEST_EXECUTION_CONFIG_KEY, {
        config_value: payload,
        config_type: 'JSON',
        description,
        tags: ['test-execution', 'automation', 'runner'],
      }, environment)
    } else {
      await ConfigService.createConfig({
        config_key: TEST_EXECUTION_CONFIG_KEY,
        config_value: payload,
        config_type: 'JSON',
        environment,
        description,
        is_core: false,
        is_enabled: true,
        is_encrypted: false,
        is_required: false,
        tags: ['test-execution', 'automation', 'runner'],
        sort_order: 0,
      })
    }

    return normalized
  }

  static async upsert(environment: TestExecutionEnvironment, config: Partial<TestExecutionConfig>): Promise<TestExecutionConfig[]> {
    const list = await this.list(environment)
    const normalized = normalizeConfig(config, environment)
    const exists = list.some((item) => item.id === normalized.id)
    const nextList = exists
      ? list.map((item) => (item.id === normalized.id ? normalized : item))
      : [normalized, ...list]

    return this.saveList(environment, nextList)
  }

  static async remove(environment: TestExecutionEnvironment, id: string): Promise<TestExecutionConfig[]> {
    const list = await this.list(environment)
    return this.saveList(environment, list.filter((item) => item.id !== id))
  }

  static async initializeDefaults(environment: TestExecutionEnvironment): Promise<TestExecutionConfig[]> {
    const existing = await this.list(environment)
    if (existing.length) return existing
    return this.saveList(environment, createDefaultExecutionConfigs(environment))
  }
}
