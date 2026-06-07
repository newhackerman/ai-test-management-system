// @ts-nocheck
/**
 * 瑙︽懜鎵嬪娍宸ュ叿绫?
 * 鎻愪緵鍚勭瑙︽懜鎵嬪娍鐨勬娴嬪拰澶勭悊
 */

export interface TouchPoint {
  x: number
  y: number
  time: number
}

export interface GestureResult {
  type: 'tap' | 'longPress' | 'swipe' | 'pinch' | 'pan' | 'none'
  direction?: 'left' | 'right' | 'up' | 'down'
  distance?: number
  duration?: number
  velocity?: number
  scale?: number
  deltaX?: number
  deltaY?: number
}

export class TouchGestureDetector {
  private startPoint: TouchPoint | null = null
  private endPoint: TouchPoint | null = null
  private longPressTimer: NodeJS.Timeout | null = null
  private longPressThreshold = 500 // 闀挎寜闃堝€硷紙姣锛?
  private swipeThreshold = 50 // 婊戝姩闃堝€硷紙鍍忕礌锛?
  private tapThreshold = 10 // 鐐瑰嚮闃堝€硷紙鍍忕礌锛?
  private velocityThreshold = 0.5 // 閫熷害闃堝€硷紙鍍忕礌/姣锛?

  /**
   * 澶勭悊瑙︽懜寮€濮嬩簨浠?
   */
  onTouchStart = (e: TouchEvent | React.TouchEvent, callback?: (result: GestureResult) => void): void => {
    const touch = 'touches' in e ? e.touches[0] : e.targetTouches[0]
    
    this.startPoint = {
      x: touch.clientX,
      y: touch.clientY,
      time: Date.now()
    }
    
    this.endPoint = null
    
    // 璁剧疆闀挎寜妫€娴?
    if (this.longPressTimer) {
      clearTimeout(this.longPressTimer)
    }
    
    this.longPressTimer = setTimeout(() => {
      if (callback && this.startPoint && !this.endPoint) {
        callback({
          type: 'longPress',
          duration: Date.now() - this.startPoint.time
        })
      }
    }, this.longPressThreshold)
  }

  /**
   * 澶勭悊瑙︽懜绉诲姩浜嬩欢
   */
  onTouchMove = (e: TouchEvent | React.TouchEvent, callback?: (result: GestureResult) => void): void => {
    const touch = 'touches' in e ? e.touches[0] : e.targetTouches[0]
    
    this.endPoint = {
      x: touch.clientX,
      y: touch.clientY,
      time: Date.now()
    }
    
    // 娓呴櫎闀挎寜妫€娴?
    if (this.longPressTimer) {
      clearTimeout(this.longPressTimer)
      this.longPressTimer = null
    }
    
    // 瀹炴椂骞崇Щ妫€娴?
    if (callback && this.startPoint) {
      const deltaX = this.endPoint.x - this.startPoint.x
      const deltaY = this.endPoint.y - this.startPoint.y
      
      callback({
        type: 'pan',
        deltaX,
        deltaY,
        distance: Math.sqrt(deltaX * deltaX + deltaY * deltaY)
      })
    }
  }

  /**
   * 澶勭悊瑙︽懜缁撴潫浜嬩欢
   */
  onTouchEnd = (e: TouchEvent | React.TouchEvent, callback?: (result: GestureResult) => void): GestureResult => {
    // 娓呴櫎闀挎寜妫€娴?
    if (this.longPressTimer) {
      clearTimeout(this.longPressTimer)
      this.longPressTimer = null
    }
    
    if (!this.startPoint) {
      return { type: 'none' }
    }
    
    const endTime = Date.now()
    const endPoint = this.endPoint || this.startPoint
    
    const deltaX = endPoint.x - this.startPoint.x
    const deltaY = endPoint.y - this.startPoint.y
    const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY)
    const duration = endTime - this.startPoint.time
    const velocity = distance / duration
    
    let result: GestureResult
    
    // 鍒ゆ柇鎵嬪娍绫诲瀷
    if (distance < this.tapThreshold && duration < 300) {
      // 鐐瑰嚮
      result = {
        type: 'tap',
        duration,
        deltaX,
        deltaY
      }
    } else if (distance >= this.swipeThreshold) {
      // 婊戝姩
      const absX = Math.abs(deltaX)
      const absY = Math.abs(deltaY)
      
      let direction: 'left' | 'right' | 'up' | 'down'
      if (absX > absY) {
        direction = deltaX > 0 ? 'right' : 'left'
      } else {
        direction = deltaY > 0 ? 'down' : 'up'
      }
      
      result = {
        type: 'swipe',
        direction,
        distance,
        duration,
        velocity,
        deltaX,
        deltaY
      }
    } else {
      result = {
        type: 'none',
        deltaX,
        deltaY,
        distance,
        duration
      }
    }
    
    if (callback) {
      callback(result)
    }
    
    // 閲嶇疆鐘舵€?
    this.startPoint = null
    this.endPoint = null
    
    return result
  }

  /**
   * 娓呯悊璧勬簮
   */
  cleanup = (): void => {
    if (this.longPressTimer) {
      clearTimeout(this.longPressTimer)
      this.longPressTimer = null
    }
    this.startPoint = null
    this.endPoint = null
  }
}

