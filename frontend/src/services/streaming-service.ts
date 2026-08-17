/**
 * AI 助手流式响应服务
 *
 * 通过 fetch + ReadableStream 消费后端 SSE 接口（POST /api/v1/streaming/query/stream），
 * 正确解析 `event:` / `data:` 行，携带 Bearer 鉴权，支持 AbortController 中止。
 */

import { apiClient, getAuthToken } from './api/client'

export interface StreamCompleteInfo {
  content: string
  provider?: string
  model?: string
  tokensUsed?: number
  confidenceScore?: number
  processingTime?: number
}

export interface StreamCallbacks {
  onStart?: (info: { provider?: string; model?: string; taskType?: string }) => void
  onDelta?: (delta: string, content: string) => void
  onComplete?: (info: StreamCompleteInfo) => void
  onError?: (message: string) => void
}

export interface StreamQueryBody {
  content: string
  context?: Record<string, unknown>
  conversation_id?: number
  preferred_model?: string
}

const buildStreamUrl = () => `${apiClient.defaults.baseURL || ''}/api/v1/streaming/query/stream`

/**
 * 发起流式 AI 查询。
 *
 * 返回值：收到 complete 事件返回 true；流异常中断且未完成返回 false（调用方可回退到非流式接口）。
 */
export async function streamAiQuery(
  body: StreamQueryBody,
  callbacks: StreamCallbacks,
  signal?: AbortSignal,
): Promise<boolean> {
  const token = getAuthToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'text/event-stream',
  }
  if (token) headers.Authorization = `Bearer ${token}`

  const response = await fetch(buildStreamUrl(), {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
    signal,
  })

  if (!response.ok) {
    let detail = `HTTP ${response.status}`
    try {
      const data = await response.json()
      detail = data?.detail || data?.message || detail
    } catch {
      /* 非 JSON 错误体，保留状态码 */
    }
    throw new Error(`流式接口请求失败：${detail}`)
  }

  const reader = response.body?.getReader()
  if (!reader) {
    throw new Error('当前浏览器不支持流式响应')
  }

  const decoder = new TextDecoder()
  let buffer = ''
  let completed = false
  let content = ''

  const handleEvent = (eventType: string, rawData: string) => {
    let data: any
    try {
      data = rawData ? JSON.parse(rawData) : {}
    } catch {
      return
    }

    switch (eventType) {
      case 'ai_start':
        callbacks.onStart?.({
          provider: data.provider,
          model: data.model,
          taskType: data.task_type,
        })
        break
      case 'ai_content':
        if (typeof data.content === 'string' && data.content) {
          content = data.content
        } else if (typeof data.delta === 'string') {
          content += data.delta
        }
        callbacks.onDelta?.(typeof data.delta === 'string' ? data.delta : '', content)
        break
      case 'ai_complete':
        completed = true
        if (typeof data.content === 'string' && data.content) content = data.content
        callbacks.onComplete?.({
          content,
          provider: data.provider,
          model: data.model,
          tokensUsed: data.tokens_used,
          confidenceScore: data.confidence_score,
          processingTime: data.processing_time,
        })
        break
      case 'error':
        callbacks.onError?.(data.message || 'AI 服务调用失败')
        break
      default:
        break
    }
  }

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      // SSE 事件以空行分隔
      const events = buffer.split('\n\n')
      buffer = events.pop() || ''

      for (const block of events) {
        let eventType = 'message'
        const dataLines: string[] = []
        for (const line of block.split('\n')) {
          if (line.startsWith('event:')) {
            eventType = line.slice(6).trim()
          } else if (line.startsWith('data:')) {
            dataLines.push(line.slice(5).trimStart())
          }
        }
        if (dataLines.length) {
          handleEvent(eventType, dataLines.join('\n'))
        }
      }
    }
  } finally {
    reader.releaseLock?.()
  }

  return completed
}
