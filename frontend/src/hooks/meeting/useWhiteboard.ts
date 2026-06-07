// 白板协作 Hook
import { useState, useCallback, useRef, useEffect } from 'react'
import { useMeetingRoomStore } from '@/stores/meeting/meetingRoomStore'
import whiteboardService, { type WhiteboardSyncEvent } from '@/services/whiteboardService'

export interface DrawingTool {
  type: 'pen' | 'rectangle' | 'circle' | 'triangle' | 'text' | 'eraser' | 'select' | 'move'
  color: string
  size: number
  opacity: number
}

export interface DrawingElement {
  id: string
  type: DrawingTool['type']
  points: Array<{ x: number; y: number }>
  style: {
    color: string
    size: number
    opacity: number
    fill?: boolean
  }
  text?: string
  bounds?: {
    x: number
    y: number
    width: number
    height: number
  }
  userId: number
  timestamp: number
  isSelected?: boolean
}

export interface WhiteboardData {
  elements: DrawingElement[]
  background: {
    color: string
    grid: boolean
  }
  zoom: number
  pan: { x: number; y: number }
}

export interface WhiteboardCollaborator {
  id: number
  name: string
  color: string
  cursor?: { x: number; y: number }
  isActive?: boolean
}

interface UseWhiteboardOptions {
  meetingId?: number
  currentUserId?: number
  canEdit?: boolean
  enableSync?: boolean
  onSave?: (data: WhiteboardData) => void
  onShare?: (data: WhiteboardData) => void
  onSync?: (data: WhiteboardData) => void
}

