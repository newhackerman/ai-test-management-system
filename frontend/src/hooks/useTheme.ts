// @ts-nocheck
import { useEffect, useState } from 'react'
import type { Theme } from '@/types'

interface UseThemeReturn {
  theme: Theme
  setTheme: (theme: Theme) => void
  systemTheme: 'light' | 'dark'
  resolvedTheme: 'light' | 'dark'
  toggleTheme: () => void
}

export function useTheme(): UseThemeReturn {
  const [theme, setThemeState] = useState<Theme>(() => {
    if (typeof window !== 'undefined') {
      return (localStorage.getItem('theme') as Theme) || 'system'
    }
    return 'system'
  })

  const [systemTheme, setSystemTheme] = useState<'light' | 'dark'>(() => {
    if (typeof window !== 'undefined') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
    }
    return 'light'
  })

  const resolvedTheme = theme === 'system' ? systemTheme : theme

  // 鐩戝惉绯荤粺涓婚鍙樺寲
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    
    const handleChange = (e: MediaQueryListEvent) => {
      setSystemTheme(e.matches ? 'dark' : 'light')
    }

    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [])

  // 搴旂敤涓婚鍒癉OM
  useEffect(() => {
    const root = window.document.documentElement
    
    root.classList.remove('light', 'dark')
    root.classList.add(resolvedTheme)
    
    // 璁剧疆涓婚鑹插僵鍏冩爣绛?
    const themeColorMeta = document.querySelector('meta[name="theme-color"]')
    if (themeColorMeta) {
      themeColorMeta.setAttribute('content', resolvedTheme === 'dark' ? '#0f172a' : '#ffffff')
    } else {
      const meta = document.createElement('meta')
      meta.name = 'theme-color'
      meta.content = resolvedTheme === 'dark' ? '#0f172a' : '#ffffff'
      document.head.appendChild(meta)
    }
  }, [resolvedTheme])

  const setTheme = (newTheme: Theme) => {
    setThemeState(newTheme)
    localStorage.setItem('theme', newTheme)
  }

  const toggleTheme = () => {
    if (theme === 'light') {
      setTheme('dark')
    } else if (theme === 'dark') {
      setTheme('system')
    } else {
      setTheme('light')
    }
  }

  return {
    theme,
    setTheme,
    systemTheme,
    resolvedTheme,
    toggleTheme,
  }
}