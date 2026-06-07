import React from 'react'

interface PasswordStrengthIndicatorProps {
  password: string
  className?: string
}

export const PasswordStrengthIndicator: React.FC<PasswordStrengthIndicatorProps> = ({
  password,
  className = ''
}) => {
  const requirements = [
    {
      test: (pwd: string) => pwd.length >= 8,
      label: '至少8个字符',
      key: 'length'
    },
    {
      test: (pwd: string) => /[A-Z]/.test(pwd),
      label: '包含大写字母',
      key: 'uppercase'
    },
    {
      test: (pwd: string) => /[a-z]/.test(pwd),
      label: '包含小写字母',
      key: 'lowercase'
    },
    {
      test: (pwd: string) => /\d/.test(pwd),
      label: '包含数字',
      key: 'number'
    },
    {
      test: (pwd: string) => /[!@#$%^&*(),.?":{}|<>]/.test(pwd),
      label: '包含特殊符号 (!@#$%^&*等)',
      key: 'special'
    }
  ]

  const passedRequirements = requirements.filter(req => req.test(password))
  const strength = passedRequirements.length
  
  const getStrengthColor = () => {
    if (strength === 0) return 'text-gray-400'
    if (strength <= 2) return 'text-red-500'
    if (strength <= 4) return 'text-yellow-500'
    return 'text-green-500'
  }

  const getStrengthText = () => {
    if (strength === 0) return '请输入密码'
    if (strength <= 2) return '密码强度：弱'
    if (strength <= 4) return '密码强度：中等'
    return '密码强度：强'
  }

  return (
    <div className={`text-xs bg-gray-50 p-3 rounded-md border ${className}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="font-medium text-gray-700">密码要求</span>
        <span className={`font-medium ${getStrengthColor()}`}>
          {getStrengthText()}
        </span>
      </div>
      
      <div className="space-y-1">
        {requirements.map((req) => {
          const passed = req.test(password)
          return (
            <div
              key={req.key}
              className={`flex items-center transition-colors ${
                passed ? 'text-green-600' : 'text-gray-400'
              }`}
            >
              <span className="mr-2 text-sm">
                {passed ? '✓' : '○'}
              </span>
              <span className="text-sm">{req.label}</span>
            </div>
          )
        })}
      </div>
      
      {/* 强度条 */}
      <div className="mt-2">
        <div className="flex space-x-1">
          {[1, 2, 3, 4, 5].map((level) => (
            <div
              key={level}
              className={`h-1 flex-1 rounded-full transition-colors ${
                level <= strength
                  ? strength <= 2
                    ? 'bg-red-400'
                    : strength <= 4
                    ? 'bg-yellow-400'
                    : 'bg-green-400'
                  : 'bg-gray-200'
              }`}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

export default PasswordStrengthIndicator