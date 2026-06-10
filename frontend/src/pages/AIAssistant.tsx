// @ts-nocheck
import React, { useEffect, useMemo, useRef, useState } from 'react'
import {
  AlertCircle,
  BarChart3,
  Bot,
  CheckCircle2,
  ChevronDown,
  ClipboardList,
  Clipboard,
  Copy,
  Download,
  FileText,
  FileImage,
  FileSpreadsheet,
  Loader2,
  MessageSquare,
  Paperclip,
  Plus,
  RefreshCw,
  RotateCcw,
  Search,
  Send,
  Settings2,
  Sparkles,
  Square,
  Trash2,
  UploadCloud,
  User,
  X,
} from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useNavigate } from 'react-router-dom'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import ConfirmDialog from '@/components/ui/ConfirmDialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/DropdownMenu'
import { Input } from '@/components/ui/Input'
import { Textarea } from '@/components/ui/Textarea'
import { apiClient } from '@/services/api/client'

type ChatRole = 'user' | 'assistant'

interface ChatMessage {
  id: string
  role: ChatRole
  content: string
  createdAt: string
  isError?: boolean
  provider?: string
  model?: string
  tokensUsed?: number
  elapsedMs?: number
  sourcePrompt?: string
}

interface ChatSession {
  id: string
  title: string
  messages: ChatMessage[]
  createdAt: string
  updatedAt: string
}

interface AIStatus {
  configured: boolean
  provider: string
  model: string
  endpoint: string
  simulated: boolean
  message: string
}

interface AttachedFile {
  id: string
  filename: string
  mimeType: string
  fileSize: number
  fileKind: string
  extractedText: string
  imageDataUrl?: string
  summary: string
  warnings: string[]
}

const STORAGE_KEY = 'ai-assistant:sessions:v2'
const AI_IMPORT_DRAFT_KEY = 'ai-assistant:import-draft'

const promptTemplates = [
  {
    title: '登录功能测试点',
    description: '边界值、异常路径、安全检查',
    prompt:
      '请为登录功能生成测试点，必须覆盖正常登录、密码错误、账号锁定、验证码、边界值、安全风险和异常路径，并按优先级输出。',
  },
  {
    title: '需求评审清单',
    description: '完整性、可测性、歧义识别',
    prompt:
      '请帮我生成一份需求评审清单，重点检查完整性、一致性、可测性、验收标准、依赖关系和风险项。',
  },
  {
    title: '缺陷根因分析',
    description: '复现、影响面、修复验证',
    prompt:
      '请按照缺陷根因分析模板输出：现象、复现条件、可能原因、影响范围、定位步骤、修复建议、回归验证范围。',
  },
  {
    title: '接口测试设计',
    description: '参数、鉴权、幂等、异常',
    prompt:
      '请为一个 REST API 设计接口测试清单，覆盖参数校验、鉴权、幂等、分页、并发、超时、错误码和数据一致性。',
  },
]

const outputModes = [
  { value: 'structured', label: '结构化清单' },
  { value: 'cases', label: '测试用例表' },
  { value: 'analysis', label: '分析报告' },
]

const businessContextTemplates = [
  {
    label: '需求分析',
    mode: 'analysis',
    description: '澄清范围、验收标准、风险和可测性',
    context:
      '业务场景：需求分析。\n请重点识别需求目标、用户角色、业务规则、边界条件、验收标准、依赖关系、歧义点、遗漏项和测试关注点。输出应便于后续导入到需求管理。',
  },
  {
    label: '用例编写',
    mode: 'cases',
    description: '生成可落库的测试用例结构',
    context:
      '业务场景：测试用例编写。\n请按平台测试用例字段组织输出，包含关联需求ID/编号/标题、用例标题、模块、优先级、前置条件、测试步骤、每步预期结果和测试数据。步骤必须拆分清楚，避免只生成一个大步骤。',
  },
  {
    label: '测试计划编写',
    mode: 'structured',
    description: '生成可保存的测试计划草稿',
    context:
      '业务场景：测试计划编写。\n请按平台测试计划字段组织输出，包含计划名称、测试类型、计划描述、测试范围、测试策略、进入/退出准则、资源安排、风险与应对、时间安排和交付物。测试类型必须从功能测试、性能测试、安全测试、集成测试、回归测试、验收测试中选择，输出内容应便于导入到新增测试计划。',
  },
  {
    label: '报告分析',
    mode: 'analysis',
    description: '质量结论、问题趋势和改进建议',
    context:
      '业务场景：测试报告分析。\n请从执行结果、缺陷分布、风险趋势、阻塞项、质量结论和改进建议进行分析，输出可用于系统报告的摘要、关键指标、问题清单和行动项。',
  },
  {
    label: '缺陷分析',
    mode: 'structured',
    description: '根因、影响面、复现和回归范围',
    context:
      '业务场景：缺陷分析。\n请输出缺陷现象、复现路径、可能根因、影响范围、修复建议、验证重点和回归测试范围，注意区分必现、偶现和环境相关因素。',
  },
  {
    label: '风险评估',
    mode: 'structured',
    description: '概率、影响、等级和应对措施',
    context:
      '业务场景：项目风险评估。\n请识别需求、进度、质量、人员、环境、数据、安全和外部依赖风险，并给出风险等级、触发条件、应对措施、责任人建议和跟踪频率。',
  },
  {
    label: '性能/安全',
    mode: 'structured',
    description: '性能瓶颈、安全威胁和专项测试点',
    context:
      '业务场景：性能与安全专项分析。\n请关注容量、并发、响应时间、稳定性、权限控制、敏感数据、输入校验、审计日志和异常处理，输出专项测试建议。',
  },
]