/**
 * 澶氱偣瑙︽帶鎵嬪娍妫€娴嬪櫒
 */
export class MultiTouchGestureDetector {
  private touches: TouchPoint[] = []
  private initialDistance = 0
  private initialScale = 1

  /**
   * 澶勭悊澶氱偣瑙︽懜寮€濮?
   */
  onTouchStart = (e: TouchEvent | React.TouchEvent): void => {
    const touches = 'touches' in e ? e.touches : e.targetTouches
    
    this.touches = Array.from(touches).map(touch => ({
      x: touch.clientX,
      y: touch.clientY,
      time: Date.now()
    }))
    
    if (this.touches.length === 2) {
      this.initialDistance = this.getDistance(this.touches[0], this.touches[1])
      this.initialScale = 1
    }
  }

  /**
   * 澶勭悊澶氱偣瑙︽懜绉诲姩
   */
  onTouchMove = (e: TouchEvent | React.TouchEvent, callback?: (result: GestureResult) => void): void => {
    const touches = 'touches' in e ? e.touches : e.targetTouches
    
    if (touches.length === 2 && this.touches.length === 2) {
      const currentTouches = Array.from(touches).map(touch => ({
        x: touch.clientX,
        y: touch.clientY,
        time: Date.now()
      }))
      
      const currentDistance = this.getDistance(currentTouches[0], currentTouches[1])
      const scale = currentDistance / this.initialDistance
      
      if (callback) {
        callback({
          type: 'pinch',
          scale,
          distance: currentDistance
        })
      }
    }
  }

  /**
   * 璁＄畻涓ょ偣闂磋窛绂?
   */
  private getDistance = (point1: TouchPoint, point2: TouchPoint): number => {
    const dx = point1.x - point2.x
    const dy = point1.y - point2.y
    return Math.sqrt(dx * dx + dy * dy)
  }

  /**
   * 娓呯悊璧勬簮
   */
  cleanup = (): void => {
    this.touches = []
    this.initialDistance = 0
    this.initialScale = 1
  }
}

/**
 * React Hook 褰㈠紡鐨勮Е鎽告墜鍔挎娴嬪櫒
 */
export const useTouchGesture = () => {
  const detector = new TouchGestureDetector()
  const multiTouchDetector = new MultiTouchGestureDetector()

  const handleTouchStart = (e: TouchEvent | React.TouchEvent, callback?: (result: GestureResult) => void) => {
    detector.onTouchStart(e, callback)
    multiTouchDetector.onTouchStart(e)
  }

  const handleTouchMove = (e: TouchEvent | React.TouchEvent, callback?: (result: GestureResult) => void) => {
    detector.onTouchMove(e, callback)
    multiTouchDetector.onTouchMove(e, callback)
  }

  const handleTouchEnd = (e: TouchEvent | React.TouchEvent, callback?: (result: GestureResult) => void) => {
    return detector.onTouchEnd(e, callback)
  }

  const cleanup = () => {
    detector.cleanup()
    multiTouchDetector.cleanup()
  }

  return {
    handleTouchStart,
    handleTouchMove,
    handleTouchEnd,
    cleanup
  }
}

/**
 * 闃叉姈瑙︽懜澶勭悊鍣?
 */
export const debouncedTouch = (callback: Function, delay: number = 300) => {
  let timeoutId: NodeJS.Timeout

  return (...args: any[]) => {
    clearTimeout(timeoutId)
    timeoutId = setTimeout(() => callback.apply(null, args), delay)
  }
}

/**
 * 鑺傛祦瑙︽懜澶勭悊鍣?
 */
export const throttledTouch = (callback: Function, delay: number = 100) => {
  let lastCall = 0

  return (...args: any[]) => {
    const now = Date.now()
    if (now - lastCall >= delay) {
      lastCall = now
      callback.apply(null, args)
    }
  }
}

/**
 * 瑙︽懜鍙嶉宸ュ叿
 */
export const touchFeedback = {
  /**
   * 瑙﹁鍙嶉
   */
  vibrate: (pattern: number | number[] = 10) => {
    if ('vibrate' in navigator) {
      navigator.vibrate(pattern)
    }
  },

  /**
   * 瑙嗚鍙嶉 - 娣诲姞鐐瑰嚮鏁堟灉
   */
  addTapEffect: (element: HTMLElement, className: string = 'tap-effect') => {
    element.classList.add(className)
    setTimeout(() => {
      element.classList.remove(className)
    }, 150)
  },

  /**
   * 闊抽鍙嶉
   */
  playSound: (frequency: number = 800, duration: number = 100) => {
    if ('AudioContext' in window || 'webkitAudioContext' in window) {
      const AudioContext = window.AudioContext || window.webkitAudioContext
      const audioContext = new AudioContext()
      const oscillator = audioContext.createOscillator()
      const gainNode = audioContext.createGain()

      oscillator.connect(gainNode)
      gainNode.connect(audioContext.destination)

      oscillator.frequency.value = frequency
      oscillator.type = 'sine'

      gainNode.gain.setValueAtTime(0.1, audioContext.currentTime)
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + duration / 1000)

      oscillator.start(audioContext.currentTime)
      oscillator.stop(audioContext.currentTime + duration / 1000)
    }
  }
}

export default TouchGestureDetector