export const useWhiteboard = (options: UseWhiteboardOptions = {}) => {
  const {
    meetingId,
    currentUserId = 1,
    canEdit = true,
    enableSync = true,
    onSave,
    onShare,
    onSync
  } = options

  // Store
  const { whiteboardData, updateWhiteboard } = useMeetingRoomStore()

  // 状态管理
  const [currentTool, setCurrentTool] = useState<DrawingTool>({
    type: 'pen',
    color: '#000000',
    size: 3,
    opacity: 1
  })
  
  const [elements, setElements] = useState<DrawingElement[]>([])
  const [selectedElements, setSelectedElements] = useState<string[]>([])
  const [isDrawing, setIsDrawing] = useState(false)
  const [currentElement, setCurrentElement] = useState<DrawingElement | null>(null)
  const [zoom, setZoom] = useState(100)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [showGrid, setShowGrid] = useState(true)
  const [backgroundColor, setBackgroundColor] = useState('#ffffff')
  const [history, setHistory] = useState<DrawingElement[][]>([])
  const [historyIndex, setHistoryIndex] = useState(-1)
  const [collaborators, setCollaborators] = useState<WhiteboardCollaborator[]>([])

  // Refs
  const syncTimeoutRef = useRef<NodeJS.Timeout>()
  const lastSyncRef = useRef<number>(0)
  const isRemoteUpdateRef = useRef<boolean>(false)

  // 同步白板数据到 store
  const syncToStore = useCallback((data: WhiteboardData) => {
    updateWhiteboard(data)
    
    // 触发同步回调
    if (onSync) {
      // 防抖同步，避免频繁更新
      if (syncTimeoutRef.current) {
        clearTimeout(syncTimeoutRef.current)
      }
      
      syncTimeoutRef.current = setTimeout(() => {
        const now = Date.now()
        if (now - lastSyncRef.current > 100) { // 最小同步间隔 100ms
          onSync(data)
          lastSyncRef.current = now
        }
      }, 50)
    }
  }, [updateWhiteboard, onSync])

  // 从 store 加载白板数据
  useEffect(() => {
    if (whiteboardData) {
      setElements(whiteboardData.elements || [])
      setZoom(whiteboardData.zoom || 100)
      setPan(whiteboardData.pan || { x: 0, y: 0 })
      setShowGrid(whiteboardData.background?.grid ?? true)
      setBackgroundColor(whiteboardData.background?.color || '#ffffff')
    }
  }, [whiteboardData])

  // 初始化实时同步
  useEffect(() => {
    if (enableSync && meetingId && currentUserId) {
      // 连接同步服务
      whiteboardService.connectSync(meetingId, currentUserId)

      // 监听同步事件
      const handleSyncEvent = (event: WhiteboardSyncEvent) => {
        // 避免处理自己发送的事件
        if (event.userId === currentUserId) return

        isRemoteUpdateRef.current = true

        switch (event.type) {
          case 'element_added':
            setElements(prev => [...prev, event.data])
            break
          
          case 'element_updated':
            setElements(prev => prev.map(el => 
              el.id === event.data.id ? event.data : el
            ))
            break
          
          case 'element_deleted':
            setElements(prev => prev.filter(el => el.id !== event.data.elementId))
            break
          
          case 'canvas_cleared':
            setElements([])
            break
          
          case 'view_changed':
            setZoom(event.data.zoom)
            setPan(event.data.pan)
            break
        }

        setTimeout(() => {
          isRemoteUpdateRef.current = false
        }, 100)
      }

      whiteboardService.onSyncEvent(handleSyncEvent)

      // 清理函数
      return () => {
        whiteboardService.offSyncEvent(handleSyncEvent)
        whiteboardService.disconnectSync()
      }
    }
  }, [enableSync, meetingId, currentUserId])

  // 添加到历史记录
  const addToHistory = useCallback((newElements: DrawingElement[]) => {
    setHistory(prev => [...prev.slice(0, historyIndex + 1), newElements])
    setHistoryIndex(prev => prev + 1)
  }, [historyIndex])

  // 开始绘制
  const startDrawing = useCallback((point: { x: number; y: number }) => {
    if (!canEdit) return null

    if (currentTool.type === 'text') {
      const text = prompt('请输入文字:')
      if (text) {
        const element: DrawingElement = {
          id: Date.now().toString(),
          type: 'text',
          points: [point],
          style: { ...currentTool },
          text,
          userId: currentUserId,
          timestamp: Date.now()
        }
        
        const newElements = [...elements, element]
        setElements(newElements)
        addToHistory(newElements)
        
        // 同步到 store
        syncToStore({
          elements: newElements,
          background: { color: backgroundColor, grid: showGrid },
          zoom,
          pan
        })

        // 实时同步
        if (enableSync && !isRemoteUpdateRef.current) {
          whiteboardService.syncElementAdded(element, currentUserId)
        }
        
        return element
      }
      return null
    }

    const element: DrawingElement = {
      id: Date.now().toString(),
      type: currentTool.type,
      points: [point],
      style: { ...currentTool },
      userId: currentUserId,
      timestamp: Date.now()
    }

    setCurrentElement(element)
    setIsDrawing(true)
    return element
  }, [canEdit, currentTool, currentUserId, elements, addToHistory, syncToStore, backgroundColor, showGrid, zoom, pan])

  // 继续绘制
  const continueDrawing = useCallback((point: { x: number; y: number }) => {
    if (!isDrawing || !currentElement || !canEdit) return

    if (currentTool.type === 'pen') {
      setCurrentElement(prev => prev ? {
        ...prev,
        points: [...prev.points, point]
      } : null)
    } else {
      setCurrentElement(prev => prev ? {
        ...prev,
        points: [prev.points[0], point]
      } : null)
    }
  }, [isDrawing, currentElement, canEdit, currentTool.type])

  // 结束绘制
  const endDrawing = useCallback(() => {
    if (!isDrawing || !currentElement) return

    const newElements = [...elements, currentElement]
    setElements(newElements)
    addToHistory(newElements)
    setCurrentElement(null)
    setIsDrawing(false)

    // 同步到 store
    syncToStore({
      elements: newElements,
      background: { color: backgroundColor, grid: showGrid },
      zoom,
      pan
    })

    // 实时同步
    if (enableSync && !isRemoteUpdateRef.current) {
      whiteboardService.syncElementAdded(currentElement, currentUserId)
    }
  }, [isDrawing, currentElement, elements, addToHistory, syncToStore, backgroundColor, showGrid, zoom, pan])

  // 撤销
  const undo = useCallback(() => {
    if (historyIndex > 0) {
      const newIndex = historyIndex - 1
      const newElements = history[newIndex] || []
      
      setHistoryIndex(newIndex)
      setElements(newElements)
      
      // 同步到 store
      syncToStore({
        elements: newElements,
        background: { color: backgroundColor, grid: showGrid },
        zoom,
        pan
      })
    }
  }, [historyIndex, history, syncToStore, backgroundColor, showGrid, zoom, pan])

  // 重做
  const redo = useCallback(() => {
    if (historyIndex < history.length - 1) {
      const newIndex = historyIndex + 1
      const newElements = history[newIndex] || []
      
      setHistoryIndex(newIndex)
      setElements(newElements)
      
      // 同步到 store
      syncToStore({
        elements: newElements,
        background: { color: backgroundColor, grid: showGrid },
        zoom,
        pan
      })
    }
  }, [historyIndex, history, syncToStore, backgroundColor, showGrid, zoom, pan])

  // 清空画布
  const clearCanvas = useCallback(() => {
    if (confirm('确定要清空画布吗？')) {
      setElements([])
      addToHistory([])
      
      // 同步到 store
      syncToStore({
        elements: [],
        background: { color: backgroundColor, grid: showGrid },
        zoom,
        pan
      })

      // 实时同步
      if (enableSync && !isRemoteUpdateRef.current) {
        whiteboardService.syncCanvasCleared(currentUserId)
      }
    }
  }, [addToHistory, syncToStore, backgroundColor, showGrid, zoom, pan, enableSync, currentUserId])

  // 缩放控制
  const zoomIn = useCallback(() => {
    const newZoom = Math.min(200, zoom + 10)
    setZoom(newZoom)
    
    // 同步到 store
    syncToStore({
      elements,
      background: { color: backgroundColor, grid: showGrid },
      zoom: newZoom,
      pan
    })
  }, [zoom, syncToStore, elements, backgroundColor, showGrid, pan])

  const zoomOut = useCallback(() => {
    const newZoom = Math.max(50, zoom - 10)
    setZoom(newZoom)
    
    // 同步到 store
    syncToStore({
      elements,
      background: { color: backgroundColor, grid: showGrid },
      zoom: newZoom,
      pan
    })
  }, [zoom, syncToStore, elements, backgroundColor, showGrid, pan])

  // 设置缩放
  const setZoomLevel = useCallback((level: number) => {
    const newZoom = Math.max(50, Math.min(200, level))
    setZoom(newZoom)
    
    // 同步到 store
    syncToStore({
      elements,
      background: { color: backgroundColor, grid: showGrid },
      zoom: newZoom,
      pan
    })
  }, [syncToStore, elements, backgroundColor, showGrid, pan])

  // 平移画布
  const panCanvas = useCallback((deltaX: number, deltaY: number) => {
    const newPan = {
      x: pan.x + deltaX,
      y: pan.y + deltaY
    }
    setPan(newPan)
    
    // 同步到 store
    syncToStore({
      elements,
      background: { color: backgroundColor, grid: showGrid },
      zoom,
      pan: newPan
    })
  }, [pan, syncToStore, elements, backgroundColor, showGrid, zoom])

  // 切换网格
  const toggleGrid = useCallback(() => {
    const newShowGrid = !showGrid
    setShowGrid(newShowGrid)
    
    // 同步到 store
    syncToStore({
      elements,
      background: { color: backgroundColor, grid: newShowGrid },
      zoom,
      pan
    })
  }, [showGrid, syncToStore, elements, backgroundColor, zoom, pan])

  // 设置背景色
  const setBackgroundColorValue = useCallback((color: string) => {
    setBackgroundColor(color)
    
    // 同步到 store
    syncToStore({
      elements,
      background: { color, grid: showGrid },
      zoom,
      pan
    })
  }, [syncToStore, elements, showGrid, zoom, pan])

  // 保存白板
  const saveWhiteboard = useCallback(() => {
    const data: WhiteboardData = {
      elements,
      background: {
        color: backgroundColor,
        grid: showGrid
      },
      zoom,
      pan
    }
    
    onSave?.(data)
  }, [elements, backgroundColor, showGrid, zoom, pan, onSave])

  // 分享白板
  const shareWhiteboard = useCallback(() => {
    const data: WhiteboardData = {
      elements,
      background: {
        color: backgroundColor,
        grid: showGrid
      },
      zoom,
      pan
    }
    
    onShare?.(data)
  }, [elements, backgroundColor, showGrid, zoom, pan, onShare])

  // 导出白板数据
  const exportWhiteboard = useCallback((format: 'json' | 'png' | 'svg' = 'json') => {
    const data: WhiteboardData = {
      elements,
      background: {
        color: backgroundColor,
        grid: showGrid
      },
      zoom,
      pan
    }

    if (format === 'json') {
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `whiteboard-${Date.now()}.json`
      a.click()
      URL.revokeObjectURL(url)
    }
    
    return data
  }, [elements, backgroundColor, showGrid, zoom, pan])

  // 导入白板数据
  const importWhiteboard = useCallback((data: WhiteboardData) => {
    setElements(data.elements || [])
    setZoom(data.zoom || 100)
    setPan(data.pan || { x: 0, y: 0 })
    setShowGrid(data.background?.grid ?? true)
    setBackgroundColor(data.background?.color || '#ffffff')
    
    // 添加到历史记录
    addToHistory(data.elements || [])
    
    // 同步到 store
    syncToStore(data)
  }, [addToHistory, syncToStore])

  // 更新协作者
  const updateCollaborators = useCallback((newCollaborators: WhiteboardCollaborator[]) => {
    setCollaborators(newCollaborators)
  }, [])

  // 清理
  useEffect(() => {
    return () => {
      if (syncTimeoutRef.current) {
        clearTimeout(syncTimeoutRef.current)
      }
    }
  }, [])

  return {
    // 状态
    currentTool,
    setCurrentTool,
    elements,
    selectedElements,
    setSelectedElements,
    isDrawing,
    currentElement,
    zoom,
    pan,
    showGrid,
    backgroundColor,
    history,
    historyIndex,
    collaborators,
    canEdit,

    // 绘制操作
    startDrawing,
    continueDrawing,
    endDrawing,

    // 历史操作
    undo,
    redo,
    canUndo: historyIndex > 0,
    canRedo: historyIndex < history.length - 1,

    // 画布操作
    clearCanvas,
    zoomIn,
    zoomOut,
    setZoomLevel,
    panCanvas,
    toggleGrid,
    setBackgroundColor: setBackgroundColorValue,

    // 数据操作
    saveWhiteboard,
    shareWhiteboard,
    exportWhiteboard,
    importWhiteboard,

    // 协作
    updateCollaborators,

    // 工具配置
    tools: [
      { type: 'select', label: '选择' },
      { type: 'pen', label: '画笔' },
      { type: 'rectangle', label: '矩形' },
      { type: 'circle', label: '圆形' },
      { type: 'triangle', label: '三角形' },
      { type: 'text', label: '文字' },
      { type: 'eraser', label: '橡皮擦' },
      { type: 'move', label: '移动' }
    ] as const,

    colors: [
      '#000000', '#ffffff', '#ff0000', '#00ff00', '#0000ff',
      '#ffff00', '#ff00ff', '#00ffff', '#ffa500', '#800080',
      '#ffc0cb', '#a52a2a', '#808080', '#008000', '#000080'
    ] as const
  }
}

export default useWhiteboard