// @ts-nocheck
import React, { createContext, useContext, useEffect, useState } from 'react'
import type { User } from '@/types'

interface AuthContextType {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

interface AuthProviderProps {
  children: React.ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const isAuthenticated = !!user

  // 妫€鏌ユ湰鍦板瓨鍌ㄧ殑token
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const token = localStorage.getItem('auth-token')
        if (token) {
          // 杩欓噷搴旇璋冪敤API楠岃瘉token骞惰幏鍙栫敤鎴蜂俊鎭?
          // 鏆傛椂浣跨敤妯℃嫙鏁版嵁
          const mockUser: User = {
            id: '1',
            username: 'admin',
            email: 'admin@example.com',
            role: 'admin',
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
          }
          setUser(mockUser)
        }
      } catch (error) {
        console.error('Auth check failed:', error)
        localStorage.removeItem('auth-token')
      } finally {
        setIsLoading(false)
      }
    }

    checkAuth()
  }, [])

  const login = async (username: string, password: string) => {
    try {
      setIsLoading(true)
      
      // 杩欓噷搴旇璋冪敤瀹為檯鐨勭櫥褰旳PI
      // const response = await apiClient.login({ username, password })
      
      // 妯℃嫙鐧诲綍
      if (username === 'admin' && password === 'admin') {
        const mockUser: User = {
          id: '1',
          username: 'admin',
          email: 'admin@example.com',
          role: 'admin',
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        }
        
        const mockToken = 'mock-jwt-token'
        localStorage.setItem('auth-token', mockToken)
        setUser(mockUser)
      } else {
        throw new Error('鐢ㄦ埛鍚嶆垨瀵嗙爜閿欒')
      }
    } catch (error) {
      throw error
    } finally {
      setIsLoading(false)
    }
  }

  const logout = () => {
    localStorage.removeItem('auth-token')
    setUser(null)
  }

  const refreshUser = async () => {
    try {
      const token = localStorage.getItem('auth-token')
      if (!token) {
        throw new Error('No token found')
      }
      
      // 杩欓噷搴旇璋冪敤API鍒锋柊鐢ㄦ埛淇℃伅
      // const response = await apiClient.getCurrentUser()
      // setUser(response.data)
    } catch (error) {
      console.error('Failed to refresh user:', error)
      logout()
    }
  }

  const value: AuthContextType = {
    user,
    isAuthenticated,
    isLoading,
    login,
    logout,
    refreshUser,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}