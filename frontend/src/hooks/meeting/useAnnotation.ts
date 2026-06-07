// 标注功能自定义Hook
import { useState, useCallback, useRef, useEffect } from 'react'

export interface AnnotationTool {
  type: 'pen' | 'rectangle' | 'circle' | 'text' | 'eraser' | 'pointer' | 'arrow' | 'line'
  color: string
  size: number
  opacity?: number
}

export interface AnnotationPoint {
  x: number
  y: number
  pressure?: number
  timestamp?: number
}

export interface Annotation {
  id: string
  tool: AnnotationTool
  points: AnnotationPoint[]
  text?: string
  timestamp: number
  userId: number
  userName?: string
  isCompleted: boolean
}

export interface AnnotationState {
  annotations: Annotation[]
  currentTool: AnnotationTool
  isDrawing: boolean
  showAnnotations: boolean
  canAnnotate: boolean
}

export const useAnnotation = (canvasRef: React.RefObject<HTMLCanvasElement>, meetingId?: string) => {
  // 状态管理
  const [state, setState] = useState<AnnotationState>({
    annotations: [],
    currentTool: {
      type: 'pen',
      color: '#ff0000',
      size: 3,
      opacity: 1
    },
    isDrawing: false,
    showAnnotations: true,
    canAnnotate: true
  })

  const currentAnnotationRef = useRef<Annotation | null>(null)
  const contextRef = useRef<CanvasRenderingContext2D | null>(null)

  // 初始化画布
  const initializeCanvas = useCallback(() => {
    if (!canvasRef.current) return

    const canvas = canvasRef.current
    const context = canvas.getContext('2d')
    if (!context) return

    contextRef.current = context
    
    // 设置画布大小
    const rect = canvas.getBoundingClientRect()
    canvas.width = rect.width * window.devicePixelRatio
    canvas.height = rect.height * window.devicePixelRatio
    
    context.scale(window.devicePixelRatio, window.devicePixelRatio)
    context.lineCap = 'round'
    context.lineJoin = 'round'
  }, [canvasRef])

  // 获取相对坐标
  const getRelativePosition = useCallback((e: MouseEvent | React.MouseEvent): AnnotationPoint => {
    if (!canvasRef.current) return { x: 0, y: 0 }

    const rect = canvasRef.current.getBoundingClientRect()
    return {
      x: (e.clientX - rect.left) / rect.width,
      y: (e.clientY - rect.top) / rect.height,
      pressure: (e as any).pressure || 1,
      timestamp: Date.now()
    }
  }, [canvasRef])

  // 开始绘制
  const startDrawing = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!state.canAnnotate || !canvasRef.current) return

    const point = getRelativePosition(e)
    
    // 创建新的标注
    const newAnnotation: Annotation = {
      id: `annotation_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      tool: { ...state.currentTool },
      points: [point],
      timestamp: Date.now(),
      userId: 1, // 当前用户ID，应该从用户状态获取
      userName: '当前用户', // 当前用户名，应该从用户状态获取
      isCompleted: false
    }

    // 处理文字标注
    if (state.currentTool.type === 'text') {
      const text = prompt('请输入文字:')
      if (text) {
        newAnnotation.text = text
        newAnnotation.isCompleted = true
        setState(prev => ({
          ...prev,
          annotations: [...prev.annotations, newAnnotation]
        }))
        
        // 同步到其他用户
        syncAnnotation(newAnnotation)
      }
      return
    }

    // 处理橡皮擦
    if (state.currentTool.type === 'eraser') {
      eraseAnnotations(point)
      return
    }

    currentAnnotationRef.current = newAnnotation
    setState(prev => ({
      ...prev,
      isDrawing: true,
      annotations: [...prev.annotations, newAnnotation]
    }))
  }, [state.canAnnotate, state.currentTool, canvasRef, getRelativePosition])

  // 继续绘制
  const continueDrawing = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!state.isDrawing || !currentAnnotationRef.current || !state.canAnnotate) return

    const point = getRelativePosition(e)
    const annotation = currentAnnotationRef.current

    // 更新当前标注的点
    annotation.points.push(point)

    setState(prev => ({
      ...prev,
      annotations: prev.annotations.map(ann => 
        ann.id === annotation.id ? { ...annotation } : ann
      )
    }))

    // 实时绘制
    drawAnnotation(annotation)
  }, [state.isDrawing, state.canAnnotate, getRelativePosition])

  // 结束绘制
  const stopDrawing = useCallback(() => {
    if (!state.isDrawing || !currentAnnotationRef.current) return

    const annotation = currentAnnotationRef.current
    annotation.isCompleted = true

    setState(prev => ({
      ...prev,
      isDrawing: false,
      annotations: prev.annotations.map(ann => 
        ann.id === annotation.id ? { ...annotation } : ann
      )
    }))

    // 同步到其他用户
    syncAnnotation(annotation)
    currentAnnotationRef.current = null
  }, [state.isDrawing])

  // 绘制单个标注
  const drawAnnotation = useCallback((annotation: Annotation) => {
    if (!contextRef.current || !canvasRef.current) return

    const context = contextRef.current
    const canvas = canvasRef.current
    const rect = canvas.getBoundingClientRect()

    context.save()
    context.globalAlpha = annotation.tool.opacity || 1
    context.strokeStyle = annotation.tool.color
    context.fillStyle = annotation.tool.color
    context.lineWidth = annotation.tool.size

    const points = annotation.points.map(p => ({
      x: p.x * rect.width,
      y: p.y * rect.height
    }))

    switch (annotation.tool.type) {
      case 'pen':
        if (points.length > 1) {
          context.beginPath()
          context.moveTo(points[0].x, points[0].y)
          for (let i = 1; i < points.length; i++) {
            context.lineTo(points[i].x, points[i].y)
          }
          context.stroke()
        }
        break

      case 'rectangle':
        if (points.length >= 2) {
          const start = points[0]
          const end = points[points.length - 1]
          context.strokeRect(
            start.x,
            start.y,
            end.x - start.x,
            end.y - start.y
          )
        }
        break

      case 'circle':
        if (points.length >= 2) {
          const start = points[0]
          const end = points[points.length - 1]
          const radius = Math.sqrt(
            Math.pow(end.x - start.x, 2) + Math.pow(end.y - start.y, 2)
          )
          context.beginPath()
          context.arc(start.x, start.y, radius, 0, 2 * Math.PI)
          context.stroke()
        }
        break

      case 'arrow':
        if (points.length >= 2) {
          const start = points[0]
          const end = points[points.length - 1]
          drawArrow(context, start.x, start.y, end.x, end.y, annotation.tool.size)
        }
        break

      case 'line':
        if (points.length >= 2) {
          const start = points[0]
          const end = points[points.length - 1]
          context.beginPath()
          context.moveTo(start.x, start.y)
          context.lineTo(end.x, end.y)
          context.stroke()
        }
        break

      case 'text':
        if (points.length > 0 && annotation.text) {
          context.font = `${annotation.tool.size * 4}px Arial`
          context.fillText(annotation.text, points[0].x, points[0].y)
        }
        break
    }

    context.restore()
  }, [canvasRef])

  // 绘制箭头
  const drawArrow = useCallback((
    context: CanvasRenderingContext2D,
    fromX: number,
    fromY: number,
    toX: number,
    toY: number,
    size: number
  ) => {
    const headLength = size * 3
    const angle = Math.atan2(toY - fromY, toX - fromX)

    // 绘制线条
    context.beginPath()
    context.moveTo(fromX, fromY)
    context.lineTo(toX, toY)
    context.stroke()

    // 绘制箭头头部
    context.beginPath()
    context.moveTo(toX, toY)
    context.lineTo(
      toX - headLength * Math.cos(angle - Math.PI / 6),
      toY - headLength * Math.sin(angle - Math.PI / 6)
    )
    context.moveTo(toX, toY)
    context.lineTo(
      toX - headLength * Math.cos(angle + Math.PI / 6),
      toY - headLength * Math.sin(angle + Math.PI / 6)
    )
    context.stroke()
  }, [])

  // 重绘所有标注
  const redrawAnnotations = useCallback(() => {
    if (!contextRef.current || !canvasRef.current) return

    const context = contextRef.current
    const canvas = canvasRef.current

    // 清空画布
    context.clearRect(0, 0, canvas.width, canvas.height)

    // 绘制所有标注
    if (state.showAnnotations) {
      state.annotations.forEach(annotation => {
        drawAnnotation(annotation)
      })
    }
  }, [state.annotations, state.showAnnotations, drawAnnotation, canvasRef])

  // 橡皮擦功能
  const eraseAnnotations = useCallback((point: AnnotationPoint) => {
    const eraseRadius = state.currentTool.size * 0.01 // 相对于画布的擦除半径

    setState(prev => ({
      ...prev,
      annotations: prev.annotations.filter(annotation => {
        // 检查标注是否在擦除范围内
        return !annotation.points.some(p => {
          const distance = Math.sqrt(
            Math.pow(p.x - point.x, 2) + Math.pow(p.y - point.y, 2)
          )
          return distance <= eraseRadius
        })
      })
    }))
  }, [state.currentTool.size])

  // 清除所有标注
  const clearAnnotations = useCallback(() => {
    setState(prev => ({
      ...prev,
      annotations: []
    }))
    
    if (meetingId) {
      // 同步清除操作到其他用户
      syncClearAnnotations()
    }
  }, [meetingId])

  // 设置工具
  const setTool = useCallback((tool: Partial<AnnotationTool>) => {
    setState(prev => ({
      ...prev,
      currentTool: { ...prev.currentTool, ...tool }
    }))
  }, [])

  // 切换标注显示
  const toggleAnnotations = useCallback(() => {
    setState(prev => ({
      ...prev,
      showAnnotations: !prev.showAnnotations
    }))
  }, [])

  // 同步标注到其他用户
  const syncAnnotation = useCallback(async (annotation: Annotation) => {
    if (!meetingId) return

    try {
      await fetch(`/api/meetings/${meetingId}/annotations`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(annotation)
      })
    } catch (error) {
      console.error('同步标注失败:', error)
    }
  }, [meetingId])

  // 同步清除操作
  const syncClearAnnotations = useCallback(async () => {
    if (!meetingId) return

    try {
      await fetch(`/api/meetings/${meetingId}/annotations/clear`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })
    } catch (error) {
      console.error('同步清除标注失败:', error)
    }
  }, [meetingId])

  // 监听画布大小变化
  useEffect(() => {
    const handleResize = () => {
      initializeCanvas()
      redrawAnnotations()
    }

    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [initializeCanvas, redrawAnnotations])

  // 初始化画布
  useEffect(() => {
    initializeCanvas()
  }, [initializeCanvas])

  // 重绘标注
  useEffect(() => {
    redrawAnnotations()
  }, [redrawAnnotations])

  return {
    // 状态
    annotations: state.annotations,
    currentTool: state.currentTool,
    isDrawing: state.isDrawing,
    showAnnotations: state.showAnnotations,
    canAnnotate: state.canAnnotate,

    // 方法
    startDrawing,
    continueDrawing,
    stopDrawing,
    clearAnnotations,
    setTool,
    toggleAnnotations,
    redrawAnnotations
  }
}

export default useAnnotation