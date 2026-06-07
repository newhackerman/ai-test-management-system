import { useState } from 'react'
import { AlertTriangle, CheckCircle, Info, Palette, Square, Type, XCircle } from 'lucide-react'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import { Checkbox } from '@/components/ui/Checkbox'
import { Input } from '@/components/ui/Input'
import { Label } from '@/components/ui/Label'
import { Loading } from '@/components/ui/Loading'
import { Progress } from '@/components/ui/Progress'
import { Separator } from '@/components/ui/Separator'
import { Skeleton } from '@/components/ui/Skeleton'
import { Textarea } from '@/components/ui/Textarea'
import { ThemeToggle } from '@/components/ui/ThemeToggle'

function DesignSystem() {
  const [progress, setProgress] = useState(65)
  const [loading, setLoading] = useState(false)
  const [checked, setChecked] = useState(false)

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">设计系统</h1>
          <p className="text-muted-foreground">展示系统中使用的基础 UI 组件和设计规范。</p>
        </div>
        <ThemeToggle />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Palette className="h-5 w-5" />
            颜色系统
          </CardTitle>
          <CardDescription>系统使用的主要颜色和语义化颜色。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            {[
              ['bg-primary', 'Primary'],
              ['bg-secondary', 'Secondary'],
              ['bg-destructive', 'Destructive'],
              ['bg-muted', 'Muted'],
            ].map(([colorClass, label]) => (
              <div key={label} className="space-y-2">
                <div className={`h-16 rounded-md ${colorClass}`} />
                <p className="text-sm font-medium">{label}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>按钮组件</CardTitle>
          <CardDescription>不同变体和尺寸的按钮组件。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Button>默认按钮</Button>
            <Button variant="secondary">次要按钮</Button>
            <Button variant="outline">轮廓按钮</Button>
            <Button variant="ghost">幽灵按钮</Button>
            <Button variant="destructive">危险按钮</Button>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button size="sm">小按钮</Button>
            <Button size="default">默认按钮</Button>
            <Button size="lg">大按钮</Button>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button disabled={loading} onClick={() => setLoading((value) => !value)}>
              {loading ? '加载中...' : '切换加载状态'}
            </Button>
            <Button disabled>禁用按钮</Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>表单组件</CardTitle>
          <CardDescription>输入框、文本域、复选框等表单元素。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="input-demo">输入框</Label>
              <Input id="input-demo" placeholder="请输入内容..." />
            </div>
            <div className="space-y-2">
              <Label htmlFor="textarea-demo">文本域</Label>
              <Textarea id="textarea-demo" placeholder="请输入多行内容..." />
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <Checkbox id="checkbox-demo" checked={checked} onCheckedChange={setChecked} />
            <Label htmlFor="checkbox-demo">复选框示例</Label>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>状态组件</CardTitle>
          <CardDescription>徽章、进度条、加载状态等组件。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Badge>默认徽章</Badge>
            <Badge variant="secondary">次要徽章</Badge>
            <Badge variant="outline">轮廓徽章</Badge>
            <Badge variant="destructive">危险徽章</Badge>
          </div>

          <div className="space-y-2">
            <Label>进度条（{progress}%）</Label>
            <Progress value={progress} className="w-full" />
            <div className="flex gap-2">
              <Button size="sm" onClick={() => setProgress((value) => Math.max(0, value - 10))}>
                -10%
              </Button>
              <Button size="sm" onClick={() => setProgress((value) => Math.min(100, value + 10))}>
                +10%
              </Button>
            </div>
          </div>

          <div className="space-y-2">
            <Label>加载状态</Label>
            <div className="flex items-center gap-4">
              <Loading />
              <Loading />
              <Loading size="lg" />
            </div>
          </div>

          <div className="space-y-2">
            <Label>骨架屏</Label>
            <div className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Type className="h-5 w-5" />
            图标系统
          </CardTitle>
          <CardDescription>系统中使用的 Lucide 图标。</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-4 gap-4 md:grid-cols-8">
            {[
              [CheckCircle, 'CheckCircle'],
              [AlertTriangle, 'AlertTriangle'],
              [XCircle, 'XCircle'],
              [Info, 'Info'],
              [Palette, 'Palette'],
              [Type, 'Type'],
              [Square, 'Square'],
            ].map(([Icon, label]) => (
              <div key={label as string} className="flex flex-col items-center gap-2">
                <Icon className="h-6 w-6" />
                <span className="text-xs">{label as string}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="space-y-4">
        <h3 className="text-lg font-semibold">分隔符</h3>
        <Separator />
        <p className="text-sm text-muted-foreground">分隔符用于在内容之间创建视觉分隔。</p>
      </div>
    </div>
  )
}

export default DesignSystem