const createId = () =>
  typeof crypto !== 'undefined' && crypto.randomUUID
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`

const createSession = (): ChatSession => {
  const now = new Date().toISOString()
  return {
    id: createId(),
    title: '新的 AI 对话',
    messages: [],
    createdAt: now,
    updatedAt: now,
  }
}

const formatTime = (value: string) =>
  new Date(value).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })

const sanitizeFilename = (value: string) =>
  (value || 'ai-conversation').replace(/[\\/:*?"<>|]/g, '_').slice(0, 80)

const formatFileSize = (value: number) => {
  if (!Number.isFinite(value) || value <= 0) return '0 B'
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
  return `${(value / 1024 / 1024).toFixed(1)} MB`
}

const getAttachmentIcon = (fileKind: string) => {
  if (fileKind === 'image') return FileImage
  if (['excel', 'spreadsheet'].includes(fileKind)) return FileSpreadsheet
  return FileText
}

const buildAttachmentRequestText = (files: AttachedFile[]) => {
  if (!files.length) return ''

  return files
    .map((file, index) => {
      const warnings = file.warnings?.length ? `\n解析提示：${file.warnings.join('；')}` : ''
      const content = file.extractedText
        ? `\n提取内容：\n${file.extractedText}`
        : file.imageDataUrl
          ? '\n提取内容：图片内容已作为视觉附件发送给支持多模态的 AI 模型。'
        : '\n提取内容：未提取到可直接读取的正文，请结合文件信息和用户补充说明进行分析。'

      return `附件 ${index + 1}：${file.filename}
