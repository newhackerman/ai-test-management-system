import React from 'react'
import { Upload } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/Card'
import { Input } from '../../../components/ui/Input'
import { Textarea } from '../../../components/ui/Textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/Select'

export interface AutomationScriptForm {
  enabled: boolean
  script_name: string
  framework: string
  language: string
  browser: string
  script_path: string
  script_content: string
}

export const defaultAutomationScriptForm: AutomationScriptForm = {
  enabled: false,
  script_name: '',
  framework: 'PYTEST',
  language: 'PYTHON',
  browser: 'chrome',
  script_path: '',
  script_content: '',
}

const frameworkOptions = [
  { value: 'PYTEST', label: 'Pytest / Python' },
  { value: 'PLAYWRIGHT', label: 'Playwright' },
  { value: 'SELENIUM', label: 'Selenium' },
  { value: 'JEST', label: 'Jest / JavaScript' },
  { value: 'CYPRESS', label: 'Cypress' },
]

const languageOptions = [
  { value: 'PYTHON', label: 'Python' },
  { value: 'JAVASCRIPT', label: 'JavaScript' },
  { value: 'JAVA', label: 'Java' },
  { value: 'CSHARP', label: 'C#' },
]

const browserOptions = [
  { value: 'chrome', label: 'Chrome' },
  { value: 'firefox', label: 'Firefox' },
  { value: 'edge', label: 'Edge' },
  { value: 'webkit', label: 'WebKit' },
]

const readFileAsText = (file: File) => new Promise<string>((resolve, reject) => {
  const reader = new FileReader()
  reader.onload = () => resolve(String(reader.result || ''))
  reader.onerror = () => reject(reader.error)
  reader.readAsText(file)
})

const inferFramework = (fileName: string, content: string) => {
  const lowerName = fileName.toLowerCase()
  const lowerContent = content.toLowerCase()
  if (lowerName.includes('playwright') || lowerContent.includes('playwright')) return 'PLAYWRIGHT'
  if (lowerName.includes('selenium') || lowerContent.includes('selenium')) return 'SELENIUM'
  if (lowerName.endsWith('.js') || lowerName.endsWith('.ts')) return 'JEST'
  return 'PYTEST'
}

const inferLanguage = (fileName: string) => {
  const lowerName = fileName.toLowerCase()
  if (lowerName.endsWith('.js') || lowerName.endsWith('.ts')) return 'JAVASCRIPT'
  if (lowerName.endsWith('.java')) return 'JAVA'
  if (lowerName.endsWith('.cs')) return 'CSHARP'
  return 'PYTHON'
}

const AutomationScriptEditor = ({
  value,
  onChange,
}: {
  value: AutomationScriptForm
  onChange: (value: AutomationScriptForm) => void
}) => {
  const update = (patch: Partial<AutomationScriptForm>) => onChange({ ...value, ...patch })

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    const content = await readFileAsText(file)
    update({
      enabled: true,
      script_path: file.name,
      script_name: value.script_name || file.name.replace(/\.[^.]+$/, ''),
      script_content: content,
      framework: inferFramework(file.name, content),
      language: inferLanguage(file.name),
    })
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <CardTitle>自动化脚本</CardTitle>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={value.enabled}
              onChange={(event) => update({ enabled: event.target.checked })}
            />
            配置可执行脚本
          </label>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 md:grid-cols-4">
          <Field label="脚本名称">
            <Input
              value={value.script_name}
              onChange={(event) => update({ script_name: event.target.value })}
              placeholder="例如：login_smoke"
              disabled={!value.enabled}
            />
          </Field>
          <Field label="框架">
            <OptionSelect value={value.framework} options={frameworkOptions} onChange={(framework) => update({ framework })} disabled={!value.enabled} />
          </Field>
          <Field label="语言">
            <OptionSelect value={value.language} options={languageOptions} onChange={(language) => update({ language })} disabled={!value.enabled} />
          </Field>
          <Field label="浏览器">
            <OptionSelect value={value.browser} options={browserOptions} onChange={(browser) => update({ browser })} disabled={!value.enabled} />
          </Field>
        </div>
        <div className="grid gap-4 md:grid-cols-[1fr_220px]">
          <Field label="脚本文件">
            <Input value={value.script_path} onChange={(event) => update({ script_path: event.target.value })} placeholder="可选；脚本文件名或路径" disabled={!value.enabled} />
          </Field>
          <Field label="上传脚本">
            <label className={`flex h-10 cursor-pointer items-center justify-center gap-2 rounded-md border px-3 text-sm ${value.enabled ? 'bg-background' : 'cursor-not-allowed opacity-60'}`}>
              <Upload className="h-4 w-4" />
              选择文件
              <input
                type="file"
                className="hidden"
                disabled={!value.enabled}
                accept=".py,.js,.ts,.java,.cs,.txt"
                onChange={handleFileChange}
              />
            </label>
          </Field>
        </div>
        <Field label="脚本内容">
          <Textarea
            rows={12}
            value={value.script_content}
            onChange={(event) => update({ script_content: event.target.value })}
            placeholder="粘贴 Python / JavaScript / Playwright / Selenium / Pytest 等可执行脚本内容"
            disabled={!value.enabled}
          />
        </Field>
      </CardContent>
    </Card>
  )
}

const Field = ({ label, children }: { label: string; children: React.ReactNode }) => (
  <label className="block space-y-2 text-sm font-medium">
    <span>{label}</span>
    {children}
  </label>
)

const OptionSelect = ({ value, options, onChange, disabled }: { value: string; options: Array<{ value: string; label: string }>; onChange: (value: string) => void; disabled?: boolean }) => (
  <Select value={value} onValueChange={onChange} disabled={disabled}>
    <SelectTrigger><SelectValue /></SelectTrigger>
    <SelectContent>
      {options.map((option) => <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>)}
    </SelectContent>
  </Select>
)

export default AutomationScriptEditor
