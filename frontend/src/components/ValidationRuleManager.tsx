import React, { useEffect, useState } from 'react'
import { Button, Form, Input, InputNumber, Modal, Select, Space, Switch, Tabs, Tag, message } from 'antd'
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons'

interface ValidationRule {
  type: string
  enabled: boolean
  value?: string | number | boolean
  message?: string
}

interface ValidationRuleManagerProps {
  visible: boolean
  onCancel: () => void
  configKey?: string
  configType?: string
  currentValue?: unknown
  environment?: string
  onRuleChange?: (rules: ValidationRule[]) => void
}

const ruleOptions = [
  { label: '必填', value: 'required' },
  { label: '最小长度', value: 'minLength' },
  { label: '最大长度', value: 'maxLength' },
  { label: '正则表达式', value: 'pattern' },
  { label: '最小值', value: 'min' },
  { label: '最大值', value: 'max' },
  { label: '邮箱', value: 'email' },
  { label: 'URL', value: 'url' },
]

const ValidationRuleManager: React.FC<ValidationRuleManagerProps> = ({
  visible,
  onCancel,
  configKey = '',
  configType = 'STRING',
  currentValue,
  environment = 'dev',
  onRuleChange,
}) => {
  const [rules, setRules] = useState<ValidationRule[]>([])
  const [testValue, setTestValue] = useState('')
  const [testMessage, setTestMessage] = useState('')

  useEffect(() => {
    if (visible) {
      setTestValue(currentValue == null ? '' : String(currentValue))
      setTestMessage('')
    }
  }, [currentValue, visible])

  const addRule = () => {
    setRules((current) => [...current, { type: 'required', enabled: true, message: '校验不通过' }])
  }

  const updateRule = (index: number, patch: Partial<ValidationRule>) => {
    setRules((current) => current.map((rule, currentIndex) => (currentIndex === index ? { ...rule, ...patch } : rule)))
  }

  const removeRule = (index: number) => {
    setRules((current) => current.filter((_, currentIndex) => currentIndex !== index))
  }

  const runValidation = () => {
    const failedRule = rules.find((rule) => {
      if (!rule.enabled) return false
      if (rule.type === 'required') return testValue.trim() === ''
      if (rule.type === 'minLength') return testValue.length < Number(rule.value || 0)
      if (rule.type === 'maxLength') return testValue.length > Number(rule.value || Infinity)
      if (rule.type === 'pattern') {
        try {
          return !new RegExp(String(rule.value || '')).test(testValue)
        } catch {
          return true
        }
      }
      if (rule.type === 'min') return Number(testValue) < Number(rule.value)
      if (rule.type === 'max') return Number(testValue) > Number(rule.value)
      if (rule.type === 'email') return !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(testValue)
      if (rule.type === 'url') return !/^https?:\/\//.test(testValue)
      return false
    })

    setTestMessage(failedRule ? failedRule.message || '校验不通过' : '校验通过')
  }

  const handleSave = () => {
    onRuleChange?.(rules)
    message.success('校验规则已保存')
    onCancel()
  }

  return (
    <Modal
      open={visible}
      title="校验规则管理"
      width={760}
      onCancel={onCancel}
      onOk={handleSave}
      okText="保存"
      cancelText="取消"
    >
      <div className="mb-4 flex flex-wrap gap-2 text-sm text-gray-600">
        <Tag>{configKey || '未选择配置'}</Tag>
        <Tag>{configType}</Tag>
        <Tag>{environment}</Tag>
      </div>

      <Tabs
        items={[
          {
            key: 'rules',
            label: '规则配置',
            children: (
              <Space direction="vertical" className="w-full" size="middle">
                {rules.map((rule, index) => (
                  <div key={`${rule.type}-${index}`} className="rounded-md border p-3">
                    <div className="grid grid-cols-1 gap-3 md:grid-cols-[160px_1fr_1fr_auto_auto]">
                      <Select
                        value={rule.type}
                        options={ruleOptions}
                        onChange={(type) => updateRule(index, { type })}
                      />
                      <Input
                        value={String(rule.value ?? '')}
                        placeholder="规则值"
                        onChange={(event) => updateRule(index, { value: event.target.value })}
                      />
                      <Input
                        value={rule.message}
                        placeholder="错误提示"
                        onChange={(event) => updateRule(index, { message: event.target.value })}
                      />
                      <Switch checked={rule.enabled} onChange={(enabled) => updateRule(index, { enabled })} />
                      <Button danger icon={<DeleteOutlined />} onClick={() => removeRule(index)} />
                    </div>
                  </div>
                ))}
                <Button type="dashed" block icon={<PlusOutlined />} onClick={addRule}>
                  添加规则
                </Button>
              </Space>
            ),
          },
          {
            key: 'test',
            label: '测试校验',
            children: (
              <Form layout="vertical">
                <Form.Item label="测试值">
                  {configType === 'NUMBER' ? (
                    <InputNumber className="w-full" value={Number(testValue || 0)} onChange={(value) => setTestValue(String(value ?? ''))} />
                  ) : (
                    <Input.TextArea value={testValue} onChange={(event) => setTestValue(event.target.value)} rows={4} />
                  )}
                </Form.Item>
                <Space>
                  <Button type="primary" onClick={runValidation}>执行校验</Button>
                  {testMessage && <Tag color={testMessage === '校验通过' ? 'green' : 'red'}>{testMessage}</Tag>}
                </Space>
              </Form>
            ),
          },
        ]}
      />
    </Modal>
  )
}

export default ValidationRuleManager
