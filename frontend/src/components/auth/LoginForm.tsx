import React, { useState } from 'react'
import { Eye, EyeOff, User, Lock } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Checkbox } from '@/components/ui/Checkbox'

interface LoginFormData {
  username: string
  password: string
  rememberMe: boolean
}

interface LoginFormProps {
  formData: LoginFormData
  onChange: (data: LoginFormData) => void
  onSubmit: (e: React.FormEvent) => void
  isLoading: boolean
  error?: string | null
}

export const LoginForm: React.FC<LoginFormProps> = ({
  formData,
  onChange,
  onSubmit,
  isLoading,
  error
}) => {
  const [showPassword, setShowPassword] = useState(false)

  const handleInputChange = (field: keyof LoginFormData, value: string | boolean) => {
    onChange({
      ...formData,
      [field]: value
    })
  }

  return (
    <form onSubmit={onSubmit} className="space-y-6">
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm">
          {error}
        </div>
      )}

      <div>
        <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-2">
          用户名或邮箱
        </label>
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <User className="h-5 w-5 text-gray-400" />
          </div>
          <Input
            id="username"
            type="text"
            value={formData.username}
            onChange={(e) => handleInputChange('username', e.target.value)}
            placeholder="请输入用户名或邮箱"
            className="pl-10"
            required
            disabled={isLoading}
          />
        </div>
      </div>

      <div>
        <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
          密码
        </label>
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Lock className="h-5 w-5 text-gray-400" />
          </div>
          <Input
            id="password"
            type={showPassword ? 'text' : 'password'}
            value={formData.password}
            onChange={(e) => handleInputChange('password', e.target.value)}
            placeholder="请输入密码"
            className="pl-10 pr-10"
            required
            disabled={isLoading}
          />
          <button
            type="button"
            className="absolute inset-y-0 right-0 pr-3 flex items-center"
            onClick={() => setShowPassword(!showPassword)}
            disabled={isLoading}
          >
            {showPassword ? (
              <EyeOff className="h-5 w-5 text-gray-400 hover:text-gray-600" />
            ) : (
              <Eye className="h-5 w-5 text-gray-400 hover:text-gray-600" />
            )}
          </button>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <Checkbox
            id="rememberMe"
            checked={formData.rememberMe}
            onCheckedChange={(checked) => handleInputChange('rememberMe', checked as boolean)}
            disabled={isLoading}
          />
          <label htmlFor="rememberMe" className="ml-2 block text-sm text-gray-700">
            记住我
          </label>
        </div>

        <div className="text-sm">
          <a
            href="#"
            className="font-medium text-blue-600 hover:text-blue-500"
            onClick={(e) => {
              e.preventDefault()
              // TODO: 实现忘记密码功能
              alert('忘记密码功能待实现')
            }}
          >
            忘记密码？
          </a>
        </div>
      </div>

      <Button
        type="submit"
        className="w-full"
        disabled={isLoading || !formData.username || !formData.password}
      >
        {isLoading ? (
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
            登录中...
          </div>
        ) : (
          '登录'
        )}
      </Button>

      <div className="text-center">
        <p className="text-sm text-gray-600">
          还没有账号？{' '}
          <a
            href="#"
            className="font-medium text-blue-600 hover:text-blue-500"
            onClick={(e) => {
              e.preventDefault()
              // TODO: 实现注册功能
              alert('注册功能待实现')
            }}
          >
            立即注册
          </a>
        </p>
      </div>
    </form>
  )
}

export default LoginForm