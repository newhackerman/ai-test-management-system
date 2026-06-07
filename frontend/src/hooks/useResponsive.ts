// @ts-nocheck
import { useState, useEffect } from 'react'

interface ResponsiveState {
  isMobile: boolean
  isTablet: boolean
  isDesktop: boolean
  screenWidth: number
  screenHeight: number
  orientation: 'portrait' | 'landscape'
  isTouchDevice: boolean
}

// 鏂偣瀹氫箟
const BREAKPOINTS = {
  mobile: 768,
  tablet: 1024,
  desktop: 1280
}

/**
 * 鍝嶅簲寮忚璁?Hook
 * 妫€娴嬭澶囩被鍨嬨€佸睆骞曞昂瀵搞€佹柟鍚戠瓑
 */
export const useResponsive = (): ResponsiveState => {
  const [state, setState] = useState<ResponsiveState>(() => {
    if (typeof window === 'undefined') {
      return {
        isMobile: false,
        isTablet: false,
        isDesktop: true,
        screenWidth: 1920,
        screenHeight: 1080,
        orientation: 'landscape',
        isTouchDevice: false
      }
    }

    const width = window.innerWidth
    const height = window.innerHeight
    
    return {
      isMobile: width < BREAKPOINTS.mobile,
      isTablet: width >= BREAKPOINTS.mobile && width < BREAKPOINTS.tablet,
      isDesktop: width >= BREAKPOINTS.tablet,
      screenWidth: width,
      screenHeight: height,
      orientation: width > height ? 'landscape' : 'portrait',
      isTouchDevice: 'ontouchstart' in window || navigator.maxTouchPoints > 0
    }
  })

  useEffect(() => {
    const handleResize = () => {
      const width = window.innerWidth
      const height = window.innerHeight
      
      setState({
        isMobile: width < BREAKPOINTS.mobile,
        isTablet: width >= BREAKPOINTS.mobile && width < BREAKPOINTS.tablet,
        isDesktop: width >= BREAKPOINTS.tablet,
        screenWidth: width,
        screenHeight: height,
        orientation: width > height ? 'landscape' : 'portrait',
        isTouchDevice: 'ontouchstart' in window || navigator.maxTouchPoints > 0
      })
    }

    const handleOrientationChange = () => {
      // 寤惰繜鎵ц浠ョ‘淇濊幏鍙栨纭殑灏哄
      setTimeout(handleResize, 100)
    }

    window.addEventListener('resize', handleResize)
    window.addEventListener('orientationchange', handleOrientationChange)

    return () => {
      window.removeEventListener('resize', handleResize)
      window.removeEventListener('orientationchange', handleOrientationChange)
    }
  }, [])

  return state
}

/**
 * 濯掍綋鏌ヨ Hook
 * 鐢ㄤ簬妫€娴嬬壒瀹氱殑濯掍綋鏌ヨ鏉′欢
 */
export const useMediaQuery = (query: string): boolean => {
  const [matches, setMatches] = useState(() => {
    if (typeof window === 'undefined') return false
    return window.matchMedia(query).matches
  })

  useEffect(() => {
    if (typeof window === 'undefined') return

    const mediaQuery = window.matchMedia(query)
    const handleChange = (e: MediaQueryListEvent) => setMatches(e.matches)

    mediaQuery.addEventListener('change', handleChange)
    setMatches(mediaQuery.matches)

    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [query])

  return matches
}

/**
 * 璁惧绫诲瀷妫€娴?Hook
 */
export const useDeviceType = () => {
  const { isMobile, isTablet, isDesktop, isTouchDevice } = useResponsive()
  
  const deviceType = isMobile ? 'mobile' : isTablet ? 'tablet' : 'desktop'
  
  // 妫€娴嬪叿浣撹澶?
  const userAgent = typeof navigator !== 'undefined' ? navigator.userAgent : ''
  const isIOS = /iPad|iPhone|iPod/.test(userAgent)
  const isAndroid = /Android/.test(userAgent)
  const isSafari = /Safari/.test(userAgent) && !/Chrome/.test(userAgent)
  const isChrome = /Chrome/.test(userAgent)
  const isFirefox = /Firefox/.test(userAgent)
  
  return {
    deviceType,
    isMobile,
    isTablet,
    isDesktop,
    isTouchDevice,
    isIOS,
    isAndroid,
    isSafari,
    isChrome,
    isFirefox
  }
}

/**
 * 灞忓箷鏂瑰悜 Hook
 */
export const useOrientation = () => {
  const { orientation, screenWidth, screenHeight } = useResponsive()
  
  return {
    orientation,
    isPortrait: orientation === 'portrait',
    isLandscape: orientation === 'landscape',
    screenWidth,
    screenHeight
  }
}

/**
 * 瑙︽懜鎵嬪娍 Hook
 */
export const useTouchGestures = () => {
  const [touchStart, setTouchStart] = useState<{ x: number; y: number; time: number } | null>(null)
  const [touchEnd, setTouchEnd] = useState<{ x: number; y: number; time: number } | null>(null)

  const handleTouchStart = (e: TouchEvent | React.TouchEvent) => {
    const touch = 'touches' in e ? e.touches[0] : e.targetTouches[0]
    setTouchEnd(null)
    setTouchStart({
      x: touch.clientX,
      y: touch.clientY,
      time: Date.now()
    })
  }

  const handleTouchMove = (e: TouchEvent | React.TouchEvent) => {
    const touch = 'touches' in e ? e.touches[0] : e.targetTouches[0]
    setTouchEnd({
      x: touch.clientX,
      y: touch.clientY,
      time: Date.now()
    })
  }

  const handleTouchEnd = () => {
    if (!touchStart || !touchEnd) return null

    const distanceX = touchStart.x - touchEnd.x
    const distanceY = touchStart.y - touchEnd.y
    const timeDistance = touchEnd.time - touchStart.time
    
    const isLeftSwipe = distanceX > 50
    const isRightSwipe = distanceX < -50
    const isUpSwipe = distanceY > 50
    const isDownSwipe = distanceY < -50
    
    const isHorizontalSwipe = Math.abs(distanceX) > Math.abs(distanceY)
    const isVerticalSwipe = Math.abs(distanceY) > Math.abs(distanceX)
    
    const isTap = Math.abs(distanceX) < 10 && Math.abs(distanceY) < 10 && timeDistance < 300
    const isLongPress = timeDistance > 500
    const isQuickSwipe = timeDistance < 300 && (Math.abs(distanceX) > 50 || Math.abs(distanceY) > 50)

    return {
      distanceX,
      distanceY,
      timeDistance,
      isLeftSwipe,
      isRightSwipe,
      isUpSwipe,
      isDownSwipe,
      isHorizontalSwipe,
      isVerticalSwipe,
      isTap,
      isLongPress,
      isQuickSwipe,
      direction: isLeftSwipe ? 'left' : isRightSwipe ? 'right' : isUpSwipe ? 'up' : isDownSwipe ? 'down' : null
    }
  }

  return {
    touchStart,
    touchEnd,
    handleTouchStart,
    handleTouchMove,
    handleTouchEnd
  }
}

/**
 * 瑙嗗彛灏哄 Hook
 */
export const useViewport = () => {
  const [viewport, setViewport] = useState(() => {
    if (typeof window === 'undefined') {
      return { width: 1920, height: 1080 }
    }
    return {
      width: window.innerWidth,
      height: window.innerHeight
    }
  })

  useEffect(() => {
    const handleResize = () => {
      setViewport({
        width: window.innerWidth,
        height: window.innerHeight
      })
    }

    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  return viewport
}

export default useResponsive