类型：${file.fileKind || file.mimeType || 'unknown'}
大小：${formatFileSize(file.fileSize)}
摘要：${file.summary || '-'}${warnings}${content}`
    })
    .join('\n\n')
}

const buildDisplayUserMessage = (prompt: string, files: AttachedFile[]) => {
  if (!files.length) return prompt
  const attachmentLines = files.map(
    (file) => `- ${file.filename}（${file.fileKind || file.mimeType || '附件'}，${formatFileSize(file.fileSize)}）`,
  )
  return `${prompt}\n\n附件：\n${attachmentLines.join('\n')}`
}

const trimPromptForAiLimit = (value: string, limit = 9500) => {
  if (value.length <= limit) return value
  return `${value.slice(0, limit).trim()}\n\n[本次附件上下文较长，已按接口限制截断]`
}

const isContinuationPrompt = (value: string) => {
  const text = value.trim().replace(/\s+/g, '')
  if (!text) return false
  return (
    /^(请)?(继续|接着说|接着写|往下写|继续写|继续上文|继续上面|继续上一轮|继续上一条|继续刚才)(一下|吧|。|！|!|，|,)?$/i.test(text) ||
    /^(goon|continue|pleasecontinue)\.?$/i.test(text)
  )
}

const buildConversationContext = (messages: ChatMessage[], currentPrompt: string) => {
  const maxMessages = 10
  const maxChars = 12000
  const recentMessages = messages
    .filter((message) => !message.isError && message.content.trim())
    .slice(-maxMessages)
    .map((message) => ({
      role: message.role,
      content: message.content.trim(),
      timestamp: message.createdAt,
    }))

  let usedChars = 0
  const conversationHistory = recentMessages
    .reverse()
    .filter((message) => {
      const length = message.content.length
      if (usedChars + length > maxChars && usedChars > 0) return false
      usedChars += length
      return true
    })
    .reverse()

  const latestAssistant = [...messages]
    .reverse()
    .find((message) => message.role === 'assistant' && !message.isError && message.content.trim())
  const continuation = isContinuationPrompt(currentPrompt)

  return {
    conversation_history: conversationHistory,
    is_continuation_request: continuation,
    latest_assistant_message: continuation ? latestAssistant?.content?.trim() : undefined,
    continuation_instruction: continuation
      ? '用户要求继续上一轮未完成内容。请严格承接最近一条 AI 回复的主题、结构、编号和上下文，从中断处继续，不要重新开始、不要换主题。'
      : undefined,
  }
}

const extractTitleFromContent = (content: string, fallback: string) => {
  const heading = content
    .split('\n')
    .map((line) => line.trim())
    .find((line) => line && !line.startsWith('|') && !/^[-*_]{3,}$/.test(line))

  return (heading || fallback || 'AI 导入草稿')
    .replace(/^#{1,6}\s*/, '')
    .replace(/^[\d一二三四五六七八九十]+[.、)]\s*/, '')
    .slice(0, 80)
}

const getErrorText = (error: any) => {
  const detail = error?.response?.data?.detail ?? error?.response?.data?.message ?? error?.message
  if (Array.isArray(detail)) return detail.map((item) => item?.msg || JSON.stringify(item)).join('；')
  if (detail && typeof detail === 'object') return detail.msg || JSON.stringify(detail)
  return detail || 'AI 服务调用失败，请检查模型配置或后端服务日志。'
}

const AssistantMarkdown = ({ content }: { content: string }) => (
  <div className="text-sm leading-6 text-gray-900 dark:text-slate-100">
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
        ul: ({ children }) => <ul className="mb-3 list-disc space-y-1 pl-5">{children}</ul>,
        ol: ({ children }) => <ol className="mb-3 list-decimal space-y-1 pl-5">{children}</ol>,
        li: ({ children }) => <li className="break-words">{children}</li>,
        strong: ({ children }) => <strong className="font-semibold text-gray-950 dark:text-white">{children}</strong>,
        code: ({ children }) => (
          <code className="rounded bg-gray-100 px-1.5 py-0.5 font-mono text-[12px] text-gray-900 dark:bg-slate-800 dark:text-slate-100">{children}</code>
        ),
        pre: ({ children }) => (
          <pre className="mb-3 overflow-x-auto rounded-md bg-gray-950 p-3 text-xs text-gray-50">{children}</pre>
        ),
        table: ({ children }) => (
          <div className="mb-3 overflow-x-auto rounded-md border border-gray-200 dark:border-slate-700">
            <table className="min-w-full border-collapse text-xs">{children}</table>
          </div>
        ),
        th: ({ children }) => <th className="border-b border-r bg-gray-50 px-3 py-2 text-left font-semibold dark:border-slate-700 dark:bg-slate-800">{children}</th>,
        td: ({ children }) => <td className="border-b border-r px-3 py-2 align-top dark:border-slate-700">{children}</td>,
      }}
    >
      {content}
    </ReactMarkdown>
  </div>
)

const AIAssistant: React.FC = () => {
  const navigate = useNavigate()
  const [sessions, setSessions] = useState<ChatSession[]>(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
      return Array.isArray(saved) && saved.length ? saved : [createSession()]
    } catch {
      return [createSession()]
    }
  })
  const [activeSessionId, setActiveSessionId] = useState(() => sessions[0]?.id)
  const [input, setInput] = useState('')
  const [search, setSearch] = useState('')
  const [outputMode, setOutputMode] = useState('structured')
  const [businessContext, setBusinessContext] = useState('')
  const [attachedFiles, setAttachedFiles] = useState<AttachedFile[]>([])
  const [attachmentLoading, setAttachmentLoading] = useState(false)
  const [loading, setLoading] = useState(false)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [statusLoading, setStatusLoading] = useState(false)
  const [statusInfo, setStatusInfo] = useState<AIStatus | null>(null)
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null)
  const [pendingDeleteSession, setPendingDeleteSession] = useState<ChatSession | null>(null)
  const [pendingDeleteMessageId, setPendingDeleteMessageId] = useState<string | null>(null)
  const [isWideLayout, setIsWideLayout] = useState(() =>
    typeof window !== 'undefined' ? window.innerWidth >= 1280 : true,
  )
  const messageEndRef = useRef<HTMLDivElement | null>(null)
  const attachmentInputRef = useRef<HTMLInputElement | null>(null)
  const requestControllerRef = useRef<AbortController | null>(null)

  const activeSession = sessions.find((session) => session.id === activeSessionId) || sessions[0]

  const filteredSessions = useMemo(() => {
    const keyword = search.trim().toLowerCase()
    if (!keyword) return sessions
    return sessions.filter((session) => {
      const content = `${session.title} ${session.messages.map((message) => message.content).join(' ')}`
      return content.toLowerCase().includes(keyword)
    })
  }, [search, sessions])

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions))
  }, [sessions])

  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [activeSession?.messages.length, loading])

  useEffect(() => {
    const handleResize = () => setIsWideLayout(window.innerWidth >= 1280)
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  useEffect(() => {
    if (!loading) {
      setElapsedSeconds(0)
      return
    }

    const startedAt = Date.now()
    const timer = window.setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - startedAt) / 1000))
    }, 1000)
    return () => window.clearInterval(timer)
  }, [loading])

  const updateActiveSession = (updater: (session: ChatSession) => ChatSession) => {
    setSessions((current) =>
      current.map((session) => (session.id === activeSession.id ? updater(session) : session)),
    )
  }

  const loadStatus = async () => {
    setStatusLoading(true)
    try {
      const response = await apiClient.get('/ai-assistant/status')
      const data = response.data?.data || response.data
      setStatusInfo(data)
    } catch (error) {
      setStatusInfo({
        configured: false,
        provider: 'unknown',
        model: '',
        endpoint: '',
        simulated: false,
        message: getErrorText(error),
      })
    } finally {
      setStatusLoading(false)
    }
  }

  useEffect(() => {
    loadStatus()
  }, [])

  const createNewSession = () => {
    const session = createSession()
    setSessions((current) => [session, ...current])
    setActiveSessionId(session.id)
    setInput('')
    setAttachedFiles([])
  }

  const deleteSession = (sessionId: string) => {
    setSessions((current) => {
      const next = current.filter((session) => session.id !== sessionId)
      if (!next.length) {
        const session = createSession()
        setActiveSessionId(session.id)
        return [session]
      }
      if (activeSessionId === sessionId) setActiveSessionId(next[0].id)
      return next
    })
  }

  const confirmDeleteSession = () => {
    if (!pendingDeleteSession) return
    deleteSession(pendingDeleteSession.id)
    setPendingDeleteSession(null)
  }

  const getMessageRound = (messages: ChatMessage[], messageId: string) => {
    const index = messages.findIndex((message) => message.id === messageId)
    if (index < 0) return []

    let start = index
    while (start > 0 && messages[start].role !== 'user') start -= 1

    let end = start + 1
    while (end < messages.length && messages[end].role !== 'user') end += 1

    return messages.slice(start, end)
  }

  const pendingDeleteMessages = useMemo(
    () => (activeSession && pendingDeleteMessageId
      ? getMessageRound(activeSession.messages, pendingDeleteMessageId)
      : []),
    [activeSession, pendingDeleteMessageId],
  )

  const requestDeleteMessageRound = (message: ChatMessage) => {
    setPendingDeleteMessageId(message.id)
  }

  const confirmDeleteMessageRound = () => {
    if (!activeSession || !pendingDeleteMessageId) return
    const deleteIds = new Set(getMessageRound(activeSession.messages, pendingDeleteMessageId).map((message) => message.id))
    updateActiveSession((session) => ({
      ...session,
      messages: session.messages.filter((message) => !deleteIds.has(message.id)),
      updatedAt: new Date().toISOString(),
    }))
    setPendingDeleteMessageId(null)
  }

  const renameSessionFromPrompt = (prompt: string) => {
    if (!activeSession || activeSession.title !== '新的 AI 对话') return
    const title = prompt.replace(/\s+/g, ' ').slice(0, 24)
    updateActiveSession((session) => ({ ...session, title, updatedAt: new Date().toISOString() }))
  }

  const applyBusinessContextTemplate = (template: (typeof businessContextTemplates)[number]) => {
    setBusinessContext(template.context)
    setOutputMode(template.mode)
  }

  const uploadAttachments = async (fileList: FileList | null) => {
    const files = Array.from(fileList || [])
    if (!files.length) return

    setAttachmentLoading(true)
    try {
      const formData = new FormData()
      files.forEach((file) => formData.append('files', file))
      const response = await apiClient.post('/ai-assistant/attachments/extract', formData, {
        timeout: 120000,
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      const items = response.data?.attachments || response.data?.data?.attachments || []
      const nextFiles = items.map((item: any): AttachedFile => ({
        id: createId(),
        filename: item.filename || '未命名附件',
        mimeType: item.mime_type || item.mimeType || '',
        fileSize: Number(item.file_size ?? item.fileSize ?? 0),
        fileKind: item.file_kind || item.fileKind || 'unknown',
        extractedText: item.extracted_text || item.extractedText || '',
        imageDataUrl: item.image_data_url || item.imageDataUrl || undefined,
        summary: item.summary || '',
        warnings: Array.isArray(item.warnings) ? item.warnings : [],
      }))
      setAttachedFiles((current) => [...current, ...nextFiles].slice(-8))
    } catch (error) {
      const now = new Date().toISOString()
      const message = getErrorText(error)
      updateActiveSession((session) => ({
        ...session,
        messages: [
          ...session.messages,
          {
            id: createId(),
            role: 'assistant',
            content: `附件解析失败：${message}`,
            createdAt: now,
            isError: true,
          },
        ],
        updatedAt: now,
      }))
    } finally {
      setAttachmentLoading(false)
      if (attachmentInputRef.current) attachmentInputRef.current.value = ''
    }
  }

  const removeAttachment = (fileId: string) => {
    setAttachedFiles((current) => current.filter((file) => file.id !== fileId))
  }

  const sendMessage = async (overridePrompt?: string) => {
    const prompt = (overridePrompt || input).trim() || (attachedFiles.length ? '请分析我上传的附件内容，并给出与测试管理相关的结论和建议。' : '')
    if (!prompt || loading || attachmentLoading || !activeSession) return
    const filesForMessage = overridePrompt ? [] : attachedFiles
    const attachmentText = buildAttachmentRequestText(filesForMessage)
    const requestContent = trimPromptForAiLimit(
      attachmentText ? `${prompt}\n\n【用户上传附件上下文】\n${attachmentText}` : prompt,
    )
    const displayContent = buildDisplayUserMessage(prompt, filesForMessage)
    const conversationContext = buildConversationContext(activeSession.messages, prompt)

    const now = new Date().toISOString()
    const userMessage: ChatMessage = {
      id: createId(),
      role: 'user',
      content: displayContent,
      createdAt: now,
    }

    setInput('')
    if (!overridePrompt) setAttachedFiles([])
    renameSessionFromPrompt(prompt)
    updateActiveSession((session) => ({
      ...session,
      messages: [...session.messages, userMessage],
      updatedAt: now,
    }))
    setLoading(true)
    const controller = new AbortController()
    requestControllerRef.current = controller

    const startedAt = performance.now()
    try {
      const response = await apiClient.post(
        '/ai-assistant/query',
        {
          content: requestContent,
          context: {
            output_mode: outputModes.find((item) => item.value === outputMode)?.label,
            business_context: businessContext.trim() || undefined,
            ...conversationContext,
            attachments: filesForMessage.map((file) => ({
              filename: file.filename,
              file_kind: file.fileKind,
              file_size: file.fileSize,
              summary: file.summary,
              warnings: file.warnings,
              extracted_chars: file.extractedText.length,
              image_data_url: file.imageDataUrl,
            })),
            ui_source: 'ai_assistant_workspace',
          },
        },
        { timeout: 120000, signal: controller.signal },
      )
      const data = response.data?.data || response.data || {}
      const answer = String(data.content || '').trim()
      if (!answer) throw new Error('后端未返回可展示的 AI 内容。')

      const assistantMessage: ChatMessage = {
        id: createId(),
        role: 'assistant',
        content: answer,
        createdAt: new Date().toISOString(),
        provider: data.provider,
        model: data.model,
        tokensUsed: data.tokens_used,
        elapsedMs: Math.round(performance.now() - startedAt),
        sourcePrompt: requestContent,
      }

      updateActiveSession((session) => ({
        ...session,
        messages: [...session.messages, assistantMessage],
        updatedAt: assistantMessage.createdAt,
      }))
      if (data.metadata?.simulated === true) {
        setStatusInfo((current) => ({ ...(current || {}), simulated: true }))
      }
    } catch (error) {
      const isCanceled = error?.code === 'ERR_CANCELED' || error?.name === 'CanceledError'
      const errorMessage: ChatMessage = {
        id: createId(),
        role: 'assistant',
        content: isCanceled ? '已停止本次 AI 请求。' : getErrorText(error),
        createdAt: new Date().toISOString(),
        isError: true,
        elapsedMs: Math.round(performance.now() - startedAt),
        sourcePrompt: requestContent,
      }
      updateActiveSession((session) => ({
        ...session,
        messages: [...session.messages, errorMessage],
        updatedAt: errorMessage.createdAt,
      }))
    } finally {
      requestControllerRef.current = null
      setLoading(false)
    }
  }

  const stopGeneration = () => {
    requestControllerRef.current?.abort()
  }

  const retryMessage = (message: ChatMessage) => {
    if (message.sourcePrompt) sendMessage(message.sourcePrompt)
  }

  const copyMessage = async (message: ChatMessage) => {
    await navigator.clipboard.writeText(message.content)
    setCopiedMessageId(message.id)
    setTimeout(() => setCopiedMessageId(null), 1500)
  }

  const buildConversationMarkdown = () => {
    if (!activeSession) return
    const markdown = activeSession.messages
      .map((message) => {
        const role = message.role === 'user' ? '用户' : 'AI 助手'
        return `## ${role} - ${formatTime(message.createdAt)}\n\n${message.content}`
      })
      .join('\n\n')

    return `# ${activeSession.title}\n\n${markdown}`
  }

  const getLatestAssistantMessage = () =>
    activeSession?.messages
      .slice()
      .reverse()
      .find((message) => message.role === 'assistant' && !message.isError)

  const buildAiImportDraft = (destination: string) => {
    if (!activeSession) return null
    const latestAssistantMessage = getLatestAssistantMessage()
    const content = latestAssistantMessage?.content || buildConversationMarkdown() || ''
    const title = extractTitleFromContent(content, activeSession.title)

    return {
      source: 'ai-assistant',
      destination,
      title,
      sessionTitle: activeSession.title,
      content,
      messages: activeSession.messages,
      createdAt: new Date().toISOString(),
    }
  }

  const exportConversation = () => {
    if (!activeSession) return
    const blob = new Blob([buildConversationMarkdown() || ''], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${sanitizeFilename(activeSession.title)}.md`
    link.click()
    URL.revokeObjectURL(url)
  }

  const importToBusinessObject = (destination: string, path: string) => {
    const draft = buildAiImportDraft(destination)
    if (!draft) return
    sessionStorage.setItem(AI_IMPORT_DRAFT_KEY, JSON.stringify(draft))
    navigate(path, { state: { aiImport: draft } })
  }

  const clearActiveMessages = () => {
    updateActiveSession((session) => ({
      ...session,
      messages: [],
      updatedAt: new Date().toISOString(),
    }))
  }

  return (
    <div className="flex h-[calc(100vh-112px)] min-h-[680px] flex-col gap-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-semibold text-gray-950">
            <Bot className="h-7 w-7 text-blue-600" />
            AI 助手
          </h1>
          <p className="mt-1 text-sm text-gray-600">真实连接模型，辅助需求分析、测试设计、缺陷定位和项目风险判断。</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {statusInfo && !statusInfo.configured && (
            <Badge variant="destructive" className="rounded-md">服务未就绪</Badge>
          )}
          {statusInfo?.simulated && <Badge variant="destructive" className="rounded-md">发现模拟响应</Badge>}
          <Button variant="outline" size="sm" onClick={loadStatus} disabled={statusLoading}>
            {statusLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
            刷新状态
          </Button>
        </div>
      </div>

      <div
        className="grid min-h-0 flex-1 grid-cols-1 gap-4"
        style={isWideLayout ? { gridTemplateColumns: '280px minmax(0, 1fr) 320px' } : undefined}
      >
        <Card className="flex min-h-0 flex-col overflow-hidden rounded-md">
          <CardHeader className="border-b p-4">
            <div className="flex items-center justify-between gap-2">
              <CardTitle className="text-base">对话</CardTitle>
              <Button size="sm" onClick={createNewSession}>
                <Plus className="mr-2 h-4 w-4" />
                新建
              </Button>
            </div>
            <div className="relative mt-3">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <Input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="搜索对话"
                className="pl-9"
              />
            </div>
          </CardHeader>
          <CardContent className="min-h-0 flex-1 overflow-y-auto p-2">
            {filteredSessions.map((session) => (
              <div
                key={session.id}
                className={`group mb-1 flex w-full items-start gap-2 rounded-md px-3 py-2 transition ${
                  session.id === activeSession?.id
                    ? 'bg-sky-50 text-sky-900 dark:bg-slate-800 dark:text-slate-100'
                    : 'hover:bg-gray-50 dark:text-slate-300 dark:hover:bg-slate-800/70'
                }`}
              >
                <button
                  type="button"
                  onClick={() => setActiveSessionId(session.id)}
                  className="min-w-0 flex-1 text-left"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate text-sm font-medium">{session.title}</span>
                    <span className="text-xs text-gray-500 dark:text-slate-400">{session.messages.length}</span>
                  </div>
                  <div className="mt-1 truncate text-xs text-gray-500 dark:text-slate-400">{formatTime(session.updatedAt)}</div>
                </button>
                <button
                  type="button"
                  title="删除对话"
                  aria-label={`删除对话：${session.title}`}
                  onClick={(event) => {
                    event.stopPropagation()
                    setPendingDeleteSession(session)
                  }}
                  className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-gray-400 opacity-0 transition hover:bg-red-50 hover:text-red-600 focus:opacity-100 group-hover:opacity-100 dark:text-slate-500 dark:hover:bg-red-950/40 dark:hover:text-red-300"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="flex min-h-0 flex-col overflow-hidden rounded-md">
          <CardHeader className="border-b p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <CardTitle className="flex items-center gap-2 text-base">
                  <MessageSquare className="h-5 w-5 text-emerald-600" />
                  {activeSession?.title || 'AI 对话'}
                </CardTitle>
                <p className="mt-1 text-xs text-gray-500 dark:text-slate-400">
                  支持多轮上下文、附件解析和业务导出
                </p>
              </div>
              <div className="flex items-center gap-2">
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm" disabled={!activeSession?.messages.length}>
                      <Download className="mr-2 h-4 w-4" />
                      导出
                      <ChevronDown className="ml-1 h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-56">
                    <DropdownMenuLabel>导出到业务功能</DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={() => importToBusinessObject('test-case', '/test-manager/test-cases/create')}>
                      <ClipboardList className="mr-2 h-4 w-4" />
                      导入到新建测试用例
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => importToBusinessObject('test-plan', '/test-manager/test-plans/create')}>
                      <ClipboardList className="mr-2 h-4 w-4" />
                      导入到新建测试计划
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => importToBusinessObject('requirement', '/requirements')}>
                      <FileText className="mr-2 h-4 w-4" />
                      导入到新建需求
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => importToBusinessObject('report', '/test-manager/reports/generate')}>
                      <BarChart3 className="mr-2 h-4 w-4" />
                      生成系统报告
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={exportConversation}>
                      <Download className="mr-2 h-4 w-4" />
                      下载 Markdown
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
                <Button variant="outline" size="sm" onClick={clearActiveMessages} disabled={!activeSession?.messages.length}>
                  <Trash2 className="mr-2 h-4 w-4" />
                  清空
                </Button>
              </div>
            </div>
          </CardHeader>

          <CardContent className="flex min-h-0 flex-1 flex-col p-0">
            <div className="min-h-0 flex-1 overflow-y-auto bg-gray-50 p-4 dark:bg-slate-950">
              {!activeSession?.messages.length && (
                <div className="flex h-full items-center justify-center">
                  <div className="max-w-lg text-center">
                    <Sparkles className="mx-auto h-10 w-10 text-amber-500" />
                    <h2 className="mt-3 text-lg font-semibold text-gray-900 dark:text-slate-100">选择模板或直接输入问题</h2>
                    <p className="mt-2 text-sm text-gray-600 dark:text-slate-400">
                      这里不会展示模拟回复；发送后将通过后端调用已配置的真实 OpenAI 兼容模型。
                    </p>
                  </div>
                </div>
              )}

              <div className="space-y-4">
                {activeSession?.messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    {message.role === 'assistant' && (
                      <div className={`mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-md ${
                        message.isError
                          ? 'bg-red-100 text-red-700 dark:bg-red-950/60 dark:text-red-300'
                          : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300'
                      }`}>
                        {message.isError ? <AlertCircle className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
                      </div>
                    )}
                    <div
                      className={`max-w-[86%] rounded-md border px-4 py-3 shadow-sm ${
                        message.role === 'user'
                          ? 'border-blue-200 bg-blue-50 text-slate-900 dark:border-blue-500/30 dark:bg-blue-950/30 dark:text-slate-100'
                          : message.isError
                            ? 'border-red-200 bg-red-50 text-red-900 dark:border-red-900/60 dark:bg-red-950/30 dark:text-red-100'
                            : 'border-gray-200 bg-white text-gray-900 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100'
                      }`}
                    >
                      {message.role === 'assistant' && !message.isError ? (
                        <AssistantMarkdown content={message.content} />
                      ) : (
                        <div className="whitespace-pre-wrap break-words text-sm leading-6">{message.content}</div>
                      )}
                      <div className={`mt-3 flex flex-wrap items-center gap-2 text-xs ${
                        message.role === 'user' ? 'text-slate-500 dark:text-slate-400' : 'text-gray-500 dark:text-slate-400'
                      }`}>
                        <span>{formatTime(message.createdAt)}</span>
                        {message.model && <span>{message.provider}/{message.model}</span>}
                        {message.tokensUsed ? <span>{message.tokensUsed} tokens</span> : null}
                        {message.elapsedMs ? <span>{(message.elapsedMs / 1000).toFixed(1)}s</span> : null}
                        <button
                          className={`inline-flex items-center gap-1 ${
                            message.role === 'user'
                              ? 'hover:text-red-600 dark:hover:text-red-300'
                              : 'hover:text-red-600 dark:hover:text-red-300'
                          }`}
                          onClick={() => requestDeleteMessageRound(message)}
                          title="删除本轮对话"
                          aria-label="删除本轮对话"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                          删除
                        </button>
                        {message.role === 'assistant' && (
                          <>
                            <button className="inline-flex items-center gap-1 hover:text-blue-600" onClick={() => copyMessage(message)}>
                              {copiedMessageId === message.id ? <CheckCircle2 className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                              复制
                            </button>
                            {message.sourcePrompt && (
                              <button className="inline-flex items-center gap-1 hover:text-blue-600" onClick={() => retryMessage(message)}>
                                <RotateCcw className="h-3.5 w-3.5" />
                                重试
                              </button>
                            )}
                          </>
                        )}
                      </div>
                    </div>
                    {message.role === 'user' && (
                      <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-blue-100 text-blue-700 dark:bg-blue-950/50 dark:text-blue-200">
                        <User className="h-4 w-4" />
                      </div>
                    )}
                  </div>
                ))}
                {loading && (
                  <div className="flex items-center gap-3 text-sm text-gray-600 dark:text-slate-400">
                    <div className="flex h-8 w-8 items-center justify-center rounded-md bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300">
                      <Loader2 className="h-4 w-4 animate-spin" />
                    </div>
                    请稍等，AI处理中... {elapsedSeconds}s
                  </div>
                )}
                <div ref={messageEndRef} />
              </div>
            </div>

            <div className="border-t bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
              {attachedFiles.length > 0 && (
                <div className="mb-3 grid gap-2">
                  {attachedFiles.map((file) => {
                    const AttachmentIcon = getAttachmentIcon(file.fileKind)
                    return (
                      <div key={file.id} className="flex items-start gap-3 rounded-md border border-gray-200 bg-gray-50 px-3 py-2 dark:border-slate-700 dark:bg-slate-800">
                        <AttachmentIcon className="mt-0.5 h-4 w-4 shrink-0 text-sky-600 dark:text-sky-300" />
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="truncate text-sm font-medium text-gray-900 dark:text-slate-100">{file.filename}</span>
                            <span className="text-xs text-gray-500 dark:text-slate-400">{formatFileSize(file.fileSize)}</span>
                            {file.extractedText ? (
                              <Badge variant="outline" className="rounded-md bg-white text-xs">已提取正文</Badge>
                            ) : file.imageDataUrl ? (
                              <Badge variant="outline" className="rounded-md bg-white text-xs">视觉附件</Badge>
                            ) : (
                              <Badge variant="outline" className="rounded-md bg-white text-xs">仅文件信息</Badge>
                            )}
                          </div>
                          <div className="mt-1 line-clamp-2 text-xs text-gray-500 dark:text-slate-400">
                            {file.summary || '附件已加入本次对话上下文'}
                            {file.warnings?.length ? `；${file.warnings.join('；')}` : ''}
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => removeAttachment(file.id)}
                          className="rounded p-1 text-gray-400 hover:bg-white hover:text-red-600 dark:text-slate-500 dark:hover:bg-slate-700 dark:hover:text-red-300"
                          title="移除附件"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                    )
                  })}
                </div>
              )}
              <div>
                <div className="relative">
                  <Textarea
                    value={input}
                    onChange={(event) => setInput(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' && !event.shiftKey) {
                        event.preventDefault()
                        sendMessage()
                      }
                    }}
                    placeholder="输入问题，例如：请结合附件生成登录功能测试点，覆盖边界值和异常路径"
                    rows={3}
                    className="min-h-[92px] resize-none pr-24"
                  />
                  <Button
                    onClick={() => (loading ? stopGeneration() : sendMessage())}
                    disabled={(!loading && attachmentLoading) || (!loading && !input.trim() && !attachedFiles.length)}
                    className={`absolute bottom-2 right-2 h-8 px-3 shadow-sm ${loading ? 'bg-red-600 hover:bg-red-700' : 'bg-blue-600 hover:bg-blue-700'}`}
                  >
                    {loading ? <Square className="mr-1.5 h-3.5 w-3.5" /> : <Send className="mr-1.5 h-3.5 w-3.5" />}
                    {loading ? '停止' : '发送'}
                  </Button>
                </div>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                    <input
                      ref={attachmentInputRef}
                      type="file"
                      multiple
                      accept="image/*,.txt,.md,.json,.csv,.html,.htm,.pdf,.doc,.docx,.xls,.xlsx,.xml,.log"
                      className="hidden"
                      onChange={(event) => uploadAttachments(event.target.files)}
                    />
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => attachmentInputRef.current?.click()}
                      disabled={attachmentLoading || loading}
                    >
                      {attachmentLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Paperclip className="mr-2 h-4 w-4" />}
                      上传附件
                    </Button>
                    <span className="text-xs text-gray-500">
                      支持图片、PDF、Word、Excel、HTML、CSV、文本；可解析正文的附件会自动加入本次 AI 上下文。
                    </span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="flex min-h-0 flex-col gap-4 overflow-y-auto">
          <Card className="rounded-md">
            <CardHeader className="p-4">
              <CardTitle className="flex items-center gap-2 text-base">
                <Settings2 className="h-5 w-5 text-slate-600" />
                调用设置
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 p-4 pt-0">
              <div>
                <div className="mb-2 text-sm font-medium text-gray-700 dark:text-slate-200">输出格式</div>
                <div className="grid grid-cols-1 gap-2">
                  {outputModes.map((mode) => (
                    <button
                      key={mode.value}
                      onClick={() => setOutputMode(mode.value)}
                      className={`rounded-md border px-3 py-2 text-left text-sm ${
                        outputMode === mode.value
                          ? 'border-sky-500 bg-sky-50 text-sky-900 dark:border-slate-500 dark:bg-slate-800 dark:text-slate-100'
                          : 'border-gray-200 hover:bg-gray-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800/70'
                      }`}
                    >
                      {mode.label}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <div className="mb-2 flex items-center justify-between gap-2">
                  <div className="text-sm font-medium text-gray-700 dark:text-slate-200">业务上下文</div>
                  {businessContext && (
                    <button type="button" onClick={() => setBusinessContext('')} className="text-xs text-gray-500 hover:text-red-600">
                      清空
                    </button>
                  )}
                </div>
                <div className="mb-3 grid grid-cols-2 gap-2">
                  {businessContextTemplates.map((template) => (
                    <button
                      key={template.label}
                      type="button"
                      onClick={() => applyBusinessContextTemplate(template)}
                      className={`rounded-md border px-2.5 py-2 text-left transition ${
                        businessContext === template.context
                          ? 'border-sky-500 bg-sky-50 text-sky-900 dark:border-slate-500 dark:bg-slate-800 dark:text-slate-100'
                          : 'border-gray-200 hover:border-blue-300 hover:bg-blue-50 dark:border-slate-700 dark:text-slate-300 dark:hover:border-slate-500 dark:hover:bg-slate-800/70'
                      }`}
                    >
                      <div className="flex items-center gap-1.5 text-sm font-medium">
                        <UploadCloud className="h-3.5 w-3.5 text-sky-600 dark:text-sky-300" />
                        {template.label}
                      </div>
                      <div className="mt-1 text-[11px] leading-4 text-gray-500 dark:text-slate-400">{template.description}</div>
                    </button>
                  ))}
                </div>
                <Textarea
                  value={businessContext}
                  onChange={(event) => setBusinessContext(event.target.value)}
                  placeholder="选择上方业务场景，或填写项目、模块、角色、风险背景等上下文"
                  rows={6}
                />
              </div>
            </CardContent>
          </Card>

          <Card className="rounded-md">
            <CardHeader className="p-4">
              <CardTitle className="flex items-center gap-2 text-base">
                <Clipboard className="h-5 w-5 text-amber-600" />
                场景模板
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 p-4 pt-0">
              {promptTemplates.map((template) => (
                <div
                  key={template.title}
                  className="rounded-md border border-gray-200 px-3 py-2 hover:border-blue-300 hover:bg-blue-50 dark:border-slate-700 dark:hover:border-slate-500 dark:hover:bg-slate-800/70"
                >
                  <button type="button" onClick={() => setInput(template.prompt)} className="w-full text-left">
                    <div className="flex items-center gap-2 text-sm font-medium text-gray-900 dark:text-slate-100">
                      <FileText className="h-4 w-4 text-sky-600 dark:text-sky-300" />
                      {template.title}
                    </div>
                    <div className="mt-1 text-xs text-gray-500 dark:text-slate-400">{template.description}</div>
                  </button>
                  <div className="mt-2 flex justify-end">
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={() => sendMessage(template.prompt)}
                      disabled={loading}
                    >
                      <Send className="mr-2 h-3.5 w-3.5" />
                      立即发送
                    </Button>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

        </div>
      </div>
      <ConfirmDialog
        open={Boolean(pendingDeleteMessageId)}
        title="确认删除本轮对话"
        description={`确定要删除本轮对话吗？将删除该轮用户提问及对应 AI 回复，共 ${pendingDeleteMessages.length} 条消息，删除后无法恢复。`}
        confirmText="删除"
        cancelText="取消"
        variant="destructive"
        onConfirm={confirmDeleteMessageRound}
        onCancel={() => setPendingDeleteMessageId(null)}
      />
      <ConfirmDialog
        open={Boolean(pendingDeleteSession)}
        title="确认删除对话"
        description={`确定要删除“${pendingDeleteSession?.title || ''}”吗？删除后该对话记录将无法恢复。`}
        confirmText="删除"
        cancelText="取消"
        variant="destructive"
        onConfirm={confirmDeleteSession}
        onCancel={() => setPendingDeleteSession(null)}
      />
    </div>
  )
}

export default AIAssistant
